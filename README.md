# Intelligent Media Processing API

An asynchronous backend service for image upload, background processing, automated image-quality/content analysis, and result persistence. The project includes a lightweight dashboard for uploading images, monitoring processing status, viewing history, and inspecting analysis results.

**Live deployment:** https://intelligent-media-processing-api-du4y.onrender.com

---

## 1. Problem Statement

Manually reviewing uploaded images for quality and content issues such as blur, duplicates, screenshots, recaptured photos, and unreadable text does not scale well.

This project provides an asynchronous image-processing pipeline:

1. Accept an image through a REST API.
2. Validate and persist the upload.
3. Create a processing job with a unique ID.
4. Return the processing ID immediately.
5. Process the image in a background worker.
6. Run multiple deterministic/heuristic analysis checks.
7. Persist the analysis result.
8. Expose job status and results through REST APIs.
9. Display the same information through the dashboard.

The goal is a practical, explainable take-home implementation rather than claiming perfect ML accuracy.

---

## 2. Features

- Asynchronous image upload and background processing
- Unique processing ID for every upload
- Job lifecycle: `PENDING` -> `PROCESSING` -> `COMPLETED` / `FAILED`
- PostgreSQL persistence
- Blur detection using Laplacian variance
- Brightness detection using mean pixel intensity
- Duplicate detection using perceptual hashing
- OCR using Tesseract
- Indian vehicle number-plate candidate extraction and validation
- Screenshot detection using image heuristics
- Photo-of-photo detection using image heuristics
- Per-job confidence scoring
- Failure reason persistence
- Paginated processing history
- Analytics summary API
- Static dashboard served by FastAPI
- Docker and Docker Compose support
- Automated pytest suite
- Live deployment on Render

---

## 3. Architecture

```text
                    Browser / Client
                           |
                           v
              +-------------------------+
              | FastAPI Application     |
              |                         |
              | Upload API              |
              | Jobs API                |
              | Analytics API           |
              | Health API              |
              +-----------+-------------+
                          |
             +------------+-------------+
             |                          |
             v                          v
      PostgreSQL Database         asyncio.Queue
             |                          |
             |                          v
             |                Background Worker
             |                          |
             |                          v
             |                    AnalysisEngine
             |                          |
             |        +-----------------+------------------+
             |        |       |       |       |      |    |
             |        v       v       v       v      v    v
             |      Blur  Brightness Duplicate OCR  Plate Screenshot
             |                                                  |
             |                                                  v
             |                                         Photo-of-photo
             |                                                  |
             +-------------------- AnalysisResult <-------------+
```

### Queue strategy

The current implementation uses a single in-process `asyncio.Queue`.

A background worker is created as an `asyncio` task during FastAPI application startup using the application's `lifespan` context. It consumes processing IDs from the queue and processes jobs sequentially.

This was intentionally chosen for the take-home assignment because it provides genuine asynchronous behavior without introducing unnecessary distributed infrastructure.

**Trade-off:** an in-process queue is not durable across process restarts and is not suitable for horizontal scaling. A production-scale implementation would use a durable distributed queue/task broker.

---

## 4. End-to-End Processing Flow

### Upload

```text
POST /api/v1/images
        |
        v
Validate file type and size
        |
        v
Validate that the file is a readable image
        |
        v
Store generated filename under uploads/
        |
        v
Create ProcessingJob(PENDING)
        |
        v
Enqueue processing ID
        |
        v
Return processing_id immediately
```

### Background processing

```text
PENDING
   |
   v
PROCESSING
   |
   v
AnalysisEngine
   |
   +--> Blur
   +--> Brightness
   +--> Duplicate
   +--> OCR
   +--> Number plate
   +--> Screenshot
   +--> Photo-of-photo
   +--> Confidence
   |
   v
Persist AnalysisResult
   |
   v
COMPLETED
```

If processing raises an exception:

```text
PROCESSING
    |
    v
FAILED
    |
    +--> failed_at
    +--> failure_reason
```

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Database | PostgreSQL |
| ORM / DB access | SQLAlchemy 2.0, psycopg 3 |
| Configuration | Pydantic Settings |
| Image processing | OpenCV, Pillow, imagehash |
| OCR | pytesseract + Tesseract OCR |
| Queue | Python asyncio.Queue |
| Frontend | HTML, CSS, vanilla JavaScript |
| Testing | pytest, pytest-asyncio, httpx |
| Containerization | Docker, Docker Compose |
| Deployment | Render |

---

## 6. Project Structure

```text
intelligent-media/
├── app/
│   ├── analysis/
│   │   ├── detectors/
│   │   │   ├── blur.py
│   │   │   ├── brightness.py
│   │   │   ├── duplicate.py
│   │   │   ├── ocr.py
│   │   │   ├── plate.py
│   │   │   ├── photo_of_photo.py
│   │   │   └── screenshot.py
│   │   ├── engine.py
│   │   └── models.py
│   ├── api/v1/
│   │   ├── analytics.py
│   │   ├── images.py
│   │   ├── jobs.py
│   │   └── router.py
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── database.py
│   │   └── models.py
│   ├── schemas/
│   ├── services/
│   │   └── upload_service.py
│   ├── workers/
│   │   ├── queue.py
│   │   └── worker.py
│   └── main.py
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── scripts/
├── tests/
├── uploads/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 7. Image Analysis Pipeline

Each uploaded image is passed through the analysis engine.

### 7.1 Blur

Uses Laplacian variance as a focus/sharpness signal.

A value below the configured threshold is reported as a blurry image.

### 7.2 Brightness

Calculates mean pixel intensity.

Images outside the configured brightness range are flagged as too dark or overexposed.

### 7.3 Duplicate detection

Uses perceptual hashing and compares the hash against previously completed jobs.

The current implementation uses a Hamming-distance threshold of `<= 5`.

### 7.4 OCR

Uses Tesseract through `pytesseract` to extract readable text.

OCR quality depends strongly on image resolution, focus, lighting, orientation, and text layout.

### 7.5 Number-plate validation

OCR output is searched for candidate vehicle registration text and matched against a simplified Indian number-plate pattern.

This is a validation heuristic, not a dedicated trained number-plate recognition model.

### 7.6 Screenshot detection

Uses a combination of:

- aspect-ratio similarity to common screen ratios
- OCR/text density
- edge density

### 7.7 Photo-of-photo detection

Uses image texture, high-frequency/Laplacian behavior, and edge-density heuristics.

The detector is explicitly treated as a first-pass heuristic and has not been calibrated against a large labelled dataset.

### 7.8 Confidence score

The current confidence score starts at `1.0` and applies fixed deductions for detected issues. The value is clamped to `[0, 1]`.

The score is intended as an interpretable heuristic indicator rather than a statistically calibrated probability.

---

## 8. API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| POST | `/api/v1/images` | Upload image and create a processing job |
| GET | `/api/v1/jobs` | Paginated processing history |
| GET | `/api/v1/jobs/{processing_id}` | Job status and lifecycle timestamps |
| GET | `/api/v1/jobs/{processing_id}/result` | Completed analysis result |
| GET | `/api/v1/analytics/summary` | Aggregate job statistics |

Interactive Swagger/OpenAPI documentation is available at:

```text
/docs
```

when the application is running.

---

## 9. Example API Flow

### Upload

```bash
curl -X POST http://localhost:8000/api/v1/images \
  -F "file=@example.jpg"
```

Example response:

```json
{
  "processing_id": "f5a96869-e85e-4f3f-ae4c-01389567ac25",
  "status": "pending",
  "message": "Image accepted for processing"
}
```

### Check status

```bash
curl http://localhost:8000/api/v1/jobs/{processing_id}
```

Example:

```json
{
  "processing_id": "f5a96869-e85e-4f3f-ae4c-01389567ac25",
  "status": "completed"
}
```

### Get result

```bash
curl http://localhost:8000/api/v1/jobs/{processing_id}/result
```

A completed result contains fields such as:

```json
{
  "processing_id": "f5a96869-e85e-4f3f-ae4c-01389567ac25",
  "status": "completed",
  "analysis": {
    "blur_score": 1.9868,
    "brightness_score": 116.7149,
    "duplicate_detected": true,
    "ocr_text": ": ES . 4 < —",
    "number_plate": null,
    "plate_valid": false,
    "screenshot_detected": false,
    "photo_of_photo_detected": false,
    "issues": "Image appears blurry; Duplicate image detected",
    "confidence": 0.75
  }
}
```

The values above are from an actual local Docker integration test, not expected/mock output.

---

## 10. Frontend

The frontend is a static HTML/CSS/JavaScript dashboard served directly by FastAPI.

It provides:

- Dashboard summary
- Image upload
- Processing-status polling
- Analysis result display
- Paginated processing history
- Result viewing for individual jobs

There is no separate frontend build system.

---

## 11. Database

PostgreSQL stores the processing lifecycle and analysis results.

The main domain entities are:

- `ProcessingJob`
- `AnalysisResult`

A job records lifecycle timestamps including creation, start, completion, and failure information.

This separates job state from analysis output and allows the API and dashboard to retrieve historical processing information.

---

## 12. Local Setup

### Prerequisites

For a native Python setup:

- Python 3.12
- PostgreSQL
- Tesseract OCR

Tesseract must be installed separately from the Python `pytesseract` package.

### Environment

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configure:

```text
APP_NAME=Intelligent Media Processing API
APP_VERSION=1.0.0
ENVIRONMENT=development

DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/intelligent_media

UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=10
```

Create the application database:

```bash
psql -U postgres -c "CREATE DATABASE intelligent_media;"
```

Create the virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Initialize the schema:

```powershell
python scripts/init_db.py
```

Run the application:

```powershell
uvicorn app.main:app
```

Then open:

```text
Dashboard: http://127.0.0.1:8000
Swagger:   http://127.0.0.1:8000/docs
Health:    http://127.0.0.1:8000/health
```

---

## 13. Docker

The project includes a Dockerfile with the system dependencies required by the image-processing pipeline:

- Tesseract OCR
- `libgl1`
- `libglib2.0-0`

The Docker Compose setup includes:

- FastAPI application container
- PostgreSQL 16 container
- PostgreSQL named volume
- upload-directory bind mount

### Run with Docker Compose

PowerShell:

```powershell
$env:POSTGRES_PASSWORD="choose-a-local-password"
docker compose up --build
```

The `POSTGRES_PASSWORD` environment variable is intentionally supplied to Compose separately rather than added to the application's `.env`, because the application configuration uses strict Pydantic settings.

The application will be available at:

```text
http://localhost:8000
```

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
```

The Dockerized system was also verified end-to-end locally:

```text
upload
  -> PENDING
  -> background worker
  -> COMPLETED
  -> analysis result
```

---

## 14. Testing

The project uses pytest with an isolated PostgreSQL test database.

The automated test suite covers:

- Health API
- Upload service
- Upload API
- Queue behavior
- Worker lifecycle
- Analysis business logic
- Individual detectors
- Jobs API

The test database is separate from the development database.

Create it once:

```bash
psql -U postgres -c "CREATE DATABASE intelligent_media_test;"
```

Run the complete suite:

```powershell
python -m pytest -v
```

### Latest verified result

```text
53 passed, 1 warning
```

The single warning is a non-blocking SQLAlchemy deprecation warning related to `datetime.utcnow()`.

The important point is that the automated suite completed successfully with **53 passing tests and zero test failures/errors**.

---

## 15. Deployment

The application is deployed on Render.

**Live application:**

https://intelligent-media-processing-api-du4y.onrender.com

The deployed application was manually verified through the dashboard, including:

- Dashboard loading
- Image upload
- Background processing
- Processing history
- Completed analysis result display

The same API health endpoint is available at:

```text
/health
```

---

## 16. Engineering Decisions

### Why FastAPI?

FastAPI provides:

- clear REST API structure
- asynchronous application support
- automatic OpenAPI documentation
- straightforward integration with Python image-processing libraries

### Why PostgreSQL?

The application has structured entities and lifecycle state, making a relational database a natural fit.

PostgreSQL also provides clear transactional persistence for jobs and analysis results.

### Why an in-process queue?

The assignment requires asynchronous processing but does not require a distributed message broker.

`asyncio.Queue` keeps the implementation small and understandable while still separating request handling from image analysis.

For a production system with multiple replicas, a durable queue would be preferable.

### Why deterministic/heuristic checks?

The assignment prioritizes meaningful image-analysis checks rather than perfect ML accuracy.

Deterministic image-processing methods are:

- explainable
- inexpensive
- easy to test
- suitable for a focused take-home implementation

The system therefore reports limitations rather than presenting heuristic scores as guaranteed predictions.

---

## 17. Assumptions and Trade-offs

This implementation intentionally favors a small, understandable architecture over production-scale infrastructure.

### Intentional simplifications

- Uploaded files use local filesystem storage rather than object storage.
- The background queue is an in-process `asyncio.Queue`.
- Screenshot and photo-of-photo detection use heuristics rather than trained models.
- Number-plate extraction depends on OCR and a simplified validation pattern.
- Confidence is a deterministic score rather than a calibrated probability.

### Trade-offs

These choices reduce infrastructure complexity and make the complete pipeline easy to run locally and demonstrate.

The trade-off is that the current design is not intended for high-volume horizontal scaling or crash-resilient distributed processing.

---

## 18. Known Limitations

### OCR and number plates

OCR accuracy depends on Tesseract and the quality of the input image. Low-resolution, blurry, angled, or poorly lit text can produce incorrect or incomplete OCR output. Number-plate extraction is therefore also limited by OCR quality.

### Photo-of-photo detection

This is a first-pass heuristic. Its thresholds have not been calibrated against a large labelled dataset and should not be treated as a production-grade classifier.

### Screenshot detection

The screenshot detector is heuristic and may produce false positives/negatives for unusual layouts or aspect ratios.

### In-process queue

Jobs waiting in the in-memory queue are not durable across process restarts. A production deployment should use a durable distributed queue and explicit retry/dead-letter handling.

### Duplicate detection

Current duplicate detection compares against prior completed jobs, resulting in O(n) hash comparisons as history grows.

### Local uploads

The application currently stores uploaded images on local disk. Production-scale deployments would typically use object storage such as S3-compatible storage.

---

## 19. Scalability and Future Improvements

If this system were taken beyond the take-home scope, the next improvements would be:

1. Replace `asyncio.Queue` with a durable queue/task broker.
2. Add retry policies and a dead-letter queue.
3. Move uploads to object storage.
4. Add structured logging and centralized observability.
5. Add metrics for queue depth, processing latency, detector failures, and throughput.
6. Add rate limiting to the upload endpoint.
7. Improve duplicate detection with indexed perceptual hashes rather than scanning all previous jobs.
8. Calibrate image-quality thresholds using labelled datasets.
9. Replace heuristic plate detection with a dedicated detection/recognition model where accuracy requirements justify it.
10. Add horizontal worker scaling.

---

## 20. AI-Assisted Development Disclosure

AI tools were used during development as productivity and engineering-assistance tools.

They were used for:

- exploring implementation approaches
- accelerating boilerplate/code generation
- debugging suggestions
- reviewing implementation ideas
- improving documentation
- generating test ideas and edge cases

AI-generated output was **not treated as automatically correct**. The implementation was validated through direct execution, automated tests, API-level testing, Docker integration testing, and deployment verification.

Environment-specific issues required manual investigation and correction. Examples included Python/Pydantic configuration behavior, pytest import/configuration behavior, Docker/Compose environment configuration, and deployment integration issues.

The final architecture and implementation were evaluated against the assignment requirements and validated through the project's test suite and live application behavior.

The AI-assisted workflow was therefore:

```text
AI suggestion / generated implementation
        |
        v
Review against project requirements
        |
        v
Run locally
        |
        v
Test / debug
        |
        v
Correct implementation where required
        |
        v
Integration testing
        |
        v
Docker verification
        |
        v
Deployment verification
```

AI assistance accelerated implementation, but validation and final integration remained part of the engineering workflow.

---

## 21. Submission Evidence

The implementation has been validated through:

- **53 automated tests passing**
- Local Docker image build
- Docker Compose with PostgreSQL
- Docker health endpoint returning HTTP 200
- Docker upload -> background worker -> completed analysis
- Production deployment on Render
- Production dashboard upload/history/result flow

The repository is intended to remain reproducible through the documented local and Docker workflows.

---

## 22. Project Status

**Status: Complete take-home implementation**

The project covers the required asynchronous image-processing workflow, persistence, image-analysis pipeline, result APIs, automated testing, Dockerization, and live deployment while explicitly documenting the limitations and trade-offs of the current design.
