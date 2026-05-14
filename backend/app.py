from gevent import monkey
monkey.patch_all()
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

from database        import init_db, reset_logs
from chat            import save_message, get_all_messages, get_message_by_id, mark_analyzed
from alerts_entity   import save_alert, get_all_alerts, get_alerts_by_message, binary_search_by_score
from main            import analyze_message, add_word_entry, get_words
from session_manager import add_to_session, get_session, clear_sessions
from alerts          import generate_alerts
from queue_processor import message_queue

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ─── Messages ────────────────────────────────────────────────

@app.route("/messages", methods=["GET"])
def api_get_messages():
    return jsonify(get_all_messages())

@app.route("/messages/<int:msg_id>", methods=["GET"])
def api_get_message(msg_id):
    msg = get_message_by_id(msg_id)
    if not msg:
        return jsonify({"error": "Message not found"}), 404
    return jsonify(msg)

@app.route("/messages", methods=["POST"])
def api_post_message():
    body     = request.get_json()
    sender   = body.get("sender",   "anonymous")
    platform = body.get("platform", "unknown")
    text     = body.get("text",     "")

    if not text.strip():
        return jsonify({"error": "Message text is required"}), 400

    msg = save_message(sender, platform, text)
    message_queue.enqueue({**msg})
    queued_msg = message_queue.dequeue()

    result          = analyze_message(queued_msg["text"])
    session_pattern = add_to_session(queued_msg["sender"], queued_msg["platform"], result)
    alerts          = generate_alerts(result, session_pattern, queued_msg["platform"], queued_msg["sender"])

    saved_alerts = []
    for alert in alerts:
        alert["original_message"] = text
        save_alert(alert, msg["id"])
        socketio.emit("new_alert", alert)
        saved_alerts.append(alert)

    mark_analyzed(msg["id"])

    return jsonify({
        "message":         msg,
        "analysis":        result,
        "session_pattern": session_pattern,
        "alerts":          saved_alerts,
        "queue_size":      message_queue.size()
    }), 201

# ─── Alerts ──────────────────────────────────────────────────

@app.route("/alerts", methods=["GET"])
def api_get_alerts():
    stakeholder = request.args.get("stakeholder")
    return jsonify(get_all_alerts(stakeholder))

@app.route("/alerts/message/<int:msg_id>", methods=["GET"])
def api_get_alerts_for_message(msg_id):
    return jsonify(get_alerts_by_message(msg_id))

@app.route("/alerts/search", methods=["GET"])
def api_search_alerts_by_score():
    try:
        threshold = int(request.args.get("min_score", 0))
    except ValueError:
        return jsonify({"error": "min_score must be an integer"}), 400

    all_alerts      = get_all_alerts()
    sorted_by_score = sorted(all_alerts, key=lambda a: a.get("score", 0), reverse=True)
    idx             = binary_search_by_score(sorted_by_score, threshold)

    if idx == -1:
        return jsonify([])
    return jsonify(sorted_by_score[:idx + 1])

# ─── Session ─────────────────────────────────────────────────

@app.route("/words", methods=["GET"])
def api_get_words():
    words = get_words()
    return jsonify({"count": len(words), "words": words})

@app.route("/words", methods=["POST"])
def api_add_word():
    body = request.get_json() or {}
    phrase = body.get("phrase", "")
    category = body.get("category", "")

    try:
        score = int(body.get("score", 0))
        entry = add_word_entry(phrase, score, category)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "message": "Word register saved",
        "entry": entry,
        "count": len(get_words())
    }), 201

@app.route("/reset", methods=["POST"])
def api_reset_simulation():
    reset_logs()
    clear_sessions()
    message_queue.clear()

    return jsonify({
        "message": "Simulation reset",
        "messages": 0,
        "alerts": 0,
        "queue_size": message_queue.size()
    })

@app.route("/session", methods=["GET"])
def api_get_session():
    sender   = request.args.get("sender")
    platform = request.args.get("platform")
    if not sender or not platform:
        return jsonify({"error": "sender and platform required"}), 400
    return jsonify(get_session(sender, platform))

# ─── Run ─────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("SafeGuard backend running on http://localhost:5069")
    socketio.run(app, host="0.0.0.0", port=5069, debug=False)
