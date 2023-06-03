"""
參考同學程式，切割稿紙文字
先調整稿紙角度，執行 s1_rotate_page.py
再執行此程式

by kyL
"""

import cv2
import os, json
import numpy as np
from tqdm import tqdm

from multiprocessing import Pool
from threading import Thread
import time

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Step 2 crop page')
    
    parser.add_argument('--id',
                        help='To rotated student id',
                        default="111C52032",
                        type=str)

    args = parser.parse_args()
    return args

def read_json(file):
    with open(file) as f:
        p = json.load(f)
        unicode = ['']*13759
        for i in range(13759):
            if (128 <= i & i < 256) or (0 <= i & i < 32): # 128 - 255: 'UNICODE' = '     '; 0 - 31: unable to print
                unicode[i] = '123'
            else:
                unicode[i] = 'U+' + p['CP950'][i]['UNICODE'][2:6] # ex: 0x1234 --> U+1234
        return unicode

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
    return  np.sqrt(
                np.sum(
                    np.power(p1 - p2, 2)
                )
            )

def getBoundingBox(mask):
    """獲取 mask 中左上、右下座標
    
    Keyword arguments:
        mask -- 照片遮罩
    Return:
        list -- [左上, 右下]
        None -- 圖片 mask 無效
    """
    
    h, w = mask.shape
    
    result = np.array([
        [w - 1, h - 1], # 左上
        [0, 0]          # 右下
    ])
    
    # 獲取左上右上左下右下
    coords = np.argwhere(mask == 255)
    if len(coords) > 0:
        min_y, min_x = coords.min(axis=0)
        max_y, max_x = coords.max(axis=0)

        result[0][1] = min(min_y, result[0][1])
        result[1][1] = max(max_y, result[1][1])
        result[0][0] = min(min_x, result[0][0])
        result[1][0] = max(max_x, result[1][0])
    else:
        return None
    return result

def savePNG(image, index, now_page, IM_DIR, unicode):
    """儲存 png 至 /1_138/ 底下
    
    Keyword arguments:
        image -- 要存的圖片
        index -- 文字的 index
    """
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(f'./{IM_DIR}/'+ unicode[index-1] + '.png', image)

def outputFileListener(outputDir, total):
    """用於顯示進度條
    
    Keyword arguments:
        outputDir -- 輸出檔案路徑
        total -- 估計輸出總字數數量
    """
    global PROCESS_END

    pbar = tqdm(total=total)
    while(not PROCESS_END):
        pbar.n = len(os.listdir(outputDir))
        pbar.refresh()
        if pbar.n >= total:
            break
        time.sleep(0.5)

def scaleAdjustment(word_img, adjustCentroid=True):
    """調整文字大小、重心
    
    Keyword arguments:
        word_img -- 文字圖片
    """
    # 把文字圖片建立在更大的空白區域上
    word_img_copy = cv2.copyMakeBorder(word_img, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    # 二值化處理
    binary_word_img = cv2.cvtColor(word_img_copy, cv2.COLOR_BGR2GRAY)
    binary_word_img = cv2.threshold(binary_word_img, 127, 255, cv2.THRESH_BINARY_INV)[1]
    # 取得文字 Bounding Box
    topLeftX, topLeftY, word_w, word_h = cv2.boundingRect(binary_word_img)

    # 計算質心
    cX, cY = topLeftX + word_w // 2, topLeftY + word_h // 2
    if adjustCentroid:
        moments = cv2.moments(binary_word_img)
        if moments["m00"] != 0:
            cX = int(moments["m10"] / moments["m00"])
            cY = int(moments["m01"] / moments["m00"])

    # 以質心作爲中心點，取得文字所在正方形區域
    block_size_half = max(
        abs(cX - topLeftX),
        abs(topLeftX + word_w - cX),
        abs(cY - topLeftY),
        abs(topLeftY + word_h - cY)
        ) + 10
    h, w, _ = word_img_copy.shape
    left_x = max(0, cX - block_size_half)
    right_x = min(w, cX + block_size_half)
    top_y = max(0, cY - block_size_half)
    bot_y = min(h, cY + block_size_half)

    finalWordImg = word_img_copy[top_y:bot_y, left_x:right_x]

    return cv2.resize(finalWordImg, (300, 300), interpolation=cv2.INTER_AREA)

def setPointImageFromPath(args) -> str:
    """主程式，用於辨識並切割稿紙
    
    Keyword arguments:
        args -- 參數(
            檔案路徑、現在頁數、開始頁數、結束頁數、文字 Unicode、
            調整質心、尺度大小、是否顯示過程、對比度)
    Return:
        True -- 執行成功
        False -- 錯誤
    """
    file_path, now_page, IM_DIR, unicode, adjustCentroid, SCALE, show, COLOR_BOOST = args

    try:
        image = cv2.imread(file_path)
        show_image = image.copy()
        if image is None:
            raise Exception
    except:
        return f"LoadError: {now_page}"
    h, w, _ = image.shape

    # Boost Contrast
    if COLOR_BOOST:
        contrast = 50
        colorBoost = image * (contrast/127 + 1) - contrast # 轉換公式
        colorBoost = np.clip(colorBoost, 0, 255)
        colorBoost = np.uint8(colorBoost)
        image = colorBoost

    # 以 HSV 獲取綠色區塊的 mask
    lower_green = np.array([20, 90, 90]) # 綠色在 HSV 的範圍
    upper_green = np.array([95, 255, 255]) # 綠色到淺藍在 HSV 的範圍
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # 對 mask 中值濾波去鹽雜訊
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilateMask = cv2.dilate(mask, kernel, iterations=5)
    mask = cv2.medianBlur(mask, 7)
    globalMask = np.zeros_like(mask)

    # 獲取 mask 中的全部矩形
    contours = cv2.findContours(dilateMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]

    # 過濾掉過小、過大或不屬於正方形的矩形
    min_area = h * w * 0.0008
    max_area = h * w * 0.028
    border = 15
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area and area < max_area:
            rect_x, rect_y, rect_w, rect_h = cv2.boundingRect(contour)

            # 過濾掉非正方形以及QRCode的框
            if (ratio := rect_w / rect_h) < 0.9 or ratio > 1.1 or rect_y + rect_h > h * 0.95:
                continue

            # 過濾掉框内的雜訊
            dilateMask[rect_y + border:rect_y + rect_h - border, rect_x + border:rect_x + rect_w - border] = 0
            globalMask[rect_y:rect_y + rect_h, rect_x:rect_x + rect_w] = \
                dilateMask[rect_y:rect_y + rect_h, rect_x:rect_x + rect_w]
    mask[globalMask == 255] = 255
    
    # 獲取左上右上左下右下座標 (如果 mask 效果不好會錯誤)
    result = getBoundingBox(globalMask)
    if result is None:
        return f"GetGlobalMaskError: {now_page}"
    globalScale = SCALE // 2
    result[0, :] += globalScale
    result[1, :] -= globalScale

    # block 綠框大小，14.75 為現實寬度，210 為 A4 寬度 (mm)
    block = 14.75 * w // 210
    # bet 左右綠框之間距離
    bet = (twoPointDistance(result[0], (result[1][0], result[0][1])) - block * 10) / 9
    # mid 上下綠框之間距離
    mid = (twoPointDistance(result[0], (result[0][0], result[1][1])) - block * 10) / 9

    if show:
        cv2.rectangle(show_image, (result[0][0], result[0][1]), (result[1][0], result[1][1]), (0, 0, 255), 5)
        cv2.imshow('Global Mask', cv2.resize(mask, (mask.shape[1] // 8, mask.shape[0] // 8)))

    # 處理此頁面的每個字
    for j in range(10):
        # calculate Y coordinate 
        y1 = int(result[0][1] + j * (block + mid))
        y2 = int(y1 + block)
        
        for k in range(10):  
            index = 100 * (now_page - 1) + k + 10 * j + 1
            
            # 檢查 index
            if index > len(unicode): 
                break
            if unicode[index - 1] == '123': # skip (ignore character)
                continue
            
            # calculate X coordinate 
            x1 = int(result[0][0] + k * (block + bet))
            x2 = int(x1 + block)
            if show:
                cv2.rectangle(show_image, (x1 - SCALE, y1 - SCALE), (x2 + SCALE, y2 + SCALE), (255, 0, 0), 5)
                cv2.imshow('Image',
                           cv2.resize(show_image,
                                      (show_image.shape[1] // 8, show_image.shape[0] // 8),
                                      interpolation=cv2.INTER_AREA)
                            )
            
            # 獲取第 j 列第 k 個圖片
            word_img = image[y1 - SCALE:y2 + SCALE, x1 - SCALE:x2 + SCALE]
            word_mask = mask[y1 - SCALE:y2 + SCALE, x1 - SCALE:x2 + SCALE]
            
            # 定位綠框左上以及右下座標
            word_result = getBoundingBox(word_mask)
            if word_result is not None and \
                twoPointDistance(word_result[0], (word_result[1][0], word_result[0][1])) - block < 10:
                # 當綠框寬度與左上右上座標之間的距離相近，採用定位到的座標(準度較佳)
                word_img[word_mask == 255] = 255
                word_img = word_img[word_result[0][1] + SCALE: word_result[1][1] - SCALE, word_result[0][0] + SCALE: word_result[1][0] - SCALE]
            else:
                # 採用計算得到的座標(準度較差)
                scale = SCALE + 20
                word_img = image[y1 + scale:y2 - scale, x1 + scale:x2 - scale]
            
            # 儲存圖片
            if index > 665 and index <= 13725:
                #僅對中文字進行重心調整
                finalWordImg = scaleAdjustment(word_img, adjustCentroid=adjustCentroid)
                savePNG(finalWordImg,\
                        index, now_page, IM_DIR, unicode)
            else:
                if word_img.shape[0] == 0 or word_img.shape[1] == 0:
                    return f'CropError: {now_page}, code_{str(unicode[index-1])}'
                savePNG(cv2.resize(word_img, (300, 300), interpolation=cv2.INTER_AREA),\
                        index, now_page, IM_DIR, unicode)
                
        if show:
            key = cv2.waitKey(1)
            if key == 27:
                cv2.destroyAllWindows()
                exit()
             
    return "Pass"

def outputResult(PAGE_START, PAGE_END, results, time):
    returnState = {
        'LoadError':[],
        'QrcodeNotFoundError':[],
        'GetGlobalMaskError':[],
        'CropError':[],
        'Pass': 0
        }
    
    # 分類回傳值
    for result in results:
        result = result.split(':')
        if result[0] in returnState.keys():
            if result[0] == 'Pass':
                returnState[result[0]] += 1
            else:
                returnState[result[0]].append(result[1])

    # 輸出執行結果
    print(f"The crop of page {PAGE_START}~{PAGE_END} has been completed in {time / 60:.2}mins")
    print(f"  A total of {returnState['Pass']} png files were processed")

    for key, value in returnState.items():
        if key == 'Pass' or value == []:
            continue
        print(f"  {key}: {value}")

def main(args):
    global PROCESS_END

    PAGE_START = input("Please enter the number of pages you want to start processing(default:1): ")
    if not PAGE_START.strip():
        PAGE_START = 1
    PAGE_END = input("Please enter the number of pages you want to end processing(default:138): ")
    if not PAGE_END.strip():
        PAGE_END = 138
    PAGE_START = int(PAGE_START)
    PAGE_END = int(PAGE_END)

    im_dir = f'./{PAGE_START}_{PAGE_END}_{args.id}' # 存放資料夾
    unicode = read_json('./CP950.json')

    if not os.path.exists(im_dir): # 創 png 這個資料夾
        os.makedirs(im_dir)
        print(f"Created folders '{im_dir}'. ")
    else:
        print(f"Folders '{im_dir}' exist. ")
    print(f"Processing page {PAGE_START}~{PAGE_END} files... ")

    # 生成全部參數
    filePaths = []
    now_pages = []
    for now_page in range(PAGE_START, PAGE_END + 1):
        filePaths.append(f'{targetPath}/{now_page}.png')
        now_pages.append(now_page)
    IM_DIRS = [im_dir] * len(filePaths)
    unicodes = [unicode] * len(filePaths)
    adjustCentroids = [ADJUST_CENTROID] * len(filePaths)
    shows = [SHOW if not MULTIPROCESSING else False] * len(filePaths)
    scales = [SCALE] * len(filePaths)
    COLOR_BOOSTs = [COLOR_BOOST] * len(filePaths)

    # 監聽輸出資料夾，顯示進度條
    start_unicode = (PAGE_START - 1) * 100
    end_unicode = min(PAGE_END * 100, 13758)
    total_available_code = len(unicode[start_unicode : end_unicode]) - unicode[start_unicode : end_unicode].count('123')
    thread = Thread(target=outputFileListener, args=(im_dir, total_available_code))
    thread.start()
    
    # 執行主程式
    t1 = time.time()
    try:
        if MULTIPROCESSING:
            with Pool(4) as p:
                results = p.map(
                    setPointImageFromPath,
                    zip(filePaths, now_pages, IM_DIRS, unicodes, adjustCentroids, scales, shows, COLOR_BOOSTs)
                    )
        else:
            results = []
            for args in zip(filePaths, now_pages, IM_DIRS, unicodes, adjustCentroids, scales, shows, COLOR_BOOSTs):
                results.append(setPointImageFromPath(args))
    finally:
        PROCESS_END = True
    thread.join()
    t2 = time.time()
    
    outputResult(PAGE_START, PAGE_END, results, t2 - t1)

if __name__ == '__main__':
    PROCESS_END = False # 勿改
    MULTIPROCESSING = True # 多進程，True不能顯示切割過程，無法中途停下
    ADJUST_CENTROID = True # 文字重心對齊
    SHOW = False # 顯示切割過程
    SCALE = 20 # 電子檔設5，紙本設20
    COLOR_BOOST = True # 增加對比度，適用於紙本掃描, 但會影響速度

    args = parse_args()
    student_id = args.id

    targetPath = f'./rotated_{student_id}' # !!! 目標資料夾 !!!

    main(args)