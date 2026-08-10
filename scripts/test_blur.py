from pathlib import Path

from app.analysis.detectors.blur import calculate_blur_score


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
    ]

    if not image_files:
        print("No images found in uploads/")
        return

    for image_path in image_files:
        score = calculate_blur_score(
            str(image_path)
        )

        print(
            f"{image_path.name}: "
            f"blur_score={score:.2f}"
        )


if __name__ == "__main__":
    main()