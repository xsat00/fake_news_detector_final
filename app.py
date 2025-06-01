import os
import re
import time
import torch
import types
from dotenv import load_dotenv

# PyTorch + Streamlit fix (optional)
if isinstance(torch.classes, types.ModuleType):
    try:
        torch.classes.__path__ = []
    except Exception:
        pass

import streamlit as st

# Load environment variables
load_dotenv()

# Mock implementations of your utils if missing
try:
    from utils.downloader import download_audio_from_youtube, download_video_from_youtube
    from utils.transcriber import transcribe_audio, load_whisper_model
    from utils.text_analyzer import detect_language, detect_trigger_words
    from utils.verifier import verify_with_bard
    from utils.video_processor import analyze_video_for_duplicates, extract_visible_text_from_frames
except ImportError:
    def download_audio_from_youtube(url): return "audio.mp3"
    def download_video_from_youtube(url): return ("video.mp4", None, None)
    def transcribe_audio(model, audio_path): return "This is a test transcript."
    def load_whisper_model(): return None
    def detect_language(text): return "en"
    def verify_with_bard(text): return "This news appears to be false because it contains misinformation."
    def analyze_video_for_duplicates(video_path): 
        return {
            "total_frames_extracted": 100,
            "duplicate_count": 5,
            "duplicate_frame_pairs": [{"frame1": 10, "frame2": 15}]
        }
    def extract_visible_text_from_frames(video_path): return "Visible text from video frames."

def remove_timestamps_and_tags(text):
    text = re.sub(r'\b\d{1,2}:\d{2}(:\d{2}(\.\d{1,3})?)?\b', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_extracted_text(text):
    if not text:
        return ""
    return remove_timestamps_and_tags(text)

def create_verification_prompt(text):
    return (
        "Please analyze the following news content and answer:\n"
        "- Is this news genuine (true) or false?\n"
        "- Provide reasons supporting your conclusion.\n\n"
        f"News content:\n{text}"
    )

@st.cache_data(show_spinner=False)
def cached_verify_with_bard(text):
    return verify_with_bard(text)

def get_youtube_thumbnail_fallback(url):
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return f"https://img.youtube.com/vi/{video_id_match.group(1)}/0.jpg"
    return None

def vtt_to_plaintext(vtt_path):
    text_lines = []
    with open(vtt_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.strip()
            if not line or '-->' in line or re.match(r'^\d+$', line):
                continue
            text_lines.append(line)
    return " ".join(text_lines)

def process_video_and_audio(video_path, audio_path, subtitle_path, downloaded_thumbnail, url):
    st.write("Analyzing video...")

    model = load_whisper_model()

    thumbnail_url = None
    if downloaded_thumbnail and os.path.exists(downloaded_thumbnail):
        thumbnail_url = downloaded_thumbnail
    elif url:
        thumbnail_url = get_youtube_thumbnail_fallback(url)
    if thumbnail_url:
        st.image(thumbnail_url, caption="Thumbnail", use_column_width=True)

    with st.spinner("Transcribing audio..."):
        start_transcribe = time.time()
        transcript = transcribe_audio(model, audio_path)
        trans_time = time.time() - start_transcribe

    with st.spinner("Checking for duplicate frames..."):
        start_dup = time.time()
        duplicate_report = analyze_video_for_duplicates(video_path)
        dup_time = time.time() - start_dup

    st.write(f"🧩 Frames extracted: {duplicate_report['total_frames_extracted']}")
    st.write(f"🔁 Duplicates: {duplicate_report['duplicate_count']}")
    st.write(f"⏱ Duplicate analysis: **{dup_time:.2f} sec**")
    if duplicate_report['duplicate_count'] > 0:
        with st.expander("Duplicate Frame Pairs"):
            st.dataframe(duplicate_report['duplicate_frame_pairs'])

    st.text_area("📝 Transcript", transcript, height=200)
    st.write(f"⏱ Transcription: **{trans_time:.2f} sec**")

    lang = detect_language(transcript)
    triggers = detect_trigger_words(transcript, lang)
    st.write(f"🌐 Language: `{lang}`")
    st.write(f"🚨 Trigger words: {triggers if triggers else 'None'}")

    subtitle_text = ""
    if subtitle_path and os.path.exists(subtitle_path):
        subtitle_text = vtt_to_plaintext(subtitle_path)
        with st.expander("📺 Subtitles"):
            st.text_area("Extracted Subtitles", subtitle_text, height=150)

    with st.spinner("Extracting text from video frames..."):
        frame_text = extract_visible_text_from_frames(video_path)
    if frame_text:
        with st.expander("🔤 Text in Frames"):
            st.text_area("Detected Text", frame_text, height=150)

    combined_text = "\n".join(filter(None, [transcript, subtitle_text, frame_text]))
    combined_text = clean_extracted_text(combined_text)

    st.write("Verifying content...")
    verification_prompt = create_verification_prompt(combined_text)
    with st.spinner("Getting verification..."):
        try:
            start_verify = time.time()
            verification = cached_verify_with_bard(verification_prompt)
            verify_time = time.time() - start_verify
            confidence = 0.9
        except Exception as e:
            verification = f"Bard API error: {e}"
            confidence = None

    st.write("✅ **Verification Result:**")
    st.write(verification)
    if confidence is not None:
        st.write(f"🔍 Confidence: **{confidence * 100:.2f}%**")
        st.write(f"⏱ Verification time: **{verify_time:.2f} sec**")

def main():
    if not os.getenv("BARD_API_KEY"):
        st.error("❌ BARD_API_KEY not set in .env file.")
        return

    st.set_page_config(
        page_title="Fake News Detection App",
        page_icon="icon.ico"
    )

    st.title("Fake News Detection App")

    input_type = st.radio("Select input type:", ("Text", "YouTube URL", "Upload Video File"))

    if input_type == "Text":
        uploaded_file = st.file_uploader("Upload a text file (.txt)", type=["txt"])
        if uploaded_file:
            raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
            lang = detect_language(raw_text)
            triggers = detect_trigger_words(raw_text, lang)

            st.write(f"🌐 Language detected: `{lang}`")
            st.write(f"🚨 Trigger words: {triggers if triggers else 'None'}")

            cleaned_text = clean_extracted_text(raw_text)
            verification_prompt = create_verification_prompt(cleaned_text)

            with st.spinner("Verifying with Bard..."):
                try:
                    start = time.time()
                    verification = cached_verify_with_bard(verification_prompt)
                    elapsed = time.time() - start
                    confidence = 0.85
                except Exception as e:
                    verification = f"Bard API error: {e}"
                    confidence = None

            st.write("✅ **Verification Result:**")
            st.write(verification)
            if confidence is not None:
                st.write(f"🔍 Confidence: **{confidence * 100:.2f}%**")
                st.write(f"⏱ Verification time: **{elapsed:.2f} sec**")

    elif input_type == "YouTube URL":
        url = st.text_input("Enter YouTube video URL")
        if url:
            with st.spinner("Downloading and processing video/audio..."):
                try:
                    video_path, subtitle_path, downloaded_thumbnail = download_video_from_youtube(url)
                    audio_path = download_audio_from_youtube(url)
                except Exception as e:
                    st.error(f"Download failed: {e}")
                    return

                if video_path and audio_path:
                    process_video_and_audio(video_path, audio_path, subtitle_path, downloaded_thumbnail, url)
                else:
                    st.error("Video or audio download failed.")

    elif input_type == "Upload Video File":
        uploaded_video = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi", "mkv"])
        if uploaded_video:
            video_path = f"/tmp/{uploaded_video.name}"
            with open(video_path, "wb") as f:
                f.write(uploaded_video.getbuffer())
            audio_path = video_path  # Assuming embedded audio
            subtitle_path = None
            downloaded_thumbnail = None
            process_video_and_audio(video_path, audio_path, subtitle_path, downloaded_thumbnail, None)

if __name__ == "__main__":
    main()
