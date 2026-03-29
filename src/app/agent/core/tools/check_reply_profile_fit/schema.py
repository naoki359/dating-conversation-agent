from pydantic import BaseModel, Field


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
        description="合致/不一致の主な理由。",
    )

    improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="返信文をより本人らしくする改善提案。",
    )

    revised_reply: str = Field(
        default="",
        description="必要に応じて改善後の返信例。",
    )
