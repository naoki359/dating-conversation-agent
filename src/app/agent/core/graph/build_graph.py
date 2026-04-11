from langgraph.graph import END, StateGraph

from app.agent.core.nodes.action.node import ActionNode
from app.agent.core.nodes.decision.node import DecisionNode
from app.agent.core.nodes.final_reply_rewrite.node import FinalReplyRewriteNode
from app.agent.core.nodes.observe.node import ObserveNode
from app.agent.core.schemas.state import ReactState

# def _route_after_action(state: ReactState) -> str:
#     observation_flg = state.get("observation_flg", False)
#     if observation_flg:
#         return "observe"
#     return "decision"

def _route_after_observe(state: ReactState) -> str:
    is_finished = state.get("is_finished", False)
    if is_finished:
        return "final_reply_rewrite"
    return "decision"

# def build_graph():
#     workflow = StateGraph(ReactState)

#     decision_node = DecisionNode()
#     action_node = ActionNode()

#     workflow.add_node("decision", decision_node.run)
#     workflow.add_node("action", action_node.run)

#     workflow.set_entry_point("decision")
#     workflow.add_edge("decision", "action")
#     workflow.add_edge("action", END)

#     return workflow.compile()


def build_graph():
    workflow = StateGraph(ReactState)

    decision_node = DecisionNode()
    action_node = ActionNode()
    observe_node = ObserveNode()
    final_reply_rewrite_node = FinalReplyRewriteNode()

    workflow.add_node("decision", decision_node.run)
    workflow.add_node("action", action_node.run)
    workflow.add_node("observe", observe_node.run)
    workflow.add_node("final_reply_rewrite", final_reply_rewrite_node.run)

    workflow.set_entry_point("decision")
    workflow.add_edge("decision", "action")
    # workflow.add_conditional_edges(
    #     "action",
    #     _route_after_action,
    #     {
    #         "observe": "observe",
    #         "decision": "decision",
    #     },
    # )
    workflow.add_edge("action", "observe")
    workflow.add_conditional_edges(
        "observe",
        _route_after_observe,
        {
            "decision": "decision",
            "final_reply_rewrite": "final_reply_rewrite",
        },
    )
    workflow.add_edge("final_reply_rewrite", END)

    return workflow.compile()