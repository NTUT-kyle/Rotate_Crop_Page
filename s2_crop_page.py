"""
參考同學程式，切割稿紙文字
先調整稿紙角度，執行 s1_rotate_page.py
再執行此程式

by kyL
"""

from s1_rotate_page import qrcode_finder, boxSize

import cv2
import os, json
import numpy as np
from tqdm import tqdm

def read_json(file):
    with open(file) as f:
        p = json.load(f)
        v = ['']*13759
        for i in range(13759):
            if (128 <= i & i < 256) or (0 <= i & i < 32): # 128 - 255: 'UNICODE' = '     '; 0 - 31: unable to print
                v[i] = '123'
            else:
                v[i] = 'U+' + p['CP950'][i]['UNICODE'][2:6] # ex: 0x1234 --> U+1234
        return v

def twoPointDistance(p1, p2):
    """計算兩點之間的距離
    
    Keyword arguments:
        p1 -- 點 1
        p2 -- 點 2
    Return:
        兩點的距離
    """
    p1 = np.array(p1)
    p2 = np.array(p2)
    return abs(
        np.sqrt(
            np.sum(
                np.power(p1 - p2, 2)
            )
        )
    )

def getTLTRBLBR(mask):
    """獲取 mask 中左上、右上、左下、右下座標
    
    Keyword arguments:
        mask -- 照片遮罩
    Return:
        list -- [左上, 右上, 左下, 右下]
        None -- 圖片 mask 無效
    """
    
    h, w = mask.shape
    
    result = [
        [w - 1, h - 1], # 左上
        [0, h - 1],     # 右上
        [w - 1, 0],     # 左下
        [0, 0]          # 右下
    ]
    
    # 獲取左上右上左下右下
    coords = np.argwhere(mask == 255)
    if len(coords) > 0:
        for pixel in coords:
            y, x = pixel
            if y < result[0][1]:
                result[0][1] = y
            if x < result[0][0]:
                result[0][0] = x
            if y < result[1][1]:
                result[1][1] = y
            if x > result[1][0]:
                result[1][0] = x
            if y > result[2][1]:
                result[2][1] = y
            if x < result[2][0]:
                result[2][0] = x
            if y > result[3][1]:
                result[3][1] = y
            if x > result[3][0]:
                result[3][0] = x
    else:
        return None
    return result

def savePNG(image, index, now_page):
    """儲存 png 至 /1_138/ 底下
    
    Keyword arguments:
        image -- 要存的圖片
        index -- 文字的 index
    """
    global PAGE_START, PAGE_END, v
    cv2.imwrite(f'./{PAGE_START}_{PAGE_END}/'+ v[index-1] + '.png', image)

def getTopBottomArea(image, w, h):
    """獲取上面與下面的多餘區域高度
    
    Keyword arguments:
        image -- 要存的照片
        index -- 文字的 index
    Return:
        上方的高度, 下方的高度
    """
    center_w = w // 2
    center_h = h // 2
    
    # QRCode detector
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    bbox = qrcode_finder(blur[center_h : h, center_w : w])
    if bbox is None: return 0, 0
    box = boxSize(bbox[0])
    
    # Calculate bottom area
    bottom_high = center_h + box[1] - 15
    
    # Calculate top area
    top_high = 0
    findtop = False
    for h_index in range(h):
        # the number of pixels that are not white
        pixel = np.sum(gray[h_index, :] != 255)
        if pixel > 30:
            findtop = True
        elif findtop and pixel == 0:
            top_high = h_index + 20
            break
    return top_high, bottom_high

def setPointImageFromPath(file_path, now_page) -> bool:
    """主程式，用於辨識並切割稿紙
    
    Keyword arguments:
        file_path -- 檔案路徑
        now_page -- 現在的 Page index
    Return:
        True -- 執行成功
        False -- 錯誤
    """
    global success_count, v, errorWord
    
    image = cv2.imread(file_path)
    h, w, _ = image.shape

    # 去除高低不需要的區塊(某些情況下會失誤，失誤原因可能是因為灰塵...)
    top_h, bottom_h = getTopBottomArea(image, w, h)
    if not (top_h and bottom_h): return False
    image[0:top_h, :] = 255
    image[bottom_h:, :] = 255

    # 以 HSV 獲取綠色區塊的 mask
    lower_green = np.array([36, 90, 90]) # 綠色在 HSV 的範圍
    upper_green = np.array([70, 255, 255])
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # 對 mask 腐蝕去雜訊
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    AfterErode = cv2.erode(mask, kernel)
    
    # 獲取左上右上左下右下座標 (如果 mask 效果不好會錯誤)
    result = getTLTRBLBR(AfterErode)
    if result == None: return False

    # block 綠框大小，14.75 為現實寬度，210 為 A4 寬度
    block = 14.75 * w // 210
    # bet 左右綠框之間距離
    bet = (twoPointDistance((result[0][0], result[0][1]), (result[1][0], result[1][1])) - block * 10) / 9
    # mid 上下綠框之間距離
    mid = (twoPointDistance((result[0][0], result[0][1]), (result[2][0], result[2][1])) - block * 10) / 9

    # 處理此頁面的每個字
    last_y = 0
    for j in range(10):
        # calculate Y coordinate 
        y1 = int(result[0][1] + j * (block + mid))
        y2 = int(y1 + block)
        
        image[last_y:y1, :] = 255
        for k in range(10):  
            index = 100 * (now_page - 1) + k + 10 * j + 1
            
            # 檢查 index
            if index > len(v): 
                break
            if v[index - 1] == '123':
                errorWord.append(f'page {now_page} 的第 {j} 列第 {k} 個無法處理')
                continue
            
            # calculate X coordinate 
            x1 = int(result[0][0] + k * (block + bet))
            x2 = int(x1 + block)
            
            scale = 10
            # 獲取第 j 列第 k 個圖片
            word_img = image[y1 - scale:y2 + scale, x1 - scale:x2 + scale]
            
            # 定位綠框左上以及右下座標
            word_hsv = cv2.cvtColor(word_img, cv2.COLOR_BGR2HSV)
            word_mask = cv2.inRange(word_hsv, lower_green, upper_green)
            word_result = getTLTRBLBR(word_mask)
            if word_result != None and twoPointDistance(word_result[0], word_result[1]) - block < 10:
                # 當綠框寬度與左上右上座標之間的距離相近，採用定位到的座標(準度較佳)
                word_img = word_img[word_result[0][1] + scale: word_result[3][1] - scale, word_result[0][0] + scale: word_result[3][0] - scale]
            else:
                # 採用計算得到的座標(準度較差)
                scale += 20
                word_img = image[y1 + scale:y2 - scale, x1 + scale:x2 - scale]
            
            
            # 儲存圖片
            savePNG(cv2.resize(word_img, (300, 300), interpolation=cv2.INTER_AREA), index, now_page)
            success_count += 1
        last_y = y2 + 25
             
    return True

if __name__ == '__main__':
    PAGE_START = input("Please enter the number of pages you want to start processing(default:1): ")
    if not PAGE_START.strip():
        PAGE_START = 1

    PAGE_END = input("Please enter the number of pages you want to end processing(default:138): ")
    if not PAGE_END.strip():
        PAGE_END = 138
    
    PAGE_START = int(PAGE_START)
    PAGE_END = int(PAGE_END)
    
    targetPath = './rotated' # !!! 目標資料夾 !!!
    im_dir = f'./{PAGE_START}_{PAGE_END}' # 存放資料夾
    v = read_json('./CP950.json')
    
    errorList = []
    errorWord = []
    success_count = 0

    if not os.path.exists(im_dir): # 創 png 這個資料夾
        os.makedirs(im_dir)
        print(f"Created folders '{PAGE_START}_{PAGE_END}'. ")
    else:
        print(f"Folders '{PAGE_START}_{PAGE_END}' have been created. ")

    print(f"Processing page {PAGE_START}~{PAGE_END} files. ")
    
    for now_page in tqdm(range(PAGE_START, PAGE_END + 1)): # 因為 Python 的 range 最後一個數字沒有包括，所以這邊需要 + 1
        filePath = f'{targetPath}/{now_page}.png'
        if not setPointImageFromPath(filePath, now_page):
            errorList.append(filePath)
    
    print(f"The crop of page {PAGE_START}~{PAGE_END} has been completed")
    print(f"  A total of {success_count} png files were processed")
    print(f"  A total of {len(errorWord)} png files were not processed")
    
    if len(errorList):
        # 錯誤原因為無法偵測綠色框線導致
        print("The following is the wrong file, please fix it yourself：")
        for errPath in errorList:
            print(errPath)