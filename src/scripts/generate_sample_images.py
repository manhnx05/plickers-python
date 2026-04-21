"""
Script tạo ảnh mẫu Plickers cho database.
Tạo các thẻ với pattern 5x5 nhị phân khác nhau.

Chạy bằng: python src/scripts/generate_sample_images.py
"""

import cv2
import numpy as np
import os
import sys

# ─── Path setup ───────────────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.detector import PlickersDetector


def create_card_image(card_matrix, card_id, orientation):
    """
    Tạo ảnh thẻ Plickers từ ma trận 5x5.
    Tạo contour lớn để detector dễ nhận diện.
    """
    # Kích thước lớn hơn để tạo contour tốt
    card_size = 300
    margin = 50
    total_size = card_size + 2 * margin

    # Tạo ảnh đen (background)
    img = np.zeros((total_size, total_size, 3), dtype=np.uint8)

    # Vẽ viền trắng dày
    cv2.rectangle(img, (margin, margin), (total_size - margin, total_size - margin), (255, 255, 255), 8)

    # Kích thước mỗi ô
    cell_size = card_size // 5

    # Vẽ pattern trắng trên nền đen
    for i in range(5):
        for j in range(5):
            if card_matrix[i, j] == 1:
                x1 = margin + j * cell_size
                y1 = margin + i * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), -1)

    # Thêm text ID
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, f"#{card_id}", (margin + 10, margin - 10), font, 1, (255, 255, 255), 2)

    return img


def generate_sample_images():
    """
    Tạo ảnh mẫu cho 34 thẻ, mỗi thẻ 4 hướng.
    Sử dụng pattern cố định để đảm bảo detector nhận diện được.
    """
    detector = PlickersDetector()

    samples_dir = os.path.join(project_root, "data", "samples")
    os.makedirs(samples_dir, exist_ok=True)

    # Pattern cơ bản cho Plickers (5x5 grid)
    base_patterns = [
        # Pattern đơn giản để detector dễ nhận
        np.array([
            [1, 0, 0, 0, 1],
            [0, 1, 0, 1, 0],
            [0, 0, 1, 0, 0],
            [0, 1, 0, 1, 0],
            [1, 0, 0, 0, 1]
        ]),
        np.array([
            [0, 1, 1, 1, 0],
            [1, 0, 0, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 0, 0, 0, 1],
            [0, 1, 1, 1, 0]
        ]),
        # Thêm nhiều pattern khác
    ]

    # Nhân bản pattern cho 34 thẻ
    patterns = []
    for i in range(34):
        if i < len(base_patterns):
            patterns.append(base_patterns[i])
        else:
            # Tạo variation
            base = base_patterns[i % len(base_patterns)]
            variation = np.copy(base)
            # Flip ngẫu nhiên một số bit
            for _ in range(np.random.randint(1, 4)):
                x, y = np.random.randint(0, 5, 2)
                variation[x, y] = 1 - variation[x, y]
            patterns.append(variation)

    for card_id in range(1, 35):  # 1-34
        pattern = patterns[card_id - 1]

        # Tạo 4 ảnh cho 4 hướng
        for orientation in ['A', 'B', 'C', 'D']:
            # Xoay pattern
            rotations = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            rotated = np.rot90(pattern, rotations[orientation])

            # Tạo ảnh với background đen và foreground trắng
            img = create_card_image(rotated, card_id, orientation)

            # Lưu
            filename = f"{str(card_id).zfill(3)}-{orientation}.jpg"
            filepath = os.path.join(samples_dir, filename)
            cv2.imwrite(filepath, img)
            print(f"Tạo: {filename}")

    print(f"\nHoàn thành! Đã tạo {34 * 4} ảnh mẫu trong {samples_dir}")


if __name__ == "__main__":
    generate_sample_images()