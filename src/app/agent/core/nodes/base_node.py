from abc import ABC, abstractmethod
import time

from app.agent.core.schemas.state import ReactState, ReactState
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.utils.shared_store import shared_store
from app.agent.core.utils.json_logger import json_logger


class BaseNode(ABC):
    node_name = "base_node"

    def run(self, state: ReactState) -> ReactState:
        # trace_idがなければ生成しておく
        if "trace_id" not in state:
            state["trace_id"] = json_logger.generate_trace_id()

        # StateのDeepコピーを作成しておく（ログ用）
        state_before = state.copy()

        try:
            # ノードを実行
            result = self.execute(state)

            # ノードの実行結果が想定通りの型かチェックを行う
            if not isinstance(result, BaseOutputSchema):
                raise TypeError(
                    f"{self.node_name}.execute() must return BaseOutputSchema, "
                    f"got {type(result).__name__}"
                )
            
            # Stateの更新を行う
            state_after = self.react_update(node_result=result, state=state)

            # Canvasの更新を行う
            self.canvas_update(result)
            
            # ログの出力を行う（UI用）
            self.console_render(result)

            # ログの出力を行う（永続化用）
            self._log(
                state_before=state_before,
                result=dict(result),
                state_after=state_after
            )

            return state_after

        except Exception as e:

            error_result = {
                "node_name": self.node_name,
                "success": False,
                "summary": f"{self.node_name} で例外が発生しました。",
                "reasoning": "ノード実行中に例外が発生したため、正常終了できませんでした。",
                "thought_process": [f"Exception: {type(e).__name__}: {str(e)}"],
            }

            error_state = {
                **state,
                "is_finished": True,
            }

            self._log(
                state_before=state_before,
                result=dict(error_result),
                state_after=error_state,
                error_type=type(e).__name__,
                error_message=str(e),
            )

            raise

    @abstractmethod
    def execute(self, state: ReactState) -> BaseOutputSchema:
        raise NotImplementedError
    
    def react_update(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        # 履歴の更新（共通）
        if "history" not in state:
            state["history"] = []
        state["history"].append({field: getattr(node_result, field) for field in BaseOutputSchema.model_fields.keys()})
        
        # 子供固有のState更新
        return self.update_state(node_result, state)
    
    def update_state(self, node_result: BaseOutputSchema, state: ReactState) -> ReactState:
        """子供クラスでオーバーライドして、ノード固有のState更新を行う"""
        return state

    def canvas_update(self, node_result: BaseOutputSchema) -> None:
        pass

    def console_render(self, result: BaseOutputSchema) -> None:
        pass

    def _log(
        self,
        state_before: ReactState,
        result: dict,
        state_after: ReactState,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        user_id = shared_store.get("user_id")
        trace_id = state_before["trace_id"]

        json_logger.save(
            user_id=user_id,
            trace_id=trace_id,
            node_name=self.node_name,
            state_before=state_before,
            output=result,
            state_after=state_after,
            error_type=error_type,
            error_message=error_message,
        )