"""
Script tạo database nhị phân từ ảnh mẫu Plickers.
Đọc tất cả ảnh trong data/samples/, trích xuất ma trận 5x5 và lưu vào
data/database/card.data và card.list bằng pickle.

Chạy bằng: python src/scripts/generate_db.py
"""
import cv2
import numpy as np
import os
import sys
import pickle

# ─── Path setup ───────────────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.utils import Math
from src.core.detector import PlickersDetector

detector = PlickersDetector()


# ─── Core function ────────────────────────────────────────────────────────────
def cv_card_read(img) -> np.ndarray | None:
    """
    Đọc ảnh thẻ Plickers, trả về ma trận 5x5 nếu nhận diện được.
    Trả về None nếu không tìm thấy contour hợp lệ.
    """
    dst  = cv2.blur(img, (3, 3))
    gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 127, 255, 1)
    contours, _ = cv2.findContours(thresh, 2, 1)

    for cnt in contours:
        if len(cnt) > 500:
            approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
            if len(approx) > 11:
                card = gray[
                    cnt[:, 0, :].min():cnt[:, 0, :].max(),
                    cnt[:, :, 0].min():cnt[:, :, 0].max()
                ]
                # THRESH_BINARY_INV để khớp với logic get_card_matrix
                _, result = cv2.threshold(card, 90, 255, 1)
                return detector.get_card_matrix(result)
    return None


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    img_dir   = os.path.join(project_root, 'data', 'samples')
    out_dir   = os.path.join(project_root, 'data', 'database')
    os.makedirs(out_dir, exist_ok=True)

    file_list = [f for f in os.listdir(img_dir) if f.endswith('.jpg')]
    if not file_list:
        print(f"[CẢNH BÁO] Không tìm thấy ảnh nào trong: {img_dir}")
        sys.exit(1)

    card_data = []
    card_list = []
    skipped   = 0

    for file in sorted(file_list):
        img = cv2.imread(os.path.join(img_dir, file))
        if img is None:
            print(f"[CẢNH BÁO] Không đọc được ảnh: {file}")
            skipped += 1
            continue

        file_name = file.split('.')[0]
        try:
            file_num, option = file_name.split('-')
        except ValueError:
            print(f"[CẢNH BÁO] Tên file không đúng định dạng '###-X.jpg': {file}")
            skipped += 1
            continue

        card_array = cv_card_read(img)
        if card_array is None:
            print(f"[THẤT BẠI] Không đọc được thẻ: {file}")
            skipped += 1
            continue

        print(f"[OK] File {file_num} — Hướng mẫu {option}")

        # Tạo 4 hướng xoay từ hướng gốc
        rotations = {'A': 0, 'B': 3, 'C': 2, 'D': 1}
        base_rot  = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        offset    = base_rot[option]

        variants = [np.rot90(card_array, (r - offset) % 4) for r in [0, 1, 2, 3]]
        card_data.extend(variants)
        card_list.extend(f"{file_num}-{l}" for l in ['A', 'B', 'C', 'D'])

    # Lưu ra binary
    fn = os.path.join(out_dir, 'card.data')
    with open(fn, 'wb') as f:
        pickle.dump(card_data, f)

    fl = os.path.join(out_dir, 'card.list')
    with open(fl, 'wb') as f:
        pickle.dump(card_list, f)

    total = len(file_list) - skipped
    print(f"\n[XONG] Đã xử lý {total}/{len(file_list)} ảnh")
    print(f"       Đã lưu {len(card_data)} entries vào database")
    print(f"       → {fn}")
    print(f"       → {fl}")