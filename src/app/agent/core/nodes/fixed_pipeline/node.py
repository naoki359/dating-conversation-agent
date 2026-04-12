from typing import Any

from app.agent.core.nodes.action.schema import ActionOutputSchema
from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState


class FixedToolNode(BaseNode):
    """固定パイプラインで1つのツールを実行するノード。"""

    def __init__(self, node_name: str, tool: Any) -> None:
        self.node_name = node_name
        self.tool = tool

    def execute(self, state: ReactState) -> ActionOutputSchema:
        execution_id = state.get("execution_id")
        tool_name = getattr(self.tool, "name", self.node_name)

        if not execution_id:
            return ActionOutputSchema(
                node_name=self.node_name,
                success=False,
                summary="execution_id が見つからないため処理を継続できません。",
                reasoning="state に execution_id が存在しないため、固定パイプラインを実行できません。",
                thought_process=["execution_id 確認", "不足のため中断"],
                selected_tool=tool_name,
                tool_result={},
                is_finished=True,
            )

        tool_result = self.tool.execute(execution_id)
        dumped_tool_result = (
            tool_result.model_dump() if hasattr(tool_result, "model_dump") else tool_result
        )

        if not tool_result.success:
            return ActionOutputSchema(
                node_name=self.node_name,
                success=False,
                summary=f"{tool_name} の実行に失敗しました。原因: {tool_result.summary}",
                reasoning="固定パイプライン内のツール実行に失敗したため終了します。",
                thought_process=[f"{tool_name} 実行", f"実行失敗。原因: {tool_result.summary}"],
                selected_tool=tool_name,
                tool_result=dumped_tool_result,
                is_finished=True,
            )

        return ActionOutputSchema(
            node_name=self.node_name,
            success=True,
            summary=f"{tool_name} を実行しました。",
            reasoning="固定パイプラインに定義された順序でツールを実行しました。",
            thought_process=[f"{tool_name} を正常実行"],
            selected_tool=tool_name,
            tool_result=dumped_tool_result,
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
            "is_finished": node_result.is_finished,
        }

    def console_render(self, result: BaseOutputSchema) -> None:
        if not isinstance(result, ActionOutputSchema):
            return

        print(f"\n=== {self.node_name} ===")
        print(result.summary)
