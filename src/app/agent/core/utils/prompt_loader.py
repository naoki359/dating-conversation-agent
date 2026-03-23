from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate


def load_prompt_from_yaml(yaml_path: Path) -> ChatPromptTemplate:
    """
    YAML 形式の prompt 定義を読み込み、
    ChatPromptTemplate に変換する。
    """
    if not yaml_path.exists():
        raise FileNotFoundError(f"prompt.yaml が見つかりません: {yaml_path}")

    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("prompt yaml のルートは mapping である必要があります。")

    raw_messages = data.get("messages")
    if not isinstance(raw_messages, list):
        raise ValueError("prompt yaml には messages: list が必要です。")

    messages = []
    for i, m in enumerate(raw_messages):
        if not isinstance(m, dict):
            raise ValueError(f"messages[{i}] は mapping である必要があります。")

        role = m.get("role")
        content = m.get("content")

        if not role or not content:
            raise ValueError(f"messages[{i}] には role と content が必要です。")

        messages.append((role, content))

    return ChatPromptTemplate.from_messages(messages)