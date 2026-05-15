# CWM — Cook With Me

AI-assisted food discovery: identify food from a photo (like circle-and-search for dishes), then fetch recipes with ingredients and cooking steps.

## Features

- **Streamlit web app** — upload a photo or search by name; browse recipes with full details from [TheMealDB](https://www.themealdb.com/)
- **Google Cloud Vision** — label detection filtered for food-related items
- **Screen capture CLI** — `food_image_detection.py` captures the screen and runs the same pipeline (optional)
- **Go REST API** — `backend/` for mobile or other clients
- **React Native mobile UI** — `mobile-branch/react-native-ui/` (Expo) talking to the Go API

## Prerequisites

- Python 3.10+
- [Google Cloud Vision API](https://cloud.google.com/vision) enabled and credentials configured (`GOOGLE_APPLICATION_CREDENTIALS` pointing to a service account JSON file — **never commit this file**)
- Optional: Go 1.21+ for the API server; Node.js for the mobile app

## Quick start (Streamlit)

```bash
cd cwm
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
set GOOGLE_APPLICATION_CREDENTIALS=path\to\your-service-account.json
streamlit run app.py
```

Or on Windows: `streamlit.cmd run app.py`

## Screen capture CLI

```bash
python food_image_detection.py
```

## Go API

```bash
cd backend
go run .
```

Default port: `4000` (see `backend/main.go`). Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env` or the environment.

## Mobile app

```bash
cd mobile-branch/react-native-ui
npx expo start
```

Point `API_BASE` in `App.tsx` at your machine’s IP when testing on a physical device.

## Tests

```bash
pytest tests/ -v
```

## Project layout

| Path | Description |
|------|-------------|
| `app.py` | Streamlit UI |
| `food_recognition.py` | Vision API food classification |
| `recipe_retrieval.py` | TheMealDB search and detail |
| `food_image_detection.py` | Screenshot → detect → recipes (CLI) |
| `backend/` | Go HTTP API |
| `mobile-branch/` | React Native / Expo client |
| `tests/` | Pytest suite |

## Security

Do not commit Google Cloud JSON keys or `.env` files. Use `.gitignore` and rotate any key that was ever pushed to a public repository.

## License

See upstream repository history. Original concept: food photo → recipe ingredients and steps for home cooking.
