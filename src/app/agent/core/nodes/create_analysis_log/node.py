from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import override

from app.agent.core.config.settings import Settings
from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.create_analysis_log.schema import CreateAnalysisLogOutputSchema
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store

_JST = timezone(timedelta(hours=9))


class CreateAnalysisLogNode(BaseNode):
    """返信生成完了後に分析用ログを作成するノード。"""

    node_name = "create_analysis_log_node"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(Path(__file__).resolve().parent / "prompt.yaml")

    def execute(self, state: ReactState) -> CreateAnalysisLogOutputSchema:
        execution_id = state.get("execution_id")
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)

        trace_id = state.get("trace_id", "")
        user_id = state.get("user_id", "unknown_user")
        final_reply = str(scoped_canvas.get("generated_reply", "")).strip()
        loop_count = state.get("action_loop_count", 0)
        intent = self._generate_intent(state=state, scoped_canvas=scoped_canvas)

        target_message_id, latest_other_message = self._extract_latest_other_message(scoped_store)

        now = datetime.now(tz=_JST)
        log_data = {
            "analysis_log": {
                "trace_id": trace_id,
                "target_message_id": target_message_id,
                "created_at": now.isoformat(),
                "input": {
                    "latest_other_message": latest_other_message,
                },
                "output": {
                    "final_reply": final_reply,
                },
                "agent": {
                    "intent": intent,
                    "loop_count": loop_count,
                },
            }
        }

        log_path = self._save_log(user_id=user_id, trace_id=trace_id, log_data=log_data, now=now)

        return CreateAnalysisLogOutputSchema(
            node_name=self.node_name,
            success=True,
            summary=f"分析用ログを保存しました: {log_path}",
            reasoning="返信生成完了後に分析用ログを作成しました。",
            thought_process=[
                "State・Canvas から分析データを収集",
                f"分析用ログを {log_path} に保存",
            ],
            trace_id=trace_id,
            log_path=str(log_path),
            final_reply=final_reply,
            intent=intent,
            target_message_id=target_message_id,
        )

    @override
    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        assert isinstance(node_result, CreateAnalysisLogOutputSchema)

        return {
            **state,
            "final_reply": node_result.final_reply,
            "intent": node_result.intent,
            "target_message_id": node_result.target_message_id,
        }

    def _generate_intent(self, state: ReactState, scoped_canvas: dict) -> str:
        """final_reply を主軸に LLM で返信意図を 1〜2 文に生成する。"""
        final_reply = str(scoped_canvas.get("generated_reply", "")).strip()
        reply_reasoning = str(scoped_canvas.get("reply_reasoning", "")).strip()

        if not final_reply:
            return ""

        prompt_value = self.prompt.invoke(
            {
                "final_reply": final_reply,
                "reply_reasoning": reply_reasoning or "（なし）",
            }
        )
        response = self.llm.invoke(prompt_value)
        return str(response.content).strip()

    def _extract_latest_other_message(self, scoped_store: dict) -> tuple[str, str]:
        """会話履歴から最新の相手メッセージIDとメッセージ本文を返す。"""
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", []) if isinstance(conversation, dict) else []
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("sender") == "other":
                return msg.get("id", ""), msg.get("message", "")
        return "", ""

    def _save_log(self, *, user_id: str, trace_id: str, log_data: dict, now: datetime) -> Path:
        """分析用ログを JSON ファイルとして保存する。"""
        log_dir = Path(Settings.AGENT_LOG_DIR) / "analysis" / user_id
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{now.strftime('%Y%m%d%H%M%S')}.json"
        with log_path.open("w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        return log_path
