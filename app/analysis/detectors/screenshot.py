from dataclasses import dataclass

import cv2


@dataclass
class ScreenshotAnalysis:
    width: int
    height: int
    aspect_ratio: float
    text_density: float
    edge_density: float
    screen_ratio_score: float
    screenshot_score: float
    screenshot_detected: bool


COMMON_SCREEN_RATIOS = {
    16 / 9,
    9 / 16,
    4 / 3,
    3 / 4,
    18 / 9,
    9 / 18,
    20 / 9,
    9 / 20,
}


def _ratio_similarity(
    aspect_ratio: float,
) -> float:
    """
    Return a score between 0 and 1 indicating
    how close the image is to a common screen ratio.
    """

    similarities = []

    for ratio in COMMON_SCREEN_RATIOS:
        difference = abs(
            aspect_ratio - ratio
        )

        similarity = max(
            0.0,
            1.0 - (difference / 0.08),
        )

        similarities.append(similarity)

    return max(similarities, default=0.0)


def calculate_screenshot_analysis(
    image_path: str,
    ocr_text: str = "",
) -> ScreenshotAnalysis:

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Unable to read image: {image_path}"
        )

    height, width = image.shape[:2]

    aspect_ratio = width / height

    grayscale = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    # Detect edges.
    edges = cv2.Canny(
        grayscale,
        100,
        200,
    )

    # Use the actual percentage of edge pixels.
    edge_density = float(
        cv2.countNonZero(edges)
        / (width * height)
    )

    # Approximate amount of OCR-readable content.
    text_characters = len(
        "".join(ocr_text.split())
    )

    # Normalize text density against image area.
    text_density = min(
        1.0,
        text_characters / 5000,
    )

    screen_ratio_score = _ratio_similarity(
        aspect_ratio
    )

    # Convert edge density into a bounded signal.
    edge_score = min(
        1.0,
        edge_density / 0.20,
    )

    # Weighted heuristic.
    screenshot_score = (
        0.30 * screen_ratio_score
        + 0.35 * text_density
        + 0.35 * edge_score
    )

    screenshot_detected = (
        screenshot_score >= 0.65
    )

    return ScreenshotAnalysis(
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        text_density=text_density,
        edge_density=edge_density,
        screen_ratio_score=screen_ratio_score,
        screenshot_score=screenshot_score,
        screenshot_detected=screenshot_detected,
    )