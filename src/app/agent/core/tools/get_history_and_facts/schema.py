from typing import Any

from pydantic import BaseModel, Field


class GetHistoryAndFactsResultSchema(BaseModel):
    partner_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="相手のプロフィール情報。",
    )
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="会話履歴のメッセージリスト。",
    )
    extracted_facts: dict[str, Any] = Field(
        default_factory=dict,
        description="会話から抽出した重要な情報。",
    )
