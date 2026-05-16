# CWM — Cook With Me

AI-assisted food discovery: identify food from a photo (like circle-and-search for dishes), then fetch recipes with ingredients and cooking steps.

**Full architecture and function reference:** see [HOW_IT_WORKS.md](HOW_IT_WORKS.md).

## Features

- **Streamlit web app** — upload a photo or search by name; browse recipes with full details from [TheMealDB](https://www.themealdb.com/)
- **Hugging Face Vision** — food photo classification via [Inference API](https://huggingface.co/docs/api-inference/index) (no Google Cloud billing)
- **Voice search** — local Whisper ASR + optional TTS
- **FoodAgent** — detect → recipes → top recipe details in one loop
- **Screen capture CLI** — `food_image_detection.py` (optional)
- **Go REST API** — `backend/` (still uses Google Vision if configured; optional)

## Prerequisites

- Python 3.10+
- [Hugging Face](https://huggingface.co/) account and access token in `.env` as `HF_TOKEN` (**never commit `.env`**)
- Optional: Go 1.21+ for the API server; Node.js for the mobile app

## Quick start (Streamlit)

```bash
cd cwm
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env
# Edit .env: HF_TOKEN=hf_...  and optionally HF_VISION_MODEL=nateraw/food
streamlit run app.py
```

Or on Windows: `streamlit.cmd run app.py`

Get a token: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (read access is enough).

**Note:** First photo request may take 15–20s while the HF model loads. Free tier has rate limits.

## Screen capture CLI

```bash
python food_image_detection.py
```

## Go API

```bash
cd backend
go run .
```

Default port: `4000`. The Go backend is separate from the Streamlit HF setup.

## Mobile app

```bash
cd mobile-branch/react-native-ui
npx expo start
```

## Tests

```bash
pytest tests/ -v
```

## Project layout

| Path | Description |
|------|-------------|
| `app.py` | Streamlit UI |
| `food_recognition.py` | HF Inference food classification |
| `recipe_retrieval.py` | TheMealDB search and detail |
| `agent.py` | FoodAgent pipeline |
| `voice.py` | Whisper + TTS |
| `food_image_detection.py` | Screenshot CLI |
| `backend/` | Go HTTP API |
| `tests/` | Pytest suite |

## Recipe coverage

Recipes come from [TheMealDB](https://www.themealdb.com/) (limited catalog). Some dishes (e.g. regional names) may not appear even when photo detection works.

## Security

Do not commit API keys or `.env` files. Use `.gitignore` and rotate any key that was ever pushed to a public repository.
