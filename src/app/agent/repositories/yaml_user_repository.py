from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.agent.core.schemas.state import AgentState


def load_agent_state(user_id: str) -> AgentState:
    """
    user_id を受け取り、data/test_user/{user_id}.yaml を読み込んで AgentState を返す。

    例:
        user_id='with_0001'
        -> data/test_user/with_0001.yaml
    """
    file_path = _build_yaml_path(user_id)
    data = _load_yaml(file_path)
    return _build_initial_state(data)


def _build_yaml_path(user_id: str) -> Path:
    """
    project_root/data/test_user/{user_id}.yaml の絶対パスを組み立てる。
    """
    project_root = Path(__file__).resolve().parents[4]
    return project_root / "data" / "test_user" / f"{user_id}.yaml"


def _load_yaml(file_path: Path) -> dict[str, Any]:
    """
    YAML ファイルを読み込み、dict として返す。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping object.")

    return data


def _build_initial_state(data: dict[str, Any]) -> AgentState:
    """
    YAML から読み込んだ dict を AgentState に正規化する。
    ReAct 実行前の初期値もここで設定する。
    """
    profile_raw = data.get("profile", {})
    conversation_raw = data.get("conversation", {})

    if not isinstance(profile_raw, dict):
        raise ValueError("profile must be a mapping object.")

    if not isinstance(conversation_raw, dict):
        raise ValueError("conversation must be a mapping object.")

    messages_raw = conversation_raw.get("messages", [])
    if messages_raw is None:
        messages_raw = []
    if not isinstance(messages_raw, list):
        raise ValueError("conversation.messages must be a list.")

    normalized_messages: list[dict[str, Any]] = []
    for i, msg in enumerate(messages_raw, start=1):
        if not isinstance(msg, dict):
            raise ValueError(
                f"conversation.messages[{i - 1}] must be a mapping object."
            )

        normalized_messages.append(
            {
                "id": msg.get("id", f"m{i:03d}"),
                "timestamp": str(msg.get("timestamp", "")),
                "sender": msg.get("sender", ""),
                "message": msg.get("message", ""),
            }
        )

    state: AgentState = {
        # ===== 元データ =====
        "user_id": data.get("user_id", ""),
        "profile": {
            "name": profile_raw.get("name", ""),
            "age": profile_raw.get("age", 0),
            "raw_profile_text": profile_raw.get("raw_profile_text", ""),
            "profile_summary": profile_raw.get("profile_summary", ""),
        },
        "conversation": {
            "messages": normalized_messages,
            "updated_at": str(conversation_raw.get("updated_at", "")),
        },
        # ===== ReAct 初期値 =====
        "current_thought": "",
        "required_tasks": [],
        "decided_action": "",
        "action_reasoning": "",
        "generated_reply": "",
        "reply_reasoning": "",
        "is_finished": False,
    }

    return state