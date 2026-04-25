from pathlib import Path
from difflib import SequenceMatcher
import re
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.reply_rule_check.schema import ReplyRuleCheckResultSchema
from app.agent.core.utils.improvement_feedback import (
    ImprovementSuggestionSchema,
    append_improvement_suggestions,
    dump_improvement_suggestions,
    merge_improvement_suggestions,
)
from app.agent.core.utils.formatCommon import (
    format_conversation_text,
    format_profile_text,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class ReplyRuleCheckTool:
    """生成済み返信のプロダクトルール遵守を評価するツール。"""

    name = "reply_rule_check"
    description = "生成済み返信が質問数や表現ルールを守れているかを確認する"
    # BANNED_WORDS = ("けっこう", "かなり")
    # DUPLICATE_SIMILARITY_THRESHOLD = 0.55
    # TOPIC_HOOK_PATTERNS = (
    #     r"ちなみに",
    #     r"自分は",
    #     r"私は",
    #     r"自分だと",
    #     r"僕は",
    #     r"俺は",
    #     r"おすすめ",
    #     r"推し",
    #     r"好きなのは",
    #     r"印象に残ってる",
    #     r"印象に残っています",
    #     r"お気に入り",
    #     r"一番好き",
    # )

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

        try:
            output = self.evaluate_reply_text(reply_text, messages, profile)

            scoped_canvas["reply_rule_score"] = int(output["rule_score"])
            scoped_canvas["reply_rule_passed"] = bool(output["passed"])
            scoped_canvas["reply_rule_reasons"] = output["reasons"]
            scoped_canvas["reply_should_regenerate"] = bool(
                scoped_canvas.get("reply_should_regenerate", False) or output["should_regenerate"]
            )

            # append_improvement_suggestions(
            #     scoped_canvas,
            #     output["improvement_suggestions"],
            #     default_priority="high",
            # )

            scoped_canvas["improvement_suggestions"] = output["improvement_suggestions"]

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信ルールを評価しました。" if output["passed"] else "返信ルール違反を検知し、再生成が必要と判定しました。",
                tool_result=output,
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信ルール評価中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def evaluate_reply_text(
        self,
        reply_text: str,
        messages: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        # recent_self_messages = self._extract_recent_self_messages(messages)
        # pre_flags = self._detect_rule_flags(reply_text, recent_self_messages)

        prompt_value = self.prompt.invoke(
            {
                "reply_text": reply_text,
                "conversation_text": self._build_conversation_text(messages),
                "profile_text": format_profile_text(profile),
                # "pre_flags": self._build_pre_flags_text(pre_flags),
            }
        )

        structured_llm = self.llm.with_structured_output(ReplyRuleCheckResultSchema)
        result = structured_llm.invoke(prompt_value)

        rule_score = result.rule_score
        passed = result.passed
        should_regenerate = result.should_regenerate or not passed or rule_score < 70
        reasons = list(result.reasons)
        suggestions = list(result.improvement_suggestions)

        return {
            "rule_score": rule_score,
            "passed": passed,
            "should_regenerate": should_regenerate,
            "reasons": self._dedupe_list(reasons),
            "improvement_suggestions": dump_improvement_suggestions(suggestions),
        }

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"
    
    # 返信文と会話履歴の静的な調査
    # def _detect_rule_flags(self, reply_text: str, recent_self_messages: list[str]) -> dict[str, bool]:
    #     # 質問数カウント（全角半角両方の疑問符を考慮）
    #     question_count = reply_text.count("?") + reply_text.count("？")

    #     # 禁止ワードの検出や誘い文の特徴を捉えるために、正規化したテキストを用いる
    #     normalized = reply_text.lower()

    #     # デート打診か検知するためのキーワードと、具体的な日時条件の有無をチェック
    #     looks_like_invite = any(keyword in reply_text for keyword in ["会", "飲", "ランチ", "ディナー", "通話", "電話"])
    #     has_specific_time = any(token in reply_text for token in ["時", "日", "土", "日曜", "平日", "来週", "今週", "午後", "夜"])
    #     has_topic_hook = self._has_topic_hook(reply_text)

    #     return {
    #         "missing_hook": question_count == 0 and not has_topic_hook,
    #         "repeated_point": self._has_repeated_point(reply_text, recent_self_messages),
    #         "multiple_questions": question_count >= 2,
    #         "banned_word": any(word in normalized for word in self.BANNED_WORDS),
    #         "ambiguous_invite": looks_like_invite and not has_specific_time,
    #     }

    # def _has_critical_rule_violation(self, pre_flags: dict[str, bool]) -> bool:
    #     return bool(
    #         pre_flags.get("missing_hook")
    #         or pre_flags.get("repeated_point")
    #         or pre_flags.get("multiple_questions")
    #         or pre_flags.get("banned_word")
    #         or pre_flags.get("ambiguous_invite")
    #     )

    # def _build_profile_text(self, profile: dict[str, Any]) -> str:
    #     return format_profile_text(profile)

    def _build_conversation_text(self, messages: list[dict[str, Any]]) -> str:
        return format_conversation_text(
            messages,
            skip_invalid_messages=True,
            skip_empty_messages=True,
            strip_message=True,
        )

    def _build_pre_flags_text(self, pre_flags: dict[str, bool]) -> str:
        return "\n".join(
            [
                f"- missing_hook: {pre_flags.get('missing_hook', False)}",
                f"- repeated_point: {pre_flags.get('repeated_point', False)}",
                f"- multiple_questions: {pre_flags.get('multiple_questions', False)}",
                f"- banned_word: {pre_flags.get('banned_word', False)}",
                f"- ambiguous_invite: {pre_flags.get('ambiguous_invite', False)}",
            ]
        )
    
    # # 直近のメッセージを取得するが、相手のメッセージは除外して自分のメッセージだけを対象とする
    # def _extract_recent_self_messages(self, messages: list[dict[str, Any]]) -> list[str]:
    #     self_messages: list[str] = []
    #     for msg in messages:
    #         if not isinstance(msg, dict):
    #             continue
    #         if msg.get("sender") != "self":
    #             continue
    #         text = str(msg.get("message", "")).strip()
    #         if text:
    #             self_messages.append(text)

    #     return self_messages[-5:]

    # def _has_topic_hook(self, reply_text: str) -> bool:
    #     normalized = reply_text.strip()
    #     if not normalized:
    #         return False

    #     for pattern in self.TOPIC_HOOK_PATTERNS:
    #         if re.search(pattern, normalized):
    #             return True

    #     topic_offer_endings = (
    #         "好きです。",
    #         "好きです！",
    #         "派です。",
    #         "派です！",
    #         "おすすめです。",
    #         "おすすめです！",
    #     )
    #     return any(ending in normalized for ending in topic_offer_endings)
    
    # 今回の返信が、直近の自分の発言と“同じ内容を繰り返していないか”を判定する処理
    # def _has_repeated_point(self, reply_text: str, recent_self_messages: list[str]) -> bool:
    #     # 今回の返信文を、ある程度の意味の塊に分割して、空白や絵文字を削除して正規化する
    #     reply_segments = self._extract_meaningful_segments(reply_text)
    #     if not reply_segments:
    #         return False
        
    #     # 過去の自分のメッセージも同様に処理して、意味の塊ごとに今回の返信文の塊と類似度を比較する。
    #     # 類似度が一定以上なら、同じ内容を繰り返していると判定する。
    #     for recent_message in recent_self_messages:
    #         recent_segments = self._extract_meaningful_segments(recent_message)
    #         for reply_segment in reply_segments:
    #             for recent_segment in recent_segments:
    #                 similarity = SequenceMatcher(None, reply_segment, recent_segment).ratio()
    #                 if similarity >= self.DUPLICATE_SIMILARITY_THRESHOLD:
    #                     return True

    #     return False
    
    # テキストをある程度の意味の塊に分割して、空白や絵文字を削除して正規化する
    def _extract_meaningful_segments(self, text: str) -> list[str]:
        # 返信文を、ある程度の長さがある意味の塊に分割する。
        # "こんにちは！元気ですか？今日はいい天気ですね。"
        # ↓
        # ["こんにちは", "元気ですか", "今日はいい天気ですね", ""]
        raw_segments = re.split(r"[\n。！？!?]+", text)

        # 戻り値
        segments: list[str] = []

        # 分割した要素ごとに、空白や絵文字を削除して、ある程度の長さがあるものだけを抽出する
        for segment in raw_segments:
            stripped = self._normalize_text(segment)
            if len(stripped) < 8:
                continue
            segments.append(stripped)
        return segments
    
    # テキストを正規化して、空白や絵文字を削除する
    def _normalize_text(self, text: str) -> str:
        # 空白を削除
        normalized = re.sub(r"[\s\u3000]+", "", text)
        # 絵文字や記号を削除
        normalized = re.sub(r"[😊👍✨☺️♨️🎶wW…・,.、!！?？]", "", normalized)
        return normalized

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
