import json
from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.invite_reply_check.schema import InviteReplyCheckResultSchema
from app.agent.core.utils.formatCommon import (
    format_conversation_text,
    format_profile_text,
)
from app.agent.core.utils.improvement_feedback import (
    append_improvement_suggestions,
    dump_improvement_suggestions,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class InviteReplyCheckTool:
    """デートへ誘う返信に特化したルールチェックツール。"""

    name = "invite_reply_check"
    description = "デート誘い返信の日時・場所の具体性やプロフィール整合性を評価する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())
        self.schedule = self._load_schedule()

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        reply_text = str(scoped_canvas.get("generated_reply", "")).strip()
        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})
        conversation_facts = scoped_canvas.get("conversation_facts", {})

        if not reply_text:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="評価対象の返信文が見つかりません。",
                tool_result={},
            )

        messages = conversation.get("messages", []) if isinstance(conversation, dict) else []

        try:
            output = self.evaluate_reply_text(reply_text, messages, profile, conversation_facts)

            scoped_canvas["reply_rule_score"] = int(output["rule_score"])
            scoped_canvas["reply_rule_passed"] = bool(output["passed"])
            scoped_canvas["reply_rule_reasons"] = output["reasons"]
            scoped_canvas["reply_should_regenerate"] = bool(
                scoped_canvas.get("reply_should_regenerate", False) or output["should_regenerate"]
            )

            append_improvement_suggestions(
                scoped_canvas,
                output["improvement_suggestions"],
                default_priority="high",
            )

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="デート誘い返信を評価しました。" if output["passed"] else "デート誘い返信のルール違反を検知し、再生成が必要と判定しました。",
                tool_result=output,
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"デート誘い返信の評価中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def evaluate_reply_text(
        self,
        reply_text: str,
        messages: list[dict[str, Any]],
        profile: dict[str, Any],
        conversation_facts: dict[str, Any],
    ) -> dict[str, Any]:
        prompt_value = self.prompt.invoke(
            {
                "reply_text": reply_text,
                "conversation_text": self._build_conversation_text(messages),
                "profile_text": format_profile_text(profile),
                "conversation_facts_text": self._build_conversation_facts_text(conversation_facts),
                "schedule_text": self._build_schedule_text(),
            }
        )

        structured_llm = self.llm.with_structured_output(InviteReplyCheckResultSchema)
        result = structured_llm.invoke(prompt_value)

        rule_score = result.rule_score
        passed = result.passed
        should_regenerate = result.should_regenerate or not passed or rule_score < 70
        reasons = list(result.reasons)
        suggestions = list(result.improvement_suggestions)

        return {
            "rule_score": rule_score,
            "passed": passed,
            "should_regenerate": should_regenerate,
            "reasons": reasons,
            "improvement_suggestions": dump_improvement_suggestions(suggestions),
        }

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _get_schedule_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "invite_date_reply" / "schedule.json"

    def _load_schedule(self) -> dict:
        schedule_path = self._get_schedule_path()
        if not schedule_path.exists():
            return {}
        with schedule_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _build_conversation_text(self, messages: list[dict[str, Any]]) -> str:
        return format_conversation_text(
            messages,
            skip_invalid_messages=True,
            skip_empty_messages=True,
            strip_message=True,
        )

    def _build_conversation_facts_text(self, conversation_facts: dict[str, Any]) -> str:
        meeting_area = conversation_facts.get("meeting_area") or {}
        available_time = conversation_facts.get("available_time") or {}

        return dedent(
            f"""
            meeting_area: {meeting_area.get('value', '未取得')}
            meeting_area_source: {meeting_area.get('source_quote', 'なし')}

            available_time: {available_time.get('value', '未取得')}
            available_time_source: {available_time.get('source_quote', 'なし')}
            """
        ).strip()

    def _build_schedule_text(self) -> str:
        if not self.schedule:
            return "スケジュール情報なし"

        lines: list[str] = []
        default_avail = self.schedule.get("default_availability", {})
        scheduled_items = self.schedule.get("scheduled_items", [])

        if scheduled_items:
            lines.append("予定済み:")
            for item in scheduled_items:
                date = item.get("date", "")
                location = item.get("location", "")
                end_time = item.get("end_time", "")
                entry = f"- {date}: {location}で{end_time}まで予定あり"
                lines.append(entry)
            lines.append("")

        lines.append("デフォルト空き時間:")
        holiday_avail = default_avail.get("holiday_afternoon", {})
        if holiday_avail.get("free", False):
            lines.append(f"- 休日（土日）の午後: 基本的に空き（希望度{holiday_avail.get('priority', '-')}）")
        weekday_avail = default_avail.get("weekday_evening", {})
        if weekday_avail.get("free", False):
            lines.append(f"- 平日夕方〜夜: 基本的に空き（希望度{weekday_avail.get('priority', '-')}）")

        return "\n".join(lines) if lines else "スケジュール情報なし"
