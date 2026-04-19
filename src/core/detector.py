import cv2
import numpy as np
import pickle
import os

class PlickersDetector:
    def __init__(self, data_path=None, list_path=None):
        if data_path is None or list_path is None:
            # Base directory is plickers-python
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_path = os.path.join(project_root, 'data', 'database', 'card.data')
            list_path = os.path.join(project_root, 'data', 'database', 'card.list')
            
        try:
            with open(data_path, 'rb') as f:
                self.card_data = pickle.loads(f.read(), encoding='latin1')
            with open(list_path, 'rb') as f:
                self.card_list = pickle.loads(f.read(), encoding='latin1')
        except Exception as e:
            print(f"Warning: Could not load card data database: {e}")
            self.card_data = []
            self.card_list = []

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect
        
    def four_point_transform(self, image, pts):
        rect = self.order_points(pts)
        (tl, tr, br, bl) = rect
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))
        
        maxDim = max(maxWidth, maxHeight)
        if maxDim < 40: return None
        
        dst = np.array([
            [0, 0],
            [249, 0],
            [249, 249],
            [0, 249]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (250, 250))
        return warped

    def get_card_matrix(self, result_img):
        """
        Parses the binary cropped image to 5x5 grid and returns the matrix.
        Expects a flat perfectly warped 250x250 square image.
        """
        if result_img is None or result_img.shape[0] != 250:
            return None
            
        card_array = np.zeros([5, 5])
        # Grid cells are exactly 50x50.
        for y in range(5):
            for x in range(5):
                # Inset 15% (7-8 pixels) to avoid boundary bleed
                inset = 8
                crop = result_img[y*50+inset:(y+1)*50-inset, x*50+inset:(x+1)*50-inset]
                # BGR inverted binary image: black became white(255).
                # Wait, if average is > 127 it means it was mostly black originally -> we assign 0.
                if np.average(crop) > 127:     
                    card_array[y, x] = 0
                else:
                    card_array[y, x] = 1
        return card_array

    def check_card_matrix(self, result_img):
        """
        Parses the binary cropped image to 5x5 grid and matches with the known data.
        Returns the card text ID if found, otherwise None.
        """
        card_array = self.get_card_matrix(result_img)
        if card_array is None: return None
        
        for num, i in enumerate(self.card_data):
            if np.array_equal(i, card_array):
                return self.card_list[num]
        return None

    def proc_single_contour(self, thresh, cnt, approx):
        pts = approx.reshape(4, 2)
        warped = self.four_point_transform(thresh, pts)
        if warped is not None:
            return self.check_card_matrix(warped)
        return None

    def extract_raw_matrix(self, img):
        """
        Pure extraction for database generation. Returns a single raw card matrix.
        """
        blur_img = cv2.GaussianBlur(img, (5, 5), 0)
        canny = cv2.Canny(blur_img, 30, 150)
        gray = cv2.cvtColor(blur_img, cv2.COLOR_BGR2GRAY)
        ret_thresh, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        contours, hierarchy = cv2.findContours(canny, 2, 1)

        for cnt in contours:
            if len(cnt) > 50:
                approx = cv2.approxPolyDP(cnt, 0.05 * cv2.arcLength(cnt, True), True)
                if len(approx) == 4:
                    pts = approx.reshape(4, 2)
                    warped = self.four_point_transform(thresh, pts)
                    if warped is not None:
                        return self.get_card_matrix(warped)
        return None

    def process_image(self, img):
        """
        Processes an entire BGR image, extracts contours, and attempts to find a valid card.
        Uses Perspective Transforms and an adaptive search to handle extreme lighting conditions.
        Returns card_id if found, else None.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive Multi-Pass to maximize recognition under varying lighting
        blur_settings = [3, 5, 7]
        canny_settings = [(30, 150), (10, 100), (50, 200)]
        
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
                    if len(cnt) > 50:
                        approx = cv2.approxPolyDP(cnt, 0.05 * cv2.arcLength(cnt, True), True)
                        if len(approx) == 4:
                            card_id = self.proc_single_contour(thresh, cnt, approx)
                            if card_id:
                                return card_id, cnt
        
        return None, None
