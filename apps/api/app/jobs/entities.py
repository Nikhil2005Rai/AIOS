from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

@dataclass(slots=True)
class Job:
    id: str
    job_type: str
    status: JobStatus
    payload: dict
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime
