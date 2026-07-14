import json
import logging
import time

import httpx

from app.core.config import settings
from app.providers.base import LLMGenerationError, LLMMessage, LLMProvider, LLMResponse, LLMToolCall, ToolSchema


logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash",
        max_output_tokens: int | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_output_tokens = max_output_tokens if max_output_tokens is not None else settings.llm_max_output_tokens

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                content=(
                    "LLM_API_KEY is not configured. The Phase 1 pipeline is working, "
                    "but set a Gemini key in apps/api/.env to get a real model response."
                )
            )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload: dict = {
            "contents": self._contents(messages),
            "generationConfig": {
                "maxOutputTokens": self.max_output_tokens,
                "thinkingConfig": {"includeThoughts": False},
            },
        }
        if tools:
            payload["tools"] = [{"functionDeclarations": [self._function_declaration(tool) for tool in tools]}]

        response = self._post_generate_content(url=url, payload=payload)
        data = response.json()
        logger.debug("Gemini raw response: %s", data)
        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(content="The model returned no candidates.")
        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        parts = candidate.get("content", {}).get("parts", [])

        for part in parts:
            function_call = part.get("functionCall")
            if function_call:
                return LLMResponse(
                    content="",
                    tool_call=LLMToolCall(
                        name=function_call.get("name", ""),
                        arguments=function_call.get("args") or {},
                    ),
                )

        text = "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()
        if finish_reason == "MAX_TOKENS" and not text:
            raise LLMGenerationError(
                f"Gemini stopped with finishReason=MAX_TOKENS before producing an answer (model={self.model})."
            )
        return LLMResponse(content=text or "The model returned an empty response.")

    def _post_generate_content(self, url: str, payload: dict) -> httpx.Response:
        for attempt in range(2):
            try:
                response = httpx.post(
                    url,
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                reason = exc.response.reason_phrase
                if status_code in RETRYABLE_STATUS_CODES and attempt == 0:
                    time.sleep(1)
                    continue
                raise LLMGenerationError(
                    f"Gemini request failed with HTTP {status_code} {reason} (model={self.model})."
                ) from exc
            except httpx.HTTPError as exc:
                raise LLMGenerationError(
                    f"Gemini request failed with {exc.__class__.__name__} (model={self.model})."
                ) from exc

        raise LLMGenerationError(f"Gemini request failed after retry (model={self.model}).")

    @staticmethod
    def _contents(messages: list[LLMMessage]) -> list[dict]:
        contents = []
        for message in messages:
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": f"{message.role}: {message.content}"}]})
        return contents

    @staticmethod
    def _function_declaration(tool: ToolSchema) -> dict:
        parameters = json.loads(json.dumps(tool.parameters))
        parameters.pop("additionalProperties", None)
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
        }
