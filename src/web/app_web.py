"""
Plickers Web App — Flask server
Teacher dashboard + Student display with real-time card scanning and authentication.
"""

import sys
import os
import json
import time
import csv
import threading
from datetime import datetime
from functools import wraps

import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, stream_with_context
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

# ─── Path setup ───────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.core.detector import PlickersDetector
from src.config import (
    FLASK_SECRET_KEY,
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    CAM_WIDTH,
    CAM_HEIGHT,
    CAM_FPS,
    SSE_INTERVAL,
    FRAME_QUALITY,
    DATA_DIR,
    RESEND_API_KEY,
    RESEND_FROM_EMAIL
)
from src.core.db import init_db, create_password_reset_token, get_user_by_token, mark_token_as_used
from src.core.models import db, User, Card, Class, Student, Question, ScanSession, ScanResult

# ─── Flask app initialization ─────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
# Initialize DB after app is created, but inside app context when needed
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Initialize DB in app context to avoid import-time errors
def init_app_db():
    from src.core.db import init_db
    init_db(app)


with app.app_context():
    init_app_db()


# ─── Detector (lazy — initialize once) ────────────────────────────────────────
_detector: PlickersDetector | None = None
_detector_lock = threading.Lock()


def get_detector() -> PlickersDetector:
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                _detector = PlickersDetector()
    return _detector


# ─── Data helpers (cached) ────────────────────────────────────────────────────
_class_data: dict | None = None
_questions_data: list | None = None
_student_lookup: dict[str, str] = {}  # card_no (str) → name
_data_lock = threading.Lock()


def load_class() -> dict:
    global _class_data, _student_lookup
    if _class_data is None:
        with _data_lock:
            if _class_data is None:
                path = os.path.join(DATA_DIR, "class.json")
                with open(path, encoding="utf-8") as f:
                    _class_data = json.load(f)
                _student_lookup = {str(s["card_no"]): s["name"] for s in _class_data.get("students", [])}
    return _class_data


def load_questions() -> list:
    global _questions_data
    if _questions_data is None:
        with _data_lock:
            if _questions_data is None:
                path = os.path.join(DATA_DIR, "questions.json")
                with open(path, encoding="utf-8") as f:
                    _questions_data = json.load(f)
    return _questions_data


def get_student_name(card_no: int | str) -> str:
    try:
        load_class()
        name = _student_lookup.get(str(card_no))
        return name if name else f"HS #{int(card_no):02d}"
    except Exception:
        return f"HS #{card_no}"


def invalidate_data_cache() -> None:
    global _class_data, _questions_data, _student_lookup
    with _data_lock:
        _class_data = None
        _questions_data = None
        _student_lookup = {}


# ─── Shared state (thread-safe) ───────────────────────────────────────────────
state_lock = threading.Lock()
state: dict = {
    "scanning": False,
    "question": None,
    "results": {},
    "revealed": False,
    "session_ts": None,
}

frame_lock = threading.Lock()
output_frame: bytes | None = None


# ─── Camera worker thread ─────────────────────────────────────────────────────
_camera_started = False
_camera_lock = threading.Lock()


def _camera_worker() -> None:
    global output_frame
    detector = get_detector()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAM_FPS)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        display = frame.copy()

        with state_lock:
            scanning = state["scanning"]

        if scanning:
            found = detector.process_image(frame)
            for card_id, cnt in found:
                parts = str(card_id).split("-")
                try:
                    card_no_str = parts[0]
                    answer = parts[1] if len(parts) > 1 else "?"
                except Exception:
                    continue

                with state_lock:
                    if card_no_str not in state["results"]:
                        state["results"][card_no_str] = answer

                try:
                    rect = cv2.minAreaRect(cnt)
                    box = np.int32(cv2.boxPoints(rect))
                    cv2.drawContours(display, [box], 0, (0, 255, 100), 2)
                except Exception:
                    pass

                try:
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cv2.putText(display, answer, (cx - 15, cy + 15), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 255), 3)
                except Exception:
                    pass

                try:
                    x, y, w, h = cv2.boundingRect(cnt)
                    name = get_student_name(card_no_str)
                    cv2.putText(display, name, (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                except Exception:
                    pass

        with state_lock:
            result_count = len(state["results"])
            scan = state["scanning"]

        cv2.rectangle(display, (0, 0), (220, 38), (0, 0, 0), -1)
        status_txt = f"DANG QUET ({result_count} the)" if scan else "TAM DUNG"
        color = (0, 220, 80) if scan else (60, 140, 255)
        cv2.putText(display, status_txt, (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        _, buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, FRAME_QUALITY])
        with frame_lock:
            output_frame = buf.tobytes()

        time.sleep(1.0 / CAM_FPS)
    cap.release()


def ensure_camera_started() -> None:
    global _camera_started
    if not _camera_started:
        with _camera_lock:
            if not _camera_started:
                threading.Thread(target=_camera_worker, daemon=True).start()
                _camera_started = True


# ─── Auth Routes ───────────────────────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return jsonify({"ok": True, "message": "Already logged in", "user": {"id": current_user.id, "name": current_user.name, "role": current_user.role}})
    
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"ok": False, "error": "Missing email or password"}), 400
        
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({"ok": True, "user": {"id": user.id, "name": user.name, "role": user.role}})
    return jsonify({"ok": False, "error": "Invalid email or password"}), 401


@app.route("/register", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return jsonify({"ok": False, "error": "Already logged in"}), 400
    
    data = request.json or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not name or not email or not password:
        return jsonify({"ok": False, "error": "Missing required fields"}), 400
        
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"ok": False, "error": "Email already registered"}), 400
        
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(
        name=name,
        email=email,
        password_hash=hashed_password,
        role='teacher'
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"ok": True, "message": "Registration successful"})


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@app.route("/api/me", methods=["GET"])
def api_me():
    if current_user.is_authenticated:
        return jsonify({"ok": True, "user": {"id": current_user.id, "name": current_user.name, "email": current_user.email, "role": current_user.role}})
    return jsonify({"ok": False, "error": "Not authenticated"}), 401





@app.route("/video_feed")
def video_feed():
    ensure_camera_started()

    def gen():
        while True:
            with frame_lock:
                frame = output_frame
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(1.0 / CAM_FPS)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/events")
def api_events():
    def stream():
        while True:
            with state_lock:
                data = json.dumps({
                    "scanning": state["scanning"],
                    "question": state["question"],
                    "results": state["results"],
                    "revealed": state["revealed"],
                })
            yield f"data: {data}\n\n"
            time.sleep(SSE_INTERVAL)

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/state")
def api_state():
    with state_lock:
        return jsonify({
            "scanning": state["scanning"],
            "question": state["question"],
            "results": state["results"],
            "revealed": state["revealed"],
        })


@app.route("/api/class")
def api_class():
    try:
        return jsonify(load_class())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/questions")
def api_questions():
    try:
        return jsonify(load_questions())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/start", methods=["POST"])
@login_required
def api_start():
    ensure_camera_started()
    data = request.json or {}
    with state_lock:
        state["scanning"] = True
        state["question"] = data.get("question")
        state["results"] = {}
        state["revealed"] = False
        state["session_ts"] = datetime.now().isoformat()
    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
@login_required
def api_stop():
    with state_lock:
        state["scanning"] = False
    return jsonify({"ok": True})


@app.route("/api/reveal", methods=["POST"])
@login_required
def api_reveal():
    with state_lock:
        state["revealed"] = True
        state["scanning"] = False
    _save_results()
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
@login_required
def api_reset():
    with state_lock:
        state["scanning"] = False
        state["question"] = None
        state["results"] = {}
        state["revealed"] = False
        state["session_ts"] = None
    return jsonify({"ok": True})


@app.route("/api/reload_data", methods=["POST"])
@login_required
def api_reload_data():
    invalidate_data_cache()
    try:
        load_class()
        load_questions()
        return jsonify({"ok": True, "message": "Data reloaded successfully"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── Internal helpers ─────────────────────────────────────────────────────────
def _save_results() -> None:
    try:
        with state_lock:
            results = dict(state["results"])
            question = state["question"]

        cls = load_class()
        out_dir = os.path.join(DATA_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(out_dir, f"session_{ts}.csv")

        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["So the", "Ten hoc sinh", "Cau hoi", "Dap an", "Dap an dung", "Ket qua"])
            for s in cls["students"]:
                cn_str = str(s["card_no"])
                ans = results.get(cn_str, "-")
                correct = question["correct"] if question else "-"
                q_text = question["text"] if question else ""
                if ans == "-":
                    result = "Chua tra loi"
                elif ans == correct:
                    result = "Dung"
                else:
                    result = "Sai"
                w.writerow([s["card_no"], s["name"], q_text, ans, correct, result])

        print(f"[OK] Saved session: {filename}")
    except Exception as e:
        print(f"[ERR] Save failed: {e}")


# ─── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 58)
    print("  Plickers Classroom API Server")
    print(f"  API Endpoint      : http://localhost:{FLASK_PORT}/api")
    print(f"  Video Stream      : http://localhost:{FLASK_PORT}/video_feed")
    print("=" * 58)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True)
