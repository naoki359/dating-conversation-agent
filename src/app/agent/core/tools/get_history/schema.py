from typing import Any, Dict, List

from pydantic import Field

from app.agent.core.schemas.base_tool_schema import BaseToolResult


class GetHistoryResultSchema(BaseToolResult):
    partner_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="相手のプロフィール情報。",
    )

    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="会話履歴のメッセージリスト。",
    )