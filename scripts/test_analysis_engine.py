from sqlalchemy import select

from app.analysis.engine import analysis_engine
from app.db.database import SessionLocal
from app.db.models import ProcessingJob


def main() -> None:
    db = SessionLocal()

    try:
        job = db.scalar(
            select(ProcessingJob)
            .order_by(
                ProcessingJob.created_at.desc()
            )
        )

        if job is None:
            print("No processing jobs found.")
            return

        print(
            f"Testing analysis engine with job: "
            f"{job.id}"
        )

        result = analysis_engine.analyze(
            db=db,
            job=job,
        )

        print("\nAnalysis completed.")
        print(f"Result ID: {result.id}")
        print(f"Job ID: {result.job_id}")
        print(
            f"Blur score: "
            f"{result.blur_score}"
        )
        print(
            f"Brightness score: "
            f"{result.brightness_score}"
        )
        print(
            f"Duplicate: "
            f"{result.duplicate_detected}"
        )
        print(
            f"OCR text available: "
            f"{bool(result.ocr_text)}"
        )
        print(
            f"Number plate: "
            f"{result.number_plate}"
        )
        print(
            f"Plate valid: "
            f"{result.plate_valid}"
        )
        print(
            f"Screenshot: "
            f"{result.screenshot_detected}"
        )
        print(
            f"Photo-of-photo: "
            f"{result.photo_of_photo_detected}"
        )
        print(
            f"Issues: "
            f"{result.issues}"
        )
        print(
            f"Confidence: "
            f"{result.confidence}"
        )
        print(
            f"Analyzed at: "
            f"{result.analyzed_at}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()