# -*- coding: utf-8 -*-
"""
Improved extraction from official Plickers PDF with better matrix detection.
Cải thiện thuật toán extract ma trận chính xác hơn.
"""

import os
import sys
import cv2
import numpy as np
from pdf2image import convert_from_path
import pickle

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


class ImprovedExtractor:
    """Improved card extraction with better matrix detection."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.output_dir = os.path.join(PROJECT_ROOT, "data", "extracted_cards_v2")
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_all_cards(self, max_pages: int = None):
        """Extract all cards from PDF."""
        print(f"📄 Đang đọc PDF: {self.pdf_path}")

        try:
            images = convert_from_path(self.pdf_path, dpi=300, fmt="png", first_page=1, last_page=max_pages)
            print(f"✅ Đã convert {len(images)} trang")
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            return []

        all_cards = []
        card_counter = 1

        for page_num, img in enumerate(images, 1):
            print(f"\n📃 Trang {page_num}/{len(images)}...")

            # Convert to OpenCV
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            # Find all large square contours (cards)
            cards_in_page = self._find_cards_in_page(gray, img_cv)

            for card_img, bbox in cards_in_page:
                # Extract matrix
                matrix = self._extract_matrix_improved(card_img)

                if matrix is not None:
                    # Save card image
                    card_filename = f"card_{card_counter:03d}.png"
                    card_path = os.path.join(self.output_dir, card_filename)
                    cv2.imwrite(card_path, card_img)

                    all_cards.append(
                        {
                            "number": card_counter,
                            "page": page_num,
                            "matrix": matrix,
                            "image_path": card_path,
                        }
                    )

                    print(f"   ✅ Thẻ {card_counter}")
                    card_counter += 1

        print(f"\n🎉 Tổng: {len(all_cards)} thẻ")
        return all_cards

    def _find_cards_in_page(self, gray: np.ndarray, img_color: np.ndarray):
        """Find all card regions in page."""
        # Threshold
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cards = []

        for cnt in contours:
            area = cv2.contourArea(cnt)

            # Filter by size (cards are large)
            if area < 50000 or area > 500000:
                continue

            # Check if square-ish
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h if h > 0 else 0

            if 0.8 < aspect_ratio < 1.2:  # Square
                # Extract card with padding
                padding = 20
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(img_color.shape[1], x + w + padding)
                y2 = min(img_color.shape[0], y + h + padding)

                card_img = img_color[y1:y2, x1:x2]
                cards.append((card_img, (x, y, w, h)))

        return cards

    def _extract_matrix_improved(self, card_img: np.ndarray):
        """
        Extract 5x5 matrix with improved algorithm.
        Sử dụng thuật toán tốt hơn để trích xuất ma trận.
        """
        # Convert to grayscale
        if len(card_img.shape) == 3:
            gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = card_img

        # Resize to standard size for consistent processing
        target_size = 500
        gray = cv2.resize(gray, (target_size, target_size))

        # Apply adaptive threshold for better contrast
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

        # Find the main card contour
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Get largest contour (should be the card border)
        main_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(main_contour)

        # Crop to card area only
        card_binary = binary[y : y + h, x : x + w]

        # Resize to exact 500x500 for grid extraction
        card_binary = cv2.resize(card_binary, (500, 500))

        # Extract 5x5 grid
        matrix = np.zeros((5, 5), dtype=int)
        cell_size = 100  # 500 / 5

        for row in range(5):
            for col in range(5):
                # Calculate cell boundaries with inset to avoid borders
                inset = 20
                y1 = row * cell_size + inset
                y2 = (row + 1) * cell_size - inset
                x1 = col * cell_size + inset
                x2 = (col + 1) * cell_size - inset

                cell = card_binary[y1:y2, x1:x2]

                # Calculate percentage of white pixels (in inverted image)
                white_ratio = np.sum(cell == 255) / cell.size

                # If more than 50% white (inverted), it's black in original
                matrix[row, col] = 1 if white_ratio > 0.5 else 0

        return matrix

    def build_database(self, cards: list):
        """Build database from extracted cards."""
        card_matrices = []
        card_ids = []

        for card in cards:
            base_matrix = card["matrix"]
            card_num = card["number"]

            # Generate 4 rotations
            for rotation, answer in enumerate(["A", "B", "C", "D"]):
                rotated = np.rot90(base_matrix, rotation)
                card_matrices.append(rotated)
                card_ids.append(f"{card_num:03d}-{answer}")

        # Save
        db_dir = os.path.join(PROJECT_ROOT, "data", "database_official_v2")
        os.makedirs(db_dir, exist_ok=True)

        data_path = os.path.join(db_dir, "card.data")
        list_path = os.path.join(db_dir, "card.list")

        with open(data_path, "wb") as f:
            pickle.dump(card_matrices, f)

        with open(list_path, "wb") as f:
            pickle.dump(card_ids, f)

        print(f"\n✅ Database lưu tại:")
        print(f"   📁 {data_path}")
        print(f"   📁 {list_path}")
        print(f"   📊 {len(card_matrices)} entries")

        # Print sample matrices for verification
        print(f"\n🔍 Sample matrix (Card 1-A):")
        if card_matrices:
            print(card_matrices[0])

        return data_path, list_path


def main():
    """Main entry point."""
    pdf_path = os.path.join(PROJECT_ROOT, "data", "data_plickers", "PlickersCards_2up.pdf")

    if not os.path.exists(pdf_path):
        print(f"❌ File không tồn tại: {pdf_path}")
        return

    extractor = ImprovedExtractor(pdf_path)

    # Extract all cards (or limit with max_pages)
    cards = extractor.extract_all_cards(max_pages=17)  # 17 pages = 34 cards

    if cards:
        extractor.build_database(cards)
        print("\n🎉 Hoàn thành!")
    else:
        print("\n❌ Không tìm thấy thẻ")


if __name__ == "__main__":
    main()
