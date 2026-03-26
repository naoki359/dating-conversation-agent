from app.agent.core.tools.base_tool import BaseTool


class ToolRegistry:
    def __init__(self, tools: list[BaseTool]):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, tool_name: str) -> BaseTool:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")
        return tool

    def list_tool_names(self) -> list[str]:
        return list(self._tools.keys())