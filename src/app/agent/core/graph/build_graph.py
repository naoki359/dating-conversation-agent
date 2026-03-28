from langgraph.graph import END, StateGraph

from app.agent.core.nodes.decision.node import DecisionNode
from app.agent.core.schemas.state import ReactState


def build_graph():
    workflow = StateGraph(ReactState)

    decision_node = DecisionNode()

    workflow.add_node("decision", decision_node.run)

    workflow.set_entry_point("decision")
    workflow.add_edge("decision", END)

    return workflow.compile()