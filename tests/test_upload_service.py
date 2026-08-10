import io

import pytest
from fastapi import UploadFile

from app.services.upload_service import UploadService


def make_upload_file(
    content: bytes,
    filename: str,
    content_type: str,
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers={"content-type": content_type},
    )


@pytest.mark.asyncio
async def test_valid_jpeg_upload(tmp_path, monkeypatch):
    from PIL import Image

    image_buffer = io.BytesIO()

    image = Image.new("RGB", (100, 80), "white")
    image.save(image_buffer, format="JPEG")

    image_buffer.seek(0)

    upload = UploadFile(
        file=image_buffer,
        filename="test.jpg",
        headers={"content-type": "image/jpeg"},
    )

    monkeypatch.setattr(
        "app.services.upload_service.settings.upload_dir",
        str(tmp_path),
    )

    job = await UploadService.save_upload(upload)

    assert job.original_filename == "test.jpg"
    assert job.content_type == "image/jpeg"
    assert job.file_size > 0
    assert job.width == 100
    assert job.height == 80
    assert job.status.value == "pending"

    assert job.file_path

    assert (tmp_path / job.stored_filename).exists()


@pytest.mark.asyncio
async def test_rejects_unsupported_content_type():
    upload = make_upload_file(
        b"test data",
        "test.txt",
        "text/plain",
    )

    with pytest.raises(ValueError, match="Unsupported image type"):
        await UploadService.save_upload(upload)


@pytest.mark.asyncio
async def test_rejects_unsupported_extension():
    upload = make_upload_file(
        b"test data",
        "test.gif",
        "image/gif",
    )

    with pytest.raises(ValueError, match="Unsupported image type"):
        await UploadService.save_upload(upload)


@pytest.mark.asyncio
async def test_rejects_invalid_image(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.upload_service.settings.upload_dir",
        str(tmp_path),
    )

    upload = make_upload_file(
        b"this is not a real image",
        "fake.jpg",
        "image/jpeg",
    )

    with pytest.raises(ValueError, match="not a valid image"):
        await UploadService.save_upload(upload)

    assert list(tmp_path.iterdir()) == []