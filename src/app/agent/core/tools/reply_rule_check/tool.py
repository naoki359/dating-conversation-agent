from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.reply_rule_check.schema import ReplyRuleCheckResultSchema
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import (
    DEFAULT_MEETING_TIMING_PREFERENCE,
    get_shared_canvas,
    get_shared_store,
)


class ReplyRuleCheckTool:
    """生成済み返信のプロダクトルール遵守を評価するツール。"""

    name = "reply_rule_check"
    description = "生成済み返信が質問数や表現ルールを守れているかを確認する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        reply_text = str(scoped_canvas.get("generated_reply", "")).strip()
        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})

        if not reply_text:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="評価対象の返信文が見つかりません。",
                tool_result={},
            )

        messages = conversation.get("messages", []) if isinstance(conversation, dict) else []
        pre_flags = self._detect_rule_flags(reply_text)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "reply_text": reply_text,
                    "conversation_text": self._build_conversation_text(messages),
                    "profile_text": self._build_profile_text(profile),
                    "pre_flags": self._build_pre_flags_text(pre_flags),
                }
            )

            structured_llm = self.llm.with_structured_output(ReplyRuleCheckResultSchema)
            result = structured_llm.invoke(prompt_value)

            rule_score = self._apply_hard_penalty(result.rule_score, pre_flags)
            passed = result.passed and not self._has_critical_rule_violation(pre_flags)
            should_regenerate = result.should_regenerate or not passed or rule_score < 70
            reasons = list(result.reasons)
            suggestions = list(result.improvement_suggestions)
            violations = list(result.violations)

            if pre_flags["multiple_questions"]:
                reasons.append("質問が複数含まれており、返信ルールの『質問は1つまで』に抵触しています。")
                suggestions.append("質問は最も返しやすい1つだけに絞ってください。")
                violations.append("multiple_questions")

            if pre_flags["banned_word"]:
                reasons.append("禁止ワード『けっこう』を含んでいます。")
                suggestions.append("『けっこう』を別表現に置き換えてください。")
                violations.append("banned_word")

            if pre_flags["ambiguous_invite"]:
                reasons.append("誘い文に具体的な日時条件が不足しており、提案が曖昧です。")
                suggestions.append("候補日時や時間帯を具体的に示してください。")
                violations.append("ambiguous_invite")

            output = {
                "rule_score": rule_score,
                "passed": passed,
                "should_regenerate": should_regenerate,
                "reasons": self._dedupe_list(reasons),
                "improvement_suggestions": self._dedupe_list(suggestions),
                "violations": self._dedupe_list(violations),
            }

            scoped_canvas["reply_rule_score"] = rule_score
            scoped_canvas["reply_rule_passed"] = passed
            scoped_canvas["reply_rule_reasons"] = output["reasons"]
            scoped_canvas["reply_should_regenerate"] = bool(
                scoped_canvas.get("reply_should_regenerate", False) or should_regenerate
            )

            existing_suggestions = scoped_canvas.get("improvement_suggestions", [])
            if isinstance(existing_suggestions, list):
                merged_suggestions = existing_suggestions + output["improvement_suggestions"]
            elif isinstance(existing_suggestions, str) and existing_suggestions.strip():
                merged_suggestions = [existing_suggestions.strip()] + output["improvement_suggestions"]
            else:
                merged_suggestions = list(output["improvement_suggestions"])

            scoped_canvas["improvement_suggestions"] = self._dedupe_list(merged_suggestions)

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信ルールを評価しました。" if passed else "返信ルール違反を検知し、再生成が必要と判定しました。",
                tool_result=output,
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信ルール評価中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _detect_rule_flags(self, reply_text: str) -> dict[str, bool]:
        question_count = reply_text.count("?") + reply_text.count("？")
        normalized = reply_text.lower()
        looks_like_invite = any(keyword in reply_text for keyword in ["会", "飲", "ランチ", "ディナー", "通話", "電話"])
        has_specific_time = any(token in reply_text for token in ["時", "日", "土", "日曜", "平日", "来週", "今週", "午後", "夜"])

        return {
            "multiple_questions": question_count >= 2,
            "banned_word": "けっこう" in normalized,
            "ambiguous_invite": looks_like_invite and not has_specific_time,
        }

    def _has_critical_rule_violation(self, pre_flags: dict[str, bool]) -> bool:
        return bool(pre_flags.get("multiple_questions") or pre_flags.get("banned_word") or pre_flags.get("ambiguous_invite"))

    def _apply_hard_penalty(self, score: int, pre_flags: dict[str, bool]) -> int:
        adjusted = max(0, min(100, score))
        if pre_flags.get("multiple_questions"):
            adjusted = min(adjusted, 60)
        if pre_flags.get("banned_word"):
            adjusted = min(adjusted, 55)
        if pre_flags.get("ambiguous_invite"):
            adjusted = min(adjusted, 60)
        return adjusted

    def _build_profile_text(self, profile: dict[str, Any]) -> str:
        if not profile:
            return "プロフィール情報はありません。"

        name = profile.get("name", "")
        age = profile.get("age", "")
        profile_summary = profile.get("profile_summary", "")
        meeting_timing_preference = profile.get("meeting_timing_preference") or DEFAULT_MEETING_TIMING_PREFERENCE

        return dedent(
            f"""
            [基本情報]
            名前: {name}
            年齢: {age}
            出会うまでの希望: {meeting_timing_preference}

            [プロフィール要約]
            {profile_summary}
            """
        ).strip()

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
                f"- multiple_questions: {pre_flags.get('multiple_questions', False)}",
                f"- banned_word: {pre_flags.get('banned_word', False)}",
                f"- ambiguous_invite: {pre_flags.get('ambiguous_invite', False)}",
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
