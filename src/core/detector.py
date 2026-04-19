"""
Plickers Card Detector Module
Provides computer vision-based detection and recognition of Plickers cards.
"""

import cv2
import numpy as np
import pickle
import os
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PlickersDetector:
    def __init__(self, data_path: Optional[str] = None, list_path: Optional[str] = None) -> None:
        """
        Initialize Plickers detector with card database.

        Args:
            data_path: Path to card.data file (optional)
            list_path: Path to card.list file (optional)
        """
        if data_path is None or list_path is None:
            # Base directory is plickers-python
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_path = os.path.join(project_root, "data", "database", "card.data")
            list_path = os.path.join(project_root, "data", "database", "card.list")

        try:
            with open(data_path, "rb") as f:
                self.card_data = pickle.loads(f.read(), encoding="latin1")
            with open(list_path, "rb") as f:
                self.card_list = pickle.loads(f.read(), encoding="latin1")
            logger.info(f"Loaded {len(self.card_data)} card matrices from database")
        except Exception as e:
            logger.warning(f"Could not load card data database: {e}")
            self.card_data = []
            self.card_list = []

    # Detection constants
    GRID_SIZE = 5
    CELL_INSET_RATIO = 0.15
    BRIGHTNESS_THRESHOLD = 120
    MIN_CONTOUR_POINTS = 50
    MIN_APPROX_POINTS = 4
    MIN_CARD_SIZE = 10
    MIN_AVG_BRIGHTNESS = 100
    MAX_AVG_BRIGHTNESS = 230

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

        card_array = np.zeros([self.GRID_SIZE, self.GRID_SIZE])
        for y in range(1, self.GRID_SIZE + 1):
            for x in range(1, self.GRID_SIZE + 1):
                y_start = int(height * ((y - 1) / float(self.GRID_SIZE)))
                y_end = int(height * (y / float(self.GRID_SIZE)))
                x_start = int(width * ((x - 1) / float(self.GRID_SIZE)))
                x_end = int(width * (x / float(self.GRID_SIZE)))

                # Inset by percentage on each side to avoid border noise
                inset_y = int((y_end - y_start) * self.CELL_INSET_RATIO)
                inset_x = int((x_end - x_start) * self.CELL_INSET_RATIO)

                crop = result_img[y_start + inset_y : y_end - inset_y, x_start + inset_x : x_end - inset_x]

                if np.average(crop) > self.BRIGHTNESS_THRESHOLD:
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

        # Adaptive Multi-Pass to maximize recognition under varying lighting
        blur_settings = [3, 5, 7]
        canny_settings = [(30, 150), (10, 100), (50, 200)]

        found_cards = {}

        for b_val in blur_settings:
            blur_img = cv2.GaussianBlur(img, (b_val, b_val), 0)

            for c_thresh in canny_settings:
                canny = cv2.Canny(blur_img, c_thresh[0], c_thresh[1])

                # Morphological closing to seal broken edges caused by glare/shadows
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                canny = cv2.morphologyEx(canny, cv2.MORPH_CLOSE, kernel)

                ret_thresh, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

                contours, hierarchy = cv2.findContours(canny, 2, 1)

                for cnt in contours:
                    if len(cnt) > self.MIN_CONTOUR_POINTS:
                        approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
                        if len(approx) > self.MIN_APPROX_POINTS:
                            card_id = self._extract_card_from_contour(cnt, thresh)

                            if card_id:
                                # Deduplicate by tracking the contour area
                                area = cv2.contourArea(cnt)
                                if card_id not in found_cards or cv2.contourArea(found_cards[card_id]) < area:
                                    found_cards[card_id] = cnt

        return list(found_cards.items())

    def _extract_card_from_contour(self, cnt: np.ndarray, thresh: np.ndarray) -> Optional[str]:
        """
        Extract and identify card from contour.

        Args:
            cnt: Contour array
            thresh: Thresholded image

        Returns:
            Card ID if found, None otherwise
        """
        card_id = None

        # Original boundary extraction logic matched against DB generator
        if cnt[:, 0, :].max() - cnt[:, 0, :].min() > cnt[:, :, 0].max() - cnt[:, :, 0].min():
            diff = cnt[:, :, 0].max() - cnt[:, :, 0].min()
            card = thresh[cnt[:, 0, :].min() : cnt[:, 0, :].min() + diff, cnt[:, :, 0].min() : cnt[:, :, 0].max()]
            if len(card) > self.MIN_CARD_SIZE and self.MIN_AVG_BRIGHTNESS < np.average(card) < self.MAX_AVG_BRIGHTNESS:
                card_id = self.check_card_matrix(card)

            if not card_id:
                card = thresh[
                    abs(cnt[:, 0, :].max() - diff) : cnt[:, 0, :].max(), cnt[:, :, 0].min() : cnt[:, :, 0].max()
                ]
                if (
                    len(card) > self.MIN_CARD_SIZE
                    and self.MIN_AVG_BRIGHTNESS < np.average(card) < self.MAX_AVG_BRIGHTNESS
                ):
                    card_id = self.check_card_matrix(card)
        else:
            diff = cnt[:, 0, :].max() - cnt[:, 0, :].min()
            card = thresh[cnt[:, 0, :].min() : cnt[:, 0, :].max(), cnt[:, :, 0].min() : cnt[:, :, 0].min() + diff]
            if len(card) > self.MIN_CARD_SIZE and self.MIN_AVG_BRIGHTNESS < np.average(card) < self.MAX_AVG_BRIGHTNESS:
                card_id = self.check_card_matrix(card)

            if not card_id:
                card = thresh[cnt[:, 0, :].min() : cnt[:, 0, :].max(), cnt[:, :, 0].max() - diff : cnt[:, :, 0].max()]
                if (
                    len(card) > self.MIN_CARD_SIZE
                    and self.MIN_AVG_BRIGHTNESS < np.average(card) < self.MAX_AVG_BRIGHTNESS
                ):
                    card_id = self.check_card_matrix(card)

        return card_id
