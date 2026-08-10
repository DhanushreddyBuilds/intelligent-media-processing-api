import asyncio

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import ProcessingJob, ProcessingStatus
from app.workers.queue import job_queue
from app.workers.worker import processing_worker


async def main() -> None:
    db = SessionLocal()

    try:
        job = db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.status == ProcessingStatus.PENDING)
            .order_by(ProcessingJob.created_at.desc())
        )

        if job is None:
            print("No PENDING job found.")
            return

        print(f"Testing worker with job: {job.id}")

    finally:
        db.close()

    worker_task = asyncio.create_task(
        processing_worker.run()
    )

    print("Worker task started.")

    await job_queue.enqueue(job.id)

    print("Job added to queue.")
    print(f"Queue size: {job_queue.size()}")

    await asyncio.sleep(3)

    worker_task.cancel()

    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    db = SessionLocal()

    try:
        updated_job = db.get(
            ProcessingJob,
            job.id,
        )

        print(f"Final status: {updated_job.status.value}")
        print(f"Started at: {updated_job.started_at}")
        print(f"Completed at: {updated_job.completed_at}")
        print(f"Failure reason: {updated_job.failure_reason}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())