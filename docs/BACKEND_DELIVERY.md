# Backend 交付文件

> **日期**: 2026-01-26
> **Backend 負責人**: Young
> **專案**: Island Parents (浮島親子) iOS App

---

## 📋 目錄

1. [Backend 總需求清單](#1-backend-總需求清單)
2. [Web 可測試項目](#2-web-可測試項目)
3. [API 可串接項目](#3-api-可串接項目)
4. [完整文件位置](#4-完整文件位置)

---

## 1. Backend 總需求清單

### 📊 本週重點總覽

| 項目 | 狀態 | 優先級 | 說明 |
|------|------|--------|------|
| **即時情緒分析 API** | ✅ 已上線 | 🟢 本週完成 | iOS 可以串接 |
| **註冊 API 簡化** | ✅ 已上線 | 🟢 已上線 | 只需 email + password，iOS 需更新 UI |
| **忘記密碼 Web 流程** | ✅ 已完成 | 🟢 已上線 | iOS 導出到 Web，PM 可直接從 Web 測試 |
| **Landing Page** | ✅ 已完成 | 🟢 已上線 | https://career-app-api-staging-978304030758.us-central1.run.app/ |
| **Terms/Privacy 網頁** | ✅ 已完成 | 🟢 本週完成 | 已上線基礎版本，PM 可隨時更新文案（見 1.5 節）|
| **專屬網域** | 🟡 待PM決策 | 🔵 非緊急 | 中期改善品牌形象（PM申請網域後，Backend協助DNS設定）|
| **Support 信箱** | ✅ 基礎建設完成 | 🔵 非緊急 | 等PM申請網域後，換 email 環境變數即可 |

---

### ✅ 本週已完成項目

#### 1.1 註冊 API 簡化 ✅

**會議金句**：「我只要 email 跟密碼就好。」

**新版規格**（已部署到 Staging）：

```json
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "password123",
  "tenant_id": "island_parents"
}

// ❌ 已移除欄位：username, full_name
// 💾 資料庫保留欄位結構（未來可擴充）
```


---

#### 1.2 忘記密碼 Web 流程 ✅

**會議決議**：「走 Web 方案，降低 App 開發量」

**完整流程**：
1. 用戶在 App 點「忘記密碼」
2. **iOS 導出到 Web**：App 開啟 WebView/Safari 到 `https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/forgot-password`
3. 用戶輸入 Email → Backend 寄重設郵件
4. 用戶收信 → 點連結到 Web 設定新密碼
5. 設定完成 → 返回 App 用新密碼登入

**iOS 實作**：
- iOS 只需放 link 導出到 Web 即可
- 不需要在 App 內實作密碼重設 UI

**PM 測試**：
- **可直接從 Web 測試**（不需要等 iOS App）
- 測試方式見「2. Web 可測試項目」

---

### 🔵 中期規劃（非緊急阻塞）

#### 1.3 Landing Page ✅

**用途**：
- 品牌形象展示
- 配合專屬網域使用
- 作為 Terms/Privacy 的母頁面

**狀態**：✅ 已完成上線

**Staging URL**：
```
https://career-app-api-staging-978304030758.us-central1.run.app/
```

**內容**：
- Hero Section（浮島親子介紹）
- 3 個特色功能卡片
- App Store 下載 CTA
- 快速連結（登入、忘記密碼）

---

#### 1.4 專屬網域 + Support 信箱

**會議討論**：「需要可信賴的網域與寄信來源」

**目前狀況**：
- **寄件者**：`noreply@groovy-iris-473015-h3.iam.gserviceaccount.com`
- **問題**：看起來像垃圾郵件，可能被標記為 spam

---

**專屬網域**：
- **狀態**：🟡 等待 PM (KM) 申請
- **Backend 協助**：DNS 設定（指向 Cloud Run）

**PM 待辦**：
- [ ] 決定購買哪個網域
- [ ] 完成網域註冊
- [ ] 提供網域名稱給 Backend

---

**Support 信箱**：
- **狀態**：✅ Backend 基礎建設已完成
- **目前設定**：使用 email 環境變數控制
- **切換方式**：PM 申請網域後，Backend 只需更新 email 環境變數即可
- **建議格式**：`support@{網域}` 或 `hello@{網域}`

**Backend 工作**：
- ✅ 郵件發送系統已建置完成
- ⏳ 等待 PM 提供新的 support email 設定

---

**建議時程**：
- **短期（本週）**：先用現有 Cloud Run URL + 現有寄件者
- **中期（1 個月內）**：購買網域 + 切換專業信箱（換環境變數）
- **長期**：持續優化品牌形象

---

#### 1.5 Terms of Service & Privacy Policy 網頁 ✅

**會議背景**：「Paywall 需要 **Terms / Privacy URL** 才能上架」

**狀態**：✅ 已完成（基礎版本上線）

**已完成項目**：
- ✅ 建立 Terms of Service 網頁（簡潔法律文件風格）
- ✅ 建立 Privacy Policy 網頁（符合個資法規範）
- ✅ 實作置頂目錄導航（桌面 + 手機響應式）
- ✅ 提供完整 URL 給 iOS 團隊整合至 RevenueCat

---

**正式 URL**（Staging 環境）：

```
Terms:   https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/terms
Privacy: https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/privacy
```

**Production URL**（Firebase Hosting）：
```
Terms:   https://island-parents-app.web.app/island-parents/terms
Privacy: https://island-parents-app.web.app/island-parents/privacy
```

---

**目前文案狀態**：
- ✅ 使用通用法律條款基礎文案（符合 App Store 審核要求）
- 📝 PM 可隨時提供客製化文案，Backend 只需更新 HTML 模板即可
- 🔄 支援快速更新（無需重新部署，只需編輯模板檔案）

**文案更新方式**：
1. PM 提供最終條款文案（Word / Notion / Markdown）
2. Backend 更新 `app/templates/island_parents/terms.html`
3. Backend 更新 `app/templates/island_parents/privacy.html`
4. 立即生效（無需重新部署）

---

**設計特色**：
- 📱 **響應式設計**：桌面 + 手機完美適配
- 📑 **置頂目錄導航**：快速跳轉到特定條款段落
- 🎯 **簡潔法律風格**：專業、易讀、符合 Apple/Google 審核標準
- ✨ **平滑捲動**：提升閱讀體驗
- 🔗 **獨立頁面**：Terms 和 Privacy 各自獨立（RevenueCat 要求）

---

## 2. Web 可測試項目

### 🌐 Staging 環境

**Base URL**: `https://career-app-api-staging-978304030758.us-central1.run.app`

---

### ⭐ 2.1 忘記密碼流程（完整體驗）- PM 必測

**測試目標**：像真實用戶一樣體驗完整的密碼重設流程

**準備工作**：
- 先註冊一個測試帳號（Email 要能收信）
- 建議用自己的 Email：`你的名字@gmail.com`

---

#### 步驟 1：打開忘記密碼頁面

**URL**：
```
https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/forgot-password
```

**預期畫面**：顯示「忘記密碼」標題 + Email 輸入框

---

#### 步驟 2：輸入 Email 並送出

- 輸入你的測試帳號 Email
- 點擊「發送重設郵件」按鈕
- **預期畫面**：「已發送重設郵件，請檢查信箱」

---

#### 步驟 3：收信

- 打開你的信箱（Gmail/Outlook）
- 等待 1-2 分鐘
- 找到主旨：「Island Parents 密碼重設」
- ⚠️ **如果沒看到**：檢查垃圾郵件（spam）資料夾

---

#### 步驟 4：點擊重設連結

- 點擊信中的「重設密碼」連結
- 應該自動開啟重設密碼頁面（帶 token 參數）
- **預期畫面**：「設定新密碼」表單

---

#### 步驟 5：設定新密碼

- 輸入新密碼（至少 8 個字元）
- 再次輸入確認密碼
- 點擊「重設密碼」按鈕
- **預期畫面**：「密碼已重設，請用新密碼登入」

---

#### 步驟 6：驗證新密碼可用

- 回到登入頁面（iOS App 或 Swagger UI）
- 使用新密碼登入
- ✅ **成功登入 = 測試通過**

---

**⚠️ 已知問題（中期改善）**：

| 問題 | 說明 | 解決方案 |
|------|------|---------|
| 寄件者顯示 | 目前使用 Gmail 或 GCP 預設信箱 | PM 申請網域後，Backend 換 `FROM_EMAIL` 環境變數即可 |
| 信任感低 | 建議使用專業信箱（如 `noreply@{網域}`） | 購買專屬網域 + 設定專業 support 信箱（見 1.4 節）|

---

## 3. API 可串接項目

### 3.1 本週變更：註冊 API 簡化 ⚠️

**變更對比**：

```json
// ❌ 舊版（已停用）
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "password123",
  "username": "username",      // 已移除
  "full_name": "Full Name",    // 已移除
  "tenant_id": "island_parents"
}

// ✅ 新版（目前使用）
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "password123",
  "tenant_id": "island_parents"
}
```


---

### 3.2 忘記密碼（Web 流程）

| 功能 | 方式 | 完整 URL |
|------|------|----------|
| **忘記密碼頁面** | iOS 開啟 WebView/Safari | `https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/forgot-password` |
| **重設密碼頁面** | 用戶點信中連結自動開啟 | `https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/reset-password?token=...` |

**優點**：
- ✅ iOS 不需實作密碼重設 UI
- ✅ 只需放 link 導出到 Web 即可
- ✅ PM 可直接從 Web 測試（不需等 iOS App）

---

### 3.3 即時情緒分析 API - 串接說明 ⭐

**端點**：`POST /api/v1/sessions/{session_id}/emotion-feedback`

**用途**：即時分析家長說話的情緒層級（紅黃綠燈），並提供簡短引導語

**回應時間**：< 3 秒（實測約 0.5 秒）

---

#### Request 格式

```json
POST /api/v1/sessions/{session_id}/emotion-feedback
Authorization: Bearer {token}
Content-Type: application/json

{
  "context": "小明：我今天考試不及格\n媽媽：你有認真準備嗎？",
  "target": "你就是不用功！"
}
```

**參數說明**：
- `context` (string, required): 對話上下文（可包含多輪對話）
- `target` (string, required): 要分析的目標句子（家長剛說的話）

---

#### Response 格式

```json
{
  "level": 3,
  "hint": "試著同理孩子的挫折感"
}
```

**欄位說明**：
- `level` (int): 情緒層級
  - `1` = 🟢 綠燈：良好溝通，語氣平和、具同理心
  - `2` = 🟡 黃燈：警告，語氣稍顯急躁但未失控
  - `3` = 🔴 紅燈：危險，語氣激動、可能傷害親子關係
- `hint` (string): 引導語，最多 17 字，具體、可行、同理

---

#### 使用時機

**呼叫時機**：每次家長說完話後（語音轉文字完成時）

**流程**：
1. 家長說話 → 語音轉文字完成
2. 呼叫 Emotion API 分析最新語句
3. 根據 `level` 顯示對應顏色燈號
4. 顯示 `hint` 引導語

**iOS 端流量控制**（參考 Notion 規格）：
- 綠燈狀態：每 7 秒最多呼叫一次
- 黃燈升級後：9 秒內不會再呼叫
- 紅燈升級後：11 秒內不會再呼叫
- 鎖定期結束後：立即用最新逐字稿再呼叫一次

---

#### 錯誤處理

| 狀態碼 | 說明 | 處理方式 |
|--------|------|---------|
| 200 | 成功 | 顯示結果 |
| 400 | Request 格式錯誤 | 檢查 context/target 是否為空 |
| 401 | 未授權 | 重新登入 |
| 404 | Session 不存在 | 檢查 session_id |
| 500 | 伺服器錯誤 | 顯示預設提示「請稍後再試」 |

---

### 3.4 其他核心 API（已完成，可規劃串接）

以下 API **已開發完成**，iOS 可參考完整文件規劃串接時程：

| API | 端點 | 用途 | 回應時間要求 |
|-----|------|------|-------------|
| **深度分析** | `POST /api/v1/sessions/{id}/deep-analyze` | 完整安全評估 | < 10 秒 |
| **快速回饋** | `POST /api/v1/sessions/{id}/quick-feedback` | 15 秒間隔回饋 | ≥ 5 秒 |
| **報告生成** | `POST /api/v1/sessions/{id}/report` | 完整對話報告 | < 30 秒 |
| **Session 管理** | `POST /api/v1/sessions` | 建立對話 session | - |
| **Client-Case 管理** | `POST /api/v1/ui/client-case` | 建立孩子檔案 | - |
| **ElevenLabs Token** | `POST /api/v1/transcript/elevenlabs-token` | 語音轉文字 token | - |

**詳細規格**：見「4. 完整文件位置」

---

## 4. 完整文件位置

### 📚 iOS 開發文件

#### 4.1 IOS_GUIDE_PARENTS.md（主要文件）

**GitHub 位置**：
```
https://github.com/Youngger9765/career_ios_backend/blob/staging/IOS_GUIDE_PARENTS.md
```

**文件內容**：
- ✅ 完整 API 規格（Request/Response 範例）
- ✅ Swift 程式碼範例
- ✅ 認證流程說明
- ✅ 錯誤處理指南
- ✅ 測試帳號資訊
- ✅ Staging 環境設定
- ✅ 所有分析 API 詳細說明（Emotion、Deep、Quick Feedback、Report）

**版本**：v1.10（最後更新：2026-01-25）

---

### 🔧 API 互動式文件

#### 4.2 Swagger UI（推薦 iOS 工程師使用）

**URL**：
```
https://career-app-api-staging-978304030758.us-central1.run.app/docs
```

**功能**：
- ✅ 互動式 API 測試介面
- ✅ Try it out 功能（直接測試 API）
- ✅ 自動生成 Request/Response 範例
- ✅ 即時查看 API 回應

**使用方式**：
1. 打開 Swagger UI
2. 展開想測試的 API endpoint
3. 點擊「Try it out」
4. 填入參數
5. 點擊「Execute」查看結果

---

#### 4.3 ReDoc（API 文件閱讀）

**URL**：
```
https://career-app-api-staging-978304030758.us-central1.run.app/redoc
```

**功能**：
- ✅ 清晰的 API 文件瀏覽介面
- ✅ 完整的 schema 定義
- ✅ 搜尋功能
- ✅ 適合閱讀與參考

---

### 📝 其他重要文件

| 文件 | 位置 | 說明 |
|------|------|------|
| **CHANGELOG** | `CHANGELOG.md` | 版本更新記錄（所有 API 變更歷史）|
| **PRD** | `PRD.md` | 產品需求文件 |
| **即時情緒分析規格** | [Notion 文件](https://www.notion.so/Backend-2f10a9aee1968038ae29ec11d74b0ba2) | 完整 API 規格與 Prompt 設計 |
| **本文件** | `docs/BACKEND_DELIVERY.md` | Backend 交付文件 |

---

### 🔗 快速連結總覽

**Web 測試頁面**：
- 忘記密碼：https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/forgot-password

**API 文件**：
- Swagger UI：https://career-app-api-staging-978304030758.us-central1.run.app/docs
- ReDoc：https://career-app-api-staging-978304030758.us-central1.run.app/redoc

**完整規格**：
- iOS 開發指南：`IOS_GUIDE_PARENTS.md`
- CHANGELOG：`CHANGELOG.md`
- PRD：`PRD.md`

---

**最後更新**: 2026-01-27
**文件版本**: v2.3
**下次更新**: Terms/Privacy 內容到位後

