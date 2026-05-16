# food_recognition.py — Hugging Face Inference API (food image classification)

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

_PROJECT_ROOT = Path(__file__).resolve().parent
_ENV_FILE = _PROJECT_ROOT / ".env"

DEFAULT_HF_MODEL = "nateraw/food"
HF_INFERENCE_BASE = "https://router.huggingface.co/hf-inference/models"
MIN_SCORE = 0.05
MAX_LABELS = 5
MODEL_LOAD_RETRY_SEC = 15


def _guess_content_type(image_file: str) -> str:
    """Router API requires Content-Type for raw image bytes."""
    ext = Path(image_file).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def _load_env_file(env_path: Path) -> bool:
    """Parse .env into os.environ (used when python-dotenv is missing)."""
    if not env_path.is_file():
        return False
    loaded = False
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value:
            os.environ[key] = value
            loaded = True
    return loaded


def _bootstrap_env() -> None:
    """Load .env from project root via dotenv or built-in fallback."""
    import importlib.util

    dotenv_installed = importlib.util.find_spec("dotenv") is not None
    dotenv_load_returned = False
    if dotenv_installed:
        from dotenv import load_dotenv

        dotenv_load_returned = bool(load_dotenv(_ENV_FILE))

    if not dotenv_load_returned:
        _load_env_file(_ENV_FILE)


_bootstrap_env()


def get_hf_token() -> str | None:
    """Return Hugging Face access token from environment."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    return token.strip() if token and token.strip() else None


def get_hf_model() -> str:
    """Model ID for food classification on HF Inference API."""
    return (os.environ.get("HF_VISION_MODEL") or DEFAULT_HF_MODEL).strip()


def vision_is_configured() -> bool:
    """True when HF_TOKEN (or HUGGINGFACE_API_KEY) is set."""
    return get_hf_token() is not None


def _normalize_label(label: str) -> str:
    """Food-101 style labels: fried_rice -> fried rice."""
    return label.strip().lower().replace("_", " ")


def _parse_hf_predictions(data: Any) -> list[str]:
    """Convert HF image-classification JSON to food label strings."""
    if not isinstance(data, list):
        return []

    detected: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        label = item.get("label") or item.get("generated_text")
        score = item.get("score", 0.0)
        if label is None:
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            score_f = 0.0
        if score_f < MIN_SCORE:
            continue
        normalized = _normalize_label(str(label))
        if normalized and normalized not in detected:
            detected.append(normalized)
        if len(detected) >= MAX_LABELS:
            break
    return detected


def _classify_with_hf(image_file: str, token: str, model_id: str) -> list[str]:
    """Call Hugging Face Inference API with raw image bytes."""
    url = f"{HF_INFERENCE_BASE}/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": _guess_content_type(image_file),
    }

    with open(image_file, "rb") as f:
        image_bytes = f.read()

    for attempt in range(2):
        resp = requests.post(url, headers=headers, data=image_bytes, timeout=60)
        if resp.status_code == 503 and attempt == 0:
            # Model cold start — wait and retry once
            time.sleep(MODEL_LOAD_RETRY_SEC)
            continue
        resp.raise_for_status()
        return _parse_hf_predictions(resp.json())

    return []


def classify_food(image_file: str) -> list[str]:
    """
    Detect food labels in an image via Hugging Face Inference API.

    Requires HF_TOKEN (or HUGGINGFACE_API_KEY) in .env or environment.
    Default model: nateraw/food (override with HF_VISION_MODEL).

    Args:
        image_file: Path to a local image file.

    Returns:
        List of detected food item strings, or empty list on failure.
    """
    try:
        token = get_hf_token()
        if not token:
            print("[classify_food] Set HF_TOKEN in .env to enable photo detection.")
            return []

        model_id = get_hf_model()
        return _classify_with_hf(image_file, token, model_id)

    except FileNotFoundError:
        print(f"[classify_food] Image file not found: {image_file}")
        return []
    except Exception as e:
        print(f"[classify_food] Error: {e}")
        return []
