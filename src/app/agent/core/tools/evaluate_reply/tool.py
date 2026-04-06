from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.check_reply_profile_fit.tool import CheckReplyProfileFitTool
from app.agent.core.tools.score_reply_quality.tool import ScoreReplyQualityTool


class EvaluateReplyTool:
    """返信文の品質評価とプロフィール適合度評価を一括実行するツール。"""

    name = "evaluate_reply"
    description = "返信文の品質・安全性評価とプロフィール適合度評価をまとめて実行する"

    def __init__(self) -> None:
        self.score_tool = ScoreReplyQualityTool()
        self.fit_tool = CheckReplyProfileFitTool()

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        score_result = self.score_tool.execute(execution_id)
        if not score_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信品質の評価に失敗しました: {score_result.summary}",
                data={
                    "score_reply_quality": score_result.model_dump(),
                },
            )

        fit_result = self.fit_tool.execute(execution_id)
        if not fit_result.success:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"プロフィール適合度の評価に失敗しました: {fit_result.summary}",
                data={
                    "score_reply_quality": score_result.model_dump(),
                    "check_reply_profile_fit": fit_result.model_dump(),
                },
            )

        return BaseToolResult(
            tool_name=self.name,
            success=True,
            summary="返信品質とプロフィール適合度を評価しました。",
            data={
                "score_reply_quality": score_result.data,
                "check_reply_profile_fit": fit_result.data,
            },
        )
