"""
Generate Plickers-style printable card PDF.
Chạy bằng: python src/scripts/generate_plickers_pdf.py
Yêu cầu: data/database/card.data và card.list đã được tạo bởi generate_db.py
"""

import os
import sys
import pickle
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_DATA = os.path.join(DATA_DIR, "database", "card.data")
DB_LIST = os.path.join(DATA_DIR, "database", "card.list")
OUTPUT = os.path.join(DATA_DIR, "output", "plickers_cards_print.pdf")


def _load_database() -> dict:
    """Load card database từ file binary. Raise rõ ràng nếu chưa tồn tại."""
    if not os.path.exists(DB_DATA) or not os.path.exists(DB_LIST):
        raise FileNotFoundError(
            f"Database chưa tồn tại.\n"
            f"Hãy chạy trước: python src/scripts/generate_db.py\n"
            f"Đường dẫn cần có:\n  {DB_DATA}\n  {DB_LIST}"
        )
    with open(DB_DATA, "rb") as f:
        card_data = pickle.load(f)
    with open(DB_LIST, "rb") as f:
        card_list = pickle.load(f)
    return {cid: mat for mat, cid in zip(card_data, card_list)}


PAGE_W_MM, PAGE_H_MM = 210, 297
MARGIN_MM = 12
GAP_MM = 8
COLS, ROWS = 2, 3
CARDS_PER_PAGE = COLS * ROWS

card_w_mm = (PAGE_W_MM - 2 * MARGIN_MM - (COLS - 1) * GAP_MM) / COLS
card_h_mm = (PAGE_H_MM - 2 * MARGIN_MM - (ROWS - 1) * GAP_MM) / ROWS
CARD_W = card_w_mm * mm
CARD_H = card_h_mm * mm

ABCD_ZONE = 10
GRID_MM = min(card_w_mm, card_h_mm) - 2 * ABCD_ZONE
CELL_MM = GRID_MM / 5

BORDER_COLORS = [
    colors.HexColor("#1e3a5f"),
    colors.HexColor("#1a3d2b"),
    colors.HexColor("#4a1942"),
    colors.HexColor("#5c2800"),
    colors.HexColor("#1c3a4a"),
    colors.HexColor("#3d2014"),
]
ABCD_CLR = {
    "A": colors.HexColor("#ef4444"),
    "B": colors.HexColor("#3b82f6"),
    "C": colors.HexColor("#22c55e"),
    "D": colors.HexColor("#f59e0b"),
}


def draw_badge(cvs, lx, ly, angle, letter, card_no, clr):
    r = 5.6 * mm
    cvs.setFillColor(clr)
    cvs.circle(lx, ly, r, fill=1, stroke=0)
    cvs.saveState()
    cvs.translate(lx, ly)
    cvs.rotate(angle)
    cvs.setFillColor(colors.white)
    cvs.setFont("Helvetica-Bold", 11)
    cvs.drawCentredString(0, 1.3 * mm, letter)
    cvs.setFont("Helvetica-Bold", 6.5)
    cvs.drawCentredString(0, -3.0 * mm, "#%02d" % card_no)
    cvs.restoreState()


def draw_tri(cvs, x1, y1, x2, y2, x3, y3, clr):
    p = cvs.beginPath()
    p.moveTo(x1, y1)
    p.lineTo(x2, y2)
    p.lineTo(x3, y3)
    p.close()
    cvs.setFillColor(clr)
    cvs.drawPath(p, fill=1, stroke=0)


def draw_card(cvs, ox, oy, card_no, matrix, cidx):
    cell = CELL_MM * mm
    gsz = cell * 5
    bclr = BORDER_COLORS[cidx % len(BORDER_COLORS)]

    cvs.setFillColor(colors.white)
    cvs.setStrokeColor(colors.HexColor("#94a3b8"))
    cvs.setLineWidth(0.4)
    cvs.roundRect(ox, oy, CARD_W, CARD_H, 5, fill=1, stroke=1)

    cvs.setStrokeColor(bclr)
    cvs.setLineWidth(2)
    cvs.roundRect(ox, oy, CARD_W, CARD_H, 5, fill=0, stroke=1)

    grid_x = ox + (CARD_W - gsz) / 2
    grid_y = oy + (CARD_H - gsz) / 2

    for row in range(5):
        for col in range(5):
            val = int(matrix[row][col])
            cx = grid_x + col * cell
            cy = grid_y + (4 - row) * cell
            cvs.setFillColor(colors.black if val else colors.white)
            cvs.rect(cx, cy, cell, cell, fill=1, stroke=0)
            if not val:
                cvs.setStrokeColor(colors.HexColor("#e2e8f0"))
                cvs.setLineWidth(0.2)
                cvs.rect(cx, cy, cell, cell, fill=0, stroke=1)

    cvs.setStrokeColor(colors.black)
    cvs.setLineWidth(2.8)
    cvs.rect(grid_x, grid_y, gsz, gsz, fill=0, stroke=1)

    cx_grid = grid_x + gsz / 2
    cy_grid = grid_y + gsz / 2
    gap = 6.5 * mm
    aw = 2.0 * mm
    ag = 1.8 * mm

    # angle: A=0 (normal), B=-90 (CW), C=180 (flipped), D=90 (CCW)
    badges = [
        ("A", cx_grid, grid_y + gsz + gap, 0),
        ("B", grid_x + gsz + gap, cy_grid, -90),
        ("C", cx_grid, grid_y - gap, 180),
        ("D", grid_x - gap, cy_grid, 90),
    ]
    for letter, lx, ly, angle in badges:
        draw_badge(cvs, lx, ly, angle, letter, card_no, ABCD_CLR[letter])

    # arrows
    ay0 = grid_y + gsz + ag
    draw_tri(cvs, cx_grid, ay0 + 2 * ag, cx_grid - aw, ay0, cx_grid + aw, ay0, ABCD_CLR["A"])
    cy0 = grid_y - ag
    draw_tri(cvs, cx_grid, cy0 - 2 * ag, cx_grid - aw, cy0, cx_grid + aw, cy0, ABCD_CLR["C"])
    bx0 = grid_x + gsz + ag
    draw_tri(cvs, bx0 + 2 * ag, cy_grid, bx0, cy_grid + aw, bx0, cy_grid - aw, ABCD_CLR["B"])
    dx0 = grid_x - ag
    draw_tri(cvs, dx0 - 2 * ag, cy_grid, dx0, cy_grid + aw, dx0, cy_grid - aw, ABCD_CLR["D"])


def build():
    """Build PDF thẻ Plickers từ database matrix."""
    db = _load_database()
    card_list = list(db.keys())
    students = sorted(set(int(cid.split("-")[0]) for cid in card_list))
    os.makedirs(os.path.join(DATA_DIR, "output"), exist_ok=True)
    cvs = canvas.Canvas(OUTPUT, pagesize=A4)
    cvs.setTitle("The Plickers - In cho Hoc Sinh")

    for i, sno in enumerate(students):
        col = i % COLS
        row = (i // COLS) % ROWS
        if i > 0 and i % CARDS_PER_PAGE == 0:
            footer(cvs, i // CARDS_PER_PAGE)
            cvs.showPage()
        if i % CARDS_PER_PAGE == 0:
            header(cvs)

        ox = (MARGIN_MM + col * (card_w_mm + GAP_MM)) * mm
        oy = (PAGE_H_MM - MARGIN_MM - (row + 1) * card_h_mm - row * GAP_MM) * mm

        mat = db.get("%03d-A" % sno)
        if mat is None:
            for s in ["B", "C", "D"]:
                mat = db.get("%03d-%s" % (sno, s))
                if mat is not None:
                    break
        if mat is None:
            continue
        draw_card(cvs, ox, oy, sno, mat, i)

    total_pages = (len(students) - 1) // CARDS_PER_PAGE + 1
    footer(cvs, total_pages)
    cvs.save()
    print("[OK] PDF saved: %s" % OUTPUT)
    print("     Cards: %d | Pages: %d" % (len(students), total_pages))


def header(cvs):
    cvs.setFont("Helvetica-Bold", 11)
    cvs.setFillColor(colors.HexColor("#1e293b"))
    cvs.drawCentredString(A4[0] / 2, A4[1] - 8 * mm, "THE PLICKERS  --  Can lenh nao len tren = chon dap an do")
    cvs.setFont("Helvetica", 8)
    cvs.setFillColor(colors.HexColor("#64748b"))
    cvs.drawCentredString(A4[0] / 2, A4[1] - 12 * mm, "A=len  |  B=phai  |  C=xuong  |  D=trai")


def footer(cvs, page_no):
    cvs.setFont("Helvetica", 7.5)
    cvs.setFillColor(colors.HexColor("#94a3b8"))
    cvs.drawCentredString(A4[0] / 2, 5 * mm, "Trang %d  --  Plickers Classroom Scanner" % page_no)


if __name__ == "__main__":
    try:
        build()
    except FileNotFoundError as e:
        print(f"[LỖI] {e}")
        sys.exit(1)
