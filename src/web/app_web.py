"""
Plickers Web App — Flask server
Teacher dashboard + Student display với real-time card scanning.
Chạy bằng: python run_web.py  hoặc  python src/web/app_web.py
"""

import sys
import os
import json
import time
import csv
import threading
import logging
from datetime import datetime


import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request, stream_with_context

logger = logging.getLogger(__name__)

# ─── Path setup ───────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
from src.core.detector import PlickersDetector

# ─── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "plickers-secret"

# ─── Config ───────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CAM_WIDTH = 800
CAM_HEIGHT = 600
CAM_FPS = 30
SSE_INTERVAL = 0.4  # giây
FRAME_QUALITY = 75  # JPEG quality

# ─── Detector (lazy — khởi tạo 1 lần duy nhất) ───────────────────────────────
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
    """Đọc class.json — cache vào bộ nhớ, chỉ đọc file 1 lần."""
    global _class_data, _student_lookup
    if _class_data is None:
        with _data_lock:
            if _class_data is None:
                path = os.path.join(DATA_DIR, "class.json")
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)

                    # Validate structure
                    if not isinstance(data, dict):
                        raise ValueError("class.json phải là object")
                    if "students" not in data:
                        raise ValueError("class.json thiếu trường 'students'")
                    if not isinstance(data["students"], list):
                        raise ValueError("'students' phải là array")

                    # Validate each student
                    for i, student in enumerate(data["students"]):
                        if not isinstance(student, dict):
                            raise ValueError(f"Student {i} phải là object")
                        if "card_no" not in student or "name" not in student:
                            raise ValueError(f"Student {i} thiếu 'card_no' hoặc 'name'")
                        if not isinstance(student["card_no"], int) or not isinstance(student["name"], str):
                            raise ValueError(f"Student {i}: card_no phải là số, name phải là string")

                    _class_data = data
                    # Build O(1) lookup dict — key là str để khớp JSON serialization
                    _student_lookup = {str(s["card_no"]): s["name"] for s in _class_data.get("students", [])}
                    logger.info(f"Loaded {len(_class_data['students'])} students from class.json")

                except FileNotFoundError:
                    logger.error(f"Không tìm thấy file: {path}")
                    raise
                except json.JSONDecodeError as e:
                    logger.error(f"Lỗi parse JSON trong {path}: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Lỗi load class.json: {e}")
                    raise

    return _class_data


def load_questions() -> list:
    """Đọc questions.json — cache vào bộ nhớ, chỉ đọc file 1 lần."""
    global _questions_data
    if _questions_data is None:
        with _data_lock:
            if _questions_data is None:
                path = os.path.join(DATA_DIR, "questions.json")
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)

                    # Validate structure
                    if not isinstance(data, list):
                        raise ValueError("questions.json phải là array")

                    # Validate each question
                    for i, question in enumerate(data):
                        if not isinstance(question, dict):
                            raise ValueError(f"Question {i} phải là object")
                        required_fields = ["id", "text", "correct", "options"]
                        for field in required_fields:
                            if field not in question:
                                raise ValueError(f"Question {i} thiếu trường '{field}'")

                        if not isinstance(question["options"], dict):
                            raise ValueError(f"Question {i}: 'options' phải là object")
                        if question["correct"] not in question["options"]:
                            raise ValueError(f"Question {i}: đáp án đúng '{question['correct']}' không có trong options")

                    _questions_data = data
                    logger.info(f"Loaded {len(_questions_data)} questions from questions.json")

                except FileNotFoundError:
                    logger.error(f"Không tìm thấy file: {path}")
                    raise
                except json.JSONDecodeError as e:
                    logger.error(f"Lỗi parse JSON trong {path}: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Lỗi load questions.json: {e}")
                    raise

    return _questions_data


def get_student_name(card_no: int | str) -> str:
    """Tra tên học sinh theo card_no theo O(1) lookup."""
    try:
        load_class()  # đảm bảo lookup đã được build
        name = _student_lookup.get(str(card_no))
        return name if name else f"HS #{int(card_no):02d}"
    except Exception:
        return f"HS #{card_no}"


def invalidate_data_cache() -> None:
    """Xóa cache dữ liệu — dùng khi file JSON bị cập nhật."""
    global _class_data, _questions_data, _student_lookup
    with _data_lock:
        _class_data = None
        _questions_data = None
        _student_lookup = {}


# ─── Shared state (thread-safe) ───────────────────────────────────────────────
# Tất cả results key là STR để nhất quán với JSON serialization
state_lock = threading.Lock()
state: dict = {
    "scanning": False,
    "question": None,  # dict câu hỏi hiện tại
    "results": {},  # {card_no_str: 'A'|'B'|'C'|'D'}
    "revealed": False,
    "session_ts": None,
}

frame_lock = threading.Lock()
output_frame: bytes | None = None  # latest JPEG bytes


# ─── Camera worker thread ─────────────────────────────────────────────────────
_camera_started = False
_camera_lock = threading.Lock()


def _camera_worker() -> None:
    """Background thread: đọc camera và xử lý thẻ khi đang scanning."""
    global output_frame
    detector = get_detector()

    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise RuntimeError("Không thể mở camera. Kiểm tra kết nối camera.")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, CAM_FPS)

        logger.info("Camera worker started successfully")
    except Exception as e:
        logger.error(f"Camera initialization failed: {e}")
        # Set error frame
        error_img = np.zeros((CAM_HEIGHT, CAM_WIDTH, 3), dtype=np.uint8)
        cv2.putText(error_img, "CAMERA ERROR", (50, CAM_HEIGHT//2 - 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
        cv2.putText(error_img, str(e), (50, CAM_HEIGHT//2 + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, buf = cv2.imencode(".jpg", error_img, [cv2.IMWRITE_JPEG_QUALITY, FRAME_QUALITY])
        with frame_lock:
            output_frame = buf.tobytes()
        return

    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                # Camera disconnected or error
                logger.warning("Failed to read frame from camera")
                error_img = np.zeros((CAM_HEIGHT, CAM_WIDTH, 3), dtype=np.uint8)
                cv2.putText(error_img, "CAMERA DISCONNECTED", (50, CAM_HEIGHT//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
                _, buf = cv2.imencode(".jpg", error_img, [cv2.IMWRITE_JPEG_QUALITY, FRAME_QUALITY])
                with frame_lock:
                    output_frame = buf.tobytes()
                time.sleep(1.0)  # Wait before retry
                continue

            display = frame.copy()

            with state_lock:
                scanning = state["scanning"]

            if scanning:
                found = detector.process_image(frame)
                for card_id, cnt in found:
                    parts = str(card_id).split("-")
                    try:
                        card_no_str = parts[0]  # giữ dạng str ngay từ đầu
                        answer = parts[1] if len(parts) > 1 else "?"
                    except Exception:
                        continue

                    # Lưu kết quả — first scan wins, key luôn là str
                    with state_lock:
                        if card_no_str not in state["results"]:
                            state["results"][card_no_str] = answer

                    # Vẽ bounding box
                    try:
                        rect = cv2.minAreaRect(cnt)
                        box = np.int32(cv2.boxPoints(rect))
                        cv2.drawContours(display, [box], 0, (0, 255, 100), 2)
                    except Exception:
                        pass

                    # Nhãn đáp án ở tâm
                    try:
                        M = cv2.moments(cnt)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            cv2.putText(display, answer, (cx - 15, cy + 15), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 255), 3)
                    except Exception:
                        pass

                    # Tag tên học sinh
                    try:
                        x, y, w, h = cv2.boundingRect(cnt)
                        name = get_student_name(card_no_str)
                        cv2.putText(display, name, (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                    except Exception:
                        pass

            # HUD status bar
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

        except Exception as e:
            logger.error(f"Camera worker error: {e}")
            try:
                cap.release()
            except:
                pass
            # Try to restart camera
            time.sleep(2.0)
            try:
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, CAM_FPS)
            except Exception as restart_e:
                logger.error(f"Failed to restart camera: {restart_e}")
                break

    cap.release()


def ensure_camera_started() -> None:
    """Lazy-start camera thread — chỉ khởi động 1 lần khi có request thực sự."""
    global _camera_started
    if not _camera_started:
        with _camera_lock:
            if not _camera_started:
                threading.Thread(target=_camera_worker, daemon=True).start()
                _camera_started = True


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("teacher.html")


@app.route("/display")
def display():
    return render_template("display.html")


@app.route("/video_feed")
def video_feed():
    """MJPEG stream — lazy-start camera khi client kết nối."""
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
    """SSE stream — push state snapshot mỗi SSE_INTERVAL giây."""

    def stream():
        while True:
            with state_lock:
                data = json.dumps(
                    {
                        "scanning": state["scanning"],
                        "question": state["question"],
                        "results": state["results"],
                        "revealed": state["revealed"],
                    }
                )
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
        return jsonify(
            {
                "scanning": state["scanning"],
                "question": state["question"],
                "results": state["results"],
                "revealed": state["revealed"],
            }
        )


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
def api_start():
    ensure_camera_started()  # start camera nếu chưa có
    data = request.json or {}
    with state_lock:
        state["scanning"] = True
        state["question"] = data.get("question")
        state["results"] = {}
        state["revealed"] = False
        state["session_ts"] = datetime.now().isoformat()
    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    with state_lock:
        state["scanning"] = False
    return jsonify({"ok": True})


@app.route("/api/reveal", methods=["POST"])
def api_reveal():
    with state_lock:
        state["revealed"] = True
        state["scanning"] = False
    _save_results()
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    with state_lock:
        state["scanning"] = False
        state["question"] = None
        state["results"] = {}
        state["revealed"] = False
        state["session_ts"] = None
    return jsonify({"ok": True})


@app.route("/api/reload_data", methods=["POST"])
def api_reload_data():
    """Reload class.json / questions.json mà không cần restart server."""
    invalidate_data_cache()
    try:
        load_class()
        load_questions()
        return jsonify({"ok": True, "message": "Data reloaded successfully"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── Internal helpers ─────────────────────────────────────────────────────────
def _save_results() -> None:
    """Lưu kết quả phiên hiện tại ra file CSV."""
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


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 58)
    print("  Plickers Classroom Web App")
    print("  Teacher Dashboard : http://localhost:5000/")
    print("  Student Display   : http://localhost:5000/display")
    print("  Camera starts lazily when first client connects.")
    print("=" * 58)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
