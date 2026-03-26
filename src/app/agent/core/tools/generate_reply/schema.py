from pydantic import BaseModel, Field


class GenerateReplyResultSchema(BaseModel):
    reply_text: str = Field(
        ...,
        description="生成された返信文。",
    )

    reasoning: str = Field(
        ...,
        description="その返信文を生成した理由や意図の要約。",
    )