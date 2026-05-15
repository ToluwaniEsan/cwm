# recipe_retrieval.py — TheMealDB recipe search (name + ingredient)

import re
import requests

MEALDB_SEARCH_URL = "https://www.themealdb.com/api/json/v1/1/search.php"
MEALDB_FILTER_URL = "https://www.themealdb.com/api/json/v1/1/filter.php"
MEALDB_DETAIL_URL = "https://www.themealdb.com/api/json/v1/1/lookup.php"

# Strip conversational filler from voice/manual queries before searching
_FILLER_PATTERNS = [
    r"can you (please )?(get|find|give) me (the )?",
    r"(please )?(get|find|show) me (the )?",
    r"(i want|i need|looking for|search for)( the)?",
    r"(the )?recipe (for|of)",
    r"how (do i |to )?(make|cook|prepare)",
    r"what is (the )?",
]


def normalize_food_query(query: str) -> str:
    """
    Clean a user or voice query down to a searchable food term.

    Example: "Can you get me the recipe for pizza" -> "pizza"
    """
    q = query.strip()
    for pattern in _FILLER_PATTERNS:
        q = re.sub(pattern, "", q, flags=re.IGNORECASE).strip()
    q = q.strip(" .,!?\"'")
    return q if q else query.strip()


def _meals_to_recipes(meals: list[dict], seen_ids: set[str]) -> list[dict]:
    """Convert MealDB meal rows into our recipe dict format."""
    recipes: list[dict] = []
    for meal in meals:
        meal_id = meal.get("idMeal")
        if not meal_id or meal_id in seen_ids:
            continue
        seen_ids.add(meal_id)
        recipes.append({
            "title": meal.get("strMeal", "Unknown"),
            "url": f"https://www.themealdb.com/meal/{meal_id}",
            "thumbnail": meal.get("strMealThumb", ""),
            "id": meal_id,
        })
    return recipes


def _fetch_meals_by_name(term: str) -> list[dict] | None:
    """Search meals by dish name (search.php?s=)."""
    resp = requests.get(MEALDB_SEARCH_URL, params={"s": term}, timeout=8)
    resp.raise_for_status()
    return resp.json().get("meals")


def _fetch_meals_by_ingredient(term: str) -> list[dict] | None:
    """Search meals that use an ingredient (filter.php?i=)."""
    resp = requests.get(MEALDB_FILTER_URL, params={"i": term}, timeout=8)
    resp.raise_for_status()
    return resp.json().get("meals")


def get_recipes(food_items: list[str], max_results: int = 5) -> list[dict]:
    """
    Fetches recipes from TheMealDB for a list of food items.

    Tries meal name search first, then ingredient filter — dish names like
    "pizza" only work with search.php, not filter.php.

    Args:
        food_items: List of food label strings (e.g. ['pizza', 'chicken']).
        max_results: Maximum number of recipes to return.

    Returns:
        List of dicts with 'title', 'url', 'thumbnail', 'id' keys.
    """
    if not food_items:
        return []

    seen_ids: set[str] = set()
    recipes: list[dict] = []

    for raw_item in food_items:
        item = normalize_food_query(raw_item)
        if not item:
            continue

        meals: list[dict] | None = None
        try:
            # Name search — works for pizza, fried rice, etc.
            meals = _fetch_meals_by_name(item)
            if not meals:
                # Ingredient filter — works for chicken, tomato, etc.
                meals = _fetch_meals_by_ingredient(item)

            if not meals:
                print(f"[get_recipes] No recipes found for '{item}' (from '{raw_item}')")
                continue

            for recipe in _meals_to_recipes(meals, seen_ids):
                recipes.append(recipe)
                if len(recipes) >= max_results:
                    return recipes

        except requests.exceptions.Timeout:
            print(f"[get_recipes] Timeout fetching recipes for '{item}'")
        except requests.exceptions.RequestException as e:
            print(f"[get_recipes] Request error for '{item}': {e}")

    return recipes[:max_results]


def get_recipe_detail(meal_id: str) -> dict | None:
    """
    Fetches full recipe details (ingredients + steps) for a meal ID.

    Args:
        meal_id: The MealDB meal ID string.

    Returns:
        Dict with full recipe info, or None if not found.
    """
    try:
        resp = requests.get(MEALDB_DETAIL_URL, params={"i": meal_id}, timeout=8)
        resp.raise_for_status()
        meals = resp.json().get("meals")
        if not meals:
            return None

        meal = meals[0]

        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}", "").strip()
            measure = meal.get(f"strMeasure{i}", "").strip()
            if ing:
                ingredients.append(f"{measure} {ing}".strip())

        return {
            "id": meal.get("idMeal"),
            "title": meal.get("strMeal"),
            "category": meal.get("strCategory"),
            "area": meal.get("strArea"),
            "instructions": meal.get("strInstructions"),
            "thumbnail": meal.get("strMealThumb"),
            "youtube": meal.get("strYoutube"),
            "ingredients": ingredients,
        }

    except Exception as e:
        print(f"[get_recipe_detail] Error: {e}")
        return None
