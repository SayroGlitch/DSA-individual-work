import sqlite3

DB_PATH = "safeguard.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            sender    TEXT NOT NULL,
            platform  TEXT NOT NULL,
            text      TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            analyzed  INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id       INTEGER,
            timestamp        TEXT,
            stakeholder      TEXT,
            stakeholder_note TEXT,
            platform         TEXT,
            sender           TEXT,
            message_level    TEXT,
            pattern_level    TEXT,
            effective_level  TEXT,
            action           TEXT,
            score            INTEGER,
            explanation      TEXT,
            original_message TEXT,
            reason_codes     TEXT,
            matched_words    TEXT,
            session_summary  TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)

    conn.commit()
    conn.close()

def reset_logs():
    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM alerts")
    c.execute("DELETE FROM messages")
    c.execute("DELETE FROM sqlite_sequence WHERE name IN ('alerts', 'messages')")

    conn.commit()
    conn.close()
