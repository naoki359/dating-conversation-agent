from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Literal

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.analyze_conversation_triggers.schema import (
    AnalyzeConversationTriggersResultSchema,
    TriggerCandidateSchema,
)
from app.agent.core.config.personal_topics import (
    CATEGORY_KEYWORDS,
    DIRECT_TOPIC_KEYWORDS,
    OUTING_CATEGORIES,
    TOPIC_SUFFIXES,
)
from app.agent.core.utils.trigger_text import (
    clean_trigger_source_text,
    clean_trigger_topic,
    normalize_topic_text,
    extract_phrase_candidates,
    looks_like_non_topic,
    SPLIT_PATTERN,
)
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


# 入力ソースは最新メッセージを最優先しつつ、相手プロフィールも補助的に使う。
# 後段の優先度計算でこの種別ごとに重みを変えるため Literal で固定している。
SourceType = Literal[
    "latest_message",
    "partner_profile_summary",
    "partner_profile_raw",
]




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

        latest_message = self._get_latest_other_message(messages)
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

        # 自分側プロフィールも同じ抽出器でトピック化しておくことで、
        # 文字列比較とカテゴリ比較を同じ軸で扱えるようにする。
        self_topics = self._build_self_topics(self_profile)
        trigger_candidates = self._build_trigger_candidates(source_texts, self_topics)
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
    ) -> list[tuple[SourceType, str]]:
        """抽出対象のテキストを優先順位つきの source 一覧にまとめる。"""
        source_texts: list[tuple[SourceType, str]] = []
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
        texts = [
            str(self_profile.get("profile_summary", "")),
            str(self_profile.get("raw_profile_text", "")),
        ]
        seen: set[str] = set()
        topics: list[dict[str, str]] = []
        for text in texts:
            for topic in self._extract_topics_from_text(text):
                normalized = self._normalize_topic(topic)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                topics.append(
                    {
                        "keyword": topic,
                        "normalized_keyword": normalized,
                        "category": self._infer_category(topic),
                    }
                )
        return topics

    def _build_trigger_candidates(
        self,
        source_texts: list[tuple[SourceType, str]],
        self_topics: list[dict[str, str]],
    ) -> list[TriggerCandidateSchema]:
        """
        各入力ソースから候補語を集め、
        1. 同じ語の重複統合
        2. 自分プロフィールとの一致度判定
        3. 優先度スコア付け
        の順に整形する。
        """
        candidates_by_key: dict[str, dict[str, Any]] = {}

        for source, text in source_texts:
            for topic in self._extract_topics_from_text(text):
                normalized = self._normalize_topic(topic)
                if not normalized:
                    continue

                existing = candidates_by_key.get(normalized)
                source_score = self._source_score(source)
                category = self._infer_category(topic)

                # 最新メッセージ由来か、具体語か、カテゴリ推定できるかで
                # まず基礎点を決める。まだ self_profile との一致度は加算しない。
                base_priority = source_score + self._topic_specificity_score(topic, category)

                if existing is None or base_priority > int(existing["priority_score"]):
                    candidates_by_key[normalized] = {
                        "keyword": topic,
                        "normalized_keyword": normalized,
                        "source": source,
                        "source_quote": text,
                        "category": category,
                        "priority_score": base_priority,
                    }

        candidates: list[TriggerCandidateSchema] = []
        for candidate_data in candidates_by_key.values():
            # 照合ロジックは exact match / category match / broad outing match の順。
            # ここで返る match_level を priority に反映する。
            match_level, related_keywords, match_reason = self._match_with_self_profile(
                candidate_keyword=str(candidate_data["keyword"]),
                candidate_normalized=str(candidate_data["normalized_keyword"]),
                candidate_category=str(candidate_data["category"]),
                self_topics=self_topics,
            )

            priority_score = int(candidate_data["priority_score"]) + self._match_score(match_level)
            candidates.append(
                TriggerCandidateSchema(
                    keyword=str(candidate_data["keyword"]),
                    normalized_keyword=str(candidate_data["normalized_keyword"]),
                    source=candidate_data["source"],
                    source_quote=str(candidate_data["source_quote"]),
                    category=str(candidate_data["category"]),
                    match_level=match_level,
                    match_reason=match_reason,
                    related_self_profile_keywords=related_keywords,
                    needs_research=(match_level == "none"),
                    priority_score=priority_score,
                )
            )

        sorted_candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate.priority_score,
                self._source_score(candidate.source),
                len(candidate.keyword),
            ),
            reverse=True,
        )
        return self._prune_generic_duplicates(sorted_candidates)

    def _prune_generic_duplicates(
        self,
        candidates: list[TriggerCandidateSchema],
    ) -> list[TriggerCandidateSchema]:
        """
        具体語がある場合に汎称を落とす。

        例:
        - すみだ水族館 があるなら 水族館 は不要
        - 下村観山展 があるなら 展 は不要
        """
        pruned: list[TriggerCandidateSchema] = []
        for candidate in candidates:
            duplicated = False
            for existing in pruned:
                if (
                    existing.category == candidate.category
                    and existing.normalized_keyword != candidate.normalized_keyword
                    and existing.normalized_keyword.endswith(candidate.normalized_keyword)
                    and len(existing.normalized_keyword) > len(candidate.normalized_keyword)
                ):
                    duplicated = True
                    break
            if not duplicated:
                pruned.append(candidate)
        return pruned

    def _extract_topics_from_text(self, text: str) -> list[str]:
        """
        1. 語尾ベースのフレーズ抽出
        2. 会話フック語彙の直接検出
        3. 区切り文字単位の補助抽出
        の3段で候補を集める。

        単一の形態素解析に寄せず、会話のフックになりやすい語だけを
        ルールベースで拾う方針にしている。
        """
        cleaned_text = clean_trigger_source_text(text)
        if not cleaned_text:
            return []
        
        # 下記の3パターンで候補を取得する
        candidates: list[str] = []

        # パターン１：語尾を利用したフレーズ抽出
        for phrase in extract_phrase_candidates(cleaned_text):
            # ふるい落としきれなかったノイズや、話題として弱い語はここで落とす。
            topic = self._clean_topic(phrase)
            if topic:
                candidates.append(topic)

        # パターン２：会話フック語彙の直接検出（suffix抽出の取りこぼし補完）
        for keyword in DIRECT_TOPIC_KEYWORDS:
            if keyword in cleaned_text:
                topic = self._clean_topic(keyword)
                if topic:
                    candidates.append(topic)

        # パターン３：区切り文字単位の補助抽出
        # ここは recall を補うための保険で、ノイズは _clean_topic 側で落とす。
        for token in SPLIT_PATTERN.split(cleaned_text):
            topic = self._clean_topic(token)
            if not topic:
                continue
            if self._is_topic_like(topic):
                candidates.append(topic)
            candidates.extend(self._extract_compound_topics(topic))

        seen: set[str] = set()
        deduplicated: list[str] = []
        for candidate in candidates:
            normalized = self._normalize_topic(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduplicated.append(candidate)

        return deduplicated



    def _extract_compound_topics(self, token: str) -> list[str]:
        """スラッシュや中黒で並列列挙された話題を個別トピックに分解する。"""
        parts: list[str] = []
        for separator in ("/", "・"):
            if separator in token:
                parts.extend(segment.strip() for segment in token.split(separator))

        cleaned_parts: list[str] = []
        for part in parts:
            topic = self._clean_topic(part)
            if topic:
                cleaned_parts.append(topic)
        return cleaned_parts

    def _clean_topic(self, raw_topic: str) -> str:
        """
        候補語から会話トリガーとして不要な修飾を落とす。

        例:
        - 最近は下村観山展 -> 下村観山展
        - すみだ水族館で -> すみだ水族館
        - クラゲみました -> クラゲ
        """
        topic = clean_trigger_topic(raw_topic)
        if not topic:
            return ""
        if looks_like_non_topic(topic):
            return ""
        return topic


    def _is_topic_like(self, topic: str) -> bool:
        """補助抽出した語が、少なくとも何らかの話題カテゴリに属しそうかを判定する。"""
        if any(topic.endswith(suffix) for suffix in TOPIC_SUFFIXES):
            return True
        return self._infer_category(topic) != "general"

    def _normalize_topic(self, topic: str) -> str:
        """句読点や記号差分を無視して比較できるように正規化する。"""
        return normalize_topic_text(topic)

    def _infer_category(self, keyword: str) -> str:
        """候補語を粗い興味カテゴリに割り当てる。"""
        normalized = self._normalize_topic(keyword)
        for category, category_keywords in CATEGORY_KEYWORDS.items():
            if any(self._normalize_topic(term) in normalized for term in category_keywords):
                return category
        return "general"

    def _match_with_self_profile(
        self,
        *,
        candidate_keyword: str,
        candidate_normalized: str,
        candidate_category: str,
        self_topics: list[dict[str, str]],
    ) -> tuple[Literal["high", "partial", "none"], list[str], str]:
        """
        候補語と self_profile の一致度を3段階で判定する。

        - high: 語として直接つながる
        - partial: 同じカテゴリ、または外出系の近い話題
        - none: 明示的な接点がない
        """
        exact_matches: list[str] = []
        category_matches: list[str] = []

        for self_topic in self_topics:
            self_keyword = self_topic["keyword"]
            self_normalized = self_topic["normalized_keyword"]
            self_category = self_topic["category"]

            if candidate_normalized in self_normalized or self_normalized in candidate_normalized:
                exact_matches.append(self_keyword)
                continue

            if candidate_category != "general" and candidate_category == self_category:
                category_matches.append(self_keyword)

        if exact_matches:
            return (
                "high",
                exact_matches[:5],
                f"自分のプロフィールに {', '.join(exact_matches[:3])} があり、直接つながる話題です。",
            )

        if category_matches:
            unique_category_matches = list(dict.fromkeys(category_matches))
            return (
                "partial",
                unique_category_matches[:5],
                f"{candidate_keyword} は自分の {', '.join(unique_category_matches[:3])} と同系統の話題です。",
            )

        if candidate_category in OUTING_CATEGORIES:
            broad_matches = [
                self_topic["keyword"]
                for self_topic in self_topics
                if self_topic["category"] in OUTING_CATEGORIES
            ]
            if broad_matches:
                unique_broad_matches = list(dict.fromkeys(broad_matches))
                return (
                    "partial",
                    unique_broad_matches[:5],
                    f"{candidate_keyword} は自分の外出系の興味 ({', '.join(unique_broad_matches[:3])}) に近い話題です。",
                )

        return (
            "none",
            [],
            "自分のプロフィール内に明確な接点が見つからない話題です。",
        )

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

    def _source_score(self, source: str) -> int:
        """どのソース由来の話題かに応じて優先度の基礎点を返す。"""
        if source == "latest_message":
            return 40
        if source == "partner_profile_summary":
            return 25
        return 15

    def _topic_specificity_score(self, topic: str, category: str) -> int:
        """具体的な施設名・展示名・カテゴリ既知語を上に出すための補正点。"""
        score = 5
        if category != "general":
            score += 10
        if any(topic.endswith(suffix) for suffix in TOPIC_SUFFIXES):
            score += 10
        if len(topic) >= 4:
            score += 5
        return score

    def _match_score(self, match_level: str) -> int:
        """self_profile との近さを最終優先度へ加点する。"""
        if match_level == "high":
            return 40
        if match_level == "partial":
            return 20
        return 0