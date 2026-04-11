from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.check_reply_profile_fit.tool import CheckReplyProfileFitTool
from app.agent.core.tools.reply_rule_check.tool import ReplyRuleCheckTool
from app.agent.core.tools.reply_safety_check.tool import ReplySafetyCheckTool
from app.agent.core.tools.score_reply_quality.tool import ScoreReplyQualityTool
from app.agent.core.utils.shared_store import get_shared_canvas


class EvaluateReplyTool:
    """返信文の安全性・ルール・品質・プロフィール適合度を一括評価するツール。"""

    name = "evaluate_reply"
    description = "返信文の安全性・ルール・品質・プロフィール適合度評価をまとめて実行する"

    def __init__(self) -> None:
        self.safety_tool = ReplySafetyCheckTool()
        self.rule_tool = ReplyRuleCheckTool()
        self.score_tool = ScoreReplyQualityTool()
        self.fit_tool = CheckReplyProfileFitTool()

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

        score_result = self.score_tool.execute(execution_id)
        if not score_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信品質の評価に失敗しました: {score_result.summary}",
                tool_result={
                    "reply_safety_check": safety_result.tool_result,
                    "reply_rule_check": rule_result.tool_result,
                    "score_reply_quality": score_result.model_dump(),
                },
            )

        fit_result = self.fit_tool.execute(execution_id)
        if not fit_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"プロフィール適合度の評価に失敗しました: {fit_result.summary}",
                tool_result={
                    "reply_safety_check": safety_result.tool_result,
                    "reply_rule_check": rule_result.tool_result,
                    "score_reply_quality": score_result.tool_result,
                    "check_reply_profile_fit": fit_result.model_dump(),
                },
            )

        scoped_canvas = get_shared_canvas(execution_id)
        fit_score = int(fit_result.tool_result.get("fit_score", 0) or 0)
        should_regenerate = any(
            [
                bool(safety_result.tool_result.get("should_regenerate", False)),
                bool(rule_result.tool_result.get("should_regenerate", False)),
                bool(score_result.tool_result.get("should_regenerate", False)),
                fit_score < 80,
            ]
        )
        scoped_canvas["reply_should_regenerate"] = should_regenerate

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="返信の安全性・ルール・品質・プロフィール適合度を評価しました。",
            tool_result={
                "reply_safety_check": safety_result.tool_result,
                "reply_rule_check": rule_result.tool_result,
                "score_reply_quality": score_result.tool_result,
                "check_reply_profile_fit": fit_result.tool_result,
                "should_regenerate": should_regenerate,
            },
        )
