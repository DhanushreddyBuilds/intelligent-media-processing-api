import io

from PIL import Image


def _make_jpeg_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), (120, 120, 120)).save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_upload_valid_jpeg_creates_pending_job(client, db_session):
    from app.db.models import ProcessingJob

    file_bytes = _make_jpeg_bytes()

    res = client.post(
        "/api/v1/images",
        files={"file": ("test.jpg", file_bytes, "image/jpeg")},
    )

    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "pending"
    assert "processing_id" in data

    job = db_session.query(ProcessingJob).filter_by(id=data["processing_id"]).first()
    assert job is not None
    assert job.original_filename == "test.jpg"


def test_upload_rejects_non_image_file(client):
    res = client.post(
        "/api/v1/images",
        files={"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
    )

    assert res.status_code == 400


def test_upload_rejects_missing_file(client):
    res = client.post("/api/v1/images")

    assert res.status_code == 422