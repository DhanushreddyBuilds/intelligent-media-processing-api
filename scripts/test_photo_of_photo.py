from pathlib import Path

from app.analysis.detectors.photo_of_photo import (
    calculate_photo_of_photo_signals,
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

    signals = calculate_photo_of_photo_signals(
        str(image_path)
    )

    print("=" * 60)
    print(f"Image: {image_path.name}")
    print(f"Resolution: {signals.width} × {signals.height}")
    print(
        f"Texture score: "
        f"{signals.texture_score:.4f}"
    )
    print(
        f"High-frequency score: "
        f"{signals.high_frequency_score:.2f}"
    )
    print(
        f"Edge density: "
        f"{signals.edge_density:.4f}"
    )


if __name__ == "__main__":
    main()