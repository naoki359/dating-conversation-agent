from app.agent.core.nodes.action.schema import ActionOutputSchema
from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.schemas.state import AgentState
from app.agent.core.tools.registry import ToolRegistry
from app.agent.core.tools.selector import ToolSelector


class ActionNode(BaseNode):
    node_name = "action_node"

    def __init__(
        self,
        tool_selector: ToolSelector,
        tool_registry: ToolRegistry,
    ) -> None:
        self.tool_selector = tool_selector
        self.tool_registry = tool_registry

    def execute(self, state: AgentState) -> ActionOutputSchema:
        decided_action = state.get("decided_action", "")

        selected_tool_name = self.tool_selector.select(decided_action)
        tool = self.tool_registry.get(selected_tool_name)
        tool_result = tool.execute(state)

        tool_result_data = tool_result.data
        generated_reply = tool_result_data.get("reply_text")
        reply_reasoning = tool_result_data.get("reasoning")

        return ActionOutputSchema(
            node_name=self.node_name,
            success=tool_result.success,
            summary=f"{selected_tool_name} を実行しました。",
            reasoning=(
                f"decided_action をもとに {selected_tool_name} を選択し、"
                "ツール実行結果を取得しました。"
            ),
            thought_process=[
                "decided_action を確認した",
                "実行するツールを選択した",
                "選択したツールを実行した",
                "ツール結果を Action ノードの出力に整理した",
            ],
            selected_tool=selected_tool_name,
            tool_result=tool_result_data,
            generated_reply=generated_reply,
            reply_reasoning=reply_reasoning,
            is_finished=True,
        )

    def console_render(self, result: ActionOutputSchema) -> None:
        print("\n=== ActionNode ===")
        print(f"tool: {result.selected_tool}")

        if result.generated_reply:
            print(f"reply: {result.generated_reply}")