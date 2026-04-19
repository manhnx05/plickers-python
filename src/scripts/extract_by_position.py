# -*- coding: utf-8 -*-
"""
Extract cards by fixed positions (2 cards per page layout).
Sử dụng vị trí cố định vì PDF có layout đều đặn.
"""

import os
import sys
import cv2
import numpy as np
from pdf2image import convert_from_path
import pickle

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


class PositionBasedExtractor:
    """Extract cards using fixed positions."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.output_dir = os.path.join(PROJECT_ROOT, "data", "extracted_cards_final")
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_all_cards(self, max_pages: int = 17):
        """Extract cards using fixed positions."""
        print(f"📄 Đọc PDF: {self.pdf_path}")

        try:
            images = convert_from_path(self.pdf_path, dpi=300, first_page=1, last_page=max_pages)
            print(f"✅ Convert {len(images)} trang")
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            return []

        all_cards = []
        card_counter = 1

        for page_num, img in enumerate(images, 1):
            print(f"\n📃 Trang {page_num}/{len(images)}...")

            # Convert to OpenCV
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            height, width = img_cv.shape[:2]

            # Each page has 2 cards vertically centered
            # Calculate positions based on page dimensions
            card_width = int(width * 0.4)  # Card is ~40% of page width
            card_height = card_width  # Square

            # Center horizontally
            x_center = width // 2
            x_start = x_center - card_width // 2

            # Two cards: top and bottom
            # Top card at ~25% from top
            # Bottom card at ~65% from top
            y_positions = [int(height * 0.20), int(height * 0.60)]

            for idx, y_start in enumerate(y_positions):
                # Extract card region
                card_img = img_cv[y_start : y_start + card_height, x_start : x_start + card_width]

                # Extract matrix
                matrix = self._extract_matrix(card_img)

                if matrix is not None:
                    # Save
                    card_filename = f"card_{card_counter:03d}.png"
                    card_path = os.path.join(self.output_dir, card_filename)
                    cv2.imwrite(card_path, card_img)

                    all_cards.append(
                        {
                            "number": card_counter,
                            "page": page_num,
                            "position": idx,
                            "matrix": matrix,
                            "image_path": card_path,
                        }
                    )

                    print(f"   ✅ Thẻ {card_counter}")
                    card_counter += 1
                else:
                    print(f"   ⚠️  Không extract được matrix (trang {page_num}, vị trí {idx})")

        print(f"\n🎉 Tổng: {len(all_cards)} thẻ")
        return all_cards

    def _extract_matrix(self, card_img: np.ndarray):
        """Extract 5x5 matrix from card image."""
        if card_img.size == 0:
            return None

        # Convert to grayscale
        gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY)

        # Resize to standard size
        gray = cv2.resize(gray, (500, 500))

        # Apply Otsu threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Extract 5x5 grid
        matrix = np.zeros((5, 5), dtype=int)
        cell_size = 100

        for row in range(5):
            for col in range(5):
                # Cell boundaries with inset
                inset = 15
                y1 = row * cell_size + inset
                y2 = (row + 1) * cell_size - inset
                x1 = col * cell_size + inset
                x2 = (col + 1) * cell_size - inset

                cell = binary[y1:y2, x1:x2]

                # White ratio (in inverted image)
                white_ratio = np.sum(cell == 255) / cell.size

                # Threshold at 50%
                matrix[row, col] = 1 if white_ratio > 0.5 else 0

        return matrix

    def build_database(self, cards: list):
        """Build database with 4 rotations per card."""
        card_matrices = []
        card_ids = []

        for card in cards:
            base_matrix = card["matrix"]
            card_num = card["number"]

            # 4 rotations for A, B, C, D
            for rotation, answer in enumerate(["A", "B", "C", "D"]):
                rotated = np.rot90(base_matrix, rotation)
                card_matrices.append(rotated)
                card_ids.append(f"{card_num:03d}-{answer}")

        # Save database
        db_dir = os.path.join(PROJECT_ROOT, "data", "database_official_final")
        os.makedirs(db_dir, exist_ok=True)

        data_path = os.path.join(db_dir, "card.data")
        list_path = os.path.join(db_dir, "card.list")

        with open(data_path, "wb") as f:
            pickle.dump(card_matrices, f)

        with open(list_path, "wb") as f:
            pickle.dump(card_ids, f)

        print(f"\n✅ Database:")
        print(f"   📁 {data_path}")
        print(f"   📁 {list_path}")
        print(f"   📊 {len(card_matrices)} entries ({len(cards)} cards × 4)")

        # Show sample
        print(f"\n🔍 Sample (Card 001-A):")
        if card_matrices:
            for row in card_matrices[0]:
                print("   ", "".join("█" if cell else "·" for cell in row))

        return data_path, list_path


def main():
    """Main entry point."""
    pdf_path = os.path.join(PROJECT_ROOT, "data", "data_plickers", "PlickersCards_2up.pdf")

    if not os.path.exists(pdf_path):
        print(f"❌ File không tồn tại: {pdf_path}")
        return

    extractor = PositionBasedExtractor(pdf_path)
    cards = extractor.extract_all_cards(max_pages=17)

    if cards:
        extractor.build_database(cards)
        print("\n🎉 Hoàn thành! Chạy test_official_cards_final.py để kiểm tra")
    else:
        print("\n❌ Không extract được thẻ")


if __name__ == "__main__":
    main()
