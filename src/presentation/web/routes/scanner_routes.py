import os
import json
import time
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_login import login_required, current_user

from src.config import SSE_INTERVAL, CAM_FPS
from src.presentation.web.services.state import state_lock, app_state, frame_lock
import src.presentation.web.services.state as state_mod
from src.presentation.web.services.camera_service import ensure_camera_started
from src.application.services.scanner_service import ScannerService

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
    
    from src.application.services.data_service import DataService
    class_data = DataService.get_class_data(current_user.id)
    name_cache = {str(s["card_no"]): s["name"] for s in class_data["students"]}
    
    with state_lock:
        app_state["scanning"] = True
        app_state["question"] = data.get("question")
        app_state["results"] = {}
        app_state["name_cache"] = name_cache
        app_state["revealed"] = False
        app_state["session_ts"] = datetime.now(timezone.utc).isoformat()
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
    _save_results(current_user.id)
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

def _save_results(teacher_id: int) -> None:
    try:
        with state_lock:
            results = dict(app_state["results"])
            question = app_state["question"]
            started_at = app_state.get("session_ts", datetime.now(timezone.utc).isoformat())

        ScannerService.save_session(teacher_id, question, results, started_at)
        print("[OK] Saved session to database")
    except Exception as e:
        print(f"[ERR] Save failed: {e}")
