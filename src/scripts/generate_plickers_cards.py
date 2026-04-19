"""
Generate authentic Plickers-style cards for printing.
Creates PDF with proper card layout matching official Plickers design.
"""

import os
import sys
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.core.detector import PlickersDetector


class PlickersCardGenerator:
    """Generate authentic Plickers cards matching official design."""

    def __init__(self, output_path: str = None):
        """
        Initialize card generator.

        Args:
            output_path: Path to save PDF file
        """
        if output_path is None:
            output_path = os.path.join(PROJECT_ROOT, "data", "output", "plickers_cards_official.pdf")

        self.output_path = output_path
        self.detector = PlickersDetector()

        # Card dimensions (matching official Plickers)
        self.card_size = 80 * mm  # 80mm x 80mm per card
        self.cell_size = self.card_size / 5  # 5x5 grid
        self.margin = 10 * mm

        # Page layout
        self.page_width, self.page_height = A4
        self.cards_per_row = 2
        self.cards_per_col = 3
        self.cards_per_page = self.cards_per_row * self.cards_per_col

    def draw_card_matrix(self, c: canvas.Canvas, x: float, y: float, matrix: np.ndarray, card_id: str):
        """
        Draw a single Plickers card with 5x5 matrix.

        Args:
            c: ReportLab canvas
            x: X position (bottom-left)
            y: Y position (bottom-left)
            matrix: 5x5 numpy array (0=white, 1=black)
            card_id: Card identifier (e.g., "001-A")
        """
        # Draw white background
        c.setFillColorRGB(1, 1, 1)
        c.rect(x, y, self.card_size, self.card_size, fill=1, stroke=0)

        # Draw 5x5 grid
        for row in range(5):
            for col in range(5):
                if matrix[row, col] == 1:  # Black cell
                    c.setFillColorRGB(0, 0, 0)
                    cell_x = x + col * self.cell_size
                    cell_y = y + (4 - row) * self.cell_size  # Flip Y axis
                    c.rect(cell_x, cell_y, self.cell_size, self.cell_size, fill=1, stroke=0)

        # Draw border
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(2)
        c.rect(x, y, self.card_size, self.card_size, fill=0, stroke=1)

        # Extract card number and answer
        parts = card_id.split("-")
        card_num = parts[0]
        answer = parts[1] if len(parts) > 1 else "A"

        # Draw card number in center (large)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.setFont("Helvetica-Bold", 24)
        text_width = c.stringWidth(card_num, "Helvetica-Bold", 24)
        c.drawString(x + (self.card_size - text_width) / 2, y + self.card_size / 2 - 8, card_num)

        # Draw answer labels on each side with proper rotation
        self._draw_answer_labels(c, x, y, answer)

    def _draw_answer_labels(self, c: canvas.Canvas, x: float, y: float, correct_answer: str):
        """
        Draw A/B/C/D labels on card edges with proper rotation.
        The correct answer is at the TOP when card is held correctly.

        Args:
            c: Canvas
            x: Card X position
            y: Card Y position
            correct_answer: The answer that should be at top (A/B/C/D)
        """
        # Answer positions relative to card orientation
        # When correct_answer is at TOP, others are rotated accordingly
        answers = ["A", "B", "C", "D"]
        correct_idx = answers.index(correct_answer)

        # Rotate answers so correct one is at top
        rotated_answers = answers[correct_idx:] + answers[:correct_idx]

        label_positions = {
            "top": (x + self.card_size / 2, y + self.card_size - 5 * mm, 0),  # Top
            "right": (x + self.card_size - 5 * mm, y + self.card_size / 2, 270),  # Right (rotated)
            "bottom": (x + self.card_size / 2, y + 5 * mm, 180),  # Bottom (upside down)
            "left": (x + 5 * mm, y + self.card_size / 2, 90),  # Left (rotated)
        }

        positions = ["top", "right", "bottom", "left"]

        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0, 0, 0)

        for i, pos_key in enumerate(positions):
            label = rotated_answers[i]
            lx, ly, rotation = label_positions[pos_key]

            c.saveState()
            c.translate(lx, ly)
            c.rotate(rotation)

            # Draw label
            text_width = c.stringWidth(label, "Helvetica-Bold", 14)
            c.drawString(-text_width / 2, -5, label)

            c.restoreState()

    def generate_pdf(self, num_cards: int = 34):
        """
        Generate PDF with Plickers cards.

        Args:
            num_cards: Number of unique cards to generate (default 34 for a class)
        """
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        c = canvas.Canvas(self.output_path, pagesize=A4)

        # Title page
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50 * mm, self.page_height - 40 * mm, "Plickers Cards - Thẻ Trả Lời")
        c.setFont("Helvetica", 12)
        c.drawString(50 * mm, self.page_height - 50 * mm, f"Tổng số thẻ: {num_cards}")
        c.drawString(50 * mm, self.page_height - 60 * mm, "Hướng dẫn: Giơ thẻ sao cho đáp án bạn chọn ở phía TRÊN")
        c.drawString(50 * mm, self.page_height - 70 * mm, "Instructions: Hold card with your answer at the TOP")

        # Draw answer orientation guide
        guide_y = self.page_height - 100 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50 * mm, guide_y, "Ví dụ: Nếu chọn đáp án B, giơ thẻ sao cho chữ B ở phía trên")

        c.showPage()

        # Generate cards
        card_count = 0
        page_count = 0

        # Get available card matrices from database
        available_cards = min(num_cards, len(self.detector.card_list))

        for card_idx in range(available_cards):
            if card_count % self.cards_per_page == 0 and card_count > 0:
                c.showPage()
                page_count += 1

            # Calculate position on page
            card_on_page = card_count % self.cards_per_page
            row = card_on_page // self.cards_per_row
            col = card_on_page % self.cards_per_row

            # Calculate card position
            x = self.margin + col * (self.card_size + self.margin)
            y = self.page_height - self.margin - (row + 1) * (self.card_size + self.margin)

            # Get card data
            card_id = self.detector.card_list[card_idx]
            matrix = self.detector.card_data[card_idx]

            # Draw card
            self.draw_card_matrix(c, x, y, matrix, card_id)

            card_count += 1

        c.save()
        print(f"✅ Generated {card_count} cards")
        print(f"📄 Saved to: {self.output_path}")
        print(f"📏 Card size: 80mm x 80mm")
        print(f"📃 Total pages: {page_count + 1}")


def main():
    """Main entry point."""
    generator = PlickersCardGenerator()
    generator.generate_pdf(num_cards=34)


if __name__ == "__main__":
    main()
