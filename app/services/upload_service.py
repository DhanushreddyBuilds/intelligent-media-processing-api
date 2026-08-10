from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from PIL import Image

from app.core.config import settings
from app.db.models import ProcessingJob, ProcessingStatus


ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


class UploadService:

    @staticmethod
    async def save_upload(
        file: UploadFile,
    ) -> ProcessingJob:

        if not file.filename:
            raise ValueError("Filename is required")

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(
                "Unsupported image type. "
                "Allowed types: JPEG, PNG, WEBP"
            )

        original_filename = Path(file.filename).name
        extension = Path(original_filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError("Unsupported file extension")

        content = await file.read()

        max_size = settings.max_upload_size_mb * 1024 * 1024

        if len(content) > max_size:
            raise ValueError(
                f"Image exceeds maximum size of "
                f"{settings.max_upload_size_mb} MB"
            )

        processing_id: UUID = uuid4()

        stored_filename = f"{processing_id}{extension}"

        upload_directory = Path(settings.upload_dir)
        upload_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = upload_directory / stored_filename

        file_path.write_bytes(content)

        try:
            with Image.open(file_path) as image:
                width, height = image.size
        except Exception:
            file_path.unlink(missing_ok=True)
            raise ValueError("Uploaded file is not a valid image")

        return ProcessingJob(
            id=processing_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            content_type=file.content_type,
            file_size=len(content),
            width=width,
            height=height,
            status=ProcessingStatus.PENDING,
        )