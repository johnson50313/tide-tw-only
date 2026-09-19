# Tide 潮汐｜GitHub 免費雲端部署與自動化排程指南

本專案可 **100% 免費** 部署至 GitHub Pages，並透過 GitHub Actions 於每個台股交易日盤後（16:30）自動抓取證交所與櫃買中心的三大法人買賣超數據，自動運算四象限指標並更新網頁！

---

## 🚀 三步驟快速部署

### 步驟 1：在 GitHub 建立新倉庫（Repository）
1. 登入 [GitHub](https://github.com/)。
2. 點擊右上角 **「+」** $\rightarrow$ **「New repository」**。
3. 輸入倉庫名稱（例如：`tide-tw`）。
4. 選擇 **Public**（公開，享有 GitHub Actions 無限制免費額度）或 **Private**。
5. **不要**勾選 "Add a README file" 或 ".gitignore"（本地已有完整檔案）。
6. 點擊 **「Create repository」**。

---

### 步驟 2：將本地專案推送到 GitHub
在您的本地終端機（PowerShell 或 CMD）中執行以下指令（將 `<your-username>` 替換為您的 GitHub 帳號）：

```powershell
cd d:\Users\LICI\Desktop\t\tide-tw

# 初始化 Git 倉庫（若尚未初始化）
git init
git branch -M main

# 新增所有檔案並提交
git add .
git commit -m "feat: initial commit for Tide Taiwan Stock Flow Visualizer"

# 設定遠端倉庫並推送
git remote add origin https://github.com/<your-username>/tide-tw.git
git push -u origin main
```

---

### 步驟 3：在 GitHub 設定頁開啟 GitHub Pages
1. 進入您剛建立的 GitHub 倉庫頁面。
2. 點擊頂部分頁 **「Settings」**（設定）。
3. 在左側選單點擊 **「Pages」**。
4. 在 **「Build and deployment」** 下方的 **「Source」** 下拉選單中：
   - 選擇 **「GitHub Actions」**。
5. 完成！接下來每次推送程式碼或每日排程觸發時，GitHub Actions 都會自動建置並發布網站。

> 💡 **您的專屬網址將會是**：
> `https://<your-username>.github.io/tide-tw/`

---

## ⚙️ 自動化排程說明

在 `.github/workflows/deploy.yml` 中已配置以下自動化機制：

1. **定時自動更新（Cron）**：
   - 設定為每週一至週五 `UTC 08:30`（**台灣時間 16:30**，此時三大法人盤後籌碼數據均已完整公告）。
   - 自動執行 `python -m pipeline.run --mode incremental`。
   - 自動將新資料提交回倉庫並更新 GitHub Pages。
2. **手動一鍵觸發（Workflow Dispatch）**：
   - 在 GitHub 倉庫的 **「Actions」** 分頁 $\rightarrow$ 點擊 **「Update Data & Deploy to GitHub Pages」** $\rightarrow$ **「Run workflow」**，即可隨時手動抓取最新數據並發布。
3. **推動即部署（Push to Main）**：
   - 只要您修改前端介面或演算法並 `git push`，系統會自動跑測試並立即更新上線。

---

## 🔒 隱私與安全性
- 本專案僅使用公開市場行情資料（證交所與櫃買中心官網 API），無須任何付費 API Key 或私密憑證。
- 自選股與自選板塊（Watchlist）及深淺色主題偏好均儲存在使用者的瀏覽器 `localStorage` 中，不同裝置各自獨立且完全注重隱私。
