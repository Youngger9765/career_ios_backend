# iOS App API 完整指南

**Base URL (Staging):** `https://your-api-staging.example.com`

**Base URL (Local):** `http://localhost:8080`

> 🔒 **注意**: Staging URL 請向技術團隊索取

**認證方式:** Bearer Token (JWT)

---

## 📋 目錄

0. [App Config API (動態配置)](#app-config-api-動態配置) ⭐️ NEW
1. [island_parents (親子版) 完整操作指南](#island_parents-親子版-完整操作指南-new) ⭐️ NEW
2. [認證 APIs](#認證-apis) (0-3)
3. [個案管理 APIs](#個案管理-apis) (4-9)
4. [會談記錄管理 APIs](#會談記錄管理-apis) (10-17)
5. [諮詢師反思 APIs](#諮詢師反思-apis) (18-19)
6. [報告 APIs](#報告-apis) (20-24)
7. [完整使用流程](#完整使用流程)
8. [錯誤處理](#錯誤處理)

---

## App Config API (動態配置)

**端點:** `GET /api/v1/app/config/{tenant}`

**認證:** 🔓 無需認證（公開端點）

**用途:** 讓 iOS 端動態獲取各種 URL 連結，無需硬編碼

**支援的租戶（tenants）:**
- `island_parents` - 浮島親子版
- `career` - 職涯諮詢版（未來）

### Request

```http
GET /api/v1/app/config/island_parents
```

### Response 200 OK

```json
{
  "terms_url": "https://www.comma.study/island_parents_terms_of_service/",
  "privacy_url": "https://www.comma.study/island_parents_privacy_policy/",
  "landing_page_url": "https://www.comma.study/island_parents_landing/",
  "data_usage_url": "https://www.comma.study/island_parents_data_usage/",
  "help_url": "https://www.comma.study/island_parents_help/",
  "faq_url": "https://www.comma.study/island_parents_faq/",
  "contact_url": "https://www.comma.study/island_parents_contact_us/"
}
```

### Response 404 Not Found (無效租戶)

```json
{
  "type": "https://api.career-counseling.app/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Tenant 'invalid_tenant' not found",
  "instance": "/api/v1/app/config/invalid_tenant"
}
```

### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `terms_url` | string | 服務條款頁面 URL |
| `privacy_url` | string | 隱私權政策頁面 URL |
| `landing_page_url` | string | Landing Page / 行銷頁面 URL |
| `data_usage_url` | string | 資料使用說明頁面 URL |
| `help_url` | string | 使用指南 / Help Center URL |
| `faq_url` | string | 常見問題 (FAQ) 頁面 URL |
| `contact_url` | string | 聯絡我們頁面 URL |

### 使用場景

1. **App 啟動時**
   - 呼叫此 API 獲取最新 URLs
   - 儲存在 UserDefaults，供後續使用

2. **顯示法律頁面**
   - 使用 `terms_url` 和 `privacy_url` 在 WebView 中顯示

3. **導向 Landing Page**
   - 使用 `landing_page_url` 導向官網 / 行銷頁面

4. **App 設定頁面**
   - **資料使用說明**: 使用 `data_usage_url`
   - **使用指南**: 使用 `help_url`
   - **FAQ**: 使用 `faq_url`
   - **聯絡我們**: 使用 `contact_url`

5. **WebView 顯示支援頁面**
   - 所有 URL 都可在 WebView 中顯示

### 優點

- ✅ **無需發版更新 URL** - 後端動態配置即可
- ✅ **支援多租戶** - 不同版本（island_parents/career）使用不同配置
- ✅ **支援 A/B Testing** - 可測試不同 URL
- ✅ **統一管理** - 所有外部連結集中在一個 API
- ✅ **清晰易讀** - 使用標準化的 URL 路徑命名 (`/island_parents_*`)

---

## 🎉 最新更新 (2025-12-15) ⭐️ NEW

### 0. 🔐 註冊功能 (Register API)

**新增 API:** `POST /api/auth/register`

**功能說明:**
- 支援新諮詢師註冊帳號
- 註冊後自動登入並返回 JWT token
- 支援多租戶（email + tenant_id 唯一性）
- 自動檢查 username 和 email+tenant_id 的唯一性

**使用場景:**
- 首次使用系統時註冊新帳號
- 註冊成功後可直接使用返回的 token 進行後續操作

**詳細文件:** 請參閱本文件「認證 APIs」章節

---

## 🎉 最新更新 (2025-11-29)

### 1. 🔍 Session 片段分析 APIs（Multi-Tenant）

**新功能:** 即時逐字稿片段分析 + 多租戶格式支援 + 分析歷程記錄管理

**新增 API:**
- `POST /api/v1/sessions/{id}/analyze-partial` - AI 驅動的即時片段分析（推薦使用）
- `POST /api/v1/sessions/{id}/analyze-keywords` - 舊版 API（向後兼容，內部調用 analyze-partial）
- `GET /api/v1/sessions/{id}/analysis-logs` - 取得分析歷程記錄
- `DELETE /api/v1/sessions/{id}/analysis-logs/{log_index}` - 刪除特定分析記錄

**Multi-Tenant 支援:**
- **island_parents 租戶**: 回傳紅黃綠燈安全評估 + 教養建議 + 建議間隔時間
- **career 租戶**: 回傳關鍵字 + 類別 + 諮詢師洞見

**Session Name 欄位:**
- Session 模型新增 `name` 欄位（可選），用於會談命名組織

**自動儲存:**
- 呼叫 analyze-partial/analyze-keywords 時，分析結果自動儲存至 `analysis_logs` 欄位
- 記錄包含：時間戳記、關鍵字、類別、信心分數、諮詢師洞見、AI/備援標記

**詳細文件:** 請參閱本文件「片段分析 APIs」章節

---

## 🎉 最新更新 (2025-11-23)

### 0. 🎨 動態表單 Schema API 優化 ⭐️ NEW

**問題:** iOS 需要兩次 API 調用才能獲取 Client 和 Case 的表單 Schema

**解決:** 新增組合端點，一次返回兩個 Schema

**新增 API:**
- `GET /api/v1/ui/field-schemas/client-case` - 一次獲取 Client + Case schemas（推薦）
- `GET /api/v1/ui/field-schemas/client` - 單獨獲取 Client schema
- `GET /api/v1/ui/field-schemas/case` - 單獨獲取 Case schema
- `GET /api/v1/ui/client-case/{id}` - 獲取單一個案完整資訊（用於更新表單）

**路徑變更:**
- ~~`/api/v1/field-schemas/*`~~ → `/api/v1/ui/field-schemas/*` (統一UI API前綴)

**Case Status 變更:**
- ~~字串enum~~ → **整數** (0=未開始, 1=進行中, 2=已完成)

**詳細文件:** 請參閱本文件「動態表單 Schema APIs」章節

---

### 1. ✅ Bruno HTTP Client OpenAPI 範例修正

**問題:** 之前在 Bruno 中查看 OpenAPI 文件時，`recordings` 欄位的範例顯示為空字串。

**解決:** 已在 Pydantic schema 中添加 `model_config` 和 `json_schema_extra.examples`，現在 OpenAPI 文件會正確顯示範例：

```json
{
  "recordings": [
    {
      "segment_number": 1,
      "start_time": "2025-01-15 10:00",
      "end_time": "2025-01-15 10:30",
      "duration_seconds": 1800,
      "transcript_text": "諮詢師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
      "transcript_sanitized": "諮詢師：今天想聊什麼？\n個案：我最近對未來感到很迷惘..."
    }
  ]
}
```

**影響範圍:**
- `POST /api/v1/sessions` - 建立會談記錄
- `POST /api/v1/sessions/{id}/recordings/append` - 添加錄音片段

**Bruno 使用:** 重新 import OpenAPI spec 即可看到完整範例。

---

### 2. 🎙️ iOS 友善的錄音片段 Append API

**新增 API:** `POST /api/v1/sessions/{session_id}/recordings/append`

**為什麼需要這個 API?**
- ✅ 自動計算 `segment_number`，iOS 無需追蹤
- ✅ 自動聚合所有片段的逐字稿
- ✅ 支援會談中斷後繼續錄音
- ✅ 樂觀鎖保護，避免並發衝突

**使用範例:**
```bash
POST https://duotopia-staging-backend-b2ovkkgl6a-de.a.run.app/api/v1/sessions/{session_id}/recordings/append
Authorization: Bearer {token}
Content-Type: application/json

{
  "start_time": "2025-01-15 10:00",
  "end_time": "2025-01-15 10:30",
  "duration_seconds": 1800,
  "transcript_text": "此片段的逐字稿內容...",
  "transcript_sanitized": "脫敏後的內容（選填）"
}
```

**詳細文件:** 請參閱本文件第 15 節「🎙️ Append 錄音片段」

---

### 3. 🆕 個案管理 UI API (JSON - iOS 使用)

⚠️ **重要：iOS 只使用 JSON API**

❌ **已移除的 HTML 路由（不要使用）:**
- `/client-case-list` - 已移除
- `/create-client-case` - 已移除

✅ **正確的 JSON API 端點（iOS 使用）:**

#### 📋 列出個案（Read）
```http
GET /api/v1/ui/client-case-list?skip=0&limit=20
Authorization: Bearer {token}
```
返回：JSON（個案列表 + 客戶資訊 + 會談次數）

#### ➕ 創建個案（Create）
```http
POST /api/v1/ui/client-case
Authorization: Bearer {token}
Content-Type: application/json
```
返回：JSON（新創建的個案和客戶 ID）

#### 🔍 個案詳情（Read）
```http
GET /api/v1/ui/client-case/{case_id}
Authorization: Bearer {token}
```
返回：JSON（個案 + 客戶 + 會談列表）

#### 🗑️ 刪除個案（Delete）
```http
DELETE /api/v1/ui/client-case/{case_id}
Authorization: Bearer {token}
```

**測試工具:**
- 訪問 `/console` 查看所有 API 的 Web 測試界面（僅用於測試，iOS 不調用）
- 訪問 `/docs` 查看完整 OpenAPI 文檔

**注意:** 這些是 Web UI 介面，iOS App 應使用對應的 REST API：
- `POST /api/v1/clients` - 建立個案
- `POST /api/v1/cases` - 建立 Case
- `GET /api/v1/clients` - 列出個案
- `GET /api/v1/cases` - 列出 Cases

---

### 4. 🏥 客戶個案管理 CRUD API

**完整的 CRUD 四個操作:**

#### 📊 列出客戶個案 (Read)
```
GET https://duotopia-staging-backend-b2ovkkgl6a-de.a.run.app/api/v1/ui/client-case-list?skip=0&limit=20
```
- 一次取得 Client + Case + Session 資訊
- 顯示每個客戶的第一個 Case
- 包含最後諮詢日期和總會談次數
- 支援分頁 (skip, limit)

**回應範例:**
```json
{
  "total": 10,
  "items": [
    {
      "client_id": "uuid",
      "case_id": "uuid",
      "client_name": "張小明",
      "client_code": "C0001",
      "client_email": "test@example.com",
      "identity_option": "轉職者",
      "current_status": "正在考慮轉職",
      "case_number": "CASE0001",
      "case_status": "active",
      "case_status_label": "進行中",
      "last_session_date_display": "2025/01/22 19:30",
      "total_sessions": 5
    }
  ]
}
```

---

#### ➕ 建立客戶個案 (Create)
```
POST https://duotopia-staging-backend-b2ovkkgl6a-de.a.run.app/api/v1/ui/client-case
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "張小明",
  "email": "test@example.com",
  "gender": "男",
  "birth_date": "1995-01-01",
  "phone": "0912345678",
  "identity_option": "轉職者",
  "current_status": "正在考慮轉職",
  "nickname": "小明",
  "education": "大學",
  "occupation": "工程師",
  "location": "台北市",
  "case_summary": "職涯轉換諮詢"
}
```
- 同時建立 Client 和 Case
- Client Code 和 Case Number 自動生成
- 必填欄位：name, email, gender, birth_date, phone, identity_option, current_status

**回應:**
```json
{
  "client_id": "uuid",
  "client_code": "C0002",
  "client_name": "張小明",
  "client_email": "test@example.com",
  "case_id": "uuid",
  "case_number": "CASE0002",
  "case_status": "active",
  "created_at": "2025-11-23T10:00:00Z",
  "message": "客戶與個案建立成功"
}
```

---

#### ✏️ 更新客戶個案 (Update)
```
PATCH https://duotopia-staging-backend-b2ovkkgl6a-de.a.run.app/api/v1/ui/client-case/{case_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "張大明",
  "phone": "0987654321",
  "current_status": "已順利轉職",
  "case_status": "completed",
  "case_summary": "成功協助轉職至新公司"
}
```
- 同時更新 Client 和 Case
- 所有欄位都是選填，只更新提供的欄位
- Case 狀態可更新為：active, completed, suspended, referred

**回應:**
```json
{
  "client_id": "uuid",
  "client_code": "C0002",
  "client_name": "張大明",
  "client_email": "test@example.com",
  "case_id": "uuid",
  "case_number": "CASE0002",
  "case_status": "completed",
  "created_at": "2025-11-23T10:00:00Z",
  "message": "客戶與個案更新成功"
}
```

---

#### 🔍 獲取客戶個案詳情 (Read Detail) ⭐️ NEW
```
GET https://duotopia-staging-backend-b2ovkkgl6a-de.a.run.app/api/v1/ui/client-case/{case_id}
Authorization: Bearer {token}
```
- 獲取單一個案的完整資訊（Client + Case）
- 用於 iOS 更新表單載入現有資料
- 返回所有 Client 和 Case 欄位

**回應:**
```json
{
  "client_id": "uuid",
  "client_name": "張小明",
  "client_code": "C0002",
  "client_email": "test@example.com",
  "gender": "男",
  "birth_date": "1995-01-01",
  "phone": "0912345678",
  "identity_option": "轉職者",
  "current_status": "正在考慮轉職",
  "nickname": "小明",
  "education": "大學",
  "occupation": "工程師",
  "location": "台北市",
  "notes": "初次諮詢",
  "case_id": "uuid",
  "case_number": "CASE0002",
  "case_status": 1,
  "case_status_label": "進行中",
  "case_summary": "職涯轉換諮詢",
  "case_goals": "協助釐清方向",
  "problem_description": "對未來感到迷惘",
  "counselor_id": "uuid",
  "created_at": "2025-11-23T10:00:00Z",
  "updated_at": "2025-11-23T11:00:00Z"
}
```

**Swift 範例:**
```swift
struct ClientCaseDetailResponse: Codable {
    // Client 資訊
    let client_id: UUID
    let client_name: String
    let client_code: String
    let client_email: String
    let gender: String
    let birth_date: String
    let phone: String
    let identity_option: String
    let current_status: String
    let nickname: String?
    let notes: String?
    let education: String?
    let occupation: String?
    let location: String?

    // Case 資訊
    let case_id: UUID
    let case_number: String
    let case_status: Int  // 0=未開始, 1=進行中, 2=已完成
    let case_status_label: String
    let case_summary: String?
    let case_goals: String?
    let problem_description: String?

    // Metadata
    let counselor_id: UUID
    let created_at: Date
    let updated_at: Date?
}

func getClientCaseDetail(token: String, caseId: UUID) async throws -> ClientCaseDetailResponse {
    let url = URL(string: "\(baseURL)/api/v1/ui/client-case/\(caseId)")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(ClientCaseDetailResponse.self, from: data)
}
```

**💡 使用場景:**
1. iOS 點擊個案列表中的某個個案
2. 進入更新表單頁面
3. 調用此 API 獲取完整資料
4. 預填充表單欄位
5. 用戶修改後 PATCH 更新

---

#### 🗑️ 刪除客戶個案 (Delete)
```
DELETE https://duotopia-staging-backend-b2ovkkgl6a-de.a.run.app/api/v1/ui/client-case/{case_id}
Authorization: Bearer {token}
```
- 軟刪除 Case (設定 deleted_at)
- 不刪除 Client (一個 Client 可能有多個 Cases)
- 只有 counselor 本人可以刪除自己的個案

**回應:**
```json
{
  "message": "Case deleted successfully",
  "case_id": "uuid",
  "case_number": "CASE0002",
  "deleted_at": "2025-11-23T11:00:00Z"
}
```

---

**Swift 範例 (完整 CRUD):**
```swift
// 1. 列出客戶個案
func listClientCases(token: String, skip: Int = 0, limit: Int = 20) async throws -> ClientCaseListResponse {
    let url = URL(string: "\(baseURL)/api/v1/ui/client-case-list?skip=\(skip)&limit=\(limit)")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(ClientCaseListResponse.self, from: data)
}

// 2. 建立客戶個案
func createClientCase(token: String, request: CreateClientCaseRequest) async throws -> CreateClientCaseResponse {
    let url = URL(string: "\(baseURL)/api/v1/ui/client-case")!
    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)

    let (data, _) = try await URLSession.shared.data(for: urlRequest)
    return try JSONDecoder().decode(CreateClientCaseResponse.self, from: data)
}

// 3. 更新客戶個案
func updateClientCase(token: String, caseId: UUID, updates: UpdateClientCaseRequest) async throws -> CreateClientCaseResponse {
    let url = URL(string: "\(baseURL)/api/v1/ui/client-case/\(caseId)")!
    var request = URLRequest(url: url)
    request.httpMethod = "PATCH"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try JSONEncoder().encode(updates)

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(CreateClientCaseResponse.self, from: data)
}

// 4. 刪除客戶個案
func deleteClientCase(token: String, caseId: UUID) async throws -> DeleteResponse {
    let url = URL(string: "\(baseURL)/api/v1/ui/client-case/\(caseId)")!
    var request = URLRequest(url: url)
    request.httpMethod = "DELETE"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(DeleteResponse.self, from: data)
}
```

---

## 🎯 island_parents (親子版) 完整操作指南 ⭐️ NEW

**目標用戶**: 家長練習與孩子溝通
**核心功能**: 即時對話分析 + 🟢🟡🔴 三級安全評估 + 親子教養建議

### 與 career 租戶的差異

| 功能 | career (職涯諮詢) | island_parents (親子版) |
|------|------------------|------------------------|
| **Client 表單** | 複雜（10+ 欄位） | 簡化（3個必填：孩子暱稱、年級、關係） |
| **Case 表單** | 標準配置 | 與 island 一致 |
| **即時分析** | 關鍵字 + 類別 | 🟢🟡🔴 安全等級 + 教養建議 |
| **分析間隔** | 固定 | 動態（5-30秒，依安全等級調整） |
| **RAG 知識庫** | 職涯輔導 | 親子教養（依附理論、情緒調節等） |

---

### 完整操作流程

#### 1️⃣ 註冊/登入

**註冊:**
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "parent@example.com",
  "username": "parent_user",
  "password": "password123",
  "full_name": "家長姓名",
  "tenant_id": "island_parents",
  "role": "counselor"
}
```

**⚠️ 關鍵**: `tenant_id` 必須是 `"island_parents"`

**登入:**
```http
POST /api/auth/login
Content-Type: application/json

{
  "tenant_id": "island_parents",
  "email": "parent@example.com",
  "password": "password123"
}
```

**回應:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 7776000
}
```

---

#### 2️⃣ 取得表單配置

**endpoint:**
```http
GET /api/v1/ui/field-schemas/client-case
Authorization: Bearer {token}
```

**island_parents Client 表單（簡化版）:**
```json
{
  "client": {
    "form_type": "client",
    "tenant_id": "island_parents",
    "sections": [
      {
        "title": "孩子基本資料",
        "fields": [
          {
            "key": "name",
            "label": "孩子暱稱",
            "type": "text",
            "required": true,
            "placeholder": "請輸入孩子暱稱",
            "order": 1
          },
          {
            "key": "grade",
            "label": "年級",
            "type": "single_select",
            "required": true,
            "options": ["1 (小一)", "2 (小二)", "3 (小三)", "4 (小四)", "5 (小五)", "6 (小六)",
                       "7 (國一)", "8 (國二)", "9 (國三)", "10 (高一)", "11 (高二)", "12 (高三)"],
            "order": 2
          },
          {
            "key": "relationship",
            "label": "你是孩子的",
            "type": "single_select",
            "required": true,
            "options": ["爸爸", "媽媽", "爺爺", "奶奶", "外公", "外婆", "其他"],
            "order": 3
          },
          {
            "key": "birth_date",
            "label": "出生日期",
            "type": "date",
            "required": false,
            "order": 4
          },
          {
            "key": "gender",
            "label": "性別",
            "type": "single_select",
            "required": false,
            "options": ["男", "女", "其他", "不願透露"],
            "order": 5
          },
          {
            "key": "notes",
            "label": "備註",
            "type": "textarea",
            "required": false,
            "order": 6
          }
        ]
      }
    ]
  }
}
```

**Swift 範例:**
```swift
struct IslandParentsClient: Codable {
    let name: String              // 孩子暱稱（必填）
    let grade: String             // 年級 1-12（必填）
    let relationship: String      // 你是孩子的（必填）
    let birth_date: String?       // 出生日期（選填）
    let gender: String?           // 性別（選填）
    let notes: String?            // 備註（選填）
}
```

---

#### 3️⃣ 建立 Client (孩子資料)

**endpoint:**
```http
POST /api/v1/clients
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "小寶",
  "other_info": {
    "grade": "3 (小三)",
    "relationship": "媽媽"
  },
  "email": "dummy@island-parents.com",
  "gender": "男",
  "birth_date": "2015-05-20",
  "phone": "0912345678",
  "identity_option": "學生",
  "current_status": "親子溝通練習"
}
```

**⚠️ 重要說明:**
- `name`: 孩子暱稱（例如：小寶、阿明）
- `grade` 和 `relationship`: 存放在 `other_info` JSON 欄位
- `email`, `phone`: 雖然必填，但親子版可使用假值
- `identity_option`, `current_status`: 必填，建議固定值

**回應:**
```json
{
  "id": "uuid",
  "name": "小寶",
  "code": "PAR0001",
  "other_info": {
    "grade": "3 (小三)",
    "relationship": "媽媽"
  },
  "tenant_id": "island_parents",
  "created_at": "2025-12-29T10:00:00Z"
}
```

---

#### 4️⃣ 建立 Case (預設案例)

**endpoint:**
```http
POST /api/v1/cases
Authorization: Bearer {token}
Content-Type: application/json

{
  "client_id": "uuid",
  "case_number": "CASE0001",
  "status": 1,
  "problem_description": "親子溝通練習"
}
```

**回應:**
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "case_number": "CASE0001",
  "status": 1,
  "created_at": "2025-12-29T10:05:00Z"
}
```

---

#### 5️⃣ 建立 Session (練習會談)

**endpoint:**
```http
POST /api/v1/sessions
Authorization: Bearer {token}
Content-Type: application/json

{
  "client_id": "uuid",
  "session_date": "2025-12-29",
  "name": "親子對話練習 #1",
  "start_time": "2025-12-29 14:00",
  "notes": "練習開放式提問與傾聽"
}
```

**回應:**
```json
{
  "id": "session-uuid",
  "client_id": "uuid",
  "session_number": 1,
  "name": "親子對話練習 #1",
  "session_date": "2025-12-29T00:00:00Z",
  "start_time": "2025-12-29T14:00:00Z",
  "created_at": "2025-12-29T14:00:00Z"
}
```

---

#### 6️⃣ 錄音循環（即時分析）

**島嶼家長版的核心流程:**

```
┌─────────────────────────────────────────────────────────────┐
│  家長與孩子對話（語音錄製）                                    │
│  ↓                                                           │
│  每 15-30 秒（根據 suggested_interval_seconds 調整）         │
│  ↓                                                           │
│  1. 語音轉文字（WebSocket STT）                              │
│  2. 追加逐字稿片段（append API）                             │
│  3. 即時分析（analyze-partial API）                          │
│     ↓                                                        │
│     AI 回傳：🟢 GREEN / 🟡 YELLOW / 🔴 RED                  │
│     + 教養建議 + 建議下次分析間隔                            │
│  ↓                                                           │
│  iOS 顯示即時回饋 & 調整下次分析間隔                         │
└─────────────────────────────────────────────────────────────┘
```

**6.1 語音轉文字（取得 WebSocket Token）**

```http
POST /api/v1/transcript/elevenlabs-token
Authorization: Bearer {token}
```

**回應:**
```json
{
  "token": "elevenlabs-websocket-token",
  "websocket_url": "wss://api.elevenlabs.io/v1/speech-to-text/realtime",
  "language": "zh"
}
```

**iOS 使用 ElevenLabs SDK 連接 WebSocket 進行即時錄音轉文字。**

---

**6.2 追加逐字稿片段**

```http
POST /api/v1/sessions/{session_id}/recordings/append
Authorization: Bearer {token}
Content-Type: application/json

{
  "start_time": "2025-12-29 14:00",
  "end_time": "2025-12-29 14:00:20",
  "duration_seconds": 20,
  "transcript_text": "家長：你今天在學校過得怎麼樣？\n孩子：還好啊。"
}
```

**回應:**
```json
{
  "session_id": "uuid",
  "recording_added": {
    "segment_number": 1,
    "transcript_text": "..."
  },
  "total_recordings": 1,
  "transcript_text": "完整逐字稿（累積）",
  "updated_at": "2025-12-29T14:00:20Z"
}
```

---

**6.3 即時片段分析（🟢🟡🔴 安全評估）**

```http
POST /api/v1/sessions/{session_id}/analyze-partial
Authorization: Bearer {token}
Content-Type: application/json

{
  "transcript_segment": "家長：你今天在學校過得怎麼樣？\n孩子：還好啊。",
  "mode": "practice"  // Optional: "emergency" or "practice" (default)
}
```

**Mode Parameter:**
- `practice` (default): 詳細教學模式，提供 3-4 個建議含技巧說明
- `emergency`: 緊急模式，快速提供 1-2 個關鍵建議（危機情況使用）

**回應（island_parents 特有格式）:**
```json
{
  "safety_level": "green",
  "severity": 1,
  "display_text": "溝通順暢，家長使用開放式提問，孩子願意回應。",
  "action_suggestion": "繼續保持開放式提問和傾聽，可進一步探問「還好」背後的感受。",
  "suggested_interval_seconds": 20,
  "rag_documents": [
    {
      "title": "開放式提問技巧",
      "excerpt": "開放式問題能鼓勵孩子分享更多..."
    }
  ],
  "keywords": ["開放式提問", "傾聽", "情緒穩定"],
  "categories": ["良好溝通", "親子互動"]
}
```

**🟢🟡🔴 安全等級說明:**

| 等級 | severity | 說明 | 建議間隔 | iOS 顯示 |
|------|----------|------|---------|---------|
| 🟢 **GREEN** | 1-2 | 正向互動，家長有同理心，語氣溫和尊重 | 20-30 秒 | 綠色背景 |
| 🟡 **YELLOW** | 3-4 | 有挫折感但仍可控，語氣開始緊繃或帶防衛 | 10-15 秒 | 黃色背景 + 提醒 |
| 🔴 **RED** | 5 | 威脅、暴力語言、極端情緒、可能造成傷害 | 5-10 秒 | 紅色背景 + 警示 |

**Swift 範例:**
```swift
struct AnalysisResponse: Codable {
    let safety_level: String           // "green", "yellow", "red"
    let severity: Int                  // 1-5
    let display_text: String           // 給家長的即時回饋
    let action_suggestion: String      // 建議採取的行動
    let suggested_interval_seconds: Int // 建議下次分析間隔（5-30秒）
    let rag_documents: [RAGDocument]?  // 相關教養知識
    let keywords: [String]?
    let categories: [String]?
}

struct RAGDocument: Codable {
    let title: String
    let excerpt: String
}

// 根據 safety_level 調整 UI
func updateUI(analysis: AnalysisResponse) {
    switch analysis.safety_level {
    case "green":
        backgroundColor = .systemGreen
        showAlert = false
    case "yellow":
        backgroundColor = .systemYellow
        showAlert = true
        alertLevel = .warning
    case "red":
        backgroundColor = .systemRed
        showAlert = true
        alertLevel = .critical
    default:
        break
    }

    feedbackLabel.text = analysis.display_text
    suggestionLabel.text = analysis.action_suggestion

    // 調整下次分析間隔
    nextAnalysisInterval = analysis.suggested_interval_seconds
}
```

---

#### 7️⃣ 查看分析歷程

**endpoint:**
```http
GET /api/v1/sessions/{session_id}/analysis-logs
Authorization: Bearer {token}
```

**回應:**
```json
{
  "session_id": "uuid",
  "total_logs": 10,
  "logs": [
    {
      "log_index": 0,
      "analyzed_at": "2025-12-29T14:00:20Z",
      "transcript": "家長：你今天在學校過得怎麼樣？\n孩子：還好啊。",
      "analysis_result": {
        "safety_level": "green",
        "display_text": "溝通順暢...",
        "action_suggestion": "繼續保持...",
        "suggested_interval_seconds": 20
      },
      "safety_level": "green",
      "rag_documents": [...]
    },
    {
      "log_index": 1,
      "analyzed_at": "2025-12-29T14:00:40Z",
      "transcript": "家長：還好是什麼意思？\n孩子：就... 沒什麼特別的。",
      "analysis_result": {
        "safety_level": "yellow",
        "display_text": "孩子開始有些防衛...",
        "suggested_interval_seconds": 15
      },
      "safety_level": "yellow"
    }
  ]
}
```

---

#### 8️⃣ 查看會談時間線

**endpoint:**
```http
GET /api/v1/sessions/timeline?client_id={client_id}
Authorization: Bearer {token}
```

**回應:**
```json
{
  "client_id": "uuid",
  "client_name": "小寶",
  "client_code": "PAR0001",
  "total_sessions": 5,
  "sessions": [
    {
      "session_id": "uuid-1",
      "session_number": 1,
      "date": "2025-12-29",
      "time_range": "14:00-14:30",
      "summary": "親子對話練習 #1，家長練習開放式提問",
      "has_report": false,
      "report_id": null
    },
    {
      "session_id": "uuid-2",
      "session_number": 2,
      "date": "2025-12-30",
      "time_range": "15:00-15:30",
      "summary": "親子對話練習 #2，孩子分享學校生活",
      "has_report": false,
      "report_id": null
    }
  ]
}
```

---

#### 9️⃣ 查看用量與計費

**endpoint:**
```http
GET /api/v1/sessions/{session_id}/usage
Authorization: Bearer {token}
```

**回應:**
```json
{
  "session_id": "uuid",
  "tenant_id": "island_parents",
  "analysis_count": 8,
  "credits_deducted": 4.0,
  "credit_deducted": 0.5,
  "last_analyzed_at": "2025-12-29T14:30:00Z"
}
```

**計費說明:**
- 每次 `analyze-partial` 調用會扣除 credits
- 背景任務自動記錄到 `SessionUsage` 和 `CreditLog`
- 支援 BigQuery 持久化記錄

---

### iOS 實作建議

#### 錄音分析循環邏輯

```swift
class IslandParentsSession {
    var nextAnalysisInterval: TimeInterval = 20  // 初始 20 秒
    var isRecording = false
    var currentTranscript = ""

    func startRecording() {
        isRecording = true
        scheduleNextAnalysis()
    }

    func scheduleNextAnalysis() {
        Timer.scheduledTimer(withTimeInterval: nextAnalysisInterval, repeats: false) { [weak self] _ in
            guard let self = self, self.isRecording else { return }

            Task {
                await self.performAnalysis()
            }
        }
    }

    func performAnalysis() async {
        // 1. 取得最近的逐字稿片段（例如最近 60 秒）
        let segment = getRecentTranscript(seconds: 60)

        // 2. 調用分析 API
        let analysis = try await analyzePartial(sessionId: sessionId, segment: segment)

        // 3. 更新 UI
        updateUI(analysis: analysis)

        // 4. 根據 suggested_interval_seconds 調整下次分析間隔
        nextAnalysisInterval = TimeInterval(analysis.suggested_interval_seconds)

        // 5. 排程下次分析
        scheduleNextAnalysis()
    }

    func updateUI(analysis: AnalysisResponse) {
        DispatchQueue.main.async {
            // 根據 safety_level 更新 UI
            switch analysis.safety_level {
            case "green":
                self.statusView.backgroundColor = .systemGreen
                self.showAlert = false
            case "yellow":
                self.statusView.backgroundColor = .systemYellow
                self.showWarning(analysis.action_suggestion)
            case "red":
                self.statusView.backgroundColor = .systemRed
                self.showCriticalAlert(analysis.action_suggestion)
            default:
                break
            }

            self.feedbackLabel.text = analysis.display_text
            self.suggestionLabel.text = analysis.action_suggestion
        }
    }
}
```

---

### 完整測試範例

**測試檔案**: `tests/integration/test_island_parents_complete_workflow.py`

已包含完整的 30 分鐘親子對話模擬測試：
- ✅ 8 個場景（GREEN → YELLOW → RED → GREEN 轉換）
- ✅ 驗證安全等級判斷邏輯
- ✅ 驗證分析歷程記錄
- ✅ 驗證計費與用量追蹤
- ✅ 效能基準（< 30 秒完成 30 分鐘模擬）

---

### 常見問題 FAQ

**Q1: 為什麼 Client 必填欄位這麼多（email, phone），但親子版不需要？**
A: 資料庫 schema 是通用的，但親子版可以使用假值（例如 dummy@island-parents.com）。UI 只顯示 3 個必填欄位（name, grade, relationship）。

**Q2: grade 和 relationship 欄位存在哪裡？**
A: 存放在 `other_info` JSON 欄位中。動態表單 schema 會告訴 iOS 這些欄位的配置。

**Q3: 安全等級的判斷標準是什麼？**
A: AI（Gemini 2.5 Flash）基於親子教養知識庫（RAG）和對話內容，評估：
- 🟢 GREEN: 同理、尊重、開放式溝通
- 🟡 YELLOW: 開始有挫折、緊繃、防衛
- 🔴 RED: 威脅、暴力語言、極端情緒

**Q4: 建議的分析間隔為什麼會變化？**
A: 為了節省成本和提供更好的體驗：
- 🟢 GREEN: 20-30 秒（互動良好，無需頻繁監控）
- 🟡 YELLOW: 10-15 秒（需要適度關注）
- 🔴 RED: 5-10 秒（需要密集監控和即時介入）

**Q5: 報告功能可用嗎？**
A: island_parents 目前主要使用即時分析，報告生成功能暫未啟用。如需啟用，可使用 `POST /api/v1/reports/generate`。

---

### 相關資源

- **Swagger 文件**: `https://your-api/docs`
- **完整測試範例**: `tests/integration/test_island_parents_complete_workflow.py`
- **Field Configs**: `app/config/field_configs.py` (line 358-532)
- **分析服務**: `app/services/keyword_analysis_service.py`

---

## API 列表

### 🎨 動態表單 Schema APIs ⭐️ NEW
1. GET /api/v1/ui/field-schemas/client-case - 一次獲取 Client + Case schemas (推薦)
2. GET /api/v1/ui/field-schemas/client - 獲取 Client schema
3. GET /api/v1/ui/field-schemas/case - 獲取 Case schema

### 👤 認證 APIs
0. POST /api/auth/register - 註冊帳號 ⭐️ NEW
1. POST /api/auth/login - 登入
2. GET /api/auth/me - 取得諮詢師資訊
3. PATCH /api/auth/me - 更新諮詢師資訊
3b. POST /api/auth/delete-account - 刪除帳號 (Soft Delete) ⭐️ NEW
4. GET /api/v1/usage/stats - 取得使用量統計 ⭐️ NEW

### 👥 個案管理 APIs
5. POST /api/v1/clients - 建立個案
6. GET /api/v1/clients - 列出個案
7. GET /api/v1/clients/{id} - 取得單一個案
8. PATCH /api/v1/clients/{id} - 更新個案
9. DELETE /api/v1/clients/{id} - 刪除個案
10. GET /api/v1/sessions/timeline - 取得個案會談歷程時間線 ⭐️ NEW

### 📝 會談記錄管理 APIs
11. POST /api/v1/sessions - 建立會談記錄
12. GET /api/v1/sessions - 列出會談記錄
13. GET /api/v1/sessions/{id} - 查看會談記錄
14. PATCH /api/v1/sessions/{id} - 更新會談記錄
15. DELETE /api/v1/sessions/{id} - 刪除會談記錄
16. POST /api/v1/sessions/{id}/recordings/append - 🎙️ Append 錄音片段 (iOS 友善) ⭐️ NEW

### 🧠 諮詢師反思 APIs
17. GET /api/v1/sessions/{id}/reflection - 取得反思內容
18. PUT /api/v1/sessions/{id}/reflection - 更新反思內容

### 🔍 片段分析 APIs（Multi-Tenant）⭐️ NEW
19. POST /api/v1/sessions/{id}/analyze-partial - 即時片段分析（推薦使用）
19b. POST /api/v1/sessions/{id}/analyze-keywords - 舊版 API（向後兼容）
20. GET /api/v1/sessions/{id}/analysis-logs - 取得分析歷程記錄
21. DELETE /api/v1/sessions/{id}/analysis-logs/{log_index} - 刪除特定分析記錄

### 📄 報告 APIs
22. POST /api/v1/reports/generate - 生成報告 (從已儲存的會談記錄生成，需提供 session_id)
23. GET /api/v1/reports - 列出報告
24. GET /api/v1/reports/{id} - 取得單一報告
25. PATCH /api/v1/reports/{id} - 更新報告 (編輯)
26. GET /api/v1/reports/{id}/formatted - 取得格式化報告 (Markdown/HTML)

---

## 🎨 動態表單 Schema APIs

### 背景說明

本系統採用**動態表單配置**，不同租戶可以有不同的 Client 和 Case 欄位。iOS App 需要先獲取租戶的 Schema 配置，然後根據 Schema 動態生成表單。

**使用場景:**
- 建立新個案前：獲取表單 Schema
- 更新個案前：獲取表單 Schema + 獲取現有資料

**推薦流程:**
1. 登入後調用 `GET /api/v1/ui/field-schemas/client-case` 一次獲取兩個 Schema
2. 根據 Schema 動態生成表單 UI
3. 用戶填寫表單後 POST 建立或 PATCH 更新

---

### 1. 獲取 Client + Case Schemas (一次調用) ⭐️ 推薦

**Endpoint:** `GET /api/v1/ui/field-schemas/client-case`

**描述:** 一次性返回 Client 和 Case 的表單配置，減少網絡請求。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "client": {
    "form_type": "client",
    "tenant_id": "career",
    "sections": [
      {
        "title": "基本資料",
        "description": "個案基本資訊",
        "order": 1,
        "fields": [
          {
            "key": "name",
            "label": "姓名",
            "type": "text",
            "required": true,
            "placeholder": "請輸入真實姓名",
            "help_text": "使用者的真實姓名",
            "order": 1
          },
          {
            "key": "email",
            "label": "電子郵件地址",
            "type": "email",
            "required": true,
            "placeholder": "example@email.com",
            "order": 2
          }
        ]
      }
    ]
  },
  "case": {
    "form_type": "case",
    "tenant_id": "career",
    "sections": [
      {
        "title": "個案資訊",
        "description": "個案編號、狀態與諮詢內容",
        "order": 1,
        "fields": [
          {
            "key": "case_number",
            "label": "個案編號",
            "type": "text",
            "required": true,
            "placeholder": "自動生成",
            "help_text": "系統自動生成，格式：CASE0001",
            "order": 1
          },
          {
            "key": "status",
            "label": "個案狀態",
            "type": "single_select",
            "required": true,
            "options": ["0", "1", "2"],
            "default_value": "0",
            "help_text": "0=未開始(NOT_STARTED), 1=進行中(IN_PROGRESS), 2=已完成(COMPLETED)",
            "order": 2
          }
        ]
      }
    ]
  },
  "tenant_id": "career"
}
```

**Swift 範例:**
```swift
struct ClientCaseSchemaResponse: Codable {
    let client: FormSchema
    let case: FormSchema
    let tenant_id: String
}

struct FormSchema: Codable {
    let form_type: String
    let tenant_id: String
    let sections: [FieldSection]
}

struct FieldSection: Codable {
    let title: String
    let description: String?
    let order: Int
    let fields: [FieldSchema]
}

struct FieldSchema: Codable {
    let key: String
    let label: String
    let type: String  // "text", "email", "phone", "textarea", "single_select", "date"
    let required: Bool
    let placeholder: String?
    let help_text: String?
    let options: [String]?
    let default_value: String?
    let validation_rules: [String: Int]?
    let order: Int
}

func getClientCaseSchemas(token: String) async throws -> ClientCaseSchemaResponse {
    let url = URL(string: "\(baseURL)/api/v1/ui/field-schemas/client-case")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(ClientCaseSchemaResponse.self, from: data)
}
```

---

### 2. 獲取 Client Schema

**Endpoint:** `GET /api/v1/ui/field-schemas/client`

**描述:** 單獨獲取 Client 表單配置。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "form_type": "client",
  "tenant_id": "career",
  "sections": [...]
}
```

---

### 3. 獲取 Case Schema

**Endpoint:** `GET /api/v1/ui/field-schemas/case`

**描述:** 單獨獲取 Case 表單配置。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "form_type": "case",
  "tenant_id": "career",
  "sections": [...]
}
```

**⚠️ Case Status 重要變更:**
- `status` 欄位從字串 enum 改為**整數**
- 值: `"0"` (未開始), `"1"` (進行中), `"2"` (已完成)
- 前端需要顯示對應的 label

---

## 🔐 認證 APIs

### 0. 註冊帳號 ⭐️ NEW (已簡化)

**Endpoint:** `POST /api/auth/register`

**描述:** 註冊新的諮詢師帳號，註冊成功後自動登入並返回 JWT token。

**簡化註冊（推薦）:** 只需要 `email` + `password` + `tenant_id`，`username` 和 `full_name` 可後續透過 `/api/auth/me` 補填。

**Request (簡化版):**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "tenant_id": "career"
}
```

**Request (完整版，向後兼容):**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "tenant_id": "career",
  "username": "newuser",
  "full_name": "新用戶",
  "role": "counselor"
}
```

**欄位說明:**
- `email` (必填): 電子郵件地址，需符合 Email 格式
- `password` (必填): 密碼，至少 8 個字元，需包含至少一個英文字母 (a-z) 和至少一個數字 (0-9)，且不可為常見密碼。無大寫或特殊字元要求
- `tenant_id` (必填): 租戶 ID（如 "career" 或 "island"）
- `username` (選填): 用戶名，3-50 個字元。如果提供，必須全系統唯一。可後續透過 `/api/auth/me` 補填
- `full_name` (選填): 全名。可後續透過 `/api/auth/me` 補填
- `role` (選填): 角色，預設為 "counselor"，可選值：counselor, supervisor, admin

**唯一性檢查:**
- `email + tenant_id` 組合必須唯一（同一 email 可在不同 tenant 註冊）
- 如果提供 `username`，必須全系統唯一

**Response (201):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 7776000,
  "email_verified": false,
  "verification_email_sent": true,
  "message": "Registration successful. Please check your email to verify your account."
}
```

**📧 Email Verification:**
- 註冊成功後，系統會自動發送驗證郵件到註冊的 email
- `email_verified`: Email 是否已驗證（註冊時預設為 `false`）
- `verification_email_sent`: 是否已成功發送驗證郵件
- **重要**: Email 未驗證前無法登入（登入會返回 403 錯誤）

**錯誤回應:**

**400 Bad Request - Email 已存在於該租戶:**
```json
{
  "detail": "Email 'newuser@example.com' already exists for tenant 'career'"
}
```

**400 Bad Request - Username 已存在 (僅當提供 username 時):**
```json
{
  "detail": "Username 'newuser' already exists"
}
```

**422 Unprocessable Entity - 驗證錯誤 (RFC 7807 格式):**
```json
{
  "type": "https://api.career-counseling.app/errors/validation-error",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "Validation failed: 1 error(s)",
  "instance": "/api/auth/register",
  "errors": [
    {
      "field": "body -> password",
      "message": "Value error, Password validation failed: Password must be at least 8 characters; Password must contain at least one digit (0-9)",
      "type": "value_error"
    }
  ],
  "password_rules": {
    "min_length": 8,
    "require_letter": true,
    "require_digit": true,
    "require_uppercase": false,
    "require_special_char": false
  }
}
```

> **💡 `password_rules` 欄位:** 當密碼驗證失敗時，回應會包含 `password_rules` 物件，iOS 端可用來動態顯示密碼規則提示，無需硬編碼規則。

**Swift 範例 (簡化版):**
```swift
struct RegisterRequest: Codable {
    let email: String
    let password: String
    let tenant_id: String
    let username: String?
    let full_name: String?
    let role: String?

    enum CodingKeys: String, CodingKey {
        case email
        case password
        case tenant_id
        case username
        case full_name
        case role
    }
}

struct RegisterResponse: Codable {
    let access_token: String
    let token_type: String
    let expires_in: Int
    let email_verified: Bool
    let verification_email_sent: Bool
    let message: String
}

// 簡化註冊（推薦）
func register(
    email: String,
    password: String,
    tenantId: String,
    role: String? = "counselor"
) async throws -> String {
    let url = URL(string: "\(baseURL)/api/auth/register")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = RegisterRequest(
        email: email,
        password: password,
        tenant_id: tenantId,
        username: nil,
        full_name: nil,
        role: role
    )
    request.httpBody = try JSONEncoder().encode(body)

    let (data, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse else {
        throw URLError(.badServerResponse)
    }

    if httpResponse.statusCode == 201 {
        let registerResponse = try JSONDecoder().decode(RegisterResponse.self, from: data)
        return registerResponse.access_token
    } else if httpResponse.statusCode == 422 {
        // 密碼驗證失敗 - 解析 RFC 7807 錯誤與 password_rules
        let errorResponse = try JSONDecoder().decode(ValidationErrorResponse.self, from: data)
        if let rules = errorResponse.password_rules {
            // 使用 password_rules 動態顯示密碼規則
            print("密碼規則: 最少 \(rules.min_length) 字元, 需要字母: \(rules.require_letter), 需要數字: \(rules.require_digit)")
        }
        let messages = errorResponse.errors.map { $0.message }
        throw NSError(domain: "RegisterError", code: 422, userInfo: [NSLocalizedDescriptionKey: messages.joined(separator: "\n")])
    } else {
        // 處理其他錯誤
        let errorData = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let errorMessage = errorData?["detail"] as? String ?? "註冊失敗"
        throw NSError(domain: "RegisterError", code: httpResponse.statusCode, userInfo: [NSLocalizedDescriptionKey: errorMessage])
    }
}

// 密碼驗證錯誤回應 Models (RFC 7807)
struct ValidationErrorResponse: Codable {
    let type: String
    let title: String
    let status: Int
    let detail: String
    let instance: String
    let errors: [ValidationError]
    let password_rules: PasswordRules?
}

struct ValidationError: Codable {
    let field: String
    let message: String
    let type: String
}

struct PasswordRules: Codable {
    let min_length: Int
    let require_letter: Bool
    let require_digit: Bool
    let require_uppercase: Bool
    let require_special_char: Bool
}
```

**使用範例:**
```swift
// 簡化註冊（只需要 email + password）
do {
    let token = try await register(
        email: "newuser@example.com",
        password: "password123",
        tenantId: "career"
    )
    // 註冊成功，token 已返回，可直接使用
    // username 和 full_name 可後續透過 PATCH /api/auth/me 補填
    print("註冊成功，Token: \(token)")
} catch {
    print("註冊失敗: \(error.localizedDescription)")
}
```

---

### 1. 登入

**Endpoint:** `POST /api/auth/login`

**⚠️ 重要：必須提供 `tenant_id`**

**Request:**
```json
{
  "tenant_id": "career",
  "email": "admin@career.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 7776000
}
```

**錯誤回應:**

**403 Forbidden - Email 未驗證:**
```json
{
  "detail": {
    "code": "EMAIL_NOT_VERIFIED",
    "message": "Please verify your email before logging in"
  }
}
```

**📧 Email Verification 檢查:**
- 登入前必須先完成 email 驗證
- 若 email 未驗證，系統會返回 `403 Forbidden` 錯誤
- iOS 端應引導用戶檢查郵件並完成驗證後再登入

**Swift 範例:**
```swift
struct LoginRequest: Codable {
    let tenant_id: String
    let email: String
    let password: String
}

struct LoginResponse: Codable {
    let access_token: String
    let token_type: String
    let expires_in: Int
}

func login(tenantId: String, email: String, password: String) async throws -> String {
    let url = URL(string: "\(baseURL)/api/auth/login")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = LoginRequest(tenant_id: tenantId, email: email, password: password)
    request.httpBody = try JSONEncoder().encode(body)

    let (data, _) = try await URLSession.shared.data(for: request)
    let response = try JSONDecoder().decode(LoginResponse.self, from: data)

    return response.access_token
}
```

---

### 2. 取得當前用戶資訊

**Endpoint:** `GET /api/auth/me`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "id": "uuid",
  "email": "test@career.com",
  "username": "test",
  "full_name": "Test Counselor",
  "tenant_id": "career",
  "role": "counselor",
  "is_active": true,
  "created_at": "2025-10-29T00:00:00Z"
}
```

**Swift 範例:**
```swift
struct Counselor: Codable {
    let id: UUID
    let email: String
    let username: String
    let full_name: String
    let tenant_id: String
    let role: String
    let is_active: Bool
    let created_at: Date
}

func getCurrentUser(token: String) async throws -> Counselor {
    let url = URL(string: "\(baseURL)/api/auth/me")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(Counselor.self, from: data)
}
```

---

### 3. 更新諮詢師資訊

**Endpoint:** `PATCH /api/auth/me`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "full_name": "Updated Name",
  "username": "newusername"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "email": "test@career.com",
  "username": "newusername",
  "full_name": "Updated Name",
  "tenant_id": "career",
  "role": "counselor",
  "is_active": true,
  "created_at": "2025-10-29T00:00:00Z",
  "updated_at": "2025-10-29T10:00:00Z"
}
```

**Swift 範例:**
```swift
struct UpdateCounselorRequest: Codable {
    let full_name: String?
    let username: String?
}

func updateCounselor(token: String, fullName: String?, username: String?) async throws -> Counselor {
    let url = URL(string: "\(baseURL)/api/auth/me")!
    var request = URLRequest(url: url)
    request.httpMethod = "PATCH"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = UpdateCounselorRequest(full_name: fullName, username: username)
    request.httpBody = try JSONEncoder().encode(body)

    let (data, _) = try await URLSession.shared.data(for: request)
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(Counselor.self, from: data)
}
```

---

### 3b. 刪除帳號 (Delete Account) ⭐️ NEW

**Endpoint:** `POST /api/auth/delete-account`

**描述:** 軟刪除帳號。清除個人資料（email prefix、username、full_name、phone），帳號標記為停用。資料保留可由管理員恢復。

**⚠️ 為什麼用 POST 不用 DELETE**: iOS HTTP client 的 request body 相容性

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "password": null
}
```

> `password` 欄位為選填，目前不做驗證。

**Response (200):**
```json
{
  "message": "Account deleted successfully"
}
```

**Soft Delete 行為:**

| 欄位 | 刪除前 | 刪除後 |
|------|--------|--------|
| email | `user@example.com` | `deleted_{timestamp}_user@example.com` |
| username | `john` | `null` |
| full_name | `John Doe` | `null` |
| phone | `+886912345678` | `null` |
| is_active | `true` | `false` |
| deleted_at | `null` | `2026-02-19T10:00:00Z` |
| hashed_password | (保留) | (保留，供恢復用) |

**錯誤回應:**

| Status | 說明 |
|--------|------|
| 200 | 帳號刪除成功 |
| 401 | Token 無效或過期 |
| 403 | 未登入 |
| 500 | 伺服器錯誤 |

**Swift 範例:**
```swift
func deleteAccount(token: String) async throws {
    let url = URL(string: "\(baseURL)/api/auth/delete-account")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = "{}".data(using: .utf8)

    let (_, response) = try await URLSession.shared.data(for: request)
    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw URLError(.badServerResponse)
    }

    // 清除本地 token
    UserDefaults.standard.removeObject(forKey: "access_token")
}
```

> **Note:** 刪除後同一 email 可重新註冊。如需恢復帳號，請聯繫管理員。

---

### 4. 取得使用量統計 ⭐️ NEW

**Endpoint:** `GET /api/v1/usage/stats`

**描述:** 取得當前諮詢師的使用量統計資訊，支援兩種計費模式：Prepaid（預付）和 Subscription（訂閱制）。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200) - Subscription Mode:**
```json
{
  "billing_mode": "subscription",
  "monthly_limit_minutes": 360,
  "monthly_used_minutes": 120,
  "monthly_remaining_minutes": 240,
  "usage_percentage": 33.33,
  "is_limit_reached": false,
  "usage_period_start": "2026-01-01T00:00:00Z",
  "usage_period_end": "2026-01-31T23:59:59Z"
}
```

**Response (200) - Prepaid Mode:**
```json
{
  "billing_mode": "prepaid",
  "available_credits": 1000.50
}
```

**欄位說明:**

**共通欄位:**
- `billing_mode`: 計費模式，"prepaid"（預付）或 "subscription"（訂閱制）

**Prepaid Mode 專屬欄位:**
- `available_credits`: 可用額度（金額或點數）

**Subscription Mode 專屬欄位:**
- `monthly_limit_minutes`: 每月使用額度上限（分鐘數）
- `monthly_used_minutes`: 本月已使用分鐘數
- `monthly_remaining_minutes`: 本月剩餘分鐘數
- `usage_percentage`: 使用率百分比（0-100）
- `is_limit_reached`: 是否已達使用上限
- `usage_period_start`: 計費週期開始時間（ISO 8601 格式）
- `usage_period_end`: 計費週期結束時間（ISO 8601 格式）

**⚠️ 超限行為:**
- 當 `is_limit_reached = true` 時，所有 AI 相關 API（片段分析、報告生成等）將返回 `HTTP 429 Too Many Requests`
- iOS 端應監控 `usage_percentage`，在接近 100% 時提前警告用戶

**📊 使用量追蹤說明:**
- **追蹤時機**: 只有創建 session 時提供 `duration_minutes` 欄位，才會計入使用量
- **累積計算**: 每次創建 session 時，`monthly_used_minutes` 會增加對應的 `duration_minutes`
- **限制檢查**: 創建 session 前會檢查是否超過 `monthly_limit_minutes`（預設 360 分鐘）
- **自動重置**: 使用週期（30 天）結束後，`monthly_used_minutes` 自動歸零
- **注意事項**: 如果創建 session 時未提供 `duration_minutes`，該 session 不會計入使用量（適用於僅記錄逐字稿的情況）

**Swift 範例:**
```swift
struct UsageStatsResponse: Codable {
    let billing_mode: String

    // Prepaid mode fields
    let available_credits: Double?

    // Subscription mode fields
    let monthly_limit_minutes: Int?
    let monthly_used_minutes: Int?
    let monthly_remaining_minutes: Int?
    let usage_percentage: Double?
    let is_limit_reached: Bool?
    let usage_period_start: Date?
    let usage_period_end: Date?
}

func getUsageStats(token: String) async throws -> UsageStatsResponse {
    let url = URL(string: "\(baseURL)/api/v1/usage/stats")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(UsageStatsResponse.self, from: data)
}

// 使用範例
do {
    let stats = try await getUsageStats(token: userToken)

    if stats.billing_mode == "subscription" {
        if let isLimitReached = stats.is_limit_reached, isLimitReached {
            print("⚠️ 已達本月使用上限")
        } else if let percentage = stats.usage_percentage {
            print("本月使用率: \(percentage)%")
            if percentage >= 80 {
                print("⚠️ 警告：使用量接近上限")
            }
        }
    } else if stats.billing_mode == "prepaid" {
        if let credits = stats.available_credits {
            print("可用額度: \(credits)")
        }
    }
} catch {
    print("無法取得使用量統計: \(error)")
}
```

**UI 建議:**
- **進度條顯示**: 使用 `usage_percentage` 顯示使用率進度條
- **剩餘時間提示**: 顯示 `monthly_remaining_minutes`（例如："剩餘 4 小時"）
- **超限警告**: 當 `usage_percentage >= 80%` 時顯示橘色警告，`>= 95%` 時顯示紅色警告
- **計費週期顯示**: 顯示 `usage_period_start` 至 `usage_period_end`（例如："2026/01/01 - 2026/01/31"）

---

## 👥 個案管理 APIs

### 5. 建立個案

**Endpoint:** `POST /api/v1/clients`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "name": "王小明",
  "code": "C001",  // optional: 如果不提供，後端會自動生成流水號 (C0001, C0002...)
  "nickname": "小明",
  "birth_date": "1998-05-15",  // ⭐️ NEW: 出生日期 (YYYY-MM-DD)，age 會自動計算
  "gender": "male",
  "occupation": "工程師",
  "education": "大學",
  "location": "台北市",
  "economic_status": "中等",
  "family_relations": "父母健在",
  "tags": ["職涯諮詢", "轉職"],
  "notes": "初次諮詢，對職涯方向感到迷惘"
}
```

**📝 重要說明:**
- `code`: 可選，不提供時系統自動生成 (C0001, C0002...)
- `birth_date`: ⭐️ 建議提供出生日期而非直接提供 age，系統會自動計算年齡
- `age`: 如果提供 birth_date，age 會被自動覆蓋；只在沒有 birth_date 時才手動填寫
- 所有欄位除了 `name` 外都是 optional

**Response (201):**
```json
{
  "id": "uuid",
  "name": "王小明",
  "code": "C001",
  "nickname": "小明",
  "age": 25,
  "gender": "male",
  "occupation": "工程師",
  "education": "大學",
  "location": "台北市",
  "economic_status": "中等",
  "family_relations": "父母健在",
  "tags": ["職涯諮詢", "轉職"],
  "counselor_id": "uuid",
  "tenant_id": "career",
  "created_at": "2025-10-29T00:00:00Z",
  "updated_at": "2025-10-29T00:00:00Z"
}
```

**Swift 範例:**
```swift
struct CreateClientRequest: Codable {
    let name: String
    let code: String?  // optional: 如果不提供，後端自動生成 C0001, C0002...
    let nickname: String?
    let age: Int?
    let gender: String?
    let occupation: String?
    let education: String?
    let location: String?
    let economic_status: String?
    let family_relations: String?
    let tags: [String]?
}

struct Client: Codable {
    let id: UUID
    let name: String
    let code: String
    let nickname: String?
    let age: Int?
    let gender: String?
    let occupation: String?
    let education: String?
    let location: String?
    let economic_status: String?
    let family_relations: String?
    let tags: [String]?
    let counselor_id: UUID
    let tenant_id: String
    let created_at: Date
    let updated_at: Date
}

func createClient(token: String, request: CreateClientRequest) async throws -> Client {
    let url = URL(string: "\(baseURL)/api/v1/clients")!
    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")

    urlRequest.httpBody = try JSONEncoder().encode(request)

    let (data, _) = try await URLSession.shared.data(for: urlRequest)
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(Client.self, from: data)
}
```

---

### 6. 列出個案

**Endpoint:** `GET /api/v1/clients`

**Query Parameters:**
- `skip` (int, optional): 分頁偏移，預設 0
- `limit` (int, optional): 每頁筆數，預設 20，最大 100
- `search` (string, optional): 搜尋關鍵字（name/nickname/code）

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "total": 10,
  "items": [
    {
      "id": "uuid",
      "name": "王小明",
      "code": "C001",
      "nickname": "小明",
      "age": 25,
      "gender": "male",
      "created_at": "2025-10-29T00:00:00Z"
    }
  ]
}
```

**Swift 範例:**
```swift
struct ClientListResponse: Codable {
    let total: Int
    let items: [Client]
}

func listClients(token: String, skip: Int = 0, limit: Int = 20, search: String? = nil) async throws -> ClientListResponse {
    var components = URLComponents(string: "\(baseURL)/api/v1/clients")!
    components.queryItems = [
        URLQueryItem(name: "skip", value: "\(skip)"),
        URLQueryItem(name: "limit", value: "\(limit)")
    ]
    if let search = search {
        components.queryItems?.append(URLQueryItem(name: "search", value: search))
    }

    var request = URLRequest(url: components.url!)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(ClientListResponse.self, from: data)
}
```

---

### 7. 取得單一個案

**Endpoint:** `GET /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):** 同建立個案的 Response

---

### 8. 更新個案

**Endpoint:** `PATCH /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:** (所有欄位都是 optional)
```json
{
  "nickname": "阿明",
  "age": 26,
  "tags": ["職涯諮詢", "轉職", "焦慮"]
}
```

**Response (200):** 更新後的完整 Client 物件

---

### 9. 刪除個案

**Endpoint:** `DELETE /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (204):** No Content

---

### 10. 取得個案會談歷程時間線 ⭐️ NEW

**Endpoint:** `GET /api/v1/sessions/timeline`

**描述:** 取得個案的所有會談記錄時間線，包含會談次數、日期、時間範圍、摘要、是否有報告等資訊。適合在個案詳情頁面顯示完整的諮詢歷程。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `client_id` **(必填)**: 個案 UUID

**Request Example:**
```
GET /api/v1/sessions/timeline?client_id=550e8400-e29b-41d4-a716-446655440000
```

**Response (200):**
```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_name": "王小明",
  "client_code": "C0001",
  "total_sessions": 4,
  "sessions": [
    {
      "session_id": "uuid-1",
      "session_number": 1,
      "date": "2024-08-26",
      "time_range": "20:30-21:30",
      "summary": "初談建立關係，確認諮詢目標與工作歷程。個案表現出疲憊與焦慮狀態...",
      "has_report": true,
      "report_id": "report-uuid-1"
    },
    {
      "session_id": "uuid-2",
      "session_number": 2,
      "date": "2024-08-30",
      "time_range": "20:30-21:30",
      "summary": "進行職游旅人牌卡盤點，歸納熱情關鍵字：表達自我、美感呈現...",
      "has_report": true,
      "report_id": "report-uuid-2"
    },
    {
      "session_id": "uuid-3",
      "session_number": 3,
      "date": "2024-09-06",
      "time_range": null,
      "summary": "盤點職能卡與24個特質。優勢：自我覺察、尊重包容...",
      "has_report": false,
      "report_id": null
    }
  ]
}
```

**欄位說明:**
- `time_range`: 會談時間範圍 (HH:MM-HH:MM)，如果沒有設定 start_time/end_time 則為 null
- `summary`: AI 自動生成的 100 字內會談摘要，用於快速瀏覽
- `has_report`: 是否已生成報告
- `report_id`: 報告 ID，沒有報告時為 null

**Swift 範例:**
```swift
struct TimelineSession: Codable {
    let session_id: UUID
    let session_number: Int
    let date: String
    let time_range: String?
    let summary: String?
    let has_report: Bool
    let report_id: UUID?
}

struct ClientTimelineResponse: Codable {
    let client_id: UUID
    let client_name: String
    let client_code: String
    let total_sessions: Int
    let sessions: [TimelineSession]
}

func getClientTimeline(token: String, clientId: UUID) async throws -> ClientTimelineResponse {
    let url = URL(string: "\(baseURL)/api/v1/sessions/timeline?client_id=\(clientId.uuidString)")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(ClientTimelineResponse.self, from: data)
}
```

---

## 📝 會談記錄管理 APIs

### 11. 建立會談記錄

**Endpoint:** `POST /api/v1/sessions`

**描述:** 儲存會談逐字稿（不立即生成報告）。諮詢師可以先儲存逐字稿，稍後再決定是否生成報告。

**重要:** `session_number` 是自動按照會談時間排序生成的：
- **排序規則**: 優先使用 `start_time`，如果沒有提供則使用 `session_date`
- **一天多場會談**: 如果同一天有多場會談，必須提供 `start_time` 才能正確排序
- **自動重新編號**: 插入較早的會談時，後續會談編號會自動 +1

**範例:**
- 先輸入 2024-01-15 14:00 的會談 → session_number = 1
- 再輸入 2024-01-20 10:00 的會談 → session_number = 2
- 後來補輸入 2024-01-10 09:00 的會談 → session_number = 1（原有的 1, 2 會自動變成 2, 3）
- 補輸入 2024-01-15 16:00 的會談 → session_number = 2（同一天下午的會談）

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "client_id": "uuid",
  "session_date": "2024-01-15",             // 必填
  "name": "初次會談 - 職涯探索",              // ⭐️ NEW optional，會談名稱（用於組織管理）
  "start_time": "2024-01-15 14:00",        // optional，會談開始時間
  "end_time": "2024-01-15 15:00",          // optional，會談結束時間
  "transcript": "逐字稿內容...",             // optional（與 recordings 二選一）
  "recordings": [                          // ⭐️ NEW optional，錄音片段數組
    {
      "segment_number": 1,
      "start_time": "2024-01-15 14:00",
      "end_time": "2024-01-15 14:20",
      "duration_seconds": 1200,
      "transcript_text": "第一段逐字稿內容...",
      "transcript_sanitized": "第一段脫敏逐字稿..."
    },
    {
      "segment_number": 2,
      "start_time": "2024-01-15 14:25",
      "end_time": "2024-01-15 14:45",
      "duration_seconds": 1200,
      "transcript_text": "第二段逐字稿內容...",
      "transcript_sanitized": "第二段脫敏逐字稿..."
    }
  ],
  "duration_minutes": 50,                  // optional (保留向下兼容)
  "notes": "備註說明",                       // optional，諮詢師人工撰寫的備註
  "reflection": {                          // ⭐️ NEW optional，諮詢師反思（人類撰寫）
    "working_with_client": "整體過程流暢輕鬆，逐漸贏得信任...",
    "feeling_source": "個案從緊張到逐步放鬆...",
    "current_challenges": "當肯定個案時，仍會有自我懷疑反應...",
    "supervision_topics": "如何在支持與挑戰間拿捏節奏..."
  }
}
```

**📝 欄位說明:**
- `name`: ⭐️ NEW 會談名稱（optional），用於組織和區分會談記錄
  - 例如：「初次會談」、「職涯探索」、「壓力管理」、「追蹤會談」
  - 幫助諮詢師快速識別會談主題
  - 未提供時系統會自動使用 `session_number` 作為預設名稱
- `transcript` vs `recordings`: **二選一**
  - `transcript`: 直接提供完整逐字稿（傳統方式）
  - `recordings`: ⭐️ 提供分段錄音逐字稿（推薦），系統會**自動聚合**成完整逐字稿
- `recordings` 自動聚合邏輯:
  - 按 `segment_number` 排序
  - 用 `\n\n` (兩個換行) 連接所有 `transcript_text`
  - 自動填充到 `transcript_text` 和 `transcript_sanitized` 欄位
- `notes`: 諮詢師對本次會談的簡短備註
- `reflection`: ⭐️ 諮詢師對本次會談的深度反思，包含 4 個反思問題（選填）
  - `working_with_client`: 我和這個人工作的感受是？
  - `feeling_source`: 這個感受的原因是？
  - `current_challenges`: 目前的困難／想更深入的地方是？
  - `supervision_topics`: 我會想找督導討論的問題是？

**Response (201):**
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "client_name": "個案姓名",
  "case_id": "uuid",
  "session_number": 1,                     // 自動按會談時間排序生成
  "name": "初次會談 - 職涯探索",              // ⭐️ NEW 會談名稱
  "session_date": "2024-01-15T00:00:00Z",
  "start_time": "2024-01-15T14:00:00Z",   // 會談開始時間
  "end_time": "2024-01-15T15:00:00Z",     // 會談結束時間
  "transcript_text": "第一段逐字稿內容...\n\n第二段逐字稿內容...",  // ⭐️ 自動聚合
  "recordings": [                          // ⭐️ NEW 錄音片段數組
    {
      "segment_number": 1,
      "start_time": "2024-01-15 14:00",
      "end_time": "2024-01-15 14:20",
      "duration_seconds": 1200,
      "transcript_text": "第一段逐字稿內容...",
      "transcript_sanitized": "第一段脫敏逐字稿..."
    },
    {
      "segment_number": 2,
      "start_time": "2024-01-15 14:25",
      "end_time": "2024-01-15 14:45",
      "duration_seconds": 1200,
      "transcript_text": "第二段逐字稿內容...",
      "transcript_sanitized": "第二段脫敏逐字稿..."
    }
  ],
  "duration_minutes": 50,
  "notes": "備註說明",
  "has_report": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

**Swift Example:**
```swift
struct RecordingSegment: Codable {
    let segment_number: Int
    let start_time: String
    let end_time: String
    let duration_seconds: Int
    let transcript_text: String
    let transcript_sanitized: String?
}

struct SessionCreateRequest: Codable {
    let client_id: UUID
    let session_date: String      // "YYYY-MM-DD"
    let name: String?             // ⭐️ NEW 會談名稱
    let start_time: String?       // "YYYY-MM-DD HH:MM"
    let end_time: String?         // "YYYY-MM-DD HH:MM"
    let transcript: String?       // ⭐️ Optional，與 recordings 二選一
    let recordings: [RecordingSegment]?  // ⭐️ NEW Optional，錄音片段數組（推薦）
    let duration_minutes: Int?    // 保留向下兼容
    let notes: String?

    // 使用 transcript 的傳統方式
    init(clientId: UUID, sessionDate: String, transcript: String, name: String? = nil, notes: String? = nil) {
        self.client_id = clientId
        self.session_date = sessionDate
        self.name = name
        self.transcript = transcript
        self.recordings = nil
        self.notes = notes
        self.start_time = nil
        self.end_time = nil
        self.duration_minutes = nil
    }

    // ⭐️ 使用 recordings 的新方式（推薦）
    init(clientId: UUID, sessionDate: String, recordings: [RecordingSegment], name: String? = nil, notes: String? = nil) {
        self.client_id = clientId
        self.session_date = sessionDate
        self.name = name
        self.recordings = recordings
        self.transcript = nil  // 系統會自動聚合
        self.notes = notes
        self.start_time = nil
        self.end_time = nil
        self.duration_minutes = nil
    }
}

func createSession(token: String, request: SessionCreateRequest) async throws -> SessionDetail {
    var urlRequest = URLRequest(url: URL(string: "\(baseURL)/api/v1/sessions")!)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)

    let (data, response) = try await URLSession.shared.data(for: urlRequest)

    guard let httpResponse = response as? HTTPURLResponse else {
        throw URLError(.badServerResponse)
    }

    guard httpResponse.statusCode == 201 else {
        throw NSError(domain: "", code: httpResponse.statusCode)
    }

    return try JSONDecoder().decode(SessionDetail.self, from: data)
}
```

---

### 12. 列出逐字稿

**Endpoint:** `GET /api/v1/sessions`

**描述:** 列出所有會談逐字稿，支援按個案篩選。

**Query Parameters:**
- `client_id` (optional): 篩選特定個案的逐字稿
- `skip` (optional, default: 0): 分頁偏移
- `limit` (optional, default: 20, max: 100): 每頁筆數

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "total": 15,
  "items": [
    {
      "id": "uuid",
      "client_id": "uuid",
      "case_id": "uuid",
      "session_number": 3,
      "session_date": "2024-01-20T00:00:00Z",
      "transcript_text": "...",
      "duration_minutes": 50,
      "notes": null,
      "has_report": true,
      "created_at": "2024-01-20T14:00:00Z",
      "updated_at": null
    }
  ]
}
```

**Swift Example:**
```swift
func listSessions(
    token: String,
    clientId: UUID? = nil,
    skip: Int = 0,
    limit: Int = 20
) async throws -> SessionListResponse {
    var components = URLComponents(string: "\(baseURL)/api/v1/sessions")!

    var queryItems: [URLQueryItem] = []
    if let clientId = clientId {
        queryItems.append(URLQueryItem(name: "client_id", value: clientId.uuidString))
    }
    queryItems.append(URLQueryItem(name: "skip", value: "\(skip)"))
    queryItems.append(URLQueryItem(name: "limit", value: "\(limit)"))
    components.queryItems = queryItems

    var request = URLRequest(url: components.url!)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(SessionListResponse.self, from: data)
}
```

---

### 13. 查看逐字稿

**Endpoint:** `GET /api/v1/sessions/{session_id}`

**描述:** 查看單一逐字稿詳情。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):** 同 SessionDetail 結構

---

### 14. 更新逐字稿

**Endpoint:** `PATCH /api/v1/sessions/{session_id}`

**描述:** 更新逐字稿內容或備註。

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body (所有欄位皆為 optional):**
```json
{
  "transcript": "更新後的逐字稿...",
  "notes": "更新備註",
  "duration_minutes": 55
}
```

**Response (200):** 更新後的 SessionDetail

---

### 15. 刪除逐字稿

**Endpoint:** `DELETE /api/v1/sessions/{session_id}`

**描述:** 刪除逐字稿。⚠️ 注意：無法刪除已生成報告的逐字稿！

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (204):** No Content

**Errors:**
- **400 Bad Request:** 該逐字稿已有關聯報告，無法刪除
  ```json
  {
    "detail": "Cannot delete session with associated reports"
  }
  ```

---

### 16. 🎙️ Append 錄音片段 (iOS 友善) ⭐️ NEW

**Endpoint:** `POST /api/v1/sessions/{session_id}/recordings/append`

**描述:** iOS 專屬簡化 API，用於添加錄音片段到現有會談記錄。系統自動處理：
- ✅ 自動計算 `segment_number`（無需 iOS 追蹤）
- ✅ 自動聚合所有片段的 `transcript_text`
- ✅ 支援會談中斷後繼續錄音

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "start_time": "2025-01-15 10:00",
  "end_time": "2025-01-15 10:30",
  "duration_seconds": 1800,
  "transcript_text": "此片段的逐字稿內容...",
  "transcript_sanitized": "脫敏後的內容（選填）"
}
```

**欄位說明:**
- `start_time` (required): 開始時間，格式 `YYYY-MM-DD HH:MM` 或 ISO 8601
- `end_time` (required): 結束時間，格式 `YYYY-MM-DD HH:MM` 或 ISO 8601
- `duration_seconds` (required): 錄音時長（秒）
- `transcript_text` (required): 此片段的逐字稿
- `transcript_sanitized` (optional): 脫敏後的逐字稿，不提供則使用原始內容

**Response (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "recording_added": {
    "segment_number": 2,
    "start_time": "2025-01-15 10:00",
    "end_time": "2025-01-15 10:30",
    "duration_seconds": 1800,
    "transcript_text": "此片段的逐字稿內容...",
    "transcript_sanitized": "脫敏後的內容"
  },
  "total_recordings": 2,
  "transcript_text": "第一段內容...\n\n第二段內容...",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

**Swift 範例:**
```swift
struct AppendRecordingRequest: Codable {
    let start_time: String
    let end_time: String
    let duration_seconds: Int
    let transcript_text: String
    let transcript_sanitized: String?
}

struct AppendRecordingResponse: Codable {
    let session_id: UUID
    let recording_added: RecordingSegment
    let total_recordings: Int
    let transcript_text: String
    let updated_at: String
}

struct RecordingSegment: Codable {
    let segment_number: Int
    let start_time: String
    let end_time: String
    let duration_seconds: Int
    let transcript_text: String
    let transcript_sanitized: String?
}

func appendRecording(
    token: String,
    sessionId: UUID,
    startTime: String,
    endTime: String,
    durationSeconds: Int,
    transcript: String,
    transcriptSanitized: String? = nil
) async throws -> AppendRecordingResponse {
    let url = URL(string: "\(baseURL)/api/v1/sessions/\(sessionId.uuidString)/recordings/append")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = AppendRecordingRequest(
        start_time: startTime,
        end_time: endTime,
        duration_seconds: durationSeconds,
        transcript_text: transcript,
        transcript_sanitized: transcriptSanitized
    )
    request.httpBody = try JSONEncoder().encode(body)

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(AppendRecordingResponse.self, from: data)
}
```

**💡 使用場景:**
1. **實時錄音上傳**: 會談過程中每 10-15 分鐘上傳一次片段
2. **中斷後繼續**: 會談中斷（電話、休息）後，新開錄音自動為新片段
3. **離線錄音同步**: 離線錄製多個片段，恢復網路後逐一上傳
4. **分段轉寫**: 長時間會談分批進行語音轉文字，轉好一段上傳一段

**vs 傳統 PATCH 方式的差異:**

| 功能 | Append API (NEW) | PATCH API (舊) |
|------|-----------------|---------------|
| **segment_number** | ✅ 自動計算 | ❌ 需手動管理 |
| **transcript 聚合** | ✅ 自動聚合 | ❌ 需手動拼接 |
| **並發安全** | ✅ 樂觀鎖保護 | ⚠️ 可能衝突 |
| **iOS 友善度** | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## 🧠 諮詢師反思 APIs

### 17. 取得反思內容

**Endpoint:** `GET /api/v1/sessions/{session_id}/reflection`

**描述:** 取得諮詢師對特定會談的反思內容。反思是諮詢師人工撰寫的內容，用於深度自我覺察和督導討論。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "session_id": "uuid",
  "reflection": {
    "working_with_client": "整體過程流暢輕鬆，逐漸贏得信任。首次面對職場PUA案例，獲得新的輔導經驗。",
    "feeling_source": "個案從緊張到逐步放鬆，願意開放心態分享更多。能夠建立良好的治療同盟。",
    "current_challenges": "當肯定個案時，仍會有自我懷疑反應；但已逐漸能接受讚賞。需要更多時間探索其內在認知模式。",
    "supervision_topics": "如何在支持與挑戰間拿捏節奏，以及量表與質化紀錄整合方式。特別是如何處理職場創傷。"
  },
  "updated_at": "2024-10-30T18:20:00Z"
}
```

**Response (200) - 沒有反思時:**
```json
{
  "session_id": "uuid",
  "reflection": null,
  "updated_at": null
}
```

**Swift 範例:**
```swift
struct ReflectionResponse: Codable {
    let session_id: UUID
    let reflection: Reflection?
    let updated_at: String?
}

struct Reflection: Codable {
    let working_with_client: String?
    let feeling_source: String?
    let current_challenges: String?
    let supervision_topics: String?
}

func getReflection(token: String, sessionId: UUID) async throws -> ReflectionResponse {
    let url = URL(string: "\(baseURL)/api/v1/sessions/\(sessionId.uuidString)/reflection")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(ReflectionResponse.self, from: data)
}
```

---

### 18. 更新反思內容 ⭐️ NEW

**Endpoint:** `PUT /api/v1/sessions/{session_id}/reflection`

**描述:** 更新或新增諮詢師對特定會談的反思。可以只填寫部分問題，未填寫的問題不會被儲存。

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "working_with_client": "整體過程流暢輕鬆，逐漸贏得信任。首次面對職場PUA案例，獲得新的輔導經驗。",
  "feeling_source": "個案從緊張到逐步放鬆，願意開放心態分享更多。",
  "current_challenges": "當肯定個案時，仍會有自我懷疑反應；但已逐漸能接受讚賞。",
  "supervision_topics": "如何在支持與挑戰間拿捏節奏，以及量表與質化紀錄整合方式。"
}
```

**📝 說明:**
- 所有欄位都是 optional
- 只會保存有內容的欄位（空字串或 null 會被忽略）
- 可以用來清空反思：傳送所有欄位為空字串或 null

**Response (200):**
```json
{
  "session_id": "uuid",
  "reflection": {
    "working_with_client": "整體過程流暢輕鬆，逐漸贏得信任。首次面對職場PUA案例，獲得新的輔導經驗。",
    "feeling_source": "個案從緊張到逐步放鬆，願意開放心態分享更多。",
    "current_challenges": "當肯定個案時，仍會有自我懷疑反應；但已逐漸能接受讚賞。",
    "supervision_topics": "如何在支持與挑戰間拿捏節奏，以及量表與質化紀錄整合方式。"
  },
  "updated_at": "2024-10-30T18:25:00Z"
}
```

**Swift 範例:**
```swift
struct ReflectionUpdateRequest: Codable {
    let working_with_client: String?
    let feeling_source: String?
    let current_challenges: String?
    let supervision_topics: String?
}

func updateReflection(token: String, sessionId: UUID, reflection: ReflectionUpdateRequest) async throws -> ReflectionResponse {
    let url = URL(string: "\(baseURL)/api/v1/sessions/\(sessionId.uuidString)/reflection")!
    var request = URLRequest(url: url)
    request.httpMethod = "PUT"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    request.httpBody = try JSONEncoder().encode(reflection)

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(ReflectionResponse.self, from: data)
}
```

**💡 使用場景:**
1. **撰寫反思**: 會談後諮詢師填寫反思問題
2. **補充反思**: 稍後回顧時補充遺漏的問題
3. **督導前整理**: 督導前重新整理反思內容
4. **生成報告時**: 反思內容會被包含在報告的「四、個人化分析」章節

---

## 🔍 片段分析 APIs (Multi-Tenant) ⭐️ NEW

### 19. 即時片段分析（推薦使用）

**Endpoint:** `POST /api/v1/sessions/{session_id}/analyze-partial`

**描述:** 使用 AI 分析逐字稿片段，**根據租戶自動選擇**分析方式和回傳格式。island_parents 租戶回傳紅黃綠燈安全評估，career 租戶回傳關鍵字分析。分析結果會**自動儲存**至 session 的 `analysis_logs` 欄位。

**技術棧:**
- **AI 引擎**: Google Vertex AI (Gemini 2.5 Flash)
- **Multi-Tenant**: 基於 JWT token tenant_id 自動切換 RAG 知識庫與 prompt
- **上下文來源**: Session → Case → Client 完整脈絡
- **儲存機制**: 自動追加至 analysis_logs JSONB 欄位
- **備援機制**: AI 失敗時使用啟發式關鍵字提取

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "transcript_segment": "最近 60 秒的逐字稿內容",
  "mode": "emergency"  // Optional (island_parents only): "emergency" or "practice", defaults to "practice"
}
```

**Mode Parameter (island_parents tenant only):**
- `emergency`: Fast, simplified analysis (1-2 critical suggestions for immediate crisis situations)
- `practice`: Detailed teaching mode (3-4 suggestions with parenting techniques, default)
- Career tenant: This parameter is ignored (not applicable)

**Response（island_parents 租戶 - Practice Mode, Default）:**
```json
{
  "safety_level": "red",
  "severity": 2,
  "display_text": "您注意到孩子提到「不想去學校」，這可能是焦慮或學校適應問題的徵兆。",
  "action_suggestion": "建議先同理孩子的感受，避免直接質問原因。可以說：「聽起來你最近在學校過得不太開心？」",
  "suggested_interval_seconds": 15,
  "rag_documents": [
    {
      "title": "依附理論與孩子安全感建立",
      "excerpt": "當孩子表達負面情緒時..."
    }
  ],
  "keywords": ["焦慮", "學校適應", "拒學"],
  "categories": ["情緒", "學校議題"]
}
```

**Response（island_parents 租戶 - Emergency Mode）:**
```json
{
  "safety_level": "red",
  "severity": 3,
  "display_text": "⚠️ 緊急：孩子表達不想活了",
  "action_suggestion": "立即停止對話，尋求專業協助（心理諮商師、自殺防治專線）",
  "suggested_interval_seconds": 5,
  "rag_documents": [],
  "keywords": ["自殺意念", "危機"],
  "categories": ["心理健康危機"]
}
```

**Response（career 租戶）- 職涯諮詢場景:**
```json
{
  "keywords": [
    "工作壓力",
    "主管批評",
    "挫折感",
    "焦慮",
    "自我懷疑",
    "離職念頭"
  ],
  "categories": [
    "職場議題",
    "情緒困擾",
    "人際關係",
    "自我認知"
  ],
  "confidence": 0.92,
  "counselor_insights": "個案正經歷職場 PUA（職場霸凌），建議探索：(1) 主管行為模式與頻率 (2) 個案的應對策略 (3) 是否有組織內部支持資源。需評估心理健康風險。",
  "safety_level": "yellow",
  "severity": 2,
  "display_text": "個案提到工作壓力與主管批評",
  "action_suggestion": "建議探索職場環境與支持資源"
}
```

**自動儲存格式 (analysis_logs):**
```json
{
  "analyzed_at": "2025-11-29T10:30:00Z",
  "transcript_segment": "個案提到最近工作壓力很大...",
  "keywords": ["工作壓力", "主管批評", ...],
  "categories": ["職場議題", "情緒困擾", ...],
  "confidence": 0.92,
  "counselor_insights": "個案正經歷職場 PUA...",
  "counselor_id": "uuid",
  "fallback": false  // true 表示使用備援機制
}
```

**Swift 範例（island_parents 租戶）:**
```swift
enum CounselingMode: String, Codable {
    case emergency = "emergency"
    case practice = "practice"
}

struct PartialAnalysisRequest: Codable {
    let transcript_segment: String
    let mode: CounselingMode?  // Optional, defaults to practice
}

struct IslandParentsAnalysisResponse: Codable {
    let safety_level: String              // "red", "yellow", "green"
    let severity: Int                      // 1-3
    let display_text: String
    let action_suggestion: String
    let suggested_interval_seconds: Int    // 建議下次分析間隔
    let rag_documents: [RAGDocument]?
    let keywords: [String]
    let categories: [String]
}

struct RAGDocument: Codable {
    let title: String
    let excerpt: String
}

func analyzePartial(token: String, sessionId: UUID, segment: String) async throws -> IslandParentsAnalysisResponse {
    let url = URL(string: "\(baseURL)/api/v1/sessions/\(sessionId.uuidString)/analyze-partial")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = PartialAnalysisRequest(transcript_segment: segment)
    request.httpBody = try JSONEncoder().encode(body)

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(IslandParentsAnalysisResponse.self, from: data)
}
```

**iOS 端建議用法（island_parents）:**
```swift
// 每分鐘 Timer 觸發
func onTimerTick() {
    let segment = getLastMinuteTranscript()

    // 並行發送兩個請求
    Task {
        async let appendResult = appendRecording(segment)
        async let analysisResult = analyzePartial(token, sessionId, segment)

        // 等待兩個結果
        let (_, analysis) = try await (appendResult, analysisResult)

        // 更新 UI
        updateSafetyCard(analysis)

        // 根據紅黃綠燈調整 Timer 間隔
        if analysis.safety_level == "red" {
            setTimerInterval(15) // 紅燈改 15 秒
        } else if analysis.safety_level == "yellow" {
            setTimerInterval(30) // 黃燈 30 秒
        } else {
            setTimerInterval(60) // 綠燈 60 秒
        }
    }
}
```

**💡 使用場景:**
1. **會談中即時分析**: 每 5-10 分鐘分析一次當前對話片段，獲得即時洞見
2. **重點片段標記**: 個案提到重要議題時，立即分析並標記關鍵字
3. **主題追蹤**: 追蹤會談過程中反覆出現的關鍵字與類別
4. **督導準備**: 會談後分析重要片段，準備督導討論材料
5. **歷程回顧**: 查看完整分析歷程，了解議題演變

**⚠️ 注意事項:**
- 每次分析會自動儲存至 `analysis_logs`，無需手動儲存
- `transcript_segment` 建議 50-500 字，過短分析效果差，過長影響效能
- `confidence` < 0.5 時建議參考 `fallback` 欄位，可能使用了備援機制
- 分析結果包含諮詢師 ID (`counselor_id`)，用於多諮詢師協作場景
- **Multi-Tenant 自動切換**：根據 JWT token 的 tenant_id 自動選擇 RAG 知識庫與回傳格式
- **Mode Parameter (island_parents only)**:
  - `emergency`: Use during crisis situations (e.g., child expressing self-harm thoughts, severe emotional distress)
  - `practice`: Use for regular practice sessions (default, more detailed feedback with techniques)
  - Career tenant ignores this parameter (analysis is always keyword-based)

**向後兼容 (Backward Compatibility):**

舊的 `POST /api/v1/sessions/{session_id}/analyze-keywords` 仍可使用：
- 內部調用 analyze-partial
- 固定回傳 career 格式（關鍵字分析）
- 建議新開發使用 analyze-partial

---

### 20. 取得分析歷程記錄

**Endpoint:** `GET /api/v1/sessions/{session_id}/analysis-logs`

**描述:** 取得特定會談的所有關鍵字分析歷程記錄，依時間順序排列（由舊到新）。可用於回顧分析歷程、追蹤議題演變。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "session_id": "uuid",
  "total_logs": 3,
  "logs": [
    {
      "log_index": 0,
      "analyzed_at": "2025-11-29T10:15:00Z",
      "transcript_segment": "個案提到童年時期父母經常吵架...",
      "keywords": ["童年創傷", "父母衝突", "不安全感"],
      "categories": ["家庭議題", "童年經驗"],
      "confidence": 0.88,
      "counselor_insights": "探索童年依附模式對當前關係的影響",
      "counselor_id": "uuid",
      "fallback": false
    },
    {
      "log_index": 1,
      "analyzed_at": "2025-11-29T10:30:00Z",
      "transcript_segment": "個案提到最近工作壓力很大...",
      "keywords": ["工作壓力", "主管批評", "挫折感"],
      "categories": ["職場議題", "情緒困擾"],
      "confidence": 0.92,
      "counselor_insights": "個案正經歷職場 PUA，需評估心理健康風險",
      "counselor_id": "uuid",
      "fallback": false
    },
    {
      "log_index": 2,
      "analyzed_at": "2025-11-29T10:45:00Z",
      "transcript_segment": "個案表示想要嘗試轉職...",
      "keywords": ["轉職", "生涯規劃", "自我探索"],
      "categories": ["職涯發展", "決策議題"],
      "confidence": 0.85,
      "counselor_insights": "協助個案澄清轉職動機與生涯價值觀",
      "counselor_id": "uuid",
      "fallback": false
    }
  ]
}
```

**Response (404):**
```json
{
  "detail": "Session not found or access denied"
}
```

**Swift 範例:**
```swift
struct AnalysisLogsResponse: Codable {
    let session_id: UUID
    let total_logs: Int
    let logs: [AnalysisLogEntry]
}

struct AnalysisLogEntry: Codable, Identifiable {
    let log_index: Int
    let analyzed_at: String
    let transcript_segment: String
    let keywords: [String]
    let categories: [String]
    let confidence: Double
    let counselor_insights: String
    let counselor_id: UUID
    let fallback: Bool

    var id: Int { log_index }  // 用於 SwiftUI List

    var analyzedDate: Date? {
        ISO8601DateFormatter().date(from: analyzed_at)
    }

    var isHighConfidence: Bool {
        confidence >= 0.8 && !fallback
    }
}

func getAnalysisLogs(token: String, sessionId: UUID) async throws -> AnalysisLogsResponse {
    let url = URL(string: "\(baseURL)/api/v1/sessions/\(sessionId.uuidString)/analysis-logs")!
    var request = URLRequest(url: url)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(AnalysisLogsResponse.self, from: data)
}
```

**SwiftUI 顯示範例:**
```swift
struct AnalysisLogsView: View {
    let logs: [AnalysisLogEntry]

    var body: some View {
        List(logs) { log in
            VStack(alignment: .leading, spacing: 8) {
                // 時間與信心分數
                HStack {
                    Text(log.analyzedDate?.formatted() ?? "")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    HStack(spacing: 4) {
                        Image(systemName: log.fallback ? "exclamationmark.triangle" : "checkmark.circle")
                            .foregroundColor(log.isHighConfidence ? .green : .orange)
                        Text(String(format: "%.0f%%", log.confidence * 100))
                            .font(.caption)
                    }
                }

                // 關鍵字標籤
                FlowLayout(spacing: 4) {
                    ForEach(log.keywords, id: \.self) { keyword in
                        Text(keyword)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.blue.opacity(0.2))
                            .cornerRadius(4)
                    }
                }

                // 諮詢師洞見
                Text(log.counselor_insights)
                    .font(.body)
                    .foregroundColor(.primary)

                // 類別
                HStack {
                    ForEach(log.categories, id: \.self) { category in
                        Text(category)
                            .font(.caption2)
                            .foregroundColor(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.purple)
                            .cornerRadius(3)
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }
}
```

**💡 使用場景:**
1. **歷程回顧**: 會談後回顧所有分析記錄，整理重點
2. **議題追蹤**: 查看關鍵字演變，了解議題發展軌跡
3. **報告準備**: 根據分析歷程撰寫會談報告
4. **督導討論**: 展示分析歷程，與督導討論諮詢策略
5. **品質檢核**: 檢視 `confidence` 和 `fallback` 欄位，評估分析品質

---

### 21. 刪除分析記錄

**Endpoint:** `DELETE /api/v1/sessions/{session_id}/analysis-logs/{log_index}`

**描述:** 刪除特定的分析記錄。`log_index` 為 0-based 索引（從 0 開始）。刪除後，後續記錄的 `log_index` 會自動調整。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Path Parameters:**
- `session_id`: Session UUID
- `log_index`: 記錄索引（0-based），可從 `GET /analysis-logs` 取得

**Response (204 No Content):**
```
(空內容，狀態碼 204 表示刪除成功)
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid log index: 5. Valid range: 0-2"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Session not found or access denied"
}
```

**Swift 範例:**
```swift
func deleteAnalysisLog(token: String, sessionId: UUID, logIndex: Int) async throws {
    let url = URL(string: "\(baseURL)/api/v1/sessions/\(sessionId.uuidString)/analysis-logs/\(logIndex)")!
    var request = URLRequest(url: url)
    request.httpMethod = "DELETE"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (_, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse else {
        throw URLError(.badServerResponse)
    }

    if httpResponse.statusCode != 204 {
        throw URLError(.badServerResponse)
    }
}
```

**SwiftUI 整合範例:**
```swift
struct AnalysisLogsManagementView: View {
    @State private var logs: [AnalysisLogEntry] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    let sessionId: UUID
    let token: String

    var body: some View {
        List {
            ForEach(logs) { log in
                AnalysisLogRow(log: log)
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button(role: .destructive) {
                            Task {
                                await deleteLog(at: log.log_index)
                            }
                        } label: {
                            Label("刪除", systemImage: "trash")
                        }
                    }
            }
        }
        .task {
            await loadLogs()
        }
        .alert("錯誤", isPresented: .constant(errorMessage != nil)) {
            Button("確定") {
                errorMessage = nil
            }
        } message: {
            if let error = errorMessage {
                Text(error)
            }
        }
    }

    func loadLogs() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let response = try await getAnalysisLogs(token: token, sessionId: sessionId)
            logs = response.logs
        } catch {
            errorMessage = "載入失敗: \(error.localizedDescription)"
        }
    }

    func deleteLog(at index: Int) async {
        do {
            try await deleteAnalysisLog(token: token, sessionId: sessionId, logIndex: index)
            // 重新載入列表
            await loadLogs()
        } catch {
            errorMessage = "刪除失敗: \(error.localizedDescription)"
        }
    }
}
```

**💡 使用場景:**
1. **錯誤修正**: 刪除分析錯誤或不相關的記錄
2. **隱私保護**: 刪除包含敏感資訊的分析記錄
3. **測試清理**: 開發測試時清理測試資料
4. **歷程整理**: 保留重要記錄，刪除冗餘分析

**⚠️ 注意事項:**
- 刪除操作**不可逆**，請謹慎使用
- 刪除記錄後，`log_index` 會重新排序（例如刪除 index 1，原本的 index 2 會變成新的 index 1）
- 建議在 UI 加上二次確認對話框
- 只能刪除自己權限範圍內的 session 記錄

---

## 📄 報告 APIs

### 22. 生成報告（異步 API ⚡️）

**Endpoint:** `POST /api/v1/reports/generate`

**⚠️ 重要說明:**
- **必須先儲存逐字稿**: 使用 `POST /api/v1/sessions` 儲存會談記錄
- **從已儲存的逐字稿生成報告**: 提供 `session_id` 即可
- **異步處理**: HTTP 202 Accepted (立即返回)
- **背景生成**: 報告在背景生成 (10-30秒)
- **輪詢狀態**: 需輪詢 `GET /api/v1/reports/{id}` 查詢生成狀態

**推薦工作流程:**
1. 先使用 `POST /api/v1/sessions` 儲存逐字稿
2. 從逐字稿列表中選擇 `has_report: false` 的記錄
3. 使用該 session_id 調用此 API 生成報告

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "session_id": "uuid",           // 必填：已儲存的逐字稿 ID
  "report_type": "enhanced",      // optional: "enhanced" (10段式) 或 "legacy" (5段式)
  "rag_system": "openai"          // optional: "openai" (GPT-4o-mini) 或 "gemini" (Gemini 2.5 Flash)
}
```

**參數說明:**
- `session_id` **(必填)**: 已儲存的逐字稿 UUID (透過 `POST /api/v1/sessions` 創建)
- `report_type`: 報告類型
  - `"enhanced"` (預設): 10段式報告
  - `"legacy"`: 5段式報告
- `rag_system`: RAG 檢索系統
  - `"openai"` (預設): 使用 GPT-4o-mini
  - `"gemini"`: 使用 Gemini 2.5 Flash

**Response (202 Accepted):**
```json
{
  "session_id": "uuid",
  "report_id": "uuid",
  "report": {
    "status": "processing",
    "message": "報告生成中，請稍後查詢結果"
  },
  "quality_summary": null
}
```

**完成後的報告格式 (GET /api/v1/reports/{id}):**
```json
{
  "id": "uuid",
  "status": "draft",  // "processing" | "draft" | "failed"
  "content_json": {
    "mode": "enhanced",
    "format": "json",
    "report": {
      "client_info": {
        "name": "陳小明",
        "gender": "男性",
        "age": 28,
        "occupation": "產品設計師"
      },
      "main_concerns": ["工作壓力", "主管衝突"],
      "conceptualization": "案主因長期承受主管情緒壓力...",
      "theories": [
        {
          "text": "根據認知行為理論...",
          "score": 0.85,
          "document": "職涯諮詢理論.pdf"
        }
      ],
      "dialogue_excerpts": [
        {
          "speaker": "Co",
          "content": "這份工作讓你最疲累的部分是什麼？"
        },
        {
          "speaker": "Cl",
          "content": "是主管的情緒，覺得不管怎麼做都被否定。"
        }
      ]
    },
    "token_usage": {
      "prompt_tokens": 1500,
      "completion_tokens": 800
    }
  },
  "content_markdown": "# 個案報告\n\n## 案主基本資料\n\n- **name**: 陳小明\n- **gender**: 男性\n...",  // ⭐️ NEW: AI 原始生成的 Markdown
  "edited_content_markdown": null,  // ⭐️ NEW: 編輯後的 Markdown (未編輯時為 null)
  "quality_summary": {
    "overall_score": 85,
    "grade": "B+",
    "strengths": ["理論引用豐富", "分析深入"],
    "improvements_needed": ["可增加具體介入策略"]
  }
}
```

**⭐️ 新增欄位說明:**
- `content_markdown`: AI 原始生成的 Markdown 格式 (與 content_json 同步生成)
- `edited_content_markdown`: 諮詢師編輯後的 Markdown 格式 (編輯後才會有值)
- **iOS 可直接使用 Markdown 欄位渲染，無需處理 JSON**

**Swift 範例:**
```swift
// 模式 1: 使用現有逐字稿 (推薦)
struct GenerateReportRequestWithSession: Codable {
    let session_id: UUID
    let report_type: String // "enhanced" or "legacy"
    let rag_system: String // "openai" or "gemini"
}

// 模式 2: 上傳新逐字稿
struct GenerateReportRequestWithTranscript: Codable {
    let client_id: UUID
    let transcript: String
    let session_date: String // YYYY-MM-DD
    let report_type: String // "enhanced" or "legacy"
    let rag_system: String // "openai" or "gemini"
}

struct GenerateReportResponse: Codable {
    let session_id: UUID
    let report_id: UUID
    let report: ProcessingStatus  // 立即返回的是狀態
    let quality_summary: QualitySummary?
}

struct ProcessingStatus: Codable {
    let status: String
    let message: String
}

// 完整報告結構 (輪詢後取得)
struct ReportDetail: Codable {
    let id: UUID
    let status: String  // "processing" | "draft" | "failed"
    let content_json: ReportData?
    let content_markdown: String?  // ⭐️ NEW: AI 原始生成的 Markdown
    let edited_content_markdown: String?  // ⭐️ NEW: 編輯後的 Markdown
    let quality_score: Int?
    let quality_grade: String?
    let error_message: String?  // 如果 status == "failed"
}

struct ReportData: Codable {
    let mode: String
    let format: String
    let report: ReportContent
}

struct ReportContent: Codable {
    let client_info: ClientInfo
    let main_concerns: [String]
    let conceptualization: String
    let theories: [Theory]
    let dialogue_excerpts: [DialogueExcerpt]
}

// 1a. 提交報告生成請求 (模式 1: 使用現有逐字稿，推薦)
func generateReportFromSession(
    token: String,
    sessionId: UUID,
    reportType: String = "enhanced",
    ragSystem: String = "openai"
) async throws -> GenerateReportResponse {
    let request = GenerateReportRequestWithSession(
        session_id: sessionId,
        report_type: reportType,
        rag_system: ragSystem
    )

    let url = URL(string: "\(baseURL)/api/v1/reports/generate")!
    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)

    let (data, response) = try await URLSession.shared.data(for: urlRequest)

    guard (response as? HTTPURLResponse)?.statusCode == 202 else {
        throw URLError(.badServerResponse)
    }

    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(GenerateReportResponse.self, from: data)
}

// 1b. 提交報告生成請求 (模式 2: 上傳新逐字稿)
func generateReportWithTranscript(
    token: String,
    clientId: UUID,
    transcript: String,
    sessionDate: String,
    reportType: String = "enhanced",
    ragSystem: String = "openai"
) async throws -> GenerateReportResponse {
    let request = GenerateReportRequestWithTranscript(
        client_id: clientId,
        transcript: transcript,
        session_date: sessionDate,
        report_type: reportType,
        rag_system: ragSystem
    )

    let url = URL(string: "\(baseURL)/api/v1/reports/generate")!
    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    urlRequest.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    urlRequest.addValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)

    let (data, response) = try await URLSession.shared.data(for: urlRequest)

    guard (response as? HTTPURLResponse)?.statusCode == 202 else {
        throw URLError(.badServerResponse)
    }

    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(GenerateReportResponse.self, from: data)
}

// 2. 輪詢報告狀態
func pollReportStatus(
    token: String,
    reportId: UUID,
    maxAttempts: Int = 20,
    intervalSeconds: TimeInterval = 3
) async throws -> ReportDetail {
    for attempt in 1...maxAttempts {
        let report = try await getReport(token: token, reportId: reportId)

        switch report.status {
        case "draft":
            // 生成完成
            return report
        case "failed":
            // 生成失敗
            throw NSError(
                domain: "ReportGeneration",
                code: -1,
                userInfo: [NSLocalizedDescriptionKey: report.error_message ?? "生成失敗"]
            )
        case "processing":
            // 繼續等待
            if attempt < maxAttempts {
                try await Task.sleep(nanoseconds: UInt64(intervalSeconds * 1_000_000_000))
            }
        default:
            break
        }
    }

    throw NSError(
        domain: "ReportGeneration",
        code: -2,
        userInfo: [NSLocalizedDescriptionKey: "報告生成超時"]
    )
}

// 3. 完整流程範例
func generateAndWaitForReport(
    token: String,
    clientId: UUID,
    transcript: String
) async throws -> ReportDetail {
    // Step 1: 提交生成請求
    let request = GenerateReportRequest(
        client_id: clientId,
        transcript: transcript,
        session_date: Date().ISO8601Format().prefix(10).description,
        report_type: "enhanced",
        rag_system: "openai"
    )

    let response = try await generateReport(token: token, request: request)
    print("報告已提交，ID: \(response.report_id)")

    // Step 2: 輪詢狀態直到完成
    let finalReport = try await pollReportStatus(
        token: token,
        reportId: response.report_id
    )

    print("報告生成完成！評分: \(finalReport.quality_grade ?? "N/A")")
    return finalReport
}
```

---

### 23. 列出報告

**Endpoint:** `GET /api/v1/reports`

**Query Parameters:**
- `skip` (int, optional): 分頁偏移，預設 0
- `limit` (int, optional): 每頁筆數，預設 20
- `client_id` (uuid, optional): 篩選特定個案的報告

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "total": 5,
  "items": [
    {
      "id": "uuid",
      "session_id": "uuid",
      "client_id": "uuid",
      "version": 1,
      "mode": "enhanced",
      "status": "draft",
      "created_at": "2025-10-29T00:00:00Z"
    }
  ]
}
```

---

### 24. 取得單一報告

**Endpoint:** `GET /api/v1/reports/{report_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):** 完整報告 JSON

---

### 25. 更新報告 (諮詢師編輯)

**Endpoint:** `PATCH /api/v1/reports/{report_id}`

**描述:** 諮詢師編輯 AI 生成的報告內容

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

#### 🎯 重要：前端應該直接傳 Markdown 字串

**前端編輯流程**：
1. 使用者在 iOS App 上編輯 Markdown 內容
2. 前端直接將編輯後的 Markdown 字串傳給後端
3. **不需要**前端自己生成 JSON 或從 Markdown 轉換

---

#### ✅ **推薦方式 1：只傳 Markdown（前端編輯）**

前端使用者編輯 Markdown 內容後，直接傳給後端：

**Request:**
```json
{
  "edited_content_markdown": "# 個案報告\n\n## 個案概念化\n\n個案呈現焦慮症狀..."
}
```

**Swift 範例:**
```swift
struct ReportUpdateRequest: Codable {
    let edited_content_markdown: String?
    let edited_content_json: [String: Any]?
}

func updateReportMarkdown(reportId: UUID, markdown: String, token: String) async throws {
    let url = URL(string: "\(baseURL)/api/v1/reports/\(reportId)")!
    var request = URLRequest(url: url)
    request.httpMethod = "PATCH"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body: [String: Any] = ["edited_content_markdown": markdown]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)

    let (_, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw APIError.updateFailed
    }
}
```

**使用範例:**
```swift
// User edits markdown in the app
let editedMarkdown = """
# 個案報告

## 個案概念化
個案呈現焦慮症狀，主要表現為...

## 治療計畫
1. 使用認知行為治療 (CBT)
2. 每週一次，共 8 週
3. 搭配放鬆訓練

_編輯時間：2024-01-01_
"""

// Send to backend
try await updateReportMarkdown(reportId: reportId, markdown: editedMarkdown, token: token)
```

---

#### ✅ **方式 2：同時傳 JSON 和 Markdown**

如果前端同時維護 JSON 結構和 Markdown 顯示：

**Request:**
```json
{
  "edited_content_json": {
    "client_name": "個案 A",
    "conceptualization": "焦慮症狀",
    "treatment_plan": "CBT 介入"
  },
  "edited_content_markdown": "# 個案報告\n\n## 個案概念化\n\n焦慮症狀..."
}
```

**注意**：Markdown 不會從 JSON 自動生成，會使用前端傳的 `edited_content_markdown`

---

#### ⚠️ **方式 3：只傳 JSON（向後相容）**

如果前端只傳 JSON，後端會自動生成 Markdown（為了向後相容）：

**Request:**
```json
{
  "edited_content_json": {
    "report": {
      "client_info": {
        "name": "王小明",
        "age": 25,
        "gender": "男性",
        "occupation": "軟體工程師"
      },
      "main_concerns": ["職場適應困難", "職涯方向迷茫"],
      "conceptualization": "案主於職場中遭遇適應困難...",
      "intervention_strategies": ["認知重構", "職涯探索"],
      "session_summary": "本次會談聚焦於..."
    }
  }
}
```

**不推薦**：這種方式生成的 Markdown 是固定格式，無法自訂排版

---

#### Response (200)

```json
{
  "id": "uuid",
  "edited_content_json": {
    "client_name": "個案 A",
    "conceptualization": "焦慮症狀"
  },
  "edited_content_markdown": "# 個案報告\n\n## 個案概念化\n\n焦慮症狀...",
  "edited_at": "2024-01-01T12:00:00+00:00",
  "edit_count": 1
}
```

---

#### 關鍵特性

✅ **前端完全控制 Markdown 格式**
✅ **支援 Emoji、特殊字符、Code blocks**
✅ **持久化到 Supabase（使用 `flag_modified()`）**
✅ **向後相容（只傳 JSON 會自動生成 Markdown）**

---

#### 重要說明

- AI 原始生成的報告保存在 `content_json` 和 `content_markdown` (不可變)
- 諮詢師編輯的版本保存在 `edited_content_json` 和 `edited_content_markdown`
- **推薦使用 Markdown 欄位直接渲染**，無需解析 JSON

**⭐️ Markdown 欄位使用建議:**
```swift
// 渲染報告時，優先使用 Markdown
func getReportMarkdown(report: ReportDetail) -> String {
    // 1. 優先使用編輯過的版本
    if let editedMarkdown = report.edited_content_markdown {
        return editedMarkdown
    }
    // 2. 沒有編輯過就用原始版本
    return report.content_markdown ?? ""
}
```

---

### 26. 取得格式化報告

**Endpoint:** `GET /api/v1/reports/{report_id}/formatted`

**Query Parameters:**
- `format`: `"markdown"` 或 `"html"`
- `use_edited`: `true` (預設) 使用編輯版本, `false` 使用 AI 原始版本

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "report_id": "uuid",
  "format": "markdown",
  "formatted_content": "# 個案報告\n\n## 案主基本資料\n...",
  "is_edited": true,
  "edited_at": "2025-10-29T10:30:00Z"
}
```

**Swift 範例:**
```swift
func getFormattedReport(
    token: String,
    reportId: UUID,
    format: String = "markdown",
    useEdited: Bool = true
) async throws -> FormattedReportResponse {
    var components = URLComponents(string: "\(baseURL)/api/v1/reports/\(reportId)/formatted")!
    components.queryItems = [
        URLQueryItem(name: "format", value: format),
        URLQueryItem(name: "use_edited", value: String(useEdited))
    ]

    var request = URLRequest(url: components.url!)
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(FormattedReportResponse.self, from: data)
}
```

---

## 🔄 完整使用流程

### iOS App 完整流程範例

```swift
// Step 1: 登入
let token = try await login(tenantId: "career", email: "admin@career.com", password: "password123")

// Step 2: 取得當前用戶
let currentUser = try await getCurrentUser(token: token)
print("登入成功：\(currentUser.full_name)")

// Step 3: 列出個案
let clients = try await listClients(token: token)
print("共有 \(clients.total) 個個案")

// Step 4: 建立新個案（如果需要）
// 方式1: 不提供 code，讓後端自動生成 (推薦)
let newClient = CreateClientRequest(
    name: "王小明",
    code: nil,  // 後端自動生成 C0001, C0002...
    nickname: "小明",
    age: 25,
    gender: "male",
    occupation: "工程師",
    education: "大學",
    location: "台北市",
    economic_status: "中等",
    family_relations: "父母健在",
    tags: ["職涯諮詢", "轉職"]
)
// 方式2: 手動指定 code
// let newClient = CreateClientRequest(name: "王小明", code: "C001", ...)

let client = try await createClient(token: token, request: newClient)
print("個案建立成功：\(client.id)，代碼：\(client.code)")

// Step 5a: 儲存逐字稿 (推薦流程)
let sessionRequest = SessionCreateRequest(
    client_id: client.id,
    session_date: "2025-10-29",
    transcript: """
    Co： 今天想討論什麼？
    Cl： 我最近對工作感到很迷惘...
    """,
    duration_minutes: 50,
    notes: "首次會談"
)
let session = try await createSession(token: token, request: sessionRequest)
print("逐字稿已儲存：\(session.id)")

// Step 5b: 從逐字稿生成報告 (異步)
let reportResponse = try await generateReportFromSession(
    token: token,
    sessionId: session.id,
    reportType: "enhanced",
    ragSystem: "openai"
)
print("報告生成中：\(reportResponse.report_id)")

// Step 5c: 輪詢報告狀態直到完成
let completedReport = try await pollReportStatus(
    token: token,
    reportId: reportResponse.report_id,
    maxAttempts: 20,
    intervalSeconds: 3
)
print("報告生成完成！狀態：\(completedReport.status)")

// Step 6: 查看報告（格式化）
let formattedReport = try await getFormattedReport(
    token: token,
    reportId: reportResponse.report_id,
    format: "markdown"
)
print(formattedReport.formatted_content)
```

---

## ⚠️ 錯誤處理

### HTTP 狀態碼

- `200 OK`: 成功
- `201 Created`: 資源建立成功
- `202 Accepted`: 異步請求已接受 (報告生成中)
- `204 No Content`: 刪除成功
- `400 Bad Request`: 請求格式錯誤
- `401 Unauthorized`: Token 無效或過期
- `403 Forbidden`: 無權限存取
- `404 Not Found`: 資源不存在
- `422 Unprocessable Entity`: 驗證失敗
- `500 Internal Server Error`: 伺服器錯誤

### 錯誤 Response 格式

```json
{
  "detail": "錯誤訊息"
}
```

### Swift 錯誤處理範例

```swift
enum APIError: Error {
    case unauthorized
    case notFound
    case serverError(String)
    case unknown
}

func handleAPIError(statusCode: Int, data: Data?) -> APIError {
    switch statusCode {
    case 401:
        return .unauthorized
    case 404:
        return .notFound
    case 500...599:
        if let data = data,
           let json = try? JSONDecoder().decode([String: String].self, from: data),
           let detail = json["detail"] {
            return .serverError(detail)
        }
        return .serverError("Server error")
    default:
        return .unknown
    }
}
```

---

## 📝 測試帳號

### Staging 環境
**Base URL:** `https://career-app-api-staging-kxaznpplqq-uc.a.run.app`

| Tenant | Email | Password | 用途 |
|--------|-------|----------|------|
| `career` | `admin@career.com` | `password123` | 職涯諮詢租戶 |
| `island` | `admin@island.com` | `password123` | 升學浮島租戶 |

### 登入 API 範例

**重要：登入時必須提供 `tenant_id`**

```bash
POST /api/auth/login
Content-Type: application/json

{
  "tenant_id": "career",
  "email": "admin@career.com",
  "password": "password123"
}
```

**Swift 範例:**
```swift
struct LoginRequest: Codable {
    let tenant_id: String
    let email: String
    let password: String
}

func login(tenantId: String, email: String, password: String) async throws -> String {
    let url = URL(string: "\(baseURL)/api/auth/login")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = LoginRequest(tenant_id: tenantId, email: email, password: password)
    request.httpBody = try JSONEncoder().encode(body)

    let (data, _) = try await URLSession.shared.data(for: request)
    let response = try JSONDecoder().decode(LoginResponse.self, from: data)

    return response.access_token
}
```

---

## 🔗 相關連結

- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc
- **Debug Console:** http://localhost:8080/console

---

**最後更新:** 2025-10-29
