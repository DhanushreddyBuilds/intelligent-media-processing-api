from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImageUploadResponse(BaseModel):
    processing_id: UUID
    status: str
    message: str

    model_config = ConfigDict(from_attributes=True)