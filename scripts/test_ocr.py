from pathlib import Path

from app.analysis.detectors.ocr import extract_text


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

    for image_path in image_files:
        try:
            text = extract_text(
                str(image_path)
            )

            print("=" * 60)
            print(f"Image: {image_path.name}")
            print(f"OCR: {text or '[NO TEXT DETECTED]'}")

        except Exception as exc:
            print("=" * 60)
            print(f"Image: {image_path.name}")
            print(f"OCR ERROR: {exc}")


if __name__ == "__main__":
    main()