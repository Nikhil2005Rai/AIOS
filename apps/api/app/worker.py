import logging
import time

from app.jobs.document_ingestion import run_document_ingestion_job
from app.jobs.chat_agent import run_chat_agent_job
from app.jobs.entities import JobStatus
from app.jobs.queue import build_job_queue
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

JOB_HANDLERS = {
    "document_ingestion": run_document_ingestion_job,
    "chat_agent_run": run_chat_agent_job,
}


def main() -> None:
    queue = build_job_queue()
    if queue is None:
        raise RuntimeError(
            "Worker requires UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN to be set."
        )
    logger.info("Worker started, polling every %.1fs", settings.worker_poll_interval_seconds)
    while True:
        handled = False
        for job_type, handler in JOB_HANDLERS.items():
            job = queue.dequeue(job_type)
            if job is None:
                continue
            handled = True
            logger.info("Running job %s (%s)", job.id, job.job_type)
            queue.update_status(job.id, JobStatus.RUNNING)
            try:
                result = handler(job.payload)
                queue.update_status(job.id, JobStatus.SUCCEEDED, result=result)
                logger.info("Job %s succeeded", job.id)
            except Exception as exc:
                queue.update_status(job.id, JobStatus.FAILED, error=str(exc))
                logger.exception("Job %s failed", job.id)
        if not handled:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
