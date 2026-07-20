import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_current_user
from app.api.deps_providers import get_conversation_repository
from app.api.rate_limit_dependencies import rate_limit_by_user
from app.api.schemas import (
    AgentJobResponse,
    AgentJobStatusResponse,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
)
from app.conversations.repository import ConversationRepository
from app.domain.entities import Conversation, Message, User
from app.jobs.queue import build_job_queue, JobQueueError


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


@router.post(
    "/{conversation_id}/messages",
    response_model=AgentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_by_user("chat_message", limit=20, window_seconds=60))],
)
def send_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> AgentJobResponse:
    _require_conversation(repo, conversation_id, current_user.id)

    content = payload.content.strip()
    user_message = repo.add_message(conversation_id=conversation_id, role="user", content=content)

    queue = build_job_queue()
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat requires Redis to be configured (UPSTASH_REDIS_REST_URL/TOKEN).",
        )
    try:
        job = queue.enqueue(
            "chat_agent_run",
            {
                "conversation_id": conversation_id,
                "user_id": current_user.id,
                "user_message_id": user_message.id,
                "content": content,
            },
        )
    except JobQueueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AgentJobResponse(job_id=job.id, status=job.status.value, user_message=_message_response(user_message))


@router.get("/{conversation_id}/messages/jobs/{job_id}", response_model=AgentJobStatusResponse)
def get_message_job(
    conversation_id: str,
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentJobStatusResponse:
    queue = build_job_queue()
    if queue is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue unavailable.")
    try:
        job = queue.get(job_id)
    except JobQueueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if (
        job is None
        or job.payload.get("user_id") != current_user.id
        or job.payload.get("conversation_id") != conversation_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    assistant_message = None
    if job.result is not None:
        assistant_message = MessageResponse(
            id=job.result["id"],
            role=job.result["role"],
            content=job.result["content"],
            tool_name=job.result.get("tool_name"),
            created_at=job.result["created_at"],
        )
    return AgentJobStatusResponse(
        job_id=job.id, status=job.status.value, assistant_message=assistant_message, error=job.error
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
