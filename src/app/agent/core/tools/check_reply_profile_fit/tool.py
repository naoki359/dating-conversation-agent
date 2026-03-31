from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.check_reply_profile_fit.schema import (
    CheckReplyProfileFitResultSchema,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import shared_store, shared_canvas


class CheckReplyProfileFitTool:
    """返信文がユーザーのプロフィール/性格と整合するかを評価するツール。"""

    name = "check_reply_profile_fit"
    description = "返信文のプロフィール/性格との合致度を評価し、改善提案を返す"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self) -> BaseToolResult:
        profile = shared_store.get("self_profile", {})
        reply_text = shared_canvas.get("generated_reply", "")

        if not profile:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="プロフィール情報が見つかりません。",
                data={},
            )

        if not reply_text:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="評価対象の返信文が見つかりません。",
                data={},
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

            shared_canvas["fit_score"] = result.fit_score
            shared_canvas["improvement_suggestions"] = result.improvement_suggestions

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信文のプロフィール適合度を評価しました。",
                data=result.model_dump(),
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"適合度チェック中にエラーが発生しました: {str(exc)}",
                data={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"
