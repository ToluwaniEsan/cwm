# voice.py — Local ASR (Whisper) and TTS (pyttsx3) for CWM

from __future__ import annotations

import tempfile
from typing import Any

# Optional dependencies — fail with clear install instructions if missing
_INSTALL_HINT = "pip install sounddevice scipy openai-whisper pyttsx3"

try:
    import sounddevice as sd
except ImportError as e:
    sd = None  # type: ignore[assignment]
    _SOUNDDEVICE_ERR = str(e)

try:
    from scipy.io import wavfile
except ImportError as e:
    wavfile = None  # type: ignore[assignment]
    _SCIPY_ERR = str(e)

try:
    import whisper
except ImportError as e:
    whisper = None  # type: ignore[assignment]
    _WHISPER_ERR = str(e)

try:
    import pyttsx3
except ImportError as e:
    pyttsx3 = None  # type: ignore[assignment]
    _PYTTSX3_ERR = str(e)


def _require_sounddevice() -> Any:
    if sd is None:
        raise ImportError(
            f"sounddevice is required for microphone recording. Install with: {_INSTALL_HINT}"
        ) from None
    return sd


def _require_scipy_wavfile() -> Any:
    if wavfile is None:
        raise ImportError(
            f"scipy is required for saving audio. Install with: {_INSTALL_HINT}"
        ) from None
    return wavfile


def _require_whisper() -> Any:
    if whisper is None:
        raise ImportError(
            f"openai-whisper is required for speech-to-text. Install with: {_INSTALL_HINT}"
        ) from None
    return whisper


def _require_pyttsx3() -> Any:
    if pyttsx3 is None:
        raise ImportError(
            f"pyttsx3 is required for text-to-speech. Install with: {_INSTALL_HINT}"
        ) from None
    return pyttsx3


def get_whisper_model():
    """
    Load and cache the Whisper base model (Streamlit cache when available).
    """
    w = _require_whisper()
    try:
        import streamlit as st

        @st.cache_resource
        def _load():
            return w.load_model("base")

        return _load()
    except ImportError:
        return w.load_model("base")


def record_audio(duration_sec: float = 5, sample_rate: int = 16000) -> str:
    """
    Record audio from the default microphone and save as a temporary WAV file.

    Args:
        duration_sec: Recording length in seconds.
        sample_rate: Sample rate in Hz (Whisper works well with 16 kHz).

    Returns:
        Path to the saved WAV file.
    """
    sounddevice = _require_sounddevice()
    wavfile_mod = _require_scipy_wavfile()

    frames = int(duration_sec * sample_rate)
    # Blocking capture from default input device
    recording = sounddevice.rec(
        frames,
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sounddevice.wait()

    fd, path = tempfile.mkstemp(suffix=".wav", prefix="cwm_voice_")
    import os
    os.close(fd)

    # Convert float32 [-1, 1] to int16 for WAV
    import numpy as np

    audio_int16 = (recording * 32767).astype(np.int16)
    wavfile_mod.write(path, sample_rate, audio_int16.squeeze())
    return path


def transcribe_audio(wav_path: str) -> str:
    """
    Transcribe a WAV file using local Whisper (base model).

    Args:
        wav_path: Path to the audio file.

    Returns:
        Stripped transcription text.
    """
    model = get_whisper_model()
    result = model.transcribe(wav_path)
    return (result.get("text") or "").strip()


def speak_recipe_summary(query: str, recipes: list[dict]) -> None:
    """
    Speak a short summary of recipe search results via pyttsx3.

    Says: "I found [N] recipes for [query]. The top result is [title]."
    """
    tts = _require_pyttsx3()
    n = len(recipes)
    top_title = recipes[0].get("title", "unknown") if recipes else "unknown"
    message = f"I found {n} recipes for {query}. The top result is {top_title}."

    engine = tts.init()
    engine.say(message)
    engine.runAndWait()
