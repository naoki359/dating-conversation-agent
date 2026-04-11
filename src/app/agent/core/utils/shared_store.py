from __future__ import annotations

from collections.abc import MutableMapping
from contextvars import ContextVar, Token
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Any, Literal, TypedDict
from textwrap import dedent


MeetingTimingPreference = Literal[
    "できればすぐ会いたい",
    "気が合えば会いたい",
    "会う前に通話したい",
    "メッセージで交流を深めてから",
]

DEFAULT_MEETING_TIMING_PREFERENCE: MeetingTimingPreference = "気が合えば会いたい"


def normalize_meeting_timing_preference(value: Any) -> MeetingTimingPreference:
    if value in (
        "できればすぐ会いたい",
        "気が合えば会いたい",
        "会う前に通話したい",
        "メッセージで交流を深めてから",
    ):
        return value
    return DEFAULT_MEETING_TIMING_PREFERENCE


# ============================================
# Message: 1発言単位
# ============================================
class Message(TypedDict):
    id: str
    timestamp: str
    sender: Literal["self", "other"]
    message: str


# ============================================
# Profile: 相手プロフィール
# ============================================
class Profile(TypedDict):
    name: str
    age: int
    raw_profile_text: str
    profile_summary: str
    meeting_timing_preference: MeetingTimingPreference


# ============================================
# Conversation: 会話履歴
# ============================================
class Conversation(TypedDict):
    messages: list[Message]
    updated_at: str


# ============================================
# SourceData: 読み取り専用データ
# ============================================
class SourceData(TypedDict, total=False):
    """
    外部から与えられる入力データ。
    Nodeは絶対に更新しない（重要）。
    """

    user_id: str
    self_profile: Profile
    profile: Profile
    conversation: Conversation


# ============================================
# デフォルト値
# ============================================
DEFAULT_SELF_PROFILE: Profile = {
    "name": "角田 直樹",
    "age": 32,
    "raw_profile_text": dedent("""
        [basic_info]
        - name: 角田 直樹
        - age: 32

        [interests]
        - アニメ/漫画/ゲーム
        - サウナ/温泉
        - 水族館
          - クラゲが好き
          - シーパラは小学生の遠足で行った。内容は全く覚えていない
        - 猫/犬
        - ポケモン/ソウルシリーズ
        - 居酒屋/日本酒/ビール
        - 焼肉/寿司/肉寿司
        - Vtuber/配信者
        - ミステリー小説
          - どんでん返しがある作品が好き。社会派も結構好き。どちらも好き
          - 最近読んだ作品：「夜明けまでに誰かが」
            - この作者の小説を依然読んだことがあったから、今回も期待して読んだ。少し重めだったけど期待通りの面白さだった。
    """).strip(),
    "profile_summary": ""
}


# ============================================
# ConversationFacts: 会話から抽出した重要情報
# ============================================
class ConversationFact(TypedDict, total=False):
    value: str
    confidence: Literal["low", "medium", "high"]
    source_quote: str


class ConversationFacts(TypedDict, total=False):
    meeting_area: ConversationFact | None
    available_time: ConversationFact | None


# ============================================
# Canvas: プロセス内で更新される成果物
# ============================================
class Canvas(TypedDict, total=False):
    """
    プロセス内で生成・更新される成果物。
    ReactStateの最終アウトプットとして最後にユーザーに返す。
    """

    # -----------------------------------
    # 出力
    # -----------------------------------
    # 返信内容
    generated_reply: str
    # 返信内容を作成した理由
    reply_reasoning: str

    # -----------------------------------
    # 出力に対する評価
    # -----------------------------------
    # プロフィール/性格との合致度スコア(0-100)。
    fit_score: int
    # プロフィール/性格との合致度スコア(0-100)。に対する理由
    reasons: list[str]
    # 返信文のプロフィール適合度に基づく改善提案
    improvement_suggestions: list[dict[str, str]]
    current_action_loop_count: int

    # -----------------------------------
    # 返信品質スコア
    # -----------------------------------
    reply_quality_score: int
    reply_should_regenerate: bool
    reply_quality_reasons: list[str]
    reply_safety_ok: bool
    reply_safety_reasons: list[str]
    reply_rule_score: int
    reply_rule_passed: bool
    reply_rule_reasons: list[str]
    # reply_check_result: dict[str, Any]

    # -----------------------------------
    # 会話から抽出した重要情報
    # -----------------------------------
    conversation_facts: ConversationFacts


@dataclass
class _ExecutionBucket:
    store: SourceData
    canvas: Canvas
    created_at: float
    last_accessed_at: float


DEFAULT_EXECUTION_ID = "default"
MAX_BUCKETS = 100
BUCKET_TTL_SECONDS = 60 * 30

_bucket_lock = Lock()
_buckets: dict[str, _ExecutionBucket] = {}
_current_execution_id: ContextVar[str] = ContextVar(
    "current_execution_id",
    default=DEFAULT_EXECUTION_ID,
)


def _build_initial_store(user_id: str | None = None) -> SourceData:
    store: SourceData = {
        "self_profile": deepcopy(DEFAULT_SELF_PROFILE),
    }
    if user_id:
        store["user_id"] = user_id
    return store


def _cleanup_stale_buckets_unlocked(ttl_seconds: int = BUCKET_TTL_SECONDS) -> int:
    now = time()
    stale_ids = [
        execution_id
        for execution_id, bucket in _buckets.items()
        if (now - bucket.last_accessed_at) > ttl_seconds
    ]

    for execution_id in stale_ids:
        _buckets.pop(execution_id, None)

    return len(stale_ids)


def cleanup_stale_buckets(ttl_seconds: int = BUCKET_TTL_SECONDS) -> int:
    with _bucket_lock:
        return _cleanup_stale_buckets_unlocked(ttl_seconds)


def _ensure_capacity_unlocked() -> None:
    if len(_buckets) < MAX_BUCKETS:
        return

    oldest_id = min(
        _buckets,
        key=lambda key: _buckets[key].last_accessed_at,
    )
    _buckets.pop(oldest_id, None)


def create_execution_bucket(execution_id: str, user_id: str | None = None) -> None:
    now = time()
    with _bucket_lock:
        _cleanup_stale_buckets_unlocked()
        _ensure_capacity_unlocked()
        _buckets[execution_id] = _ExecutionBucket(
            store=_build_initial_store(user_id=user_id),
            canvas={},
            created_at=now,
            last_accessed_at=now,
        )


def destroy_execution_bucket(execution_id: str) -> None:
    with _bucket_lock:
        _buckets.pop(execution_id, None)


def resolve_execution_id(execution_id: str | None = None) -> str:
    if execution_id:
        return execution_id
    return _current_execution_id.get()


def set_current_execution_id(execution_id: str) -> Token:
    return _current_execution_id.set(execution_id)


def reset_current_execution_id(token: Token) -> None:
    _current_execution_id.reset(token)


def _get_bucket(execution_id: str | None = None) -> _ExecutionBucket:
    resolved_execution_id = resolve_execution_id(execution_id)

    with _bucket_lock:
        bucket = _buckets.get(resolved_execution_id)
        if bucket is None:
            now = time()
            _cleanup_stale_buckets_unlocked()
            _ensure_capacity_unlocked()
            bucket = _ExecutionBucket(
                store=_build_initial_store(),
                canvas={},
                created_at=now,
                last_accessed_at=now,
            )
            _buckets[resolved_execution_id] = bucket

        bucket.last_accessed_at = time()
        return bucket


def get_shared_store(execution_id: str | None = None) -> SourceData:
    return _get_bucket(execution_id).store


def get_shared_canvas(execution_id: str | None = None) -> Canvas:
    return _get_bucket(execution_id).canvas


class _ScopedSharedDict(MutableMapping[str, Any]):
    def __init__(self, kind: Literal["store", "canvas"]) -> None:
        self._kind = kind

    def _target(self) -> dict[str, Any]:
        if self._kind == "store":
            return get_shared_store()
        return get_shared_canvas()

    def __getitem__(self, key: str) -> Any:
        return self._target()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._target()[key] = value

    def __delitem__(self, key: str) -> None:
        del self._target()[key]

    def __iter__(self):
        return iter(self._target())

    def __len__(self) -> int:
        return len(self._target())

    def clear(self) -> None:
        self._target().clear()


# 後方互換用。新実装では get_shared_store/get_shared_canvas を優先する。
create_execution_bucket(DEFAULT_EXECUTION_ID)
shared_store: SourceData = _ScopedSharedDict("store")  # type: ignore[assignment]
shared_canvas: Canvas = _ScopedSharedDict("canvas")  # type: ignore[assignment]