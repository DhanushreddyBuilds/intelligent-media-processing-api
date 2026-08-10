import uuid

from app.db.models import ProcessingStatus


def test_list_jobs_returns_paginated_response(client, make_job):
    make_job(original_filename="a.jpg")
    make_job(original_filename="b.jpg")
    make_job(original_filename="c.jpg")

    res = client.get("/api/v1/jobs?page=1&page_size=2")

    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["jobs"]) == 2


def test_list_jobs_second_page_returns_remaining_job(client, make_job):
    make_job(original_filename="a.jpg")
    make_job(original_filename="b.jpg")
    make_job(original_filename="c.jpg")

    res = client.get("/api/v1/jobs?page=2&page_size=2")

    assert res.status_code == 200
    data = res.json()

    assert data["page"] == 2
    assert len(data["jobs"]) == 1


def test_list_jobs_empty_database_returns_empty_list(client):
    res = client.get("/api/v1/jobs")

    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 0
    assert data["jobs"] == []


def test_get_job_status_returns_job(client, make_job):
    job = make_job(status=ProcessingStatus.PROCESSING)

    res = client.get(f"/api/v1/jobs/{job.id}")

    assert res.status_code == 200
    data = res.json()

    assert data["processing_id"] == str(job.id)
    assert data["status"] == "processing"


def test_get_job_status_missing_job_returns_404(client):
    random_id = uuid.uuid4()

    res = client.get(f"/api/v1/jobs/{random_id}")

    assert res.status_code == 404


def test_get_job_status_malformed_uuid_returns_422(client):
    res = client.get("/api/v1/jobs/not-a-valid-uuid")

    assert res.status_code == 422


def test_get_job_result_missing_job_returns_404(client):
    random_id = uuid.uuid4()

    res = client.get(f"/api/v1/jobs/{random_id}/result")

    assert res.status_code == 404


def test_get_job_result_pending_job_returns_409(client, make_job):
    job = make_job(status=ProcessingStatus.PENDING)

    res = client.get(f"/api/v1/jobs/{job.id}/result")

    assert res.status_code == 409


def test_get_job_result_failed_job_returns_422(client, make_job):
    job = make_job(
        status=ProcessingStatus.FAILED,
        failure_reason="Image could not be read",
    )

    res = client.get(f"/api/v1/jobs/{job.id}/result")

    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["failure_reason"] == "An internal error occurred while processing this image."
def test_get_job_result_completed_job_returns_analysis(client, make_job, make_result):
    job = make_job(status=ProcessingStatus.COMPLETED)
    make_result(
        job,
        blur_score=1471.85,
        brightness_score=116.71,
        duplicate_detected=True,
        confidence=0.9,
        issues="Duplicate image detected",
    )

    res = client.get(f"/api/v1/jobs/{job.id}/result")

    assert res.status_code == 200
    data = res.json()

    assert data["processing_id"] == str(job.id)
    assert data["status"] == "completed"
    assert data["analysis"]["blur_score"] == 1471.85
    assert data["analysis"]["duplicate_detected"] is True
    assert data["analysis"]["confidence"] == 0.9
    assert data["analysis"]["issues"] == "Duplicate image detected"