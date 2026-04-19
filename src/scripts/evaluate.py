import os
import sys
import cv2

# Ensure Python can load modules from the src folder
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.detector import PlickersDetector

# Set proper utf-8 encoding for printing to Windows terminal
sys.stdout.reconfigure(encoding='utf-8')

def main():
    detector = PlickersDetector()
    
    img_dir = os.path.join(project_root, 'data', 'samples')
    if not os.path.exists(img_dir):
        print(f"[CẢNH BÁO] Không tìm thấy thư mục: {img_dir}")
        return

    test_files = [f for f in os.listdir(img_dir) if f.endswith('.jpg')]
    found_count = 0

    print("BẮT ĐẦU CHẠY KIỂM THỬ TRÊN TÀN BỘ CÁC ẢNH:\n" + "-"*50)
    for file in test_files:
        img_path = os.path.join(img_dir, file)
        img = cv2.imread(img_path)
        if img is None:
            continue
            
        card_id, cnt = detector.process_image(img)
        
        if card_id:
            print(f"=> Ảnh test mẫu {file:12} | Kết quả phân tích: BINGO >>> {str(card_id)}")
            found_count += 1
        else:
            print(f"=> Ảnh test mẫu {file:12} | Kết quả phân tích: THẤT BẠI.")

    print("-" * 50)
    print(f"Tổng kết: Tự tin nhận diện thành công {found_count}/{len(test_files)} ảnh.")

if __name__ == '__main__':
    main()
