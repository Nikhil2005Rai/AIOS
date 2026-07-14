import hashlib
import json
import logging
from dataclasses import asdict

from app.cache.redis_client import RedisCache
from app.core.config import settings
from app.providers.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall, ToolSchema


logger = logging.getLogger(__name__)


class CachingLLMProvider(LLMProvider):
    def __init__(self, inner: LLMProvider, cache: RedisCache, user_id: str) -> None:
        self.inner = inner
        self.cache = cache
        self.user_id = user_id

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        cache_key = self._cache_key(messages=messages, tools=tools)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        response = self.inner.generate(messages, tools=tools)
        self._cache_set(cache_key, response)
        return response

    def _cache_key(self, messages: list[LLMMessage], tools: list[ToolSchema] | None) -> str:
        payload = {
            "provider": type(self.inner).__name__,
            "model": getattr(self.inner, "model", None),
            "user_id": self.user_id,
            "messages": [asdict(message) for message in messages],
            "tools": [asdict(tool) for tool in tools or []],
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"llmcache:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"

    def _cache_get(self, key: str) -> LLMResponse | None:
        try:
            cached = self.cache.get(key)
            if cached is None:
                return None
            payload = json.loads(cached)
            tool_call = payload.get("tool_call")
            return LLMResponse(
                content=payload.get("content", ""),
                tool_call=LLMToolCall(**tool_call) if tool_call else None,
            )
        except Exception:
            logger.exception("LLM cache read failed")
            return None

    def _cache_set(self, key: str, response: LLMResponse) -> None:
        try:
            payload = {
                "content": response.content,
                "tool_call": asdict(response.tool_call) if response.tool_call else None,
            }
            self.cache.set(key, json.dumps(payload, sort_keys=True), settings.llm_cache_ttl_seconds)
        except Exception:
            logger.exception("LLM cache write failed")
