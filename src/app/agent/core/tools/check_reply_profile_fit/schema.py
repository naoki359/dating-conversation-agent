from pydantic import BaseModel, Field

from app.agent.core.utils.improvement_feedback import ImprovementSuggestionSchema


class CheckReplyProfileFitResultSchema(BaseModel):
    """返信文とユーザー性格・プロフィールの整合性チェック結果。"""

    fit_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="プロフィール/性格との合致度スコア(0-100)。",
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="返信文のプロフィール合致度スコア（0-100）に対する理由",
    )

    improvement_suggestions: list[ImprovementSuggestionSchema] = Field(
        default_factory=list,
        description="返信文をより本人らしくする改善提案。",
    )
