from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.refine_reply.schema import RefineReplyStructuredOutputSchema
from app.agent.core.utils.formatCommon import (
    format_conversation_with_updated_at,
    format_profile_text,
)
from app.agent.core.utils.improvement_feedback import FeedbackPriority
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class RefineReplyTool:
    """指摘事項を基に既存の返信案を修正するツール。"""

    name = "refine_reply"
    description = "指摘事項を反映して返信案を改善する"
    DEFAULT_MEDIUM_PRIORITY_MAX_LOOP_COUNT = 3

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
        if not feedback_items:
            scoped_canvas["reply_should_regenerate"] = False
            scoped_canvas["fit_score"] = 100
            scoped_canvas["reply_quality_score"] = 100
            scoped_canvas["reply_reasoning"] = "具体的な指摘事項が存在しなかったため、修正不要として完了しました。"
            scoped_canvas["improvement_suggestions"] = []

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="具体的な指摘事項が存在しなかったため、修正せず完了しました。",
                tool_result={
                    "refined_reply": original_reply,
                    "reasoning": "具体的な指摘事項が存在しなかったため、修正不要として完了しました。",
                    "applied_feedback": [],
                    "remaining_risks": [],
                },
            )

        feedback_text = self._build_feedback_text(feedback_items, original_text=original_reply)
        prompt_debug_text = ""

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
            prompt_debug_text = self._render_prompt_text(prompt_value)

            structured_llm = self.llm.with_structured_output(RefineReplyStructuredOutputSchema)
            result = structured_llm.invoke(prompt_value)

            debug_text = self._build_debug_output(
                prompt_text=prompt_debug_text,
                refined_reply=result.refined_reply
            )
            self._write_text_to_timestamped_file(debug_text)

            scoped_canvas["generated_reply"] = result.refined_reply
            scoped_canvas["reply_reasoning"] = result.reasoning

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="指摘事項を基に返信案を修正しました。再度評価を行ってください",
                tool_result=result.model_dump(),
            )
        except Exception as exc:
            if prompt_debug_text:
                error_debug_text = self._build_debug_output(
                    prompt_text=prompt_debug_text,
                    error_message=str(exc),
                )
                self._write_text_to_timestamped_file(error_debug_text)
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信修正中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _render_prompt_text(self, prompt_value: Any) -> str:
        if not hasattr(prompt_value, "to_messages"):
            return self._format_debug_section(
                title="[refine_reply] prompt_value",
                body=str(prompt_value),
            )

        message_blocks: list[str] = []
        for message in prompt_value.to_messages():
            role = getattr(message, "type", "unknown")
            content = getattr(message, "content", "")
            message_blocks.append(f"[{role}]\n{content}")
        return self._format_debug_section(
            title="[refine_reply] prompt",
            body=("\n" + ("-" * 80) + "\n").join(message_blocks),
        )

    def _build_debug_output(
        self,
        prompt_text: str,
        refined_reply: str | None = None,
        error_message: str | None = None,
    ) -> str:
        sections = [prompt_text]

        if refined_reply is not None:
            sections.append(
                self._format_debug_section(
                    title="[refine_reply] result.refined_reply",
                    body=refined_reply,
                )
            )

        if error_message is not None:
            sections.append(
                self._format_debug_section(
                    title="[refine_reply] error",
                    body=error_message,
                )
            )

        return "\n".join(sections) + "\n"

    def _format_debug_section(self, title: str, body: str) -> str:
        separator = "=" * 80
        return f"{title}\n{separator}\n{body}\n"

    def _write_text_to_timestamped_file(self, text: str) -> Path:
        output_dir = self._get_debug_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_path = output_dir / f"{timestamp}.txt"
        suffix = 1
        while output_path.exists():
            output_path = output_dir / f"{timestamp}_{suffix}.txt"
            suffix += 1

        output_path.write_text(text, encoding="utf-8")
        return output_path

    def _get_debug_output_dir(self) -> Path:
        return Path(__file__).resolve().parents[6] / "logs"  / "tmp"

    def _collect_feedback(self, scoped_canvas: dict[str, Any]) -> list[str]:
        raw_feedback = scoped_canvas.get("improvement_suggestions")
        if isinstance(raw_feedback, str) and raw_feedback.strip():
            return [raw_feedback.strip()]
        elif isinstance(raw_feedback, list):
            prioritized_feedback = self._collect_prioritized_feedback(raw_feedback, scoped_canvas)
            if prioritized_feedback:
                return prioritized_feedback

            legacy_feedback_items = [
                item.strip()
                for item in raw_feedback
                if isinstance(item, str) and item.strip()
            ]
            return self._dedupe_feedback_items(legacy_feedback_items)

        return []

    def _dedupe_feedback_items(self, feedback_items: list[str]) -> list[str]:
        if not feedback_items:
            return []

        deduped_feedback: list[str] = []
        seen: set[str] = set()
        for item in feedback_items:
            if item in seen:
                continue
            seen.add(item)
            deduped_feedback.append(item)

        return deduped_feedback

    def _collect_prioritized_feedback(
        self,
        raw_items: list[Any],
        scoped_canvas: dict[str, Any],
    ) -> list[str]:
        current_loop_count = int(scoped_canvas.get("current_action_loop_count", 0) or 0)
        selected_messages: list[str] = []
        seen: set[str] = set()

        for priority in ("high", "medium"):
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                message = str(raw_item.get("message", "")).strip()
                item_priority = str(raw_item.get("priority", "medium")).strip().lower()
                if not message or item_priority != priority:
                    continue
                if not self._should_apply_feedback(item_priority, current_loop_count):
                    continue
                if message in seen:
                    continue
                seen.add(message)
                selected_messages.append(message)

        return selected_messages

    def _should_apply_feedback(
        self,
        priority: FeedbackPriority | str,
        current_loop_count: int,
    ) -> bool:
        if priority == "high":
            return True
        if priority == "low":
            return False

        return current_loop_count <= self.DEFAULT_MEDIUM_PRIORITY_MAX_LOOP_COUNT

    def _build_feedback_text(self, feedback_items: list[str], original_text: str = "") -> str:
        lines: list[str] = []
        if original_text:
            lines.append(f"【修正対象の返信】\n{original_text}")
            lines.append("")
        lines.append("【指摘事項】")
        lines.extend(f"- {item}" for item in feedback_items)
        return "\n".join(lines)

    def _build_profile_text(self, profile: dict[str, Any]) -> str:
        return format_profile_text(
            profile,
            basic_info_header=None,
            include_raw_profile_text=True,
        )

    def _build_conversation_text(self, conversation: dict[str, Any]) -> str:
        return format_conversation_with_updated_at(conversation)
