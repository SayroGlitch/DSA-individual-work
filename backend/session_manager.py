from collections import defaultdict

sessions = {}

def add_to_session(sender: str, platform: str, result: dict) -> dict:
    key = f"{sender}:{platform}"

    if key not in sessions:
        sessions[key] = {
            "messages":           [],
            "high_count":         0,
            "medium_count":       0,
            "total":              0,
            "escalating":         False,
            "repeated_harassment":False,
            "dominant_categories":defaultdict(int),
            "pattern_level":      "NONE"
        }

    s     = sessions[key]
    level = result.get("level", "NONE")

    s["messages"].append(result)
    s["total"] += 1

    if level == "HIGH":
        s["high_count"] += 1
    elif level == "MEDIUM":
        s["medium_count"] += 1

    for cat in result.get("categories", []):
        s["dominant_categories"][cat] += 1

    if s["high_count"] >= 3:
        s["pattern_level"]       = "CRITICAL"
        s["repeated_harassment"] = True
    elif s["high_count"] >= 2:
        s["pattern_level"] = "HIGH"
        s["escalating"]    = True
    elif s["high_count"] >= 1 or s["medium_count"] >= 3:
        s["pattern_level"] = "MEDIUM"
    else:
        s["pattern_level"] = "LOW"

    return {
        "pattern_level":       s["pattern_level"],
        "total_messages":      s["total"],
        "high_count":          s["high_count"],
        "medium_count":        s["medium_count"],
        "repeated_harassment": s["repeated_harassment"],
        "escalating":          s["escalating"],
        "dominant_categories": dict(s["dominant_categories"])
    }

def get_session(sender: str, platform: str) -> dict:
    key = f"{sender}:{platform}"
    s = sessions.get(key)
    if not s:
        return {}

    return {
        "pattern_level":       s["pattern_level"],
        "total_messages":      s["total"],
        "high_count":          s["high_count"],
        "medium_count":        s["medium_count"],
        "repeated_harassment": s["repeated_harassment"],
        "escalating":          s["escalating"],
        "dominant_categories": dict(s["dominant_categories"])
    }

def clear_sessions():
    sessions.clear()
