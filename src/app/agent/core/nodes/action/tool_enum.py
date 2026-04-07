from enum import Enum

from app.agent.core.tools.get_history_and_facts.tool import GetHistoryAndFactsTool
from app.agent.core.tools.generate_reply.tool import GenerateReplyTool
from app.agent.core.tools.evaluate_reply.tool import EvaluateReplyTool
from app.agent.core.tools.refine_reply.tool import RefineReplyTool


class ToolEnum(Enum):
    """
    ツール名とそのメソッドの実態を保持するenum。
    """

    # 値: (メソッド, 説明, 実行完了後の状態テキスト)
    GET_HISTORY_AND_FACTS = (
        GetHistoryAndFactsTool().execute,
        "相手のプロフィールと会話履歴を取得し、住んでいる地域などの重要な情報を抽出する",
        "shared_store に profile と conversation が保存され、canvas に conversation_facts が展開された状態になる"
    )

    GENERATE_REPLY = (
        GenerateReplyTool().execute,
        "相手のプロフィールと会話履歴を参考に、自然な返信を生成する",
        "返信案が生成され、返信文を次工程で評価・提示できる状態になる"
    )

    REFINE_REPLY = (
        RefineReplyTool().execute,
        "指摘事項を反映して既存の返信案を修正する",
        "返信案が改善され、再評価または最終出力に進める状態になる"
    )

    EVALUATE_REPLY = (
        EvaluateReplyTool().execute,
        "生成済み返信の品質・安全性とプロフィール適合度を一括評価する",
        "返信品質スコアとプロフィール適合度、改善提案が得られ、改善判断ができる状態になる"
    )

    def __init__(self, method, description, completion_state):
        self.method = method
        self.description = description
        self.completion_state = completion_state