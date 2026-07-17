from app.auth.api_key_repository import UserApiKeyRepository
from app.auth.encryption import EncryptionService
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
        gemini_key_entity = UserApiKeyRepository(session).get_for_user_provider(user_id, "gemini")
        if gemini_key_entity is not None:
            api_key = EncryptionService().decrypt(gemini_key_entity.encrypted_key)
        else:
            user_model = session.get(UserModel, user_id)
            if not user_model:
                raise ValueError("User not found")
            
            user_keys = UserApiKeyRepository(session).list_for_user(user_id)
            user_key = None
            if user_model.preferred_provider:
                user_key = next((key for key in user_keys if key.provider == user_model.preferred_provider), None)
            elif len(user_keys) == 1:
                user_key = user_keys[0]
            
            if user_key is not None:
                active_provider = user_key.provider
                active_api_key = EncryptionService().decrypt(user_key.encrypted_key)
            else:
                active_provider = settings.llm_provider
                active_api_key = settings.llm_api_key
            
            if active_provider == "gemini":
                api_key = active_api_key
            else:
                raise ValueError("Embeddings require a Gemini key; save one in BYOK settings.")

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
