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
                react_updates={"is_finished": True},
                canvas_updates={},
            )

        # ツールを実行
        tool_result = tool_method(state)
        data = tool_result.data

        return BaseOutputSchema(
            node_name=self.node_name,
            success=tool_result.success,
            summary=f"{selected_tool.name} を実行しました。",
            reasoning="Decisionに基づきツールを選択。",
            thought_process=[
                "action確認",
                "tool選択",
                "実行",
                "結果整理",
            ],
            react_updates={
                "selected_tool": selected_tool.name,
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