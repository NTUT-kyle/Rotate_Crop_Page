# Rotate_Crop_Page

For 字體課程 138 page 使用 (一部份參考同學程式)

本程式會自動進行質心置中，並縮放到同樣大小。

如果有任何問題請提出 Issue

！ 感謝 [Heng Wei Bin](https://github.com/HengWeiBin) 幫忙提高程式碼品質，並提升準確度以及效能 ！

### Demo 影片
![Demo example](./ReadMeImage/CropWord.gif)
## 初始化專案

### 環境 Environment

使用 Python 3.9 (版本 3 以上應該都行...吧)

### 套件 Package

-   使用 requirements.txt 安裝

```cmd
pip install -r requirements.txt
```

-   或使用 pipenv 安裝 (本機需要有 pipenv 套件)

```cmd
# 建立虛擬環境
python -m pipenv shell

# Install requirements
pipenv install -r requirements.txt
```

## 使用說明

### 校正旋轉 page

環境安裝完成後，執行以下步驟：

1. 先修改目標資料夾，在`s1_rotate_page.py`中`L140`改成你的稿紙圖片資料夾位置([程式碼位置](https://github.com/NTUT-kyle/Rotate_Crop_Page/blob/main/s1_rotate_page.py#L140))
2. 執行程式`python s1_rotate_page.py`
3. 等待執行完成
4. 結果可以在`rotated`資料夾中看到

結束後，如果出現`The following is the wrong file`的話，照以下步驟手動修復：

1. 找出出錯檔案後，複製到`rotated`資料夾
2. 使用各種工具把圖片轉正
3. 回到第一步，繼續把其他錯誤的檔案轉正

### 影像處理切割文字

如果已經轉正，再做以下步驟：

1. 執行程式`python s2_crop_page.py`，可以在`s2_crop_page.py`的`L379~L385`修改參數
```
    - MULTIPROCESSING # 多進程，True不能顯示切割過程，無法中途停下
    - ADJUST_CENTROID # 文字重心對齊
    - SHOW # 顯示切割過程
    - SCALE # 電子檔設5，紙本設20
    - COLOR_BOOST # 增加對比度，適用於紙本掃描較差的圖，但會嚴重影響效率
    - targetPath # !!! 目標資料夾 !!!
```
2. 先輸入你要從哪個 Page 開始切割，如果是從 `30` 開始的話，就輸出 `30`(初始為 `1`)
3. 再輸入切割到哪個 Page，如果是 `30` 至 `60`，則輸入 `60` (初始為`138`)
4. 等待執行結束
5. 結果會在`1_138`資料夾中看到(如果不是初始值，則是在你設定數字的資料夾中看到)
6. 最後記得檢查是否有分割錯誤的字

結束後，如果出現一些問題的話，可以至已知問題中尋找解答！

## 已知問題以及解決步驟

通常`s1_rotate_page.py`不會有太大的問題，但`s2_crop_page.py`就不一樣了！

如果有更好的方法歡迎提出！

### 已知問題

#### The following is the wrong file & 字切割錯誤

如果發現`s2_crop_page.py`輸出`The following is the wrong file`的話，可以先試試

- 修改COLOR_BOOST參數、調色或去除雜訊以讓程式更好辨識
- 如果發現結果中，還是有切割錯誤的地方，請找到錯誤的 Page (下方的`找出字的頁面編號`)並照著下方的`手動切割`的解決方法來解決

#### 單一字元錯誤

如果發現單一字元，有切割錯誤的地方，可以自行使用任何工具切割，並命名為錯誤字元的檔名(U+XXXX)，最後再把錯誤的字元圖片覆蓋成新的。

#### 發生 Exception

如果發生 `Exception`，可以把錯誤訊息以及學號發 `Issue`，以便修復！(問題可能出在綠色 HSV 範圍上，因為掃描機掃出來的色彩並不是那麼 OK，所以範圍會因 Page 而異，可以調整 `contrast(L166), lower/upper_green(L173)` 參數看看)

### 解決方法
#### 找出字的頁面編號

若要找出字的頁面編號，可以使用`find_word_page.py`來快速尋找：

1. 在 console 中輸入`python ./find_word_page.py`並執行
2. 輸入錯誤字的 Unicode，假設錯誤的字為`絕`，其 Unicode 為 `5584`(可以看檔名)，那這邊就輸入 `5584`
3. 接下來程式就會幫你找字，會顯示`Found 5584 in page 35`，就代表字在第 35 個 Page，接下來就可以針對 Page 35 做修復或是手動切割等等。
#### 手動切割

若要讓字分割得更準確，可以使用`**manual_cutting**.py`來手動分割：

1. 找出出錯字的頁面(可以用`find_word_page.py`來找頁面)後，並單獨複製到其他地方
2. 在 console 中輸入`python ./manual_cutting.py`並執行
3. 輸入頁面檔案路徑，比如說`D:/50.png`
4. 輸入頁面編號，比如說`50`，這邊要正確，不然 Unicode 會是錯的！
5. 接下來會開啟一個視窗(沒的話應該會在底下工作列)，需要把整個字頁給框起來，可以參考底下的圖片！
    -  Console 會有說明
    -  按住右鍵會出現紅色輔助線，幫助對齊框線
    -  按住左鍵拖移會出現藍色選取框，把整個字都框起來
    -  確認藍色框 OK 後，按下任意鍵確認，程式就會開始切割
6. 最後如果沒有錯誤的話，會產生一個資料夾名為`Result_XXX`，XXX 為 Page 編號
7. 如果結果中還是有錯誤的話，再請手動修復，或是重新 RUN 整個流程
8. 完成後記得把所有分割後的字，複製並貼到自動分割後的資料夾`XXX_XXX`中(取代原先存在的)

如果頁面編號打錯，分割後的檔名就會錯誤(正確要 Unicode 對應檔名)

如果沒有對齊就會分割錯誤，請多加注意！

<img src="./ReadMeImage/example.png" width="700" title="選取範例圖片"/>


#### 去除污漬或強化色彩

如果一直分割錯誤(應該不太可能把...)，可以嘗試以下步驟：

1. 找出出錯檔案(可以用`find_word_page.py`來找頁面)
2. 使用各種工具把圖片強化色彩，或去除污漬已讓程式更好辨識
3. 再次執行程式，但開始以及結束 page 輸入錯誤檔案的名稱，如果錯誤檔案是`20.png`，則開始以及結束輸入`20`
    - 如果沒有錯誤的話`20_20`資料夾中的圖片就是最後結果(名稱會與錯誤檔案名稱相同)
    - 如果還是錯誤的話，再從第二步開始！
4. 回到第一步，繼續把其他錯誤檔案修復
