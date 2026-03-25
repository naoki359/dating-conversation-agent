from abc import ABC, abstractmethod
import time

from app.agent.core.schemas.state import AgentState
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.utils.json_logger import json_logger


class BaseNode(ABC):
    node_name = "base_node"

    def run(self, state: AgentState) -> AgentState:
        working_state = dict(state)

        if "trace_id" not in working_state:
            working_state["trace_id"] = json_logger.generate_trace_id()

        start = time.perf_counter()

        try:
            result = self.execute(working_state)

            if not isinstance(result, BaseOutputSchema):
                raise TypeError(
                    f"{self.node_name}.execute() must return BaseOutputSchema, "
                    f"got {type(result).__name__}"
                )

            output_dict = result.model_dump(
                exclude={"node_name", "log_message"},
                exclude_none=True,
            )

            updated_state = {
                **working_state,
                **{
                    key: value
                    for key, value in output_dict.items()
                    if key not in {"success"}
                },
            }

            execution_ms = int((time.perf_counter() - start) * 1000)

            self._log(
                state_before=working_state,
                result=output_dict,
                state_after=updated_state,
                execution_ms=execution_ms,
            )

            self.console_render(result)

            return updated_state

        except Exception as e:
            execution_ms = int((time.perf_counter() - start) * 1000)

            error_result = {
                "node_name": self.node_name,
                "success": False,
                "summary": f"{self.node_name} で例外が発生しました。",
                "reasoning": "ノード実行中に例外が発生したため、正常終了できませんでした。",
                "thought_process": [f"Exception: {type(e).__name__}: {str(e)}"],
            }

            error_state = {
                **working_state,
                "is_finished": True,
            }

            self._log(
                state_before=working_state,
                result=error_result,
                state_after=error_state,
                execution_ms=execution_ms,
                error_type=type(e).__name__,
                error_message=str(e),
            )

            raise

    @abstractmethod
    def execute(self, state: AgentState) -> BaseOutputSchema:
        raise NotImplementedError

    def console_render(self, result: BaseOutputSchema) -> None:
        pass

    def _log(
        self,
        state_before: AgentState,
        result: dict,
        state_after: AgentState,
        execution_ms: int,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        user_id = state_before.get("user_id", "unknown_user")
        trace_id = state_before["trace_id"]

        json_logger.save(
            user_id=user_id,
            trace_id=trace_id,
            node_name=self.node_name,
            state_before=state_before,
            output=result,
            state_after=state_after,
            execution_ms=execution_ms,
            error_type=error_type,
            error_message=error_message,
        )