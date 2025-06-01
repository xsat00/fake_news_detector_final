import streamlit as st
import yt_dlp
import tempfile
import os
import cv2
from PIL import Image
import pytesseract
from langdetect import detect
import hashlib
import whisper
import numpy as np
import json
import re
import time

# === Configuration ===
MAX_FRAMES = 50  # max frames to process to limit runtime
TRIGGER_WORDS_FILE = "trigger_words.json"  # load trigger words JSON
WHISPER_MODEL = "base"  # Whisper model name

# === Load Trigger Words ===
@st.cache_data
def load_trigger_words():
    if os.path.exists(TRIGGER_WORDS_FILE):
        with open(TRIGGER_WORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # fallback example trigger words in English + Hindi (add more)
        return {
            "en": ["fake", "hoax", "rumor", "false", "misinformation"],
            "hi": ["झूठा", "फेक", "अफवाह", "गलत"],
        }

trigger_words = load_trigger_words()

# === Helper Functions ===

def download_video(url):
    temp_dir = tempfile.mkdtemp()
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(temp_dir, 'video.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    return path

def extract_frames(video_path, max_frames=MAX_FRAMES):
    vidcap = cv2.VideoCapture(video_path)
    frames = []
    count = 0
    success = True
    while success and count < max_frames:
        success, frame = vidcap.read()
        if success:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            count += 1
    vidcap.release()
    return frames

def frame_hash(frame):
    """Create a hash of the image frame for duplicate detection"""
    img = Image.fromarray(frame).resize((64,64)).convert('L')  # grayscale small thumbnail
    return hashlib.md5(img.tobytes()).hexdigest()

def detect_duplicate_frames(frames):
    hashes = [frame_hash(f) for f in frames]
    duplicates = {}
    for i, h in enumerate(hashes):
        duplicates.setdefault(h, []).append(i)
    # Keep only hashes with duplicates (more than 1 frame)
    return {k:v for k,v in duplicates.items() if len(v) > 1}

def ocr_on_frames(frames):
    texts = []
    for f in frames:
        pil_img = Image.fromarray(f)
        text = pytesseract.image_to_string(pil_img).strip()
        texts.append(text)
    return texts

def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

def scan_trigger_words(texts, trigger_words):
    """Scan texts for any trigger words per language"""
    hits = []
    for text in texts:
        lang = detect_language(text)
        tw_list = trigger_words.get(lang, []) + trigger_words.get("en", [])
        for tw in tw_list:
            if re.search(r"\b" + re.escape(tw) + r"\b", text, re.IGNORECASE):
                hits.append((lang, tw, text))
    return hits

def transcribe_audio(video_path):
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(video_path)
    return result["text"]

def clean_text(text):
    return text.strip().replace("\n", " ")

# Placeholder Bard API call function (replace with your real API calls)
def fact_check_script(script_text):
    # This should call your Bard or other API for fact checking.
    # Here just a stub:
    time.sleep(1)  # simulate delay
    if "fake" in script_text.lower() or "hoax" in script_text.lower():
        return "⚠️ Warning: Script contains suspicious content."
    else:
        return "✅ Script appears genuine."

# === Streamlit UI ===

st.title("🚩 Fake News Detection App")

st.markdown("""
Upload a video file or provide a YouTube URL. The app will:
- Extract frames and detect duplicates
- Run OCR on frames for visible text detection
- Extract and transcribe audio script (supports multiple languages)
- Scan text for fake news trigger words
- Fact check the transcribed script with Bard API (placeholder)
""")

input_type = st.radio("Select input type:", ["YouTube URL", "Upload Video"])

video_path = None
if input_type == "YouTube URL":
    url = st.text_input("Enter YouTube URL:")
    if url:
        with st.spinner("Downloading video..."):
            try:
                video_path = download_video(url)
                st.success("Downloaded video successfully.")
            except Exception as e:
                st.error(f"Error downloading video: {e}")
elif input_type == "Upload Video":
    uploaded = st.file_uploader("Upload your video file", type=["mp4","mov","avi","mkv"])
    if uploaded is not None:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(uploaded.read())
        temp_file.flush()
        video_path = temp_file.name
        st.success("Uploaded video successfully.")

if video_path:
    # Extract frames
    with st.spinner("Extracting frames..."):
        frames = extract_frames(video_path)
        st.write(f"Extracted {len(frames)} frames.")

    # Duplicate frames detection
    with st.spinner("Detecting duplicate frames..."):
        duplicates = detect_duplicate_frames(frames)
        if duplicates:
            st.warning(f"Found {len(duplicates)} sets of duplicate frames.")
            for h, idxs in duplicates.items():
                st.write(f"Duplicate frame indexes: {idxs}")
        else:
            st.success("No duplicate frames detected.")

    # OCR on frames
    with st.spinner("Running OCR on frames..."):
        ocr_texts = ocr_on_frames(frames)

    st.subheader("Sample OCR Extracted Texts (First 5 frames):")
    for i, text in enumerate(ocr_texts[:5]):
        lang = detect_language(text) if text else "No text"
        st.markdown(f"**Frame {i+1} (lang: {lang}):**")
        st.text(text if text else "No visible text detected")

    # Scan trigger words in OCR texts
    ocr_hits = scan_trigger_words(ocr_texts, trigger_words)
    if ocr_hits:
        st.error(f"Trigger words detected in OCR texts:")
        for lang, word, txt in ocr_hits:
            st.write(f"- Language: {lang} | Word: '{word}' | Text snippet: {txt[:100]}...")
    else:
        st.success("No trigger words detected in OCR texts.")

    # Transcribe audio
    with st.spinner("Transcribing audio (this may take a while)..."):
        try:
            transcription = transcribe_audio(video_path)
            cleaned_script = clean_text(transcription)
            st.subheader("Transcribed Audio Script:")
            st.write(cleaned_script)
        except Exception as e:
            st.error(f"Audio transcription failed: {e}")
            transcription = None

    # Scan trigger words in transcription
    if transcription:
        script_hits = scan_trigger_words([transcription], trigger_words)
        if script_hits:
            st.error(f"Trigger words detected in audio transcription:")
            for lang, word, txt in script_hits:
                st.write(f"- Language: {lang} | Word: '{word}'")
        else:
            st.success("No trigger words detected in audio transcription.")

    # Fact-check script via Bard (placeholder)
    if transcription:
        with st.spinner("Fact-checking the script..."):
            fact_check_result = fact_check_script(transcription)
            if fact_check_result.startswith("⚠️"):
                st.error(fact_check_result)
            else:
                st.success(fact_check_result)

# Cleanup button (optional)
if st.button("Clear temporary video files"):
    try:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        st.success("Temporary files cleared.")
    except Exception as e:
        st.error(f"Error clearing temp files: {e}")
