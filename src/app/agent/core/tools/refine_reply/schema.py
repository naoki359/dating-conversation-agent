from pydantic import BaseModel, Field


class RefineReplyStructuredOutputSchema(BaseModel):
    """LLM structured output schema for reply refinement."""

    refined_reply: str = Field(
        description="指摘事項を反映した修正版の返信文。",
    )

    reasoning: str = Field(
        description="どの指摘をどう反映して返信を修正したかの要約。",
    )

    applied_feedback: list[str] = Field(
        default_factory=list,
        description="修正時に反映した指摘事項の一覧。",
    )

    remaining_risks: list[str] = Field(
        default_factory=list,
        description="まだ懸念として残る点。",
    )
