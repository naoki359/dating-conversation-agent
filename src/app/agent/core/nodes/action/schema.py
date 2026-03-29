from typing import Any

from pydantic import Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema


class ActionOutputSchema(BaseOutputSchema):
    selected_tool: str = Field(
        ...,
        description="今回の Action ノードで実行したツール名。",
    )

    tool_result: Any = Field(
        default_factory=dict,
        description="実行したツールの結果",
    )

    is_finished: bool = Field(
        default=False,
        description="この時点でワークフローを終了してよいかどうか。",
    )