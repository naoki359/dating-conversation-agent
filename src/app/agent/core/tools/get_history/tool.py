from pathlib import Path
import yaml

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.get_history.schema import GetHistoryResultSchema
from app.agent.core.utils.shared_store import get_shared_store


class GetHistoryTool():
    name = "get_history"
    description = "相手のプロフィールと会話履歴を取得する"

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        user_id = scoped_store.get("user_id")
        if not user_id:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="ユーザーIDが指定されていません。",
                tool_result={},
            )

        file_path = Path("data/test_user") / f"{user_id}.yaml"
        if not file_path.exists():
            # 初回の会話
            profile = {}
            conversation = []
            updated_at = ""
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            profile = data.get("profile", {})
            conversation = data.get("conversation", {}).get("messages", [])
            updated_at = data.get("conversation", {}).get("updated_at", "")

        scoped_store["profile"] = profile
        scoped_store["conversation"] = {
            "messages": conversation,
            "updated_at": updated_at,
        }

        result = GetHistoryResultSchema(
            partner_profile=scoped_store["profile"],
            conversation_history=scoped_store["conversation"]["messages"],
        )

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="履歴を取得しました。",
            tool_result=result.model_dump(),
        )