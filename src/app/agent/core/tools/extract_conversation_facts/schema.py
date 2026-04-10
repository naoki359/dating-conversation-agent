from typing import Literal

from pydantic import BaseModel, Field


class ConversationFact(BaseModel):
    value: str = Field(description="抽出された値（例：新宿、新宿に近いなど）")
    confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "確信度。"
            "high=相手が明言している、"
            "medium=会話の流れから強く推測できる、"
            "low=薄い手がかりがある"
        )
    )
    source_quote: str = Field(description="根拠となった相手の発言の引用")


class ExtractedConversationFacts(BaseModel):
    meeting_area: ConversationFact | None = Field(
        default=None,
        description="会う場所を提案しやすいエリア（居住地または勤務地）。情報がなければ null。",
    )
