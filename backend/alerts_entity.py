import json
from database import get_db

LEVEL_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "NONE": 4}

# ─── Merge Sort ───────────────────────────────────────────────

def merge_sort_alerts(alerts: list) -> list:
    if len(alerts) <= 1:
        return alerts
    mid   = len(alerts) // 2
    left  = merge_sort_alerts(alerts[:mid])
    right = merge_sort_alerts(alerts[mid:])
    return _merge(left, right)

def _merge(left: list, right: list) -> list:
    result = []
    i = j  = 0
    while i < len(left) and j < len(right):
        l_rank = LEVEL_ORDER.get(left[i].get("effective_level",  "NONE"), 99)
        r_rank = LEVEL_ORDER.get(right[j].get("effective_level", "NONE"), 99)
        if l_rank <= r_rank:
            result.append(left[i]);  i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

# ─── Binary Search ────────────────────────────────────────────

def binary_search_by_score(alerts: list, target_score: int) -> int:
    """
    Returns index of last alert with score >= target_score.
    Assumes alerts sorted by score descending.
    """
    lo, hi = 0, len(alerts) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if alerts[mid].get("score", 0) >= target_score:
            result = mid
            lo     = mid + 1
        else:
            hi = mid - 1
    return result

# ─── DB operations ────────────────────────────────────────────

def save_alert(alert: dict, message_id: int):
    conn = get_db()
    c    = conn.cursor()
    c.execute("""
        INSERT INTO alerts (
            message_id, timestamp, stakeholder, stakeholder_note,
            platform, sender, message_level, pattern_level,
            effective_level, action, score, explanation,
            original_message, reason_codes, matched_words, session_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message_id,
        alert.get("timestamp"),
        alert.get("stakeholder"),
        alert.get("stakeholder_note"),
        alert.get("platform"),
        alert.get("sender"),
        alert.get("message_level"),
        alert.get("pattern_level"),
        alert.get("effective_level"),
        alert.get("action"),
        alert.get("score"),
        alert.get("explanation"),
        alert.get("original_message"),
        json.dumps(alert.get("reason_codes",   [])),
        json.dumps(alert.get("matched_words",  [])),
        json.dumps(alert.get("session_summary", {}))
    ))
    conn.commit()
    conn.close()

def get_all_alerts(stakeholder: str = None) -> list:
    conn = get_db()
    c    = conn.cursor()
    if stakeholder:
        c.execute(
            "SELECT * FROM alerts WHERE stakeholder = ? ORDER BY id DESC",
            (stakeholder,)
        )
    else:
        c.execute("SELECT * FROM alerts ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    results = []
    for r in rows:
        row = dict(r)
        for field in ("reason_codes", "matched_words", "session_summary"):
            try:
                row[field] = json.loads(row[field]) if row[field] else []
            except Exception:
                pass
        results.append(row)

    return merge_sort_alerts(results)

def get_alerts_by_message(message_id: int) -> list:
    conn = get_db()
    c    = conn.cursor()
    c.execute(
        "SELECT * FROM alerts WHERE message_id = ? ORDER BY id ASC",
        (message_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]