# agent.py — FoodAgent: autonomous multi-step food → recipe pipeline

from __future__ import annotations

import time
from typing import Any, Callable

from food_recognition import classify_food
from recipe_retrieval import get_recipe_detail, get_recipes, normalize_food_query

# Status messages shown in the Streamlit demo UI during processing
STATUS_STEP1 = "Step 1: Detecting food..."
STATUS_STEP2 = "Step 2: Fetching recipes..."
STATUS_STEP3 = "Step 3: Loading top recipe details..."
STATUS_STEP4 = "Step 4: Done."

INSTRUCTIONS_MAX_LEN = 500


class FoodAgent:
    """
    Wraps vision detection, recipe search, and top-recipe detail fetch
    into a single agentic loop with timing and graceful failure handling.
    """

    def run(
        self,
        *,
        image_path: str | None = None,
        text_query: str | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """
        Execute the full detect → recipes → detail pipeline.

        Provide exactly one of image_path or text_query.

        Returns:
            Summary dict with detected_items, recipes_found, top recipe fields,
            and latency_ms. On failure, includes error and error_message keys.
        """
        start = time.perf_counter()

        def _status(msg: str) -> None:
            if on_status:
                on_status(msg)

        def _finish(extra: dict[str, Any]) -> dict[str, Any]:
            extra["latency_ms"] = int((time.perf_counter() - start) * 1000)
            return extra

        has_image = bool(image_path)
        has_text = bool(text_query and text_query.strip())

        if has_image == has_text:
            return _finish({
                "error": "step0_input",
                "error_message": "Provide exactly one of image_path or text_query.",
                "detected_items": [],
                "recipes_found": [],
            })

        # ── Step 1: Detect food labels or use text query ─────────────────────
        _status(STATUS_STEP1)
        if has_image:
            detected_items = classify_food(image_path)  # type: ignore[arg-type]
        else:
            # Normalize voice/manual phrasing ("recipe for pizza" -> "pizza")
            cleaned = normalize_food_query(text_query.strip())  # type: ignore[union-attr]
            detected_items = [cleaned]

        if not detected_items:
            return _finish({
                "error": "step1_detection",
                "error_message": "No food items detected in the image.",
                "detected_items": [],
                "recipes_found": [],
            })

        # ── Step 2: Fetch recipes from TheMealDB ─────────────────────────────
        _status(STATUS_STEP2)
        recipes = get_recipes(detected_items)

        if not recipes:
            return _finish({
                "error": "step2_recipes",
                "error_message": "No recipes found for the detected food items.",
                "detected_items": detected_items,
                "recipes_found": [],
            })

        # ── Step 3: Load full details for the top recipe ─────────────────────
        _status(STATUS_STEP3)
        top_id = recipes[0]["id"]
        detail = get_recipe_detail(top_id)

        if not detail:
            return _finish({
                "error": "step3_detail",
                "error_message": "Could not load details for the top recipe.",
                "detected_items": detected_items,
                "recipes_found": recipes,
            })

        # ── Step 4: Build structured summary ─────────────────────────────────
        _status(STATUS_STEP4)
        instructions = detail.get("instructions") or ""
        if len(instructions) > INSTRUCTIONS_MAX_LEN:
            instructions = instructions[:INSTRUCTIONS_MAX_LEN] + "…"

        return _finish({
            "detected_items": detected_items,
            "recipes_found": recipes,
            "top_recipe_title": detail.get("title", recipes[0].get("title", "Unknown")),
            "top_recipe_ingredients": detail.get("ingredients", []),
            "top_recipe_instructions": instructions,
        })
