from enum import Enum

from app.agent.core.tools.get_history.tool import GetHistoryTool
from app.agent.core.tools.generate_reply.tool import GenerateReplyTool
from app.agent.core.tools.check_reply_profile_fit.tool import CheckReplyProfileFitTool


class ToolEnum(Enum):
    """
    ツール名とそのメソッドの実態を保持するenum。
    """

    # 値: (メソッド, 説明, 実行完了後の状態テキスト)
    GET_HISTORY = (
        GetHistoryTool().execute,
        "相手のプロフィールと会話履歴を取得する",
        "shared_store に profile と conversation が保存され、履歴参照が可能な状態になる"
    )

    GENERATE_REPLY = (
        GenerateReplyTool().execute,
        "相手のプロフィールと会話履歴を参考に、自然な返信を生成する",
        "返信案が生成され、返信文を次工程で評価・提示できる状態になる"
    )

    CHECK_REPLY_PROFILE_FIT = (
        CheckReplyProfileFitTool().execute,
        "返信文がユーザープロフィール/性格と合っているかを評価する",
        "返信文のプロフィール適合度と改善提案が得られ、最終返信を調整できる状態になる"
    )

    def __init__(self, method, description, completion_state):
        self.method = method
        self.description = description
        self.completion_state = completion_state