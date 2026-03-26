from typing import Any

from pydantic import Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema


class ActionOutputSchema(BaseOutputSchema):
    selected_tool: str = Field(
        ...,
        description="今回の Action ノードで実行したツール名。",
    )

    tool_result: dict[str, Any] = Field(
        default_factory=dict,
        description="実行したツールの結果。tools/xxx/schema.py の内容を dict で保持する。",
    )

    generated_reply: str | None = Field(
        default=None,
        description="生成された返信文。返信生成系ツールでない場合は None。",
    )

    reply_reasoning: str | None = Field(
        default=None,
        description="返信文生成理由。返信生成系ツールでない場合は None。",
    )

    is_finished: bool = Field(
        default=False,
        description="この時点でワークフローを終了してよいかどうか。",
    )