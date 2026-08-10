import cv2


def calculate_brightness_score(image_path: str) -> float:
    """
    Calculate the average grayscale brightness of an image.

    Returns a value between approximately 0 and 255.

    Lower values indicate darker images.
    Higher values indicate brighter images.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Unable to read image: {image_path}"
        )

    grayscale = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    return float(grayscale.mean())