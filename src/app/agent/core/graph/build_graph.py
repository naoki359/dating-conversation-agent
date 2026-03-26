from langgraph.graph import END, StateGraph

from app.agent.core.nodes.action.node import ActionNode
from app.agent.core.nodes.decision.node import DecisionNode
from app.agent.core.schemas.state import AgentState
from app.agent.core.tools.generate_reply.tool import GenerateReplyTool
from app.agent.core.tools.registry import ToolRegistry
from app.agent.core.tools.selector import ToolSelector


def build_graph():
    workflow = StateGraph(AgentState)

    decision_node = DecisionNode()

    tool_selector = ToolSelector()
    tool_registry = ToolRegistry(
        tools=[
            GenerateReplyTool(),
        ]
    )
    action_node = ActionNode(
        tool_selector=tool_selector,
        tool_registry=tool_registry,
    )

    workflow.add_node("decision", decision_node.run)
    workflow.add_node("action", action_node.run)

    workflow.set_entry_point("decision")
    workflow.add_edge("decision", "action")
    workflow.add_edge("action", END)

    return workflow.compile()