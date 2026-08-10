\# Intelligent Media Processing API



An asynchronous backend service that accepts image uploads, queues them for

background processing, and runs an automated analysis pipeline (blur,

brightness, duplicate detection, OCR, number-plate recognition, screenshot

detection, and photo-of-photo detection) — with a lightweight dashboard

frontend for monitoring results.



\## Problem Statement



Manually reviewing uploaded images for quality and content issues (blur,

duplicates, screenshots, recaptured photos, etc.) doesn't scale. This API

automates that triage: an image is uploaded, queued, analyzed in the

background, and the results (scores, detected issues, and an overall

confidence score) are persisted and made available through a REST API and

dashboard.



\## Features



\- Asynchronous image upload → background processing pipeline

\- Blur detection (Laplacian variance)

\- Brightness detection

\- Duplicate detection (perceptual hashing)

\- OCR text extraction (Tesseract)

\- Indian vehicle number-plate candidate extraction and validation

\- Screenshot detection (aspect ratio + text density + edge heuristics)

\- Photo-of-photo detection (texture/frequency heuristic — see

&#x20; \*\*Known Limitations\*\*)

\- Per-job confidence scoring based on detected issues

\- Paginated job history and analytics summary API

\- Dashboard frontend with real-time processing status, history, and

&#x20; analytics — no localStorage dependency, fully backed by the API



\## Architecture
Frontend (HTML/CSS/JS)

│

▼

FastAPI application

│

▼

Upload API ──► UploadService ──► ProcessingJob row (PostgreSQL, PENDING)

│

▼

asyncio.Queue (in-process job queue)

│

▼

Background ProcessingWorker (runs via FastAPI lifespan)

│

▼

AnalysisEngine ──► Detectors (blur, brightness, duplicate, OCR,

│ plate, screenshot, photo-of-photo)

▼

AnalysisResult row (PostgreSQL) ──► ProcessingJob status → COMPLETED/FAILED

│

▼

Jobs API / Analytics API ──► Frontend Dashboard \& History





The worker is a single background `asyncio` task started in the FastAPI

`lifespan` context; it consumes job IDs from an in-process `asyncio.Queue`

(not a distributed queue) and processes them one at a time.



\## Technology Stack



\- \*\*Backend:\*\* Python, FastAPI, Uvicorn

\- \*\*Database:\*\* PostgreSQL, SQLAlchemy (2.0 declarative style), psycopg 3

\- \*\*Config:\*\* Pydantic Settings (`.env`-based)

\- \*\*Image processing:\*\* OpenCV, Pillow, imagehash

\- \*\*OCR:\*\* pytesseract + Tesseract OCR engine

\- \*\*Testing:\*\* pytest, pytest-asyncio, httpx (via FastAPI `TestClient`)

\- \*\*Frontend:\*\* vanilla HTML/CSS/JavaScript (no build step, no framework)



\## Project Structure



app/

main.py FastAPI app, lifespan (starts background worker)

api/v1/

images.py POST /api/v1/images

jobs.py GET /api/v1/jobs, /jobs/{id}, /jobs/{id}/result

analytics.py GET /api/v1/analytics/summary

router.py Combines the above under /api/v1

core/config.py Pydantic Settings (.env)

db/

database.py SQLAlchemy engine/session

models.py ProcessingJob, AnalysisResult, ProcessingStatus

schemas/ Pydantic request/response models

services/upload\_service.py Upload validation + storage

workers/

queue.py asyncio.Queue wrapper

worker.py Background processing loop

analysis/

engine.py Orchestrates all detectors

detectors/ blur, brightness, duplicate, ocr, plate,

screenshot, photo\_of\_photo



frontend/ Dashboard, Upload, History views (static, served

by FastAPI's StaticFiles at "/")



scripts/ Manual verification scripts used during

development (not part of the automated suite)



tests/ Automated pytest suite (see Testing below)



uploads/ Stored uploaded images (gitignored — see

Project Hygiene notes)





\## Prerequisites



\- Python 3.12 (developed and tested against 3.12.4)

\- PostgreSQL (running locally, with a database you can create)

\- Tesseract OCR installed locally — the code shells out to Tesseract via

&#x20; `pytesseract`, which requires the Tesseract binary to be installed

&#x20; separately from the Python package. Verified working with:



tesseract v5.5.3



&#x20; On Windows, Tesseract is commonly installed to:



C:\\Program Files\\Tesseract-OCR\\tesseract.exe



&#x20; and must either be on your `PATH` or configured for `pytesseract` to find it.



\## Environment Variables



Copy `.env.example` to `.env` and fill in real values:



APP\_NAME=Intelligent Media Processing API

APP\_VERSION=1.0.0

ENVIRONMENT=development



DATABASE\_URL=postgresql+psycopg://postgres:YOUR\_PASSWORD@localhost:5432/intelligent\_media



UPLOAD\_DIR=uploads

MAX\_UPLOAD\_SIZE\_MB=10





`DATABASE\_URL` must point at a PostgreSQL database that already exists —

the application does not create the database itself (see below).



\## Setup



1\. \*\*Create a virtual environment and activate it:\*\*



python -m venv .venv

.venv\\Scripts\\Activate.ps1





2\. \*\*Install dependencies:\*\*



pip install -r requirements.txt





3\. \*\*Create the PostgreSQL database\*\* (the application does not do this

&#x20;  automatically):



psql -U postgres -c "CREATE DATABASE intelligent\_media;"





4\. \*\*Configure environment variables:\*\*



copy .env.example .env



&#x20;  Then edit `.env` with your actual PostgreSQL password.



5\. \*\*Initialize the database schema:\*\*



python scripts\\init\_db.py





6\. \*\*Run the application:\*\*



uvicorn app.main:app



&#x20;  The API and dashboard are both served from the same origin:

&#x20;  - Dashboard: http://127.0.0.1:8000

&#x20;  - Swagger/OpenAPI docs: http://127.0.0.1:8000/docs

&#x20;  - Health check: http://127.0.0.1:8000/health



\## Frontend Usage



The frontend is a static site (no build step) served directly by FastAPI

at `/`. It has three views:



\- \*\*Dashboard\*\* — total/completed/failed job counts and a recent-jobs list,

&#x20; backed by `GET /api/v1/analytics/summary` and `GET /api/v1/jobs`.

\- \*\*Upload\*\* — drag-and-drop or click-to-browse image upload, with live

&#x20; status polling until the job completes and its analysis result renders.

\- \*\*History\*\* — paginated table of all processing jobs (`GET

&#x20; /api/v1/jobs?page=\&page\_size=`), with a "View" action that opens a modal

&#x20; showing the full analysis result for that specific job.



\## API Endpoints



| Method | Path | Description |

|---|---|---|

| GET | `/health` | Service health check |

| POST | `/api/v1/images` | Upload an image; creates a PENDING job and enqueues it |

| GET | `/api/v1/jobs` | Paginated job list (`page`, `page\_size` query params) |

| GET | `/api/v1/jobs/{processing\_id}` | Job status/lifecycle timestamps |

| GET | `/api/v1/jobs/{processing\_id}/result` | Full analysis result (200 completed / 409 pending / 422 failed / 404 not found) |

| GET | `/api/v1/analytics/summary` | Aggregate counts and rates for the dashboard |



Full interactive documentation is available via Swagger at `/docs` once

the app is running.



\## Image Upload Workflow



1\. Client sends `POST /api/v1/images` with a multipart file.

2\. `UploadService` validates content type/extension (JPEG, PNG, WEBP only)

&#x20;  and enforces `MAX\_UPLOAD\_SIZE\_MB` (default 10 MB), validates the file is

&#x20;  actually a readable image (via Pillow), and stores it under `uploads/`

&#x20;  with a generated filename (not the original filename) to avoid path

&#x20;  collisions/traversal issues.

3\. A `ProcessingJob` row is created with status `PENDING`.

4\. The job ID is pushed onto the in-process `asyncio.Queue`.

5\. The response returns immediately with `processing\_id` and `status:

&#x20;  "pending"` — processing happens asynchronously.



\## Background Processing Flow



The background worker (started as an `asyncio` task in the FastAPI

`lifespan`) continuously dequeues job IDs and, for each one:



1\. Loads the `ProcessingJob` from PostgreSQL, verifies it's `PENDING`.

2\. Transitions it to `PROCESSING`, records `started\_at`.

3\. Calls `AnalysisEngine.analyze()`, which runs all detectors and persists

&#x20;  an `AnalysisResult` row.

4\. Transitions the job to `COMPLETED` (`completed\_at` set) on success, or

&#x20;  `FAILED` (`failed\_at` + `failure\_reason` set) if an exception occurs.



\## Analysis Pipeline



Each uploaded image is run through:



1\. \*\*Blur\*\* — Laplacian variance; below threshold (100.0) flags "blurry."

2\. \*\*Brightness\*\* — mean pixel intensity; outside 40–220 flags too

&#x20;  dark/overexposed.

3\. \*\*OCR\*\* — Tesseract extracts any readable text from the image.

4\. \*\*Number plate\*\* — candidate extraction from OCR text, matched against

&#x20;  a simplified Indian plate format regex.

5\. \*\*Screenshot detection\*\* — weighted heuristic combining aspect-ratio

&#x20;  similarity to common screen ratios, OCR text density, and edge density.

6\. \*\*Photo-of-photo detection\*\* — weighted heuristic combining texture

&#x20;  noise, high-frequency (Laplacian) variance, and edge density. \*\*This

&#x20;  detector's thresholds are a first-pass heuristic and have not been

&#x20;  calibrated against real labeled sample images — see Known Limitations.\*\*

7\. \*\*Duplicate detection\*\* — perceptual hash compared against all other

&#x20;  completed jobs' images (Hamming distance ≤ 5).

8\. \*\*Confidence score\*\* — starts at 1.0, with fixed deductions for each

&#x20;  detected issue (blur −0.15, dark/overexposed −0.10, duplicate −0.10,

&#x20;  screenshot −0.10, photo-of-photo −0.10), clamped to \[0, 1].



\## Testing



The project uses `pytest` with an isolated PostgreSQL test database.



\*\*Test database:\*\* `intelligent\_media\_test` — a separate physical database

from your development `intelligent\_media` database. Tests never read from

or write to your real development data. `tests/conftest.py`:



\- Overrides `DATABASE\_URL` to point at the test database \*before\* any

&#x20; application module is imported.

\- Creates all tables at the start of the test session and drops them at

&#x20; the end (`Base.metadata.create\_all` / `drop\_all`).

\- Overrides the FastAPI `get\_db` dependency for the API routers so

&#x20; requests during tests use the isolated test session.

\- Disables the FastAPI lifespan (background worker) during tests, since

&#x20; HTTP-level API tests exercise the database directly and don't need the

&#x20; live worker/queue running.



\*\*Before running tests for the first time\*\*, create the test database:



psql -U postgres -c "CREATE DATABASE intelligent\_media\_test;"





\*\*Run the full suite:\*\*



python -m pytest -v





Current state: \*\*53 tests, 53 passed, 0 failed, 0 errors.\*\*



| Area | Tests |

|---|---|

| Health API | 1 |

| Upload service (unit) | 4 |

| Upload API (HTTP) | 3 |

| Queue | 3 |

| Worker lifecycle | 4 |

| Analysis business logic | 8 |

| Detectors | 20 |

| Jobs API (HTTP) | 10 |



`scripts/` also contains standalone manual verification scripts used

during development (e.g. `scripts/test\_plate.py`); these are not part of

the automated pytest suite and are run individually with `python -m

scripts.<name>` if needed for manual spot-checking.



\## Known Limitations



\- \*\*Photo-of-photo detection is an untuned heuristic.\*\* Its scoring

&#x20; weights and threshold were set as a reasonable first pass but have not

&#x20; been validated against real labeled "photo of a photo" sample images.

&#x20; Treat its output with caution; recalibration with real test data is

&#x20; recommended before relying on it.

\- \*\*OCR accuracy depends entirely on Tesseract\*\* and image quality; no

&#x20; custom text-recognition model is used. Number-plate extraction is

&#x20; correspondingly limited by OCR quality.

\- \*\*The job queue is in-process (`asyncio.Queue`), not distributed.\*\* If

&#x20; the application process restarts, any jobs still in the queue (not yet

&#x20; picked up by the worker) are lost; `PENDING` jobs already committed to

&#x20; the database are not automatically resumed.

\- \*\*Duplicate detection compares against every prior completed job\*\* on

&#x20; each upload (O(n) hash comparisons per upload), which will not scale

&#x20; indefinitely with job history size.

\- \*\*Docker is not implemented.\*\* This was evaluated against the assignment

&#x20; requirements and, since Docker was not confirmed as an explicit

&#x20; requirement or scored bonus item, it was intentionally not built to

&#x20; avoid speculative, unrequested work.



\## Production Considerations



\- Move the job queue to a durable, distributed system (e.g. Redis-backed

&#x20; queue or a task broker) if horizontal scaling or crash-resilience is

&#x20; required.

\- Add structured logging and monitoring around the worker loop and

&#x20; analysis pipeline for production observability.

\- Review and harden CORS configuration if the frontend is ever served

&#x20; from a different origin than the API.

\- Consider rate-limiting the upload endpoint.

