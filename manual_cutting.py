import cv2
import os
import numpy as np

from s2_crop_page import read_json, twoPointDistance, getBoundingBox, scaleAdjustment

class ImagePage(object):
    def __init__(self, v, now_page, resize_scale):
        self.image = None
        self.resize_image = None
        self.h = 0
        self.w = 0
        
        self.now_page = now_page
        self.v = v
        
        self.dot_1 = []
        self.dot_2 = []
        
        self.resize_scale = resize_scale
        
    def read_image(self, path):
        try:
            self.image = cv2.imread(path)
            self.h, self.w, _ = self.image.shape
            
            # Boost Contrast
            contrast = 50
            colorBoost = self.image * (contrast / 127 + 1) - contrast # 轉換公式
            colorBoost = np.clip(colorBoost, 0, 255)
            self.image = np.uint8(colorBoost)
            
            # resize image for manual cutting
            self.resize_image = cv2.resize(
                self.image,
                (self.w // self.resize_scale, self.h // self.resize_scale)
            )
            return True
        except:
            print(f"檔案錯誤 {path}")
            return False
    
    def selection_box(self, event, x, y, flags, param):
        def drag_img(isLButtonDown):
            temp_img = self.resize_image.copy()
            th, tw, _ = temp_img.shape
            cv2.line(temp_img,
                (0, y), (tw - 1, y),
                (0, 0, 255), 1
            )
            cv2.line(temp_img,
                (x, 0), (x, th),
                (0, 0, 255), 1
            )
            cv2.imshow('SelectionBox', temp_img)
            if isLButtonDown:
                cv2.rectangle(
                    temp_img, 
                    (self.dot_1[0], self.dot_1[1]),
                    (self.dot_2[0], self.dot_2[1]),
                    (255, 0, 0), 1
                )
            cv2.imshow('SelectionBox', temp_img)
            
        if flags == cv2.EVENT_FLAG_LBUTTON:
            if event == cv2.EVENT_LBUTTONDOWN:
                self.dot_1 = [x, y]
            elif event == cv2.EVENT_MOUSEMOVE:
                self.dot_2 = [x, y]
                drag_img(True)
                
        elif flags == cv2.EVENT_FLAG_RBUTTON:
            if event == cv2.EVENT_MOUSEMOVE:
                drag_img(False)
                
        
    def selection_box_on_image(self):
        print('1. 按住"右鍵"顯示輔助線，幫助對準字框')
        print('2. 按住"左鍵"把需要切割的區域框起來(左上字框以及右下字框，越準越好)')
        print('3. 放開"左鍵"把需要切割的區域定型(再按住左鍵即重新定型)')
        print('4. 確認後按下任意鍵開始切割')
        cv2.imshow("SelectionBox", self.resize_image)
        cv2.setMouseCallback('SelectionBox', self.selection_box)
        cv2.waitKey(0)
        
        self.dot_1 = [self.dot_1[0] * self.resize_scale, self.dot_1[1] * self.resize_scale]
        self.dot_2 = [self.dot_2[0] * self.resize_scale, self.dot_2[1] * self.resize_scale]
        
        cv2.destroyAllWindows()
        
    def crop_image_from_box(self):
        errorWord = []
        lower_green = np.array([20, 90, 90]) # 綠色在 HSV 的範圍
        upper_green = np.array([95, 255, 255]) # 綠色到淺藍在 HSV 的範圍
        
        # block 綠框大小，14.75 為現實寬度，210 為 A4 寬度
        block = 14.75 * self.w // 210
        # bet 左右綠框之間距離
        bet = (twoPointDistance(self.dot_1, (self.dot_2[0], self.dot_1[1])) - block * 10) / 9
        # mid 上下綠框之間距離
        mid = (twoPointDistance((self.dot_2[0], self.dot_1[1]), self.dot_2) - block * 10) / 9
        
        # 處理此頁面的每個字
        for j in range(10):
            # calculate Y coordinate 
            y1 = int(self.dot_1[1] + j * (block + mid))
            y2 = int(y1 + block)
            
            for k in range(10):
                index = 100 * (self.now_page - 1) + k + 10 * j + 1
            
                # 檢查 index
                if index > len(self.v): 
                    break
                if self.v[index - 1] == '123':
                    errorWord.append(f'page {self.now_page} 的第 {j} 列第 {k} 個無法處理')
                    continue
                
                # calculate X coordinate 
                x1 = int(self.dot_1[0] + k * (block + bet))
                x2 = int(x1 + block)
                
                scale = 10
                # 獲取第 j 列第 k 個圖片
                word_img = self.image[y1 - scale:y2 + scale, x1 - scale:x2 + scale]
                
                # 定位綠框左上以及右下座標
                word_hsv = cv2.cvtColor(word_img, cv2.COLOR_BGR2HSV)
                word_mask = cv2.inRange(word_hsv, lower_green, upper_green)
                word_result = getBoundingBox(word_mask)
                if word_result is not None and \
                    twoPointDistance(word_result[0], (word_result[1][0], word_result[0][1])) - block < 10:
                    # 當綠框寬度與左上右上座標之間的距離相近，採用定位到的座標(準度較佳)
                    word_img[word_mask == 255] = 255
                    word_img = word_img[word_result[0][1] + scale: word_result[1][1] - scale, word_result[0][0] + scale: word_result[1][0] - scale]
                else:
                    # 採用計算得到的座標(準度較差)
                    scale += 20
                    word_img = image[y1 + scale:y2 - scale, x1 + scale:x2 - scale]
                
                # 儲存圖片
                if index > 665 and index <= 13725:
                    #僅對中文字進行重心調整
                    finalWordImg = scaleAdjustment(word_img)
                    self.save_word_image(finalWordImg, index)
                else:
                    if word_img.shape[0] == 0 or word_img.shape[1] == 0:
                        return f'CropError: code_{str(unicode[index-1])}'
                    self.save_word_image(cv2.resize(word_img, (300, 300), interpolation=cv2.INTER_AREA), index)
        return errorWord
        
    def save_word_image(self, word_image, index):
        try:
            cv2.imwrite(
                f'./Result_{self.now_page}/'+ self.v[index-1] + '.png',
                word_image
            )
            return True
        except:
            print(f"轉成圖片錯誤 {self.v[index-1]}")
            return False

        

def main_func():
    file_path = input('輸入圖片頁面路徑: ')
    now_page = input('輸入頁面編號: ')
    
    # 檢查頁面編號
    try:
        now_page = int(now_page)
    except:
        print('頁面編號錯誤 {}'.format(now_page))
        return False
    
    if not (1 < now_page < 139):
        print('頁面編號並沒有介於 1 - 138 : {}'.format(now_page))
        return False
    
    # 檢查檔案
    if not os.path.isfile(file_path):
        print('檔案錯誤 {}'.format(file_path))
        return
    
    img_page = ImagePage(read_json('./CP950.json'), now_page, 7) # 7 為選取框的圖片縮小倍數(可改)
    
    if not img_page.read_image(file_path):
        print('檔案錯誤 {}'.format(file_path))
        return
    
    # 建立輸出資料夾
    if not os.path.exists(f'Result_{now_page}'):
        os.makedirs(f'Result_{now_page}')
    
    # 圖片框選
    img_page.selection_box_on_image()
    # 切割圖片並儲存
    errorWord = img_page.crop_image_from_box()
    if len(errorWord):
        print("以下為錯誤的字檔，請自行修復：")
        for errPath in errorWord:
            print(errPath)
    
if __name__ == '__main__':
    main_func()