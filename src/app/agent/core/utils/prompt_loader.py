from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate


def load_prompt_from_yaml(path: str | Path) -> ChatPromptTemplate:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    messages = []
    for message in data["messages"]:
        role = message["role"]
        content = message["content"]
        messages.append((role, content))

    return ChatPromptTemplate.from_messages(messages)