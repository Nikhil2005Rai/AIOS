from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.deps_providers import get_embedding_provider
from app.api.schemas import DocumentCreateRequest, DocumentResponse
from app.db import get_db_session
from app.domain.entities import User
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.errors import EmbeddingError
from app.retrieval.chunking import chunk_text
from app.retrieval.repository import DocumentRepository


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> DocumentResponse:
    chunks = chunk_text(payload.content)
    if not chunks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document content is empty")

    try:
        embeddings = embedding_provider.embed(chunks)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding provider failed: upstream request failed.",
        ) from exc
    except (EmbeddingError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Embedding provider failed: {exc}") from exc

    document = DocumentRepository(session).create_with_chunks(
        user_id=current_user.id,
        title=payload.title.strip(),
        source_type="pasted_text",
        chunks=chunks,
        embeddings=embeddings,
    )
    return DocumentResponse(
        id=document.id,
        title=document.title,
        source_type=document.source_type,
        chunk_count=len(chunks),
        created_at=document.created_at,
    )
