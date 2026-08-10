from pathlib import Path

from app.analysis.detectors.ocr import extract_text
from app.analysis.detectors.screenshot import (
    calculate_screenshot_analysis,
)


def main() -> None:
    upload_directory = Path("uploads")

    image_files = [
        path
        for path in upload_directory.iterdir()
        if path.suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }
        and path.name != "blur_test_reference.jpg"
    ]

    if not image_files:
        print("No images found in uploads/")
        return

    image_path = image_files[0]

    ocr_text = extract_text(
        str(image_path)
    )

    analysis = calculate_screenshot_analysis(
        str(image_path),
        ocr_text,
    )

    print("=" * 60)
    print(f"Image: {image_path.name}")
    print(f"Resolution: {analysis.width} × {analysis.height}")
    print(
        f"Aspect ratio: "
        f"{analysis.aspect_ratio:.3f}"
    )
    print(
        f"Text density: "
        f"{analysis.text_density:.4f}"
    )
    print(
        f"Edge density: "
        f"{analysis.edge_density:.4f}"
    )
    print(
        f"Screen ratio score: "
        f"{analysis.screen_ratio_score:.4f}"
    )
    print(
        f"Screenshot score: "
        f"{analysis.screenshot_score:.4f}"
    )
    print(
        f"Screenshot detected: "
        f"{analysis.screenshot_detected}"
    )


if __name__ == "__main__":
    main()