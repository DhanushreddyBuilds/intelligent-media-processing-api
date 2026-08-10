import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.analysis.engine import analysis_engine
from app.db.database import SessionLocal
from app.db.models import (
    ProcessingJob,
    ProcessingStatus,
)
from app.workers.queue import job_queue


logger = logging.getLogger(__name__)


class ProcessingWorker:
    """
    Background worker responsible for consuming
    processing jobs and running the analysis engine.
    """

    async def run(self) -> None:
        logger.info("Processing worker started")

        while True:
            message = await job_queue.dequeue()

            try:
                await self.process_job(
                    message.job_id
                )

            except Exception:
                logger.exception(
                    "Unexpected error while processing job %s",
                    message.job_id,
                )

            finally:
                job_queue.task_done()

    async def process_job(
        self,
        job_id: UUID,
    ) -> None:

        db: Session = SessionLocal()

        try:
            job = db.get(
                ProcessingJob,
                job_id,
            )

            if job is None:
                logger.error(
                    "Processing job %s was not found",
                    job_id,
                )
                return

            if job.status != ProcessingStatus.PENDING:
                logger.warning(
                    "Job %s has unexpected status %s",
                    job_id,
                    job.status,
                )
                return

            # -----------------------------------------
            # Mark job as processing
            # -----------------------------------------

            job.status = (
                ProcessingStatus.PROCESSING
            )

            job.started_at = (
                datetime.now(timezone.utc)
            )

            db.commit()

            logger.info(
                "Job %s is now processing",
                job_id,
            )

            # -----------------------------------------
            # Run actual analysis
            # -----------------------------------------

            analysis_engine.analyze(
                db=db,
                job=job,
            )

            # -----------------------------------------
            # Mark job as completed
            # -----------------------------------------

            job.status = (
                ProcessingStatus.COMPLETED
            )

            job.completed_at = (
                datetime.now(timezone.utc)
            )

            db.commit()

            logger.info(
                "Job %s completed successfully",
                job_id,
            )

        except Exception as exc:

            db.rollback()

            job = db.get(
                ProcessingJob,
                job_id,
            )

            if job is not None:

                job.status = (
                    ProcessingStatus.FAILED
                )

                job.failed_at = (
                    datetime.now(timezone.utc)
                )

                job.failure_reason = str(exc)

                db.commit()

            raise

        finally:
            db.close()


processing_worker = ProcessingWorker()