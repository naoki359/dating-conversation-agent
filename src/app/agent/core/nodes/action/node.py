from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.nodes.action.tool_enum import ToolEnum
from app.agent.core.tools.generate_reply.schema import GenerateReplyResultSchema
from app.agent.core.utils.shared_store import shared_canvas


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

        if not tool_result.success:
            return BaseOutputSchema(
                node_name=self.node_name,
                success=False,
                summary=f"{selected_tool.name} の実行に失敗しました。原因：{tool_result.summary}",
                reasoning="ツールの実行に失敗。",
                thought_process=[f"{selected_tool.name} 実行", F"実行失敗。原因: {tool_result.summary}"],
            )

        # ツールの実行結果を基にCanvasDataを生成
        # ツールの実行結果がsuccess且つ、戻り値がGenerateReplyResultSchemaの形式であれば、生成された返信文をCanvasに含める
        if tool_result.success and selected_tool == ToolEnum.GENERATE_REPLY:
            try:
                # tool_result.dataをGenerateReplyResultSchemaに変換
                reply_data = GenerateReplyResultSchema(**tool_result.data)
                # プロセス内でアクセス可能なshared_canvasに保存
                shared_canvas["generated_reply"] = reply_data.reply_text
                shared_canvas["reply_reasoning"] = reply_data.reasoning
            except Exception as e:
                # GenerateReplyResultSchemaへの変換に失敗した場合
                return BaseOutputSchema(
                    node_name=self.node_name,
                    success=False,
                    summary=f"返信データの処理に失敗しました: {str(e)}",
                    reasoning="GenerateReplyResultSchemaへの変換でエラーが発生。",
                    thought_process=["ツール実行", "結果の解析失敗"],
                )
            
        # 実行したツールがCHECK_REPLY_PROFILE_FITまたはSCORE_REPLY_QUALITYであれば、観測フラグを立てる
        if selected_tool in [ToolEnum.CHECK_REPLY_PROFILE_FIT, ToolEnum.SCORE_REPLY_QUALITY] and tool_result.success:
            state["observation_flg"] = True
        else:
            state["observation_flg"] = False

        return BaseOutputSchema(
            node_name=self.node_name,
            success=tool_result.success,
            summary=f"{selected_tool.name} を実行しました。{selected_tool.completion_state}" if tool_result.success else f"{selected_tool.name} の実行に失敗しました。状況を確認したのち再度実行してください。",
            reasoning="Decisionに基づきツールを選択。",
            thought_process=[]
        )

    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        action_loop_count = state.get("action_loop_count", 0) + 1
        decided_action = state.get("decided_action", "")

        # selected_toolをツール名から取得
        selected_tool_name = decided_action.upper().replace(" ", "_")

        return {
            **state,
            "action_loop_count": action_loop_count,
            "selected_tool": selected_tool_name,
            "tool_result": node_result.model_dump() if node_result else {},
        }

    def console_render(self, result: BaseOutputSchema):
        print("\n=== ActionNode ===")
        print(result.summary)