# iOS App API 完整指南

**Base URL (Staging):** `https://your-api-staging.example.com`

**Base URL (Local):** `http://localhost:8080`

> 🔒 **注意**: Staging URL 請向技術團隊索取

**認證方式:** Bearer Token (JWT)

---

## 📋 目錄

1. [認證 APIs](#認證-apis) (1-3)
2. [個案管理 APIs](#個案管理-apis) (4-9)
3. [會談記錄管理 APIs](#會談記錄管理-apis) (10-17)
4. [諮詢師反思 APIs](#諮詢師反思-apis) (18-19)
5. [報告 APIs](#報告-apis) (20-24)
6. [完整使用流程](#完整使用流程)
7. [錯誤處理](#錯誤處理)

---

## 🎉 最新更新 (2025-11-29) ⭐️ NEW

### 0. 🔍 Session 關鍵字分析 APIs

**新功能:** 即時逐字稿關鍵字分析 + 分析歷程記錄管理

**新增 API:**
- `POST /api/v1/sessions/{id}/analyze-keywords` - AI 驅動的即時關鍵字分析
- `GET /api/v1/sessions/{id}/analysis-logs` - 取得分析歷程記錄
- `DELETE /api/v1/sessions/{id}/analysis-logs/{log_index}` - 刪除特定分析記錄

**Session Name 欄位:**
- Session 模型新增 `name` 欄位（可選），用於會談命名組織

**自動儲存:**
- 呼叫 analyze-keywords 時，分析結果自動儲存至 `analysis_logs` 欄位
- 記錄包含：時間戳記、關鍵字、類別、信心分數、諮詢師洞見、AI/備援標記

**詳細文件:** 請參閱本文件「關鍵字分析 APIs」章節

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

## API 列表

### 🎨 動態表單 Schema APIs ⭐️ NEW
1. GET /api/v1/ui/field-schemas/client-case - 一次獲取 Client + Case schemas (推薦)
2. GET /api/v1/ui/field-schemas/client - 獲取 Client schema
3. GET /api/v1/ui/field-schemas/case - 獲取 Case schema

### 👤 認證 APIs
4. POST /api/auth/login - 登入
5. GET /api/auth/me - 取得諮詢師資訊
6. PATCH /api/auth/me - 更新諮詢師資訊

### 👥 個案管理 APIs
4. POST /api/v1/clients - 建立個案
5. GET /api/v1/clients - 列出個案
6. GET /api/v1/clients/{id} - 取得單一個案
7. PATCH /api/v1/clients/{id} - 更新個案
8. DELETE /api/v1/clients/{id} - 刪除個案
9. GET /api/v1/sessions/timeline - 取得個案會談歷程時間線 ⭐️ NEW

### 📝 會談記錄管理 APIs
10. POST /api/v1/sessions - 建立會談記錄
11. GET /api/v1/sessions - 列出會談記錄
12. GET /api/v1/sessions/{id} - 查看會談記錄
13. PATCH /api/v1/sessions/{id} - 更新會談記錄
14. DELETE /api/v1/sessions/{id} - 刪除會談記錄
15. POST /api/v1/sessions/{id}/recordings/append - 🎙️ Append 錄音片段 (iOS 友善) ⭐️ NEW

### 🧠 諮詢師反思 APIs
16. GET /api/v1/sessions/{id}/reflection - 取得反思內容
17. PUT /api/v1/sessions/{id}/reflection - 更新反思內容

### 🔍 關鍵字分析 APIs ⭐️ NEW
18. POST /api/v1/sessions/{id}/analyze-keywords - 即時關鍵字分析
19. GET /api/v1/sessions/{id}/analysis-logs - 取得分析歷程記錄
20. DELETE /api/v1/sessions/{id}/analysis-logs/{log_index} - 刪除特定分析記錄

### 📄 報告 APIs
21. POST /api/v1/reports/generate - 生成報告 (從已儲存的會談記錄生成，需提供 session_id)
22. GET /api/v1/reports - 列出報告
23. GET /api/v1/reports/{id} - 取得單一報告
24. PATCH /api/v1/reports/{id} - 更新報告 (編輯)
25. GET /api/v1/reports/{id}/formatted - 取得格式化報告 (Markdown/HTML)

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

### 4. 登入

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
  "expires_in": 86400
}
```

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

## 👥 個案管理 APIs

### 4. 建立個案

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

### 5. 列出個案

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

### 6. 取得單一個案

**Endpoint:** `GET /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):** 同建立個案的 Response

---

### 7. 更新個案

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

### 8. 刪除個案

**Endpoint:** `DELETE /api/v1/clients/{client_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (204):** No Content

---

### 9. 取得個案會談歷程時間線 ⭐️ NEW

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

### 10. 建立會談記錄

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

### 10. 列出逐字稿

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

### 11. 查看逐字稿

**Endpoint:** `GET /api/v1/sessions/{session_id}`

**描述:** 查看單一逐字稿詳情。

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):** 同 SessionDetail 結構

---

### 12. 更新逐字稿

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

### 13. 刪除逐字稿

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

### 15. 🎙️ Append 錄音片段 (iOS 友善) ⭐️ NEW

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

### 16. 取得反思內容

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

### 16. 更新反思內容 ⭐️ NEW

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

## 🔍 關鍵字分析 APIs ⭐️ NEW

### 18. 即時關鍵字分析

**Endpoint:** `POST /api/v1/sessions/{session_id}/analyze-keywords`

**描述:** 使用 AI 分析逐字稿片段，提取關鍵字、類別、信心分數與諮詢師洞見。分析結果會**自動儲存**至 session 的 `analysis_logs` 欄位，建立完整的分析歷程記錄。

**技術棧:**
- **AI 引擎**: Google Vertex AI (Gemini 2.5 Flash)
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
  "transcript_segment": "個案提到最近工作壓力很大，主管經常在公開場合批評他的表現，讓他感到很挫折和焦慮。他開始懷疑自己的能力，甚至想要離職。"
}
```

**Response (200):**
```json
{
  "keywords": [
    "工作壓力",
    "主管批評",
    "挫折感",
    "焦慮",
    "自我懷疑",
    "離職念頭",
    "公開批評",
    "職場壓力"
  ],
  "categories": [
    "職場議題",
    "情緒困擾",
    "人際關係",
    "自我認知"
  ],
  "confidence": 0.92,
  "counselor_insights": "個案正經歷職場 PUA（職場霸凌），建議探索：(1) 主管行為模式與頻率 (2) 個案的應對策略 (3) 是否有組織內部支持資源。需評估心理健康風險。"
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

**Swift 範例:**
```swift
struct KeywordAnalysisRequest: Codable {
    let transcript_segment: String
}

struct KeywordAnalysisResponse: Codable {
    let keywords: [String]           // 最多 10 個關鍵字
    let categories: [String]         // 最多 5 個類別
    let confidence: Double           // 0.0 - 1.0
    let counselor_insights: String   // 最多 200 字
}

func analyzeKeywords(token: String, sessionId: UUID, segment: String) async throws -> KeywordAnalysisResponse {
    let url = URL(string: "\(baseURL)/api/v1/sessions/\(sessionId.uuidString)/analyze-keywords")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = KeywordAnalysisRequest(transcript_segment: segment)
    request.httpBody = try JSONEncoder().encode(body)

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(KeywordAnalysisResponse.self, from: data)
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

---

### 19. 取得分析歷程記錄

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

### 20. 刪除分析記錄

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

### 17. 生成報告（異步 API ⚡️）

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

### 18. 列出報告

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

### 19. 取得單一報告

**Endpoint:** `GET /api/v1/reports/{report_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):** 完整報告 JSON

---

### 20. 更新報告 (諮詢師編輯)

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

### 21. 取得格式化報告

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
