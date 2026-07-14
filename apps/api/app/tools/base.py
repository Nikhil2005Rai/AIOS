from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ToolResult:
    content: str


class Tool(Protocol):
    name: str
    description: str
    parameters: dict

    def execute(self, arguments: dict) -> ToolResult:
        raise NotImplementedError
