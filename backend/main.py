import json
import re
import ctypes
from pathlib import Path
from collections import Counter
from ctypes import Structure, c_char, c_int
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
WORDS_FILE = BASE_DIR / "words.json"
CUSTOM_WORDS_FILE = BASE_DIR / "custom_words.json"
OUTPUT_FILE = BASE_DIR / "last_result.json"
AUDIT_LOG_FILE = BASE_DIR / "audit_log.jsonl"
SCORER_DLL = BASE_DIR / "scorer.dll"

VALID_CATEGORIES = [
    "insult",
    "mockery",
    "humiliation",
    "exclusion",
    "harassment",
    "threat",
    "self-harm encouragement",
    "identity-targeted",
    "sexual-harassment",
    "appearance-shaming",
    "body-shaming",
    "gaslighting",
    "profanity-targeted",
    "profanity-general",
    "doxxing",
    "impersonation",
    "cyberstalking",
    "defamation"
]

VALID_SEVERITIES = ["low", "medium", "high", "critical"]
VALID_TARGET_TYPES = ["individual", "group", "identity", "unknown"]
VALID_DIRECTNESS = ["direct", "indirect"]
VALID_INTENTS = ["attack", "mock", "exclude", "intimidate", "sexualize", "degrade", "shame", "manipulate"]
VALID_PLATFORM_CONTEXTS = ["general", "chat", "social", "forum", "gaming"]

CATEGORY_DEFAULTS = {
    "mockery": {"severity": "low", "target_type": "individual", "directness": "direct", "intent": "mock", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "insult": {"severity": "medium", "target_type": "individual", "directness": "direct", "intent": "attack", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "humiliation": {"severity": "medium", "target_type": "individual", "directness": "direct", "intent": "degrade", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "exclusion": {"severity": "medium", "target_type": "individual", "directness": "direct", "intent": "exclude", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "harassment": {"severity": "medium", "target_type": "individual", "directness": "direct", "intent": "attack", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "threat": {"severity": "critical", "target_type": "individual", "directness": "direct", "intent": "intimidate", "platform_context": "general", "needs_context": False, "repeat_sensitive": True},
    "self-harm encouragement": {"severity": "critical", "target_type": "individual", "directness": "direct", "intent": "intimidate", "platform_context": "general", "needs_context": False, "repeat_sensitive": True},
    "identity-targeted": {"severity": "high", "target_type": "identity", "directness": "direct", "intent": "degrade", "platform_context": "general", "needs_context": False, "repeat_sensitive": True},
    "sexual-harassment": {"severity": "high", "target_type": "individual", "directness": "direct", "intent": "sexualize", "platform_context": "general", "needs_context": False, "repeat_sensitive": True},
    "appearance-shaming": {"severity": "medium", "target_type": "individual", "directness": "direct", "intent": "shame", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "body-shaming": {"severity": "high", "target_type": "individual", "directness": "direct", "intent": "shame", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "gaslighting": {"severity": "high", "target_type": "individual", "directness": "indirect", "intent": "manipulate", "platform_context": "general", "needs_context": True, "repeat_sensitive": True},
    "profanity-targeted": {"severity": "high", "target_type": "individual", "directness": "direct", "intent": "attack", "platform_context": "general", "needs_context": False, "repeat_sensitive": True},
    "profanity-general": {"severity": "low", "target_type": "unknown", "directness": "indirect", "intent": "attack", "platform_context": "general", "needs_context": True, "repeat_sensitive": False},
    "doxxing": {"severity": "critical", "target_type": "individual", "directness": "direct", "intent": "intimidate", "platform_context": "social", "needs_context": False, "repeat_sensitive": True},
    "impersonation": {"severity": "high", "target_type": "individual", "directness": "indirect", "intent": "manipulate", "platform_context": "social", "needs_context": True, "repeat_sensitive": True},
    "cyberstalking": {"severity": "critical", "target_type": "individual", "directness": "direct", "intent": "intimidate", "platform_context": "social", "needs_context": False, "repeat_sensitive": True},
    "defamation": {"severity": "high", "target_type": "individual", "directness": "indirect", "intent": "degrade", "platform_context": "social", "needs_context": True, "repeat_sensitive": True}
}

TARGET_WORDS = {"you", "your", "u", "ur", "youre", "you're", "@user"}

class LexiconEntry(Structure):
    _fields_ = [
        ("phrase", c_char * 128),
        ("score", c_int),
        ("category", c_char * 64),
    ]

class ScanResult(Structure):
    _fields_ = [
        ("matched_phrases", (c_char * 128) * 256),
        ("matched_categories", (c_char * 64) * 256),
        ("matched_scores", c_int * 256),
        ("match_count", c_int),
        ("total_score", c_int),
    ]

def load_json_file(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json_file(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_words():
    base_words = load_json_file(WORDS_FILE)
    custom_words = load_json_file(CUSTOM_WORDS_FILE)
    merged = base_words.copy()
    merged.update(custom_words)
    return merged

WORDS = load_words()

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    text = re.sub(r"[@#]\w+", " @user ", text)

    replacements = {
        r"f[\W_]*u[\W_]*c[\W_]*k": "fuck",
        r"s[\W_]*h[\W_]*i[\W_]*t": "shit",
        r"b[\W_]*i[\W_]*t[\W_]*c[\W_]*h": "bitch",
        r"k[\W_]*y[\W_]*s": "kys",
        r"k[\W_]*m[\W_]*s": "kms",
        r"\bu\b": "you",
        r"\bur\b": "your"
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"[^a-z0-9\s@']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def load_c_library():
    if not SCORER_DLL.exists():
        raise FileNotFoundError(f"Missing scorer.dll at {SCORER_DLL}")

    c_lib = ctypes.CDLL(str(SCORER_DLL))
    c_lib.scan_text_c.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(LexiconEntry),
        c_int,
        ctypes.POINTER(ScanResult)
    ]
    c_lib.scan_text_c.restype = None

    c_lib.classify_score_c.argtypes = [c_int]
    c_lib.classify_score_c.restype = c_int

    c_lib.normalize_text_c.argtypes = [ctypes.c_char_p, ctypes.c_char_p, c_int]
    c_lib.normalize_text_c.restype = None
    return c_lib

c_lib = load_c_library()

def analyze_with_c(message: str):
    entries = []

    for phrase, info in WORDS.items():
        phrase_bytes = normalize_text(phrase).encode("utf-8")[:127]
        category_bytes = info.get("category", "harassment").encode("utf-8")[:63]
        score = int(info.get("score", 0))

        entry = LexiconEntry()
        entry.phrase = phrase_bytes
        entry.score = score
        entry.category = category_bytes
        entries.append(entry)

    entry_array = (LexiconEntry * len(entries))(*entries)
    result = ScanResult()

    c_lib.scan_text_c(
        message.encode("utf-8"),
        entry_array,
        len(entries),
        ctypes.byref(result)
    )

    matched_entries = []
    category_counts = Counter()

    for i in range(result.match_count):
        phrase = bytes(result.matched_phrases[i]).split(b"\0", 1)[0].decode("utf-8")
        category = bytes(result.matched_categories[i]).split(b"\0", 1)[0].decode("utf-8")
        score = int(result.matched_scores[i])

        matched_entries.append({
            "phrase": phrase,
            "score": score,
            "category": category,
            "mode": "trie_exact"
        })
        category_counts[category] += 1

    normalized_buffer = ctypes.create_string_buffer(4096)
    c_lib.normalize_text_c(message.encode("utf-8"), normalized_buffer, 4096)
    normalized = normalized_buffer.value.decode("utf-8")

    return normalized, matched_entries, result.total_score, category_counts

def detect_targeting(tokens):
    return any(token in TARGET_WORDS for token in tokens)

def calculate_repetition_bonus(matched_entries):
    phrase_counts = Counter(entry["phrase"] for entry in matched_entries)
    return sum((count - 1) * 2 for count in phrase_counts.values() if count > 1)

def calculate_toxicity_accumulation(matched_entries, tokens):
    bonus = 0
    if len(matched_entries) >= 3:
        bonus += 2

    high_risk_categories = {"threat", "self-harm encouragement", "sexual-harassment"}
    if any(entry["category"] in high_risk_categories for entry in matched_entries):
        bonus += 3

    if len(tokens) <= 5 and len(matched_entries) > 0:
        bonus += 1

    return bonus

def build_explanation(categories, targeted, repetition_bonus, toxicity_bonus):
    if not categories:
        return "No strong harassment indicators detected."

    top_categories = [cat for cat, _ in categories.most_common(2)]
    explanation = "Detected " + " and ".join(top_categories) + " language."

    if targeted:
        explanation += " Message appears directly targeted."
    if repetition_bonus > 0:
        explanation += " Repeated harmful patterns increased the risk."
    if toxicity_bonus > 0:
        explanation += " Combined toxicity signals increased the final score."

    return explanation

def get_action(level):
    if level == "HIGH":
        return "BLOCK"
    if level == "MEDIUM":
        return "REVIEW"
    return "ALLOW"

def get_reason_codes(matched_entries, targeted, repetition_bonus, toxicity_bonus):
    reasons = []

    if targeted:
        reasons.append("targeted_abuse")
    if repetition_bonus > 0:
        reasons.append("repetition")
    if toxicity_bonus > 0:
        reasons.append("toxicity_accumulation")

    categories = {entry["category"] for entry in matched_entries}
    if "self-harm encouragement" in categories:
        reasons.append("self_harm")
    if "threat" in categories:
        reasons.append("threat")
    if "sexual-harassment" in categories:
        reasons.append("sexual_harassment")
    if "identity-targeted" in categories:
        reasons.append("identity_attack")

    if not reasons and matched_entries:
        reasons.append("keyword_match")

    return reasons

def save_last_result(result: dict):
    save_json_file(OUTPUT_FILE, result)

def append_audit_log(result: dict):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "result": result
    }
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def prompt_choice(label, options, default_value):
    print(f"{label} options: {', '.join(options)}")
    while True:
        value = input(f"{label} [{default_value}]: ").strip()
        if not value:
            return default_value
        if value in options:
            return value
        print("Invalid choice.")

def prompt_bool(label, default_value):
    default_text = "true" if default_value else "false"
    while True:
        value = input(f"{label} [{default_text}] (true/false): ").strip().lower()
        if not value:
            return default_value
        if value in {"true", "t", "yes", "y", "1"}:
            return True
        if value in {"false", "f", "no", "n", "0"}:
            return False
        print("Invalid choice. Type true or false.")

def infer_platform_context(phrase):
    gaming_terms = {"npc", "skill issue", "delete the game", "uninstall", "bot", "mid", "washed", "you fell off"}
    social_terms = {"ratio", "common l", "take the l", "womp womp", "chronically online", "discord mod"}
    lower_phrase = phrase.lower()

    for term in gaming_terms:
        if term in lower_phrase:
            return "gaming"
    for term in social_terms:
        if term in lower_phrase:
            return "social"
    return "general"

def get_category_defaults(category, phrase):
    defaults = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["harassment"]).copy()
    defaults["platform_context"] = infer_platform_context(phrase)
    return defaults

def dev_add_or_fix_entry(message):
    global WORDS

    print("\nDid I get this right? (y/n)")
    answer = input("> ").strip().lower()
    if answer != "n":
        return

    phrase = input("What phrase should be added/fixed?: ").strip()
    if not phrase:
        phrase = normalize_text(message)

    print("\nWhat type of insult is it?")
    category = prompt_choice("Category", VALID_CATEGORIES, "harassment")

    while True:
        score_input = input("Score [1-10] [4]: ").strip()
        if not score_input:
            score = 4
            break
        if score_input.isdigit() and 1 <= int(score_input) <= 10:
            score = int(score_input)
            break
        print("Invalid score.")

    defaults = get_category_defaults(category, phrase)

    severity = prompt_choice("Severity", VALID_SEVERITIES, defaults["severity"])
    target_type = prompt_choice("Target type", VALID_TARGET_TYPES, defaults["target_type"])
    directness = prompt_choice("Directness", VALID_DIRECTNESS, defaults["directness"])
    intent = prompt_choice("Intent", VALID_INTENTS, defaults["intent"])
    platform_context = prompt_choice("Platform context", VALID_PLATFORM_CONTEXTS, defaults["platform_context"])
    needs_context = prompt_bool("Needs context", defaults["needs_context"])
    repeat_sensitive = prompt_bool("Repeat sensitive", defaults["repeat_sensitive"])

    custom_words = load_json_file(CUSTOM_WORDS_FILE)
    normalized_phrase = normalize_text(phrase)

    custom_words[normalized_phrase] = {
        "score": score,
        "category": category,
        "severity": severity,
        "target_type": target_type,
        "directness": directness,
        "intent": intent,
        "platform_context": platform_context,
        "needs_context": needs_context,
        "repeat_sensitive": repeat_sensitive
    }

    save_json_file(CUSTOM_WORDS_FILE, custom_words)
    WORDS = load_words()

    print(f"\nSaved dev entry: {normalized_phrase}")
    print(json.dumps(custom_words[normalized_phrase], indent=2, ensure_ascii=False))

def analyze_message(message: str) -> dict:
    normalized, matched_entries, exact_score, category_counts = analyze_with_c(message)
    tokens = normalized.split()

    repetition_bonus = calculate_repetition_bonus(matched_entries)
    targeted = detect_targeting(tokens)
    targeting_bonus = 2 if targeted and exact_score > 0 else 0
    toxicity_bonus = calculate_toxicity_accumulation(matched_entries, tokens)

    total_score = exact_score + repetition_bonus + targeting_bonus + toxicity_bonus
    level_num = c_lib.classify_score_c(total_score)
    level = ["LOW", "MEDIUM", "HIGH"][level_num]
    action = get_action(level)
    reason_codes = get_reason_codes(matched_entries, targeted, repetition_bonus, toxicity_bonus)
    explanation = build_explanation(category_counts, targeted, repetition_bonus, toxicity_bonus)

    return {
        "success": True,
        "data": {
            "original_message": message,
            "normalized_message": normalized,
            "score": total_score,
            "level": level,
            "action": action,
            "reason_codes": reason_codes,
            "targeted": targeted,
            "repetition_bonus": repetition_bonus,
            "targeting_bonus": targeting_bonus,
            "toxicity_accumulation": toxicity_bonus,
            "matched_words": [entry["phrase"] for entry in matched_entries],
            "matched_details": matched_entries,
            "categories": dict(category_counts),
            "explanation": explanation
        },
        "errors": []
    }

def main():
    dev_mode = input("Enable dev mode? (y/n): ").strip().lower() == "y"

    while True:
        user_input = input("\nEnter a message (or type 'exit'): ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        result = analyze_message(user_input)
        save_last_result(result)
        append_audit_log(result)

        print("\nResult:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\nSaved to: {OUTPUT_FILE}")
        print(f"Audit log: {AUDIT_LOG_FILE}")

        if dev_mode:
            dev_add_or_fix_entry(user_input)

if __name__ == "__main__":
    main()