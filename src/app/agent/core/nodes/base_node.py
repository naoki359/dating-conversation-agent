from abc import ABC, abstractmethod

from app.agent.core.schemas.state import AgentState
from app.agent.core.schemas.base_output_schema import BaseOutputSchema


class BaseNode(ABC):
    node_name = "base_node"

    def run(self, state: AgentState) -> AgentState:
        result = self.execute(state)

        if not isinstance(result, BaseOutputSchema):
            raise TypeError(
                f"{self.node_name}.execute() must return BaseOutputSchema, "
                f"got {type(result).__name__}"
            )

        self._log(result)

        updated_state = {
            **state,
            **result.model_dump(
                exclude={"node_name", "success", "log_message"}, exclude_none=True
            ),
        }

        return updated_state

    @abstractmethod
    def execute(self, state: AgentState) -> BaseOutputSchema:
        raise NotImplementedError
    
    def _log(self, result: BaseOutputSchema) -> None:
      print(f"[{result.node_name}] success={result.success}")

      if result.summary:
          print(f"[{result.node_name}] summary={result.summary}")

      if result.reasoning:
          print(f"[{result.node_name}] reasoning={result.reasoning}")

      if result.thought_process:
          print(f"[{result.node_name}] thought_process:")
          for i, step in enumerate(result.thought_process, start=1):
              print(f"  {i}. {step}")



