from typing import Dict, Any, TypedDict, Literal


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

# プロセス内でデータを永続化するための共有ストア
shared_store: SourceData = {}