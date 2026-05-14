import yaml

from app.agent.core.config.settings import Settings
from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.get_history.schema import GetHistoryResultSchema
from app.agent.core.utils.shared_store import (
    get_shared_store,
    normalize_meeting_timing_preference,
)


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

        file_path = Settings.get_data_dir() / f"{user_id}.yaml"

        print(f"GetHistoryTool: Loading history from {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"ユーザーデータが見つかりません: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        profile_raw = data.get("profile", {})
        profile = dict(profile_raw) if isinstance(profile_raw, dict) else {}
        profile["meeting_timing_preference"] = normalize_meeting_timing_preference(
            profile.get("meeting_timing_preference")
        )
        picture = data.get("picture")
        if picture is not None and isinstance(profile, dict) and "picture" not in profile:
            profile["picture"] = picture
        conversation_raw = data.get("conversation", {})
        conversation = conversation_raw.get("messages", [])
        updated_at = conversation_raw.get("updated_at", "")
        now_hint = conversation_raw.get("now_hint", "")

        scoped_store["profile"] = profile
        conversation_data: dict = {
            "messages": conversation,
            "updated_at": updated_at,
        }
        if now_hint:
            conversation_data["now_hint"] = now_hint
        scoped_store["conversation"] = conversation_data

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