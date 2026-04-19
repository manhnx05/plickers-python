# -*- coding: utf-8 -*-
"""
Test detection with official Plickers cards database.
"""

import os
import sys
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.core.detector import PlickersDetector


def test_official_database():
    """Test with official database."""
    # Load detector with official database
    data_path = os.path.join(PROJECT_ROOT, "data", "database_official", "card.data")
    list_path = os.path.join(PROJECT_ROOT, "data", "database_official", "card.list")

    if not os.path.exists(data_path):
        print("❌ Official database not found. Run extract_from_official_pdf.py first")
        return

    detector = PlickersDetector(data_path=data_path, list_path=list_path)

    print(f"✅ Loaded official database:")
    print(f"   📊 {len(detector.card_data)} matrices")
    print(f"   🎴 {len(detector.card_list)} card IDs")
    print(f"   📋 Sample IDs: {detector.card_list[:8]}")

    # Test on extracted cards
    extracted_dir = os.path.join(PROJECT_ROOT, "data", "extracted_cards")

    if not os.path.exists(extracted_dir):
        print("\n❌ No extracted cards found")
        return

    card_files = sorted([f for f in os.listdir(extracted_dir) if f.endswith(".png")])

    print(f"\n🧪 Testing on {len(card_files)} extracted cards...")
    print("=" * 60)

    success_count = 0
    for card_file in card_files:
        img_path = os.path.join(extracted_dir, card_file)
        img = cv2.imread(img_path)

        if img is None:
            continue

        # Detect
        found = detector.process_image(img)

        if found:
            card_ids = [card_id for card_id, _ in found]
            print(f"✅ {card_file:20} → {card_ids}")
            success_count += 1
        else:
            print(f"❌ {card_file:20} → NOT DETECTED")

    print("=" * 60)
    print(f"📊 Kết quả: {success_count}/{len(card_files)} thẻ nhận diện thành công")
    print(f"   Tỷ lệ: {success_count/len(card_files)*100:.1f}%")


if __name__ == "__main__":
    test_official_database()
