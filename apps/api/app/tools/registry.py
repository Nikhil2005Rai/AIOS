from app.providers.base import ToolSchema
from app.tools.base import Tool
from app.tools.current_time import CurrentTimeTool


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[ToolSchema]:
        return [
            ToolSchema(name=tool.name, description=tool.description, parameters=tool.parameters)
            for tool in self.all()
        ]


def build_tool_registry() -> ToolRegistry:
    return ToolRegistry(tools=[CurrentTimeTool()])
