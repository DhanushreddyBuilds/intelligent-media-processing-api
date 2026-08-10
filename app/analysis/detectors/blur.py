import cv2
import numpy as np


def calculate_blur_score(image_path: str) -> float:
    """
    Calculate image sharpness using the variance
    of the Laplacian.

    Higher values generally indicate a sharper image.
    Lower values generally indicate a blurrier image.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Unable to read image: {image_path}"
        )

    grayscale = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    laplacian = cv2.Laplacian(
        grayscale,
        cv2.CV_64F,
    )

    score = float(laplacian.var())

    return score
