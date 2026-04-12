from typing import Optional

from pydantic import BaseModel, Field


class GeneratedReplyCandidateSchema(BaseModel):
    """単一の返信候補を表すスキーマ。"""

    candidate_id: str = Field(description="返信候補ID。")
    theme_id: str = Field(description="返信テーマID。")
    theme_label: str = Field(description="返信テーマの表示名。")
    reply_text: str = Field(description="生成された返信テキスト。")
    tone: str = Field(description="返信のトーン。")
    reasoning: str = Field(description="この返信を生成した理由。")
    follow_up_suggestion: Optional[str] = Field(
        default=None,
        description="必要に応じた改善提案。",
    )
    selected: bool = Field(default=False, description="最終候補に選ばれたかどうか。")


class GenerateReplyCandidatesResultSchema(BaseModel):
    """複数の返信候補生成結果。"""

    reply_candidates: list[GeneratedReplyCandidateSchema] = Field(
        default_factory=list,
        description="生成された返信候補一覧。",
    )
