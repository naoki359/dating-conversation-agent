from __future__ import annotations

from typing import override

from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.observe.schema import ObserveOutputSchema
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.utils.shared_store import shared_canvas


class ObserveNode(BaseNode):
    """
    各ステップの終わりに状態を監視し、fit_score と action_loop_count に基づいて
    ループを継続するか終了するかを判定するノード。
    """

    node_name = "observe_node"

    # パラメータ
    FIT_SCORE_THRESHOLD = 80  # fit_score がこの値以上なら継続を検討
    MAX_ACTION_LOOP_COUNT = 10  # 最大ループ回数

    def execute(self, state: ReactState) -> ObserveOutputSchema:
        """
        fit_score と action_loop_count を確認し、判定を行う。
        """
        fit_score = shared_canvas.get("fit_score")
        action_loop_count = state.get("action_loop_count", 0)

        if not state.get("observation_flg", False):
            return ObserveOutputSchema(
                node_name=self.node_name,
                success=True,
                summary="評価未実施のため、ループを継続します。",
                fit_score=None,
                action_loop_count=action_loop_count,
                decision="continue",
                reasoning="評価がまだ行われていない為、終了条件を満たしていない",
            )

        decision, reasoning = self._make_decision(fit_score, action_loop_count)

        result = ObserveOutputSchema(
            node_name=self.node_name,
            success=True,
            summary=f"fit_score={fit_score}, action_loop_count={action_loop_count} に基づいて '{decision}' と判定。指摘事項を基に返信の再作成を行うこと",
            fit_score=fit_score,
            action_loop_count=action_loop_count,
            decision=decision,
            reasoning=reasoning,
        )

        return result

    @override
    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        """判定結果に基づいて state を更新する。"""
        assert isinstance(node_result, ObserveOutputSchema)

        is_finished = node_result.decision == "end"

        updated_state = {
            **state,
            "is_finished": is_finished,
        }

        return updated_state
    
    @override
    def canvas_update(self, node_result: BaseOutputSchema) -> None:
        print("\n=== ObserveNode ===")
        print(f"fit_score: {shared_canvas.get('fit_score', 0)}")
        print(f"action_loop_count: {node_result.action_loop_count}")
        print(f"decision: {node_result.decision}")
        print(f"reasoning: {node_result.reasoning}")

    def _make_decision(self, fit_score: int, action_loop_count: int) -> tuple[str, str]:
        """
        fit_score と action_loop_count に基づいて、継続するか終了するかを判定する。

        Returns:
            tuple[str, str]: ("continue" or "end", reasoning)
        """

        # 最大ループ回数に達した場合は終了
        if action_loop_count >= self.MAX_ACTION_LOOP_COUNT:
            reason = (
                f"最大ループ回数（{self.MAX_ACTION_LOOP_COUNT}回）に達した"
                "ため、ループを終了します。"
            )
            return "end", reason

        # fit_score が閾値以上の場合は終了
        if fit_score >= self.FIT_SCORE_THRESHOLD:
            reason = (
                f"fit_score（{fit_score}）が閾値（{self.FIT_SCORE_THRESHOLD}）以上"
                "であるため、品質基準を満たしています。ループを終了します。"
            )
            return "end", reason

        # それ以外は継続
        reason = (
            f"fit_score（{fit_score}）が閾値（{self.FIT_SCORE_THRESHOLD}）未満"
            f"で、ループ回数（{action_loop_count}）が上限（{self.MAX_ACTION_LOOP_COUNT}）"
            "に達していないため、品質向上のため継続します。"
        )
        return "continue", reason
