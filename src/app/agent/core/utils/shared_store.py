from typing import Dict, Any, TypedDict, Literal
from textwrap import dedent


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

        [personality]
        - 落ち着いている
        - やや人見知り
        - 聞き役になることが多い
                               
        [communication_style]
        - 礼儀正しい
        - 丁寧な言葉遣い
        - 柔らかい
        - テンション高すぎない
        - 基本的には相手の話を聞く
                               
        [message_length]
        - 短すぎず、長すぎない（2～4文）
                               
        [emoji_usage]
        - 1つの返信に対して2つまで
                               
        [interests]
        - アニメ/漫画/ゲーム
        - サウナ
        - 旅行
    """).strip(),
    "profile_summary": ""
}


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
    improvement_suggestions: list[str]

    # -----------------------------------
    # 返信品質スコア
    # -----------------------------------
    reply_quality_score: int
    reply_should_regenerate: bool
    reply_quality_reasons: list[str]
    # reply_check_result: dict[str, Any]


# プロセス内でデータを永続化するための共有ストア（読み取り専用）
shared_store: SourceData = {
    "self_profile": DEFAULT_SELF_PROFILE
}

# プロセス内で更新される成果物を管理するCanvas
shared_canvas: Canvas = {}