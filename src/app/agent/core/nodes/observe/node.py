from __future__ import annotations

from pathlib import Path
from typing import override

from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.observe.schema import ObserveOutputSchema
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas


class ObserveNode(BaseNode):
    """
    各ステップの終わりに状態を監視し、fit_score・reply_quality_score・
    reply_should_regenerate と action_loop_count に基づいて
    ループを継続するか終了するかを判定するノード。
    """

    node_name = "observe_node"

    # パラメータ
    FIT_SCORE_THRESHOLD = 90  # fit_score がこの値以上なら継続を検討
    REPLY_QUALITY_SCORE_THRESHOLD = 90  # 返信品質スコアがこの値以上なら継続を検討
    MAX_ACTION_LOOP_COUNT = 10  # 最大ループ回数

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, state: ReactState) -> ObserveOutputSchema:
        """
        fit_score・reply_quality_score・reply_should_regenerate と action_loop_count を確認し、判定を行う。
        """
        execution_id = state.get("execution_id")
        scoped_canvas = get_shared_canvas(execution_id)
        fit_score = int(scoped_canvas.get("fit_score", 0) or 0)
        reply_quality_score = int(scoped_canvas.get("reply_quality_score", 0) or 0)
        reply_should_regenerate = bool(scoped_canvas.get("reply_should_regenerate", False))
        action_loop_count = state.get("action_loop_count", 0)

        # if not state.get("observation_flg", False):
        #     return ObserveOutputSchema(
        #         node_name=self.node_name,
        #         success=True,
        #         summary="評価未実施のため、ループを継続します。",
        #         fit_score=None,
        #         action_loop_count=action_loop_count,
        #         decision="continue" if action_loop_count <= self.MAX_ACTION_LOOP_COUNT else "end",
        #         reasoning="評価がまだ行われていない為、終了条件を満たしていない",
        #     )

        decision, reasoning = self._make_decision(
            fit_score,
            reply_quality_score,
            reply_should_regenerate,
            action_loop_count,
        )

        current_loop_history = self._extract_current_loop_history(state)
        summary = self._generate_summary_with_llm(
            action_loop_count=action_loop_count,
            current_loop_history=current_loop_history,
            fit_score=fit_score,
            reply_quality_score=reply_quality_score,
            reply_should_regenerate=reply_should_regenerate,
            decision=decision,
            reasoning=reasoning,
        )

        result = ObserveOutputSchema(
            node_name=self.node_name,
            success=True,
            summary=summary,
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
            "decided_action": "",
            "selected_tool": "",
        }

        return updated_state
    
    @override
    def canvas_update(self, node_result: BaseOutputSchema) -> None:
        if not isinstance(node_result, ObserveOutputSchema):
            return

        print("\n=== ObserveNode ===")
        print(f"fit_score: {node_result.fit_score}")
        print(f"action_loop_count: {node_result.action_loop_count}")
        print(f"decision: {node_result.decision}")
        print(f"reasoning: {node_result.reasoning}")

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _extract_current_loop_history(self, state: ReactState) -> list[dict]:
        """historyから今ループ分（直近のobserve_node以降のエントリ）を抽出する。"""
        history = state.get("history", [])
        current_loop: list[dict] = []
        for item in reversed(history):
            if isinstance(item, dict):
                node_name = item.get("node_name", "")
                summary = item.get("summary", "")
            else:
                node_name = getattr(item, "node_name", "")
                summary = getattr(item, "summary", "")

            if node_name == "observe_node":
                break

            current_loop.insert(0, {"node_name": node_name, "summary": summary})

        return current_loop

    def _generate_summary_with_llm(
        self,
        action_loop_count: int,
        current_loop_history: list[dict],
        fit_score: int,
        reply_quality_score: int,
        reply_should_regenerate: bool,
        decision: str,
        reasoning: str,
    ) -> str:
        """LLMを使って構造化されたサマリを生成する。"""
        history_text = "\n".join(
            f"- [{item['node_name']}]: {item['summary']}"
            for item in current_loop_history
        ) or "（なし）"

        prompt_value = self.prompt.invoke(
            {
                "action_loop_count": action_loop_count,
                "history_text": history_text,
                "fit_score": fit_score,
                "reply_quality_score": reply_quality_score,
                "reply_should_regenerate": reply_should_regenerate,
                "decision": decision,
                "reasoning": reasoning,
            }
        )

        response = self.llm.invoke(prompt_value)
        return str(response.content)

    def _make_decision(
        self,
        fit_score: int,
        reply_quality_score: int,
        reply_should_regenerate: bool,
        action_loop_count: int,
    ) -> tuple[str, str]:
        """
        fit_score・reply_quality_score・reply_should_regenerate と action_loop_count に基づいて、
        継続するか終了するかを判定する。

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

        if reply_should_regenerate:
            reason = (
                "安全性・返信ルール・返信品質・プロフィール適合度のいずれかで"
                "再生成が必要と判定されたため、ループを継続します。"
            )
            return "continue", reason

        # fit_score と reply_quality_score の両方が閾値以上の場合は終了
        if (
            fit_score >= self.FIT_SCORE_THRESHOLD
            and reply_quality_score >= self.REPLY_QUALITY_SCORE_THRESHOLD
        ):
            reason = (
                f"fit_score（{fit_score}）が閾値（{self.FIT_SCORE_THRESHOLD}）以上、"
                f"reply_quality_score（{reply_quality_score}）が閾値"
                f"（{self.REPLY_QUALITY_SCORE_THRESHOLD}）以上であるため、"
                "品質基準を満たしています。ループを終了します。"
            )
            return "end", reason

        # それ以外は継続
        reason = (
            f"fit_score（{fit_score}）または reply_quality_score（{reply_quality_score}）"
            f"が閾値（fit: {self.FIT_SCORE_THRESHOLD}, quality: {self.REPLY_QUALITY_SCORE_THRESHOLD}）"
            "を満たしておらず"
            f"で、ループ回数（{action_loop_count}）が上限（{self.MAX_ACTION_LOOP_COUNT}）"
            "に達していないため、品質向上のため継続します。"
        )
        return "continue", reason
