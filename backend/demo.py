import requests
import time

BASE = "http://localhost:5069"

messages = [
    {"sender": "StudentA", "platform": "school_chat", "text": "hello how are you"},
    {"sender": "StudentA", "platform": "school_chat", "text": "you are so stupid and worthless"},
    {"sender": "StudentA", "platform": "school_chat", "text": "nobody likes you loser"},
    {"sender": "StudentA", "platform": "school_chat", "text": "kys nobody would miss you"},
    {"sender": "StudentA", "platform": "school_chat", "text": "i know where you live you better hide"},
]

for i, msg in enumerate(messages):
    r = requests.post(f"{BASE}/messages", json=msg).json()
    a = r.get("analysis", {})
    p = r.get("session_pattern", {})

    print(f"\n{'='*55}")
    print(f"Message {i+1}: {msg['text']}")
    print(f"  Score:          {a.get('score')}")
    print(f"  Level:          {a.get('level')}")
    print(f"  Matched:        {a.get('matched_words')}")
    print(f"  Categories:     {a.get('categories')}")
    print(f"  Pattern level:  {p.get('pattern_level')}")
    print(f"  Alerts sent to: {[x['stakeholder'] for x in r.get('alerts', [])]}")
    time.sleep(0.3)

print(f"\n{'='*55}")
print("Final alerts in DB:")
alerts = requests.get(f"{BASE}/alerts").json()
for a in alerts:
    print(f"  [{a['effective_level']}] → {a['stakeholder']} | {a['original_message'][:40]}")