from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import AnalysisResult, ProcessingJob, ProcessingStatus
from app.schemas.analytics import AnalyticsSummaryResponse


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
)
async def get_analytics_summary(
    db: Session = Depends(get_db),
):
    """
    Return real aggregate statistics computed from the database.
    """

    total_jobs = db.scalar(
        select(func.count()).select_from(ProcessingJob)
    ) or 0

    status_rows = db.execute(
        select(
            ProcessingJob.status,
            func.count(),
        ).group_by(ProcessingJob.status)
    ).all()

    status_counts = {row[0]: row[1] for row in status_rows}

    pending = status_counts.get(ProcessingStatus.PENDING, 0)
    processing = status_counts.get(ProcessingStatus.PROCESSING, 0)
    completed = status_counts.get(ProcessingStatus.COMPLETED, 0)
    failed = status_counts.get(ProcessingStatus.FAILED, 0)

    duplicate_rate = None
    screenshot_rate = None
    average_confidence = None
    average_processing_time_seconds = None

    if completed > 0:
        duplicate_count = db.scalar(
            select(func.count())
            .select_from(AnalysisResult)
            .join(
                ProcessingJob,
                AnalysisResult.job_id == ProcessingJob.id,
            )
            .where(ProcessingJob.status == ProcessingStatus.COMPLETED)
            .where(AnalysisResult.duplicate_detected.is_(True))
        ) or 0

        screenshot_count = db.scalar(
            select(func.count())
            .select_from(AnalysisResult)
            .join(
                ProcessingJob,
                AnalysisResult.job_id == ProcessingJob.id,
            )
            .where(ProcessingJob.status == ProcessingStatus.COMPLETED)
            .where(AnalysisResult.screenshot_detected.is_(True))
        ) or 0

        duplicate_rate = round((duplicate_count / completed) * 100, 2)
        screenshot_rate = round((screenshot_count / completed) * 100, 2)

        avg_confidence = db.scalar(
            select(func.avg(AnalysisResult.confidence))
            .join(
                ProcessingJob,
                AnalysisResult.job_id == ProcessingJob.id,
            )
            .where(ProcessingJob.status == ProcessingStatus.COMPLETED)
        )

        if avg_confidence is not None:
            average_confidence = round(float(avg_confidence), 3)

        avg_seconds = db.scalar(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        ProcessingJob.completed_at
                        - ProcessingJob.started_at,
                    )
                )
            )
            .where(ProcessingJob.status == ProcessingStatus.COMPLETED)
            .where(ProcessingJob.started_at.is_not(None))
            .where(ProcessingJob.completed_at.is_not(None))
        )

        if avg_seconds is not None:
            average_processing_time_seconds = round(
                float(avg_seconds), 3
            )

    return AnalyticsSummaryResponse(
        total_jobs=total_jobs,
        pending=pending,
        processing=processing,
        completed=completed,
        failed=failed,
        duplicate_rate=duplicate_rate,
        screenshot_rate=screenshot_rate,
        average_confidence=average_confidence,
        average_processing_time_seconds=average_processing_time_seconds,
    )
