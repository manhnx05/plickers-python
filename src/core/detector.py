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

    def get_card_matrix(self, result_img):
        """
        Parses the binary cropped image to 5x5 grid and returns the matrix.
        """
        height, width = result_img.shape
        result_img = cv2.resize(result_img, (10 * width, 10 * height))
        height, width = result_img.shape
        
        card_array = np.zeros([5, 5])
        for y in range(1, 6):
            for x in range(1, 6):
                y_start = int(height * ((y - 1) / 5.0))
                y_end = int(height * (y / 5.0))
                x_start = int(width * ((x - 1) / 5.0))
                x_end = int(width * (x / 5.0))
                
                # Inset by 10% on each side to avoid border noise
                inset_y = int((y_end - y_start) * 0.15)
                inset_x = int((x_end - x_start) * 0.15)
                
                crop = result_img[y_start + inset_y : y_end - inset_y, x_start + inset_x : x_end - inset_x]

                if np.average(crop) > 120:     
                    card_array[y - 1, x - 1] = 0
                else:
                    card_array[y - 1, x - 1] = 1
        return card_array

    def check_card_matrix(self, result_img):
        """
        Parses the binary cropped image to 5x5 grid and matches with the known data.
        Returns the card text ID if found, otherwise None.
        """
        card_array = self.get_card_matrix(result_img)
        for num, i in enumerate(self.card_data):
            if np.array_equal(i, card_array):
                return self.card_list[num]
        return None

    def process_image(self, img):
        """
        Processes an entire BGR image, extracts contours, and attempts to find a valid card.
        Returns card_id if found, else None.
        """
        blur_img = cv2.GaussianBlur(img, (5, 5), 0)
        canny = cv2.Canny(blur_img, 30, 150)
        gray = cv2.cvtColor(blur_img, cv2.COLOR_BGR2GRAY)
        ret_thresh, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        contours, hierarchy = cv2.findContours(canny, 2, 1)

        for cnt in contours:
            if len(cnt) > 50:
                approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
                if len(approx) > 4:
                    card_id = None
                    if cnt[:,0,:].max() - cnt[:,0,:].min() > cnt[:,:,0].max() - cnt[:,:,0].min():
                        diff = cnt[:,:,0].max() - cnt[:,:,0].min()
                        card = thresh[cnt[:,0,:].min():cnt[:,0,:].min()+diff, cnt[:,:,0].min():cnt[:,:,0].max()]
                        if len(card) > 10 and 100 < np.average(card) < 230:
                            card_id = self.check_card_matrix(card)
                        
                        if not card_id:
                            card = thresh[abs(cnt[:,0,:].max()-diff):cnt[:,0,:].max(), cnt[:,:,0].min():cnt[:,:,0].max()]
                            if len(card) > 10 and 100 < np.average(card) < 230:
                                card_id = self.check_card_matrix(card)
                    else:
                        diff = cnt[:,0,:].max() - cnt[:,0,:].min()
                        card = thresh[cnt[:,0,:].min():cnt[:,0,:].max(), cnt[:,:,0].min():cnt[:,:,0].min()+diff]
                        if len(card) > 10 and 100 < np.average(card) < 230:
                            card_id = self.check_card_matrix(card)
                            
                        if not card_id:
                            card = thresh[cnt[:,0,:].min():cnt[:,0,:].max(), cnt[:,:,0].max()-diff:cnt[:,:,0].max()]
                            if len(card) > 10 and 100 < np.average(card) < 230:
                                card_id = self.check_card_matrix(card)
                                
                    if card_id:
                        return card_id, cnt
        return None, None
