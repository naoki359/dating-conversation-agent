from pathlib import Path

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.schemas.state import ReactState
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.base_tool import BaseTool
from app.agent.core.tools.generate_reply.schema import GenerateReplyResultSchema
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml


class GenerateReplyTool(BaseTool):
    name = "generate_reply"
    description = "会話履歴とプロフィールをもとに返信文を生成する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, state: ReactState) -> BaseToolResult:
        profile = state.get("profile", {})
        conversation = state.get("conversation", [])
        current_thought = state.get("current_thought", "")
        required_tasks = state.get("required_tasks", [])
        decided_action = state.get("decided_action", "")

        conversation_text = self._format_conversation(conversation)

        structured_llm = self.llm.with_structured_output(GenerateReplyResultSchema)
        chain = self.prompt | structured_llm

        response = chain.invoke(
            {
                "profile": str(profile),
                "conversation": conversation_text,
                "current_thought": current_thought,
                "required_tasks": "\n".join(required_tasks),
                "decided_action": decided_action,
            }
        )

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="返信文を生成しました。",
            data=response.model_dump(),
        )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).with_name("prompt.yaml")

    def _format_conversation(self, conversation: list[dict | str]) -> str:
        lines: list[str] = []

        for msg in conversation:
            if isinstance(msg, dict):
                sender = msg.get("sender", "unknown")
                message = msg.get("message", "")
                lines.append(f"[{sender}] {message}")
            elif isinstance(msg, str):
                lines.append(f"[unknown] {msg}")
            else:
                lines.append(f"[unknown] {str(msg)}")

        return "\n".join(lines)