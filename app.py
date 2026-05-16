# app.py — CWM Food Detection & Recipe Finder (Multimodal + Agentic)

import io
from typing import Any

import streamlit as st
from PIL import Image

from agent import FoodAgent
from food_recognition import vision_is_configured
from recipe_retrieval import get_recipe_detail, normalize_food_query
from voice import record_audio, speak_recipe_summary, transcribe_audio


# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CWM — Cook With Me",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Outfit:wght@600;800&display=swap" rel="stylesheet">
<style>
    .stApp {
        background: linear-gradient(165deg, #0a0b10 0%, #12141f 40%, #1a1030 100%);
        color: #f0f2fa;
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #141622 0%, #0d0e14 100%);
        border-right: 1px solid rgba(255,107,107,0.15);
    }
    .cwm-hero {
        text-align: center;
        padding: 2rem 1rem 1.5rem;
        margin-bottom: 1rem;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(255,107,107,0.12) 0%, rgba(108,99,255,0.18) 50%, rgba(255,193,7,0.08) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    }
    .cwm-hero h1 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 2.6rem;
        margin: 0;
        background: linear-gradient(90deg, #ff8a80, #ffc107, #b388ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .cwm-subtitle {
        color: #a8adc8;
        font-size: 1.05rem;
        margin-top: 0.5rem;
    }
    .cwm-badge {
        display: inline-block;
        background: rgba(108,99,255,0.25);
        color: #c4b5fd;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.35rem 0.25rem;
        border: 1px solid rgba(108,99,255,0.4);
    }
    .food-tag {
        display: inline-block;
        background: linear-gradient(135deg, #2a2040, #1e2438);
        color: #ffb74d;
        padding: 6px 14px;
        border-radius: 999px;
        margin: 4px;
        font-size: 0.88rem;
        font-weight: 600;
        border: 1px solid rgba(255,183,77,0.35);
    }
    .cwm-card {
        background: rgba(30,32,41,0.85);
        border-radius: 16px;
        padding: 1.25rem;
        border: 1px solid rgba(255,255,255,0.06);
        margin-bottom: 0.75rem;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255,107,107,0.15), rgba(108,99,255,0.15));
        padding: 0.75rem 1rem;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    div[data-testid="stMetric"] label { color: #ffc107 !important; }
    /* Keep uploaded photo preview compact */
    [data-testid="stImage"] img {
        max-height: 220px !important;
        width: auto !important;
        object-fit: contain;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _to_rgb(img: Image.Image) -> Image.Image:
    """Convert PNG/transparency modes to RGB so JPEG export works."""
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        return background
    if img.mode == "P":
        return _to_rgb(img.convert("RGBA"))
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


# Max size for on-screen preview only (full-res still sent to HF for classification)
PREVIEW_MAX_SIZE = (400, 280)


def make_preview(img: Image.Image, max_size: tuple[int, int] = PREVIEW_MAX_SIZE) -> Image.Image:
    """Return a smaller copy for UI display so results stay above the fold."""
    preview = img.copy()
    preview.thumbnail(max_size, Image.Resampling.LANCZOS)
    return preview


def resize_image(image_file, max_size: tuple[int, int] = (1024, 1024)) -> io.BytesIO:
    """Resize uploaded image for display and HF classification."""
    with Image.open(image_file) as img:
        img = _to_rgb(img)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=90)
        output.seek(0)
        return output


def _update_status(msg: str, slot: Any) -> None:
    """Write the current agent step into the status log placeholder."""
    slot.markdown(
        f'<div class="cwm-card" style="padding:0.75rem 1rem;">'
        f'<span style="color:#ffc107;">●</span> <strong>Agent:</strong> {msg}</div>',
        unsafe_allow_html=True,
    )


def _run_agent(
    status_slot: Any,
    *,
    image_path: str | None = None,
    text_query: str | None = None,
) -> dict[str, Any]:
    """Run FoodAgent with live status updates in the UI."""
    agent = FoodAgent()

    def on_status(msg: str) -> None:
        _update_status(msg, status_slot)

    return agent.run(
        image_path=image_path,
        text_query=text_query,
        on_status=on_status,
    )


def _display_agent_result(result: dict[str, Any], *, query_label: str) -> None:
    """Render agent output: errors, tags, latency, and recipe cards."""
    err = result.get("error")

    if err == "step1_detection":
        st.error(
            "**Photo detection failed** — could not identify food in this image. "
            "Check **HF_TOKEN** in `.env`, wait if the model is loading, or try **typing** / **speaking** the dish name."
        )
    elif err:
        st.warning(result.get("error_message", "Something went wrong."))

    detected = result.get("detected_items") or []
    if detected and not err:
        st.success(f"Results for **{query_label}**")
        tags_html = " ".join(f'<span class="food-tag">{item}</span>' for item in detected)
        st.markdown(tags_html, unsafe_allow_html=True)

    if "latency_ms" in result:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("⚡ Response time", f"{result['latency_ms']} ms")
        with c2:
            st.metric("Recipes found", len(result.get("recipes_found") or []))
        with c3:
            st.metric("Items matched", len(detected))

    recipes = result.get("recipes_found") or []
    if recipes and not err:
        st.markdown("---")
        top = result.get("top_recipe_title", "")
        with st.expander(f"⭐ Chef's pick — {top}", expanded=True):
            if result.get("top_recipe_ingredients"):
                st.markdown("**Ingredients**")
                st.markdown("\n".join(f"- {i}" for i in result["top_recipe_ingredients"]))
            if result.get("top_recipe_instructions"):
                st.markdown("**Quick steps**")
                st.markdown(result["top_recipe_instructions"])

        st.markdown("### More recipes")
        _render_recipes(recipes)


def _render_recipes(recipes: list[dict]) -> None:
    """Render recipe cards in a responsive grid."""
    cols = st.columns(min(len(recipes), 3))
    for idx, recipe in enumerate(recipes):
        with cols[idx % len(cols)]:
            st.markdown('<div class="cwm-card">', unsafe_allow_html=True)
            if recipe.get("thumbnail"):
                st.image(recipe["thumbnail"], width=120)
            st.markdown(f"#### {recipe['title']}")
            st.link_button("Open recipe", recipe["url"], use_container_width=True)
            if st.button("Full details", key=f"detail_{recipe['id']}", use_container_width=True):
                with st.spinner("Loading…"):
                    detail = get_recipe_detail(recipe["id"])
                if detail:
                    st.caption(f"{detail.get('category')} · {detail.get('area')}")
                    if detail.get("ingredients"):
                        for ing in detail["ingredients"][:8]:
                            st.markdown(f"- {ing}")
                    if detail.get("instructions"):
                        t = detail["instructions"]
                        st.markdown(t[:800] + ("…" if len(t) > 800 else ""))
                    if detail.get("youtube"):
                        st.video(detail["youtube"])
            st.markdown("</div>", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Photo detection (Hugging Face)")

    if vision_is_configured():
        st.success("HF Vision ready (.env)")
    else:
        st.warning(
            "Photo detection not configured — **text & voice still work**. "
            "Add to **`.env`** in the project folder:\n\n"
            "`HF_TOKEN=hf_...`\n\n"
            "Get a token: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)"
        )

    st.markdown("---")
    st.markdown("**Tips**")
    st.markdown(
        "- Say dish names clearly: *\"pizza\"*, *\"fried rice\"*\n"
        "- Type or speak the **dish name**, not full sentences\n"
        "- First photo scan may be slow while the HF model loads"
    )

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cwm-hero">
    <h1>🍽️ Cook With Me</h1>
    <p class="cwm-subtitle">Multimodal AI: Vision + Voice + Agentic Reasoning</p>
    <span class="cwm-badge">Vision</span>
    <span class="cwm-badge">Voice</span>
    <span class="cwm-badge">Recipes</span>
</div>
""", unsafe_allow_html=True)

status_slot = st.empty()

# ── Input panels ──────────────────────────────────────────────────────────────
col_photo, col_text, col_voice = st.columns([1.2, 1, 0.9], gap="large")

with col_photo:
    st.markdown("#### 📷 Photo")
    uploaded_file = st.file_uploader(
        "Snap or upload food",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

with col_text:
    st.markdown("#### ⌨️ Type")
    manual_query = st.text_input(
        "Dish name",
        placeholder="e.g. pizza, fried rice",
        label_visibility="collapsed",
    )
    search_text_btn = st.button("Find recipes", type="primary", use_container_width=True)

with col_voice:
    st.markdown("#### 🎙️ Voice")
    st.caption("5 sec — say the dish name")
    voice_btn = st.button("Speak your search", use_container_width=True)

temp_path: str | None = None
detect_btn = False

if uploaded_file is not None:
    try:
        resized = resize_image(uploaded_file)
        image = _to_rgb(Image.open(resized))
        temp_path = "temp_image.jpg"
        image.save(temp_path, format="JPEG", quality=90)

        preview_col, action_col = st.columns([1, 2], gap="medium")
        with preview_col:
            st.image(
                make_preview(image),
                caption="Your photo",
                width=260,
            )
        with action_col:
            st.markdown("##### Ready to scan")
            st.caption("We analyze the full-resolution file; only the preview is shrunk here.")
            detect_btn = st.button(
                "🔍 Detect food & find recipes",
                type="primary",
                use_container_width=True,
            )
    except Exception as e:
        st.error(f"Image error: {e}")

# ── Process inputs (manual > voice > detect) ───────────────────────────────────
if search_text_btn and manual_query:
    q = normalize_food_query(manual_query)
    result = _run_agent(status_slot, text_query=q)
    _display_agent_result(result, query_label=q)

elif voice_btn:
    try:
        with st.spinner("🎙️ Listening… speak the dish name (5 seconds)"):
            _update_status("Recording audio…", status_slot)
            wav_path = record_audio(duration_sec=5)
            _update_status("Transcribing with Whisper…", status_slot)
            transcription = transcribe_audio(wav_path)

        if not transcription:
            st.warning("Couldn't hear you — try again closer to the mic.")
        else:
            q = normalize_food_query(transcription)
            st.info(f'Heard: "{transcription}" → searching for **{q}**')
            result = _run_agent(status_slot, text_query=q)
            _display_agent_result(result, query_label=q)
            recipes = result.get("recipes_found") or []
            if recipes and not result.get("error"):
                speak_recipe_summary(q, recipes)
    except ImportError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Voice failed: {e}")

elif detect_btn and temp_path:
    if not vision_is_configured():
        st.error(
            "Add **HF_TOKEN** to your **`.env`** file, "
            "then click detect again."
        )
    else:
        result = _run_agent(status_slot, image_path=temp_path)
        label = ", ".join(result.get("detected_items") or ["photo"])
        _display_agent_result(result, query_label=label)

elif not uploaded_file and not manual_query:
    st.markdown(
        '<div class="cwm-card" style="text-align:center;color:#a8adc8;">'
        "Upload a photo, type a dish name, or use voice to get started."
        "</div>",
        unsafe_allow_html=True,
    )
