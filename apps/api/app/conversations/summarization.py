import hashlib
import logging

from app.cache.redis_client import RedisCache
from app.core.config import settings
from app.domain.entities import Message
from app.providers.base import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "Summarize the following conversation history concisely, preserving any facts, "
    "decisions, names, numbers, or commitments that later turns might need to reference. "
    "Write it as a neutral third-person summary, not a transcript. Aim for well under "
    "10% of the original length."
)


def build_effective_history(
    messages: list[Message],
    llm_provider: LLMProvider,
    cache: RedisCache | None,
    conversation_id: str,
) -> list[LLMMessage]:
    """Returns the message history to send to an agent, summarizing older messages
    if the conversation has grown past the configured threshold. Always keeps the
    most recent `history_keep_recent_messages` messages verbatim."""
    if len(messages) <= settings.history_summary_trigger_messages:
        return [LLMMessage(role=message.role, content=message.content) for message in messages]

    recent = messages[-settings.history_keep_recent_messages :]
    older = messages[: -settings.history_keep_recent_messages]

    summary_text = _get_or_build_summary(older, llm_provider, cache, conversation_id)

    result = [LLMMessage(role="system", content=f"Summary of earlier conversation:\n{summary_text}")]
    result.extend(LLMMessage(role=message.role, content=message.content) for message in recent)
    return result


def _get_or_build_summary(
    older: list[Message],
    llm_provider: LLMProvider,
    cache: RedisCache | None,
    conversation_id: str,
) -> str:
    cache_key = _summary_cache_key(conversation_id, older)
    if cache is not None:
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            logger.exception("Failed to read conversation summary from cache")

    transcript = "\n".join(f"{message.role}: {message.content}" for message in older)
    response = llm_provider.generate(
        [
            LLMMessage(role="system", content=SUMMARY_SYSTEM_PROMPT),
            LLMMessage(role="user", content=transcript),
        ]
    )
    summary_text = response.content

    if cache is not None:
        try:
            cache.set(cache_key, summary_text, settings.history_summary_cache_ttl_seconds)
        except Exception:
            logger.exception("Failed to cache conversation summary")

    return summary_text


def _summary_cache_key(conversation_id: str, older: list[Message]) -> str:
    fingerprint = hashlib.sha256(
        "|".join(message.id for message in older).encode("utf-8")
    ).hexdigest()
    return f"convsummary:{conversation_id}:{fingerprint}"
