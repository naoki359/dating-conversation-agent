from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.nodes.action.tool_enum import ToolEnum


class ActionNode(BaseNode):
    """
    実際のツール実行を行うノード。

    - ReactStateを元にツールを選択
    - ツールを実行
    - ReactStateを更新
    - CanvasDataを生成
    """

    node_name = "action_node"

    def execute(self, state: ReactState) -> BaseOutputSchema:
        decided_action = state.get("decided_action", "")

        # ToolEnumからツールを選択
        try:
            selected_tool = ToolEnum[decided_action.upper().replace(" ", "_")]
            tool_method = selected_tool.method
        except KeyError:
            # ツールが見つからない場合のエラーハンドリング
            return BaseOutputSchema(
                node_name=self.node_name,
                success=False,
                summary=f"指定されたツール '{decided_action}' が見つかりません。",
                reasoning="decided_actionが無効です。",
                thought_process=["ツール選択", "ツールが見つからない"],
            )

        # ツールを実行
        tool_result = tool_method()

        return BaseOutputSchema(
            node_name=self.node_name,
            success=tool_result.success,
            summary=f"{selected_tool.name} を実行しました。",
            reasoning="Decisionに基づきツールを選択。",
            thought_process=[]
        )

    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        action_loop_count = state.get("action_loop_count", 0) + 1

        return {
            **state,
            "action_loop_count": action_loop_count,
        }

    def console_render(self, result: BaseOutputSchema):
        print("\n=== ActionNode ===")
        print(result.summary)