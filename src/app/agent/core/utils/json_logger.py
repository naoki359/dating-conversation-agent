import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agent.core.config.settings import Settings
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class JsonLogger:
    def __init__(self) -> None:
        self.enabled = Settings.AGENT_LOG_ENABLED
        self.base_dir = Path(Settings.AGENT_LOG_DIR)
        self.conversation_tail_count = Settings.AGENT_LOG_CONVERSATION_TAIL_COUNT

    def generate_trace_id(self) -> str:
        return str(uuid.uuid4())

    def save(
        self,
        *,
        user_id: str,
        trace_id: str,
        node_name: str,
        state_before: dict[str, Any],
        output: dict[str, Any],
        state_after: dict[str, Any],
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if not self.enabled:
            return

        now = datetime.now()
        log_dir = self.base_dir / user_id / now.strftime("%Y%m%d")
        log_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{trace_id}_{now.strftime('%H%M%S_%f')}_{node_name}.json"
        log_path = log_dir / filename

        common_keys = {
            "node_name",
            "success",
            "summary",
            "reasoning",
            "thought_process",
        }

        node_data = {
            key: value
            for key, value in output.items()
            if key not in common_keys
        }

        execution_id = self._extract_execution_id(
            state_before=state_before,
            state_after=state_after,
        )

        payload = {
            "meta": {
                "timestamp": now.isoformat(),
                "user_id": user_id,
                "trace_id": trace_id,
                "node_name": node_name,
                "success": output.get("success"),
            },
            "input": {
                "profile_summary": self._extract_profile_summary(state_before),
                "conversation_tail": self._extract_conversation_tail(
                    state_before,
                    limit=self.conversation_tail_count,
                ),
                "state_summary": self._extract_state_summary(state_before),
            },
            "base_data": {
                "summary": output.get("summary"),
                "reasoning": output.get("reasoning"),
                "thought_process": output.get("thought_process"),
            },
            "node_data": node_data,
            "shared_store": {
                "canvas": dict(get_shared_canvas(execution_id)),
                "sourceData": dict(get_shared_store(execution_id)),
            },
            "error": None
            if not error_type
            else {
                "error_type": error_type,
                "error_message": error_message,
            },
        }

        with log_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    def _extract_execution_id(
        self,
        *,
        state_before: dict[str, Any],
        state_after: dict[str, Any],
    ) -> str | None:
        execution_id = state_after.get("execution_id")
        if execution_id is None:
            execution_id = state_before.get("execution_id")

        if execution_id is None:
            return None

        return str(execution_id)

    def _extract_profile_summary(self, state: dict[str, Any]) -> str | None:
        profile = state.get("profile") or {}

        if isinstance(profile, dict):
            return (
                profile.get("profile_summary")
                or profile.get("summary")
                or profile.get("raw_profile_text")
            )

        return None

    def _extract_conversation_tail(
        self,
        state: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        conversation = state.get("conversation") or {}

        if isinstance(conversation, dict):
            messages = conversation.get("messages") or []
        elif isinstance(conversation, list):
            messages = conversation
        else:
            messages = []

        tail = messages[-limit:]

        result = []
        for msg in tail:
            if not isinstance(msg, dict):
                continue

            result.append(
                {
                    "id": msg.get("id"),
                    "sender": msg.get("sender"),
                    "message": msg.get("message"),
                }
            )

        return result

    def _extract_state_summary(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "current_thought": state.get("current_thought"),
            "required_tasks": state.get("required_tasks"),
            "decided_action": state.get("decided_action"),
            "generated_reply": state.get("generated_reply"),
            "is_finished": state.get("is_finished"),
        }


json_logger = JsonLogger()