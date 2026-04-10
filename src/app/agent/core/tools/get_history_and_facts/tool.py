from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.get_history.tool import GetHistoryTool
from app.agent.core.tools.extract_conversation_facts.tool import ExtractConversationFactsTool
from app.agent.core.tools.get_history_and_facts.schema import GetHistoryAndFactsResultSchema
from app.agent.core.utils.shared_store import get_shared_store, get_shared_canvas


class GetHistoryAndFactsTool:
    """プロフィール・会話履歴の取得と重要情報の抽出を一括で行うツール。"""

    name = "get_history_and_facts"
    description = "相手のプロフィールと会話履歴を取得し、住んでいる地域などの重要な情報を抽出する"

    def __init__(self) -> None:
        self._get_history = GetHistoryTool()
        self._extract_facts = ExtractConversationFactsTool()

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        """履歴取得と重要情報抽出を順に実行する。"""
        history_result = self._get_history.execute(execution_id)
        if not history_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=history_result.summary,
                tool_result={},
            )

        facts_result = self._extract_facts.execute(execution_id)

        scoped_store = get_shared_store(execution_id)
        result = GetHistoryAndFactsResultSchema(
            partner_profile=scoped_store.get("profile", {}),
            conversation_history=scoped_store.get("conversation", {}).get("messages", []),
            extracted_facts=facts_result.tool_result if facts_result.success else {},
        )

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="履歴を取得し、重要な情報を抽出しました。",
            tool_result=result.model_dump(),
        )
