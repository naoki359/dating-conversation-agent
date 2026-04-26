from pydantic import Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema


class FinalizeReplyOutputSchema(BaseOutputSchema):
    final_reply: str = Field(
        ...,
        description="ReActループが生成した最終返信文。",
    )
