# -*- coding: utf-8 -*-
"""
Test detection with final official database.
"""

import os
import sys
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.core.detector import PlickersDetector


def test_final_database():
    """Test with final official database."""
    data_path = os.path.join(PROJECT_ROOT, "data", "database_official_final", "card.data")
    list_path = os.path.join(PROJECT_ROOT, "data", "database_official_final", "card.list")

    if not os.path.exists(data_path):
        print("❌ Database not found. Run extract_by_position.py first")
        return

    detector = PlickersDetector(data_path=data_path, list_path=list_path)

    print(f"✅ Loaded official database:")
    print(f"   📊 {len(detector.card_data)} matrices")
    print(f"   🎴 {len(detector.card_list)} IDs")
    print(f"   📋 Sample: {detector.card_list[:8]}")

    # Test on extracted cards
    extracted_dir = os.path.join(PROJECT_ROOT, "data", "extracted_cards_final")

    if not os.path.exists(extracted_dir):
        print("\n❌ No extracted cards")
        return

    card_files = sorted([f for f in os.listdir(extracted_dir) if f.endswith(".png")])

    print(f"\n🧪 Testing {len(card_files)} cards...")
    print("=" * 70)

    success = 0
    for card_file in card_files:
        img_path = os.path.join(extracted_dir, card_file)
        img = cv2.imread(img_path)

        if img is None:
            continue

        # Detect
        found = detector.process_image(img)

        expected_num = card_file.replace("card_", "").replace(".png", "")

        if found:
            card_ids = [card_id for card_id, _ in found]
            # Check if any detected ID matches expected card number
            matches = [cid for cid in card_ids if cid.startswith(expected_num)]

            if matches:
                print(f"✅ {card_file:20} → {matches[0]:10} (detected: {len(card_ids)})")
                success += 1
            else:
                print(f"⚠️  {card_file:20} → {card_ids[0]:10} (expected {expected_num}-X)")
        else:
            print(f"❌ {card_file:20} → NOT DETECTED")

    print("=" * 70)
    accuracy = success / len(card_files) * 100 if card_files else 0
    print(f"📊 Kết quả: {success}/{len(card_files)} ({accuracy:.1f}%)")

    if accuracy >= 90:
        print("🎉 EXCELLENT! Detection rate >= 90%")
    elif accuracy >= 70:
        print("✅ GOOD! Detection rate >= 70%")
    else:
        print("⚠️  Cần cải thiện thêm")


if __name__ == "__main__":
    test_final_database()
