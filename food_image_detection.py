"""Screen-capture CLI: screenshot → Vision food labels → MealDB recipes."""

import cv2
import numpy as np
import pyautogui

from food_recognition import classify_food
from recipe_retrieval import get_recipes


def capture_screen():
    screenshot = pyautogui.screenshot()
    frame = np.array(screenshot)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def save_frame(frame, filename: str = "detected_image.jpg") -> str:
    cv2.imwrite(filename, frame)
    print(f"Image saved as {filename}")
    return filename


def print_recipes(recipes: list[dict]) -> None:
    if not recipes:
        print("No recipes found.")
        return
    print("\nTop recipes found:")
    for i, recipe in enumerate(recipes, start=1):
        print(f"{i}. {recipe['title']}")
        print(f"   {recipe['url']}")


def main() -> None:
    frame = capture_screen()
    image_path = save_frame(frame)

    detected_food = classify_food(image_path)
    print("Detected food items:", detected_food or "(none)")

    if not detected_food:
        return

    recipes = get_recipes(detected_food)
    print_recipes(recipes)


if __name__ == "__main__":
    main()
