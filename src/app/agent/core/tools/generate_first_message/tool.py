from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.generate_first_message.schema import GenerateFirstMessageResultSchema
from app.agent.core.utils.formatCommon import (
    format_profile_text,
    format_self_profile_text,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store, shared_store


class GenerateFirstMessageTool:
    """プロフィールを基に初回メッセージを生成するツール。"""

    name = "generate_first_message"
    description = "会話履歴がない相手に対して、プロフィールを基に自然な初回メッセージを生成する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id) if execution_id else shared_store
        scoped_canvas = get_shared_canvas(execution_id)

        self_profile = scoped_store.get("self_profile", {})
        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", [])

        if not profile:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="初回メッセージ生成に必要なプロフィール情報が見つかりません。",
                tool_result={},
            )

        if messages:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="会話履歴が存在するため、初回メッセージ専用ツールは利用できません。",
                tool_result={},
            )

        try:
            prompt_value = self.prompt.invoke(
                {
                    "self_profile_text": self._build_self_profile_text(self_profile),
                    "profile_text": self._build_profile_text(profile),
                    "raw_profile_text": str(profile.get("raw_profile_text", "")).strip() or "プロフィール原文はありません。",
                    "picture_text": self._build_picture_text(profile.get("picture")),
                }
            )

            structured_llm = self.llm.with_structured_output(GenerateFirstMessageResultSchema)
            result = structured_llm.invoke(prompt_value)
            message_data = GenerateFirstMessageResultSchema.model_validate(result)

            scoped_canvas["generated_reply"] = message_data.reply_text
            scoped_canvas["reply_reasoning"] = message_data.reasoning
            scoped_canvas["initial_message_topic"] = message_data.selected_topic

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="プロフィールを基に初回メッセージを生成しました。",
                tool_result=message_data.model_dump(),
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"初回メッセージ生成中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_profile_text(self, profile: dict[str, Any]) -> str:
        return format_profile_text(profile)

    def _build_self_profile_text(self, profile: dict[str, Any]) -> str:
        return format_self_profile_text(profile)

    def _build_picture_text(self, picture: Any) -> str:
        if picture is None:
            return "写真情報はありません。"

        if isinstance(picture, str):
            text = picture.strip()
            return text or "写真情報はありません。"

        if isinstance(picture, list):
            items = [self._format_picture_item(item, index) for index, item in enumerate(picture, start=1)]
            items = [item for item in items if item]
            if not items:
                return "写真情報はありません。"
            return "\n".join(items)

        if isinstance(picture, dict):
            items = [f"- {key}: {str(value).strip()}" for key, value in picture.items() if str(value).strip()]
            if not items:
                return "写真情報はありません。"
            return "\n".join(items)

        text = str(picture).strip()
        return text or "写真情報はありません。"

    def _format_picture_item(self, item: Any, index: int) -> str:
        if isinstance(item, dict):
            description = str(item.get("description") or item.get("content") or "").strip()
            message_hint = str(item.get("message_hint") or item.get("memo") or "").strip()

            if not description and not message_hint:
                return ""

            lines = [f"- 写真{index}"]
            if description:
                lines.append(f"  - description: {description}")
            if message_hint:
                lines.append(f"  - message_hint: {message_hint}")
            return "\n".join(lines)

        text = str(item).strip()
        if not text:
            return ""
        return f"- 写真{index}: {text}"
