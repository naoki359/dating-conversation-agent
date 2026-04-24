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
        - 旅行(引きこもりだからそんなに好みではない。でも綺麗な景色は好き)
          - 沖縄
            - こうりじまに行った。レンタカーを借りて島を一周した。橋を渡るときの景色がすごくきれいだった。
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


class ClassifiedConversationTerm(TypedDict, total=False):
    expression: str
    normalized_expression: str
    speaker: Literal["self", "other", "both"]
    occurrence_count: int
    source_quotes: list[str]


class ConversationWordClassification(TypedDict, total=False):
    topic_terms: list[ClassifiedConversationTerm]
    reaction_terms: list[ClassifiedConversationTerm]
    function_terms: list[ClassifiedConversationTerm]


class TriggerCandidate(TypedDict, total=False):
    keyword: str
    normalized_keyword: str
    source: str
    source_quote: str
    category: str
    match_level: str
    match_reason: str
    related_self_profile_keywords: list[str]
    needs_research: bool
    priority_score: int


ReplyCandidateThemeId = Literal[
    "question_continue",
    "question_shift",
    "topic_continue",
    "topic_shift",
]


class ImprovementSuggestion(TypedDict, total=False):
    message: str
    priority: Literal["low", "medium", "high"]


class CandidateSafetyCheck(TypedDict, total=False):
    safety_ok: bool
    should_regenerate: bool
    reasons: list[str]
    improvement_suggestions: list[ImprovementSuggestion]
    detected_risks: list[str]


class CandidateRuleCheck(TypedDict, total=False):
    passed: bool
    should_regenerate: bool
    rule_score: int
    reasons: list[str]
    improvement_suggestions: list[ImprovementSuggestion]
    violations: list[str]


class ReplyCandidate(TypedDict, total=False):
    candidate_id: str
    theme_id: ReplyCandidateThemeId
    theme_label: str
    reply_text: str
    reasoning: str
    safety_check: CandidateSafetyCheck
    rule_check: CandidateRuleCheck
    final_score: int
    rank: int
    selected: bool


class ReplySelectionSummary(TypedDict, total=False):
    selected_candidate_id: str
    selected_theme_id: ReplyCandidateThemeId
    selection_reason: str
    evaluated_candidate_count: int


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
    # 複数の返信候補
    reply_candidates: list[ReplyCandidate]
    # 最終採用した返信候補ID
    selected_reply_candidate_id: str
    # 候補選抜の理由
    reply_selection_reason: str
    # 候補選抜の要約
    reply_selection_summary: ReplySelectionSummary

    # -----------------------------------
    # 出力に対する評価
    # -----------------------------------
    # プロフィール/性格との合致度スコア(0-100)。
    fit_score: int
    # プロフィール/性格との合致度スコア(0-100)。に対する理由
    reasons: list[str]
    # 最終採用候補に対する改善提案
    improvement_suggestions: list[ImprovementSuggestion]
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
    conversation_word_classification: ConversationWordClassification
    trigger_candidates: list[TriggerCandidate]
    selected_trigger_keyword: str
    trigger_analysis_summary: list[str]


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


# 古いバケットをクリーンアップする関数。
# 指定された TTL（有効期限）を超えてアクセスされていないバケットを削除します。
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


# バケットの容量を確保する関数。
# バケットの数が最大値を超えた場合、最も古いバケットを削除します。
def _ensure_capacity_unlocked() -> None:
    if len(_buckets) < MAX_BUCKETS:
        return

    oldest_id = min(
        _buckets,
        key=lambda key: _buckets[key].last_accessed_at,
    )
    _buckets.pop(oldest_id, None)


# 実行バケットを作成する関数
# execution_idごとに状態（storeやcanvasなど）を管理する箱を作る
def create_execution_bucket(execution_id: str, user_id: str | None = None) -> None:
    now = time()  # 現在時刻を取得（作成時間・アクセス時間に使う）

    # ロックをかけてこの中の処理を同時に1つのスレッドだけが実行できるようにする
    # → データの競合（壊れること）を防ぐため
    with _bucket_lock:
        # 古くなった不要なバケットを削除する（メモリ節約・リーク防止）
        _cleanup_stale_buckets_unlocked()
        # バケット数が上限を超えないように調整する（容量管理）
        _ensure_capacity_unlocked()
        # 新しいバケットを作成して登録する
        _buckets[execution_id] = _ExecutionBucket(
            # 初期状態のデータを作成（ユーザー情報などを元に）
            store=_build_initial_store(user_id=user_id),
            # 出力結果などを保持する領域（最初は空）
            canvas={},
            # 作成時刻
            created_at=now,
            # 最後にアクセスされた時刻（初回は作成時と同じ）
            last_accessed_at=now,
        )

# バケットを削除する関数
def destroy_execution_bucket(execution_id: str) -> None:
    # ロックをかけて安全に操作する（同時アクセス防止）
    with _bucket_lock:
        # 指定されたexecution_idのバケットを削除する
        # 存在しなくてもエラーにならないようにNoneを指定している
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

# 実行IDを基に共有キャンバスを取得する関数
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