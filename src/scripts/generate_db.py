import cv2
import numpy as np
import os
import sys
import pickle

# Ensure Python can load modules from the src folder
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# It used 'my_math.py' originally, now it's src.core.utils
from src.core.utils import Math
from src.core.detector import PlickersDetector

detector = PlickersDetector()

def cv_card_read(img):
    dst = cv2.blur(img,(3,3))
    gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    np.set_printoptions(threshold=sys.maxsize)

    ret, thresh = cv2.threshold(gray, 127, 255, 1)
    contours, h = cv2.findContours(thresh,2,1)
    for cnt in contours:
        if len(cnt) >500:
            approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
            if len(approx) > 11:
                card=gray[cnt[:,0,:].min():cnt[:,0,:].max(),cnt[:,:,0].min():cnt[:,:,0].max()]
                # Using THRESH_BINARY_INV (1) so that we can reuse get_card_matrix logic which expects inverted colors
                retval, result = cv2.threshold(card, 90, 255, 1)
                return detector.get_card_matrix(result)
    return None

if __name__ == '__main__':
    img_dir = os.path.join(project_root, 'data', 'samples')
    file_list = os.listdir(img_dir)
    card_data=[]
    card_list=[]
    for file in file_list:
        if not file.endswith('.jpg'): continue
        img = cv2.imread(os.path.join(img_dir, file))
        file_name=file.split('.')[0]
        file_num,option=file_name.split('-')

        card_array=cv_card_read(img)
        if card_array is None:
            print(f"Khong the doc the tu file {file}")
            continue

        print('file',file_num,option)
        # print(card_array)
        if option=='A':
            A=card_array
            B=np.rot90(card_array,1)
            C=np.rot90(card_array,2)
            D=np.rot90(card_array,3)
        elif option=='B':
            A=np.rot90(card_array,3)
            B=card_array
            C=np.rot90(card_array,1)
            D=np.rot90(card_array,2)
        elif option=='C':
            C=card_array
            D=np.rot90(card_array,1)
            A=np.rot90(card_array,2)
            B=np.rot90(card_array,3)
        else:
            D=card_array
            A=np.rot90(card_array,1)
            B=np.rot90(card_array,2)
            C=np.rot90(card_array,3)
        card_data.extend(i for i in [A,B,C,D])
        card_list.extend(file_num+'-'+i for i in ['A','B','C','D'])
        del img,file_name,file_num,option,card_array
        
    fn = os.path.join(project_root, 'data', 'database', 'card.data')
    with open(fn, 'wb') as f:
        pickle.dump(card_data, f)

    fl = os.path.join(project_root, 'data', 'database', 'card.list')
    with open(fl, 'wb') as ff:
        pickle.dump(card_list, ff)