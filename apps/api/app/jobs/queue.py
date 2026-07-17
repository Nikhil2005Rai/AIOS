import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import settings
from app.jobs.entities import Job, JobStatus

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 86400  # 24 hours


class JobQueueError(RuntimeError):
    """Raised when the job queue is unavailable or an operation fails."""


class JobQueue:
    def __init__(self, url: str, token: str) -> None:
        from upstash_redis import Redis
        self.client = Redis(url=url, token=token)

    def enqueue(self, job_type: str, payload: dict) -> Job:
        job = Job(
            id=str(uuid4()),
            job_type=job_type,
            status=JobStatus.QUEUED,
            payload=payload,
            result=None,
            error=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        try:
            self._save(job)
            self.client.rpush(f"jobqueue:{job_type}", job.id)
        except Exception as exc:
            raise JobQueueError(f"Failed to enqueue job: {exc}") from exc
        return job

    def dequeue(self, job_type: str) -> Job | None:
        try:
            job_id = self.client.lpop(f"jobqueue:{job_type}")
        except Exception as exc:
            raise JobQueueError(f"Failed to dequeue job: {exc}") from exc
        if job_id is None:
            return None
        return self.get(job_id)

    def get(self, job_id: str) -> Job | None:
        try:
            raw = self.client.get(f"job:{job_id}")
        except Exception as exc:
            raise JobQueueError(f"Failed to read job {job_id}: {exc}") from exc
        if raw is None:
            return None
        return self._deserialize(raw)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        job = self.get(job_id)
        if job is None:
            raise JobQueueError(f"Cannot update unknown job {job_id}")
        job.status = status
        job.result = result
        job.error = error
        job.updated_at = datetime.now(timezone.utc)
        try:
            self._save(job)
        except Exception as exc:
            raise JobQueueError(f"Failed to update job {job_id}: {exc}") from exc

    def _save(self, job: Job) -> None:
        payload = asdict(job)
        payload["status"] = job.status.value
        payload["created_at"] = job.created_at.isoformat()
        payload["updated_at"] = job.updated_at.isoformat()
        self.client.set(f"job:{job.id}", json.dumps(payload), ex=JOB_TTL_SECONDS)

    @staticmethod
    def _deserialize(raw: str) -> Job:
        payload = json.loads(raw)
        return Job(
            id=payload["id"],
            job_type=payload["job_type"],
            status=JobStatus(payload["status"]),
            payload=payload["payload"],
            result=payload.get("result"),
            error=payload.get("error"),
            created_at=datetime.fromisoformat(payload["created_at"]),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
        )


def build_job_queue() -> JobQueue | None:
    if not settings.upstash_redis_rest_url or not settings.upstash_redis_rest_token:
        return None
    try:
        return JobQueue(url=settings.upstash_redis_rest_url, token=settings.upstash_redis_rest_token)
    except Exception:
        logger.exception("Job queue initialization failed")
        return None
