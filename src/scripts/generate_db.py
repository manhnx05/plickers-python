"""
Script to create SQLite database from Plickers sample images.
Reads all images in data/samples/, extracts 5x5 matrices and saves to
data/database/plickers.db.

Run with: python src/scripts/generate_db.py
"""

import cv2
import numpy as np
import os
import sys

# ─── Path setup ───────────────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.detector import PlickersDetector
from src.core.db import init_db, clear_cards, save_card


# ─── Core function ────────────────────────────────────────────────────────────
def cv_card_read(img, detector: PlickersDetector) -> np.ndarray | None:
    """
    Read Plickers card image, return 5x5 matrix if detected.
    Return None if no valid contour found.
    """
    dst = cv2.blur(img, (3, 3))
    gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 127, 255, 1)
    contours, _ = cv2.findContours(thresh, 2, 1)

    for cnt in contours:
        if len(cnt) > 500:
            approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
            if len(approx) > 11:
                card = gray[cnt[:, 0, :].min() : cnt[:, 0, :].max(), cnt[:, :, 0].min() : cnt[:, :, 0].max()]
                _, result = cv2.threshold(card, 90, 255, 1)
                return detector.get_card_matrix(result)
    return None


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Initialize Flask app and database
    print("[1/4] Initializing SQLite database...")
    from src.web.app_web import app
    with app.app_context():
        init_db(app)
        
        # Clear existing cards
        print("[2/4] Clearing existing cards...")
        clear_cards()
        
        detector = PlickersDetector()
        img_dir = os.path.join(project_root, "data", "samples")

        file_list = [f for f in os.listdir(img_dir) if f.endswith(".jpg")]
        if not file_list:
            print(f"[WARNING] No images found in: {img_dir}")
            sys.exit(1)

        total_cards = 0
        skipped = 0

        print("[3/4] Processing sample images...")
        for file in sorted(file_list):
            img = cv2.imread(os.path.join(img_dir, file))
            if img is None:
                print(f"[WARNING] Cannot read image: {file}")
                skipped += 1
                continue

            file_name = file.split(".")[0]
            try:
                file_num, option = file_name.split("-")
                card_number = int(file_num)
            except ValueError:
                print(f"[WARNING] Invalid filename format '###-X.jpg': {file}")
                skipped += 1
                continue

            card_array = cv_card_read(img, detector)
            if card_array is None:
                print(f"[FAILED] Cannot read card: {file}")
                skipped += 1
                continue

            print(f"[OK] File {file_num} — Orientation {option}")

            # Generate all 4 rotations from original orientation
            rotations = {"A": 0, "B": 3, "C": 2, "D": 1}
            base_rot = {"A": 0, "B": 1, "C": 2, "D": 3}
            offset = base_rot[option]

            # Generate all 4 rotations and save to DB
            options = ["A", "B", "C", "D"]
            for r, opt in enumerate(options):
                rotated_matrix = np.rot90(card_array, (r - offset) % 4)
                card_id = f"{file_num}-{opt}"
                save_card(card_id, card_number, opt, rotated_matrix)
                total_cards += 1

        # Verify
        print("[4/4] Verifying database...")
        from src.core.db import load_all_cards
        card_data, card_list = load_all_cards()
        
        total = len(file_list) - skipped
        print(f"\n[SUCCESS] Done!")
        print(f"   Processed {total}/{len(file_list)} images")
        print(f"   Saved {total_cards} entries to SQLite database")
        print(f"   Database path: {os.path.join(project_root, 'data', 'database', 'plickers.db')}")
        sys.exit(0)

    file_list = [f for f in os.listdir(img_dir) if f.endswith(".jpg")]
    if not file_list:
        print(f"[WARNING] No images found in: {img_dir}")
        sys.exit(1)

    total_cards = 0
    skipped = 0

    print("[3/4] Processing sample images...")
    for file in sorted(file_list):
        img = cv2.imread(os.path.join(img_dir, file))
        if img is None:
            print(f"[WARNING] Cannot read image: {file}")
            skipped += 1
            continue

        file_name = file.split(".")[0]
        try:
            file_num, option = file_name.split("-")
            card_number = int(file_num)
        except ValueError:
            print(f"[WARNING] Invalid filename format '###-X.jpg': {file}")
            skipped += 1
            continue

        card_array = cv_card_read(img, detector)
        if card_array is None:
            print(f"[FAILED] Cannot read card: {file}")
            skipped += 1
            continue

        print(f"[OK] File {file_num} — Orientation {option}")

        # Generate all 4 rotations from original orientation
        rotations = {"A": 0, "B": 3, "C": 2, "D": 1}
        base_rot = {"A": 0, "B": 1, "C": 2, "D": 3}
        offset = base_rot[option]

        # Generate all 4 rotations and save to DB
        options = ["A", "B", "C", "D"]
        for r, opt in enumerate(options):
            rotated_matrix = np.rot90(card_array, (r - offset) % 4)
            card_id = f"{file_num}-{opt}"
            save_card(card_id, card_number, opt, rotated_matrix)
            total_cards += 1

    # Verify
    print("[4/4] Verifying database...")
    from src.core.db import load_all_cards
    card_data, card_list = load_all_cards()
    
    total = len(file_list) - skipped
    print(f"\n[SUCCESS] Done!")
    print(f"   Processed {total}/{len(file_list)} images")
    print(f"   Saved {total_cards} entries to SQLite database")
    print(f"   Database path: {os.path.join(project_root, 'data', 'database', 'plickers.db')}")
