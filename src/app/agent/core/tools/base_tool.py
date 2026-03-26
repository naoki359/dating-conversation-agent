from abc import ABC, abstractmethod

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.schemas.state import AgentState


class BaseTool(ABC):
    name: str
    description: str = ""

    @abstractmethod
    def execute(self, state: AgentState) -> BaseToolResult:
        """state を受け取り、共通形式の BaseToolResult を返す。"""
        raise NotImplementedError