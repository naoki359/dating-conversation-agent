from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.invite_reply_check.tool import InviteReplyCheckTool
from app.agent.core.tools.reply_safety_check.tool import ReplySafetyCheckTool
from app.agent.core.utils.shared_store import get_shared_canvas


class EvaluateInviteReplyTool:
    """デートへ誘う返信の安全性と誘い文ルールを一括評価するツール。"""

    name = "evaluate_invite_reply"
    description = "デートへ誘う返信の安全性と誘い文ルール評価をまとめて実行する"

    def __init__(self) -> None:
        self.safety_tool = ReplySafetyCheckTool()
        self.invite_check_tool = InviteReplyCheckTool()

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        # 評価に対する改善提案を空にしておく
        # 追加するロジックの為、空にしないと過去の内容が残ってしまう
        scoped_canvas = get_shared_canvas(execution_id)
        scoped_canvas["improvement_suggestions"] = []

        safety_result = self.safety_tool.execute(execution_id)
        if not safety_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信安全性の評価に失敗しました: {safety_result.summary}",
                tool_result={
                    "reply_safety_check": safety_result.model_dump(),
                },
            )

        # 安全性NGの場合は invite_reply_check をスキップし再生成フラグを立てる
        if not safety_result.tool_result.get("safety_ok", True):
            scoped_canvas = get_shared_canvas(execution_id)
            scoped_canvas["reply_should_regenerate"] = True
            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="安全性NGのため、デート誘い評価をスキップし再生成フラグを設定しました。",
                tool_result={
                    "reply_safety_check": safety_result.tool_result,
                    "invite_reply_check": None,
                    "should_regenerate": True,
                },
            )

        invite_result = self.invite_check_tool.execute(execution_id)
        if not invite_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"デート誘い返信の評価に失敗しました: {invite_result.summary}",
                tool_result={
                    "reply_safety_check": safety_result.tool_result,
                    "invite_reply_check": invite_result.model_dump(),
                },
            )

        scoped_canvas = get_shared_canvas(execution_id)
        should_regenerate = any(
            [
                bool(safety_result.tool_result.get("should_regenerate", False)),
                bool(invite_result.tool_result.get("should_regenerate", False)),
            ]
        )
        scoped_canvas["reply_should_regenerate"] = should_regenerate

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="デート誘い返信の安全性と誘いルールを評価しました。",
            tool_result={
                "reply_safety_check": safety_result.tool_result,
                "invite_reply_check": invite_result.tool_result,
                "should_regenerate": should_regenerate,
            },
        )
