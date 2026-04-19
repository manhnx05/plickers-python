"""
Tạo PDF thẻ Plickers chuẩn để in cho học sinh.
- Mỗi thẻ có mã 5x5 thực lấy từ database, có thể xoay 4 hướng → 4 đáp án
- Định dạng y hệt Plickers: ô đen/trắng + nhãn ABCD 4 cạnh + số thẻ
- Layout: 2 cột × 3 hàng = 6 thẻ/trang A4
"""
import os
import sys
import pickle

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR  = os.path.join(PROJECT_ROOT, 'data')
DB_DATA   = os.path.join(DATA_DIR, 'database', 'card.data')
DB_LIST   = os.path.join(DATA_DIR, 'database', 'card.list')
OUTPUT    = os.path.join(DATA_DIR, 'output', 'plickers_cards_print.pdf')

# ── Load DB ──────────────────────────────────────────────────────────────────
with open(DB_DATA, 'rb') as f:
    card_data = pickle.load(f)
with open(DB_LIST, 'rb') as f:
    card_list = pickle.load(f)

# Build lookup: "001-A" → 5×5 matrix
db = {}
for mat, cid in zip(card_data, card_list):
    db[cid] = mat

# ── Layout constants (all in mm, will be converted to points) ────────────────
PAGE_W_MM,  PAGE_H_MM  = 210, 297        # A4
MARGIN_MM   = 12
GAP_MM      = 8                          # gap between cards
COLS, ROWS  = 2, 3
CARDS_PER_PAGE = COLS * ROWS

card_w_mm = (PAGE_W_MM - 2*MARGIN_MM - (COLS-1)*GAP_MM) / COLS   # ≈ 85mm
card_h_mm = (PAGE_H_MM - 2*MARGIN_MM - (ROWS-1)*GAP_MM) / ROWS   # ≈ 85mm
CARD_W = card_w_mm * mm
CARD_H = card_h_mm * mm

BORDER_MM   = 1.5       # outer card border
HEADER_MM   = 11        # top header strip height
ABCD_ZONE   = 9         # mm on each side reserved for ABCD label
GRID_MM = min(card_w_mm, card_h_mm) - 2 * ABCD_ZONE - 2 - HEADER_MM / 2
CELL_MM = GRID_MM / 5

# ── Colors ───────────────────────────────────────────────────────────────────
HDR_COLORS = [
    colors.HexColor('#1e3a5f'),   # deep blue
    colors.HexColor('#1a3d2b'),   # deep green
    colors.HexColor('#4a1942'),   # deep purple
    colors.HexColor('#5c2800'),   # deep brown
    colors.HexColor('#1c3a4a'),   # teal
    colors.HexColor('#3d2014'),   # dark earth
]
ABCD_CLR = {
    'A': colors.HexColor('#ef4444'),
    'B': colors.HexColor('#3b82f6'),
    'C': colors.HexColor('#22c55e'),
    'D': colors.HexColor('#f59e0b'),
}


# ── Draw one card ─────────────────────────────────────────────────────────────
def draw_card(cvs: canvas.Canvas, ox, oy, card_no: int, matrix, color_idx: int):
    """
    ox, oy = bottom-left of card cell (in points)
    matrix = 5x5 numpy array (1=black, 0=white)
    """
    hdr_h  = HEADER_MM * mm
    az     = ABCD_ZONE * mm        # ABCD zone width on each side
    cell   = CELL_MM * mm
    gsz    = cell * 5              # total grid size

    # ── Card background ──────────────────────────────────────────────────────
    cvs.setFillColor(colors.white)
    cvs.setStrokeColor(colors.HexColor('#94a3b8'))
    cvs.setLineWidth(0.5)
    cvs.roundRect(ox, oy, CARD_W, CARD_H, 4, fill=1, stroke=1)

    # ── Header strip ─────────────────────────────────────────────────────────
    hdr_clr = HDR_COLORS[color_idx % len(HDR_COLORS)]
    cvs.setFillColor(hdr_clr)
    cvs.roundRect(ox, oy + CARD_H - hdr_h, CARD_W, hdr_h, 4, fill=1, stroke=0)
    # Mask bottom corners of header (make them square against card body)
    cvs.setFillColor(hdr_clr)
    cvs.rect(ox, oy + CARD_H - hdr_h, CARD_W, hdr_h/2, fill=1, stroke=0)

    cvs.setFillColor(colors.white)
    cvs.setFont('Helvetica-Bold', 10)
    cvs.drawCentredString(ox + CARD_W/2, oy + CARD_H - hdr_h + 3*mm,
                          f'HOC SINH  #{card_no:02d}')

    # ── Grid position: centered horizontally, centered vertically in body ────
    body_h = CARD_H - hdr_h
    grid_x = ox + (CARD_W - gsz) / 2
    grid_y = oy + (body_h - gsz) / 2

    # ── Draw 5×5 pattern cells ───────────────────────────────────────────────
    for row in range(5):
        for col in range(5):
            val  = int(matrix[row][col])
            cx   = grid_x + col * cell
            cy   = grid_y + (4 - row) * cell   # reportlab Y is bottom-up

            # Cell fill
            cvs.setFillColor(colors.black if val else colors.white)
            cvs.rect(cx, cy, cell, cell, fill=1, stroke=0)

            # Thin grid line (visible only on white cells)
            if not val:
                cvs.setStrokeColor(colors.HexColor('#cbd5e1'))
                cvs.setLineWidth(0.25)
                cvs.rect(cx, cy, cell, cell, fill=0, stroke=1)

    # ── Grid thick outer border ───────────────────────────────────────────────
    cvs.setStrokeColor(colors.black)
    cvs.setLineWidth(2.5)
    cvs.rect(grid_x, grid_y, gsz, gsz, fill=0, stroke=1)

    # ── ABCD Labels on 4 sides ───────────────────────────────────────────────
    #  A = top edge (pointing up)
    #  B = right edge (pointing right)
    #  C = bottom edge (pointing down)
    #  D = left edge (pointing left)

    def label(letter, lx, ly, align='center'):
        clr  = ABCD_CLR[letter]
        fs   = 13
        # Circle background
        r = 5.5 * mm
        cvs.setFillColor(clr)
        cvs.circle(lx, ly, r, fill=1, stroke=0)
        cvs.setFillColor(colors.white)
        cvs.setFont('Helvetica-Bold', fs)
        cvs.drawCentredString(lx, ly - fs/2.5, letter)

    gap = 6 * mm
    cx = grid_x + gsz / 2
    cy_center = grid_y + gsz / 2

    label('A', cx,              grid_y + gsz + gap)          # top
    label('C', cx,              grid_y - gap)                 # bottom
    label('B', grid_x + gsz + gap,  cy_center)               # right
    label('D', grid_x - gap,        cy_center)               # left

    # Small directional arrows between circle and grid edge
    arrow_clr = colors.HexColor('#64748b')
    cvs.setStrokeColor(arrow_clr)
    cvs.setLineWidth(0.8)
    aw = 3 * mm  # arrow half-width

    def tri(x1, y1, x2, y2, x3, y3, clr):
        p = cvs.beginPath()
        p.moveTo(x1, y1)
        p.lineTo(x2, y2)
        p.lineTo(x3, y3)
        p.close()
        cvs.setFillColor(clr)
        cvs.drawPath(p, fill=1, stroke=0)

    midgap = gap * 0.4
    # ↑ A arrow
    tri(cx, grid_y + gsz + midgap*1.6,
        cx - aw, grid_y + gsz + midgap*0.5,
        cx + aw, grid_y + gsz + midgap*0.5,
        ABCD_CLR['A'])
    # ↓ C arrow
    tri(cx, grid_y - midgap*1.6,
        cx - aw, grid_y - midgap*0.5,
        cx + aw, grid_y - midgap*0.5,
        ABCD_CLR['C'])
    # → B arrow
    tri(grid_x + gsz + midgap*1.6, cy_center,
        grid_x + gsz + midgap*0.5, cy_center + aw,
        grid_x + gsz + midgap*0.5, cy_center - aw,
        ABCD_CLR['B'])
    # ← D arrow
    tri(grid_x - midgap*1.6, cy_center,
        grid_x - midgap*0.5, cy_center + aw,
        grid_x - midgap*0.5, cy_center - aw,
        ABCD_CLR['D'])

    # ── Bottom caption ───────────────────────────────────────────────────────
    cvs.setFont('Helvetica', 6.5)
    cvs.setFillColor(colors.HexColor('#94a3b8'))
    cvs.drawCentredString(ox + CARD_W/2, oy + 2*mm,
                          'Gioi thieu huong dap an len tren dau')


# ── Build PDF ─────────────────────────────────────────────────────────────────
def build():
    # Only take the "A" orientation matrix for each student number
    # This is the canonical form; the same physical card rotated gives B/C/D
    students = sorted(set(int(cid.split('-')[0]) for cid in card_list))

    os.makedirs(os.path.join(DATA_DIR, 'output'), exist_ok=True)
    cvs = canvas.Canvas(OUTPUT, pagesize=A4)
    cvs.setTitle('The Plickers - In cho Hoc Sinh')
    cvs.setAuthor('Plickers Python')

    for i, sno in enumerate(students):
        col  = i % COLS
        row  = (i // COLS) % ROWS

        # New page
        if i > 0 and i % CARDS_PER_PAGE == 0:
            _draw_page_footer(cvs, i // CARDS_PER_PAGE)
            cvs.showPage()

        # Page header (first card on page)
        if i % CARDS_PER_PAGE == 0:
            _draw_page_header(cvs)

        # Card origin (bottom-left)
        ox = (MARGIN_MM + col * (card_w_mm + GAP_MM)) * mm
        oy = (PAGE_H_MM - MARGIN_MM - (row + 1) * card_h_mm - row * GAP_MM) * mm

        # Get canonical matrix for this student (use "A" orientation)
        cid_a = f'{sno:03d}-A'
        mat   = db.get(cid_a)
        if mat is None:
            # Fallback to any orientation we have
            for suf in ['B', 'C', 'D']:
                mat = db.get(f'{sno:03d}-{suf}')
                if mat is not None:
                    break
        if mat is None:
            continue

        draw_card(cvs, ox, oy, sno, mat, i)

    total_pages = (len(students) - 1) // CARDS_PER_PAGE + 1
    _draw_page_footer(cvs, total_pages)
    cvs.save()

    print(f'[OK] PDF saved: {OUTPUT}')
    print(f'     Cards: {len(students)} | Pages: {total_pages}')


def _draw_page_header(cvs):
    cvs.setFont('Helvetica-Bold', 11)
    cvs.setFillColor(colors.HexColor('#1e293b'))
    cvs.drawCentredString(A4[0]/2, A4[1] - 8*mm,
                          'THE PLICKERS  -  Giu huong dap an len tren dau the')
    cvs.setFont('Helvetica', 8)
    cvs.setFillColor(colors.HexColor('#64748b'))
    cvs.drawCentredString(A4[0]/2, A4[1] - 11.5*mm,
                          'A=len  B=phai  C=xuong  D=trai')


def _draw_page_footer(cvs, page_no):
    cvs.setFont('Helvetica', 7.5)
    cvs.setFillColor(colors.HexColor('#94a3b8'))
    cvs.drawCentredString(A4[0]/2, 5*mm,
                          f'Trang {page_no}  -  Plickers Classroom Scanner')


if __name__ == '__main__':
    build()
