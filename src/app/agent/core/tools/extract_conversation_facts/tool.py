from pathlib import Path
from textwrap import dedent

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.extract_conversation_facts.schema import ExtractedConversationFacts
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import (
    DEFAULT_MEETING_TIMING_PREFERENCE,
    get_shared_canvas,
    get_shared_store,
)


class ExtractConversationFactsTool:
    """会話履歴から重要な情報を抽出するツール。"""

    name = "extract_conversation_facts"
    description = "会話履歴から住んでいる地域などの重要な情報を抽出する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        """会話履歴から重要な情報を抽出する。"""
        scoped_store = get_shared_store(execution_id)
        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", [])

        empty_facts = ExtractedConversationFacts()

        if not messages:
            scoped_canvas = get_shared_canvas(execution_id)
            scoped_canvas["conversation_facts"] = empty_facts.model_dump()
            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="会話履歴がないため、抽出できませんでした。",
                tool_result=empty_facts.model_dump(),
            )

        conversation_text = self._build_conversation_text(messages)
        profile_text = self._build_profile_text(profile)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "profile_text": profile_text,
                    "conversation_text": conversation_text,
                }
            )
            structured_llm = self.llm.with_structured_output(ExtractedConversationFacts)
            result = structured_llm.invoke(prompt_value)

            print("=== プロンプト ===")
            print(prompt_value)

            print("=== LLMからの抽出結果 ===")
            print(result)

            facts = ExtractedConversationFacts.model_validate(result)

            scoped_canvas = get_shared_canvas(execution_id)
            scoped_canvas["conversation_facts"] = facts.model_dump()

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="会話から重要な情報を抽出しました。",
                tool_result=facts.model_dump(),
            )
        except Exception as e:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"情報抽出中にエラーが発生しました: {str(e)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_conversation_text(self, messages: list) -> str:
        if not messages:
            return "会話履歴はありません。"
        lines = []
        for msg in messages:
            sender = msg.get("sender", "")
            message = msg.get("message", "")
            sender_label = "相手" if sender == "other" else "自分"
            lines.append(f"{sender_label}: {message}")
        return "\n".join(lines)

    def _build_profile_text(self, profile: dict) -> str:
        if not profile:
            return "プロフィール情報はありません。"

        name = profile.get("name", "")
        age = profile.get("age", "")
        raw_profile_text = profile.get("raw_profile_text", "")
        profile_summary = profile.get("profile_summary", "")
        meeting_timing_preference = (
            profile.get("meeting_timing_preference")
            or DEFAULT_MEETING_TIMING_PREFERENCE
        )

        return dedent(
            f"""
            [プロフィール基本情報]
            名前: {name}
            年齢: {age}
            出会うまでの希望: {meeting_timing_preference}

            [プロフィール要約]
            {profile_summary}

            [プロフィール原文]
            {raw_profile_text}
            """
        ).strip()
