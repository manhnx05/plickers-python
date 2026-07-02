import os
import csv
import json
import time
from datetime import datetime
from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_login import login_required

from src.config import SSE_INTERVAL, CAM_FPS, DATA_DIR
from src.web.services.state import state_lock, app_state, frame_lock
import src.web.services.state as state_mod
from src.web.services.camera_service import ensure_camera_started
from src.web.services.data_service import load_class

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route("/video_feed")
def video_feed():
    ensure_camera_started()
    def gen():
        while True:
            with frame_lock:
                frame = state_mod.output_frame
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(1.0 / CAM_FPS)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@scanner_bp.route("/api/events")
def api_events():
    def stream():
        while True:
            with state_lock:
                data = json.dumps({
                    "scanning": app_state["scanning"],
                    "question": app_state["question"],
                    "results": app_state["results"],
                    "revealed": app_state["revealed"],
                })
            yield f"data: {data}\n\n"
            time.sleep(SSE_INTERVAL)
    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@scanner_bp.route("/api/state")
def api_state():
    with state_lock:
        return jsonify({
            "scanning": app_state["scanning"],
            "question": app_state["question"],
            "results": app_state["results"],
            "revealed": app_state["revealed"],
        })

@scanner_bp.route("/api/start", methods=["POST"])
@login_required
def api_start():
    ensure_camera_started()
    data = request.json or {}
    with state_lock:
        app_state["scanning"] = True
        app_state["question"] = data.get("question")
        app_state["results"] = {}
        app_state["revealed"] = False
        app_state["session_ts"] = datetime.now().isoformat()
    return jsonify({"ok": True})

@scanner_bp.route("/api/stop", methods=["POST"])
@login_required
def api_stop():
    with state_lock:
        app_state["scanning"] = False
    return jsonify({"ok": True})

@scanner_bp.route("/api/reveal", methods=["POST"])
@login_required
def api_reveal():
    with state_lock:
        app_state["revealed"] = True
        app_state["scanning"] = False
    _save_results()
    return jsonify({"ok": True})

@scanner_bp.route("/api/reset", methods=["POST"])
@login_required
def api_reset():
    with state_lock:
        app_state["scanning"] = False
        app_state["question"] = None
        app_state["results"] = {}
        app_state["revealed"] = False
        app_state["session_ts"] = None
    return jsonify({"ok": True})

def _save_results() -> None:
    try:
        with state_lock:
            results = dict(app_state["results"])
            question = app_state["question"]

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
