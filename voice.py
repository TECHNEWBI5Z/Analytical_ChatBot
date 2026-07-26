"""Free, local speech-to-text using faster-whisper."""
import os
import tempfile

import streamlit as st


@st.cache_resource(show_spinner=False)
def get_whisper_model():
    """Load the model once per Streamlit session; it downloads on first use."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise RuntimeError("Voice support is not installed. Run: python -m pip install -r requirements.txt") from error

    return WhisperModel(
        os.getenv("WHISPER_MODEL", "tiny.en"),
        device="cpu",
        compute_type="int8",
    )


def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe an audio recording made by Streamlit's browser microphone input."""
    audio_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_file.write(audio_bytes)
            audio_path = audio_file.name
        segments, _ = get_whisper_model().transcribe(
            audio_path,
            language="en",
            beam_size=1,
            vad_filter=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
