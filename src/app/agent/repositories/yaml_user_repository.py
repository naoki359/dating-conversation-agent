from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.agent.core.config.settings import Settings
from app.agent.core.schemas.state import ReactState
from app.agent.core.utils.shared_store import normalize_meeting_timing_preference


def load_agent_state(user_id: str) -> ReactState:
    """
    user_id を受け取り、data/{data_source}/{user_id}.yaml を読み込んで ReactState を返す。

    例:
        user_id='with_0001'
        -> data/test_user/with_0001.yaml  (DATA_SOURCE=test)
        -> data/user/with_0001.yaml       (DATA_SOURCE=prod)
    """
    file_path = _build_yaml_path(user_id)
    data = _load_yaml(file_path)
    return _build_initial_state(data)


def _build_yaml_path(user_id: str) -> Path:
    """
    Settings.get_data_dir() / {user_id}.yaml の絶対パスを組み立てる。
    """
    return Settings.get_data_dir() / f"{user_id}.yaml"


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


def _build_initial_state(data: dict[str, Any]) -> ReactState:
    """
    YAML から読み込んだ dict を ReactState に正規化する。
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

    state: ReactState = {
        # ===== 元データ =====
        "user_id": data.get("user_id", ""),
        "profile": {
            "name": profile_raw.get("name", ""),
            "age": profile_raw.get("age", 0),
            "raw_profile_text": profile_raw.get("raw_profile_text", ""),
            "profile_summary": profile_raw.get("profile_summary", ""),
            "meeting_timing_preference": normalize_meeting_timing_preference(
                profile_raw.get("meeting_timing_preference")
            ),
        },
        "conversation": {
            "messages": normalized_messages,
            "updated_at": str(conversation_raw.get("updated_at", "")),
        },
        # ===== ReAct 初期値 =====
        "current_thought": "",
        "decided_action": "",
        "generated_reply": "",
        "reply_reasoning": "",
        "is_finished": False,
    }

    return state