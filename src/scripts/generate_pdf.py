"""
Script tạo PDF in thẻ Plickers cho học sinh.
Mỗi trang A4 chứa 6 thẻ, 2 cột x 3 hàng.
Mỗi thẻ có viền màu, số thứ tự học sinh, và ký hiệu ABCD 4 hướng rõ ràng.
"""

import os
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "data", "samples")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "output")
OUTPUT_PDF = os.path.join(OUTPUT_DIR, "the_plickers_hoc_sinh.pdf")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Bảng màu nền xen kẽ cho mỗi thẻ ---
CARD_BG_COLORS = [
    colors.HexColor("#EAF4FB"),  # xanh nhạt
    colors.HexColor("#FEF9E7"),  # vàng nhạt
    colors.HexColor("#EAFAF1"),  # xanh lá nhạt
    colors.HexColor("#FDEDEC"),  # hồng nhạt
    colors.HexColor("#F4ECF7"),  # tím nhạt
    colors.HexColor("#FDF2E9"),  # cam nhạt
]

BORDER_COLORS = [
    colors.HexColor("#2E86C1"),
    colors.HexColor("#F39C12"),
    colors.HexColor("#27AE60"),
    colors.HexColor("#E74C3C"),
    colors.HexColor("#8E44AD"),
    colors.HexColor("#D35400"),
]

PAGE_W, PAGE_H = A4  # 595.27 x 841.89 pt
MARGIN = 1.5 * cm
COLS = 2
ROWS = 3
CARDS_PER_PAGE = COLS * ROWS

card_w = (PAGE_W - 2 * MARGIN - 0.5 * cm) / COLS  # width of each card cell
card_h = (PAGE_H - 2 * MARGIN - 1.0 * cm) / ROWS  # height of each card cell

IMG_PAD = 0.9 * cm  # padding inside card cell
IMG_SIZE = min(card_w, card_h) - 2 * IMG_PAD - 0.8 * cm  # photo square size

LABEL_FONT = "Helvetica-Bold"
NUM_FONT = "Helvetica-Bold"
ABCD_COLORS = {
    "A": colors.HexColor("#E74C3C"),
    "B": colors.HexColor("#2E86C1"),
    "C": colors.HexColor("#27AE60"),
    "D": colors.HexColor("#F39C12"),
}


def draw_card(c: canvas.Canvas, x, y, card_img_path, student_no, answer_letter, color_idx):
    """Vẽ 1 ô thẻ học sinh."""
    bg = CARD_BG_COLORS[color_idx % len(CARD_BG_COLORS)]
    bdr = BORDER_COLORS[color_idx % len(BORDER_COLORS)]

    # --- Nền & viền ---
    c.setFillColor(bg)
    c.setStrokeColor(bdr)
    c.setLineWidth(2.5)
    c.roundRect(x, y, card_w, card_h, 8, fill=1, stroke=1)

    # --- Tiêu đề: số thứ tự học sinh ---
    c.setFillColor(bdr)
    c.setFont(NUM_FONT, 13)
    c.drawCentredString(x + card_w / 2, y + card_h - 0.65 * cm, f"Học sinh số  {student_no:02d}")

    # Ảnh thẻ
    img_x = x + (card_w - IMG_SIZE) / 2
    img_y = y + card_h / 2 - IMG_SIZE / 2 + 0.15 * cm
    if os.path.exists(card_img_path):
        img = ImageReader(card_img_path)
        c.drawImage(img, img_x, img_y, IMG_SIZE, IMG_SIZE, preserveAspectRatio=True, anchor="c")

    # --- Viền ảnh ---
    c.setStrokeColor(bdr)
    c.setLineWidth(1.2)
    c.rect(img_x, img_y, IMG_SIZE, IMG_SIZE)

    # --- Label ABCD ở 4 góc quanh ảnh với mũi tên hướng ---
    #  A = Trên (phía trên ảnh)
    #  B = Phải (phía phải ảnh)
    #  C = Dưới (phía dưới ảnh)
    #  D = Trái (phía trái ảnh)
    abcd_font_size = 14
    abcd_offset = 0.5 * cm

    labels = [
        ("A", img_x + IMG_SIZE / 2, img_y + IMG_SIZE + abcd_offset, "↑ A"),
        ("B", img_x + IMG_SIZE + abcd_offset / 1.5, img_y + IMG_SIZE / 2, "B →"),
        ("C", img_x + IMG_SIZE / 2, img_y - abcd_offset + 3, "C ↓"),
        ("D", img_x - abcd_offset / 1.5, img_y + IMG_SIZE / 2, "← D"),
    ]

    for letter, lx, ly, text in labels:
        c.setFillColor(ABCD_COLORS[letter])
        c.setFont(LABEL_FONT, abcd_font_size)
        c.drawCentredString(lx, ly, text)

    # --- Đáp án hiện tại của ảnh mẫu (nhỏ ở góc dưới phải) ---
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.grey)
    c.drawRightString(x + card_w - 4, y + 4, f"[Mẫu: {answer_letter}]")


def build_pdf():
    # Lấy danh sách ảnh đã sắp xếp
    files = sorted([f for f in os.listdir(SAMPLES_DIR) if f.endswith(".jpg")])

    c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    c.setTitle("Thẻ Plickers - In cho Học sinh")
    c.setAuthor("Plickers Python")

    for i, filename in enumerate(files):
        col = i % COLS
        row = (i // COLS) % ROWS

        # Bắt đầu trang mới
        if i > 0 and i % CARDS_PER_PAGE == 0:
            # Footer trang
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.grey)
            c.drawCentredString(PAGE_W / 2, 0.6 * cm, f"Trang {i // CARDS_PER_PAGE} — Plickers Classroom Scanner")
            c.showPage()

        # Tạo trang đầu tiên: Header
        if i % CARDS_PER_PAGE == 0:
            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(colors.HexColor("#1A252F"))
            c.drawCentredString(PAGE_W / 2, PAGE_H - 0.9 * cm, "📋 THẺ PLICKERS — CẦM ĐÚNG HƯỚNG ĐÁP ÁN LÊN TRÊN ĐẦU")
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.grey)
            c.drawCentredString(
                PAGE_W / 2, PAGE_H - 1.4 * cm, "Hướng nào lên đầu = Đáp án đó.  A=Trên  B=Phải  C=Dưới  D=Trái"
            )

        # Vị trí ô thẻ
        x = MARGIN + col * (card_w + 0.5 * cm)
        y = PAGE_H - MARGIN - 1.2 * cm - (row + 1) * card_h + 0.3 * cm * row

        # Phân tích tên file: e.g. "003-A.jpg" → student_no=3, answer='A'
        name = filename.replace(".jpg", "")
        parts = name.split("-")
        try:
            student_no = int(parts[0])
        except:
            student_no = i + 1
        answer = parts[1] if len(parts) > 1 else "?"

        img_path = os.path.join(SAMPLES_DIR, filename)
        draw_card(c, x, y, img_path, student_no, answer, i)

    # Footer trang cuối
    total_pages = (len(files) - 1) // CARDS_PER_PAGE + 1
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(PAGE_W / 2, 0.6 * cm, f"Trang {total_pages} — Plickers Classroom Scanner")

    c.save()
    print(f"[OK] Da tao PDF thanh cong: {OUTPUT_PDF}")
    print(f"     Tong so the: {len(files)}")
    print(f"     Tong so trang: {total_pages}")


if __name__ == "__main__":
    build_pdf()
