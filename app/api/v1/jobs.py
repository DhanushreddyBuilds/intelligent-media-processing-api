from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ProcessingJob
from app.schemas.result import (
    AnalysisResultResponse,
    JobListItem,
    JobListResponse,
    JobResultResponse,
    JobStatusResponse,
)


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get(
    "",
    response_model=JobListResponse,
)
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of processing jobs, newest first.
    """

    if page < 1:
        page = 1

    if page_size < 1:
        page_size = 20
    elif page_size > 100:
        page_size = 100

    total = db.scalar(
        select(func.count()).select_from(ProcessingJob)
    )

    offset = (page - 1) * page_size

    jobs = db.scalars(
        select(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .offset(offset)
        .limit(page_size)
    ).all()

    items = []

    for job in jobs:
        confidence = None
        issues = None

        if job.analysis_result is not None:
            confidence = job.analysis_result.confidence
            issues = job.analysis_result.issues

        items.append(
            JobListItem(
                processing_id=job.id,
                original_filename=job.original_filename,
                status=job.status.value,
                created_at=job.created_at,
                completed_at=job.completed_at,
                confidence=confidence,
                issues=issues,
            )
        )

    return JobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        jobs=items,
    )


@router.get(
    "/{processing_id}",
    response_model=JobStatusResponse,
)
async def get_job_status(
    processing_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return the current processing status of a job.
    """

    job = db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.id == processing_id
        )
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found",
        )

    return JobStatusResponse(
        processing_id=job.id,
        status=job.status.value,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        failed_at=job.failed_at,
        failure_reason=(
            "An internal error occurred while processing this image."
            if job.failure_reason
            else None
        ),
    )


@router.get(
    "/{processing_id}/result",
    response_model=JobResultResponse,
)
async def get_job_result(
    processing_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return the analysis result for a completed job.
    """

    job = db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.id == processing_id
        )
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found",
        )

    if job.analysis_result is None:

        if job.status.value == "failed":
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Processing failed",
                    "failure_reason": "An internal error occurred while processing this image.",
                },
            )

        raise HTTPException(
            status_code=409,
            detail="Analysis result is not ready yet",
        )

    return JobResultResponse(
        processing_id=job.id,
        status=job.status.value,
        analysis=AnalysisResultResponse(
            blur_score=job.analysis_result.blur_score,
            brightness_score=(
                job.analysis_result.brightness_score
            ),
            duplicate_detected=(
                job.analysis_result.duplicate_detected
            ),
            ocr_text=job.analysis_result.ocr_text,
            number_plate=job.analysis_result.number_plate,
            plate_valid=job.analysis_result.plate_valid,
            screenshot_detected=(
                job.analysis_result.screenshot_detected
            ),
            photo_of_photo_detected=(
                job.analysis_result.photo_of_photo_detected
            ),
            issues=job.analysis_result.issues,
            confidence=job.analysis_result.confidence,
            analyzed_at=job.analysis_result.analyzed_at,
        ),
    )