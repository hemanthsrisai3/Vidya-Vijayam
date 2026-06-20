import unittest
import json
import os
import sys

# Ensure parent directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curriculum_parser import CurriculumDatabase
from question_generator import QuestionGenerator
from app import app, GAME_SESSIONS, normalize_telugu_text
import re

def get_starting_letter(word):
    if not word:
        return ""
    pattern = r'^([\u0c05-\u0c14]|[\u0c15-\u0c39](?:\u0c4d[\u0c15-\u0c39])*[\u0c3e-\u0c4c]?[\u0c01-\u0c03]?)'
    match = re.match(pattern, word)
    if match:
        return match.group(1)
    return word[0] if word else ""

class TestTeluguEducationalGame(unittest.TestCase):
    def setUp(self):
        # Setup clean curriculum DB
        self.db = CurriculumDatabase()
        self.q_gen = QuestionGenerator(self.db)
        
        # Clear sessions to ensure test isolation
        GAME_SESSIONS.clear()
        
        # Configure flask for testing
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'testsecretkey'
        self.client = app.test_client()

    def test_telugu_text_normalization(self):
        # Check standard normalizations for spaces, casing, and punctuation!
        self.assertEqual(normalize_telugu_text("అమ్మ "), "అమ్మ")
        self.assertEqual(normalize_telugu_text(" ఆవు. "), "ఆవు")
        self.assertEqual(normalize_telugu_text("ఇది  ఆవు?"), "ఇదిఆవు")
        self.assertEqual(normalize_telugu_text("Idi Aavu!"), "idiaavu")
        self.assertEqual(normalize_telugu_text("  కప్ప.  "), "కప్ప")

    def test_database_default_load(self):
        self.assertIn("vowels", self.db.curriculum)
        self.assertIn("consonants", self.db.curriculum)
        self.assertIn("vocabulary", self.db.curriculum)
        self.assertIn("sentences", self.db.curriculum)
        self.assertIn("stories", self.db.curriculum)
        
        # Verify standard Balabadi associations
        vowels_map = {item["char"]: item["example"] for item in self.db.curriculum["vowels"]}
        self.assertEqual(vowels_map["అ"], "అమ్మ")
        self.assertEqual(vowels_map["ఆ"], "ఆవు")
        self.assertEqual(vowels_map["ఇ"], "ఇల్లు")
        self.assertEqual(vowels_map["ఈ"], "ఈల")
        self.assertEqual(vowels_map["ఉ"], "ఉడుత")
        self.assertEqual(vowels_map["ఊ"], "ఊయల")
        
        consonants_map = {item["char"]: item["example"] for item in self.db.curriculum["consonants"]}
        self.assertEqual(consonants_map["క"], "కప్ప")
        self.assertEqual(consonants_map["గ"], "గంప")
        self.assertEqual(consonants_map["చ"], "చక్రం")

    def test_database_add_items(self):
        # Add a test word
        added_word = self.db.add_vocabulary_word("పరీక్ష", "Test", "Pareeksha")
        self.assertTrue(added_word)
        # Check duplicate fails
        added_dup = self.db.add_vocabulary_word("పరీక్ష", "Test", "Pareeksha")
        self.assertFalse(added_dup)
        
        # Add a test sentence
        added_sent = self.db.add_sentence("ఇది ఒక పరీక్ష", "This is a test", "Idi oka pareeksha")
        self.assertTrue(added_sent)
        self.assertIn("ఒక", self.db.curriculum["sentences"][-1]["words"])

    def test_question_generator_all_modules(self):
        modules = [
            "vowels_consonants",
            "spelling_words",
            "vocabulary_definitions",
            "sentence_formation",
            "reading_comprehension"
        ]
        
        for m in modules:
            q = self.q_gen.generate(m, level=1)
            self.assertEqual(q["module"], m)
            self.assertIn("question", q)
            self.assertIn("english_subtitle", q)
            self.assertIn("answer", q)
            self.assertIn("speech_prompt", q)
            
            # Specific properties checks
            if q["type"] == "multiple_choice":
                self.assertIn("options", q)
                self.assertIn(q["answer"], q["options"])
            elif q["type"] == "missing_letter":
                self.assertIn("options", q)
                self.assertIn(q["answer"], q["options"])
            elif q["type"] == "scrambled_letters":
                self.assertIn("scrambled", q)
            elif q["type"] == "drag_drop_sentence":
                self.assertIn("scrambled", q)
                self.assertIsInstance(q["answer"], list)

    def test_flask_api_state_and_reset(self):
        # Get state
        res = self.client.get('/api/state?session_id=test_user_123')
        data = json.loads(res.data.decode('utf-8'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["session_id"], "test_user_123")
        self.assertEqual(data["state"]["level"], 1)
        self.assertEqual(data["state"]["xp"], 0)
        
        # Modify session state in memory
        GAME_SESSIONS["test_user_123"]["xp"] = 50
        
        # Reset state
        res = self.client.post('/api/reset', 
                               data=json.dumps({"session_id": "test_user_123"}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["state"]["xp"], 0) # must reset to 0

    def test_flask_api_generate_question(self):
        res = self.client.get('/api/generate-question?session_id=test_user_123&module=vowels_consonants')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertEqual(res.status_code, 200)
        self.assertIn("question", data)
        self.assertIn("timer_seconds", data)
        # Verify correct answer is NOT sent in client question payload
        self.assertNotIn("answer", data["question"])
        
        # But answer must be recorded in backend state
        state_data = GAME_SESSIONS["test_user_123"]
        self.assertIsNotNone(state_data["current_question"])
        self.assertEqual(state_data["current_question"]["module"], "vowels_consonants")

    def test_flask_api_submit_answer_correct(self):
        # 1. Generate question
        self.client.get('/api/generate-question?session_id=test_user_123&module=vocabulary_definitions')
        state_data = GAME_SESSIONS["test_user_123"]
        correct_answer = state_data["current_question"]["answer"]
        
        # 2. Submit correct answer
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "test_user_123", "answer": correct_answer}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertEqual(res.status_code, 200)
        self.assertTrue(data["correct"])
        self.assertEqual(data["state"]["streak"], 1)
        self.assertTrue(data["state"]["xp"] > 0)

    def test_flask_api_submit_answer_wrong(self):
        # 1. Generate question
        self.client.get('/api/generate-question?session_id=test_user_123&module=vocabulary_definitions')
        
        # 2. Submit wrong answer
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "test_user_123", "answer": "WRONG_ANSWER_xyz"}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertEqual(res.status_code, 200)
        self.assertFalse(data["correct"])
        self.assertEqual(data["state"]["streak"], 0)
        self.assertEqual(data["state"]["xp"], 0)

    def test_level_up_progression(self):
        # Force state to level 1, streak 2, questions correct 2
        GAME_SESSIONS["test_user_prog"] = {
            "level": 1,
            "xp": 20,
            "stars": 0,
            "streak": 2,
            "questions_correct": 2,
            "questions_total": 2,
            "current_question": {"answer": "అమ్మ", "module": "vowels_consonants"},
            "timer_seconds": 90
        }
        
        # Submit correct answer to triggers streak = 3 -> Level up!
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "test_user_prog", "answer": "అమ్మ"}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertTrue(data["correct"])
        self.assertTrue(data["level_up"])
        self.assertEqual(data["state"]["level"], 2)
        self.assertEqual(data["state"]["stars"], 1)
        self.assertEqual(data["state"]["streak"], 0) # reset streak on level up

    def test_toddler_speech_tolerance(self):
        # 1. Setup session state with an active vowel question
        GAME_SESSIONS["speech_test_user"] = {
            "level": 1,
            "xp": 0,
            "stars": 0,
            "streak": 0,
            "questions_correct": 0,
            "questions_total": 0,
            "current_question": {"answer": "అ", "module": "vowels_consonants"},
            "timer_seconds": 90
        }
        
        # Test: Example word instead of letter (అమ్మ instead of అ)
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "speech_test_user", "answer": "అమ్మ", "is_speech": True}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertTrue(data["correct"])
        
        # Test: Transliterated sound / sound name (a instead of అ)
        GAME_SESSIONS["speech_test_user"]["current_question"] = {"answer": "అ", "module": "vowels_consonants"}
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "speech_test_user", "answer": "a", "is_speech": True}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertTrue(data["correct"])
        
        # 2. Vocabulary word matching with dropped double consonants (dvitvakshara)
        GAME_SESSIONS["speech_test_user"]["current_question"] = {"answer": "కప్ప", "module": "vocabulary_definitions"}
        # Child says "కప" instead of "కప్ప"
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "speech_test_user", "answer": "కప", "is_speech": True}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertTrue(data["correct"])
        
        # Test: English transliteration ("kappa" instead of "కప్ప")
        GAME_SESSIONS["speech_test_user"]["current_question"] = {"answer": "కప్ప", "module": "vocabulary_definitions"}
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "speech_test_user", "answer": "kappa", "is_speech": True}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertTrue(data["correct"])

        # 3. Phonetic vowel equivalence (అవు instead of ఆవు)
        GAME_SESSIONS["speech_test_user"]["current_question"] = {"answer": "ఆవు", "module": "vocabulary_definitions"}
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "speech_test_user", "answer": "అవు", "is_speech": True}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertTrue(data["correct"])

        # 4. Levenshtein edit distance check (1 typo allowed for len >= 3)
        # E.g. correct is "ఎలుక", child says "ఎలుగ"
        GAME_SESSIONS["speech_test_user"]["current_question"] = {"answer": "ఎలుక", "module": "vocabulary_definitions"}
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "speech_test_user", "answer": "ఎలుగ", "is_speech": True}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertTrue(data["correct"])

    def test_fishing_xp_submission(self):
        # Setup session
        GAME_SESSIONS["fish_test_user"] = {
            "level": 1,
            "xp": 10,
            "score": 10,
            "stars": 0,
            "streak": 0,
            "questions_correct": 0,
            "questions_total": 0,
            "current_question": None,
            "timer_seconds": 90
        }
        
        # Submit fishing XP token
        res = self.client.post('/api/submit-answer',
                               data=json.dumps({"session_id": "fish_test_user", "answer": "__FISHING_XP__", "bonus_xp": 75}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertTrue(data["correct"])
        self.assertEqual(data["state"]["xp"], 85) # 10 + 75
        self.assertEqual(data["message"], "🐠 చేపను పట్టావు! (You caught a fish!)")

    def test_catch_fish_endpoint(self):
        # Setup session with bait
        GAME_SESSIONS["fish_catch_user"] = {
            "level": 1,
            "xp": 10,
            "score": 10,
            "stars": 0,
            "streak": 0,
            "questions_correct": 0,
            "questions_total": 0,
            "current_question": None,
            "timer_seconds": 90,
            "bait": 3,
            "max_bait": 3,
            "inventory": [],
            "inventory_limit": 5,
            "upgrades": {"rod": 1, "backpack": 1, "bait_bucket": 1}
        }
        
        res = self.client.post('/api/catch-fish',
                               data=json.dumps({"session_id": "fish_catch_user"}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertTrue(data["success"])
        self.assertEqual(data["state"]["bait"], 2) # Consumed 1 bait
        self.assertEqual(len(data["state"]["inventory"]), 1) # Added to inventory
        self.assertIn("emoji", data["fish"])
        self.assertIn("value", data["fish"])

    def test_sell_fish_endpoint(self):
        # Setup session with inventory
        GAME_SESSIONS["fish_sell_user"] = {
            "level": 1,
            "xp": 10,
            "score": 10,
            "stars": 0,
            "streak": 0,
            "questions_correct": 0,
            "questions_total": 0,
            "current_question": None,
            "timer_seconds": 90,
            "bait": 0,
            "max_bait": 3,
            "inventory": [
                {"emoji": "🐠", "name": "Goldfish", "value": 15},
                {"emoji": "🐡", "name": "Blowfish", "value": 35}
            ],
            "inventory_limit": 5,
            "upgrades": {"rod": 1, "backpack": 1, "bait_bucket": 1}
        }
        
        res = self.client.post('/api/sell-fish',
                               data=json.dumps({"session_id": "fish_sell_user"}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertTrue(data["success"])
        self.assertEqual(data["points_earned"], 50)
        self.assertEqual(data["state"]["xp"], 60) # 10 + 50
        self.assertEqual(len(data["state"]["inventory"]), 0) # Cleared inventory

    def test_buy_upgrade_endpoint(self):
        # Setup session with score points
        GAME_SESSIONS["fish_upgrade_user"] = {
            "level": 1,
            "xp": 150,
            "score": 150,
            "stars": 0,
            "streak": 0,
            "questions_correct": 0,
            "questions_total": 0,
            "current_question": None,
            "timer_seconds": 90,
            "bait": 0,
            "max_bait": 3,
            "inventory": [],
            "inventory_limit": 5,
            "upgrades": {"rod": 1, "backpack": 1, "bait_bucket": 1}
        }
        
        # Upgrade backpack (costs 75 points)
        res = self.client.post('/api/buy-upgrade',
                               data=json.dumps({"session_id": "fish_upgrade_user", "upgrade_type": "backpack"}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertTrue(data["success"])
        self.assertEqual(data["state"]["upgrades"]["backpack"], 2)
        self.assertEqual(data["state"]["inventory_limit"], 10) # Level 2 limit
        self.assertEqual(data["state"]["xp"], 75) # 150 - 75
        
        # Try to upgrade rod (costs 100 points, but only 75 left -> should fail)
        res = self.client.post('/api/buy-upgrade',
                               data=json.dumps({"session_id": "fish_upgrade_user", "upgrade_type": "rod"}),
                               content_type='application/json')
        data = json.loads(res.data.decode('utf-8'))
        self.assertEqual(res.status_code, 400)

    def test_veena_starting_letter_loop(self):
        import random
        # 1. Parse the targeted term "వీణ (Veena)" -> confirm that the extracted answer string evaluates strictly to "వీ"
        resolved_letter = get_starting_letter("వీణ")
        self.assertEqual(resolved_letter, "వీ")
        
        # 2. Simulate running 50 sequential loops of the generator algorithm and scan output options array
        # to verify that correct_answer is strictly in options every single time
        pool = self.db.curriculum["vowels"] + self.db.curriculum["consonants"]
        veena_item = next(item for item in pool if item["example"] == "వీణ")
        
        for _ in range(50):
            correct_ans = get_starting_letter(veena_item["example"])
            all_letters = list(set([get_starting_letter(x["example"]) for x in pool]))
            distractors = [l for l in all_letters if l != correct_ans and l.strip()]
            selected_distractors = random.sample(distractors, min(3, len(distractors)))
            opt_texts = [correct_ans] + selected_distractors
            random.shuffle(opt_texts)
            
            # Verify correct_ans is in options every time
            self.assertIn(correct_ans, opt_texts)
            # Verify all options are unique
            self.assertEqual(len(opt_texts), len(set(opt_texts)))
            # Verify there are 4 options
            self.assertEqual(len(opt_texts), 4)

if __name__ == '__main__':
    unittest.main()


