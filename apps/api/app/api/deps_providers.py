from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.graph import MultiAgentGraph
from app.agents.planner import PlannerAgent
from app.agents.registry import AgentRegistry, build_agent_registry
from app.api.dependencies import get_current_user
from app.auth.api_key_repository import UserApiKeyRepository
from app.auth.encryption import EncryptionService
from app.auth.gemini_key_resolver import resolve_gemini_api_key
from app.cache.redis_client import build_redis_cache
from app.conversations.caching import CachingConversationRepository
from app.conversations.repository import ConversationRepository
from app.core.config import settings
from app.db import get_db_session
from app.domain.entities import User
from app.providers.base import LLMProvider
from app.providers.caching import CachingLLMProvider
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.gemini import GeminiEmbeddingProvider
from app.providers.registry import build_provider
from app.retrieval.repository import RetrievalRepository
from app.tools.registry import ToolRegistry, build_tool_registry


def get_llm_provider(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> LLMProvider:
    provider_name, api_key = _resolve_active_provider(current_user, session)
    provider = build_provider(api_key=api_key, provider_name=provider_name)
    cache = build_redis_cache()
    if cache is None:
        return provider
    return CachingLLMProvider(inner=provider, cache=cache, user_id=current_user.id)


def _resolve_active_provider(current_user: User, session: Session) -> tuple[str, str]:
    user_keys = UserApiKeyRepository(session).list_for_user(current_user.id)
    user_key = None
    if current_user.preferred_provider:
        user_key = next((key for key in user_keys if key.provider == current_user.preferred_provider), None)
    elif len(user_keys) == 1:
        user_key = user_keys[0]

    if user_key is not None:
        try:
            decrypted = EncryptionService().decrypt(user_key.encrypted_key)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Your stored {user_key.provider.upper()} API key could not be decrypted and needs to be re-saved.",
            ) from exc
        return user_key.provider, decrypted

    return settings.llm_provider, settings.llm_api_key


def get_embedding_provider(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> EmbeddingProvider:
    try:
        api_key = resolve_gemini_api_key(session, current_user.id, current_user.preferred_provider)
    except ValueError as exc:
        if "could not be decrypted" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your stored GEMINI API key could not be decrypted and needs to be re-saved.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return GeminiEmbeddingProvider(
        api_key=api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


def get_retrieval_repository(session: Annotated[Session, Depends(get_db_session)]) -> RetrievalRepository:
    return RetrievalRepository(session)


def get_conversation_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> ConversationRepository | CachingConversationRepository:
    repository = ConversationRepository(session)
    cache = build_redis_cache()
    if cache is None:
        return repository
    return CachingConversationRepository(inner=repository, cache=cache)


def get_tool_registry() -> ToolRegistry:
    return build_tool_registry()


def get_agent_registry() -> AgentRegistry:
    return build_agent_registry()


def get_planner_agent(
    current_user: Annotated[User, Depends(get_current_user)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    retrieval_repository: Annotated[RetrievalRepository, Depends(get_retrieval_repository)],
    tool_registry: Annotated[ToolRegistry, Depends(get_tool_registry)],
    agent_registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
) -> PlannerAgent:
    return MultiAgentGraph(
        llm_provider=llm_provider,
        tools=tool_registry,
        agents=agent_registry,
        embedding_provider=embedding_provider,
        retrieval_repository=retrieval_repository,
        user_id=current_user.id,
    )
