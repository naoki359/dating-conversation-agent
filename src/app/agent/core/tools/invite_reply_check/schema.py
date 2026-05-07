from pydantic import BaseModel, Field

from app.agent.core.utils.improvement_feedback import ImprovementSuggestionSchema


class InviteReplyCheckResultSchema(BaseModel):
    rule_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="デート誘い返信ルール遵守スコア。",
    )

    passed: bool = Field(
        ...,
        description="デート誘い返信ルールを満たしているかどうか。",
    )

    should_regenerate: bool = Field(
        ...,
        description="デート誘い返信ルール違反により再生成すべきかどうか。",
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="デート誘い返信ルールの評価理由。",
    )

    improvement_suggestions: list[ImprovementSuggestionSchema] = Field(
        default_factory=list,
        description="デート誘い返信ルール上の改善提案。",
    )
