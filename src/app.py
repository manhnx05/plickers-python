# -*-coding:utf-8-*-
import cv2
import csv
import os
import sys
from datetime import datetime
import time

# Ensure Python can load modules from the src folder
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.detector import PlickersDetector

# Initialize the detector
detector = PlickersDetector()

#############main####################
print("Dang khoi dong Camera (CAP_DSHOW)... Bam phim 'q' tren cua so Camera de thoat.")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

csv_filename = os.path.join(project_root, "data", "output", "ket_qua.csv")
try:
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Thoi_Gian", "Ma_Hoc_Sinh", "Dap_An_Chon", "Day_Du"])
except Exception as e:
    print(f"Loi tao file CSV: {e}")

scanned_cards = {}
COOLDOWN_TIME = 5.0 # Mức chặn thẻ điền đè liên tiếp: 5 giây

# Windows specific sound
try:
    import winsound
except ImportError:
    winsound = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("Khong the ket noi voi Camera!")
        break
        
    img = frame.copy()
    found_cards = detector.process_image(img)
    
    current_time = time.time()
    overlay = frame.copy()
    
    # Process all detected cards in the frame
    for card_id, cnt in found_cards:
        # Determine format
        part = str(card_id).split('-')
        student_no = part[0]
        student_ans = part[1] if len(part)>1 else ""
        
        # Debounce to prevent flooding DB
        if card_id not in scanned_cards or (current_time - scanned_cards[card_id] > COOLDOWN_TIME):
            scanned_cards[card_id] = current_time
            if winsound:
                winsound.Beep(1000, 100) # 1000Hz, 100ms
                
            try:
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([time_str, student_no, student_ans, str(card_id)])
                print(f"[THÀNH CÔNG] Lớp học ghi nhận thẻ {student_no} | Đáp án {student_ans}")
            except Exception as e:
                print(f"[LỖI] Khong the luu file CSV: {e}")

        # Draw a beautiful bounding box instead of rough contours
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int32(box)
        cv2.drawContours(frame, [box], 0, (0, 255, 100), 2)
        
        # Draw huge Answer text in the center
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"])
            cy = int(M["m01"]/M["m00"])
            cv2.putText(frame, student_ans, (cx - 15, cy + 15), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 255), 3)
            
        # Draw Student ID tag
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.putText(frame, f"ID: {student_no}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

    # Draw Roll-Call HUD on Screen
    cv2.rectangle(overlay, (10, 10), (280, 40 + len(scanned_cards) * 30), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    
    cv2.putText(frame, "--- ĐIỂM DANH ---", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    y_offset = 65
    for c_id, tstamp in list(scanned_cards.items())[-10:]: # Show last 10
        p = str(c_id).split('-')
        txt = f"Hoc Sinh {p[0]} : Chon {p[1]}" if len(p)>1 else str(c_id)
        
        # Highlight green if scanned recently
        color = (0, 255, 0) if (current_time - tstamp < 2.0) else (200, 200, 200)
        cv2.putText(frame, txt, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y_offset += 30

    cv2.imshow("Plickers Scanner - Nhan 'q' de thoat", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
