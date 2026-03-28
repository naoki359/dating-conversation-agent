from typing import Any, Literal, TypedDict


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
    profile: Profile
    conversation: Conversation


# ============================================
# ReactState: ReActの作業状態
# ============================================
class ReactState(TypedDict, total=False):
    """
    LangGraphでノード間を流れる状態。

    役割:
    - 思考（Thought）
    - タスク洗い出し（Task Discovery）
    - 意思決定（Decision）
    - 行動結果（Action）

    ※ 成果物（返信など）は持たない
    """

    # ===== Thought =====
    current_thought: str

    # ===== Task Discovery =====
    required_tasks: list[str]

    # ===== Decision =====
    decided_action: str
    action_reasoning: str

    # ===== Action =====
    selected_tool: str
    tool_result: dict[str, Any]

    # ===== Control =====
    is_finished: bool

    # ===== Trace =====
    trace_id: str


# ============================================
# CanvasData: 成果物
# ============================================
class CanvasData(TypedDict, total=False):
    """
    最終的にユーザーに見せる成果物。
    1ループの最後にのみ更新される。

    ReactStateと重複させない（重要）。
    """

    generated_reply: str
    reply_reasoning: str