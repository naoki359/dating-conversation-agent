from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.decision.output_schema import DecisionOutputSchema
from app.agent.core.schemas.state import AgentState


class DecisionNode(BaseNode):
    node_name = "decision_node"

    def execute(self, state: AgentState) -> DecisionOutputSchema:
        messages = state.get("messages", [])
        latest_context_summary = state.get("latest_context_summary", "")

        if not messages:
            return DecisionOutputSchema(
                node_name=self.node_name,
                success=True,
                log_message="会話履歴がないため wait を選択しました。",
                decided_action="wait",
                action_reasoning="会話履歴が存在しないため、返信生成はまだ行えない。",
                reply_focus_points=[],
            )

        if not latest_context_summary:
            return DecisionOutputSchema(
                node_name=self.node_name,
                success=True,
                log_message="コンテキスト要約がないため summarize_context を選択しました。",
                decided_action="summarize_context",
                action_reasoning="最新会話の要約が未作成のため、先に文脈整理を行う。",
                reply_focus_points=[],
            )

        return DecisionOutputSchema(
            node_name=self.node_name,
            success=True,
            log_message="返信生成アクションを選択しました。",
            decided_action="generate_reply",
            action_reasoning=(
                "会話履歴と最新コンテキスト要約が存在するため、"
                "次のアクションとして返信生成を行う。"
            ),
            reply_focus_points=[
                "自然な温度感で返す",
                "会話を続けやすくする",
                "必要に応じて軽い質問を含める",
            ],
        )