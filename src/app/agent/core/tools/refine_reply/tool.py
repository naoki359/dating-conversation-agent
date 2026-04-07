from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.refine_reply.schema import RefineReplyStructuredOutputSchema
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class RefineReplyTool:
    """指摘事項を基に既存の返信案を修正するツール。"""

    name = "refine_reply"
    description = "指摘事項を反映して返信案を改善する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        original_reply = scoped_canvas.get("generated_reply", "")
        fit_score = scoped_canvas.get("fit_score")
        self_profile = scoped_store.get("self_profile", {})
        partner_profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})

        if not original_reply:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="修正対象の返信案が見つかりません。",
                tool_result={},
            )

        feedback_items = self._collect_feedback(scoped_canvas)
        feedback_text = self._build_feedback_text(feedback_items)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "self_profile_text": self._build_profile_text(self_profile),
                    "partner_profile_text": self._build_profile_text(partner_profile),
                    "conversation_text": self._build_conversation_text(conversation),
                    "original_reply": original_reply,
                    "fit_score": fit_score if fit_score is not None else "未評価",
                    "feedback_text": feedback_text,
                }
            )

            structured_llm = self.llm.with_structured_output(RefineReplyStructuredOutputSchema)
            result = structured_llm.invoke(prompt_value)

            scoped_canvas["generated_reply"] = result.refined_reply
            scoped_canvas["reply_reasoning"] = result.reasoning

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="指摘事項を基に返信案を修正しました。",
                tool_result=result.model_dump(),
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信修正中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _collect_feedback(self, scoped_canvas: dict[str, Any]) -> list[str]:
        feedback_items: list[str] = []

        raw_feedback = scoped_canvas.get("fit_improvement_suggestion")
        if isinstance(raw_feedback, str) and raw_feedback.strip():
            feedback_items.append(raw_feedback.strip())
        elif isinstance(raw_feedback, list):
            feedback_items.extend(
                item.strip()
                for item in raw_feedback
                if isinstance(item, str) and item.strip()
            )

        reasons = scoped_canvas.get("reasons")
        if isinstance(reasons, list):
            feedback_items.extend(
                reason.strip()
                for reason in reasons
                if isinstance(reason, str) and reason.strip()
            )

        if not feedback_items:
            feedback_items.append(
                "明示的な指摘事項がないため、プロフィールとの整合性と自然さを優先して改善する"
            )

        deduped_feedback: list[str] = []
        seen: set[str] = set()
        for item in feedback_items:
            if item in seen:
                continue
            seen.add(item)
            deduped_feedback.append(item)

        return deduped_feedback

    def _build_feedback_text(self, feedback_items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in feedback_items)

    def _build_profile_text(self, profile: dict[str, Any]) -> str:
        if not profile:
            return "プロフィール情報はありません。"

        name = profile.get("name", "")
        age = profile.get("age", "")
        raw_profile_text = profile.get("raw_profile_text", "")
        profile_summary = profile.get("profile_summary", "")

        return dedent(
            f"""
            名前: {name}
            年齢: {age}

            [プロフィール要約]
            {profile_summary}

            [プロフィール原文]
            {raw_profile_text}
            """
        ).strip()

    def _build_conversation_text(self, conversation: dict[str, Any]) -> str:
        messages = conversation.get("messages", [])
        if not messages:
            return "会話履歴はありません。"

        lines: list[str] = []
        for msg in messages:
            sender = msg.get("sender", "")
            message = msg.get("message", "")
            lines.append(f"- {sender}: {message}")

        updated_at = conversation.get("updated_at", "")
        lines.append(f"- updated_at: {updated_at}")
        return "\n".join(lines)