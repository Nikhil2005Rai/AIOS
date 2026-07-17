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


from app.jobs.queue import JobQueue

class FakeUpstashRedisClient:
    def __init__(self) -> None:
        self.db: dict[str, str] = {}
        self.queues: dict[str, list[str]] = {}

    def get(self, key: str) -> str | None:
        return self.db.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.db[key] = value

    def rpush(self, key: str, value: str) -> int:
        if key not in self.queues:
            self.queues[key] = []
        self.queues[key].append(value)
        return len(self.queues[key])

    def lpop(self, key: str) -> str | None:
        if key not in self.queues or not self.queues[key]:
            return None
        return self.queues[key].pop(0)


def test_chunk_text_uses_overlap() -> None:
    chunks = chunk_text("abcdefghij", chunk_size=4, overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_create_document_enqueues_successfully(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_queue = JobQueue("http://fake", "fake")
    fake_queue.client = FakeUpstashRedisClient()
    monkeypatch.setattr("app.api.routes.documents.build_job_queue", lambda: fake_queue)

    class MockEmbeddingProvider:
        api_key = "gemini-test-key"
    app.dependency_overrides[get_embedding_provider] = lambda: MockEmbeddingProvider()

    response = client.post(
        "/documents",
        headers=auth_headers,
        json={"title": "Notes", "content": "alpha beta gamma"},
    )
    assert response.status_code == 202
    res_data = response.json()
    assert "job_id" in res_data
    assert res_data["status"] == "queued"

    job_id = res_data["job_id"]
    job_response = client.get(f"/documents/jobs/{job_id}", headers=auth_headers)
    assert job_response.status_code == 200
    job_data = job_response.json()
    assert job_data["job_id"] == job_id
    assert job_data["status"] == "queued"
    assert job_data["result"] is None


def test_create_document_without_redis_returns_503(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.routes.documents.build_job_queue", lambda: None)

    class MockEmbeddingProvider:
        api_key = "gemini-test-key"
    app.dependency_overrides[get_embedding_provider] = lambda: MockEmbeddingProvider()

    response = client.post(
        "/documents",
        headers=auth_headers,
        json={"title": "Notes", "content": "alpha beta gamma"},
    )
    assert response.status_code == 503
    assert "ingestion requires Redis" in response.json()["detail"]


def test_get_document_job_returns_404_for_other_user(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_queue = JobQueue("http://fake", "fake")
    fake_queue.client = FakeUpstashRedisClient()
    monkeypatch.setattr("app.api.routes.documents.build_job_queue", lambda: fake_queue)

    class MockEmbeddingProvider:
        api_key = "gemini-test-key"
    app.dependency_overrides[get_embedding_provider] = lambda: MockEmbeddingProvider()

    response = client.post(
        "/documents",
        headers=auth_headers,
        json={"title": "Notes", "content": "alpha beta gamma"},
    )
    job_id = response.json()["job_id"]

    other_register = client.post("/auth/register", json={"email": "other_doc_user@example.com", "password": "password123"})
    other_token = other_register.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    bad_get = client.get(f"/documents/jobs/{job_id}", headers=other_headers)
    assert bad_get.status_code == 404


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
