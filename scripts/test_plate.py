from app.analysis.detectors.plate import (
    extract_plate_candidates,
    find_valid_plate,
    is_valid_indian_plate,
)


def main() -> None:
    test_plates = [
        "KA01AB1234",
        "MH12DE1432",
        "DL01CA1234",
        "TN38BZ5678",
        "INVALID123",
        "PUNEFCROAD",
    ]

    print("Validation tests:\n")

    for plate in test_plates:
        result = is_valid_indian_plate(plate)

        print(
            f"{plate:15} -> {result}"
        )

    print("\nOCR candidate extraction:\n")

    sample_text = """
    Vehicle registration:
    KA01AB1234
    """

    candidates = extract_plate_candidates(
        sample_text
    )

    print(f"Candidates: {candidates}")
    print(
        f"Valid plate: "
        f"{find_valid_plate(sample_text)}"
    )


if __name__ == "__main__":
    main()