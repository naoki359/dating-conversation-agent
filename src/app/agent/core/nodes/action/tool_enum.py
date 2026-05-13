from enum import Enum

from app.agent.core.tools.analyze_conversation_triggers.tool import AnalyzeConversationTriggersTool
from app.agent.core.tools.decide_conversation_topic.tool import DecideConversationTopicTool
from app.agent.core.tools.invite_date_reply.tool import InviteDateReplyTool
from app.agent.core.tools.generate_first_message.tool import GenerateFirstMessageTool
from app.agent.core.tools.get_history_and_facts.tool import GetHistoryAndFactsTool
from app.agent.core.tools.generate_reply.tool import GenerateReplyTool
from app.agent.core.tools.evaluate_invite_reply.tool import EvaluateInviteReplyTool
from app.agent.core.tools.evaluate_reply.tool import EvaluateReplyTool
from app.agent.core.tools.refine_reply.tool import RefineReplyTool


class ToolEnum(Enum):
    """
    ツール名とそのメソッドの実態を保持するenum。
    """

    # 値: (メソッド, 説明, 重要事項, 実行完了後の状態テキスト)
    GET_HISTORY_AND_FACTS = (
        GetHistoryAndFactsTool().execute,
        "相手のプロフィールと会話履歴を取得し、住んでいる地域などの重要な情報を抽出する",
        "必ず一番初めに実行すること",
        "shared_store に profile と conversation が保存され、canvas に conversation_facts が展開された状態になる"
    )

    DECIDE_CONVERSATION_TOPIC = (
        DecideConversationTopicTool().execute,
        "会話履歴を分析し、話題を継続するべきか切り替えるべきかを判定する。会話が単調になるのを防ぐ。",
        "GENERATE_REPLY の前に必ず実行すること",
        "canvas に conversation_topic_strategy が保存され、返信生成ノードが話題方針を参照できる状態になる"
    )

    GENERATE_REPLY = (
        GenerateReplyTool().execute,
        "相手のプロフィールと会話履歴を参考に、自然な返信を生成する。一回だけ実行することを想定している",
        "デートへの打診の場合には使用しないこと。今回の実行で GENERATE_REPLY を使用した場合は INVITE_DATE_REPLY を使わないこと。返信案を生成したあとは、同じ生成系ツールを続けずに EVALUATE_REPLY を優先すること。",
        "返信案が生成され、返信文を次工程で評価・提示できる状態になる"
    )

    INVITE_DATE_REPLY = (
        InviteDateReplyTool().execute,
        "重要情報と店舗候補を使って、デート場所と日時を含む誘い文を生成する。一回だけ実行することを想定している",
        "会話の継続を目的とした返信には使用しないこと。今回の実行で INVITE_DATE_REPLY を使用した場合は GENERATE_REPLY を使わないこと。返信案を生成したあとは、同じ生成系ツールを続けずに EVALUATE_INVITE_REPLY を優先すること。",
        "デート打診用の返信文が生成され、必要に応じて通話の代替案も提示できる状態になる"
    )

    GENERATE_FIRST_MESSAGE = (
        GenerateFirstMessageTool().execute,
        "会話履歴がない相手に対して、プロフィールを基に自然で具体性のある初回メッセージを生成する",
        "",
        "初回送信用のメッセージ案が生成されました"
    )

    REFINE_REPLY = (
        RefineReplyTool().execute,
        "指摘事項を反映して既存の返信案を修正する",
        "",
        "返信案が改善され、再評価または最終出力に進める状態になる"
    )

    EVALUATE_REPLY = (
        EvaluateReplyTool().execute,
        "生成済み返信の安全性、返信ルール、品質、プロフィール適合度を一括評価する",
        "GENERATE_REPLY または INVITE_DATE_REPLY の直後に優先して使用すること。未評価の生成済み返信がある場合は、他の生成系ツールより先に使用すること。",
        "安全性、返信ルール、返信品質、プロフィール適合度、改善提案が得られ、改善判断ができる状態になる"
    )

    EVALUATE_INVITE_REPLY = (
        EvaluateInviteReplyTool().execute,
        "デートへ誘う返信の安全性とデート誘い専用ルールを一括評価する",
        "INVITE_DATE_REPLY の直後に使用すること。EVALUATE_REPLY とは別物であり、通常の返信評価には使用しないこと。",
        "安全性、デート誘いルール適合度、改善提案が得られ、再生成判断ができる状態になる"
    )

    def __init__(self, method, description, important_notes, completion_state):
        self.method = method
        self.description = description
        self.important_notes = important_notes
        self.completion_state = completion_state