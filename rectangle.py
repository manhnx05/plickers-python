# -*-coding:utf-8-*-
import cv2
import numpy as np
from my_math import  Math
from time import sleep
import pickle
import sys
import csv
from datetime import datetime
import time

global CARD_NUM

CARD_NUM=1
def card_check(result):
    global CARD_NUM
    count = 1
    wigth,higth=result.shape
    result=cv2.resize(result,(10*higth,10*wigth))
    card_array = np.zeros([5, 5])  # array sort [y,x]
    wigth,higth=result.shape
    #print 'check',wigth,higth
    for y in range(1, 6):
        for x in range(1, 6):
            # print('con',count,y,x)
            # print((higth)* (y/5.0))
            if y == 1 and x == 1:
                crop = result[0:int(wigth * (y / 5.0)), 0:int(wigth * (x / 5.0))]
            elif y == 1:
                crop = result[0:int(wigth * (y / 5.0)), int(wigth * ((x - 1) / 5.0)):int(wigth * (x / 5.0))]
                #print int(wigth*(y/5.0)),int(wigth*((x-1)/5.0)),int(wigth*(x/5.0))
                # cv2.imshow(str(y)+':'+str(x), crop)
                # cv2.waitKey(0)
            elif x == 1:
                crop = result[int(wigth * ((y - 1) / 5.0)):int(wigth * (y / 5.0)), 0:int(wigth * (x / 5.0))]
            else:
                crop = result[int(wigth * ((y - 1) / 5.0)):int(wigth * (y / 5.0)),
                       int(wigth * ((x - 1) / 5.0)):int(wigth * (x / 5.0))]

            if np.average(crop) > 120:
                #1 is white  0 is balck
                card_array[y - 1, x - 1] = 0
            else:
                card_array[y - 1, x - 1] = 1
            count += 1

    num = 0
    check = 0
    # print('the global num',CARD_NUM,'the card',card_array)
    for i in card_data:
        # print(i)
        if np.array_equal(i, card_array):
            check = 1
            break
        num += 1
    if check:
        print('the global num',CARD_NUM,num, 'bingo',card_list[num])
        return card_list[num]
    CARD_NUM+=1
    return 0

import sys
#####读取卡片的矩阵信息#######
np.set_printoptions(threshold=sys.maxsize)

fn= './card.data'
f=open(fn,'rb').read()
card_data=pickle.loads(f, encoding='latin1')
fn= './card.list'
f=open(fn,'rb').read()
card_list=pickle.loads(f, encoding='latin1')
#print(len(card_list))
#print(card_list)
#print(card_data)


#############main####################
cap = cv2.VideoCapture(0)

csv_filename = "ket_qua.csv"
try:
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Thoi_Gian", "Ma_Hoc_Sinh", "Dap_An_Chon", "Day_Du"])
except Exception:
    pass

scanned_cards = {}
COOLDOWN_TIME = 5.0 # Mức chặn thẻ điền đè liên tiếp: 5 giây

print("Đang khởi động Camera... Bấm phím 'q' trên cửa sổ Camera để thoát.")
while True:
    ret, frame = cap.read()
    if not ret:
        print("Không thể kết nối với Camera!")
        break
        
    img = frame.copy()
    
    ### Blur ###
    blur_img = cv2.GaussianBlur(img, (3, 3), 0)
    ### Canny Edge ###
    canny = cv2.Canny(blur_img, 40, 170)
    ### Grayscale ###
    gray = cv2.cvtColor(blur_img, cv2.COLOR_BGR2GRAY)
    ### Threshold ###
    ret_thresh, thresh = cv2.threshold(gray, 99, 255, 1)

    ### Find Contours ###
    contours, hierarchy = cv2.findContours(canny, 2, 1)

    for cnt in contours:
        if len(cnt) > 50:
            approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
            if len(approx) > 4:
                card_id = 0
                if cnt[:,0,:].max() - cnt[:,0,:].min() > cnt[:,:,0].max() - cnt[:,:,0].min():
                    diff = cnt[:,:,0].max() - cnt[:,:,0].min()
                    card = thresh[cnt[:,0,:].min():cnt[:,0,:].min()+diff, cnt[:,:,0].min():cnt[:,:,0].max()]
                    if len(card) > 10 and 100 < np.average(card) < 230:
                        card_id = card_check(card)
                    
                    if not card_id:
                        card = thresh[abs(cnt[:,0,:].max()-diff):cnt[:,0,:].max(), cnt[:,:,0].min():cnt[:,:,0].max()]
                        if len(card) > 10 and 100 < np.average(card) < 230:
                            card_id = card_check(card)
                else:
                    diff = cnt[:,0,:].max() - cnt[:,0,:].min()
                    card = thresh[cnt[:,0,:].min():cnt[:,0,:].max(), cnt[:,:,0].min():cnt[:,:,0].min()+diff]
                    if len(card) > 10 and 100 < np.average(card) < 230:
                        card_id = card_check(card)
                        
                    if not card_id:
                        card = thresh[cnt[:,0,:].min():cnt[:,0,:].max(), cnt[:,:,0].max()-diff:cnt[:,:,0].max()]
                        if len(card) > 10 and 100 < np.average(card) < 230:
                            card_id = card_check(card)
                            
                # Nếu tìm thấy định dạng thẻ, lưu vào CSV và vẽ hiển thị
                if card_id:
                    current_time = time.time()
                    if card_id not in scanned_cards or (current_time - scanned_cards[card_id] > COOLDOWN_TIME):
                        scanned_cards[card_id] = current_time
                        try:
                            # Parse format: e.g. "015-A" -> "015", "A"
                            part = str(card_id).split('-')
                            student_no = part[0]
                            student_ans = part[1] if len(part)>1 else ""
                            
                            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
                                csv.writer(f).writerow([time_str, student_no, student_ans, str(card_id)])
                            print(f"[THÀNH CÔNG] Đã lưu thẻ {student_no} đáp án {student_ans} lúc {time_str}")
                        except Exception as e:
                            print(f"[LỖI] Không thể lưu file CSV: {e}")

                    cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 3)
                    x, y = cnt[:,:,0].min(), cnt[:,0,:].min()
                    cv2.putText(frame, str(card_id), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Plickers Scanner - Nhan 'q' de thoat", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
