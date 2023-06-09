"""
參考同學程式，旋轉稿紙角度

by kyL
"""

import os
import cv2
import numpy as np
from tqdm import tqdm
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Step 1 rotate scan page')
    
    parser.add_argument('--id',
                        help='To rotated page from student id folder',
                        default="111C52032",
                        type=str)

    args = parser.parse_args()
    return args

def zoom_qrcode_finder(image, qrcode, thresh=64):
    """放大處理QRCode位置，二值化處理並搜尋 QR Code 位置
    
    Keyword arguments: 
        image -- 要搜尋的圖片
    Return:
        now_page -- 檔案頁面
        bbox -- QR Code 邊界
        None -- 找不到 QR Code
    """
    h, w = image.shape
    crop_h = h // 3
    crop_w = w // 3
    scale_h = crop_h / h
    scale_w = crop_w / w
    crop_img = image[h - crop_h : h, w - crop_w : w]
    zoom_img = cv2.resize(crop_img, (w, h))
    zoom_img = cv2.threshold(zoom_img, thresh, 255, cv2.THRESH_BINARY)[1]
    now_page, bbox, _ = qrcode.detectAndDecode(zoom_img)

    if bbox is not None:
        bbox[:, :, 0] = bbox[:, :, 0] * scale_w + w - crop_w
        bbox[:, :, 1] = bbox[:, :, 1] * scale_h + h - crop_h
        return now_page, bbox

    elif thresh == 192:
        return None
    return zoom_qrcode_finder(image, qrcode, thresh + 64)


def qrcode_finder(image):
    """搜尋 QR Code 位置
    
    Keyword arguments: 
        image -- 要搜尋的圖片
    Return:
        now_page -- 檔案頁面
        bbox -- QR Code 邊界
        None -- 找不到 QR Code
    """
    qrcode = cv2.QRCodeDetector()
    now_page, bbox, rectified = qrcode.detectAndDecode(image)
    
    if bbox is None:
        return zoom_qrcode_finder(image, qrcode)
    return now_page, bbox
    
def boxSize(arr):
    """獲取 bbox 的最大以及最小 X, Y
    
    Keyword arguments: 
        arr -- bbox
    Return: 
        (min_x, min_y, max_x, max_y)
    """
    box_roll = np.rollaxis(arr, 1, 0)
    xmax = int(np.amax(box_roll[0]))
    xmin = int(np.amin(box_roll[0]))
    ymax = int(np.amax(box_roll[1]))
    ymin = int(np.amin(box_roll[1]))
    return (xmin, ymin, xmax, ymax)
    
def get_skew_angle(qrcode_img) -> float:
    """計算角度
    
    Keyword arguments:
        qrcode_img -- 含有 qrcode 的圖片
    Return:
        angle -- 角度 float
    """
    
    # cv2.imshow("test", qrcode_img)
    # cv2.waitKey(0)
    
    gray = 255 - qrcode_img
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1] # (0, 90]
        
    if angle > 45:
        angle = 90 - angle
    else:
        angle = -angle
        
    return angle

def saveImage(image, now_page):
    """儲存 png 至 ./rotated/ 底下
    
    Keyword arguments:
        image -- 要存的圖片
        now_page -- 頁面 index
    """
    global result_path
    cv2.imwrite('./{}/{}.png'.format(result_path, now_page), image)
    

def rotate_img(file_path, index) -> bool:
    """主程式，以 QR Code 旋轉稿紙
    
    Keyword arguments:
        file_path -- 檔案路徑
    Return:
        True -- 執行成功
        False -- 錯誤
    """
    
    # Read Image from path
    try:
        img = cv2.imread(file_path)
    except:
        print("\n 錯誤檔案：{}".format(file_path))
        return False
    height, width, _ = img.shape
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    center_w = width // 2
    center_h = height // 2
    
    # QRCode detector
    right_bottom = blur[center_h : height, center_w : width]
    IsRightBottom = True
    now_page, bbox = qrcode_finder(right_bottom)
    # if there is no qrcode in the right bottom corner
    if bbox is None:
        left_top = blur[0 : center_h, 0 : center_w]
        now_page, bbox = qrcode_finder(left_top)
        IsRightBottom = False
    if bbox is None: return False
    if now_page == '':
        now_page = str(index + 1)
        print(f'\nGet information from QR code failed, replace to "{now_page}.png", file path: {file_path}')
        print(f'Warning: It may contained page error, please check it manually')
    
    # Calculate qrcode angle
    box = boxSize(bbox[0])
    scale = 30
    angle = 0
    # check if there is a qrcode in the right bottom corner
    if IsRightBottom:
        angle = get_skew_angle(gray[
            box[1] + center_h - scale : box[3] + center_h + scale,
            box[0] + center_w - scale : box[2] + center_w+ scale
        ])
    else:
        angle = get_skew_angle(gray[
            box[1] - scale : box[3] + scale,
            box[0] - scale : box[2] + scale
        ])
    
    # Rotate Image
    M = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
    rotated = cv2.warpAffine(img, M, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Write Image
    saveImage(rotated, now_page)
    
    return True

if __name__ == '__main__':
    args = parse_args()
    student_id = args.id

    target_path = f'./{student_id}' # !!! 目標資料夾 !!!
    result_path = f'rotated_{student_id}' # 存放資料夾
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    
    print(f"Handling page rotation, student id = {student_id}")
    
    errorList = []
    allFileList = os.listdir(target_path)
    for index in tqdm(range(len(allFileList))):
        filePath = target_path + "/" + allFileList[index]
        if not rotate_img(filePath, index):
            errorList.append(allFileList[index])
            
    print("Rotate successfully")
    
    if len(errorList):
        # 錯誤原因為 QR Code 無法偵測
        print("The following is the wrong file, please rotate it yourself：")
        for errPath in errorList:
            print(errPath)