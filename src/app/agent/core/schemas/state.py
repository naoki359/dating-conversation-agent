from typing import Literal, NotRequired, TypedDict


# ===== Message =====
class Message(TypedDict):
    id: str  # 例: "m001"
    timestamp: str  # 例: "2026-03-21T19:00:00+09:00"
    sender: Literal["self", "other"]  # 自分 or 相手
    message: str  # 実際の発言内容


# ===== Profile =====
class Profile(TypedDict):
    name: str  # 例: "さやか"
    age: int  # 例: 28

    raw_profile_text: str
    # 例:
    # "はじめまして☺️\nプロフィール見ていただきありがとうございます！..."

    profile_summary: str
    # 例:
    # "映画好き（特に韓国映画・サスペンス）。カフェ巡り。落ち着いた性格。"


# ===== Conversation =====
class Conversation(TypedDict):
    messages: list[Message]

    updated_at: str
    # 例: "2026-03-21T19:10:00+09:00"


# ===== AgentState =====
class AgentState(TypedDict):
    # ===== 元データ（YAMLから読み込む情報） =====

    user_id: NotRequired[str]
    # 例: "with_0001"

    profile: NotRequired[Profile]
    # YAMLの profile をそのまま格納

    conversation: NotRequired[Conversation]
    # YAMLの conversation をそのまま格納


    # ===== ReAct: Thought =====

    current_thought: NotRequired[str]
    # 例:
    # "相手は韓国映画・サスペンスが好きと明言している。
    # 会話はまだ初期段階なので、興味に寄せて話題を広げるのが良い。"


    # ===== ReAct: Task Discovery =====

    required_tasks: NotRequired[list[str]]
    # 例:
    # [
    #   "相手の興味を整理する",
    #   "次の返信方針を決める",
    #   "会話を広げる返信を生成する"
    # ]
    #
    # 現在の状況に対して必要だと考えられるタスク一覧。
    # 今すぐ実行しない候補も含めて広めに保持する。


    # ===== ReAct: Decision =====

    decided_action: NotRequired[str]
    # 例:
    # "会話を広げる返信を生成する"
    #
    # required_tasks の中から、今回このステップで実際に選んだタスク。

    action_reasoning: NotRequired[str]
    # 例:
    # "相手の興味に寄せた質問を返すことで、
    # 会話を継続しやすくなるため。"


    # ===== Action結果 =====

    generated_reply: NotRequired[str]
    # 例:
    # "韓国映画いいですね！最近観た中で特に面白かった作品ってありますか？"

    reply_reasoning: NotRequired[str]
    # 例:
    # "相手の興味（韓国映画・サスペンス）に寄せ、
    # 具体的な作品名を引き出す質問で会話を広げる構成にした。"


    # ===== 制御 =====

    is_finished: NotRequired[bool]
    # 例:
    # True（1ループで終了）