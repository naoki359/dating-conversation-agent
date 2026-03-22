from pydantic import BaseModel, Field


class BaseOutputSchema(BaseModel):
    node_name: str = Field(
        ...,
        description="この出力を生成したノード名。",
    )
    
    success: bool = Field(
        ...,
        description="ノードの処理が成功したかどうか。正常に判断・生成できた場合は true。",
    )

    reasoning: str = Field(
        ...,
        description=(
            "このノードがその結論や出力に至った理由。"
            "後から判断根拠を確認できるよう、簡潔かつ具体的に記載する。"
        ),
    )

    log_message: str = Field(
        default="",
        description=(
            "ログ出力用の短いメッセージ。"
            "アプリケーションログやデバッグ表示で利用することを想定する。"
        ),
    )