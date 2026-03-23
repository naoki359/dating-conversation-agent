from pydantic import BaseModel, Field


class BaseOutputSchema(BaseModel):
    node_name: str = Field(
        ...,
        description="この出力を生成したノード名。",
    )

    success: bool = Field(
        ...,
        description="ノードの処理が成功したかどうか。",
    )

    summary: str = Field(
        ...,
        description="このノードの結論を短く要約したもの。",
    )

    reasoning: str = Field(
        ...,
        description=(
            "このノードがその結論や出力に至った理由の要約。"
            "結論を支える主要な根拠を簡潔にまとめる。"
        ),
    )

    thought_process: list[str] = Field(
        default_factory=list,
        description=(
            "結論に至るまでの思考過程。"
            "観察した事実、解釈、判断の流れを順番に記載する。"
        ),
    )