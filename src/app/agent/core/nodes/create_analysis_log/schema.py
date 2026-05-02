from pydantic import Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema


class CreateAnalysisLogOutputSchema(BaseOutputSchema):
    trace_id: str = Field(
        ...,
        description="今回の返信生成のトレースID。",
    )
    log_path: str = Field(
        ...,
        description="保存した分析用ログファイルのパス。",
    )
    final_reply: str = Field(
        ...,
        description="最終的にユーザーに提示する返信文。",
    )
    intent: str = Field(
        ...,
        description="返信生成時の意図。",
    )
    target_message_id: str = Field(
        ...,
        description="今回の返信生成対象となった相手メッセージID。",
    )
