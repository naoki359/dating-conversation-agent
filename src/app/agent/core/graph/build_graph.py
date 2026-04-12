from langgraph.graph import END, StateGraph

from app.agent.core.config.settings import Settings
from app.agent.core.nodes.action.node import ActionNode
from app.agent.core.nodes.decision.node import DecisionNode
from app.agent.core.nodes.final_reply_rewrite.node import FinalReplyRewriteNode
from app.agent.core.nodes.fixed_pipeline.node import FixedToolNode
from app.agent.core.nodes.observe.node import ObserveNode
from app.agent.core.schemas.state import ReactState
from app.agent.core.tools.evaluate_reply_candidates.tool import EvaluateReplyCandidatesTool
from app.agent.core.tools.generate_reply_candidates.tool import GenerateReplyCandidatesTool
from app.agent.core.tools.get_history_and_facts.tool import GetHistoryAndFactsTool

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


def _route_after_fixed_step(state: ReactState) -> str:
    if state.get("is_finished", False):
        return "end"
    return "next"

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


def build_react_graph():
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


def build_fixed_graph():
    workflow = StateGraph(ReactState)

    get_history_and_facts_node = FixedToolNode(
        node_name="fixed_get_history_and_facts_node",
        tool=GetHistoryAndFactsTool(),
    )
    generate_reply_candidates_node = FixedToolNode(
        node_name="fixed_generate_reply_candidates_node",
        tool=GenerateReplyCandidatesTool(),
    )
    evaluate_reply_candidates_node = FixedToolNode(
        node_name="fixed_evaluate_reply_candidates_node",
        tool=EvaluateReplyCandidatesTool(),
    )
    final_reply_rewrite_node = FinalReplyRewriteNode()

    workflow.add_node("fixed_get_history_and_facts", get_history_and_facts_node.run)
    workflow.add_node("fixed_generate_reply_candidates", generate_reply_candidates_node.run)
    workflow.add_node("fixed_evaluate_reply_candidates", evaluate_reply_candidates_node.run)
    workflow.add_node("final_reply_rewrite", final_reply_rewrite_node.run)

    workflow.set_entry_point("fixed_get_history_and_facts")
    workflow.add_conditional_edges(
        "fixed_get_history_and_facts",
        _route_after_fixed_step,
        {
            "next": "fixed_generate_reply_candidates",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "fixed_generate_reply_candidates",
        _route_after_fixed_step,
        {
            "next": "fixed_evaluate_reply_candidates",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "fixed_evaluate_reply_candidates",
        _route_after_fixed_step,
        {
            "next": "final_reply_rewrite",
            "end": END,
        },
    )
    workflow.add_edge("final_reply_rewrite", END)

    return workflow.compile()


def build_graph():
    if Settings.AGENT_PIPELINE_MODE == "react":
        return build_react_graph()
    return build_fixed_graph()