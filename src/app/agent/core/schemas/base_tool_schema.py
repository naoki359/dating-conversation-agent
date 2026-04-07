from typing import Any

from pydantic import BaseModel, Field


class BaseToolResult(BaseModel):
    tool_name: str = Field(
        ...,
        description="実行したツール名。",
    )

    success: bool = Field(
        ...,
        description="ツールの実行が成功したかどうか。",
    )

    summary: str = Field(
        ...,
        description="ツール実行結果の短い要約。",
    )

    tool_result: dict[str, Any] = Field(
        default_factory=dict,
        description="ツール固有の実行結果。tools/xxx/schema.py の内容を dict 化して保持する。",
    )