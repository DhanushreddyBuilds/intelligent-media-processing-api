from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class JobStatusResponse(BaseModel):
    processing_id: UUID
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    model_config = ConfigDict(
        from_attributes=True
    )


class AnalysisResultResponse(BaseModel):
    blur_score: float | None = None
    brightness_score: float | None = None
    duplicate_detected: bool
    ocr_text: str | None = None
    number_plate: str | None = None
    plate_valid: bool | None = None
    screenshot_detected: bool
    photo_of_photo_detected: bool
    issues: str | None = None
    confidence: float | None = None
    analyzed_at: datetime | None = None
    model_config = ConfigDict(
        from_attributes=True
    )


class JobResultResponse(BaseModel):
    processing_id: UUID
    status: str
    analysis: AnalysisResultResponse
    model_config = ConfigDict(
        from_attributes=True
    )


class JobListItem(BaseModel):
    processing_id: UUID
    original_filename: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    confidence: float | None = None
    issues: str | None = None
    model_config = ConfigDict(
        from_attributes=True
    )


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    jobs: list[JobListItem]
    model_config = ConfigDict(
        from_attributes=True
    )
