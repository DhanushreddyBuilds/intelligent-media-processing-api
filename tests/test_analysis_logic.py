import pytest
from types import SimpleNamespace

from app.analysis.engine import AnalysisEngine


def test_build_issues_detects_blur():
    engine = AnalysisEngine()

    issues = engine._build_issues(
        blur_score=50,
        brightness_score=100,
        duplicate_detected=False,
        plate_valid=False,
        screenshot_detected=False,
        photo_signals=SimpleNamespace(
            photo_of_photo_detected=False
        ),
    )

    assert issues == "Image appears blurry"


def test_build_issues_detects_multiple_issues():
    engine = AnalysisEngine()

    issues = engine._build_issues(
        blur_score=50,
        brightness_score=250,
        duplicate_detected=True,
        plate_valid=False,
        screenshot_detected=True,
        photo_signals=SimpleNamespace(
            photo_of_photo_detected=True
        ),
    )

    assert "Image appears blurry" in issues
    assert "Image appears overexposed" in issues
    assert "Duplicate image detected" in issues
    assert "Image may be a screenshot" in issues
    assert "Image may be a photo of a photo/screen" in issues


def test_build_issues_detects_dark_image():
    engine = AnalysisEngine()

    issues = engine._build_issues(
        blur_score=500,
        brightness_score=20,
        duplicate_detected=False,
        plate_valid=False,
        screenshot_detected=False,
        photo_signals=SimpleNamespace(
            photo_of_photo_detected=False
        ),
    )

    assert issues == "Image appears too dark"


def test_build_issues_returns_empty_for_good_image():
    engine = AnalysisEngine()

    issues = engine._build_issues(
        blur_score=500,
        brightness_score=120,
        duplicate_detected=False,
        plate_valid=True,
        screenshot_detected=False,
        photo_signals=SimpleNamespace(
            photo_of_photo_detected=False
        ),
    )

    assert issues == ""


def test_confidence_for_clean_image():
    engine = AnalysisEngine()

    confidence = engine._calculate_confidence(
        blur_score=500,
        brightness_score=120,
        duplicate_detected=False,
        screenshot_detected=False,
        photo_of_photo_detected=False,
    )

    assert confidence == 1.0


def test_confidence_decreases_for_blur():
    engine = AnalysisEngine()

    confidence = engine._calculate_confidence(
        blur_score=50,
        brightness_score=120,
        duplicate_detected=False,
        screenshot_detected=False,
        photo_of_photo_detected=False,
    )

    assert confidence == 0.85


def test_confidence_decreases_for_multiple_problems():
    engine = AnalysisEngine()

    confidence = engine._calculate_confidence(
        blur_score=50,
        brightness_score=20,
        duplicate_detected=True,
        screenshot_detected=True,
        photo_of_photo_detected=True,
    )

    assert confidence == pytest.approx(0.45)


def test_confidence_never_goes_below_zero():
    engine = AnalysisEngine()

    confidence = engine._calculate_confidence(
        blur_score=0,
        brightness_score=0,
        duplicate_detected=True,
        screenshot_detected=True,
        photo_of_photo_detected=True,
    )

    assert confidence >= 0.0