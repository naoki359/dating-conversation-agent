from pydantic import BaseModel, Field

from app.agent.core.utils.improvement_feedback import ImprovementSuggestionSchema


class ReplySafetyCheckResultSchema(BaseModel):
    safety_ok: bool = Field(
        ...,
        description="返信が安全で送信可能かどうか。",
    )

    should_regenerate: bool = Field(
        ...,
        description="安全性の観点で返信を再生成すべきかどうか。",
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="安全性の評価理由。",
    )

    improvement_suggestions: list[ImprovementSuggestionSchema] = Field(
        default_factory=list,
        description="安全性の改善提案。",
    )

    detected_risks: list[str] = Field(
        default_factory=list,
        description="検知したリスクカテゴリ。",
    )
