from pydantic import BaseModel, Field

from app.agent.core.utils.improvement_feedback import ImprovementSuggestionSchema


class QualityDeductionItem(BaseModel):
    category: str = Field(
        ...,
        description="減点カテゴリ（例: sexual, hurtful, duplicate, unnatural）。",
    )

    points: int = Field(
        ...,
        ge=0,
        le=100,
        description="減点値（0-100）。",
    )

    reason: str = Field(
        ...,
        description="減点理由。",
    )


class ScoreReplyQualityResultSchema(BaseModel):
    quality_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="返信品質スコア（0-100）。",
    )

    should_regenerate: bool = Field(
        ...,
        description="返信を再作成すべきかどうか。",
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="評価理由。",
    )

    improvement_suggestions: list[ImprovementSuggestionSchema] = Field(
        default_factory=list,
        description="改善提案。",
    )

    deduction_breakdown: list[QualityDeductionItem] = Field(
        default_factory=list,
        description="減点内訳。",
    )
