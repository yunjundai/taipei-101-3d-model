# Taipei 101 3D Model

參數化建構之台北 101（Taipei 101）3D 建築模型，提供多種標準 3D 格式與獨立互動式網頁檢視器。

## 線上互動預覽

- [開啟 3D 建築與工程解說動畫（含台灣女聲旁白）](https://yunjundai.github.io/taipei-101-3d-model/)（或直接開啟 [explainer.html](https://yunjundai.github.io/taipei-101-3d-model/explainer.html)）
- [開啟純 3D 模型互動檢視器](https://yunjundai.github.io/taipei-101-3d-model/viewer.html)

## 檔案清單

- `explainer.html`：內嵌 GLB 與台灣女性神經語音旁白（`zh-TW-HsiaoChenNeural`）之 7 章節 3D 解說動畫網頁
- `build_explainer.py`：封裝 `explainer.html` 之建置腳本
- `generate_narration.py` / `narration/`：台灣女性神經語音合成腳本與 7 章節 MP3 旁白音檔
- `taipei_101.glb`：glTF 2.0 二進位模型（含 7 組 PBR 材質）
- `taipei_101.obj` / `taipei_101.mtl`：通用 3D 網格與材質定義檔
- `taipei_101.stl`：Z 軸朝上之二進位 STL 檔（適用 CAD 與 3D 列印）
- `generate_taipei_101.py`：純 Python 參數化建模腳本（無外部套件相依）
- `viewer.html`：內嵌 GLB 之 Three.js 互動式 3D 檢視器（雙擊即可自動載入）

## 模型規格

- **比例**：1 單位 = 1 公尺
- **總高度**：508.25 m（對應實際高度 508.2 m）
- **網格數量**：53,868 個頂點、17,956 個三角形
- **建築特徵**：階梯式基地廣場、東側購物中心裙樓、26F 四面古銅錢裝飾、8 節 W 型鋸齒轉角竹節塔身、8 根外露巨柱、如意裝飾、91F 至 101F 頂部收頭與塔尖警示燈

## 重新生成模型

```bash
python generate_taipei_101.py
```
