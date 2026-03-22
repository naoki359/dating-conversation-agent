from langgraph.graph import END, StateGraph

from app.agent.core.nodes.decision.decision_node import DecisionNode
from app.agent.core.schemas.state import AgentState


def build_graph():
    workflow = StateGraph(AgentState)

    decision_node = DecisionNode()

    workflow.add_node("decision", decision_node.run)

    workflow.set_entry_point("decision")
    workflow.add_edge("decision", END)

    return workflow.compile()

# テスト用
# def build_graph():
#     print("build_graph() called")

#     class DummyGraph:
#         def invoke(self, request):
#             print("DummyGraph.invoke() called")
#             return {
#                 "generated_reply": "ダミー返信です（build_graph経由）",
#                 "reply_reasoning": "graph.invoke() が呼ばれたことを確認",
#             }

#     return DummyGraph()