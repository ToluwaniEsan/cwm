import io
from PIL import Image
from google.cloud import vision

def classify_food(image_file):
    """
    Uses Google Cloud Vision API to classify food in an image.
    This version uses the official google.cloud.vision library to process the image and detect labels.
    """
    try:
        # Initialize the Vision API client
        client = vision.ImageAnnotatorClient()

        # Read the image file and prepare it for Google Vision API
        with open(image_file, "rb") as image:
            content = image.read()

        # Create an image instance for Google Vision API
        image = types.Image(content=content)

        # Use the Vision API to detect labels in the image
        response = client.label_detection(image=image)

        # If the API call is successful
        if response.error.message:
            raise Exception(f"API Error: {response.error.message}")

        # Process the response to get food-related labels
        detected_food = []
        for label in response.label_annotations:
            description = label.description.lower()
            if "food" in description or description in ["pizza", "burger", "sushi", "pasta"]:  # Custom filter for food items
                detected_food.append(description)

        # Return the list of detected food items
        return detected_food

    except Exception as e:
        print(f"Error in classify_food: {str(e)}")
        return None
