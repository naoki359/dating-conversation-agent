from pathlib import Path
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.score_reply_quality.schema import ScoreReplyQualityResultSchema
from app.agent.core.utils.improvement_feedback import (
    ImprovementSuggestionSchema,
    append_improvement_suggestions,
    dump_improvement_suggestions,
    merge_improvement_suggestions,
)
from app.agent.core.utils.formatCommon import format_conversation_text
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class ScoreReplyQualityTool:
    """生成済み返信の品質を採点するツール。"""

    name = "score_reply_quality"
    description = "生成済み返信の自然さ・継続性・重複を評価し、再作成要否と指摘事項を返す"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        reply_text = str(scoped_canvas.get("generated_reply", "")).strip()
        conversation = scoped_store.get("conversation", {})

        if not reply_text:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="評価対象の返信文が見つかりません。",
                tool_result={},
            )

        messages = conversation.get("messages", []) if isinstance(conversation, dict) else []
        recent_self_messages = self._extract_recent_self_messages(messages)
        duplicate_flags = self._detect_duplicate(reply_text, recent_self_messages)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "reply_text": reply_text,
                    "conversation_text": self._build_conversation_text(messages),
                    "recent_self_messages": "\n".join(f"- {m}" for m in recent_self_messages) or "なし",
                }
            )

            structured_llm = self.llm.with_structured_output(ScoreReplyQualityResultSchema)
            result = structured_llm.invoke(prompt_value)

            final_score = self._apply_hard_penalty(result.quality_score, duplicate_flags)
            should_regenerate = result.should_regenerate or final_score < 70

            reasons = list(result.reasons)
            improvement_suggestions = list(result.improvement_suggestions)

            if duplicate_flags["exact_duplicate"]:
                reasons.append("直近の自分の発言と同一内容のため大幅減点")
                improvement_suggestions.append(
                    ImprovementSuggestionSchema(
                        message="同じ内容の繰り返しを避け、新しい情報か質問を1つ追加する",
                        priority="medium",
                        alternative_text="直前の発言を繰り返さず、新しい情報か質問を1つ加えた返信にする",
                    )
                )

            normalized_suggestions = merge_improvement_suggestions(
                [],
                improvement_suggestions,
                default_priority="medium",
            )

            output = result.model_dump()
            output["quality_score"] = final_score
            output["should_regenerate"] = should_regenerate
            output["reasons"] = self._dedupe_list(reasons)
            output["improvement_suggestions"] = dump_improvement_suggestions(normalized_suggestions)

            append_improvement_suggestions(
                scoped_canvas,
                output["improvement_suggestions"],
                default_priority="medium",
            )
            scoped_canvas["reply_quality_score"] = final_score
            scoped_canvas["reply_should_regenerate"] = should_regenerate
            scoped_canvas["reply_quality_reasons"] = output["reasons"]

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信品質スコアを評価しました。" if not should_regenerate else "返信品質スコアを評価し、再作成が必要と判定しました。",
                tool_result=output,
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信品質スコア評価中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _extract_recent_self_messages(self, messages: list[dict[str, Any]]) -> list[str]:
        self_messages: list[str] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("sender") != "self":
                continue
            text = str(msg.get("message", "")).strip()
            if text:
                self_messages.append(text)

        return self_messages[-5:]

    def _detect_duplicate(self, reply_text: str, recent_self_messages: list[str]) -> dict[str, bool]:
        exact_duplicate = reply_text in recent_self_messages
        return {
            "exact_duplicate": exact_duplicate,
        }

    def _apply_hard_penalty(self, score: int, duplicate_flags: dict[str, bool]) -> int:
        adjusted = max(0, min(100, score))

        if duplicate_flags.get("exact_duplicate"):
            adjusted = min(adjusted, 45)

        return adjusted

    def _build_conversation_text(self, messages: list[dict[str, Any]]) -> str:
        return format_conversation_text(messages, skip_invalid_messages=True)

    def _dedupe_list(self, items: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()

        for item in items:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)

        return deduped
