import os
import secrets
import re
import random
from flask import Flask, request, jsonify, send_from_directory, session
from curriculum_parser import CurriculumDatabase, parse_telugu_pdf
from question_generator import QuestionGenerator

# A safe terminal printing helper to prevent Windows Cp1252 encoding crashes! 🌟
def safe_print(message):
    try:
        print(message)
    except UnicodeEncodeError:
        try:
            print(message.encode('ascii', 'replace').decode('ascii'))
        except Exception:
            pass

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(24))

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

# Setup local database. Let's load our friendly Telugu Balabadi database!
DATABASE_FILE = os.path.join(os.path.dirname(__file__), 'curriculum_db.json')
db = CurriculumDatabase(DATABASE_FILE)
q_gen = QuestionGenerator(db)

# In-memory session store to keep track of our little friends' game progress!
GAME_SESSIONS = {}

def get_game_state(session_id):
    if session_id not in GAME_SESSIONS:
        # Hello new explorer! Let's start your game journey with some fresh stats! 🚀
        GAME_SESSIONS[session_id] = {
            "level": 1,
            "xp": 0,
            "score": 0,
            "stars": 0,
            "streak": 0,
            "active_module": None,
            "questions_correct": 0,
            "questions_total": 0,
            "current_question": None,
            "timer_seconds": 90, # Generous 90s timer for level 1 to keep things stress-free!
            "bait": 0,
            "max_bait": 3,
            "inventory": [],
            "inventory_limit": 5,
            "upgrades": {
                "rod": 1,
                "backpack": 1,
                "bait_bucket": 1
            }
        }
    return GAME_SESSIONS[session_id]

def normalize_telugu_text(text):
    """
    Cleans Telugu and English text by removing punctuation, collapsing spaces, 
    and standardizing inputs to give children a fair, stress-free evaluation! 🌟
    """
    if not isinstance(text, str):
        return ""
    # Strip spaces and lowercase (helpful for English translations)
    cleaned = text.strip().lower()
    # Remove punctuation marks that speech recognition often appends
    cleaned = re.sub(r'[\.\?,\!|"\']', '', cleaned)
    # Collapse multiple spaces into one
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Remove internal spaces completely to compare letter tokens safely
    cleaned = cleaned.replace(" ", "")
    return cleaned

def simplify_telugu_phonetics(text):
    """
    Simplifies Telugu phonetics for toddlers (e.g. short vs long vowels, 
    aspirated vs unaspirated consonants) to normalize speech transcriptions.
    """
    if not isinstance(text, str):
        return ""
    replacements = {
        "ఆ": "అ",
        "ఈ": "ఇ",
        "ఊ": "ఉ",
        "ఏ": "ఎ",
        "ఓ": "ఒ",
        "ఖ": "క",
        "ఘ": "గ",
        "ఛ": "చ",
        "ఝ": "జ",
        "ఠ": "ట",
        "ఢ": "డ",
        "థ": "త",
        "ధ": "ద",
        "ఫ": "ప",
        "భ": "బ",
        "ళ": "ల",
        "ఱ": "ర",
        "ష": "శ",
        "స": "శ"
    }
    simplified = text
    for target, replacement in replacements.items():
        simplified = simplified.replace(target, replacement)
    return simplified

def simplify_telugu_doubles(text):
    """
    Strips virama characters and collapses doubled consonants, allowing toddlers'
    simplified pronunciations to pass verification.
    """
    if not isinstance(text, str):
        return ""
    # Strip the virama (\u0c4d)
    text_no_virama = text.replace("\u0c4d", "")
    if not text_no_virama:
        return ""
    # Collapse duplicate characters next to each other
    collapsed = [text_no_virama[0]]
    for char in text_no_virama[1:]:
        if char == collapsed[-1]:
            continue
        collapsed.append(char)
    return "".join(collapsed)

def edit_distance(s1, s2):
    """
    Calculates Levenshtein edit distance between s1 and s2.
    Used for toddler pronunciation typo tolerance.
    """
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]

def find_curriculum_item(correct_str, database):
    """
    Searches vowels, consonants, vocabulary, and sentences for the corresponding
    dictionary item to extract roman transliteration or synonyms.
    """
    norm_correct = normalize_telugu_text(correct_str)
    if not norm_correct:
        return None
        
    # Search Vowels
    for item in database.curriculum.get("vowels", []):
        if (normalize_telugu_text(item.get("char")) == norm_correct or 
            normalize_telugu_text(item.get("sound")) == norm_correct or
            normalize_telugu_text(item.get("example")) == norm_correct or
            normalize_telugu_text(item.get("roman")) == norm_correct):
            return item
            
    # Search Consonants
    for item in database.curriculum.get("consonants", []):
        if (normalize_telugu_text(item.get("char")) == norm_correct or 
            normalize_telugu_text(item.get("sound")) == norm_correct or
            normalize_telugu_text(item.get("example")) == norm_correct or
            normalize_telugu_text(item.get("roman")) == norm_correct):
            return item
            
    # Search Vocabulary
    for item in database.curriculum.get("vocabulary", []):
        if (normalize_telugu_text(item.get("word")) == norm_correct or 
            normalize_telugu_text(item.get("meaning")) == norm_correct or
            normalize_telugu_text(item.get("roman")) == norm_correct):
            return item
            
    # Search Sentences
    for item in database.curriculum.get("sentences", []):
        if (normalize_telugu_text(item.get("sentence")) == norm_correct or 
            normalize_telugu_text(item.get("meaning")) == norm_correct or
            normalize_telugu_text(item.get("roman")) == norm_correct):
            return item
            
    return None

def is_speech_match(user_answer, correct_answer, database):
    """
    Checks if user_answer spoken text is a match under pronunciation tolerance system.
    """
    if not user_answer:
        return False
        
    # Standardize strings
    if isinstance(correct_answer, list):
        correct_str = " ".join(correct_answer)
        norm_correct = "".join([normalize_telugu_text(w) for w in correct_answer])
    else:
        correct_str = str(correct_answer)
        norm_correct = normalize_telugu_text(correct_str)
        
    norm_user = normalize_telugu_text(str(user_answer))
    
    # 1. Exact match check
    if norm_user == norm_correct:
        return True
        
    # 2. Lookup in curriculum database (e.g. check transliteration/examples/roman/english synonyms)
    item = find_curriculum_item(correct_str, database)
    if item:
        allowed_fields = ["char", "sound", "example", "roman", "meaning", "word", "sentence"]
        for field in allowed_fields:
            val = item.get(field)
            if val:
                if isinstance(val, list):
                    joined_val = "".join([normalize_telugu_text(w) for w in val])
                    if joined_val == norm_user:
                        return True
                else:
                    if normalize_telugu_text(str(val)) == norm_user:
                        return True
                        
    # 3. Simplify phonetic vowel lengths and aspirations
    simplified_user = simplify_telugu_phonetics(norm_user)
    simplified_correct = simplify_telugu_phonetics(norm_correct)
    
    if simplified_user == simplified_correct:
        return True
        
    # 4. Collapse double consonants
    doubles_user = simplify_telugu_doubles(simplified_user)
    doubles_correct = simplify_telugu_doubles(simplified_correct)
    
    if doubles_user == doubles_correct:
        return True
        
    # 5. Check if child said example word instead of character, or character instead of example word
    if len(norm_correct) == 1 and item and "example" in item:
        norm_example = normalize_telugu_text(item["example"])
        if norm_user == norm_example or simplify_telugu_phonetics(norm_user) == simplify_telugu_phonetics(norm_example):
            return True
            
    # 6. Levenshtein edit distance check (typos, mishearings)
    # Allow 1 edit distance for words >= 3, and 2 edit distance for phrases >= 8
    dist = edit_distance(doubles_user, doubles_correct)
    if len(doubles_correct) >= 8:
        if dist <= 2:
            return True
    elif len(doubles_correct) >= 3:
        if dist <= 1:
            return True
            
    return False

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/state', methods=['GET'])
def state():
    session_id = request.args.get('session_id') or session.get('session_id')
    if not session_id:
        session_id = secrets.token_hex(16)
        session['session_id'] = session_id
        safe_print(f"Welcome, new explorer! Created a brand new game session: {session_id} 🎒")
        
    state_data = get_game_state(session_id)
    return jsonify({
        "session_id": session_id,
        "state": state_data
    })

@app.route('/api/reset', methods=['POST'])
def reset():
    session_id = request.json.get('session_id') or session.get('session_id')
    if session_id in GAME_SESSIONS:
        del GAME_SESSIONS[session_id]
        safe_print(f"Resetting progress for explorer: {session_id}. A fresh start is always fun! 🌈")
    
    new_session_id = session_id or secrets.token_hex(16)
    session['session_id'] = new_session_id
    state_data = get_game_state(new_session_id)
    
    return jsonify({
        "session_id": new_session_id,
        "state": state_data,
        "message": "We have reset your scoreboard! Let's start a new adventure! 🚀"
    })

@app.route('/api/modules', methods=['GET'])
def modules():
    # Return warm, child-friendly descriptions of our 5 learning adventure zones!
    return jsonify([
        {
            "id": "vowels_consonants",
            "name": "అచ్చులు & హల్లులు",
            "english": "Vowels & Consonants",
            "description": "అక్షరాలను గుర్తించడం, పలకడం మరియు జత చేయడం నేర్చుకుందాం! 🎈",
            "description_english": "Let's learn to recognize, say, and match our core Telugu letters!",
            "unlocked": True,
            "icon": "🎈"
        },
        {
            "id": "spelling_words",
            "name": "పదాల అమరిక",
            "english": "Spelling Words",
            "description": "అక్షరాల ఆట! ఖాళీలను పూరిస్తూ కొత్త పదాలను తయారు చేద్దాం! 🧸",
            "description_english": "A fun game of letters! Let's fill in blanks and arrange blocks to build spelling skills!",
            "unlocked": True,
            "icon": "🧸"
        },
        {
            "id": "vocabulary_definitions",
            "name": "పదాల అర్ధాలు",
            "english": "Vocabulary Definitions",
            "description": "తెలుగు పదాలను వాటి అందమైన బొమ్మలు మరియు ఇంగ్లీష్ అర్ధాలతో జత చేద్దాం! 🦁",
            "description_english": "Let's learn what Telugu words mean by connecting them to their English translations!",
            "unlocked": True,
            "icon": "🦁"
        },
        {
            "id": "sentence_formation",
            "name": "వాక్య నిర్మాణం",
            "english": "Sentence Formation",
            "description": "చిన్న చిన్న మాటలను ఒకటిగా చేర్చి ఒక చక్కని వాక్యాన్ని చేద్దాం! 🧩",
            "description_english": "Let's put simple words side-by-side to make full, beautiful Telugu sentences!",
            "unlocked": True,
            "icon": "🧩"
        },
        {
            "id": "reading_comprehension",
            "name": "పఠన అవగాహన",
            "english": "Reading Comprehension",
            "description": "చిన్న కథ చదువుదాం, సరదా ప్రశ్నలకు జవాబులు చెబుదాం! 🏰",
            "description_english": "Let's read super sweet, short stories and answer simple questions together!",
            "unlocked": True,
            "icon": "🏰"
        }
    ])

@app.route('/api/generate-question', methods=['GET'])
def generate_question():
    session_id = request.args.get('session_id') or session.get('session_id')
    if not session_id:
        session_id = secrets.token_hex(16)
        session['session_id'] = session_id
        
    module_id = request.args.get('module')
    if not module_id:
        safe_print("Wait! We received a request to make a question, but no module was selected! 🔍")
        return jsonify({"error": "Oops! Please tell us which module you want to play! 🌟"}), 400
        
    state_data = get_game_state(session_id)
    state_data["active_module"] = module_id
    
    # Adaptive countdown scaling based on level
    # Level 1: 90s, Level 2: 75s, Level 3: 60s, Level 4: 45s, Level 5+: 30s
    level = state_data["level"]
    timer_seconds = max(30, 90 - (level - 1) * 15)
    state_data["timer_seconds"] = timer_seconds
    
    # Create the question
    question = q_gen.generate(module_id, level)
    
    # Store correct answer context in our secure server state
    state_data["current_question"] = {
        "answer": question["answer"],
        "module": module_id
    }
    
    # Duplicate and clean the answer field so the client has to solve it honestly!
    client_question = question.copy()
    del client_question["answer"]
    
    safe_print(f"Created a fresh {module_id} challenge for session {session_id} on level {level}! 🌟")
    return jsonify({
        "question": client_question,
        "timer_seconds": timer_seconds
    })

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    data = request.json or {}
    session_id = data.get('session_id') or session.get('session_id')
    user_answer = data.get('answer')
    is_speech = data.get('is_speech', False)
    
    if not session_id or session_id not in GAME_SESSIONS:
        safe_print(f"Oops! Received an answer submission, but the session ID {session_id} is missing or expired. 🔍")
        return jsonify({"error": "Oh no! We couldn't find your active game session. Let's start fresh!"}), 400
        
    state_data = GAME_SESSIONS[session_id]
    
    if user_answer == "__FISHING_XP__":
        bonus_xp = data.get("bonus_xp", 10)
        state_data["xp"] += bonus_xp
        state_data["score"] = state_data["xp"]
        return jsonify({
            "correct": True,
            "correct_answer": "",
            "message": "🐠 చేపను పట్టావు! (You caught a fish!)",
            "level_up": False,
            "state": state_data
        })
        
    current_q = state_data.get("current_question")
    if not current_q:
        return jsonify({"error": "Wait, friend! We don't have an active question ready yet. Let's generate one!"}), 400
        
    correct_answer = current_q["answer"]
    is_correct = False
    
    if is_speech:
        is_correct = is_speech_match(user_answer, correct_answer, db)
    else:
        # Let's perform a robust comparison using our Telugu normalizer!
        if isinstance(correct_answer, list):
            # List of words (used for sentence building)
            if isinstance(user_answer, list):
                # Clean and normalize each word
                user_normalized = [normalize_telugu_text(w) for w in user_answer]
                correct_normalized = [normalize_telugu_text(w) for w in correct_answer]
                is_correct = user_normalized == correct_normalized
            elif isinstance(user_answer, str):
                # Fallback string compare
                user_norm = normalize_telugu_text(user_answer)
                correct_norm = "".join([normalize_telugu_text(w) for w in correct_answer])
                is_correct = user_norm == correct_norm
        else:
            # Standard string answer (letters, spelling, vocabulary)
            user_norm = normalize_telugu_text(str(user_answer))
            correct_norm = normalize_telugu_text(str(correct_answer))
            is_correct = user_norm == correct_norm
        
    state_data["questions_total"] += 1
    
    # List of encouraging Telugu phrases
    praises = [
        "అద్భుతం! చాలా బాగుంది! (Excellent! Beautiful!) 🌟",
        "భలే చేసాവ്! నువ్వు గెలిచావు! (Great job! You won!) 🎉",
        "సబాష్! సరైన సమాధానం! (Superb! Correct answer!) 🏆",
        "శుభం! ఇలాగే కొనసాగించు! (Wonderful! Keep it up!) ❤️",
        "సూపర్! చాలా చక్కగా చేసావ్! (Super! Very well done!) 🌈"
    ]
    
    if is_correct:
        state_data["questions_correct"] += 1
        state_data["streak"] += 1
        # Give them 10 base XP plus a friendly streak bonus!
        xp_gain = 10 + min(5, state_data["streak"])
        state_data["xp"] += xp_gain
        state_data["score"] = state_data["xp"]
        
        # Add 1 unit of Bait, capped at max_bait
        max_b = state_data.setdefault("max_bait", 3)
        curr_b = state_data.setdefault("bait", 0)
        
        bait_gain = 1
        streak_bonus = False
        if state_data["streak"] % 5 == 0:
            bait_gain += 2
            streak_bonus = True
            
        state_data["bait"] = min(max_b, curr_b + bait_gain)
        
        # Level up rules: get 3 correct answers in a row or clear 4 questions overall
        if state_data["streak"] >= 3 or state_data["questions_correct"] % 4 == 0:
            state_data["level"] += 1
            state_data["stars"] += 1
            state_data["streak"] = 0 # reset streak on level up
            level_up = True
            safe_print(f"Hooray! Player leveled up to Level {state_data['level']}! 👑")
        else:
            level_up = False
            
        # Select a random encouraging Telugu praise phrase
        response_msg = praises[hash(session_id + str(state_data["xp"])) % len(praises)]
    else:
        # Don't break their spirits on wrong answers! Encourage them to try again.
        state_data["streak"] = 0
        level_up = False
        state_data["score"] = state_data["xp"]
        response_msg = "మళ్ళీ ప్రయత్నించు, నువ్వు చేయగలవు! (Try again, you can do it!) 💪"
        safe_print(f"No worries! Wrong answer checked. Correct was: {correct_answer}")
        
    # Clear the active question so they can generate a new challenge
    state_data["current_question"] = None
    
    return jsonify({
        "correct": is_correct,
        "correct_answer": correct_answer,
        "message": response_msg,
        "level_up": level_up,
        "streak_bonus": streak_bonus if is_correct else False,
        "state": state_data
    })

@app.route('/api/catch-fish', methods=['POST'])
def catch_fish():
    data = request.json or {}
    session_id = data.get('session_id') or session.get('session_id')
    
    if not session_id or session_id not in GAME_SESSIONS:
        return jsonify({"error": "Session missing or expired."}), 400
        
    state_data = GAME_SESSIONS[session_id]
    
    if state_data.get("bait", 0) <= 0:
        return jsonify({"error": "ఎర లేదు! (No bait! Answer questions to get bait.)"}), 400
        
    if len(state_data.get("inventory", [])) >= state_data.get("inventory_limit", 5):
        return jsonify({"error": "సంచి నిండిపోయింది! (Backpack is full! Sell fish at the dock.)"}), 400
        
    # Consume bait
    state_data["bait"] -= 1
    
    # Fish configurations
    fishes = [
        {"emoji": "🐠", "name": "బంగారు చేప (Goldfish)", "english": "Goldfish", "base_points": 15, "rarity": "common"},
        {"emoji": "🦀", "name": "పీత (Crab)", "english": "Crab", "base_points": 20, "rarity": "common"},
        {"emoji": "🦐", "name": "రొయ్య (Shrimp)", "english": "Shrimp", "base_points": 25, "rarity": "common"},
        {"emoji": "🐡", "name": "బుడగ చేప (Blowfish)", "english": "Blowfish", "base_points": 35, "rarity": "common"},
        {"emoji": "🐙", "name": "ఎనిమిది కాళ్ల చేప (Octopus)", "english": "Octopus", "base_points": 50, "rarity": "rare"},
        {"emoji": "🦈", "name": "సొరచేప పిల్లకు (Baby Shark)", "english": "Baby Shark", "base_points": 80, "rarity": "rare"},
        {"emoji": "🐬", "name": "సముద్ర స్నేహితుడు (Dolphin)", "english": "Dolphin", "base_points": 120, "rarity": "epic"},
        {"emoji": "🐳", "name": "భారీ తిమింగిలం (Whale)", "english": "Whale", "base_points": 250, "rarity": "legendary"}
    ]
    
    # Rod level affects probability of rarities
    rod_level = state_data.get("upgrades", {}).get("rod", 1)
    
    if rod_level == 1:
        weights = [85, 85, 85, 85, 12, 12, 3, 0]
    elif rod_level == 2:
        weights = [60, 60, 60, 60, 25, 25, 12, 3]
    elif rod_level == 3:
        weights = [40, 40, 40, 40, 35, 35, 18, 7]
    else: # rod lvl >= 4
        weights = [15, 15, 15, 15, 40, 40, 30, 15]
        
    caught = random.choices(fishes, weights=weights, k=1)[0].copy()
    
    # Rod level also multiplies fish value
    multiplier = 1.0
    if rod_level == 2:
        multiplier = 1.5
    elif rod_level == 3:
        multiplier = 2.0
    elif rod_level >= 4:
        multiplier = 3.0
        
    caught["value"] = int(caught["base_points"] * multiplier)
    caught["id"] = secrets.token_hex(4)
    
    state_data["inventory"].append(caught)
    
    safe_print(f"Session {session_id} caught a {caught['english']} worth {caught['value']} points!")
    return jsonify({
        "success": True,
        "fish": caught,
        "state": state_data
    })

@app.route('/api/sell-fish', methods=['POST'])
def sell_fish():
    data = request.json or {}
    session_id = data.get('session_id') or session.get('session_id')
    
    if not session_id or session_id not in GAME_SESSIONS:
        return jsonify({"error": "Session missing or expired."}), 400
        
    state_data = GAME_SESSIONS[session_id]
    
    inventory = state_data.get("inventory", [])
    if not inventory:
        return jsonify({"error": "సంచి ఖాళీగా ఉంది! (Backpack is empty!)", "points_earned": 0, "state": state_data}), 200
        
    earned_points = sum(item.get("value", 0) for item in inventory)
    
    state_data["xp"] += earned_points
    state_data["score"] = state_data["xp"]
    state_data["inventory"] = []
    
    safe_print(f"Session {session_id} sold fish for {earned_points} points!")
    return jsonify({
        "success": True,
        "points_earned": earned_points,
        "state": state_data
    })

@app.route('/api/buy-upgrade', methods=['POST'])
def buy_upgrade():
    data = request.json or {}
    session_id = data.get('session_id') or session.get('session_id')
    upgrade_type = data.get('upgrade_type') # 'rod', 'backpack', 'bait_bucket'
    
    if not session_id or session_id not in GAME_SESSIONS:
        return jsonify({"error": "Session missing or expired."}), 400
        
    state_data = GAME_SESSIONS[session_id]
    
    if upgrade_type not in ["rod", "backpack", "bait_bucket"]:
        return jsonify({"error": "Invalid upgrade type."}), 400
        
    current_upgrades = state_data.setdefault("upgrades", {"rod": 1, "backpack": 1, "bait_bucket": 1})
    current_level = current_upgrades.get(upgrade_type, 1)
    
    if current_level >= 4:
        return jsonify({"error": "గరిష్ట స్థాయికి చేరుకుంది! (Already at maximum level!)"}), 400
        
    # Cost config
    costs = {
        "rod": {2: 100, 3: 300, 4: 800},
        "backpack": {2: 75, 3: 150, 4: 225},
        "bait_bucket": {2: 50, 3: 150, 4: 400}
    }
    
    next_level = current_level + 1
    cost = costs[upgrade_type][next_level]
    
    if state_data.get("xp", 0) < cost:
        return jsonify({"error": "సరిపోవు పాయింట్లు లేవు! (Not enough points!)"}), 400
        
    # Deduct cost
    state_data["xp"] -= cost
    state_data["score"] = state_data["xp"]
    
    # Apply upgrade
    current_upgrades[upgrade_type] = next_level
    
    if upgrade_type == "backpack":
        limits = {2: 10, 3: 15, 4: 20}
        state_data["inventory_limit"] = limits[next_level]
    elif upgrade_type == "bait_bucket":
        limits = {2: 5, 3: 8, 4: 12}
        state_data["max_bait"] = limits[next_level]
        
    safe_print(f"Session {session_id} upgraded {upgrade_type} to level {next_level}!")
    return jsonify({
        "success": True,
        "upgrade_type": upgrade_type,
        "new_level": next_level,
        "state": state_data
    })

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        safe_print("Wait! We received a file upload request, but no file payload was attached! 📁")
        return jsonify({"error": "Oh no! We couldn't find any file in your request. Please select a PDF file!"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Oops! You did not select a file. Please pick a curriculum PDF!"}), 400
        
    if file and file.filename.endswith('.pdf'):
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        try:
            safe_print(f"Reading curriculum from: {file.filename}... This is exciting! 📚")
            success, message = parse_telugu_pdf(temp_path, db)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "error": message}), 500
    else:
        return jsonify({"error": "Oh, we can only read PDF files! Please upload a PDF curriculum. 📁"}), 400

if __name__ == '__main__':
    # Make sure static directory exists to serve assets
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
    safe_print("----------------------------------------------------------------------")
    safe_print("  విద్యా విజయం (Vidya Vijayam) educational application is starting up!")
    safe_print("  We're ready to teach Telugu to our little stars! 🌟")
    safe_print("  Join us at: http://127.0.0.1:5000")
    safe_print("----------------------------------------------------------------------")
    app.run(debug=True, port=5000)
