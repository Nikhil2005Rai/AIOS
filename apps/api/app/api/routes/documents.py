from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.api.deps_providers import get_embedding_provider
from app.api.rate_limit_dependencies import rate_limit_by_user
from app.api.schemas import DocumentCreateRequest, DocumentJobResponse, DocumentJobStatusResponse, DocumentResponse
from app.db import get_db_session
from app.domain.entities import User
from app.infrastructure.models import DocumentModel
from app.providers.embeddings.base import EmbeddingProvider
from app.jobs.queue import build_job_queue, JobQueueError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_by_user("document_upload", limit=2, window_seconds=60))],
)
def create_document(
    payload: DocumentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> DocumentJobResponse:
    queue = build_job_queue()
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document ingestion requires Redis to be configured (UPSTASH_REDIS_REST_URL/TOKEN).",
        )
    api_key = getattr(embedding_provider, "api_key", None)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Embeddings require a Gemini key; save one in BYOK settings.",
        )
    try:
        job = queue.enqueue(
            "document_ingestion",
            {
                "user_id": current_user.id,
                "title": payload.title.strip(),
                "content": payload.content,
            },
        )
    except JobQueueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return DocumentJobResponse(job_id=job.id, status=job.status.value)


@router.get("/jobs/{job_id}", response_model=DocumentJobStatusResponse)
def get_document_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentJobStatusResponse:
    queue = build_job_queue()
    if queue is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue unavailable.")
    try:
        job = queue.get(job_id)
    except JobQueueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if job is None or job.payload.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return DocumentJobStatusResponse(
        job_id=job.id, status=job.status.value, result=job.result, error=job.error
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[DocumentResponse]:
    documents = session.scalars(
        select(DocumentModel).where(DocumentModel.user_id == current_user.id).order_by(DocumentModel.created_at.desc())
    ).all()
    return [
        DocumentResponse(
            id=doc.id,
            title=doc.title,
            source_type=doc.source_type,
            chunk_count=len(doc.chunks),
            created_at=doc.created_at,
        )
        for doc in documents
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> None:
    document = session.scalar(
        select(DocumentModel).where(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id
        )
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    session.delete(document)
    session.commit()
