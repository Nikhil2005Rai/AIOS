import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.agents.planner import PlannerAgent
from app.api.dependencies import get_current_user
from app.api.deps_providers import get_conversation_repository, get_planner_agent
from app.api.schemas import (
    AgentMessageResponse,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
)
from app.conversations.repository import ConversationRepository
from app.db import get_db_session
from app.domain.entities import Conversation, Message, User
from app.providers.base import LLMGenerationError, LLMMessage
from app.providers.embeddings.errors import EmbeddingError
from app.retrieval.repository import RetrievalRepository
from app.tools.repository import ToolCallRepository


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> list[ConversationResponse]:
    conversations = repo.list_for_user(current_user.id)
    return [_conversation_response(conversation) for conversation in conversations]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> ConversationResponse:
    conversation = repo.create(user_id=current_user.id, title=payload.title.strip())
    return _conversation_response(conversation)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> list[MessageResponse]:
    _require_conversation(repo, conversation_id, current_user.id)
    return [_message_response(message) for message in repo.list_messages(conversation_id)]


@router.post("/{conversation_id}/messages", response_model=AgentMessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    agent: Annotated[PlannerAgent, Depends(get_planner_agent)],
) -> AgentMessageResponse:
    _require_conversation(repo, conversation_id, current_user.id)

    content = payload.content.strip()
    user_message = repo.add_message(conversation_id=conversation_id, role="user", content=content)
    history = [
        LLMMessage(role=message.role, content=message.content)
        for message in repo.list_messages(conversation_id)
        if message.id != user_message.id
    ]

    try:
        result = agent.run(user_input=content, history=history)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM provider failed: upstream request failed.",
        ) from exc
    except LLMGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM provider failed: {exc}") from exc
    except EmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Embedding provider failed: {exc}") from exc
    except Exception as exc:
        logger.exception("An unexpected error occurred during agent execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred.",
        ) from exc

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
    return AgentMessageResponse(
        user_message=_message_response(user_message),
        assistant_message=_message_response(assistant_message),
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> Response:
    deleted = repo.delete(conversation_id=conversation_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> ConversationResponse:
    conversation = repo.update_title(conversation_id=conversation_id, user_id=current_user.id, title=payload.title.strip())
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _conversation_response(conversation)


def _require_conversation(repo: ConversationRepository, conversation_id: str, user_id: str) -> Conversation:
    conversation = repo.get_for_user(conversation_id=conversation_id, user_id=user_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def _conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        tool_name=message.tool_name,
        created_at=message.created_at,
    )
