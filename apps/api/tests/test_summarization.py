"""Tests for conversation summarization middleware.

Tests are pure-unit: no DB, no Redis, no real LLM.
All dependencies are faked via simple in-process objects.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from app.conversations.summarization import (
    _summary_cache_key,
    build_effective_history,
)
from app.domain.entities import Message
from app.providers.base import LLMMessage, LLMResponse


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

def _msg(index: int) -> Message:
    """Build a deterministic Message with a stable id."""
    return Message(
        id=f"msg-{index:04d}",
        conversation_id="conv-test",
        role="user" if index % 2 == 0 else "assistant",
        content=f"Message number {index}",
        tool_name=None,
        created_at=datetime(2024, 1, 1, 0, index % 60),
    )


def _messages(n: int) -> list[Message]:
    return [_msg(i) for i in range(n)]


class FakeProvider:
    """LLMProvider stub that counts generate() calls."""

    def __init__(self, summary: str = "FAKE SUMMARY") -> None:
        self.call_count = 0
        self._summary = summary

    def generate(self, messages: list[LLMMessage], tools=None) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(content=self._summary)


class FakeCache:
    """In-memory cache that behaves like RedisCache."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class BrokenCache:
    """Cache whose get/set always raise, to test graceful fallback."""

    def get(self, key: str) -> str | None:
        raise RuntimeError("Cache is broken")

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        raise RuntimeError("Cache is broken")


# ---------------------------------------------------------------------------
# Test 1: Below-threshold — returns all messages verbatim, no LLM call
# ---------------------------------------------------------------------------

def test_below_threshold_returns_all_messages_unchanged() -> None:
    """5 messages < threshold(20) → all returned verbatim, no LLM call."""
    msgs = _messages(5)
    provider = FakeProvider()

    result = build_effective_history(
        messages=msgs,
        llm_provider=provider,
        cache=None,
        conversation_id="conv-1",
    )

    assert len(result) == 5
    # Content preserved exactly
    for i, llm_msg in enumerate(result):
        assert llm_msg.content == msgs[i].content
        assert llm_msg.role == msgs[i].role
    assert provider.call_count == 0, "No LLM call should be made below threshold"


# ---------------------------------------------------------------------------
# Test 2: Above-threshold — 1 summary + recent messages, one LLM call
# ---------------------------------------------------------------------------

def test_above_threshold_returns_summary_plus_recent() -> None:
    """25 messages > threshold(20) → 1 system summary + 8 recent, LLM called once."""
    msgs = _messages(25)
    provider = FakeProvider("Short summary of earlier turns.")
    cache = FakeCache()

    result = build_effective_history(
        messages=msgs,
        llm_provider=provider,
        cache=cache,
        conversation_id="conv-2",
    )

    # Should be 1 summary message + 8 recent
    assert len(result) == 1 + 8
    # First message is the system summary
    summary_msg = result[0]
    assert summary_msg.role == "system"
    assert summary_msg.content.startswith("Summary of earlier conversation:")
    assert "Short summary of earlier turns." in summary_msg.content
    # Remaining 8 are the most-recent verbatim
    recent_msgs = result[1:]
    expected_recent = msgs[-8:]
    for i, llm_msg in enumerate(recent_msgs):
        assert llm_msg.content == expected_recent[i].content
        assert llm_msg.role == expected_recent[i].role
    # LLM called exactly once
    assert provider.call_count == 1


# ---------------------------------------------------------------------------
# Test 3: Cache hit — second call with same messages does NOT call LLM again
# ---------------------------------------------------------------------------

def test_cache_hit_prevents_second_llm_call() -> None:
    """Second call with the same older set and a working cache → no second LLM call."""
    msgs = _messages(25)
    provider = FakeProvider("Cached summary.")
    cache = FakeCache()

    # First call populates the cache
    build_effective_history(
        messages=msgs,
        llm_provider=provider,
        cache=cache,
        conversation_id="conv-3",
    )
    assert provider.call_count == 1

    # Second call with identical messages should hit cache
    result = build_effective_history(
        messages=msgs,
        llm_provider=provider,
        cache=cache,
        conversation_id="conv-3",
    )
    assert provider.call_count == 1, "LLM must NOT be called on a cache hit"
    assert len(result) == 1 + 8
    assert "Cached summary." in result[0].content


# ---------------------------------------------------------------------------
# Test 4: cache=None — no caching, LLM called every time, no crash
# ---------------------------------------------------------------------------

def test_no_cache_calls_llm_every_time() -> None:
    """cache=None → LLM is called on every invocation, no crash."""
    msgs = _messages(25)
    provider = FakeProvider("Summary without cache.")

    # Call twice
    for _ in range(2):
        result = build_effective_history(
            messages=msgs,
            llm_provider=provider,
            cache=None,
            conversation_id="conv-4",
        )
        assert len(result) == 1 + 8

    assert provider.call_count == 2, "LLM called once per invocation when cache=None"


# ---------------------------------------------------------------------------
# Test 5: Broken cache — falls through gracefully, still produces correct summary
# ---------------------------------------------------------------------------

def test_broken_cache_falls_through_gracefully() -> None:
    """A cache whose get/set raise → still returns a correct summary, no crash."""
    msgs = _messages(25)
    provider = FakeProvider("Summary despite broken cache.")
    cache = BrokenCache()

    result = build_effective_history(
        messages=msgs,
        llm_provider=provider,
        cache=cache,
        conversation_id="conv-5",
    )

    assert len(result) == 1 + 8
    assert result[0].role == "system"
    assert "Summary despite broken cache." in result[0].content
    assert provider.call_count == 1


# ---------------------------------------------------------------------------
# Test 6: Cache key stability — same messages produce same key
# ---------------------------------------------------------------------------

def test_summary_cache_key_is_deterministic() -> None:
    """The cache key must be stable for the same set of messages."""
    msgs = _messages(17)  # the "older" portion for a 25-msg conversation
    key1 = _summary_cache_key("conv-x", msgs)
    key2 = _summary_cache_key("conv-x", msgs)
    assert key1 == key2


def test_summary_cache_key_differs_on_new_message() -> None:
    """Adding one more message to the older set changes the cache key."""
    older_a = _messages(17)
    older_b = _messages(18)
    key_a = _summary_cache_key("conv-x", older_a)
    key_b = _summary_cache_key("conv-x", older_b)
    assert key_a != key_b


def test_summary_cache_key_differs_across_conversations() -> None:
    """Same messages under different conversation IDs produce different keys."""
    msgs = _messages(17)
    key_a = _summary_cache_key("conv-alpha", msgs)
    key_b = _summary_cache_key("conv-beta", msgs)
    assert key_a != key_b


# ---------------------------------------------------------------------------
# Test 7: Boundary — exactly at threshold returns verbatim (no summary)
# ---------------------------------------------------------------------------

def test_exactly_at_threshold_returns_verbatim() -> None:
    """20 messages == threshold → no summarization triggered."""
    msgs = _messages(20)
    provider = FakeProvider()

    result = build_effective_history(
        messages=msgs,
        llm_provider=provider,
        cache=None,
        conversation_id="conv-boundary",
    )

    assert len(result) == 20
    assert provider.call_count == 0


# ---------------------------------------------------------------------------
# Test 8: Exactly one message over threshold → summarization kicks in
# ---------------------------------------------------------------------------

def test_one_over_threshold_triggers_summarization() -> None:
    """21 messages > threshold(20) → summarization is triggered."""
    msgs = _messages(21)
    provider = FakeProvider("One-over summary.")

    result = build_effective_history(
        messages=msgs,
        llm_provider=provider,
        cache=None,
        conversation_id="conv-one-over",
    )

    assert len(result) == 1 + 8
    assert result[0].role == "system"
    assert provider.call_count == 1
