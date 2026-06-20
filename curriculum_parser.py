import os
import re
import json
import pdfplumber
from PyPDF2 import PdfReader

# A safe terminal printing helper to prevent Windows Cp1252 encoding crashes! 🌟
def safe_print(message):
    try:
        print(message)
    except UnicodeEncodeError:
        try:
            print(message.encode('ascii', 'replace').decode('ascii'))
        except Exception:
            pass

BALABADI_CURRICULUM = {
    "vowels": [
        {"char": "అ", "example": "అమ్మ", "sound": "a", "roman": "Amma"},
        {"char": "ఆ", "example": "ఆవు", "sound": "aa", "roman": "Aavu"},
        {"char": "ఇ", "example": "ఇల్లు", "sound": "i", "roman": "Illu"},
        {"char": "ఈ", "example": "ఈల", "sound": "ee", "roman": "Eela"},
        {"char": "ఉ", "example": "ఉడుత", "sound": "u", "roman": "Uduta"},
        {"char": "ఊ", "example": "ఊయల", "sound": "oo", "roman": "Ooyala"},
        {"char": "ఎ", "example": "ఎలుక", "sound": "e", "roman": "Eluka"},
        {"char": "ఏ", "example": "ఏనుగు", "sound": "ae", "roman": "Aenugu"},
        {"char": "ఐ", "example": "ఐదు", "sound": "ai", "roman": "Aidu"},
        {"char": "ఒ", "example": "ఒంటె", "sound": "o", "roman": "Onte"},
        {"char": "ఓ", "example": "ఓడ", "sound": "oo", "roman": "Oda"},
        {"char": "ఔ", "example": "ఔషధం", "sound": "au", "roman": "Aushadham"}
    ],
    "consonants": [
        {"char": "క", "example": "కప్ప", "sound": "ka", "roman": "Kappa"},
        {"char": "గ", "example": "గంప", "sound": "ga", "roman": "Gampa"},
        {"char": "చ", "example": "చక్రం", "sound": "cha", "roman": "Chakram"},
        {"char": "వీ", "example": "వీణ", "sound": "vee", "roman": "Veena"}
    ],
    "alphabet": [
        {"item": "అమ్మ (Amma)", "correct": "అ"},
        {"item": "ఆవు (Aavu)", "correct": "ఆ"},
        {"item": "ఇల్లు (Illu)", "correct": "ఇ"},
        {"item": "ఈల (Eela)", "correct": "ఈ"},
        {"item": "ఉడుత (Uduta)", "correct": "ఉ"},
        {"item": "ఊయల (Ooyala)", "correct": "ఊ"},
        {"item": "ఎలుక (Eluka)", "correct": "ఎ"},
        {"item": "ఏనుగు (Aenugu)", "correct": "ఏ"},
        {"item": "ఒంటె (Onte)", "correct": "ఒ"},
        {"item": "ఓడ (Oda)", "correct": "ఓ"},
        {"item": "కలం (Kalam)", "correct": "క"},
        {"item": "గంప (Gampa)", "correct": "గ"},
        {"item": "వీణ (Veena)", "correct": "వీ"}
    ],
    "vocabulary": [
        {"item": "🐠", "correct": "చేప (Fish)", "word": "చేప", "meaning": "Fish", "roman": "Chepa"},
        {"item": "🛶", "correct": "పడవ (Boat)", "word": "పడవ", "meaning": "Boat", "roman": "Padava"},
        {"item": "🏡", "correct": "ఇల్లు (House)", "word": "ఇల్లు", "meaning": "House", "roman": "Illu"},
        {"item": "🌳", "correct": "చెట్టు (Tree)", "word": "చెట్టు", "meaning": "Tree", "roman": "Chettu"},
        {"item": "🖊️", "correct": "కలం (Pen)", "word": "కలం", "meaning": "Pen", "roman": "Kalam"},
        {"item": "కప్ప", "correct": "కప్ప (Frog)", "word": "కప్ప", "meaning": "Frog", "roman": "Kappa"},
        {"item": "ఆవు", "correct": "ఆవు (Cow)", "word": "ఆవు", "meaning": "Cow", "roman": "Aavu"},
        {"item": "ఎలుక", "correct": "ఎలుక (Rat)", "word": "ఎలుక", "meaning": "Rat", "roman": "Eluka"}
    ],
    "spelling": [
        {"word": "అమ్మ", "scrambled": ["మ", "అ", "్మ"], "display": "అ_మ్మ"},
        {"word": "ఆవు", "scrambled": ["వు", "ఆ"], "display": "ఆ_వు"},
        {"word": "ఈల", "scrambled": ["ల", "ఈ"], "display": "ఈ_ల"}
    ],
    "sentences": [
        {"sentence": "ఇది ఒక ఆవు", "meaning": "This is a cow", "roman": "Idi oka aavu", "words": ["ఇది", "ఒక", "ఆవు"]}
    ],
    "stories": [
        {"title": "చిన్న కథ", "passage": "ఒక ఊరిలో ఒక కాకి ఉండేది.", "meaning": "In a village, there was a crow.", "questions": []}
    ]
}

DEFAULT_CURRICULUM = BALABADI_CURRICULUM

class CurriculumDatabase:
    """Manages learning content extracted from standard curriculum text or loaded from default vocabulary lists."""
    def __init__(self, data_file_path=None):
        self.data_file_path = data_file_path
        self.curriculum = DEFAULT_CURRICULUM.copy()
        if data_file_path and os.path.exists(data_file_path):
            self.load_from_file()

    def load_from_file(self):
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Let's ensure structure is preserved and we merge gracefully!
                for key in DEFAULT_CURRICULUM.keys():
                    if key in loaded:
                        self.curriculum[key] = loaded[key]
            safe_print("Yay! We successfully loaded the custom Balabadi syllabus database! 🌟")
        except Exception as e:
            # Encouraging log fallback statement
            safe_print(f"Hi there! We had a tiny splash of trouble reading your custom syllabus file, but no worries at all! We're using our standard Balabadi defaults. Details: {e}")

    def save_to_file(self):
        if self.data_file_path:
            try:
                with open(self.data_file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.curriculum, f, ensure_ascii=False, indent=2)
                safe_print("Splendid! We've saved the latest additions to our syllabus file! 📝")
            except Exception as e:
                # Friendly error warning statement
                safe_print(f"Oops! We couldn't save the curriculum changes to your file, but we will keep them safe in memory for this session! Details: {e}")

    def add_vocabulary_word(self, word, meaning, roman=""):
        # Let's check for duplicates first so we don't crowd the cards
        if not any(v.get("word") == word or v.get("correct") == word for v in self.curriculum["vocabulary"]):
            self.curriculum["vocabulary"].append({
                "word": word,
                "meaning": meaning,
                "roman": roman or word,
                "item": meaning,
                "correct": f"{word} ({meaning})"
            })
            self.save_to_file()
            return True
        return False

    def add_sentence(self, sentence, meaning, roman=""):
        if not any(s.get("sentence") == sentence for s in self.curriculum.setdefault("sentences", [])):
            words = [w.strip() for w in sentence.split() if w.strip()]
            self.curriculum["sentences"].append({
                "sentence": sentence,
                "meaning": meaning,
                "roman": roman or sentence,
                "words": words
            })
            self.save_to_file()
            return True
        return False


def parse_telugu_pdf(pdf_path, database: CurriculumDatabase):
    """
    Parses a Telugu curriculum PDF to extract learning materials.
    Looks for pattern matching and populates the database dynamically.
    """
    extracted_text = ""
    # Let's try our trusty pdfplumber tool first!
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
    except Exception as plumber_error:
        safe_print(f"pdfplumber had a tiny stretch of trouble: {plumber_error}. Let's let our backup helper PyPDF2 try to read this workbook! 🚀")
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
        except Exception as pypdf_error:
            safe_print(f"PyPDF2 also hit a bump: {pypdf_error}. We might need a cleanly structured text PDF!")
            return False, "We tried our best, but we couldn't read the text in this PDF. Please double check if it's scanned or copy-protected! 🌟"

    if not extracted_text.strip():
        return False, "We scanned the document, but it seems to be empty or an image PDF. Let's try uploading a text-based PDF instead! 📖"

    # Let's extract Telugu-English vocabulary pairs
    word_pairs = re.findall(r'([\u0c00-\u0c7f]+)\s*[-–—:]\s*([a-zA-Z\s,]+)', extracted_text)
    words_added = 0
    for telugu, english in word_pairs:
        telugu = telugu.strip()
        english = english.strip()
        if len(telugu) > 1 and len(english) > 1:
            if database.add_vocabulary_word(telugu, english):
                words_added += 1

    # Let's also look for parenthesized translation lines: అమ్మ (Mother)
    paren_pairs = re.findall(r'([\u0c00-\u0c7f]+)\s*\(([a-zA-Z\s,]+)\)', extracted_text)
    for telugu, english in paren_pairs:
        telugu = telugu.strip()
        english = english.strip()
        if len(telugu) > 1 and len(english) > 1:
            if database.add_vocabulary_word(telugu, english):
                words_added += 1

    # Let's find short Telugu sentences with English meanings: "ఇది ఆవు - This is a cow."
    sentence_pairs = re.findall(r'((?:[\u0c00-\u0c7f]+\s+)+[\u0c00-\u0c7f]+)\s*[-–—:]\s*([a-zA-Z\s,\.\?!]+)', extracted_text)
    sentences_added = 0
    for tel_sent, eng_sent in sentence_pairs:
        tel_sent = tel_sent.strip()
        eng_sent = eng_sent.strip()
        if len(tel_sent.split()) > 1 and len(eng_sent) > 5:
            if database.add_sentence(tel_sent, eng_sent):
                sentences_added += 1

    return True, f"Hooray! We successfully parsed the curriculum PDF and found {words_added} vocabulary words and {sentences_added} sentences! You are amazing! 🎉"
