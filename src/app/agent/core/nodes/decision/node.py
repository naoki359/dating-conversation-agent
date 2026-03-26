from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.decision.schema import DecisionOutputSchema
from app.agent.core.schemas.state import AgentState
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.config.settings import Settings


class DecisionNode(BaseNode):
    node_name = "decision_node"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, state: AgentState) -> DecisionOutputSchema:
        profile_text = self._build_profile_text(state)
        conversation_text = self._build_conversation_text(state)

        prompt_value = self.prompt.invoke(
            {
                "node_name": self.node_name,
                "profile_text": profile_text,
                "conversation_text": conversation_text,
            }
        )

        structured_llm = self.llm.with_structured_output(DecisionOutputSchema)
        result = structured_llm.invoke(prompt_value)

        result.node_name = self.node_name
        return result

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_profile_text(self, state: AgentState) -> str:
        profile = state.get("profile", {})

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

    def _build_conversation_text(self, state: AgentState) -> str:
        conversation = state.get("conversation", {})
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

    @staticmethod
    def _indent_block(text: str, spaces: int) -> str:
        indent = " " * spaces
        lines = text.splitlines() or [text]
        return "\n".join(f"{indent}{line}" for line in lines)
    
    def console_render(self, result: DecisionOutputSchema) -> None:
        if not Settings.AGENT_LOCAL_MODE:
            return

        print("")
        print("相手の返答をもとに、次の進め方を整理しています...")
        print("")

        if result.thought_process:
            print("考えたこと:")
            for i, step in enumerate(result.thought_process, start=1):
                print(f"  {i}. {step}")
            print("")

        print("結論:")
        print(f"  {result.summary}")
        print("")