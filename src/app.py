# -*-coding:utf-8-*-
import cv2
import csv
from datetime import datetime
import time
from detector import PlickersDetector

# Initialize the detector
detector = PlickersDetector()

#############main####################
print("Dang khoi dong Camera (CAP_DSHOW)... Bam phim 'q' tren cua so Camera de thoat.")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

csv_filename = "ket_qua.csv"
try:
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Thoi_Gian", "Ma_Hoc_Sinh", "Dap_An_Chon", "Day_Du"])
except Exception:
    pass

scanned_cards = {}
COOLDOWN_TIME = 5.0 # Mức chặn thẻ điền đè liên tiếp: 5 giây

while True:
    ret, frame = cap.read()
    if not ret:
        print("Khong the ket noi voi Camera!")
        break
        
    img = frame.copy()
    card_id, cnt = detector.process_image(img)
    
    # Nếu tìm thấy định dạng thẻ, lưu vào CSV và vẽ hiển thị
    if card_id:
        current_time = time.time()
        if card_id not in scanned_cards or (current_time - scanned_cards[card_id] > COOLDOWN_TIME):
            scanned_cards[card_id] = current_time
            try:
                # Parse format: e.g. "015-A" -> "015", "A"
                part = str(card_id).split('-')
                student_no = part[0]
                student_ans = part[1] if len(part)>1 else ""
                
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([time_str, student_no, student_ans, str(card_id)])
                print(f"[THANH CONG] Da luu the {student_no} dap an {student_ans} luc {time_str}")
            except Exception as e:
                print(f"[LOI] Khong the luu file CSV: {e}")

        cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 3)
        x, y = cnt[:,:,0].min(), cnt[:,0,:].min()
        cv2.putText(frame, str(card_id), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Plickers Scanner - Nhan 'q' de thoat", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
