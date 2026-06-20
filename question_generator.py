import random
import re
from curriculum_parser import CurriculumDatabase, BALABADI_CURRICULUM

def generate_multiple_choice_question(target_word, correct_answer, curriculum_pool, total_options=4):
    """
    Guarantees that the correct answer is absolutely included in the options 
    and handles complex Telugu scripts properly.
    """
    # Initialize choices array with the correct answer immediately
    choices = [correct_answer]
    
    # Extract unique potential distractors from the curriculum pool
    all_distractors = list(set([item for item in curriculum_pool if item != correct_answer]))
    
    # Safety Check: If we don't have enough distinct distractors, backfill with standard alphabet elements
    if len(all_distractors) < (total_options - 1):
        backup_letters = ['అ', 'ఆ', 'ఇ', 'ఈ', 'క', 'ఖ', 'గ', 'ఘ', 'చ', 'ఛ']
        all_distractors.extend([let for let in backup_letters if let != correct_answer])
        all_distractors = list(set(all_distractors))

    # Randomly select unique distractors to fill up the remaining option slots
    selected_distractors = random.sample(all_distractors, total_options - 1)
    choices.extend(selected_distractors)
    
    # Shuffle the combined list so the correct answer isn't always in the first slot
    random.shuffle(choices)
    
    # Return the structured choices array
    return choices


class QuestionGenerator:
    """Generates dynamic educational questions based on the active curriculum database."""
    def __init__(self, db: CurriculumDatabase):
        self.db = db

    def generate(self, module_id, level=1):
        """
        Generates a question dictionary based on module_id:
        """
        if module_id == 1 or module_id == "vowels_consonants":
            return self._generate_alphabet(level)
        elif module_id == 2 or module_id == "spelling_words":
            return self._generate_spelling(level)
        elif module_id == 3 or module_id == "vocabulary_definitions":
            return self._generate_vocabulary(level)
        elif module_id == 4 or module_id == "sentence_formation":
            return self._generate_sentence_formation(level)
        elif module_id == 5 or module_id == "reading_comprehension":
            return self._generate_reading_comprehension(level)
        else:
            return self._generate_alphabet(level)

    def _generate_alphabet(self, level):
        pool = self.db.curriculum.get("alphabet", BALABADI_CURRICULUM["alphabet"])
        item = random.choice(pool)
        
        question_text = f"'{item['item']}' ఏ అక్షరంతో మొదలవుతుంది?"
        english_sub = f"Which letter starts the word '{item['item']}'?"
        correct_ans = item["correct"]
        all_chars = [x["correct"] for x in pool]
        
        choices = generate_multiple_choice_question(item["item"], correct_ans, all_chars, total_options=4)
        
        return {
            "module": "vowels_consonants",
            "type": "multiple_choice",
            "question": question_text,
            "english_subtitle": english_sub,
            "target": correct_ans,
            "roman": "",
            "options": choices,
            "answer": correct_ans,
            "speech_prompt": f"Which letter starts the word {item['item'].split('(')[0].strip()}?",
            "hint": f"It starts with '{correct_ans}'"
        }

    def _generate_spelling(self, level):
        pool = self.db.curriculum.get("spelling", BALABADI_CURRICULUM["spelling"])
        item = random.choice(pool)
        
        word = item["word"]
        scrambled = item["scrambled"]
        
        return {
            "module": "spelling_words",
            "type": "scrambled_letters",
            "question": f"అక్షరాలను సరిచేసి పదాన్ని రాయండి: {', '.join(scrambled)}",
            "english_subtitle": f"Arrange the letters to spell: {item['display']}",
            "target": word,
            "roman": "",
            "scrambled": scrambled,
            "answer": word,
            "speech_prompt": f"Arrange the scrambled letters to spell {word}",
            "hint": f"The full word is '{word}'"
        }

    def _generate_vocabulary(self, level):
        pool = self.db.curriculum.get("vocabulary", BALABADI_CURRICULUM["vocabulary"])
        item = random.choice(pool)
        
        question_text = f"'{item['item']}' ని తెలుగులో ఏమంటారు?"
        english_sub = f"How do you say this in Telugu?"
        correct_ans = item["correct"]
        all_words = [x["correct"] for x in pool]
        
        choices = generate_multiple_choice_question(item["item"], correct_ans, all_words, total_options=4)
        
        return {
            "module": "vocabulary_definitions",
            "type": "multiple_choice",
            "question": question_text,
            "english_subtitle": english_sub,
            "target": correct_ans,
            "roman": "",
            "options": choices,
            "answer": correct_ans,
            "speech_prompt": f"What is the Telugu word for {item['correct'].split('(')[-1].replace(')','').strip()}?",
            "hint": f"The answer is {correct_ans}"
        }

    def _generate_sentence_formation(self, level):
        pool = self.db.curriculum.get("sentences", BALABADI_CURRICULUM["sentences"])
        item = random.choice(pool)
        sentence = item["sentence"]
        words = item.get("words", [w.strip() for w in sentence.split() if w.strip()])
        scrambled = words.copy()
        random.shuffle(scrambled)
        
        return {
            "module": "sentence_formation",
            "type": "drag_drop_sentence",
            "question": f"సరైన వరుసలో ఉంచి వాక్యం రాయండి: {sentence}",
            "english_subtitle": f"Arrange the words: {item['meaning']}",
            "target": sentence,
            "roman": item.get("roman", ""),
            "scrambled": scrambled,
            "answer": words,
            "speech_prompt": f"Arrange the words to spell the sentence",
            "hint": f"The sentence starts with '{words[0]}'"
        }

    def _generate_reading_comprehension(self, level):
        return {
            "module": "reading_comprehension",
            "type": "multiple_choice",
            "question": "ఒక ఊరిలో ఒక కాకి ఉంది. కాకికి చాలా దాహం వేసింది. కాకి నీటి కోసం వెతికింది.",
            "english_subtitle": "Read the story: In a village there was a crow. The crow was very thirsty. It searched for water.",
            "target": "కాకి",
            "roman": "",
            "options": ["కాకి", "పిచుక", "కోడి", "హంస"],
            "answer": "కాకి",
            "speech_prompt": "Who was thirsty in the story?",
            "hint": "The answer is కాకి"
        }
