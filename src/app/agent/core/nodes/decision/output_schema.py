from pydantic import Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema


class DecisionOutputSchema(BaseOutputSchema):
    decided_action: str = Field(..., description="次に実行するアクション")
    action_reasoning: str = Field(..., description="そのアクションを選んだ理由")
    reply_focus_points: list[str] = Field(
        default_factory=list,
        description="返信生成時に意識したいポイント",
    )