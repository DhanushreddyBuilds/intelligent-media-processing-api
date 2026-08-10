from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.analysis.detectors.blur import (
    calculate_blur_score,
)
from app.analysis.detectors.brightness import (
    calculate_brightness_score,
)
from app.analysis.detectors.duplicate import (
    are_duplicates,
    calculate_perceptual_hash,
)
from app.analysis.detectors.ocr import (
    extract_text,
)
from app.analysis.detectors.plate import (
    find_valid_plate,
)
from app.analysis.detectors.screenshot import (
    calculate_screenshot_analysis,
)
from app.analysis.detectors.photo_of_photo import (
    calculate_photo_of_photo_signals,
)
from app.db.models import (
    AnalysisResult,
    ProcessingJob,
    ProcessingStatus,
)


class AnalysisEngine:
    """
    Orchestrates all media analysis detectors.

    The engine is intentionally independent from the worker.
    The worker only asks the engine to analyze a job.
    """

    BLUR_THRESHOLD = 100.0
    DUPLICATE_THRESHOLD = 5

    def analyze(
        self,
        db: Session,
        job: ProcessingJob,
    ) -> AnalysisResult:
        """
        Run all analysis detectors for a processing job
        and return a persisted AnalysisResult.
        """

        image_path = Path(job.file_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image file not found: {image_path}"
            )

        # -------------------------------------------------
        # 1. Blur
        # -------------------------------------------------

        blur_score = calculate_blur_score(
            str(image_path)
        )

        # -------------------------------------------------
        # 2. Brightness
        # -------------------------------------------------

        brightness_score = calculate_brightness_score(
            str(image_path)
        )

        # -------------------------------------------------
        # 3. OCR
        # -------------------------------------------------

        ocr_text = extract_text(
            str(image_path)
        )

        # -------------------------------------------------
        # 4. Number plate
        # -------------------------------------------------

        number_plate = find_valid_plate(
            ocr_text
        )

        plate_valid = (
            number_plate is not None
        )

        # -------------------------------------------------
        # 5. Screenshot
        # -------------------------------------------------

        screenshot_analysis = (
            calculate_screenshot_analysis(
                str(image_path),
                ocr_text,
            )
        )

        # -------------------------------------------------
        # 6. Photo-of-photo signals
        # -------------------------------------------------

        photo_signals = (
            calculate_photo_of_photo_signals(
                str(image_path)
            )
        )

        # -------------------------------------------------
        # 7. Duplicate detection
        # -------------------------------------------------

        duplicate_detected = (
            self._check_duplicate(
                db=db,
                job=job,
                current_image_path=image_path,
            )
        )

        # -------------------------------------------------
        # 8. Issues
        # -------------------------------------------------

        issues = self._build_issues(
            blur_score=blur_score,
            brightness_score=brightness_score,
            duplicate_detected=duplicate_detected,
            plate_valid=plate_valid,
            screenshot_detected=(
                screenshot_analysis.screenshot_detected
            ),
            photo_signals=photo_signals,
        )

        # -------------------------------------------------
        # 9. Confidence
        # -------------------------------------------------

        confidence = self._calculate_confidence(
            blur_score=blur_score,
            brightness_score=brightness_score,
            duplicate_detected=duplicate_detected,
            screenshot_detected=(
                screenshot_analysis.screenshot_detected
            ),
            photo_of_photo_detected=(
                photo_signals.photo_of_photo_detected
            ),
        )

        # -------------------------------------------------
        # 10. Persist result
        # -------------------------------------------------

        result = AnalysisResult(
            job_id=job.id,
            blur_score=blur_score,
            brightness_score=brightness_score,
            duplicate_detected=duplicate_detected,
            ocr_text=ocr_text or None,
            number_plate=number_plate,
            plate_valid=plate_valid,
            screenshot_detected=(
                screenshot_analysis.screenshot_detected
            ),
            photo_of_photo_detected=(
                photo_signals.photo_of_photo_detected
            ),
            issues=issues or None,
            confidence=confidence,
            analyzed_at=datetime.now(timezone.utc),
        )

        db.add(result)
        db.commit()
        db.refresh(result)

        return result

    def _check_duplicate(
        self,
        db: Session,
        job: ProcessingJob,
        current_image_path: Path,
    ) -> bool:
        """
        Compare the current image against previously
        processed images.

        The first version intentionally compares against
        existing completed jobs.
        """

        current_hash = calculate_perceptual_hash(
            str(current_image_path)
        )

        previous_jobs = (
            db.query(ProcessingJob)
            .filter(
                ProcessingJob.id != job.id,
                ProcessingJob.status == ProcessingStatus.COMPLETED,
            )
            .all()
        )

        for previous_job in previous_jobs:
            previous_path = Path(
                previous_job.file_path
            )

            if not previous_path.exists():
                continue

            previous_hash = (
                calculate_perceptual_hash(
                    str(previous_path)
                )
            )

            if are_duplicates(
                current_hash,
                previous_hash,
                threshold=self.DUPLICATE_THRESHOLD,
            ):
                return True

        return False

    def _build_issues(
        self,
        blur_score: float,
        brightness_score: float,
        duplicate_detected: bool,
        plate_valid: bool,
        screenshot_detected: bool,
        photo_signals,
    ) -> str:
        """
        Build a human-readable list of detected issues.
        """

        issues: list[str] = []

        if blur_score < self.BLUR_THRESHOLD:
            issues.append(
                "Image appears blurry"
            )

        if brightness_score < 40:
            issues.append(
                "Image appears too dark"
            )

        elif brightness_score > 220:
            issues.append(
                "Image appears overexposed"
            )

        if duplicate_detected:
            issues.append(
                "Duplicate image detected"
            )

        if screenshot_detected:
            issues.append(
                "Image may be a screenshot"
            )

        if photo_signals.photo_of_photo_detected:
            issues.append(
                "Image may be a photo of a photo/screen"
            )

        return "; ".join(issues)

    def _calculate_confidence(
        self,
        blur_score: float,
        brightness_score: float,
        duplicate_detected: bool,
        screenshot_detected: bool,
        photo_of_photo_detected: bool,
    ) -> float:
        """
        Calculate an overall analysis confidence.

        This is an engineering confidence score for the
        analysis pipeline, not a statistical probability.
        """

        confidence = 1.0

        if blur_score < self.BLUR_THRESHOLD:
            confidence -= 0.15

        if (
            brightness_score < 40
            or brightness_score > 220
        ):
            confidence -= 0.10

        if duplicate_detected:
            confidence -= 0.10

        if screenshot_detected:
            confidence -= 0.10

        if photo_of_photo_detected:
            confidence -= 0.10

        return max(
            0.0,
            min(1.0, confidence),
        )


analysis_engine = AnalysisEngine()