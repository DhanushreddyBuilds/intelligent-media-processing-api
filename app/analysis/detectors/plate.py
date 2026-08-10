import re


INDIAN_PLATE_PATTERN = re.compile(
    r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$"
)

# Matches plate-shaped sequences directly (2 letters, 1-2 digits,
# 1-3 letters, 1-4 digits) allowing OCR-typical separators between
# the groups, instead of grabbing a broad free-form token that can
# swallow surrounding prose on a single line with no natural break.
PLATE_CANDIDATE_PATTERN = re.compile(
    r"[A-Z]{2}[\s\-.:_/|]*\d{1,2}[\s\-.:_/|]*"
    r"[A-Z]{1,3}[\s\-.:_/|]*\d{1,4}"
)


def normalize_plate_candidate(text: str) -> str:
    """
    Normalize OCR text for number-plate matching.
    """

    normalized = text.upper()

    # Remove common separators and whitespace.
    normalized = re.sub(
        r"[\s\-.:_/|]+",
        "",
        normalized,
    )

    # Keep only alphanumeric characters.
    normalized = re.sub(
        r"[^A-Z0-9]",
        "",
        normalized,
    )

    return normalized


def is_valid_indian_plate(candidate: str) -> bool:
    """
    Validate a candidate against a simplified
    Indian vehicle registration format.
    """

    normalized = normalize_plate_candidate(
        candidate
    )

    return bool(
        INDIAN_PLATE_PATTERN.fullmatch(
            normalized
        )
    )


def extract_plate_candidates(
    ocr_text: str,
) -> list[str]:
    """
    Extract possible Indian registration numbers
    from OCR text.

    OCR frequently inserts spaces or punctuation,
    so we match the shape of a plate directly
    (letters/digits/letters/digits with optional
    separators between groups) rather than
    extracting broad free-form tokens, which can
    otherwise swallow surrounding prose on a
    single line with no natural line break.
    """

    normalized_text = ocr_text.upper()

    tokens = PLATE_CANDIDATE_PATTERN.findall(
        normalized_text
    )

    candidates: list[str] = []

    for token in tokens:
        candidate = normalize_plate_candidate(
            token
        )

        if 6 <= len(candidate) <= 13:
            candidates.append(candidate)

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(candidates))


def find_valid_plate(
    ocr_text: str,
) -> str | None:
    """
    Find the first OCR candidate that matches
    the simplified Indian registration format.
    """

    candidates = extract_plate_candidates(
        ocr_text
    )

    for candidate in candidates:
        if is_valid_indian_plate(candidate):
            return candidate

    return None