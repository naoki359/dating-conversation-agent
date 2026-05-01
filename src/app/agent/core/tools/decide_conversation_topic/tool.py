from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.analyze_conversation_triggers.tool import (
    AnalyzeConversationTriggersTool,
)
from app.agent.core.tools.decide_conversation_topic.schema import (
    ConversationTopicStrategySchema,
)
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.formatCommon import (
    format_conversation_text,
    format_profile_text,
    format_self_profile_text,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store

_MIN_HISTORY_TURNS = 2


class DecideConversationTopicTool:
    """会話履歴から話題の継続・切り替え方針を判定する。

    会話履歴が不十分な場合は AnalyzeConversationTriggersTool に委譲し、
    十分な履歴がある場合は LLM で話題分析を行う。
    """

    name = "decide_conversation_topic"
    description = (
        "会話履歴を分析し、話題を継続するべきか切り替えるべきかを判定する。"
        "返信生成前に実行し、単調な返信を防ぐ。"
    )

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        """話題方針を判定し、結果を shared_canvas に保存する。"""
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)

        messages = scoped_store.get("conversation", {}).get("messages", [])

        # 会話履歴が不十分な場合は AnalyzeConversationTriggersTool に委譲
        if not self._has_sufficient_history(messages):
            triggers_result = AnalyzeConversationTriggersTool().execute(execution_id)
            default_strategy = ConversationTopicStrategySchema(
                current_topic="",
                same_topic_turns=0,
                should_continue_topic=True,
                reasoning="会話履歴が不十分なため、AnalyzeConversationTriggersTool を実行しました。",
            )
            scoped_canvas["conversation_topic_strategy"] = default_strategy.model_dump()
            return BaseToolResult(
                tool_name=self.name,
                success=triggers_result.success,
                summary="会話履歴が不十分なため、AnalyzeConversationTriggersTool を実行しました。",
                tool_result=default_strategy.model_dump(),
            )

        # 会話履歴がある場合は LLM で分析
        self_profile = scoped_store.get("self_profile", {})
        partner_profile = scoped_store.get("profile", {})

        self_profile_text = format_self_profile_text(self_profile)
        profile_text = format_profile_text(partner_profile)
        conversation_text = format_conversation_text(messages)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "self_profile_text": self_profile_text,
                    "profile_text": profile_text,
                    "conversation_text": conversation_text,
                }
            )

            structured_llm = self.llm.with_structured_output(ConversationTopicStrategySchema)
            result = structured_llm.invoke(prompt_value)
            strategy = ConversationTopicStrategySchema.model_validate(result)

            scoped_canvas["conversation_topic_strategy"] = strategy.model_dump()

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary=(
                    f"話題継続・切り替え方針を判定しました。"
                    f"（{'継続' if strategy.should_continue_topic else '切り替え'}）"
                ),
                tool_result=strategy.model_dump(),
            )

        except Exception as e:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"話題判定中にエラーが発生しました: {str(e)}",
                tool_result={},
            )

    def _has_sufficient_history(self, messages: list[dict[str, Any]]) -> bool:
        """往復が _MIN_HISTORY_TURNS 以上あるか確認する。"""
        self_count = sum(1 for m in messages if m.get("sender") == "self")
        other_count = sum(1 for m in messages if m.get("sender") == "other")
        return self_count >= _MIN_HISTORY_TURNS and other_count >= _MIN_HISTORY_TURNS

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"
