# food_recognition.py — Fixed version
# Fixes: missing `types` import, wrong error-check logic, added fallback

from google.cloud import vision


def classify_food(image_file: str) -> list[str]:
    """
    Uses Google Cloud Vision API to detect food-related labels in an image.

    Args:
        image_file: Path to a local image file.

    Returns:
        List of detected food item strings, or empty list on failure.
    """
    FOOD_KEYWORDS = {
        "pizza", "burger", "hamburger", "sushi", "pasta", "salad",
        "sandwich", "taco", "noodle", "soup", "steak", "chicken",
        "bread", "cake", "dessert", "fruit", "vegetable", "rice",
        "ramen", "curry", "waffle", "pancake", "cereal", "seafood",
        "shrimp", "salmon", "donut", "cookie", "pie", "hot dog",
    }

    try:
        client = vision.ImageAnnotatorClient()

        with open(image_file, "rb") as f:
            content = f.read()

        image = vision.Image(content=content)  # Fix: use vision.Image, not types.Image
        response = client.label_detection(image=image)

        # Fix: check error.message correctly — it's falsy when empty
        if response.error.message:
            raise RuntimeError(f"Vision API error: {response.error.message}")

        detected_food = []
        for label in response.label_annotations:
            description = label.description.lower()
            if "food" in description or description in FOOD_KEYWORDS:
                detected_food.append(description)

        return detected_food

    except FileNotFoundError:
        print(f"[classify_food] Image file not found: {image_file}")
        return []
    except Exception as e:
        print(f"[classify_food] Error: {e}")
        return []
