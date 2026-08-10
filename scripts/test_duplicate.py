from pathlib import Path

from app.analysis.detectors.duplicate import (
    are_duplicates,
    calculate_hash_distance,
    calculate_perceptual_hash,
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

    if len(image_files) < 2:
        print("At least two images are required.")
        return

    hashes = {}

    for image_path in image_files:
        image_hash = calculate_perceptual_hash(
            str(image_path)
        )

        hashes[image_path.name] = image_hash

        print(
            f"{image_path.name}: "
            f"pHash={image_hash}"
        )

    print("\nPairwise comparison:\n")

    first_name = image_files[0].name
    first_hash = hashes[first_name]

    for image_path in image_files[1:]:
        second_name = image_path.name
        second_hash = hashes[second_name]

        distance = calculate_hash_distance(
            first_hash,
            second_hash,
        )

        duplicate = are_duplicates(
            first_hash,
            second_hash,
        )

        print(
            f"{first_name} ↔ {second_name}"
        )
        print(f"  distance: {distance}")
        print(f"  duplicate: {duplicate}")
        print()


if __name__ == "__main__":
    main()