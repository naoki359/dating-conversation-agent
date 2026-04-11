from pathlib import Path
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.reply_safety_check.schema import ReplySafetyCheckResultSchema
from app.agent.core.utils.improvement_feedback import (
    ImprovementSuggestionSchema,
    append_improvement_suggestions,
    dump_improvement_suggestions,
    merge_improvement_suggestions,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class ReplySafetyCheckTool:
    """生成済み返信の安全性を評価するツール。"""

    name = "reply_safety_check"
    description = "生成済み返信の倫理面・安全面を確認し、再生成要否を返す"

    SEXUAL_KEYWORDS = [
        "エッチ",
        "エロ",
        "下ネタ",
        "セックス",
        "ホテル",
        "体の関係",
        "裸",
    ]

    HURTFUL_KEYWORDS = [
        "きもい",
        "ブス",
        "うざい",
        "死ね",
        "消えろ",
        "頭悪い",
    ]

    PRESSURING_KEYWORDS = [
        "今すぐ会おう",
        "絶対会おう",
        "断らないで",
        "ホテル行こ",
    ]

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        reply_text = str(scoped_canvas.get("generated_reply", "")).strip()
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", []) if isinstance(conversation, dict) else []

        if not reply_text:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="評価対象の返信文が見つかりません。",
                tool_result={},
            )

        pre_flags = self._detect_risks(reply_text)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "reply_text": reply_text,
                    "conversation_text": self._build_conversation_text(messages),
                    "pre_flags": self._build_pre_flags_text(pre_flags),
                }
            )

            structured_llm = self.llm.with_structured_output(ReplySafetyCheckResultSchema)
            result = structured_llm.invoke(prompt_value)

            safety_ok = result.safety_ok and not self._has_critical_flag(pre_flags)
            should_regenerate = result.should_regenerate or not safety_ok
            reasons = list(result.reasons)
            suggestions = list(result.improvement_suggestions)
            detected_risks = list(result.detected_risks)

            if pre_flags["sexual_risk"]:
                reasons.append("性的な示唆または過度な下ネタのリスクを検知しました。")
                suggestions.append(
                    ImprovementSuggestionSchema(
                        message="性的な含みを完全に外し、安心感のある話題に置き換えてください。",
                        priority="high",
                    )
                )
                detected_risks.append("sexual")

            if pre_flags["hurtful_risk"]:
                reasons.append("侮辱的または相手を傷つける表現のリスクを検知しました。")
                suggestions.append(
                    ImprovementSuggestionSchema(
                        message="否定や攻撃ではなく、相手を尊重する表現に修正してください。",
                        priority="high",
                    )
                )
                detected_risks.append("hurtful")

            if pre_flags["pressuring_risk"]:
                reasons.append("相手に圧をかける表現のリスクを検知しました。")
                suggestions.append(
                    ImprovementSuggestionSchema(
                        message="相手が断りやすい余白を残した誘い方に修正してください。",
                        priority="high",
                    )
                )
                detected_risks.append("pressuring")

            normalized_suggestions = merge_improvement_suggestions(
                [],
                suggestions,
                default_priority="high",
            )

            output = {
                "safety_ok": safety_ok,
                "should_regenerate": should_regenerate,
                "reasons": self._dedupe_list(reasons),
                "improvement_suggestions": dump_improvement_suggestions(normalized_suggestions),
                "detected_risks": self._dedupe_list(detected_risks),
            }

            scoped_canvas["reply_safety_ok"] = safety_ok
            scoped_canvas["reply_safety_reasons"] = output["reasons"]
            scoped_canvas["reply_should_regenerate"] = bool(
                scoped_canvas.get("reply_should_regenerate", False) or should_regenerate
            )
            append_improvement_suggestions(
                scoped_canvas,
                output["improvement_suggestions"],
                default_priority="high",
            )

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信の安全性を確認しました。" if safety_ok else "返信に安全性の問題があり、再生成が必要と判定しました。",
                tool_result=output,
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信安全性チェック中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _detect_risks(self, reply_text: str) -> dict[str, bool]:
        normalized = reply_text.lower()
        return {
            "sexual_risk": any(keyword in normalized for keyword in self.SEXUAL_KEYWORDS),
            "hurtful_risk": any(keyword in normalized for keyword in self.HURTFUL_KEYWORDS),
            "pressuring_risk": any(keyword in reply_text for keyword in self.PRESSURING_KEYWORDS),
        }

    def _has_critical_flag(self, pre_flags: dict[str, bool]) -> bool:
        return any(pre_flags.values())

    def _build_conversation_text(self, messages: list[dict[str, Any]]) -> str:
        if not messages:
            return "会話履歴はありません。"

        lines: list[str] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            sender = msg.get("sender", "")
            message = str(msg.get("message", "")).strip()
            if not message:
                continue
            sender_label = "相手" if sender == "other" else "自分"
            lines.append(f"{sender_label}: {message}")

        return "\n".join(lines) or "会話履歴はありません。"

    def _build_pre_flags_text(self, pre_flags: dict[str, bool]) -> str:
        return "\n".join(
            [
                f"- sexual_risk: {pre_flags.get('sexual_risk', False)}",
                f"- hurtful_risk: {pre_flags.get('hurtful_risk', False)}",
                f"- pressuring_risk: {pre_flags.get('pressuring_risk', False)}",
            ]
        )

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
