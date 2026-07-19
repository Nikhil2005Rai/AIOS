from app.auth.provider_resolution import resolve_gemini_api_key
from app.core.config import settings
from app.db import SessionLocal, get_engine
from app.infrastructure.models import UserModel
from app.providers.embeddings.gemini import GeminiEmbeddingProvider
from app.retrieval.chunking import chunk_text
from app.retrieval.repository import DocumentRepository


def run_document_ingestion_job(payload: dict) -> dict:
    """payload: {"user_id": str, "title": str, "content": str}"""
    get_engine()
    session = SessionLocal()
    try:
        user_id = payload["user_id"]
        user_model = session.get(UserModel, user_id)
        if not user_model:
            raise ValueError("User not found")
        api_key = resolve_gemini_api_key(session, user_id, user_model.preferred_provider)

        chunks = chunk_text(payload["content"])
        if not chunks:
            raise ValueError("Document content is empty after chunking")

        embedding_provider = GeminiEmbeddingProvider(
            api_key=api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
        embeddings = embedding_provider.embed(chunks)

        document = DocumentRepository(session).create_with_chunks(
            user_id=user_id,
            title=payload["title"],
            source_type="pasted_text",
            chunks=chunks,
            embeddings=embeddings,
        )
        return {
            "document_id": document.id,
            "title": document.title,
            "chunk_count": len(chunks),
        }
    finally:
        session.close()
