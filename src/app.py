# -*- coding: utf-8 -*-
"""
Plickers Standalone Camera Scanner
Chạy bằng: python src/app.py  hoặc  python run_scanner.py
"""
import cv2
import csv
import os
import sys
import numpy as np
from datetime import datetime
import time

# ─── Path setup ───────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.detector import PlickersDetector

# Windows-only sound (optional)
try:
    import winsound
except ImportError:
    winsound = None

# ─── Constants ────────────────────────────────────────────────────────────────
COOLDOWN_TIME  = 5.0       # giây — chặn ghi đè thẻ liên tiếp
CAM_WIDTH      = 800
CAM_HEIGHT     = 600
CAM_FPS        = 30
CSV_PATH       = os.path.join(PROJECT_ROOT, "data", "output", "ket_qua.csv")
HUD_MAX_ROWS   = 10        # số thẻ tối đa hiển thị trong HUD


def _init_csv(path: str) -> None:
    """Tạo file CSV với header nếu chưa tồn tại."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Thoi_Gian", "Ma_Hoc_Sinh", "Dap_An_Chon", "Day_Du"])
    except Exception as e:
        print(f"[LỖI] Không thể tạo file CSV: {e}")


def _save_result(path: str, student_no: str, student_ans: str, card_id: str) -> None:
    """Ghi một dòng kết quả vào CSV."""
    try:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, mode='a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([time_str, student_no, student_ans, card_id])
        print(f"[THÀNH CÔNG] Học sinh {student_no} | Đáp án {student_ans}")
    except Exception as e:
        print(f"[LỖI] Không thể lưu CSV: {e}")


def _draw_hud(frame, scanned_cards: dict, current_time: float) -> None:
    """Vẽ Roll-Call HUD lên frame."""
    overlay = frame.copy()
    rows = list(scanned_cards.items())[-HUD_MAX_ROWS:]

    # Nền HUD
    hud_h = 40 + len(rows) * 30
    cv2.rectangle(overlay, (10, 10), (300, hud_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    cv2.putText(frame, "--- DIEM DANH ---", (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    y_offset = 65
    for c_id, tstamp in rows:
        p = str(c_id).split('-')
        txt = f"HS {p[0]} : Chon {p[1]}" if len(p) > 1 else str(c_id)
        color = (0, 255, 0) if (current_time - tstamp < 2.0) else (200, 200, 200)
        cv2.putText(frame, txt, (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y_offset += 30


def main() -> None:
    """Entry point chính cho Standalone Scanner."""
    detector = PlickersDetector()
    _init_csv(CSV_PATH)

    print("Đang khởi động Camera (CAP_DSHOW)... Nhấn 'q' để thoát.")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAM_FPS)

    scanned_cards: dict = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[LỖI] Không thể kết nối Camera!")
            break

        img = frame.copy()
        found_cards = detector.process_image(img)
        current_time = time.time()

        for card_id, cnt in found_cards:
            parts = str(card_id).split('-')
            student_no  = parts[0]
            student_ans = parts[1] if len(parts) > 1 else ""

            # Debounce
            if card_id not in scanned_cards or \
               (current_time - scanned_cards[card_id] > COOLDOWN_TIME):
                scanned_cards[card_id] = current_time
                if winsound:
                    winsound.Beep(1000, 100)
                _save_result(CSV_PATH, student_no, student_ans, str(card_id))

            # Vẽ bounding box
            try:
                rect = cv2.minAreaRect(cnt)
                box  = np.int32(cv2.boxPoints(rect))
                cv2.drawContours(frame, [box], 0, (0, 255, 100), 2)
            except Exception:
                pass

            # Nhãn đáp án ở tâm
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(frame, student_ans, (cx - 15, cy + 15),
                            cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 255), 3)

            # Tag ID học sinh
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.putText(frame, f"ID: {student_no}", (x, max(y - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

        _draw_hud(frame, scanned_cards, current_time)

        # FPS counter
        process_time = time.time() - current_time
        fps = 1.0 / process_time if process_time > 0 else CAM_FPS
        cv2.putText(frame, f"FPS: {int(fps)}", (frame.shape[1] - 120, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imshow("Plickers Scanner — Nhan 'q' de thoat", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[OK] Scanner đã dừng.")


if __name__ == '__main__':
    main()
