from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.score_reply_quality.schema import ScoreReplyQualityResultSchema
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class ScoreReplyQualityTool:
    """生成済み返信の品質・安全性を採点するツール。"""

    name = "score_reply_quality"
    description = "生成済み返信の品質・安全性を評価し、再作成要否と指摘事項を返す"

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
        recent_self_messages = self._extract_recent_self_messages(messages)

        pre_flags = self._detect_risks(reply_text, recent_self_messages)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "reply_text": reply_text,
                    "profile_text": self._build_profile_text(profile),
                    "conversation_text": self._build_conversation_text(messages),
                    "recent_self_messages": "\n".join(f"- {m}" for m in recent_self_messages) or "なし",
                    "pre_flags": self._build_pre_flags_text(pre_flags),
                }
            )

            structured_llm = self.llm.with_structured_output(ScoreReplyQualityResultSchema)
            result = structured_llm.invoke(prompt_value)

            final_score = self._apply_hard_penalty(result.quality_score, pre_flags)
            should_regenerate = result.should_regenerate or final_score < 70 or self._has_critical_flag(pre_flags)

            reasons = list(result.reasons)
            improvement_suggestions = list(result.improvement_suggestions)

            if pre_flags["sexual_risk"]:
                reasons.append("下ネタ/性的示唆のリスクを検知したため重大減点")
                improvement_suggestions.append("性的示唆を完全に除去し、相手が安心できる表現に修正する")

            if pre_flags["hurtful_risk"]:
                reasons.append("相手を傷つける可能性がある表現を検知したため重大減点")
                improvement_suggestions.append("否定・侮辱表現を避け、尊重と配慮を示す言い回しに変更する")

            if pre_flags["exact_duplicate"]:
                reasons.append("直近の自分の発言と同一内容のため大幅減点")
                improvement_suggestions.append("同じ内容の繰り返しを避け、新しい情報か質問を1つ追加する")

            output = result.model_dump()
            output["quality_score"] = final_score
            output["should_regenerate"] = should_regenerate
            output["reasons"] = self._dedupe_list(reasons)
            output["improvement_suggestions"] = self._dedupe_list(improvement_suggestions)

            existing_suggestions = scoped_canvas.get("improvement_suggestions", [])
            if isinstance(existing_suggestions, list):
                merged_suggestions = existing_suggestions + output["improvement_suggestions"]
            elif isinstance(existing_suggestions, str) and existing_suggestions.strip():
                merged_suggestions = [existing_suggestions.strip()] + output["improvement_suggestions"]
            else:
                merged_suggestions = list(output["improvement_suggestions"])

            scoped_canvas["improvement_suggestions"] = self._dedupe_list(merged_suggestions)
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

    def _detect_risks(self, reply_text: str, recent_self_messages: list[str]) -> dict[str, bool]:
        normalized = reply_text.lower()
        exact_duplicate = reply_text in recent_self_messages

        sexual_risk = any(keyword in normalized for keyword in self.SEXUAL_KEYWORDS)
        hurtful_risk = any(keyword in normalized for keyword in self.HURTFUL_KEYWORDS)

        return {
            "sexual_risk": sexual_risk,
            "hurtful_risk": hurtful_risk,
            "exact_duplicate": exact_duplicate,
        }

    def _apply_hard_penalty(self, score: int, pre_flags: dict[str, bool]) -> int:
        adjusted = max(0, min(100, score))

        if pre_flags.get("sexual_risk"):
            adjusted = min(adjusted, 25)

        if pre_flags.get("hurtful_risk"):
            adjusted = min(adjusted, 25)

        if pre_flags.get("exact_duplicate"):
            adjusted = min(adjusted, 45)

        return adjusted

    def _has_critical_flag(self, pre_flags: dict[str, bool]) -> bool:
        return bool(pre_flags.get("sexual_risk") or pre_flags.get("hurtful_risk"))

    def _build_profile_text(self, profile: dict[str, Any]) -> str:
        if not profile:
            return "プロフィール情報はありません。"

        name = profile.get("name", "")
        age = profile.get("age", "")
        profile_summary = profile.get("profile_summary", "")

        return dedent(
            f"""
            [基本情報]
            名前: {name}
            年齢: {age}

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
            message = str(msg.get("message", ""))
            sender_label = "相手" if sender == "other" else "自分"
            lines.append(f"{sender_label}: {message}")

        return "\n".join(lines)

    def _build_pre_flags_text(self, pre_flags: dict[str, bool]) -> str:
        lines = [
            f"- sexual_risk: {pre_flags.get('sexual_risk', False)}",
            f"- hurtful_risk: {pre_flags.get('hurtful_risk', False)}",
            f"- exact_duplicate: {pre_flags.get('exact_duplicate', False)}",
        ]
        return "\n".join(lines)

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
