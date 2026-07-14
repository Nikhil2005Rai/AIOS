from datetime import datetime, timezone

from app.tools.base import ToolResult


class CurrentTimeTool:
    name = "current_time"
    description = "Get the current local date and time."
    parameters = {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }

    def execute(self, arguments: dict) -> ToolResult:
        now = datetime.now(timezone.utc).astimezone()
        return ToolResult(content=f"Current local time is {now:%Y-%m-%d %H:%M:%S %Z}.")
