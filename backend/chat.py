from database import get_db
from datetime import datetime, timezone

def save_message(sender: str, platform: str, text: str) -> dict:
    conn = get_db()
    c = conn.cursor()
    ts = datetime.now(timezone.utc).isoformat()
    c.execute(
        "INSERT INTO messages (sender, platform, text, timestamp) VALUES (?, ?, ?, ?)",
        (sender, platform, text, ts)
    )
    conn.commit()
    msg_id = c.lastrowid
    conn.close()
    return {"id": msg_id, "sender": sender, "platform": platform,
            "text": text, "timestamp": ts}

def get_all_messages() -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM messages ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_message_by_id(msg_id: int) -> dict | None:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_analyzed(msg_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE messages SET analyzed = 1 WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()