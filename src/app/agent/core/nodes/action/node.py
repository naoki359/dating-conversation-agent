from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.action.schema import ActionOutputSchema
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.nodes.action.tool_enum import ToolEnum
from app.agent.core.utils.shared_store import get_shared_canvas


class ActionNode(BaseNode):
    """
    実際のツール実行を行うノード。

    - ReactStateを元にツールを選択
    - ツールを実行
    - ReactStateを更新
    - CanvasDataを生成
    """

    node_name = "action_node"

    def execute(self, state: ReactState) -> ActionOutputSchema:
        decided_action = state.get("decided_action", "")
        execution_id = state.get("execution_id")

        if not execution_id:
            return ActionOutputSchema(
                node_name=self.node_name,
                success=False,
                summary="execution_id が見つからないため処理を継続できません。",
                reasoning="stateにexecution_idが存在しない。",
                thought_process=["execution_id確認", "不足のため中断"],
                selected_tool="",
                tool_result={},
                is_finished=False,
            )

        # ToolEnumからツールを選択
        try:
            selected_tool = ToolEnum[decided_action.upper().replace(" ", "_")]
            tool_method = selected_tool.method
        except KeyError:
            # ツールが見つからない場合のエラーハンドリング
            return ActionOutputSchema(
                node_name=self.node_name,
                success=False,
                summary=f"指定されたツール '{decided_action}' が見つかりません。",
                reasoning="decided_actionが無効です。",
                thought_process=["ツール選択", "ツールが見つからない"],
                selected_tool=decided_action.upper().replace(" ", "_"),
                tool_result={},
                is_finished=False,
            )

        scoped_canvas = get_shared_canvas(execution_id)
        scoped_canvas["current_action_loop_count"] = int(state.get("action_loop_count", 0) or 0)

        # ツールを実行
        tool_result = tool_method(execution_id)

        if not tool_result.success:
            return ActionOutputSchema(
                node_name=self.node_name,
                success=False,
                summary=f"{selected_tool.name} の実行に失敗しました。原因：{tool_result.summary}",
                reasoning="ツールの実行に失敗。",
                thought_process=[f"{selected_tool.name} 実行", F"実行失敗。原因: {tool_result.summary}"],
                selected_tool=selected_tool.name,
                tool_result=tool_result.model_dump() if hasattr(tool_result, "model_dump") else tool_result,
                is_finished=False,
            )
            
        # 実行したツールがEVALUATE_REPLYであれば、観測フラグを立てる
        if selected_tool == ToolEnum.EVALUATE_REPLY and tool_result.success:
            state["observation_flg"] = True
        else:
            state["observation_flg"] = False

        return ActionOutputSchema(
            node_name=self.node_name,
            success=tool_result.success,
            summary=f"{selected_tool.name} を実行しました。{selected_tool.completion_state}" if tool_result.success else f"{selected_tool.name} の実行に失敗しました。状況を確認したのち再度実行してください。",
            reasoning="Decisionに基づきツールを選択。",
            thought_process=[],
            selected_tool=selected_tool.name,
            tool_result=tool_result.model_dump() if hasattr(tool_result, "model_dump") else tool_result,
            is_finished=False,
        )

    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        assert isinstance(node_result, ActionOutputSchema)

        action_loop_count = state.get("action_loop_count", 0) + 1

        return {
            **state,
            "action_loop_count": action_loop_count,
            "selected_tool": node_result.selected_tool,
            "tool_result": node_result.tool_result,
        }

    def console_render(self, result: BaseOutputSchema):
        print("\n=== ActionNode ===")
        print(result.summary)