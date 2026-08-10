import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values

# ------------------------------------------------------------
# CRITICAL: this block must run before any `app.*` module is
# imported anywhere in the test session. Settings() binds to
# DATABASE_URL at import time, so we derive an isolated test
# database URL from .env and set it as an environment variable
# first, ensuring the app/engine never touches the real
# development database during tests.
# ------------------------------------------------------------

_env_path = Path(__file__).resolve().parent.parent / ".env"
_real_values = dotenv_values(_env_path)
_real_database_url = _real_values.get("DATABASE_URL") or os.environ.get("DATABASE_URL")

if not _real_database_url:
    raise RuntimeError(
        "DATABASE_URL not found in .env; cannot derive an isolated test database URL."
    )

_parts = urlsplit(_real_database_url)
_test_database_url = urlunsplit(
    (_parts.scheme, _parts.netloc, "/intelligent_media_test", _parts.query, _parts.fragment)
)

os.environ["DATABASE_URL"] = _test_database_url

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.v1 import images as images_module  # noqa: E402
from app.api.v1 import jobs as jobs_module  # noqa: E402
from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.models import AnalysisResult, Base, ProcessingJob, ProcessingStatus  # noqa: E402
from app.main import app  # noqa: E402


# ------------------------------------------------------------
# Tests exercise routes and the database directly; they don't
# need the background worker/queue running. Overriding the
# lifespan here avoids the real job_queue singleton binding to
# a test event loop, which is a test-infrastructure concern
# only -- app/main.py itself is unchanged.
# ------------------------------------------------------------
@asynccontextmanager
async def _noop_lifespan(_app):
    yield


app.router.lifespan_context = _noop_lifespan


# ------------------------------------------------------------
# Override each router's get_db so API requests during tests
# use the isolated test session instead of the real DB.
# ------------------------------------------------------------
def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[jobs_module.get_db] = _override_get_db
app.dependency_overrides[images_module.get_db] = _override_get_db


# ------------------------------------------------------------
# Schema lifecycle: create tables once per test session against
# the isolated test database, drop them when the session ends.
# ------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _setup_test_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ------------------------------------------------------------
# Clean up rows between tests so each test starts from an
# empty table, without dropping/recreating the schema each time.
# ------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    session = SessionLocal()
    try:
        session.query(AnalysisResult).delete()
        session.query(ProcessingJob).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def make_job(db_session):
    """
    Factory fixture for creating a ProcessingJob row directly in
    the test database, bypassing the upload/worker flow, so Jobs
    API tests can set up specific states (pending/failed/completed).
    """

    created_count = {"n": 0}

    def _make_job(status=ProcessingStatus.PENDING, **overrides):
        created_count["n"] += 1

        # Stagger created_at so ordering (newest first) is deterministic
        # across multiple jobs created within the same test.
        base_time = datetime.now(timezone.utc) - timedelta(seconds=created_count["n"])

        defaults = dict(
            id=uuid.uuid4(),
            original_filename="test.jpg",
            stored_filename=f"{uuid.uuid4()}.jpg",
            file_path="uploads/test.jpg",
            content_type="image/jpeg",
            file_size=1024,
            width=200,
            height=200,
            status=status,
            created_at=base_time,
        )
        defaults.update(overrides)

        job = ProcessingJob(**defaults)
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    return _make_job


@pytest.fixture()
def make_result(db_session):
    """
    Factory fixture for attaching an AnalysisResult row to an
    existing job.
    """

    def _make_result(job, **overrides):
        defaults = dict(
            id=uuid.uuid4(),
            job_id=job.id,
            blur_score=500.0,
            brightness_score=120.0,
            duplicate_detected=False,
            ocr_text=None,
            number_plate=None,
            plate_valid=None,
            screenshot_detected=False,
            photo_of_photo_detected=False,
            issues=None,
            confidence=1.0,
            analyzed_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)

        result = AnalysisResult(**defaults)
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        return result

    return _make_result