from __future__ import annotations

from textwrap import dedent
from typing import Any, Mapping

from app.agent.core.utils.shared_store import DEFAULT_MEETING_TIMING_PREFERENCE


def format_profile_text(
    profile: Mapping[str, Any] | None,
    *,
    empty_text: str = "プロフィール情報はありません。",
    basic_info_header: str | None = "[基本情報]",
    include_meeting_timing_preference: bool = True,
    use_default_meeting_timing_preference: bool = True,
    summary_header: str = "[プロフィール要約]",
    include_raw_profile_text: bool = False,
    raw_profile_header: str = "[プロフィール原文]",
    summary_fallback: str = "",
    raw_profile_fallback: str = "",
) -> str:
    if not profile:
        return empty_text

    name = str(profile.get("name", ""))
    age = str(profile.get("age", ""))
    profile_summary = str(profile.get("profile_summary", ""))
    raw_profile_text = str(profile.get("raw_profile_text", "")).strip()
    meeting_timing_preference = str(profile.get("meeting_timing_preference") or "")

    if use_default_meeting_timing_preference and not meeting_timing_preference:
        meeting_timing_preference = DEFAULT_MEETING_TIMING_PREFERENCE

    lines: list[str] = []
    if basic_info_header:
        lines.append(basic_info_header)
    lines.append(f"名前: {name}")
    lines.append(f"年齢: {age}")

    if include_meeting_timing_preference:
        lines.append(f"出会うまでの希望: {meeting_timing_preference}")

    lines.extend(
        [
            "",
            summary_header,
            profile_summary or summary_fallback,
        ]
    )

    if include_raw_profile_text:
        lines.extend(
            [
                "",
                raw_profile_header,
                raw_profile_text or raw_profile_fallback,
            ]
        )

    return "\n".join(lines).strip()


def format_self_profile_text(profile: Mapping[str, Any] | None) -> str:
    return format_profile_text(
        profile,
        empty_text="自分のプロフィール情報はありません。",
        include_meeting_timing_preference=False,
        include_raw_profile_text=True,
        summary_fallback="要約はありません。",
        raw_profile_fallback="原文はありません。",
    )


def format_conversation_text(
    messages: list[dict[str, Any]] | list[dict],
    *,
    empty_text: str = "会話履歴はありません。",
    line_prefix: str = "",
    use_sender_labels: bool = True,
    skip_invalid_messages: bool = False,
    skip_empty_messages: bool = False,
    strip_message: bool = False,
) -> str:
    if not messages:
        return empty_text

    lines: list[str] = []
    for msg in messages:
        if skip_invalid_messages and not isinstance(msg, dict):
            continue

        sender = str(msg.get("sender", ""))
        message = str(msg.get("message", ""))
        if strip_message:
            message = message.strip()
        if skip_empty_messages and not message:
            continue

        sender_text = "相手" if use_sender_labels and sender == "other" else sender
        if use_sender_labels and sender != "other":
            sender_text = "自分"
        lines.append(f"{line_prefix}{sender_text}: {message}")

    return "\n".join(lines) or empty_text


def format_conversation_with_metadata(
    conversation: Mapping[str, Any] | None,
    *,
    empty_text: str = "会話履歴はありません。",
) -> str:
    conversation = conversation or {}
    messages = conversation.get("messages", [])
    if not messages:
        return empty_text

    lines: list[str] = []
    for msg in messages:
        message_id = msg.get("id", "")
        timestamp = msg.get("timestamp", "")
        sender = msg.get("sender", "")
        message = str(msg.get("message", ""))

        lines.append(
            dedent(
                f"""
                - id: {message_id}
                  timestamp: {timestamp}
                  sender: {sender}
                  message:
                {_indent_block(message, 4)}
                """
            ).rstrip()
        )

    updated_at = conversation.get("updated_at", "")
    history_text = "\n".join(lines)

    return dedent(
        f"""
        [会話更新日時]
        {updated_at}

        [会話履歴]
        {history_text}
        """
    ).strip()


def format_conversation_with_updated_at(
    conversation: Mapping[str, Any] | None,
    *,
    empty_text: str = "会話履歴はありません。",
) -> str:
    conversation = conversation or {}
    messages = conversation.get("messages", [])
    if not messages:
        return empty_text

    lines = format_conversation_text(
        messages,
        empty_text=empty_text,
        line_prefix="- ",
        use_sender_labels=False,
    ).splitlines()
    lines.append(f"- updated_at: {conversation.get('updated_at', '')}")
    return "\n".join(lines)


def _indent_block(text: str, spaces: int) -> str:
    indent = " " * spaces
    lines = text.splitlines() or [text]
    return "\n".join(f"{indent}{line}" for line in lines)
