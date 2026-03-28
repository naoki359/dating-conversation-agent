from enum import Enum

from app.agent.core.tools.get_history.tool import GetHistoryTool


class ToolEnum(Enum):
    """
    ツール名とそのメソッドの実態を保持するenum。
    """

    # 値: (メソッド, 説明, パラメータ辞書)
    GET_HISTORY = (
        GetHistoryTool().execute,
        "相手のプロフィールと会話履歴を取得する",
        {"user_id": "str - ユーザーのID"}
    )

    # 仮定: CHECK_REPLY = (CheckReplyTool().execute, "返信をチェックする", {"reply_text": "str - チェックする返信テキスト"})
    # 仮定: GENERATE_REPLY = (GenerateReplyTool().execute, "返信を生成する", {"context": "dict - 生成に必要なコンテキスト"})

    def __init__(self, method, description, params):
        self.method = method
        self.description = description
        self.params = params