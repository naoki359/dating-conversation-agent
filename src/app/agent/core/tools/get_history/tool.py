from pathlib import Path
import yaml

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.get_history.schema import GetHistoryResultSchema
from app.agent.core.utils.shared_store import shared_store


class GetHistoryTool():
    name = "get_history"
    description = "相手のプロフィールと会話履歴を取得する"

    def execute(self, user_id: str) -> BaseToolResult:
        if not user_id:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="ユーザーIDが指定されていません。",
                data={},
            )

        file_path = Path("data/test_user") / f"{user_id}.yaml"
        if not file_path.exists():
            # 初回の会話
            profile = {}
            conversation = []
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            profile = data.get("profile", {})
            conversation = data.get("conversation", {}).get("messages", [])

            # データをプロセス内で永続化
            shared_store["profile"] = profile
            shared_store["conversation"] = {
                "messages": conversation,
                "updated_at": data.get("conversation", {}).get("updated_at", ""),
            }

            result = GetHistoryResultSchema(
                partner_profile=shared_store["profile"],
                conversation_history=shared_store["conversation"],
            )

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="履歴を取得しました。",
            data=result.model_dump(),
        )