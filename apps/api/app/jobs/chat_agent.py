import json
import logging

from app.agents.graph import MultiAgentGraph
from app.agents.registry import build_agent_registry
from app.auth.provider_resolution import resolve_active_provider, resolve_gemini_api_key
from app.cache.redis_client import build_redis_cache
from app.conversations.caching import CachingConversationRepository
from app.conversations.repository import ConversationRepository
from app.core.config import settings
from app.db import SessionLocal, get_engine
from app.infrastructure.models import UserModel
from app.providers.base import LLMGenerationError, LLMMessage
from app.providers.caching import CachingLLMProvider
from app.providers.embeddings.errors import EmbeddingError
from app.providers.embeddings.gemini import GeminiEmbeddingProvider
from app.providers.registry import build_provider
from app.conversations.summarization import build_effective_history
from app.retrieval.repository import RetrievalRepository
from app.tools.registry import build_tool_registry
from app.tools.repository import ToolCallRepository

logger = logging.getLogger(__name__)


def run_chat_agent_job(payload: dict) -> dict:
    """payload: {"conversation_id": str, "user_id": str, "user_message_id": str, "content": str}"""
    get_engine()
    session = SessionLocal()
    try:
        conversation_id = payload["conversation_id"]
        user_id = payload["user_id"]
        user_message_id = payload["user_message_id"]
        content = payload["content"]

        user_model = session.get(UserModel, user_id)
        if user_model is None:
            raise ValueError("User not found")
        preferred_provider = user_model.preferred_provider

        inner_repo = ConversationRepository(session)
        cache = build_redis_cache()
        repo = CachingConversationRepository(inner=inner_repo, cache=cache) if cache else inner_repo

        try:
            provider_name, api_key = resolve_active_provider(session, user_id, preferred_provider)
        except ValueError as exc:
            raise ValueError(f"LLM provider failed: {exc}") from exc

        llm_provider = build_provider(api_key=api_key, provider_name=provider_name)
        if cache is not None:
            llm_provider = CachingLLMProvider(inner=llm_provider, cache=cache, user_id=user_id)

        try:
            gemini_key = resolve_gemini_api_key(session, user_id, preferred_provider)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        embedding_provider = GeminiEmbeddingProvider(
            api_key=gemini_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

        agent = MultiAgentGraph(
            llm_provider=llm_provider,
            tools=build_tool_registry(),
            agents=build_agent_registry(),
            embedding_provider=embedding_provider,
            retrieval_repository=RetrievalRepository(session),
            user_id=user_id,
        )

        all_messages = [
            m for m in repo.list_messages(conversation_id)
            if m.id != user_message_id
        ]
        history = build_effective_history(
            messages=all_messages,
            llm_provider=llm_provider,
            cache=cache,
            conversation_id=conversation_id,
        )

        try:
            result = agent.run(user_input=content, history=history)
        except LLMGenerationError as exc:
            raise ValueError(f"LLM provider failed: {exc}") from exc
        except EmbeddingError as exc:
            raise ValueError(f"Embedding provider failed: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected error during agent execution")
            raise ValueError("An unexpected server error occurred.") from exc

        assistant_message = repo.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.answer,
            tool_name=result.tool_name,
        )
        if result.tool_name and result.tool_arguments is not None and result.tool_output is not None:
            ToolCallRepository(session).create(
                conversation_id=conversation_id,
                message_id=assistant_message.id,
                tool_name=result.tool_name,
                agent_name=result.agent_name or "planner",
                arguments=json.dumps(result.tool_arguments),
                output=result.tool_output,
            )
        if result.retrieval_query is not None:
            RetrievalRepository(session).create(
                conversation_id=conversation_id,
                message_id=assistant_message.id,
                agent_name=result.agent_name or "knowledge",
                query=result.retrieval_query,
                chunk_ids=result.retrieval_chunk_ids or [],
                scores=result.retrieval_scores or [],
            )

        return {
            "id": assistant_message.id,
            "role": assistant_message.role,
            "content": assistant_message.content,
            "tool_name": assistant_message.tool_name,
            "created_at": assistant_message.created_at.isoformat(),
        }
    finally:
        session.close()
