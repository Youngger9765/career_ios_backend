# 職涯諮詢平台 - 交付說明

## 📦 給案主及設計（產品面）

### 🌐 Staging 環境

**主頁**: https://career-app-api-staging-kxaznpplqq-uc.a.run.app/

### 功能展示區域

#### 1️⃣ 諮詢系統 Console
**URL**: https://career-app-api-staging-kxaznpplqq-uc.a.run.app/console

**功能**:
- ✅ 客戶管理（Clients）- 新增、查詢、編輯客戶資料
- ✅ 個案管理（Cases）- 建立個案、追蹤個案狀態
- ✅ 會談記錄（Sessions）- 上傳逐字稿、錄音片段
- ✅ 報告生成（Reports）- AI 自動生成職涯分析報告
- ✅ 多租戶隔離 - 每個組織獨立資料空間

**測試帳號**: （請聯繫技術團隊取得測試帳號）

#### 2️⃣ RAG 知識庫 Console
**URL**: https://career-app-api-staging-kxaznpplqq-uc.a.run.app/rag

**功能**:
- 📚 文件上傳與管理
- 🔍 知識庫向量搜尋測試
- 🤖 AI Agent 對話測試

---

## 👨‍💻 給 iOS 開發者（技術面）

### 🏢 重要概念：多租戶架構 (Multi-Tenancy)

#### 什麼是 Tenant ID？

本系統採用 **多租戶架構**，支援多個獨立組織同時使用同一套 API：

```
組織 A (tenant_id: "career")
  ├── 諮詢師 Alice, Bob, Carol
  └── 客戶 100 人

組織 B (tenant_id: "island")
  ├── 諮詢師 David, Eve
  └── 客戶 50 人
```

**租戶隔離保證**：
- ✅ 組織 A 的諮詢師只能看到組織 A 的客戶
- ✅ 組織 B 的諮詢師只能看到組織 B 的客戶
- ✅ 資料完全隔離，無法跨組織存取

#### iOS App 如何處理 Tenant ID？

**重要：前端不需要手動傳遞 `tenant_id`！**

1. **登入時取得 JWT Token**：
```swift
// 登入 API 回傳的 JWT Token 已包含 tenant_id
let response = try await api.login(email: "user@career.com", password: "***")
let jwtToken = response.access_token

// JWT Payload 內容（自動包含）：
// {
//   "sub": "user@career.com",
//   "tenant_id": "career",    // ⭐️ 後端自動加入
//   "role": "counselor",
//   "exp": 1234567890
// }
```

2. **每個 API 請求只需附加 JWT Token**：
```swift
var request = URLRequest(url: url)
request.addValue("Bearer \(jwtToken)", forHTTPHeaderField: "Authorization")

// ✅ 正確：只傳 JWT Token
// ❌ 不需要：額外傳遞 X-Tenant-ID header
```

3. **後端自動從 JWT 提取 `tenant_id`**：
```python
# 後端自動處理（iOS 開發者無需關心）
def get_tenant_id(current_user: Counselor = Depends(get_current_user)) -> str:
    return current_user.tenant_id  # 從 JWT 解析出來
```

#### 動態欄位配置（Field Schemas）

不同租戶可以有不同的表單欄位：

| 租戶 | 客戶欄位範例 |
|------|-------------|
| **職涯諮詢 (career)** | 學歷、職業、年資、職涯目標 |
| **大學輔導 (island)** | 學號、科系、年級、社團 |

**前端動態渲染表單**：
```swift
// 1. App 啟動時取得該租戶的欄位配置
let schema = try await api.getFieldSchema(type: "client")

// schema.tenant_id = "career"（自動對應當前登入使用者的組織）
// schema.sections = [各種欄位定義...]

// 2. 根據 schema 動態生成表單
for section in schema.sections {
    for field in section.fields {
        // 根據 field.type 生成對應 UI 元件
        switch field.type {
        case "text": createTextField(field)
        case "single_select": createPicker(field)
        // ...
        }
    }
}
```

**詳細說明**：參考 [`PRD.md`](https://github.com/Youngger9765/career_ios_backend/blob/staging/PRD.md) - 動態欄位 Schema 詳細說明章節

---

### 📚 開發文檔

**GitHub Repository**: https://github.com/Youngger9765/career_ios_backend

#### 主要文檔（根目錄）

1. **iOS API 完整指南** ⭐️ 必讀
   - 檔案: [`IOS_API_GUIDE.md`](https://github.com/Youngger9765/career_ios_backend/blob/staging/IOS_API_GUIDE.md)
   - 內容:
     - 完整 API 規格說明
     - Swift 程式碼範例
     - Sessions API（支援 recordings 錄音片段）
     - Reports API（含 Markdown 編輯）
     - 錯誤處理與認證

2. **客戶與個案管理 API**
   - 檔案: [`IOS_API_GUIDE.md`](https://github.com/Youngger9765/career_ios_backend/blob/staging/IOS_API_GUIDE.md)
   - 內容:
     - Clients CRUD API (Section 3)
     - Cases CRUD API (Section 4)
     - 動態欄位系統（Field Schemas - Section 2.3）
     - **多租戶（tenant_id）架構詳細說明** ⭐️

3. **動態欄位配置指南**
   - 檔案: [`PRD.md`](https://github.com/Youngger9765/career_ios_backend/blob/staging/PRD.md)
   - 內容:
     - Field Schemas 概述與欄位類型
     - Tenant 配置差異（Career vs Island）
     - iOS Swift 類型對照表

4. **專案 README**
   - 檔案: [`README.md`](https://github.com/Youngger9765/career_ios_backend/blob/staging/README.md)
   - 內容: 專案架構、快速開始、資料庫設計

### 🔗 Staging API URLs

**Base URL**: `https://career-app-api-staging-kxaznpplqq-uc.a.run.app`

#### 互動式 API 文檔

1. **Swagger UI** (推薦測試 API)
   - https://career-app-api-staging-kxaznpplqq-uc.a.run.app/docs
   - 可直接測試 API 請求
   - 查看完整 Request/Response Schema

2. **ReDoc** (查閱文檔)
   - https://career-app-api-staging-kxaznpplqq-uc.a.run.app/redoc
   - 更適合閱讀的文檔格式

3. **OpenAPI JSON** (匯入到 Postman/Insomnia)
   - https://career-app-api-staging-kxaznpplqq-uc.a.run.app/openapi.json

### 🚀 快速開始（iOS 開發）

#### Step 1: 查看 API 文檔
```bash
# 在瀏覽器開啟 Swagger UI
open https://career-app-api-staging-kxaznpplqq-uc.a.run.app/docs
```

#### Step 2: 閱讀 iOS API 指南
```bash
# Clone repository
git clone https://github.com/Youngger9765/career_ios_backend.git
cd career_ios_backend

# 閱讀主要文檔
cat IOS_API_GUIDE.md
```

#### Step 3: 實作 Swift Models

**RecordingSegment** (錄音片段):
```swift
struct RecordingSegment: Codable {
    let segment_number: Int
    let start_time: String        // "2024-11-19 10:00:00"
    let end_time: String          // "2024-11-19 10:05:00"
    let duration_seconds: Int     // 300
    let transcript_text: String
    let transcript_sanitized: String?
}
```

**SessionCreateRequest** (建立會談):
```swift
struct SessionCreateRequest: Codable {
    let case_id: UUID
    let session_date: String      // "2024-11-19"
    let recordings: [RecordingSegment]?  // ⭐️ 新功能：分段錄音
    let transcript: String?              // 或直接傳完整逐字稿
    let notes: String?
}
```

#### Step 4: 認證流程

所有 API 請求需包含 JWT Token:
```swift
var request = URLRequest(url: url)
request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
```

### 📋 核心 API Endpoints

| 功能 | Method | Endpoint |
|------|--------|----------|
| 取得客戶列表 | GET | `/api/v1/clients` |
| 建立客戶 | POST | `/api/v1/clients` |
| 取得個案列表 | GET | `/api/v1/cases` |
| 建立個案 | POST | `/api/v1/cases` |
| 建立會談 | POST | `/api/v1/sessions` |
| 更新會談 | PATCH | `/api/v1/sessions/{id}` |
| 生成報告 | POST | `/api/v1/reports/generate` |
| 編輯報告 | PATCH | `/api/v1/reports/{id}` |

### ⭐️ 最新功能：Recordings 錄音片段

**特色**:
- iOS App 可分段上傳錄音逐字稿
- 後端自動聚合成完整 transcript
- 支援顯示錄音時間軸

**使用方式**:
```swift
// 方式 1：上傳多段錄音逐字稿（推薦）
let recordings = [
    RecordingSegment(segment_number: 1, start_time: "10:00", ...),
    RecordingSegment(segment_number: 2, start_time: "10:05", ...)
]
let request = SessionCreateRequest(case_id: caseId, recordings: recordings)

// 方式 2：直接上傳完整逐字稿（傳統）
let request = SessionCreateRequest(case_id: caseId, transcript: fullText)
```

### 🔄 報告編輯功能

支援前端編輯 Markdown 格式報告：
```swift
// 更新報告 Markdown
struct ReportUpdateRequest: Codable {
    let edited_content_markdown: String
}

// PATCH /api/v1/reports/{reportId}
```

詳細範例見: `IOS_API_GUIDE.md` 第 8 節

---

## 📞 聯絡資訊

- **技術支援**: [填入聯絡方式]
- **GitHub Issues**: https://github.com/Youngger9765/career_ios_backend/issues
- **API 問題**: 在 Slack 頻道提出或開 GitHub Issue

---

## ✅ 檢查清單（iOS 開發開始前）

### 核心概念理解
- [ ] 已理解多租戶架構（Multi-Tenancy）
- [ ] 已理解 JWT Token 包含 `tenant_id`
- [ ] 已理解前端不需手動傳遞 `tenant_id`
- [ ] 已理解動態欄位配置（Field Schemas）

### 文檔閱讀
- [ ] 已閱讀 `HANDOFF_GUIDE.md` 多租戶架構說明
- [ ] 已閱讀 `IOS_API_GUIDE.md`（完整 API 技術文件）
- [ ] 已閱讀 `PRD.md` 動態欄位 Schema 章節

### 開發準備
- [ ] 已測試 Swagger UI 各 API
- [ ] 已取得測試用 JWT Token
- [ ] 已實作 Swift Models（RecordingSegment, SessionRequest, FieldSchema 等）
- [ ] 已實作動態表單渲染邏輯
- [ ] 已測試認證流程
- [ ] 已測試 Recordings 上傳功能
- [ ] 已測試 Field Schemas API

---

**最後更新**: 2024-11-19
**API 版本**: v0.1.0
**環境**: Staging (production-ready)
