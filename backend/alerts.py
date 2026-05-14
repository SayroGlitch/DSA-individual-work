from datetime import datetime, timezone

STAKEHOLDER_RULES = {
    "NONE":     [],
    "LOW":      [],
    "MEDIUM":   ["moderator"],
    "HIGH":     ["moderator", "parent"],
    "CRITICAL": ["moderator", "parent", "legal"]
}

STAKEHOLDER_NOTES = {
    "moderator": "Platform moderator: review and take action.",
    "parent":    "Parent/guardian: your child may be involved in a harmful interaction.",
    "legal":     "Legal team: content may require escalation or reporting."
}

def generate_alerts(result: dict, session_pattern: dict, platform: str, sender: str) -> list:
    message_level  = result.get("level", "NONE")
    pattern_level  = session_pattern.get("pattern_level", "NONE")

    levels          = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    effective_level = levels[max(levels.index(message_level), levels.index(pattern_level))]

    stakeholders = STAKEHOLDER_RULES.get(effective_level, [])
    if not stakeholders:
        return []

    ts     = datetime.now(timezone.utc).isoformat()
    alerts = []

    for stakeholder in stakeholders:
        alerts.append({
            "timestamp":        ts,
            "stakeholder":      stakeholder,
            "stakeholder_note": STAKEHOLDER_NOTES[stakeholder],
            "platform":         platform,
            "sender":           sender,
            "message_level":    message_level,
            "pattern_level":    pattern_level,
            "effective_level":  effective_level,
            "action":           result.get("action", "MONITOR"),
            "score":            result.get("score", 0),
            "explanation":      result.get("explanation", ""),
            "reason_codes":     result.get("reason_codes", []),
            "matched_words":    result.get("matched_words", []),
            "session_summary":  session_pattern
        })

    return alerts