import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps_providers import get_embedding_provider
from app.core.config import settings
from app.domain.entities import User
from app.infrastructure.models import DocumentChunkModel, DocumentModel
from app.main import app
from app.providers.embeddings.gemini import GeminiEmbeddingProvider
from app.providers.embeddings.errors import EmbeddingError
from app.retrieval.chunking import chunk_text


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]


class FailingEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Gemini returned 3072 embedding dimensions, expected 768.")


def test_chunk_text_uses_overlap() -> None:
    chunks = chunk_text("abcdefghij", chunk_size=4, overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_create_document_chunks_embeds_and_persists(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbeddingProvider()

    response = client.post(
        "/documents",
        headers=auth_headers,
        json={"title": "Notes", "content": "alpha beta gamma"},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Notes"
    assert response.json()["chunk_count"] == 1

    document = db_session.scalar(select(DocumentModel).where(DocumentModel.title == "Notes"))
    assert document is not None
    chunk = db_session.scalar(select(DocumentChunkModel).where(DocumentChunkModel.document_id == document.id))
    assert chunk is not None
    assert chunk.content == "alpha beta gamma"


def test_create_document_returns_502_when_embedding_provider_fails(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_embedding_provider] = lambda: FailingEmbeddingProvider()

    response = client.post(
        "/documents",
        headers=auth_headers,
        json={"title": "Bad Notes", "content": "alpha beta gamma"},
    )

    assert response.status_code == 502
    assert "Embedding provider failed" in response.json()["detail"]
    assert "expected 768" in response.json()["detail"]


def test_embedding_provider_requires_gemini_key_when_active_provider_is_groq(
    db_session: Session,
    monkeypatch,
) -> None:
    user = User(id="user-3", email="groq@example.com", password_hash="hash", created_at=None)
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "llm_api_key", "groq-key")

    try:
        get_embedding_provider(current_user=user, session=db_session)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        assert "Gemini key" in getattr(exc, "detail", "")
    else:
        raise AssertionError("Expected get_embedding_provider to reject Groq-only embedding setup")


def test_gemini_embedding_provider_uses_embed_content_config(monkeypatch) -> None:
    captured_payload = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"embedding": {"values": [0.1] * 768}}

    def fake_post(url: str, json: dict, timeout: int):
        captured_payload["url"] = url
        captured_payload["json"] = json
        captured_payload["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.providers.embeddings.gemini.httpx.post", fake_post)

    vectors = GeminiEmbeddingProvider(api_key="gemini-key", model="gemini-embedding-001", dimensions=768).embed(
        ["hello"]
    )

    assert len(vectors[0]) == 768
    assert "models/gemini-embedding-001:embedContent" in captured_payload["url"]
    assert captured_payload["json"]["model"] == "models/gemini-embedding-001"
    assert captured_payload["json"]["outputDimensionality"] == 768


def test_gemini_embedding_provider_sanitizes_http_errors(monkeypatch) -> None:
    def fake_post(url: str, json: dict, timeout: int):
        request = httpx.Request("POST", url)
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError("upstream failed", request=request, response=response)

    monkeypatch.setattr("app.providers.embeddings.gemini.httpx.post", fake_post)

    with pytest.raises(EmbeddingError) as exc_info:
        GeminiEmbeddingProvider(api_key="secret-key", model="gemini-embedding-001", dimensions=768).embed(
            ["hello"]
        )

    message = str(exc_info.value)
    assert "HTTP 503 Service Unavailable" in message
    assert "secret-key" not in message
    assert "?key=" not in message
