# -*- coding: utf-8 -*-
"""
Extract Plickers cards from official PDF and build database.
Cắt PDF thành từng thẻ và tạo database từ thẻ thật.
"""

import os
import sys
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.core.detector import PlickersDetector


class OfficialPDFExtractor:
    """Extract cards from official Plickers PDF."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.output_dir = os.path.join(PROJECT_ROOT, "data", "extracted_cards")
        os.makedirs(self.output_dir, exist_ok=True)

        self.detector = PlickersDetector()

    def extract_cards_from_pdf(self, max_pages: int = None):
        """
        Convert PDF to images and extract individual cards.

        Args:
            max_pages: Maximum number of pages to process (None = all)
        """
        print(f"📄 Đang đọc PDF: {self.pdf_path}")

        # Convert PDF to images
        try:
            images = convert_from_path(self.pdf_path, dpi=300, fmt="png", first_page=1, last_page=max_pages)
            print(f"✅ Đã convert {len(images)} trang")
        except Exception as e:
            print(f"❌ Lỗi convert PDF: {e}")
            print("💡 Cần cài Poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
            return []

        all_cards = []

        for page_num, img in enumerate(images, 1):
            print(f"\n📃 Xử lý trang {page_num}/{len(images)}...")

            # Convert PIL to OpenCV
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # Extract cards from this page (2 cards per page)
            cards = self._extract_cards_from_page(img_cv, page_num)
            all_cards.extend(cards)

            print(f"   ✅ Tìm thấy {len(cards)} thẻ")

        print(f"\n🎉 Tổng cộng: {len(all_cards)} thẻ")
        return all_cards

    def _extract_cards_from_page(self, img: np.ndarray, page_num: int):
        """Extract 2 cards from one page."""
        height, width = img.shape[:2]

        # Each page has 2 cards vertically
        # Top card and bottom card
        cards = []

        # Split page into 2 halves
        half_height = height // 2

        for card_idx, (y_start, y_end) in enumerate([(0, half_height + 100), (half_height - 100, height)]):
            card_img = img[y_start:y_end, :]

            # Find the card contour
            card_data = self._find_and_extract_card(card_img, page_num, card_idx)

            if card_data:
                cards.append(card_data)

        return cards

    def _find_and_extract_card(self, img: np.ndarray, page_num: int, card_idx: int):
        """Find card in image and extract matrix + metadata."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Threshold to find black regions
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Find largest square-ish contour (the card)
        best_contour = None
        best_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 10000:  # Too small
                continue

            # Check if roughly square
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h if h > 0 else 0

            if 0.7 < aspect_ratio < 1.3 and area > best_area:  # Square-ish
                best_contour = cnt
                best_area = area

        if best_contour is None:
            return None

        # Extract card region
        x, y, w, h = cv2.boundingRect(best_contour)

        # Add padding
        padding = 50
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img.shape[1] - x, w + 2 * padding)
        h = min(img.shape[0] - y, h + 2 * padding)

        card_img = img[y : y + h, x : x + w]

        # Try to read card number from image (OCR or pattern matching)
        card_number = self._extract_card_number(img, x, y, w, h)

        # Save card image
        card_filename = f"card_{page_num:03d}_{card_idx}.png"
        card_path = os.path.join(self.output_dir, card_filename)
        cv2.imwrite(card_path, card_img)

        # Extract matrix using detector
        matrix = self._extract_matrix_from_card(card_img)

        return {
            "page": page_num,
            "index": card_idx,
            "number": card_number,
            "image_path": card_path,
            "matrix": matrix,
            "bbox": (x, y, w, h),
        }

    def _extract_card_number(self, img: np.ndarray, x: int, y: int, w: int, h: int):
        """Extract card number from surrounding text."""
        # Look for number below the card
        number_region = img[y + h : y + h + 100, x : x + w]

        # Simple OCR alternative: look for the card number pattern
        # For now, use page number as approximation
        # In production, use pytesseract or similar

        # Placeholder: return None, will be filled manually or via OCR
        return None

    def _extract_matrix_from_card(self, card_img: np.ndarray):
        """Extract 5x5 binary matrix from card image."""
        # Use existing detector logic
        gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Resize to standard size
        binary = cv2.resize(binary, (500, 500))

        # Extract 5x5 grid
        matrix = np.zeros((5, 5))
        cell_size = 100  # 500 / 5

        for row in range(5):
            for col in range(5):
                y_start = row * cell_size + 15
                y_end = (row + 1) * cell_size - 15
                x_start = col * cell_size + 15
                x_end = (col + 1) * cell_size - 15

                cell = binary[y_start:y_end, x_start:x_end]
                avg = np.mean(cell)

                # If mostly white (in inverted image), it's black in original
                matrix[row, col] = 1 if avg > 127 else 0

        return matrix

    def build_database(self, cards_data: list):
        """Build database from extracted cards."""
        import pickle

        card_matrices = []
        card_ids = []

        for card in cards_data:
            if card["matrix"] is not None:
                # Generate 4 rotations for each card
                base_matrix = card["matrix"]
                card_num = card["number"] if card["number"] else card["page"] * 2 + card["index"]

                for rotation, answer in enumerate(["A", "B", "C", "D"]):
                    rotated = np.rot90(base_matrix, rotation)
                    card_matrices.append(rotated)
                    card_ids.append(f"{card_num:03d}-{answer}")

        # Save database
        db_dir = os.path.join(PROJECT_ROOT, "data", "database_official")
        os.makedirs(db_dir, exist_ok=True)

        data_path = os.path.join(db_dir, "card.data")
        list_path = os.path.join(db_dir, "card.list")

        with open(data_path, "wb") as f:
            pickle.dump(card_matrices, f)

        with open(list_path, "wb") as f:
            pickle.dump(card_ids, f)

        print(f"\n✅ Database saved:")
        print(f"   📁 {data_path}")
        print(f"   📁 {list_path}")
        print(f"   📊 {len(card_matrices)} entries ({len(cards_data)} cards × 4 rotations)")

        return data_path, list_path


def main():
    """Main entry point."""
    pdf_path = os.path.join(PROJECT_ROOT, "data", "data_plickers", "PlickersCards_2up.pdf")

    if not os.path.exists(pdf_path):
        print(f"❌ Không tìm thấy file: {pdf_path}")
        return

    extractor = OfficialPDFExtractor(pdf_path)

    # Extract cards (process first 5 pages for testing)
    cards = extractor.extract_cards_from_pdf(max_pages=5)

    if cards:
        # Build database
        extractor.build_database(cards)

        print("\n🎉 Hoàn thành!")
        print(f"📂 Thẻ đã cắt: {extractor.output_dir}")
    else:
        print("\n❌ Không tìm thấy thẻ nào")


if __name__ == "__main__":
    main()
