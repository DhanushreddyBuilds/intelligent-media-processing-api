from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PhotoOfPhotoSignals:
    width: int
    height: int
    texture_score: float
    high_frequency_score: float
    edge_density: float
    photo_of_photo_score: float
    photo_of_photo_detected: bool


def calculate_photo_of_photo_signals(
    image_path: str,
) -> PhotoOfPhotoSignals:

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Unable to read image: {image_path}"
        )

    height, width = image.shape[:2]

    grayscale = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    # Edge structure.
    edges = cv2.Canny(
        grayscale,
        100,
        200,
    )

    edge_density = float(
        cv2.countNonZero(edges)
        / (width * height)
    )

    # High-frequency detail using Laplacian.
    laplacian = cv2.Laplacian(
        grayscale,
        cv2.CV_64F,
    )

    high_frequency_score = float(
        laplacian.var()
    )

    # Local texture estimate.
    local_mean = cv2.GaussianBlur(
        grayscale,
        (7, 7),
        0,
    )

    texture = cv2.absdiff(
        grayscale,
        local_mean,
    )

    texture_score = float(
        texture.mean()
    )

    # -------------------------------------------------
    # NOTE: First-pass heuristic, NOT yet tuned against
    # real "photo of photo" sample data. Divisors and the
    # 0.65 threshold below are reasonable starting guesses,
    # mirroring the style of screenshot_analysis's scoring,
    # but should be recalibrated once real test images are
    # available. Treat this detector's output with caution
    # until it has been validated. (Flagged during Phase 7.)
    # -------------------------------------------------

    texture_signal = min(
        1.0,
        texture_score / 25.0,
    )

    frequency_signal = min(
        1.0,
        high_frequency_score / 3000.0,
    )

    edge_signal = min(
        1.0,
        edge_density / 0.20,
    )

    photo_of_photo_score = (
        0.45 * texture_signal
        + 0.40 * frequency_signal
        + 0.15 * edge_signal
    )

    photo_of_photo_detected = (
        photo_of_photo_score >= 0.65
    )

    return PhotoOfPhotoSignals(
        width=width,
        height=height,
        texture_score=texture_score,
        high_frequency_score=high_frequency_score,
        edge_density=edge_density,
        photo_of_photo_score=photo_of_photo_score,
        photo_of_photo_detected=photo_of_photo_detected,
    )