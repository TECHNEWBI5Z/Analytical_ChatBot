import re
from pathlib import Path

import streamlit as st

from charts import show_chart
from db import get_schema, run_read_query
from llm import question_to_sql
from sql_safety import validate_and_limit
from voice import transcribe_audio

st.set_page_config(page_title="Brinjal Insights", page_icon="🍆", layout="wide")

HERO_IMAGE = Path(__file__).parent / "assets" / "eggplant-varieties.jpg"

st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(135deg, #fbf8fc 0%, #f4f8f1 55%, #f9f3e6 100%); }
      [data-testid="stSidebar"] { background: linear-gradient(180deg, #30173d 0%, #51255f 100%); }
      [data-testid="stSidebar"] * { color: #fffdfd; }
      .hero-title { font-size: 3rem; font-weight: 800; color: #3b1648; letter-spacing: -0.05em; margin: 0; }
      .hero-copy { font-size: 1.08rem; color: #62486b; margin-top: 0.6rem; max-width: 38rem; }
      .tag { display: inline-block; border-radius: 999px; padding: 0.35rem 0.75rem; margin: 0.8rem 0.35rem 0 0; background: #e9d8ef; color: #4a1858; font-size: 0.86rem; font-weight: 650; }
      .hero-image img { border-radius: 22px; box-shadow: 0 12px 30px rgba(59, 22, 72, 0.20); }
      .section-label { color: #4b1c58; font-size: 1.25rem; font-weight: 750; margin-top: 1.2rem; }
      [data-testid="stChatInput"] { border: 1px solid #b78fc4; border-radius: 14px; background: #fff; }
      [data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_text, hero_photo = st.columns((1.45, 1), vertical_alignment="center")
with hero_text:
    st.markdown('<p class="hero-title">Brinjal Insights 🍆</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">Explore eggplant breeding-trial data through natural-language questions, voice input, read-only MySQL analysis, and interactive trait visualizations, with parameter-driven analytics for flexible exploration.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="tag">Plant traits</span><span class="tag">Growth analytics</span><span class="tag">Local AI</span>',
        unsafe_allow_html=True,
    )
with hero_photo:
    st.image(HERO_IMAGE, use_container_width=True)

st.markdown('<p class="section-label">Ask your data</p>', unsafe_allow_html=True)

with st.sidebar:
    if HERO_IMAGE.exists():
        st.image(HERO_IMAGE, use_container_width=True)
    st.header("🍆 Data explorer")
    st.caption("Plant growth & morphology analytics")
    st.divider()
    st.header("Database schema")
    if st.button("Refresh schema"):
        get_schema.cache_clear()
    try:
        st.code(get_schema(), language="text")
    except Exception as error:
        st.error(f"Cannot read schema: {error}")
    st.divider()
    st.caption("Eggplant varieties photo: J.E. Fee / Wikimedia Commons (CC BY 2.0)")

typed_question = st.chat_input(
    "Example: Compare average RootLength between Root_fst and Root_scd, or show genotype 101 traits"
)
st.divider()
st.subheader("Ask by voice")
if "voice_input_id" not in st.session_state:
    st.session_state.voice_input_id = 0

# A new widget key clears the completed recording after it has been transcribed.
audio_question = st.audio_input(
    "Record an English question",
    help="Transcription starts automatically when recording finishes.",
    key=f"voice_audio_{st.session_state.voice_input_id}",
)
if audio_question:
    try:
        with st.spinner("Transcribing locally with Whisper..."):
            voice_question = transcribe_audio(audio_question.getvalue())
        if voice_question:
            st.session_state.pending_voice_question = voice_question
        else:
            st.session_state.latest_error = "I could not hear a question. Please record again and speak clearly."
    except Exception as error:
        st.session_state.latest_error = f"Voice transcription failed: {error}"
    finally:
        st.session_state.voice_input_id += 1
    st.rerun()

# chat_input resets itself after submission. A voice transcription is kept only
# long enough to execute this one request, then the microphone input is blank again.
question = typed_question or st.session_state.pop("pending_voice_question", None)
if question:
    try:
        if re.match(r"^\s*(SELECT|WITH|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b", question, re.IGNORECASE):
            raise ValueError("Please ask in plain English, for example: `Show the first 10 rows from phy_fst`.")
        with st.spinner("Creating a safe query locally..."):
            answer = question_to_sql(question, get_schema())
            if not answer["sql"]:
                raise ValueError(answer["explanation"] or "I could not form a query for that question.")
            sql = validate_and_limit(answer["sql"])
            data = run_read_query(sql)
        st.session_state.latest_result = {
            "question": question,
            "explanation": answer["explanation"],
            "sql": sql,
            "data": data,
            "chart_id": st.session_state.get("chart_id", 0) + 1,
        }
        st.session_state.chart_id = st.session_state.latest_result["chart_id"]
    except Exception as error:
        st.session_state.latest_error = str(error)

if "latest_error" in st.session_state:
    st.error(st.session_state.pop("latest_error"))

if "latest_result" in st.session_state:
    result = st.session_state.latest_result
    with st.chat_message("user"):
        st.write(result["question"])
    with st.chat_message("assistant"):
        st.write(result["explanation"] or "Here are the results.")
        with st.expander("SQL used"):
            st.code(result["sql"], language="sql")
        st.dataframe(result["data"], use_container_width=True, hide_index=True)
        st.caption(f"{len(result['data'])} row(s) returned")
        show_chart(result["data"], result["chart_id"])
