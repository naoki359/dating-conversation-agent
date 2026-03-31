from typing import Literal

from pydantic import Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema


DecisionLiteral = Literal["continue", "end"]


class ObserveOutputSchema(BaseOutputSchema):
    """Observe node の出力スキーマ。fit_score と action_loop_count に基づいて判定結果を返す。"""

    fit_score: int | None = Field(
        ...,
        ge=0,
        le=100,
        description="前のステップで計算されたプロフィール合致度スコア（0-100）。None の場合は未評価。",
    )

    action_loop_count: int = Field(
        ...,
        ge=0,
        description="現在のアクションループの回数。",
    )

    decision: DecisionLiteral = Field(
        ...,
        description="判定結果。'continue' または 'end'。",
    )

    reasoning: str = Field(
        ...,
        description=(
            "判定の理由。fit_score や action_loop_count がどのような理由で"
            "'continue' または 'end' と判定されたかを説明する。"
        ),
    )
