"""
Generate premium Plickers cards with enhanced design and instructions.
Professional layout matching official Plickers with Vietnamese instructions.
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


class PremiumPlickersGenerator:
    """Generate premium Plickers cards with professional design."""

    def __init__(self, output_path: str = None):
        if output_path is None:
            output_path = os.path.join(PROJECT_ROOT, "data", "output", "plickers_cards_premium.pdf")

        self.output_path = output_path
        self.detector = PlickersDetector()

        # Design constants
        self.card_size = 85 * mm
        self.cell_size = self.card_size / 5
        self.margin = 12 * mm
        self.page_width, self.page_height = A4

        # Colors
        self.primary_color = HexColor("#2196F3")  # Blue
        self.accent_color = HexColor("#FF5722")  # Orange
        self.text_color = HexColor("#212121")  # Dark gray

    def draw_instruction_page(self, c: canvas.Canvas):
        """Draw comprehensive instruction page."""
        c.setFillColor(self.primary_color)
        c.rect(0, self.page_height - 60 * mm, self.page_width, 60 * mm, fill=1, stroke=0)

        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(self.page_width / 2, self.page_height - 35 * mm, "THẺ TRẢ LỜI PLICKERS")

        c.setFont("Helvetica", 14)
        c.drawCentredString(self.page_width / 2, self.page_height - 45 * mm, "Plickers Response Cards")

        # Instructions section
        y = self.page_height - 80 * mm
        c.setFillColor(self.text_color)

        # Vietnamese instructions
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30 * mm, y, "📋 HƯỚNG DẪN SỬ DỤNG")
        y -= 10 * mm

        instructions_vi = [
            "1. Mỗi học sinh nhận một thẻ có số riêng (từ 1 đến 34)",
            "2. Khi giáo viên đưa ra câu hỏi, chọn đáp án A, B, C hoặc D",
            "3. Giơ thẻ lên sao cho CHỮ CÁI đáp án bạn chọn ở phía TRÊN",
            "4. Giữ thẻ thẳng và rõ ràng để camera có thể quét",
            "5. Đợi giáo viên xác nhận đã quét xong",
        ]

        c.setFont("Helvetica", 11)
        for instruction in instructions_vi:
            c.drawString(35 * mm, y, instruction)
            y -= 7 * mm

        y -= 5 * mm

        # English instructions
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30 * mm, y, "📖 INSTRUCTIONS")
        y -= 8 * mm

        instructions_en = [
            "1. Each student receives a card with a unique number (1-34)",
            "2. When teacher asks a question, choose answer A, B, C, or D",
            "3. Hold card with your CHOSEN LETTER at the TOP",
            "4. Keep card straight and clear for camera scanning",
            "5. Wait for teacher confirmation",
        ]

        c.setFont("Helvetica", 10)
        for instruction in instructions_en:
            c.drawString(35 * mm, y, instruction)
            y -= 6 * mm

        # Visual guide
        y -= 10 * mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30 * mm, y, "🎯 VÍ DỤ MINH HỌA")
        y -= 8 * mm

        # Draw example boxes
        examples = [
            ("Chọn A", "A ở trên", self.primary_color),
            ("Chọn B", "B ở trên", HexColor("#4CAF50")),
            ("Chọn C", "C ở trên", HexColor("#FF9800")),
            ("Chọn D", "D ở trên", self.accent_color),
        ]

        box_width = 40 * mm
        box_height = 15 * mm
        x_start = 30 * mm

        for i, (label, instruction, color) in enumerate(examples):
            x = x_start + (i % 2) * (box_width + 10 * mm)
            box_y = y - (i // 2) * (box_height + 5 * mm)

            # Draw box
            c.setFillColor(color)
            c.roundRect(x, box_y - box_height, box_width, box_height, 3 * mm, fill=1, stroke=0)

            # Draw text
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x + box_width / 2, box_y - 6 * mm, label)
            c.setFont("Helvetica", 9)
            c.drawCentredString(x + box_width / 2, box_y - 11 * mm, instruction)

        # Footer
        c.setFillColor(self.text_color)
        c.setFont("Helvetica", 9)
        c.drawCentredString(
            self.page_width / 2,
            20 * mm,
            "💡 Mẹo: Giữ thẻ ổn định và tránh che khuất để quét chính xác nhất",
        )

        c.showPage()

    def draw_enhanced_card(self, c: canvas.Canvas, x: float, y: float, matrix: np.ndarray, card_id: str):
        """Draw enhanced card with better visual design."""
        # Shadow effect
        c.setFillColorRGB(0.8, 0.8, 0.8)
        c.roundRect(x + 2, y - 2, self.card_size, self.card_size, 3, fill=1, stroke=0)

        # White background
        c.setFillColor(white)
        c.roundRect(x, y, self.card_size, self.card_size, 3, fill=1, stroke=0)

        # Draw 5x5 matrix
        for row in range(5):
            for col in range(5):
                if matrix[row, col] == 1:
                    c.setFillColor(black)
                    cell_x = x + col * self.cell_size
                    cell_y = y + (4 - row) * self.cell_size
                    c.rect(cell_x, cell_y, self.cell_size, self.cell_size, fill=1, stroke=0)

        # Border with color accent
        c.setStrokeColor(self.primary_color)
        c.setLineWidth(3)
        c.roundRect(x, y, self.card_size, self.card_size, 3, fill=0, stroke=1)

        # Card info
        parts = card_id.split("-")
        card_num = parts[0]
        answer = parts[1] if len(parts) > 1 else "A"

        # Card number with background
        c.setFillColor(self.primary_color)
        num_box_size = 18 * mm
        c.circle(x + self.card_size / 2, y + self.card_size / 2, num_box_size / 2, fill=1, stroke=0)

        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 28)
        text_width = c.stringWidth(card_num, "Helvetica-Bold", 28)
        c.drawString(x + (self.card_size - text_width) / 2, y + self.card_size / 2 - 9, card_num)

        # Answer labels with enhanced styling
        self._draw_enhanced_labels(c, x, y, answer)

    def _draw_enhanced_labels(self, c: canvas.Canvas, x: float, y: float, correct_answer: str):
        """Draw answer labels with enhanced styling."""
        answers = ["A", "B", "C", "D"]
        correct_idx = answers.index(correct_answer)
        rotated_answers = answers[correct_idx:] + answers[:correct_idx]

        label_positions = {
            "top": (x + self.card_size / 2, y + self.card_size - 4 * mm, 0),
            "right": (x + self.card_size - 4 * mm, y + self.card_size / 2, 270),
            "bottom": (x + self.card_size / 2, y + 4 * mm, 180),
            "left": (x + 4 * mm, y + self.card_size / 2, 90),
        }

        positions = ["top", "right", "bottom", "left"]
        colors = [self.accent_color, HexColor("#4CAF50"), HexColor("#FF9800"), HexColor("#9C27B0")]

        for i, pos_key in enumerate(positions):
            label = rotated_answers[i]
            lx, ly, rotation = label_positions[pos_key]

            c.saveState()
            c.translate(lx, ly)
            c.rotate(rotation)

            # Background circle
            c.setFillColor(colors[i])
            c.circle(0, 0, 4 * mm, fill=1, stroke=0)

            # Label text
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 16)
            text_width = c.stringWidth(label, "Helvetica-Bold", 16)
            c.drawString(-text_width / 2, -5, label)

            c.restoreState()

    def generate_pdf(self, num_cards: int = 34):
        """Generate premium PDF."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        c = canvas.Canvas(self.output_path, pagesize=A4)

        # Instruction page
        self.draw_instruction_page(c)

        # Generate cards (2 per page for better print quality)
        cards_per_page = 2
        available_cards = min(num_cards, len(self.detector.card_list))

        for card_idx in range(available_cards):
            if card_idx % cards_per_page == 0 and card_idx > 0:
                c.showPage()

            # Position (centered, 2 cards vertically)
            card_on_page = card_idx % cards_per_page
            x = (self.page_width - self.card_size) / 2
            y = self.page_height - 40 * mm - (card_on_page + 1) * (self.card_size + 20 * mm)

            # Get card data
            card_id = self.detector.card_list[card_idx]
            matrix = self.detector.card_data[card_idx]

            # Draw card
            self.draw_enhanced_card(c, x, y, matrix, card_id)

            # Card label below
            c.setFillColor(self.text_color)
            c.setFont("Helvetica", 10)
            c.drawCentredString(x + self.card_size / 2, y - 8 * mm, f"Thẻ số {card_id.split('-')[0]}")

        c.save()
        print(f"✅ Generated {available_cards} premium cards")
        print(f"📄 Saved to: {self.output_path}")


def main():
    generator = PremiumPlickersGenerator()
    generator.generate_pdf(num_cards=34)


if __name__ == "__main__":
    main()
