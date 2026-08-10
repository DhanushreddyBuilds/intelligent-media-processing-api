import numpy as np
import pytest
from PIL import Image

from app.analysis.detectors.blur import calculate_blur_score
from app.analysis.detectors.brightness import calculate_brightness_score
from app.analysis.detectors.duplicate import (
    are_duplicates,
    calculate_hash_distance,
    calculate_perceptual_hash,
)
from app.analysis.detectors.plate import (
    extract_plate_candidates,
    find_valid_plate,
    is_valid_indian_plate,
    normalize_plate_candidate,
)


def create_image(path, color, size=(200, 200)):
    image = Image.new("RGB", size, color)
    image.save(path)


def test_blur_score_sharp_image_is_positive(tmp_path):
    image_path = tmp_path / "sharp.jpg"

    array = np.zeros((200, 200), dtype=np.uint8)
    array[:, ::2] = 255

    Image.fromarray(array).save(image_path)

    score = calculate_blur_score(str(image_path))

    assert score > 0


def test_blur_score_rejects_missing_image():
    with pytest.raises(ValueError, match="Unable to read image"):
        calculate_blur_score("does-not-exist.jpg")


def test_brightness_score_for_dark_image(tmp_path):
    image_path = tmp_path / "dark.jpg"

    create_image(image_path, (0, 0, 0))

    score = calculate_brightness_score(str(image_path))

    assert score == pytest.approx(0.0)


def test_brightness_score_for_bright_image(tmp_path):
    image_path = tmp_path / "bright.jpg"

    create_image(image_path, (255, 255, 255))

    score = calculate_brightness_score(str(image_path))

    assert score == pytest.approx(255.0)


def test_brightness_score_rejects_missing_image():
    with pytest.raises(ValueError, match="Unable to read image"):
        calculate_brightness_score("does-not-exist.jpg")


def test_identical_images_have_zero_hash_distance(tmp_path):
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"

    create_image(first_path, (120, 120, 120))
    create_image(second_path, (120, 120, 120))

    first_hash = calculate_perceptual_hash(str(first_path))
    second_hash = calculate_perceptual_hash(str(second_path))

    assert calculate_hash_distance(first_hash, second_hash) == 0
    assert are_duplicates(first_hash, second_hash)


def test_duplicate_detection_rejects_different_images(tmp_path):
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"

    create_image(first_path, (0, 0, 0))
    create_image(second_path, (255, 255, 255))

    first_hash = calculate_perceptual_hash(str(first_path))
    second_hash = calculate_perceptual_hash(str(second_path))

    assert not are_duplicates(
        first_hash,
        second_hash,
        threshold=0,
    )


def test_perceptual_hash_rejects_missing_image():
    with pytest.raises(ValueError, match="Image does not exist"):
        calculate_perceptual_hash("does-not-exist.jpg")


def test_plate_normalization():
    assert normalize_plate_candidate("KA 01-AB 1234") == "KA01AB1234"


@pytest.mark.parametrize(
    "plate",
    [
        "KA01AB1234",
        "MH12DE1432",
        "DL01CA1234",
        "TN38BZ5678",
    ],
)
def test_valid_indian_plates(plate):
    assert is_valid_indian_plate(plate)


@pytest.mark.parametrize(
    "plate",
    [
        "INVALID123",
        "PUNEFCROAD",
        "123456",
        "",
    ],
)
def test_invalid_indian_plates(plate):
    assert not is_valid_indian_plate(plate)


def test_plate_candidate_extraction():
    text = "Vehicle number appears to be KA01AB1234"

    candidates = extract_plate_candidates(text)

    assert "KA01AB1234" in candidates


def test_find_valid_plate():
    text = "Random text KA01AB1234 more text"

    assert find_valid_plate(text) == "KA01AB1234"


def test_find_valid_plate_returns_none_when_not_found():
    text = "No vehicle registration number here"

    assert find_valid_plate(text) is None