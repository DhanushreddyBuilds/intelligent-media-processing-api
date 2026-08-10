from pathlib import Path

import imagehash
from PIL import Image


def calculate_perceptual_hash(image_path: str) -> imagehash.ImageHash:
    """
    Generate a perceptual hash for an image.

    Perceptual hashes represent visual characteristics
    of an image rather than its filename or exact bytes.
    """

    path = Path(image_path)

    if not path.exists():
        raise ValueError(
            f"Image does not exist: {image_path}"
        )

    try:
        with Image.open(path) as image:
            return imagehash.phash(image)

    except Exception as exc:
        raise ValueError(
            f"Unable to calculate perceptual hash: {image_path}"
        ) from exc


def calculate_hash_distance(
    first_hash: imagehash.ImageHash,
    second_hash: imagehash.ImageHash,
) -> int:
    """
    Calculate the Hamming distance between two perceptual hashes.

    A distance of 0 means the perceptual hashes are identical.
    Smaller distances indicate greater visual similarity.
    """

    return first_hash - second_hash


def are_duplicates(
    first_hash: imagehash.ImageHash,
    second_hash: imagehash.ImageHash,
    threshold: int = 5,
) -> bool:
    """
    Determine whether two images are visually similar enough
    to be considered duplicates.

    The threshold is intentionally configurable.
    """

    distance = calculate_hash_distance(
        first_hash,
        second_hash,
    )

    return distance <= threshold