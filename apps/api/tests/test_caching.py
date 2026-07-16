from datetime import datetime, timezone

import pytest

from app.cache.redis_client import RedisCache, build_redis_cache
from app.conversations.caching import CachingConversationRepository
from app.domain.entities import Conversation, Message
from app.providers.base import LLMGenerationError, LLMMessage, LLMResponse, LLMToolCall, ToolSchema
from app.providers.caching import CachingLLMProvider


class FakeRedisCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value
        self.ttls[key] = ttl_seconds

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


class FailingRedisCache:
    def get(self, key: str) -> str | None:
        raise RuntimeError("redis get failed")

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        raise RuntimeError("redis set failed")

    def delete(self, key: str) -> None:
        raise RuntimeError("redis delete failed")


class CountingProvider:
    model = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        self.calls += 1
        return LLMResponse(content=f"response-{self.calls}")


class FailingProvider:
    model = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
        self.calls += 1
        raise LLMGenerationError("provider failed")


def test_build_redis_cache_returns_none_without_credentials(monkeypatch) -> None:
    monkeypatch.setattr("app.cache.redis_client.settings.upstash_redis_rest_url", "")
    monkeypatch.setattr("app.cache.redis_client.settings.upstash_redis_rest_token", "")

    assert build_redis_cache() is None


def test_redis_cache_methods_degrade_when_sdk_fails() -> None:
    class FailingClient:
        def get(self, key: str):
            raise RuntimeError("get failed")

        def set(self, key: str, value: str, ex: int):
            raise RuntimeError("set failed")

        def delete(self, key: str):
            raise RuntimeError("delete failed")

    cache = RedisCache.__new__(RedisCache)
    cache.client = FailingClient()

    assert cache.get("key") is None
    cache.set("key", "value", 60)
    cache.delete("key")


def test_caching_llm_provider_reuses_identical_response() -> None:
    inner = CountingProvider()
    provider = CachingLLMProvider(inner=inner, cache=FakeRedisCache(), user_id="user-1")
    messages = [LLMMessage(role="user", content="hello")]

    first = provider.generate(messages)
    second = provider.generate(messages)

    assert first.content == "response-1"
    assert second.content == "response-1"
    assert inner.calls == 1


def test_caching_llm_provider_isolates_cache_by_user() -> None:
    inner = CountingProvider()
    cache = FakeRedisCache()
    messages = [LLMMessage(role="user", content="hello")]

    provider_a = CachingLLMProvider(inner=inner, cache=cache, user_id="user-a")
    provider_b = CachingLLMProvider(inner=inner, cache=cache, user_id="user-b")

    first = provider_a.generate(messages)
    second = provider_b.generate(messages)

    assert first.content == "response-1"
    assert second.content == "response-2"
    assert inner.calls == 2


def test_caching_llm_provider_restores_cached_tool_call() -> None:
    class ToolCallingProvider:
        model = "fake-model"

        def __init__(self) -> None:
            self.calls = 0

        def generate(self, messages: list[LLMMessage], tools: list[ToolSchema] | None = None) -> LLMResponse:
            self.calls += 1
            return LLMResponse(
                content="",
                tool_call=LLMToolCall(name="echo", arguments={"text": "hello"}),
            )

    inner = ToolCallingProvider()
    provider = CachingLLMProvider(inner=inner, cache=FakeRedisCache(), user_id="user-1")
    messages = [LLMMessage(role="user", content="use a tool")]

    first = provider.generate(messages)
    second = provider.generate(messages)

    assert first.tool_call == LLMToolCall(name="echo", arguments={"text": "hello"})
    assert second.tool_call == LLMToolCall(name="echo", arguments={"text": "hello"})
    assert inner.calls == 1


def test_caching_llm_provider_uses_different_keys_for_different_messages() -> None:
    inner = CountingProvider()
    provider = CachingLLMProvider(inner=inner, cache=FakeRedisCache(), user_id="user-1")

    first = provider.generate([LLMMessage(role="user", content="hello")])
    second = provider.generate([LLMMessage(role="user", content="goodbye")])

    assert first.content == "response-1"
    assert second.content == "response-2"
    assert inner.calls == 2


def test_caching_llm_provider_propagates_inner_exception_uncached() -> None:
    inner = FailingProvider()
    provider = CachingLLMProvider(inner=inner, cache=FakeRedisCache(), user_id="user-1")

    with pytest.raises(LLMGenerationError):
        provider.generate([LLMMessage(role="user", content="hello")])
    with pytest.raises(LLMGenerationError):
        provider.generate([LLMMessage(role="user", content="hello")])

    assert inner.calls == 2


def test_caching_llm_provider_survives_cache_failures() -> None:
    inner = CountingProvider()
    provider = CachingLLMProvider(inner=inner, cache=FailingRedisCache(), user_id="user-1")

    response = provider.generate([LLMMessage(role="user", content="hello")])

    assert response.content == "response-1"
    assert inner.calls == 1


class FakeConversationRepository:
    def __init__(self) -> None:
        self.list_messages_calls = 0
        self.messages = [
            Message(
                id="message-1",
                conversation_id="conversation-1",
                role="user",
                content="hello",
                tool_name=None,
                created_at=datetime.now(timezone.utc),
            )
        ]

    def list_for_user(self, user_id: str) -> list[Conversation]:
        return []

    def get_for_user(self, conversation_id: str, user_id: str) -> Conversation | None:
        return None

    def create(self, user_id: str, title: str) -> Conversation:
        return Conversation(
            id="conversation-1",
            user_id=user_id,
            title=title,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def list_messages(self, conversation_id: str) -> list[Message]:
        self.list_messages_calls += 1
        return list(self.messages)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
    ) -> Message:
        message = Message(
            id=f"message-{len(self.messages) + 1}",
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name,
            created_at=datetime.now(timezone.utc),
        )
        self.messages.append(message)
        return message


def test_caching_conversation_repository_caches_until_add_message_invalidates() -> None:
    inner = FakeConversationRepository()
    repository = CachingConversationRepository(inner=inner, cache=FakeRedisCache())

    first = repository.list_messages("conversation-1")
    second = repository.list_messages("conversation-1")
    repository.add_message("conversation-1", role="assistant", content="hi")
    third = repository.list_messages("conversation-1")

    assert [message.id for message in first] == ["message-1"]
    assert [message.id for message in second] == ["message-1"]
    assert [message.id for message in third] == ["message-1", "message-2"]
    assert inner.list_messages_calls == 2


def test_caching_conversation_repository_survives_cache_failures() -> None:
    inner = FakeConversationRepository()
    repository = CachingConversationRepository(inner=inner, cache=FailingRedisCache())

    messages = repository.list_messages("conversation-1")
    added = repository.add_message("conversation-1", role="assistant", content="hi")

    assert [message.id for message in messages] == ["message-1"]
    assert added.id == "message-2"
    assert inner.list_messages_calls == 1
