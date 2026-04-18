from typing import Literal

from pydantic import BaseModel, Field


# 入力ソースを schema 側でも固定しておくことで、
# tool 側の実装と downstream の利用側の期待値を揃える。
TriggerSource = Literal[
    "latest_message",
    "partner_profile_summary",
    "partner_profile_raw",
]

# 一致度は UI や後続ツールで扱いやすい3段階に限定する。
TriggerMatchLevel = Literal["high", "partial", "none"]


class TriggerCandidateSchema(BaseModel):
    """1つの会話トリガー候補に対する抽出・照合結果。"""

    keyword: str = Field(..., description="会話トリガーとして抽出したキーワード。")
    normalized_keyword: str = Field(
        ...,
        description="比較用に正規化したキーワード。",
    )
    source: TriggerSource = Field(..., description="キーワードの抽出元。")
    source_quote: str = Field(..., description="抽出根拠となる原文。")
    category: str = Field(
        default="general",
        description="キーワードの大まかなカテゴリ。",
    )
    match_level: TriggerMatchLevel = Field(
        ...,
        description="自分のプロフィールとの一致度。",
    )
    match_reason: str = Field(..., description="一致度の判定理由。")
    related_self_profile_keywords: list[str] = Field(
        default_factory=list,
        description="一致判定に使った自分プロフィール側の関連キーワード。",
    )
    needs_research: bool = Field(
        default=False,
        description="会話を広げる前に追加調査が必要か。",
    )
    priority_score: int = Field(
        default=0,
        description="返信候補としての内部優先度スコア。",
    )


class AnalyzeConversationTriggersResultSchema(BaseModel):
    """会話トリガー分析ツールの最終出力。"""

    latest_message: str = Field(
        default="",
        description="相手の最新メッセージ。",
    )
    trigger_candidates: list[TriggerCandidateSchema] = Field(
        default_factory=list,
        description="抽出・照合した会話トリガー候補一覧。",
    )
    selected_keyword: str = Field(
        default="",
        description="優先度が最も高い採用候補キーワード。",
    )
    summary_notes: list[str] = Field(
        default_factory=list,
        description="抽出結果の要点メモ。",
    )