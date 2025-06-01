import whisper
import streamlit as st

@st.cache_resource(show_spinner=False)
def load_whisper_model():
    return whisper.load_model("base")

def transcribe_audio(model, audio_path):
    result = model.transcribe(audio_path)
    return result["text"]
