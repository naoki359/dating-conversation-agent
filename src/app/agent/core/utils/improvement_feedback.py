from typing import Any, Literal

from pydantic import BaseModel, Field


FeedbackPriority = Literal["high", "medium", "low"]


class ImprovementSuggestionSchema(BaseModel):
    message: str = Field(
        ...,
        description="修正すべき指摘内容。",
    )

    priority: FeedbackPriority = Field(
        ...,
        description="指摘の優先度。high, medium, low のいずれか。",
    )

    alternative_text: str = Field(
        ...,
        description="指摘事項に対しての代替となるテキスト。",
    )



_PRIORITY_RANK: dict[FeedbackPriority, int] = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def append_improvement_suggestions(
    scoped_canvas: dict[str, Any],
    suggestions: list[Any],
    *,
    default_priority: FeedbackPriority = "medium",
) -> None:
    existing_raw = scoped_canvas.get("improvement_suggestions", [])
    merged = merge_improvement_suggestions(
        existing_raw,
        suggestions,
        default_priority=default_priority,
    )
    scoped_canvas["improvement_suggestions"] = dump_improvement_suggestions(merged)


def merge_improvement_suggestions(
    existing: list[Any],
    new_items: list[Any],
    *,
    default_priority: FeedbackPriority = "medium",
) -> list[ImprovementSuggestionSchema]:
    merged_by_message: dict[str, ImprovementSuggestionSchema] = {}

    for raw_item in [*existing, *new_items]:
        suggestion = coerce_improvement_suggestion(
            raw_item,
            default_priority=default_priority,
        )
        if suggestion is None:
            continue

        existing_suggestion = merged_by_message.get(suggestion.message)
        if existing_suggestion is None:
            merged_by_message[suggestion.message] = suggestion
            continue

        if _PRIORITY_RANK[suggestion.priority] > _PRIORITY_RANK[existing_suggestion.priority]:
            merged_by_message[suggestion.message] = suggestion

    return list(merged_by_message.values())


def dump_improvement_suggestions(
    suggestions: list[ImprovementSuggestionSchema],
) -> list[dict[str, str]]:
    return [suggestion.model_dump() for suggestion in suggestions]


def coerce_improvement_suggestion(
    raw_item: Any,
    *,
    default_priority: FeedbackPriority = "medium",
) -> ImprovementSuggestionSchema | None:
    if isinstance(raw_item, ImprovementSuggestionSchema):
        return raw_item

    if isinstance(raw_item, str):
        message = raw_item.strip()
        if not message:
            return None
        return ImprovementSuggestionSchema(
            message=message,
            priority=default_priority,
            alternative_text=message,
        )

    if isinstance(raw_item, dict):
        message = str(raw_item.get("message", "")).strip()
        if not message:
            return None
        priority = _normalize_priority(raw_item.get("priority"), default_priority)
        alternative_text = _normalize_alternative_text(
            raw_item.get("alternative_text"),
            message,
        )
        return ImprovementSuggestionSchema(
            message=message,
            priority=priority,
            alternative_text=alternative_text,
        )

    return None


def _normalize_priority(
    raw_priority: Any,
    default_priority: FeedbackPriority = "medium",
) -> FeedbackPriority:
    if raw_priority in _PRIORITY_RANK:
        return raw_priority
    return default_priority


def _normalize_alternative_text(raw_alternative_text: Any, fallback_message: str) -> str:
    alternative_text = str(raw_alternative_text or "").strip()
    if alternative_text:
        return alternative_text
    return fallback_message
