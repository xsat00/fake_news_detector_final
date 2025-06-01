from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
import json

# Load trigger words from JSON file
import os
TRIGGER_WORDS_PATH = os.path.join(os.path.dirname(__file__), '..', 'trigger_words.json')

def load_trigger_words():
    with open(TRIGGER_WORDS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

TRIGGER_WORDS = load_trigger_words()

def detect_language(text):
    try:
        lang = detect(text)
        if lang not in TRIGGER_WORDS:
            lang = "en"  # fallback
        return lang
    except LangDetectException:
        return "en"

def detect_trigger_words(text, lang):
    triggers = TRIGGER_WORDS.get(lang, TRIGGER_WORDS.get("en", []))
    found = [w for w in triggers if w.lower() in text.lower()]
    return list(set(found))


