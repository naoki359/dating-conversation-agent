from pydantic import BaseModel, Field


class EvaluateReplyCandidatesResultSchema(BaseModel):
    """返信候補の評価結果。"""

    selected_reply_candidate_id: str = Field(
        default="",
        description="最終採用した返信候補ID。",
    )
    candidate_count: int = Field(
        default=0,
        description="評価対象候補数。",
    )
    passed_candidate_count: int = Field(
        default=0,
        description="安全性を通過した候補数。",
    )
    should_regenerate: bool = Field(
        default=False,
        description="再生成が必要かどうか。",
    )
    reply_selection_reason: str = Field(
        default="",
        description="候補選抜の理由。",
    )
