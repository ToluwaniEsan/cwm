# tests/test_cwm.py — CWM Test Suite
# Run with: pytest tests/ -v

import io
import os

import pytest
from unittest.mock import patch, MagicMock, mock_open

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: classify_food — handles missing file gracefully
# ─────────────────────────────────────────────────────────────────────────────
def test_classify_food_file_not_found():
    """classify_food returns empty list when image file doesn't exist."""
    from food_recognition import classify_food
    result = classify_food("does_not_exist.jpg")
    assert result == [], "Should return empty list for missing file"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: classify_food — parses HF Inference API labels
# ─────────────────────────────────────────────────────────────────────────────
def test_classify_food_filters_labels():
    """classify_food returns top food labels from HF classification JSON."""
    from food_recognition import classify_food

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"label": "pizza", "score": 0.92},
        {"label": "bread", "score": 0.01},
        {"label": "fried_rice", "score": 0.15},
    ]
    mock_resp.raise_for_status = MagicMock()

    with patch.dict("os.environ", {"HF_TOKEN": "hf_test"}, clear=False), patch(
        "food_recognition.requests.post", return_value=mock_resp
    ), patch("builtins.open", mock_open(read_data=b"\xff\xd8\xff")):
        result = classify_food("fake_image.jpg")

    assert "pizza" in result
    assert "fried rice" in result
    assert "bread" not in result


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: get_recipes — returns correct structure from MealDB
# ─────────────────────────────────────────────────────────────────────────────
def test_get_recipes_returns_correct_structure():
    """get_recipes returns list of dicts with required keys."""
    from recipe_retrieval import get_recipes

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "meals": [
            {"idMeal": "52772", "strMeal": "Teriyaki Chicken Casserole", "strMealThumb": "https://img.com/t.jpg"},
            {"idMeal": "52773", "strMeal": "Chicken Handi", "strMealThumb": "https://img.com/c.jpg"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("recipe_retrieval.requests.get", return_value=mock_response):
        results = get_recipes(["chicken"])

    assert len(results) > 0, "Should return at least one recipe"
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "thumbnail" in r
        assert "id" in r
        assert r["url"].startswith("https://www.themealdb.com/meal/")


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: get_recipes — handles empty food_items list
# ─────────────────────────────────────────────────────────────────────────────
def test_get_recipes_empty_input():
    """get_recipes returns empty list when given no food items."""
    from recipe_retrieval import get_recipes
    result = get_recipes([])
    assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: get_recipes — handles API returning null meals gracefully
# ─────────────────────────────────────────────────────────────────────────────
def test_get_recipes_null_meals():
    """get_recipes handles MealDB returning null for meals field."""
    from recipe_retrieval import get_recipes

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"meals": None}
    mock_response.raise_for_status = MagicMock()

    with patch("recipe_retrieval.requests.get", return_value=mock_response):
        results = get_recipes(["unknownfood123"])

    assert results == [], "Should return empty list when meals is null"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: get_recipes — respects max_results cap
# ─────────────────────────────────────────────────────────────────────────────
def test_get_recipes_max_results():
    """get_recipes does not return more than max_results recipes."""
    from recipe_retrieval import get_recipes

    # Return 10 meals per item
    meals = [{"idMeal": str(i), "strMeal": f"Meal {i}", "strMealThumb": ""} for i in range(10)]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"meals": meals}
    mock_response.raise_for_status = MagicMock()

    with patch("recipe_retrieval.requests.get", return_value=mock_response):
        results = get_recipes(["chicken", "pasta", "pizza"], max_results=5)

    assert len(results) <= 5, f"Expected ≤5 results, got {len(results)}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: get_recipe_detail — parses ingredients correctly
# ─────────────────────────────────────────────────────────────────────────────
def test_get_recipe_detail_parses_ingredients():
    """get_recipe_detail extracts ingredients and measures correctly."""
    from recipe_retrieval import get_recipe_detail

    meal_data = {
        "idMeal": "52772",
        "strMeal": "Teriyaki Chicken",
        "strCategory": "Chicken",
        "strArea": "Japanese",
        "strInstructions": "Mix ingredients and cook.",
        "strMealThumb": "https://img.com/t.jpg",
        "strYoutube": "",
        "strIngredient1": "Chicken",
        "strMeasure1": "500g",
        "strIngredient2": "Soy Sauce",
        "strMeasure2": "3 tbsp",
        "strIngredient3": "",
        "strMeasure3": "",
    }
    # Fill remaining ingredient slots
    for i in range(4, 21):
        meal_data[f"strIngredient{i}"] = ""
        meal_data[f"strMeasure{i}"] = ""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"meals": [meal_data]}
    mock_response.raise_for_status = MagicMock()

    with patch("recipe_retrieval.requests.get", return_value=mock_response):
        detail = get_recipe_detail("52772")

    assert detail is not None
    assert detail["title"] == "Teriyaki Chicken"
    assert "500g Chicken" in detail["ingredients"]
    assert "3 tbsp Soy Sauce" in detail["ingredients"]
    assert len(detail["ingredients"]) == 2  # Only non-empty ones


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: FoodAgent — text query success path
# ─────────────────────────────────────────────────────────────────────────────
def test_agent_text_query_success():
    """FoodAgent returns full summary for a text query."""
    from agent import FoodAgent

    mock_recipes = [
        {"id": "52772", "title": "Teriyaki Chicken", "url": "https://x", "thumbnail": ""},
    ]
    long_instructions = "x" * 600
    mock_detail = {
        "title": "Teriyaki Chicken",
        "ingredients": ["500g Chicken"],
        "instructions": long_instructions,
    }

    with patch("agent.get_recipes", return_value=mock_recipes), patch(
        "agent.get_recipe_detail", return_value=mock_detail
    ):
        result = FoodAgent().run(text_query="chicken")

    assert "error" not in result
    assert result["detected_items"] == ["chicken"]
    assert len(result["recipes_found"]) == 1
    assert result["top_recipe_title"] == "Teriyaki Chicken"
    assert result["top_recipe_ingredients"] == ["500g Chicken"]
    assert len(result["top_recipe_instructions"]) <= 501  # 500 + ellipsis
    assert result["latency_ms"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: FoodAgent — empty image detection
# ─────────────────────────────────────────────────────────────────────────────
def test_agent_image_detection_empty():
    """FoodAgent returns step1 error when Vision detects nothing."""
    from agent import FoodAgent

    with patch("agent.classify_food", return_value=[]):
        result = FoodAgent().run(image_path="fake.jpg")

    assert result.get("error") == "step1_detection"
    assert "detected" in result.get("error_message", "").lower() or "No food" in result.get("error_message", "")


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: FoodAgent — no recipes found
# ─────────────────────────────────────────────────────────────────────────────
def test_agent_no_recipes():
    """FoodAgent returns step2 error when MealDB returns nothing."""
    from agent import FoodAgent

    with patch("agent.get_recipes", return_value=[]):
        result = FoodAgent().run(text_query="unknownfood123")

    assert result.get("error") == "step2_recipes"
    assert result["detected_items"] == ["unknownfood123"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: FoodAgent — status callback receives all step messages
# ─────────────────────────────────────────────────────────────────────────────
def test_agent_status_callback():
    """FoodAgent calls on_status with Step 1–4 messages."""
    from agent import FoodAgent, STATUS_STEP1, STATUS_STEP2, STATUS_STEP3, STATUS_STEP4

    mock_recipes = [{"id": "1", "title": "Test Meal", "url": "https://x", "thumbnail": ""}]
    mock_detail = {"title": "Test Meal", "ingredients": [], "instructions": "Cook."}
    steps: list[str] = []

    with patch("agent.get_recipes", return_value=mock_recipes), patch(
        "agent.get_recipe_detail", return_value=mock_detail
    ):
        FoodAgent().run(text_query="pasta", on_status=steps.append)

    assert steps == [STATUS_STEP1, STATUS_STEP2, STATUS_STEP3, STATUS_STEP4]


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: normalize_food_query — strips conversational filler
# ─────────────────────────────────────────────────────────────────────────────
def test_normalize_food_query_strips_filler():
    """Voice-style phrases are cleaned to a searchable food term."""
    from recipe_retrieval import normalize_food_query

    assert normalize_food_query("Can you get me the recipe for pizza") == "pizza"
    assert normalize_food_query("fried rice") == "fried rice"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: classify_food — HF Inference API auth header
# ─────────────────────────────────────────────────────────────────────────────
def test_classify_food_with_hf_token():
    """classify_food POSTs to HF Inference with Bearer token."""
    from food_recognition import classify_food

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"label": "pizza", "score": 0.9}]
    mock_resp.raise_for_status = MagicMock()

    with patch.dict(
        os.environ,
        {"HF_TOKEN": "hf_test", "HF_VISION_MODEL": "nateraw/food"},
        clear=False,
    ), patch("food_recognition.requests.post", return_value=mock_resp) as mock_post, patch(
        "builtins.open", mock_open(read_data=b"\xff\xd8\xff")
    ):
        result = classify_food("fake.jpg")

    assert "pizza" in result
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer hf_test"
    assert "router.huggingface.co" in mock_post.call_args.args[0]
    assert "nateraw/food" in mock_post.call_args.args[0]


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: vision_is_configured — false without HF token
# ─────────────────────────────────────────────────────────────────────────────
def test_vision_not_configured_without_token():
    """vision_is_configured is False when HF_TOKEN is missing."""
    from food_recognition import vision_is_configured

    with patch("food_recognition.get_hf_token", return_value=None):
        assert vision_is_configured() is False
