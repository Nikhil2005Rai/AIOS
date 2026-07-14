import json

import httpx

from app.providers.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall, ToolSchema


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                content=(
                    "LLM_API_KEY is not configured. Set a Groq key in apps/api/.env "
                    "to get a real model response."
                )
            )

        payload: dict = {
            "model": self.model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"

        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            function = tool_calls[0]["function"]
            return LLMResponse(
                content=message.get("content") or "",
                tool_call=LLMToolCall(
                    name=function["name"],
                    arguments=json.loads(function.get("arguments") or "{}"),
                ),
            )
        return LLMResponse(content=(message.get("content") or "").strip())
