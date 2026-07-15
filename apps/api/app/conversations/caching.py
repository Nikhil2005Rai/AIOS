import json
import logging
from dataclasses import asdict
from datetime import datetime

from app.cache.redis_client import RedisCache
from app.conversations.repository import ConversationRepository
from app.core.config import settings
from app.domain.entities import Conversation, Message


logger = logging.getLogger(__name__)


class CachingConversationRepository:
    def __init__(self, inner: ConversationRepository, cache: RedisCache) -> None:
        self.inner = inner
        self.cache = cache

    def list_for_user(self, user_id: str) -> list[Conversation]:
        return self.inner.list_for_user(user_id)

    def get_for_user(self, conversation_id: str, user_id: str) -> Conversation | None:
        return self.inner.get_for_user(conversation_id=conversation_id, user_id=user_id)

    def create(self, user_id: str, title: str) -> Conversation:
        return self.inner.create(user_id=user_id, title=title)

    def list_messages(self, conversation_id: str) -> list[Message]:
        cache_key = self._messages_key(conversation_id)
        cached_messages = self._cache_get(cache_key)
        if cached_messages is not None:
            return cached_messages

        messages = self.inner.list_messages(conversation_id)
        self._cache_set(cache_key, messages)
        return messages

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
    ) -> Message:
        message = self.inner.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name,
        )
        try:
            self.cache.delete(self._messages_key(conversation_id))
        except Exception:
            logger.exception("Conversation message cache invalidation failed")
        return message

    @staticmethod
    def _messages_key(conversation_id: str) -> str:
        return f"conv:{conversation_id}:messages"

    def _cache_get(self, key: str) -> list[Message] | None:
        try:
            cached = self.cache.get(key)
            if cached is None:
                return None
            return [self._message_from_payload(payload) for payload in json.loads(cached)]
        except Exception:
            logger.exception("Conversation message cache read failed")
            return None

    def _cache_set(self, key: str, messages: list[Message]) -> None:
        try:
            payload = [self._message_to_payload(message) for message in messages]
            self.cache.set(
                key,
                json.dumps(payload, sort_keys=True),
                settings.conversation_cache_ttl_seconds,
            )
        except Exception:
            logger.exception("Conversation message cache write failed")

    @staticmethod
    def _message_to_payload(message: Message) -> dict:
        payload = asdict(message)
        payload["created_at"] = message.created_at.isoformat()
        return payload

    @staticmethod
    def _message_from_payload(payload: dict) -> Message:
        return Message(
            id=payload["id"],
            conversation_id=payload["conversation_id"],
            role=payload["role"],
            content=payload["content"],
            tool_name=payload.get("tool_name"),
            created_at=datetime.fromisoformat(payload["created_at"]),
        )
