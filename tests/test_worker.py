from datetime import datetime
from uuid import uuid4

import pytest

from app.db.models import ProcessingJob, ProcessingStatus
from app.workers.worker import ProcessingWorker


class FakeSession:
    def __init__(self, job=None):
        self.job = job
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def get(self, model, job_id):
        if self.job is not None and self.job.id == job_id:
            return self.job
        return None

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_worker_missing_job(monkeypatch):
    worker = ProcessingWorker()
    job_id = uuid4()

    session = FakeSession()

    monkeypatch.setattr(
        "app.workers.worker.SessionLocal",
        lambda: session,
    )

    await worker.process_job(job_id)

    assert session.commits == 0
    assert session.rollbacks == 0
    assert session.closed is True


@pytest.mark.asyncio
async def test_worker_ignores_non_pending_job(monkeypatch):
    worker = ProcessingWorker()

    job = ProcessingJob(
        id=uuid4(),
        original_filename="test.jpg",
        stored_filename="test.jpg",
        file_path="test.jpg",
        content_type="image/jpeg",
        file_size=100,
        width=100,
        height=100,
        status=ProcessingStatus.COMPLETED,
    )

    session = FakeSession(job)

    monkeypatch.setattr(
        "app.workers.worker.SessionLocal",
        lambda: session,
    )

    await worker.process_job(job.id)

    assert job.status == ProcessingStatus.COMPLETED
    assert session.commits == 0
    assert session.closed is True


@pytest.mark.asyncio
async def test_worker_completes_successful_job(monkeypatch):
    worker = ProcessingWorker()

    job = ProcessingJob(
        id=uuid4(),
        original_filename="test.jpg",
        stored_filename="test.jpg",
        file_path="test.jpg",
        content_type="image/jpeg",
        file_size=100,
        width=100,
        height=100,
        status=ProcessingStatus.PENDING,
    )

    session = FakeSession(job)

    monkeypatch.setattr(
        "app.workers.worker.SessionLocal",
        lambda: session,
    )

    analysis_called = False

    def fake_analyze(db, job):
        nonlocal analysis_called
        analysis_called = True

    monkeypatch.setattr(
        "app.workers.worker.analysis_engine.analyze",
        fake_analyze,
    )

    await worker.process_job(job.id)

    assert analysis_called is True
    assert job.status == ProcessingStatus.COMPLETED
    assert job.started_at is not None
    assert job.completed_at is not None
    assert isinstance(job.started_at, datetime)
    assert isinstance(job.completed_at, datetime)
    assert session.commits == 2
    assert session.rollbacks == 0
    assert session.closed is True


@pytest.mark.asyncio
async def test_worker_marks_failed_job(monkeypatch):
    worker = ProcessingWorker()

    job = ProcessingJob(
        id=uuid4(),
        original_filename="test.jpg",
        stored_filename="test.jpg",
        file_path="test.jpg",
        content_type="image/jpeg",
        file_size=100,
        width=100,
        height=100,
        status=ProcessingStatus.PENDING,
    )

    session = FakeSession(job)

    monkeypatch.setattr(
        "app.workers.worker.SessionLocal",
        lambda: session,
    )

    def failing_analyze(db, job):
        raise RuntimeError("analysis failed")

    monkeypatch.setattr(
        "app.workers.worker.analysis_engine.analyze",
        failing_analyze,
    )

    with pytest.raises(RuntimeError, match="analysis failed"):
        await worker.process_job(job.id)

    assert job.status == ProcessingStatus.FAILED
    assert job.started_at is not None
    assert job.failed_at is not None
    assert job.failure_reason == "analysis failed"
    assert session.rollbacks == 1
    assert session.commits == 2
    assert session.closed is True