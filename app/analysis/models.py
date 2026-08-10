from dataclasses import dataclass, field


@dataclass
class AnalysisOutput:
    """
    Unified result produced by the image analysis engine.
    """

    blur_score: float | None = None
    brightness_score: float | None = None

    duplicate_detected: bool = False

    ocr_text: str | None = None

    number_plate: str | None = None
    plate_valid: bool | None = None

    screenshot_detected: bool = False
    photo_of_photo_detected: bool = False

    issues: list[str] = field(default_factory=list)

    confidence: float | None = None