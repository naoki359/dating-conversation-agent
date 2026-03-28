from typing import Any, Dict, List

from pydantic import BaseModel, Field


class GetHistoryResultSchema(BaseModel):
    partner_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="相手のプロフィール情報。",
    )

    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="会話履歴のメッセージリスト。",
    )