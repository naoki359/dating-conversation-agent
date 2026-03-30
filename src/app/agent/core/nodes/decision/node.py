from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import override

from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.decision.schema import DecisionOutputSchema
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.config.settings import Settings
from app.agent.core.nodes.action.tool_enum import ToolEnum
from app.agent.core.utils.shared_store import shared_store


class DecisionNode(BaseNode):
    node_name = "decision_node"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, state: ReactState) -> DecisionOutputSchema:
        profile_text = self._build_profile_text()
        conversation_text = self._build_conversation_text()
        past_thought_process_text = self._build_past_thought_process_text(state)
        tools_info = self._build_tools_info()

        prompt_value = self.prompt.invoke(
            {
                "node_name": self.node_name,
                "profile_text": profile_text,
                "conversation_text": conversation_text,
                "past_thought_process_text": past_thought_process_text,
                "tools_info": tools_info,
            }
        )

        # self._debug_render_prompt(prompt_value, title=self.node_name)

        structured_llm = self.llm.with_structured_output(DecisionOutputSchema)
        result = structured_llm.invoke(prompt_value)

        result.node_name = self.node_name
        return result
    
    @override
    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        assert isinstance(node_result, DecisionOutputSchema)

        updated_state = {
            **state,
            "current_thought": node_result.current_thought,
            "required_tasks": node_result.required_tasks,
            "decided_action": node_result.decided_action,
            "action_reasoning": node_result.reasoning,
        }

        return updated_state

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_profile_text(self) -> str:
        profile = shared_store.get("profile", {})

        name = profile.get("name", "")
        age = profile.get("age", "")
        raw_profile_text = profile.get("raw_profile_text", "")
        profile_summary = profile.get("profile_summary", "")

        return dedent(
            f"""
            [プロフィール基本情報]
            名前: {name}
            年齢: {age}

            [プロフィール要約]
            {profile_summary}

            [プロフィール原文]
            {raw_profile_text}
            """
        ).strip()

    def _build_conversation_text(self) -> str:
        conversation = shared_store.get("conversation", {})
        messages = conversation.get("messages", [])

        if not messages:
            return "会話履歴はありません。"

        lines: list[str] = []
        for msg in messages:
            message_id = msg.get("id", "")
            timestamp = msg.get("timestamp", "")
            sender = msg.get("sender", "")
            message = msg.get("message", "")

            lines.append(
                dedent(
                    f"""
                    - id: {message_id}
                      timestamp: {timestamp}
                      sender: {sender}
                      message:
                    {self._indent_block(message, 4)}
                    """
                ).rstrip()
            )

        updated_at = conversation.get("updated_at", "")

        history_text = "\n".join(lines)

        return dedent(
            f"""
            [会話更新日時]
            {updated_at}

            [会話履歴]
            {history_text}
            """
        ).strip()

    def _build_past_thought_process_text(self, state: ReactState) -> str:
        history = state.get("history", [])
        if not history:
            return "過去の思考過程はありません。"

        blocks: list[str] = []
        for idx, item in enumerate(history, start=1):
            if isinstance(item, BaseOutputSchema):
                node_name = item.node_name
                summary = item.summary
            elif isinstance(item, dict):
                node_name = str(item.get("node_name", "unknown_node"))
                summary = str(item.get("summary", ""))
            else:
                continue

            if not summary:
                continue

            blocks.append(
                dedent(
                    f"""
                    [{idx}] node: {node_name}
                      - {summary}
                    """
                ).strip()
            )

        if not blocks:
            return "過去の思考過程はありません。"

        return "\n\n".join(blocks)

    @staticmethod
    def _indent_block(text: str, spaces: int) -> str:
        indent = " " * spaces
        lines = text.splitlines() or [text]
        return "\n".join(f"{indent}{line}" for line in lines)
    
    def _build_tools_info(self) -> str:
        """利用可能なツールの情報を構築する"""
        lines = []
        for tool in ToolEnum:
            lines.append(
                f"- {tool.name}: {tool.description} (完了後状態: {tool.completion_state})"
            )
        return "\n".join(lines)

    def console_render(self, result: DecisionOutputSchema) -> None:
        if not Settings.AGENT_LOCAL_MODE:
            return
        
        print("\n=== DecisionNode ===")
        print("")
        print("相手の返答をもとに、次の進め方を整理しています...")
        print("")

        # if result.thought_process:
        #     print("考えたこと:")
        #     for i, step in enumerate(result.thought_process, start=1):
        #         print(f"  {i}. {step}")
        #     print("")

        print("結論:")
        print(f"  {result.summary}")
        print("")

        print("次にやること:")
        print(f"  {result.decided_action}")
