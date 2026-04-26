from __future__ import annotations

from typing import override

from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.finalize_reply.schema import FinalizeReplyOutputSchema
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.utils.shared_store import get_shared_canvas


class FinalizeReplyNode(BaseNode):
    """ReActループ終了後に最終返信をStateに保存するノード。"""

    node_name = "finalize_reply_node"

    def execute(self, state: ReactState) -> FinalizeReplyOutputSchema:
        execution_id = state.get("execution_id")
        scoped_canvas = get_shared_canvas(execution_id)
        final_reply = str(scoped_canvas.get("generated_reply", "")).strip()

        return FinalizeReplyOutputSchema(
            node_name=self.node_name,
            success=True,
            summary=f"最終返信をStateに保存しました。",
            reasoning="ReActループが生成したgenerated_replyをStateのfinal_replyフィールドに格納しました。",
            thought_process=["canvasからgenerated_replyを取得", "StateのfinalReplyに格納"],
            final_reply=final_reply,
        )

    @override
    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        assert isinstance(node_result, FinalizeReplyOutputSchema)

        return {
            **state,
            "final_reply": node_result.final_reply,
        }
