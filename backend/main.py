import ctypes, sys, os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_PATH = os.path.join(BASE_DIR, "words.json")

def _load_lib():
    if sys.platform == "win32":   name = "scorer.dll"
    elif sys.platform == "darwin": name = "scorer.dylib"
    else:                          name = "scorer.so"
    path = os.path.join(BASE_DIR, name)
    lib = ctypes.CDLL(path)
    lib.score_text.argtypes = [ctypes.c_char_p]
    lib.score_text.restype  = ctypes.c_int
    try:
        lib.reload_words.argtypes = []
        lib.reload_words.restype = None
    except AttributeError:
        pass
    return lib

_lib = _load_lib()

def _load_words():
    for p in [WORDS_PATH, "words.json", "/app/words.json", "../words.json"]:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            continue
    return {}

_words = _load_words()

VALID_CATEGORIES = {
    "appearance-shaming",
    "body-shaming",
    "exclusion",
    "gaslighting",
    "harassment",
    "humiliation",
    "identity-targeted",
    "insult",
    "intimidation",
    "mockery",
    "profanity-targeted",
    "self-harm encouragement",
    "sexual-harassment",
    "threat"
}

def reload_words():
    global _words
    _words = _load_words()
    if hasattr(_lib, "reload_words"):
        _lib.reload_words()
    return _words

def get_words():
    return _words

def _normalize_phrase(phrase: str) -> str:
    return " ".join(phrase.lower().split())

def _unique_words() -> dict:
    unique = {}

    for phrase, data in _words.items():
        normalized = _normalize_phrase(phrase)
        if normalized:
            unique[normalized] = data

    return unique

def add_word_entry(phrase: str, score: int, category: str) -> dict:
    phrase = _normalize_phrase(phrase)
    category = category.strip()

    if not phrase:
        raise ValueError("Phrase is required")
    if not category:
        raise ValueError("Category is required")
    if category not in VALID_CATEGORIES:
        raise ValueError("Choose a valid category")
    if score < 0:
        raise ValueError("Score must be 0 or higher")

    words = _load_words()
    for existing_phrase in list(words.keys()):
        if _normalize_phrase(existing_phrase) == phrase:
            del words[existing_phrase]

    words[phrase] = {"score": score, "category": category}

    tmp_path = WORDS_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, WORDS_PATH)

    reload_words()
    return {"phrase": phrase, "score": score, "category": category}

THRESHOLDS = {"HIGH": 15, "MEDIUM": 7, "LOW": 1}

ACTIONS = {
    "HIGH":   "BLOCK",
    "MEDIUM": "WARN",
    "LOW":    "MONITOR",
    "NONE":   "ALLOW"
}

EXPLANATIONS = {
    "HIGH":   "Severe harmful content detected. Immediate action required.",
    "MEDIUM": "Potentially harmful content detected. Review recommended.",
    "LOW":    "Mild content flagged. Monitoring advised.",
    "NONE":   "No harmful content detected."
}

def get_level(score: int) -> str:
    if score >= THRESHOLDS["HIGH"]:   return "HIGH"
    if score >= THRESHOLDS["MEDIUM"]: return "MEDIUM"
    if score >= THRESHOLDS["LOW"]:    return "LOW"
    return "NONE"

def _is_boundary(text: str, index: int) -> bool:
    return index < 0 or index >= len(text) or not text[index].isalnum()

def _count_phrase_matches(text: str, phrase: str) -> int:
    if not text or not phrase:
        return 0

    count = 0
    start = text.find(phrase)
    while start != -1:
        end = start + len(phrase)
        if _is_boundary(text, start - 1) and _is_boundary(text, end):
            count += 1
        start = text.find(phrase, start + 1)

    return count

def _score_from_words(lower_text: str) -> int:
    total = 0

    for phrase, data in _unique_words().items():
        match_count = _count_phrase_matches(lower_text, phrase)
        if match_count > 0:
            total += int(data.get("score", 0)) * match_count

    return total

def analyze_message(text: str) -> dict:
    lower_text = text.lower()
    score      = _score_from_words(lower_text)
    level      = get_level(score)

    matched_words  = []
    reason_codes   = []
    categories     = []

    for phrase, data in _unique_words().items():
        match_count = _count_phrase_matches(lower_text, phrase)

        if match_count > 0:
            matched_words.extend([phrase] * match_count)
            cat = data.get("category", "")
            if cat and cat not in categories:
                categories.append(cat)
            if cat and cat not in reason_codes:
                reason_codes.append(cat)

    return {
        "score":         score,
        "level":         level,
        "action":        ACTIONS[level],
        "explanation":   EXPLANATIONS[level],
        "reason_codes":  reason_codes,
        "matched_words": matched_words,
        "categories":    categories
    }
