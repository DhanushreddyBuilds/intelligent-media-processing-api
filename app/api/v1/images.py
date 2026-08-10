from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.schemas.image import ImageUploadResponse
from app.services.upload_service import UploadService
from app.workers.queue import job_queue


router = APIRouter(
    prefix="/images",
    tags=["Images"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=ImageUploadResponse,
)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        job = await UploadService.save_upload(file)

        db.add(job)
        db.commit()
        db.refresh(job)

        await job_queue.enqueue(job.id)

        return ImageUploadResponse(
            processing_id=job.id,
            status=job.status.value,
            message="Image accepted for processing",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )