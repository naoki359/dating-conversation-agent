from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.analyze_conversation_triggers.schema import (
    AnalyzeConversationTriggersResultSchema,
    TriggerCandidateSchema,
    TriggerSource,
)
from app.agent.core.utils.trigger_text import (
    build_self_topics,
    build_trigger_candidates,
    extract_topics_from_text,
    infer_category,
)
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store




class AnalyzeConversationTriggersTool:
    """相手の発話とプロフィールから会話トリガーを抽出し、自分との一致度を判定する。"""

    name = "analyze_conversation_triggers"
    description = (
        "相手の最新メッセージとプロフィールから会話トリガー候補を抽出し、"
        "自分のプロフィールとの一致度を返す"
    )

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        """shared_store から分析対象を読み込み、抽出結果を shared_canvas に保存する。"""
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)

        self_profile = scoped_store.get("self_profile", {})
        partner_profile = scoped_store.get("profile", {})
        messages = scoped_store.get("conversation", {}).get("messages", [])

        if not self_profile:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="自分のプロフィール情報が見つかりません。",
                tool_result={},
            )
        
        # 最新の相手メッセージを取得
        latest_message = self._get_latest_other_message(messages)

        # 話題抽出対象のテキストをリストとしてまとめる。
        # 最新メッセージがあれば最優先、次いでプロフィール要約、最後に生テキストの順。
        source_texts = self._collect_source_texts(partner_profile, latest_message)
        if not source_texts:
            # 下流は canvas に結果がある前提で読む可能性があるため、
            # 空振りでも空の構造を明示的に残しておく。
            empty_result = AnalyzeConversationTriggersResultSchema(
                latest_message=latest_message,
                trigger_candidates=[],
                selected_keyword="",
                summary_notes=["分析対象となる相手メッセージまたはプロフィール情報がありません。"],
            )
            scoped_canvas["trigger_candidates"] = []
            scoped_canvas["selected_trigger_keyword"] = ""
            scoped_canvas["trigger_analysis_summary"] = list(empty_result.summary_notes)
            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="分析対象データがなかったため、会話トリガーは抽出されませんでした。",
                tool_result=empty_result.model_dump(),
            )

        # 自分側プロフィールを抽出器でトピック化しておく
        self_topics = self._build_self_topics(self_profile)

        # 相手の会話履歴とプロフィールからトリガー候補を抽出し、自分のプロフィールとの一致度を判定して優先度付けする。
        trigger_candidates = build_trigger_candidates(source_texts, self_topics)

        selected_keyword = trigger_candidates[0].keyword if trigger_candidates else ""
        summary_notes = self._build_summary_notes(trigger_candidates)

        result = AnalyzeConversationTriggersResultSchema(
            latest_message=latest_message,
            trigger_candidates=trigger_candidates,
            selected_keyword=selected_keyword,
            summary_notes=summary_notes,
        )

        scoped_canvas["trigger_candidates"] = [
            candidate.model_dump() for candidate in trigger_candidates
        ]
        scoped_canvas["selected_trigger_keyword"] = selected_keyword
        scoped_canvas["trigger_analysis_summary"] = list(summary_notes)

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="会話トリガー候補を抽出し、自分のプロフィールとの一致度を判定しました。",
            tool_result=result.model_dump(),
        )

    def _get_latest_other_message(self, messages: list[dict[str, Any]]) -> str:
        """会話履歴の末尾から見て、相手の最後の発話だけを取り出す。"""
        for message in reversed(messages):
            if message.get("sender") == "other":
                return str(message.get("message", "")).strip()
        return ""

    def _collect_source_texts(
        self,
        partner_profile: dict[str, Any],
        latest_message: str,
    ) -> list[tuple[TriggerSource, str]]:
        """抽出対象のテキストを優先順位つきの source 一覧にまとめる。"""
        source_texts: list[tuple[TriggerSource, str]] = []
        if latest_message:
            source_texts.append(("latest_message", latest_message))

        profile_summary = str(partner_profile.get("profile_summary", "")).strip()
        if profile_summary:
            source_texts.append(("partner_profile_summary", profile_summary))

        raw_profile_text = str(partner_profile.get("raw_profile_text", "")).strip()
        if raw_profile_text:
            source_texts.append(("partner_profile_raw", raw_profile_text))

        return source_texts

    def _build_self_topics(self, self_profile: dict[str, Any]) -> list[dict[str, str]]:
        """自分のプロフィール文を照合用トピック集合に正規化する。"""
        return build_self_topics(self_profile, extract_topics_from_text, infer_category)

    def _build_summary_notes(
        self,
        trigger_candidates: list[TriggerCandidateSchema],
    ) -> list[str]:
        """UI やログでそのまま使える簡易サマリを組み立てる。"""
        if not trigger_candidates:
            return ["会話を広げやすいキーワードは抽出されませんでした。"]

        grouped_counts: dict[str, int] = defaultdict(int)
        for candidate in trigger_candidates:
            grouped_counts[candidate.match_level] += 1

        notes = [
            f"抽出件数: {len(trigger_candidates)}件",
            f"一致: {grouped_counts['high']}件 / 準一致: {grouped_counts['partial']}件 / 不一致: {grouped_counts['none']}件",
        ]

        top_candidate = trigger_candidates[0]
        notes.append(
            f"最優先候補は {top_candidate.keyword} ({top_candidate.match_level}) です。"
        )
        return notes

