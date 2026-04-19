import os
import sys
import cv2

# Ensure Python can load modules from the src folder
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.detector import PlickersDetector

# Set proper utf-8 encoding for printing to Windows terminal
sys.stdout.reconfigure(encoding="utf-8")


def main():
    detector = PlickersDetector()

    img_dir = os.path.join(project_root, "data", "samples")
    if not os.path.exists(img_dir):
        print(f"[CẢNH BÁO] Không tìm thấy thư mục: {img_dir}")
        return

    test_files = [f for f in os.listdir(img_dir) if f.endswith(".jpg")]
    found_count = 0

    print("BẮT ĐẦU CHẠY KIỂM THỬ TRÊN TÀN BỘ CÁC ẢNH:\n" + "-" * 50)
    for file in test_files:
        img_path = os.path.join(img_dir, file)
        img = cv2.imread(img_path)
        if img is None:
            continue

        found_cards = detector.process_image(img)
        expected_id = file.split(".")[0]

        # Check if the expected card is within the found_cards
        found_expected = False
        misclassified = []
        for card_id, cnt in found_cards:
            if card_id == expected_id:
                found_expected = True
            else:
                misclassified.append(str(card_id))

        if found_expected:
            print(f"=> Ảnh test mẫu {file:12} | Kết quả phân tích: BINGO >>> {expected_id}")
            found_count += 1
        elif len(misclassified) > 0:
            print(
                f"=> Ảnh test mẫu {file:12} | Kết quả phân tích: SO KHỚP SAI (Nhận nhầm thành {','.join(misclassified)})"
            )
        else:
            print(f"=> Ảnh test mẫu {file:12} | Kết quả phân tích: THẤT BẠI.")

    print("-" * 50)
    print(f"Tổng kết: Tự tin nhận diện chính xác {found_count}/{len(test_files)} ảnh.")


if __name__ == "__main__":
    main()
