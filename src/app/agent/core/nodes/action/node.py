from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.tools.registry import ToolRegistry
from app.agent.core.tools.selector import ToolSelector


class ActionNode(BaseNode):
    """
    実際のツール実行を行うノード。

    - ReactStateを元にツールを選択
    - ツールを実行
    - ReactStateを更新
    - CanvasDataを生成
    """

    node_name = "action_node"

    def __init__(self, tool_selector: ToolSelector, tool_registry: ToolRegistry):
        self.tool_selector = tool_selector
        self.tool_registry = tool_registry

    def execute(self, state: ReactState) -> BaseOutputSchema:
        decided_action = state.get("decided_action", "")

        # ===== ツール選択 =====
        selected_tool_name = self.tool_selector.select(decided_action)
        tool = self.tool_registry.get(selected_tool_name)

        # ===== 実行 =====
        tool_result = tool.execute(state)
        data = tool_result.data

        return BaseOutputSchema(
            node_name=self.node_name,
            success=tool_result.success,
            summary=f"{selected_tool_name} を実行しました。",
            reasoning="Decisionに基づきツールを選択。",
            thought_process=[
                "action確認",
                "tool選択",
                "実行",
                "結果整理",
            ],
            react_updates={
                "selected_tool": selected_tool_name,
                "tool_result": {
                    "tool_name": tool_result.tool_name,
                    "summary": tool_result.summary,
                    "data": data,
                },
                "is_finished": True,
            },
            canvas_updates={
                "generated_reply": data.get("reply_text"),
                "reply_reasoning": data.get("reasoning"),
            },
        )

    def console_render(self, result: BaseOutputSchema):
        print("\n=== ActionNode ===")
        print(result.summary)

        if result.canvas_updates.get("generated_reply"):
            print("Reply:", result.canvas_updates["generated_reply"])