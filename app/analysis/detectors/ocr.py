import re

import cv2
import pytesseract


def preprocess_for_ocr(image_path: str):
    """
    Prepare an image for OCR using OpenCV.
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

    # Increase resolution for OCR.
    upscaled = cv2.resize(
        grayscale,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC,
    )

    # Improve local contrast.
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(upscaled)

    # Light noise reduction.
    denoised = cv2.GaussianBlur(
        enhanced,
        (3, 3),
        0,
    )

    return denoised


def clean_ocr_text(text: str) -> str:
    """
    Normalize OCR output while preserving readable text.
    """

    text = text.upper()

    # Normalize common OCR whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_text(image_path: str) -> str:
    """
    Run Tesseract OCR on an image and return cleaned text.
    """

    processed_image = preprocess_for_ocr(
        image_path
    )

    config = "--oem 3 --psm 6"

    text = pytesseract.image_to_string(
        processed_image,
        config=config,
    )

    return clean_ocr_text(text)