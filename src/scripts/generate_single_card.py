# -*- coding: utf-8 -*-
"""
Generate Plickers cards - ONE CARD PER PAGE for maximum clarity.
Mỗi trang 1 thẻ, tránh chồng chéo thông tin.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.core.detector import PlickersDetector


class SingleCardGenerator:
    """Generate Plickers cards - ONE per page for clarity."""

    def __init__(self, output_path: str = None):
        if output_path is None:
            output_path = os.path.join(PROJECT_ROOT, "data", "output", "plickers_single_card.pdf")

        self.output_path = output_path
        self.detector = PlickersDetector()

        # Page size
        self.page_width, self.page_height = A4

        # Card size - large and centered
        self.card_size = 120 * mm  # Large scannable area
        self.cell_size = self.card_size / 5

        # Colors
        self.label_colors = {
            "A": HexColor("#FF5722"),  # Red
            "B": HexColor("#4CAF50"),  # Green
            "C": HexColor("#FF9800"),  # Orange
            "D": HexColor("#9C27B0"),  # Purple
        }

    def draw_instruction_page(self, c: canvas.Canvas):
        """Draw instruction page."""
        # Title
        c.setFillColor(HexColor("#2196F3"))
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(self.page_width / 2, self.page_height - 50 * mm, "THẺ PLICKERS")

        c.setFont("Helvetica", 16)
        c.drawCentredString(self.page_width / 2, self.page_height - 65 * mm, "Mỗi trang 1 thẻ - Rõ ràng, dễ sử dụng")

        # Instructions
        y = self.page_height - 90 * mm
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(40 * mm, y, "HƯỚNG DẪN:")
        y -= 15 * mm

        instructions = [
            "1. Mỗi học sinh nhận một thẻ có số riêng",
            "",
            "2. Giơ thẻ sao cho CHỮ CÁI đáp án ở phía TRÊN",
            "",
            "   • Chọn A → Chữ A ở trên",
            "   • Chọn B → Chữ B ở trên",
            "   • Chọn C → Chữ C ở trên",
            "   • Chọn D → Chữ D ở trên",
            "",
            "3. Giữ thẻ thẳng để camera quét",
        ]

        c.setFont("Helvetica", 14)
        for instruction in instructions:
            if instruction:
                c.drawString(45 * mm, y, instruction)
            y -= 8 * mm

        # Visual guide
        y -= 10 * mm
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40 * mm, y, "MÀU SẮC:")
        y -= 12 * mm

        labels = [
            ("A - Đỏ", self.label_colors["A"]),
            ("B - Xanh lá", self.label_colors["B"]),
            ("C - Cam", self.label_colors["C"]),
            ("D - Tím", self.label_colors["D"]),
        ]

        for label, color in labels:
            c.setFillColor(color)
            c.circle(50 * mm, y + 3, 4 * mm, fill=1, stroke=0)
            c.setFillColor(black)
            c.setFont("Helvetica", 14)
            c.drawString(60 * mm, y, label)
            y -= 10 * mm

        c.showPage()

    def draw_single_card(self, c: canvas.Canvas, matrix: np.ndarray, card_id: str):
        """Draw ONE large card centered on page."""
        # Calculate center position
        card_x = (self.page_width - self.card_size) / 2
        card_y = (self.page_height - self.card_size) / 2

        # Draw white background
        c.setFillColor(white)
        c.rect(card_x, card_y, self.card_size, self.card_size, fill=1, stroke=0)

        # Draw 5x5 matrix
        for row in range(5):
            for col in range(5):
                if matrix[row, col] == 1:
                    c.setFillColor(black)
                    cell_x = card_x + col * self.cell_size
                    cell_y = card_y + (4 - row) * self.cell_size
                    c.rect(cell_x, cell_y, self.cell_size, self.cell_size, fill=1, stroke=0)

        # Draw border
        c.setStrokeColor(black)
        c.setLineWidth(3)
        c.rect(card_x, card_y, self.card_size, self.card_size, fill=0, stroke=1)

        # Extract info
        parts = card_id.split("-")
        card_num = parts[0]
        answer = parts[1] if len(parts) > 1 else "A"

        # Draw labels with LARGE spacing
        self._draw_labels_with_spacing(c, card_x, card_y, card_num, answer)

    def _draw_labels_with_spacing(
        self, c: canvas.Canvas, card_x: float, card_y: float, card_num: str, correct_answer: str
    ):
        """Draw labels with large spacing to avoid overlap."""
        # Card number at TOP (above card)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 28)
        text_width = c.stringWidth(f"THẺ SỐ {card_num}", "Helvetica-Bold", 28)
        c.drawString(
            (self.page_width - text_width) / 2,
            card_y + self.card_size + 20 * mm,
            f"THẺ SỐ {card_num}",
        )

        # Answer rotation
        answers = ["A", "B", "C", "D"]
        correct_idx = answers.index(correct_answer)
        rotated_answers = answers[correct_idx:] + answers[:correct_idx]

        # Label positions - FAR from card edges
        spacing = 25 * mm  # Large spacing

        label_positions = {
            "top": (self.page_width / 2, card_y + self.card_size + spacing, 0),
            "right": (card_x + self.card_size + spacing, self.page_height / 2, 270),
            "bottom": (self.page_width / 2, card_y - spacing, 180),
            "left": (card_x - spacing, self.page_height / 2, 90),
        }

        positions = ["top", "right", "bottom", "left"]

        for i, pos_key in enumerate(positions):
            label = rotated_answers[i]
            lx, ly, rotation = label_positions[pos_key]

            c.saveState()
            c.translate(lx, ly)
            c.rotate(rotation)

            # Large colored circle
            c.setFillColor(self.label_colors[label])
            c.circle(0, 0, 10 * mm, fill=1, stroke=0)

            # Large letter
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 32)
            text_width = c.stringWidth(label, "Helvetica-Bold", 32)
            c.drawString(-text_width / 2, -10, label)

            c.restoreState()

        # Instruction at BOTTOM (below card)
        c.setFillColor(HexColor("#666666"))
        c.setFont("Helvetica", 12)
        instruction = f"Để chọn đáp án, giơ thẻ sao cho chữ cái tương ứng ở phía TRÊN"
        text_width = c.stringWidth(instruction, "Helvetica", 12)
        c.drawString(
            (self.page_width - text_width) / 2,
            card_y - spacing - 15 * mm,
            instruction,
        )

    def generate_pdf(self, num_cards: int = 34):
        """Generate PDF with ONE card per page."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        c = canvas.Canvas(self.output_path, pagesize=A4)
        c.setTitle("Thẻ Plickers - 1 thẻ/trang")

        # Instruction page
        self.draw_instruction_page(c)

        # Generate cards - ONE per page
        available_cards = min(num_cards, len(self.detector.card_list))

        for card_idx in range(available_cards):
            # Get card data
            card_id = self.detector.card_list[card_idx]
            matrix = self.detector.card_data[card_idx]

            # Draw card
            self.draw_single_card(c, matrix, card_id)

            # New page for next card
            c.showPage()

        c.save()
        print(f"✅ Đã tạo {available_cards} thẻ")
        print(f"📄 Lưu tại: {self.output_path}")
        print(f"📏 Kích thước thẻ: {int(self.card_size/mm)}mm x {int(self.card_size/mm)}mm")
        print(f"📃 Tổng số trang: {available_cards + 1} (1 trang hướng dẫn + {available_cards} thẻ)")
        print("✨ MỖI TRANG 1 THẺ - Không bị chồng chéo!")


def main():
    """Main entry point."""
    generator = SingleCardGenerator()
    generator.generate_pdf(num_cards=34)


if __name__ == "__main__":
    main()
