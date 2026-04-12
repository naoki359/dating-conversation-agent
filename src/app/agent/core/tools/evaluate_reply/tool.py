from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.reply_rule_check.tool import ReplyRuleCheckTool
from app.agent.core.tools.reply_safety_check.tool import ReplySafetyCheckTool
from app.agent.core.utils.shared_store import get_shared_canvas


class EvaluateReplyTool:
    """返信文の安全性とルールを一括評価するツール。"""

    name = "evaluate_reply"
    description = "返信文の安全性とルール評価をまとめて実行する"

    def __init__(self) -> None:
        self.safety_tool = ReplySafetyCheckTool()
        self.rule_tool = ReplyRuleCheckTool()

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

        rule_result = self.rule_tool.execute(execution_id)
        if not rule_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信ルールの評価に失敗しました: {rule_result.summary}",
                tool_result={
                    "reply_safety_check": safety_result.tool_result,
                    "reply_rule_check": rule_result.model_dump(),
                },
            )

        scoped_canvas = get_shared_canvas(execution_id)
        should_regenerate = any(
            [
                bool(safety_result.tool_result.get("should_regenerate", False)),
                bool(rule_result.tool_result.get("should_regenerate", False)),
            ]
        )
        scoped_canvas["reply_should_regenerate"] = should_regenerate

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="返信の安全性とルールを評価しました。",
            tool_result={
                "reply_safety_check": safety_result.tool_result,
                "reply_rule_check": rule_result.tool_result,
                "should_regenerate": should_regenerate,
            },
        )
