from pydantic import BaseModel, Field


class BaseOutputSchema(BaseModel):
    node_name: str = Field(..., description="ノード名")
    success: bool = Field(..., description="実行成功可否")
    log_message: str = Field(default="", description="ログ用メッセージ")