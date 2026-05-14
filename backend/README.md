# SafeGuard — Cyberbullying Detection Backend

A real-time message analysis and alert system that detects harmful content using a
Trie-based C scorer, session pattern tracking, and multi-stakeholder alert routing.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop) — that is all you need

---

## Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/YOURNAME/safeguard-backend.git
cd safeguard-backend
```

### 2. Start the backend
```bash
docker compose up --build
```

The first run compiles the C scorer and installs all dependencies automatically.
Server is live at **http://localhost:5000**

### 3. Stop the server
```bash
docker compose down
```

---

## Project Structure




---

## Algorithms & Data Structures

| Concept | Implementation | File |
|---|---|---|
| **Trie** | Word/phrase lookup, O(L) per word | `scorer.c` |
| **Merge Sort** | Alerts sorted by severity (CRITICAL → NONE) | `alerts_entity.py` |
| **Binary Search** | Find alerts at or above a score threshold | `alerts_entity.py` |
| **Queue (FIFO)** | Message processing order via deque | `queue_processor.py` |
| **Hash Map** | Session storage keyed by `sender:platform` | `session_manager.py` |
| **State Machine** | Pattern level escalation logic | `session_manager.py` |

---

## API Reference

### Messages

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/messages` | Submit a message for analysis |
| `GET`  | `/messages` | Get all messages |
| `GET`  | `/messages/:id` | Get one message by ID |

#### POST /messages — request body
```json
{
  "sender": "StudentA",
  "platform": "school_chat",
  "text": "your message here"
}
```

#### POST /messages — response
```json
{
  "message":         { "id": 1, "sender": "StudentA", "platform": "school_chat", "text": "...", "timestamp": "..." },
  "analysis":        { "score": 17, "level": "HIGH", "action": "BLOCK", "matched_words": ["..."], "categories": ["..."] },
  "session_pattern": { "pattern_level": "HIGH", "total_messages": 2, "high_count": 2, "escalating": true },
  "alerts":          [ { "stakeholder": "moderator", "effective_level": "HIGH", ... } ],
  "queue_size":      0
}
```

---

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/alerts` | Get all alerts, sorted by severity |
| `GET` | `/alerts?stakeholder=moderator` | Filter by stakeholder |
| `GET` | `/alerts/message/:id` | Get all alerts for a specific message |
| `GET` | `/alerts/search?min_score=12` | Binary search — alerts at or above score |

---

### Session

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/session?sender=StudentA&platform=school_chat` | Get session state for a user |

---

### WebSocket

Connect to `http://localhost:5000` with Socket.IO.

| Event | Direction | Description |
|-------|-----------|-------------|
| `new_alert` | Server → Client | Emitted in real time whenever an alert is generated |

#### new_alert payload
```json
{
  "stakeholder":      "moderator",
  "effective_level":  "CRITICAL",
  "action":           "BLOCK",
  "sender":           "StudentA",
  "platform":         "school_chat",
  "score":            24,
  "matched_words":    ["kys", "kill yourself"],
  "categories":       ["self-harm encouragement"],
  "session_summary":  { "pattern_level": "CRITICAL", "high_count": 3, ... }
}
```

---

## Stakeholder Alert Routing

| Effective Level | Notified Stakeholders |
|---|---|
| `NONE` / `LOW` | Nobody |
| `MEDIUM` | Moderator |
| `HIGH` | Moderator + Parent |
| `CRITICAL` | Moderator + Parent + Legal |

Effective level is the **higher** of the single message level and the session pattern level.

---

## Editing the Word List

Open `words.json` and add entries in this format:

```json
"your phrase here": { "score": 7, "category": "harassment" }
```

No recompilation needed — the scorer reads `words.json` fresh on every server start.

---

## Scoring Thresholds

| Score | Level | Action |
|---|---|---|
| 0 | NONE | ALLOW |
| 1 – 6 | LOW | MONITOR |
| 7 – 14 | MEDIUM | WARN |
| 15+ | HIGH | BLOCK |

---

## Demo Script

Run a simulated harassment scenario while the server is running:

```python
import requests, time

BASE = "http://localhost:5000"

messages = [
    {"sender": "StudentA", "platform": "school_chat", "text": "you are so stupid"},
    {"sender": "StudentA", "platform": "school_chat", "text": "nobody likes you loser"},
    {"sender": "StudentA", "platform": "school_chat", "text": "kill yourself nobody would miss you"},
]

for i, msg in enumerate(messages):
    r = requests.post(f"{BASE}/messages", json=msg).json()
    print(f"\nMessage {i+1}: {msg['text']}")
    print(f"  Score:         {r['analysis']['score']}")
    print(f"  Level:         {r['analysis']['level']}")
    print(f"  Pattern:       {r['session_pattern']['pattern_level']}")
    print(f"  Alerts sent:   {[a['stakeholder'] for a in r['alerts']]}")
    time.sleep(0.5)
```

Save as `demo.py` and run:
```bash
python demo.py
```