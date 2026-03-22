from typing import Literal, NotRequired, TypedDict


class Message(TypedDict):
    id: str
    timestamp: str
    sender: Literal["self", "partner"]
    message: str


class AgentState(TypedDict):
    profile_summary: NotRequired[str]
    latest_context_summary: NotRequired[str]
    messages: NotRequired[list[Message]]

    decided_action: NotRequired[str]
    action_reasoning: NotRequired[str]
    reply_focus_points: NotRequired[list[str]]