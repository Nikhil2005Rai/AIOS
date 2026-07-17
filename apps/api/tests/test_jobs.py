import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs.queue import JobQueue, JobQueueError
from app.jobs.entities import JobStatus
from app.jobs.document_ingestion import run_document_ingestion_job
from app.infrastructure.models import DocumentModel, DocumentChunkModel


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


class FailingUpstashRedisClient:
    def get(self, key: str) -> str | None:
        raise RuntimeError("Redis connection lost")

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        raise RuntimeError("Redis connection lost")

    def rpush(self, key: str, value: str) -> int:
        raise RuntimeError("Redis connection lost")

    def lpop(self, key: str) -> str | None:
        raise RuntimeError("Redis connection lost")


class FakeEmbeddingProvider:
    def __init__(self, **kwargs) -> None:
        pass

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]


def test_job_queue_round_trip() -> None:
    queue = JobQueue("http://fake", "fake")
    queue.client = FakeUpstashRedisClient()

    payload = {"test": 123}
    job = queue.enqueue("test_job", payload)
    assert job.status == JobStatus.QUEUED
    assert job.payload == payload

    retrieved = queue.get(job.id)
    assert retrieved is not None
    assert retrieved.id == job.id

    dequeued = queue.dequeue("test_job")
    assert dequeued is not None
    assert dequeued.id == job.id

    assert queue.dequeue("test_job") is None

    queue.update_status(job.id, JobStatus.RUNNING)
    updated = queue.get(job.id)
    assert updated.status == JobStatus.RUNNING

    queue.update_status(job.id, JobStatus.SUCCEEDED, result={"ok": True})
    updated2 = queue.get(job.id)
    assert updated2.status == JobStatus.SUCCEEDED
    assert updated2.result == {"ok": True}


def test_job_queue_raises_on_failure() -> None:
    queue = JobQueue("http://fake", "fake")
    queue.client = FailingUpstashRedisClient()

    with pytest.raises(JobQueueError):
        queue.enqueue("test_job", {})

    with pytest.raises(JobQueueError):
        queue.dequeue("test_job")

    with pytest.raises(JobQueueError):
        queue.get("some-id")

    with pytest.raises(JobQueueError):
        queue.update_status("some-id", JobStatus.RUNNING)


def test_run_document_ingestion_job(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.jobs.document_ingestion.GeminiEmbeddingProvider",
        FakeEmbeddingProvider
    )
    monkeypatch.setattr(
        "app.jobs.document_ingestion.SessionLocal",
        lambda: db_session
    )
    monkeypatch.setattr(
        "app.jobs.document_ingestion.get_engine",
        lambda: db_session.bind
    )

    from app.infrastructure.models import UserModel
    from app.auth.api_key_repository import UserApiKeyRepository
    from app.auth.encryption import EncryptionService

    user = UserModel(id="test-user-id", email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    UserApiKeyRepository(db_session).upsert(
        user_id="test-user-id",
        provider="gemini",
        encrypted_key=EncryptionService().encrypt("fake-api-key")
    )

    payload = {
        "user_id": "test-user-id",
        "title": "Ingested Notes",
        "content": "alpha beta gamma",
    }

    result = run_document_ingestion_job(payload)
    assert result["title"] == "Ingested Notes"
    assert result["chunk_count"] == 1
    assert "document_id" in result

    document_id = result["document_id"]
    document = db_session.scalar(select(DocumentModel).where(DocumentModel.id == document_id))
    assert document is not None
    assert document.title == "Ingested Notes"
    assert document.user_id == "test-user-id"

    chunk = db_session.scalar(select(DocumentChunkModel).where(DocumentChunkModel.document_id == document.id))
    assert chunk is not None
    assert chunk.content == "alpha beta gamma"
    assert chunk.embedding == [0.1] * 768
