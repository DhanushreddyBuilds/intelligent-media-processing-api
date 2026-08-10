from pydantic import BaseModel, ConfigDict


class AnalyticsSummaryResponse(BaseModel):
    total_jobs: int
    pending: int
    processing: int
    completed: int
    failed: int
    duplicate_rate: float | None = None
    screenshot_rate: float | None = None
    average_confidence: float | None = None
    average_processing_time_seconds: float | None = None
    model_config = ConfigDict(
        from_attributes=True
    )
