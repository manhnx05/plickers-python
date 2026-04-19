# -*- coding: utf-8 -*-
"""
Generate clean Plickers cards - Labels OUTSIDE the scannable area.
Chữ và số nằm BÊN NGOÀI vùng quét, chỉ có ma trận đen trắng bên trong.
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


class CleanPlickersGenerator:
    """Generate clean Plickers cards with labels outside scannable area."""

    def __init__(self, output_path: str = None):
        if output_path is None:
            output_path = os.path.join(PROJECT_ROOT, "data", "output", "plickers_cards_clean.pdf")

        self.output_path = output_path
        self.detector = PlickersDetector()

        # Card dimensions
        self.card_size = 80 * mm  # Scannable area only
        self.cell_size = self.card_size / 5
        self.label_space = 15 * mm  # Space for labels outside
        self.total_card_size = self.card_size + 2 * self.label_space

        # Page layout
        self.page_width, self.page_height = A4
        self.margin = 10 * mm
        self.cards_per_row = 2
        self.cards_per_col = 3

        # Colors
        self.primary_color = HexColor("#2196F3")
        self.label_colors = {
            "A": HexColor("#FF5722"),  # Red-Orange
            "B": HexColor("#4CAF50"),  # Green
            "C": HexColor("#FF9800"),  # Orange
            "D": HexColor("#9C27B0"),  # Purple
        }

    def draw_instruction_page(self, c: canvas.Canvas):
        """Draw instruction page in Vietnamese."""
        # Header
        c.setFillColor(self.primary_color)
        c.rect(0, self.page_height - 60 * mm, self.page_width, 60 * mm, fill=1, stroke=0)

        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(self.page_width / 2, self.page_height - 35 * mm, "THẺ TRẢ LỜI PLICKERS")

        c.setFont("Helvetica", 14)
        c.drawCentredString(self.page_width / 2, self.page_height - 45 * mm, "Plickers Response Cards")

        # Instructions
        y = self.page_height - 80 * mm
        c.setFillColor(black)

        c.setFont("Helvetica-Bold", 16)
        c.drawString(30 * mm, y, "HƯỚNG DẪN SỬ DỤNG")
        y -= 10 * mm

        instructions = [
            "1. Mỗi học sinh nhận một thẻ có số riêng (từ 1 đến 34)",
            "",
            "2. Khi giáo viên đưa ra câu hỏi, chọn đáp án A, B, C hoặc D",
            "",
            "3. Giơ thẻ lên sao cho CHỮ CÁI đáp án bạn chọn ở phía TRÊN",
            "",
            "4. Giữ thẻ thẳng và rõ ràng để camera có thể quét",
            "",
            "5. Đợi giáo viên xác nhận đã quét xong",
        ]

        c.setFont("Helvetica", 12)
        for instruction in instructions:
            if instruction:
                c.drawString(35 * mm, y, instruction)
            y -= 7 * mm

        # Visual examples
        y -= 5 * mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30 * mm, y, "VÍ DỤ:")
        y -= 10 * mm

        examples = [
            ("Chọn A", "Chữ A ở trên", self.label_colors["A"]),
            ("Chọn B", "Chữ B ở trên", self.label_colors["B"]),
            ("Chọn C", "Chữ C ở trên", self.label_colors["C"]),
            ("Chọn D", "Chữ D ở trên", self.label_colors["D"]),
        ]

        box_width = 40 * mm
        box_height = 15 * mm
        x_start = 30 * mm

        for i, (label, instruction, color) in enumerate(examples):
            x = x_start + (i % 2) * (box_width + 10 * mm)
            box_y = y - (i // 2) * (box_height + 5 * mm)

            c.setFillColor(color)
            c.roundRect(x, box_y - box_height, box_width, box_height, 3 * mm, fill=1, stroke=0)

            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x + box_width / 2, box_y - 6 * mm, label)
            c.setFont("Helvetica", 9)
            c.drawCentredString(x + box_width / 2, box_y - 11 * mm, instruction)

        # Footer
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawCentredString(
            self.page_width / 2,
            20 * mm,
            "Lưu ý: Giữ thẻ ổn định và tránh che khuất để quét chính xác nhất",
        )

        c.showPage()

    def draw_clean_card(self, c: canvas.Canvas, x: float, y: float, matrix: np.ndarray, card_id: str):
        """
        Draw card with ONLY black/white matrix inside.
        Labels are placed OUTSIDE the scannable area.
        """
        # Calculate center position for the scannable card
        card_x = x + self.label_space
        card_y = y + self.label_space

        # Draw white background for scannable area
        c.setFillColor(white)
        c.rect(card_x, card_y, self.card_size, self.card_size, fill=1, stroke=0)

        # Draw 5x5 matrix (ONLY black and white, no decorations)
        for row in range(5):
            for col in range(5):
                if matrix[row, col] == 1:  # Black cell
                    c.setFillColor(black)
                    cell_x = card_x + col * self.cell_size
                    cell_y = card_y + (4 - row) * self.cell_size
                    c.rect(cell_x, cell_y, self.cell_size, self.cell_size, fill=1, stroke=0)

        # Draw border around scannable area
        c.setStrokeColor(black)
        c.setLineWidth(2)
        c.rect(card_x, card_y, self.card_size, self.card_size, fill=0, stroke=1)

        # Extract card info
        parts = card_id.split("-")
        card_num = parts[0]
        answer = parts[1] if len(parts) > 1 else "A"

        # Draw labels OUTSIDE the card
        self._draw_outside_labels(c, x, y, card_num, answer)

    def _draw_outside_labels(self, c: canvas.Canvas, x: float, y: float, card_num: str, correct_answer: str):
        """Draw labels outside the scannable card area."""
        # Card number at bottom center
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 14)
        text_width = c.stringWidth(f"Thẻ số {card_num}", "Helvetica-Bold", 14)
        c.drawString(
            x + (self.total_card_size - text_width) / 2,
            y + 3 * mm,
            f"Thẻ số {card_num}",
        )

        # Answer labels on 4 sides (OUTSIDE the card)
        answers = ["A", "B", "C", "D"]
        correct_idx = answers.index(correct_answer)
        rotated_answers = answers[correct_idx:] + answers[:correct_idx]

        # Label positions (outside the scannable area)
        label_positions = {
            "top": (
                x + self.total_card_size / 2,
                y + self.total_card_size - 5 * mm,
                0,
            ),  # Top
            "right": (
                x + self.total_card_size - 5 * mm,
                y + self.total_card_size / 2,
                270,
            ),  # Right
            "bottom": (x + self.total_card_size / 2, y + 5 * mm, 180),  # Bottom
            "left": (x + 5 * mm, y + self.total_card_size / 2, 90),  # Left
        }

        positions = ["top", "right", "bottom", "left"]

        for i, pos_key in enumerate(positions):
            label = rotated_answers[i]
            lx, ly, rotation = label_positions[pos_key]

            c.saveState()
            c.translate(lx, ly)
            c.rotate(rotation)

            # Draw colored circle background
            c.setFillColor(self.label_colors[label])
            c.circle(0, 0, 5 * mm, fill=1, stroke=0)

            # Draw letter
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 18)
            text_width = c.stringWidth(label, "Helvetica-Bold", 18)
            c.drawString(-text_width / 2, -6, label)

            c.restoreState()

    def generate_pdf(self, num_cards: int = 34):
        """Generate clean PDF with proper Vietnamese encoding."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        c = canvas.Canvas(self.output_path, pagesize=A4)

        # Set encoding for Vietnamese
        c.setTitle("Thẻ Plickers")
        c.setAuthor("Plickers Python")

        # Instruction page
        self.draw_instruction_page(c)

        # Generate cards
        available_cards = min(num_cards, len(self.detector.card_list))
        cards_per_page = self.cards_per_row * self.cards_per_col

        for card_idx in range(available_cards):
            if card_idx % cards_per_page == 0 and card_idx > 0:
                c.showPage()

            # Calculate position
            card_on_page = card_idx % cards_per_page
            row = card_on_page // self.cards_per_row
            col = card_on_page % self.cards_per_row

            x = self.margin + col * (self.total_card_size + self.margin)
            y = self.page_height - self.margin - (row + 1) * (self.total_card_size + self.margin)

            # Get card data
            card_id = self.detector.card_list[card_idx]
            matrix = self.detector.card_data[card_idx]

            # Draw card
            self.draw_clean_card(c, x, y, matrix, card_id)

        c.save()
        print(f"✅ Đã tạo {available_cards} thẻ")
        print(f"📄 Lưu tại: {self.output_path}")
        print(f"📏 Vùng quét: {int(self.card_size/mm)}mm x {int(self.card_size/mm)}mm")
        print(f"📐 Kích thước tổng: {int(self.total_card_size/mm)}mm x {int(self.total_card_size/mm)}mm")
        print("✨ Chữ và số nằm BÊN NGOÀI vùng quét")


def main():
    """Main entry point."""
    generator = CleanPlickersGenerator()
    generator.generate_pdf(num_cards=34)


if __name__ == "__main__":
    main()
