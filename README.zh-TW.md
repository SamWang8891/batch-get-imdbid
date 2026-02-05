# Batch Get IMDb ID

<img src="https://img.shields.io/badge/Version-v1.0-green">

一個桌面應用程式，用於批次取得電視劇的 IMDb 集數 ID — 非常適合用於整理媒體庫。

[Link for English version](README.md)

---

## 目錄 📖

- [特點 ✨](#特點-)
- [截圖 📸](#截圖-)
- [用法 🚀](#用法-)
    - [從原始碼執行 🐍](#從原始碼執行-)
    - [從 Release 執行 📦](#從-release-執行-)
- [自己建構 🛠](#自己建構-)
    - [事前準備 ✅](#事前準備-)
    - [建構 🚧](#建構-)
- [備註 📝](#備註-)
    - [已知的 Bug 🐛](#已知的-bug-)
- [問題 / Bugs? 🙋‍♀️](#問題--bugs-)

---

## 特點 ✨

厭倦了手動查詢每一集的 IMDb ID 嗎？這個工具幫你搞定！

- **批次取得**：貼上任何 IMDb 網址或 tt ID，即可取得整部影集的所有集數 ID。
- **自動複製模式**：按照設定的間隔自動逐一複製集數 ID — 非常適合搭配 metadata 工具使用。
- **季數選擇**：選擇要自動複製的季數。
- **反向順序**：可依需求以反向順序複製集數。
- **音效提示**：複製時可選擇播放音效回饋。
- **跨平台**：支援 macOS、Windows 和 Linux。
- **深色/淺色模式**：自動適應系統主題。

---

## 截圖 📸

<!-- 在此加入截圖 -->
<!-- <img src="readme-image/1.png" width="600" alt="Screenshot 1"> -->

---

## 用法 🚀

### 從原始碼執行 🐍

1. Clone 此 repository：
   ```bash
   git clone https://github.com/SamWang8891/batch-get-imdbid.git
   cd batch-get-imdbid
   ```

2. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```

3. 執行程式：
   ```bash
   python main.py
   ```

### 從 Release 執行 📦

1. 從 [Releases](https://github.com/SamWang8891/batch-get-imdbid/releases) 頁面下載適合您平台的版本。
2. 解壓縮並執行。

### 如何使用 🎯

1. 打開 IMDb 並找到您的電視劇 / 動漫。
2. 複製網址（或直接複製 tt ID，例如 `tt1234567`）。
3. 貼到程式中並點擊 **Fetch**。
4. 瀏覽集數 ID，或使用 **Auto Copy** 逐一複製。
5. 使用 **Copy All** 一次複製全部。

---

## 自己建構 🛠

### 事前準備 ✅

- Python >= 3.10
- 必要套件：`requests`、`beautifulsoup4`

### 建構 🚧

#### 使用 PyInstaller 📦

1. 安裝 PyInstaller：
   ```bash
   pip install pyinstaller
   ```

2. 建構執行檔：
   ```bash
   pyinstaller --onefile --windowed --add-data "sounds:sounds" main.py
   ```

3. 執行檔會在 `dist` 資料夾中。

---

## 備註 📝

### 音效檔案 🔊

音效檔案位於 `sounds` 資料夾：
- `copy_sound.mp3` — 每次自動複製時播放
- `done_sound.mp3` — 自動複製完成時播放

### 已知的 Bug 🐛

- 目前尚無回報。

---

## 問題 / Bugs? 🙋‍♀️

遇到問題或 Bug 嗎？歡迎在 Issues 回報並提交 Pull Requests。
