from pathlib import Path

import cv2


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

    source = image_files[0]

    image = cv2.imread(str(source))

    if image is None:
        print(f"Unable to read {source}")
        return

    output_path = upload_directory / "blur_test_reference.jpg"

    blurred = cv2.GaussianBlur(
        image,
        (31, 31),
        0,
    )

    cv2.imwrite(
        str(output_path),
        blurred,
    )

    print(f"Source image: {source.name}")
    print(f"Blurred image: {output_path.name}")


if __name__ == "__main__":
    main()