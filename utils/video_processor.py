import cv2
import numpy as np
import os
import pandas as pd
import pytesseract
from collections import defaultdict
from skimage.metrics import structural_similarity as ssim

# For Windows users: set the path to your installed Tesseract executable
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
def extract_visible_text_from_frames(video_path, frame_skip=30):
    cap = cv2.VideoCapture(video_path)
    visible_text = []

    frame_count = 0
    success, frame = cap.read()

    while success:
        if frame_count % frame_skip == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, lang='eng+tel+hin')  # Extend with more languages as needed
            if text.strip():
                visible_text.append(text.strip())
        frame_count += 1
        success, frame = cap.read()

    cap.release()
    return "\n".join(visible_text)


def analyze_video_for_duplicates(video_path, frame_skip=5, similarity_threshold=0.97):
    cap = cv2.VideoCapture(video_path)
    frame_id = 0
    prev_frame = None
    duplicate_pairs = []
    total_frames = 0

    frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_id % frame_skip == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append((frame_id, gray))
            total_frames += 1
        frame_id += 1

    for i in range(len(frames) - 1):
        id1, f1 = frames[i]
        id2, f2 = frames[i + 1]
        score = ssim(f1, f2)
        if score > similarity_threshold:
            duplicate_pairs.append((id1, id2))

    cap.release()

    return {
        "total_frames_extracted": total_frames,
        "duplicate_count": len(duplicate_pairs),
        "duplicate_frame_pairs": pd.DataFrame(duplicate_pairs, columns=["Frame A", "Frame B"])
    }
