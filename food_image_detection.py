import cv2
import pyautogui
import numpy as np

def capture_screen():
    # Take a screenshot of the entire screen
    screenshot = pyautogui.screenshot()
    frame = np.array(screenshot)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame

def extract_images(frame):
    # Simple placeholder: save the full screenshot as an image
    filename = "detected_image.jpg"
    cv2.imwrite(filename, frame)
    print(f"Image saved as {filename}")
    return filename

# Usage
frame = capture_screen()
image_path = extract_images(frame)

from food_recognition import classify_food

# Example usage
detected_food = classify_food("detected_image.jpg")
print("Detected Food Items:", detected_food)

from recipe_retrieval import get_recipes

# After detecting food items
detected_food = classify_food(image_path)
print("Detected Food Items:", detected_food)

# Fetch recipes for the detected food items
recipes = get_recipes(detected_food)
if recipes:
    print("\nFound Recipes:")
    for recipe in recipes:
        print(f"Title: {recipe['title']}, URL: {recipe['url']}")
else:
    print("\nNo recipes found.")

print("Detected Food Items:", detected_food)

# Display the recipes
if recipes:
    print("\nTop Recipes Found:")
    for i, recipe in enumerate(recipes, start=1):
        print(f"{i}. {recipe['title']}")
        print(f"   Recipe Link: {recipe['url']}")
else:
    print("\nNo recipes found for the detected food items.")

