from pathlib import Path

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.check_reply_profile_fit.schema import (
    CheckReplyProfileFitResultSchema,
)
from app.agent.core.utils.improvement_feedback import (
    append_improvement_suggestions,
    dump_improvement_suggestions,
    merge_improvement_suggestions,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class CheckReplyProfileFitTool:
    """返信文がユーザーのプロフィール/性格と整合するかを評価するツール。"""

    name = "check_reply_profile_fit"
    description = "返信文のプロフィール/性格との合致度を評価し、改善提案を返す"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        profile = scoped_store.get("self_profile", {})
        reply_text = scoped_canvas.get("generated_reply", "")

        if not profile:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="プロフィール情報が見つかりません。",
                tool_result={},
            )

        if not reply_text:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="評価対象の返信文が見つかりません。",
                tool_result={},
            )

        try:
            prompt_value = self.prompt.invoke(
                {
                    "profile_text": profile,
                    "reply_text": reply_text,
                }
            )

            structured_llm = self.llm.with_structured_output(
                CheckReplyProfileFitResultSchema
            )
            result = structured_llm.invoke(prompt_value)

            # print(result)

            scoped_canvas["fit_score"] = result.fit_score
            normalized_suggestions = merge_improvement_suggestions(
                [],
                list(result.improvement_suggestions),
                default_priority="medium",
            )
            result.improvement_suggestions = normalized_suggestions
            append_improvement_suggestions(
                scoped_canvas,
                dump_improvement_suggestions(normalized_suggestions),
                default_priority="medium",
            )

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信文のプロフィール適合度を評価しました。",
                tool_result=result.model_dump(),
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"適合度チェック中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"
