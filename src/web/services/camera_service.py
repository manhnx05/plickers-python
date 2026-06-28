import time
import cv2
import numpy as np
import threading

from src.core.detector import PlickersDetector
from src.config import CAM_WIDTH, CAM_HEIGHT, CAM_FPS, FRAME_QUALITY
from src.web.services.state import state_lock, app_state, frame_lock
import src.web.services.state as state_mod
from src.web.services.data_service import get_student_name

_detector = None
_detector_lock = threading.Lock()
_camera_started = False
_camera_lock = threading.Lock()

def get_detector() -> PlickersDetector:
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                _detector = PlickersDetector()
    return _detector

def _camera_worker() -> None:
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
            scanning = app_state["scanning"]

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
                    if card_no_str not in app_state["results"]:
                        app_state["results"][card_no_str] = answer

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
            result_count = len(app_state["results"])
            scan = app_state["scanning"]

        cv2.rectangle(display, (0, 0), (220, 38), (0, 0, 0), -1)
        status_txt = f"DANG QUET ({result_count} the)" if scan else "TAM DUNG"
        color = (0, 220, 80) if scan else (60, 140, 255)
        cv2.putText(display, status_txt, (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        _, buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, FRAME_QUALITY])
        with frame_lock:
            state_mod.output_frame = buf.tobytes()

        time.sleep(1.0 / CAM_FPS)
    cap.release()

def ensure_camera_started() -> None:
    global _camera_started
    if not _camera_started:
        with _camera_lock:
            if not _camera_started:
                threading.Thread(target=_camera_worker, daemon=True).start()
                _camera_started = True
