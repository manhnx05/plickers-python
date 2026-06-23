"""
Plickers Card Detector Module
Provides computer vision-based detection and recognition of Plickers cards.
"""

import cv2
import numpy as np
import os
from typing import List, Tuple, Optional
import logging
import sys

# Add project root to path to import config
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.config import (
    GRID_SIZE,
    CELL_INSET_RATIO,
    BRIGHTNESS_THRESHOLD,
    MIN_CONTOUR_POINTS,
    MIN_APPROX_POINTS,
    MIN_CARD_SIZE,
    MIN_AVG_BRIGHTNESS,
    MAX_AVG_BRIGHTNESS,
    BLUR_SETTINGS,
    CANNY_SETTINGS,
)
from src.core.db import load_all_cards

logger = logging.getLogger(__name__)


class PlickersDetector:
    def __init__(self) -> None:
        """
        Initialize Plickers detector with card database from SQLite.
        """
        try:
            self.card_data, self.card_list = load_all_cards()
            logger.info(f"Loaded {len(self.card_data)} card matrices from SQLite database")
        except Exception as e:
            logger.warning(f"Could not load card data from database: {e}")
            self.card_data = []
            self.card_list = []

    def get_card_matrix(self, result_img: np.ndarray) -> np.ndarray:
        """
        Parse binary cropped image to 5x5 grid matrix.

        Args:
            result_img: Binary image of the card

        Returns:
            5x5 numpy array representing the card pattern
        """
        height, width = result_img.shape
        result_img = cv2.resize(result_img, (10 * width, 10 * height))
        height, width = result_img.shape

        card_array = np.zeros([GRID_SIZE, GRID_SIZE])
        for y in range(1, GRID_SIZE + 1):
            for x in range(1, GRID_SIZE + 1):
                y_start = int(height * ((y - 1) / float(GRID_SIZE)))
                y_end = int(height * (y / float(GRID_SIZE)))
                x_start = int(width * ((x - 1) / float(GRID_SIZE)))
                x_end = int(width * (x / float(GRID_SIZE)))

                # Inset by percentage on each side to avoid border noise
                inset_y = int((y_end - y_start) * CELL_INSET_RATIO)
                inset_x = int((x_end - x_start) * CELL_INSET_RATIO)

                crop = result_img[y_start + inset_y : y_end - inset_y, x_start + inset_x : x_end - inset_x]

                if np.average(crop) > BRIGHTNESS_THRESHOLD:
                    card_array[y - 1, x - 1] = 0
                else:
                    card_array[y - 1, x - 1] = 1
        return card_array

    def check_card_matrix(self, result_img: np.ndarray) -> Optional[str]:
        """
        Parse binary cropped image and match with known card database.

        Args:
            result_img: Binary image of the card

        Returns:
            Card text ID if found, None otherwise
        """
        card_array = self.get_card_matrix(result_img)
        for num, i in enumerate(self.card_data):
            if np.array_equal(i, card_array):
                return self.card_list[num]
        return None

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        Order contour points: top-left, top-right, bottom-right, bottom-left
        """
        rect = np.zeros((4, 2), dtype="float32")
        
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left (smallest sum)
        rect[2] = pts[np.argmax(s)]  # bottom-right (largest sum)
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right (smallest diff)
        rect[3] = pts[np.argmax(diff)]  # bottom-left (largest diff)
        
        return rect

    def _four_point_transform(self, image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """
        Apply perspective transform to get a top-down view of the card
        """
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect

        # Compute width of new image
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))

        # Compute height of new image
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))

        # Destination points
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        # Compute perspective transform matrix and apply it
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        
        return warped

    def _enhance_image(self, gray: np.ndarray) -> np.ndarray:
        """
        Enhance image quality using CLAHE and normalization
        """
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return enhanced

    def process_image(self, img: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """
        Process entire BGR image and extract valid Plickers cards.
        Uses adaptive multi-pass detection to handle varying lighting conditions.

        Args:
            img: BGR image from camera or file

        Returns:
            List of tuples: [(card_id, contour), ...]
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        enhanced_gray = self._enhance_image(gray)

        found_cards = {}

        for b_val in BLUR_SETTINGS:
            blur_img = cv2.GaussianBlur(img, (b_val, b_val), 0)

            for c_thresh in CANNY_SETTINGS:
                canny = cv2.Canny(blur_img, c_thresh[0], c_thresh[1])

                # Morphological closing to seal broken edges caused by glare/shadows
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                canny = cv2.morphologyEx(canny, cv2.MORPH_CLOSE, kernel)

                # Try multiple thresholding methods
                # 1. Original Otsu on plain gray
                ret_otsu, thresh_original = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                # 2. Otsu on enhanced gray
                ret_otsu_enhanced, thresh_otsu_enhanced = cv2.threshold(enhanced_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                # 3. Adaptive threshold on enhanced gray
                thresh_adaptive = cv2.adaptiveThreshold(
                    enhanced_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
                )

                contours, _ = cv2.findContours(canny, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    if len(cnt) > MIN_CONTOUR_POINTS:
                        approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
                        if len(approx) > MIN_APPROX_POINTS:
                            # Try all thresholding methods
                            card_id = self._extract_card_from_contour(cnt, thresh_original)
                            if not card_id:
                                card_id = self._extract_card_from_contour(cnt, thresh_otsu_enhanced)
                            if not card_id:
                                card_id = self._extract_card_from_contour(cnt, thresh_adaptive)
                            
                            if card_id:
                                # Deduplicate by tracking the contour area
                                area = cv2.contourArea(cnt)
                                if card_id not in found_cards or cv2.contourArea(found_cards[card_id]) < area:
                                    found_cards[card_id] = cnt
            
            # Early stopping: if we already found cards, no need for further passes
            if found_cards:
                break

        return list(found_cards.items())

    def _extract_card_from_contour(self, cnt: np.ndarray, thresh: np.ndarray) -> Optional[str]:
        """
        Extract and identify card from contour. First tries perspective transform,
        then falls back to original method if needed.

        Args:
            cnt: Contour array
            thresh: Thresholded image

        Returns:
            Card ID if found, None otherwise
        """
        card_id = None
        
        # First try perspective transform (for real-world cards)
        try:
            # Approximate contour to check if it's a quadrilateral
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            if len(approx) == 4:
                # Reshape contour for perspective transform
                pts = approx.reshape(4, 2).astype("float32")
                
                # Apply perspective transform to get top-down view
                warped = self._four_point_transform(thresh, pts)
                
                # Check size and brightness
                if (warped.shape[0] > MIN_CARD_SIZE and 
                    warped.shape[1] > MIN_CARD_SIZE and
                    MIN_AVG_BRIGHTNESS < np.average(warped) < MAX_AVG_BRIGHTNESS):
                    
                    # Try all 4 rotations (0°, 90°, 180°, 270°) to match database
                    for k in range(4):
                        rotated = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE * k)
                        card_id = self.check_card_matrix(rotated)
                        if card_id:
                            break
        except Exception:
            pass
        
        # If perspective transform didn't work, fall back to original method (for sample images)
        if not card_id:
            # Original boundary extraction logic matched against DB generator
            if cnt[:, 0, :].max() - cnt[:, 0, :].min() > cnt[:, :, 0].max() - cnt[:, :, 0].min():
                diff = cnt[:, :, 0].max() - cnt[:, :, 0].min()
                card = thresh[cnt[:, 0, :].min() : cnt[:, 0, :].min() + diff, cnt[:, :, 0].min() : cnt[:, :, 0].max()]
                if len(card) > MIN_CARD_SIZE and MIN_AVG_BRIGHTNESS < np.average(card) < MAX_AVG_BRIGHTNESS:
                    card_id = self.check_card_matrix(card)

                if not card_id:
                    card = thresh[
                        abs(cnt[:, 0, :].max() - diff) : cnt[:, 0, :].max(), cnt[:, :, 0].min() : cnt[:, :, 0].max()]
                    if (
                        len(card) > MIN_CARD_SIZE
                        and MIN_AVG_BRIGHTNESS < np.average(card) < MAX_AVG_BRIGHTNESS
                    ):
                        card_id = self.check_card_matrix(card)
            else:
                diff = cnt[:, 0, :].max() - cnt[:, 0, :].min()
                card = thresh[cnt[:, 0, :].min() : cnt[:, 0, :].max(), cnt[:, :, 0].min() : cnt[:, :, 0].min() + diff]
                if len(card) > MIN_CARD_SIZE and MIN_AVG_BRIGHTNESS < np.average(card) < MAX_AVG_BRIGHTNESS:
                    card_id = self.check_card_matrix(card)

                if not card_id:
                    card = thresh[cnt[:, 0, :].min() : cnt[:, 0, :].max(), cnt[:, :, 0].max() - diff : cnt[:, :, 0].max()]
                    if (
                        len(card) > MIN_CARD_SIZE
                        and MIN_AVG_BRIGHTNESS < np.average(card) < MAX_AVG_BRIGHTNESS
                    ):
                        card_id = self.check_card_matrix(card)
                        
        return card_id
