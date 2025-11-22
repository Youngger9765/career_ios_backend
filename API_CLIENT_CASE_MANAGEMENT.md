# Client & Case Management API 文件

**Base URL**: `https://your-api-domain.com`

**核心功能**: 多租戶客戶與個案管理系統，支援動態欄位配置

---

## 📑 目錄

- [認證與多租戶架構](#認證與多租戶架構)
- [動態欄位配置 API](#動態欄位配置-api)
- [客戶管理 API](#客戶管理-api-client)
- [個案管理 API](#個案管理-api-case)
- [完整使用流程](#完整使用流程)

---

## 🔐 認證與多租戶架構

### 架構說明

本系統採用 **JWT 多租戶架構**，每個請求都需要：
1. **JWT Token** - 認證身份（`Authorization: Bearer <token>`）
2. **Tenant ID** - 自動從 JWT payload 中提取

### JWT Token 格式

```json
{
  "sub": "counselor@example.com",
  "tenant_id": "org_123",
  "role": "counselor",
  "exp": 1234567890
}
```

### 請求範例

```http
GET /api/v1/clients
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 租戶隔離機制

- ✅ 所有資料按 `tenant_id` 隔離
- ✅ Client、Case、Field Schema 都是租戶級別
- ✅ 無法跨租戶存取資料
- ✅ 自動從 JWT 提取 `tenant_id`，前端無需傳遞

---

## 🎨 動態欄位配置 API

### 核心概念

每個租戶可以**自訂** Client 和 Case 的欄位配置：
- 📝 不同租戶有不同的表單欄位
- 🎯 支援多種欄位類型（text, textarea, select, date, email, phone）
- 📋 欄位分組（sections）
- ✅ 欄位驗證（required, placeholder, help_text）

**⭐️ 最新更新 (2025-11-23):**
- API 路徑變更：`/api/v1/field-schemas/*` → `/api/v1/ui/field-schemas/*`
- 新增組合端點：`/api/v1/ui/field-schemas/client-case` (一次獲取兩個 Schema)
- Case status 改為整數：0=未進行, 1=進行中, 2=已完成

---

### 1. 取得 Client + Case 欄位配置 (組合端點) ⭐️ 推薦

**GET** `/api/v1/ui/field-schemas/client-case`

一次性取得當前租戶的 Client 和 Case 欄位配置，減少網絡請求。

#### Request

```http
GET /api/v1/ui/field-schemas/client-case
Authorization: Bearer <token>
```

#### Response 200 OK

```json
{
  "client": {
    "form_type": "client",
    "tenant_id": "career",
    "sections": [...]
  },
  "case": {
    "form_type": "case",
    "tenant_id": "career",
    "sections": [...]
  },
  "tenant_id": "career"
}
```

**使用場景:**
- iOS App 進入建立/更新個案頁面時，一次獲取兩個表單的 Schema
- 減少 API 調用次數，提升用戶體驗

---

### 2. 取得 Client 欄位配置

**GET** `/api/v1/ui/field-schemas/client`

取得當前租戶的 Client 欄位配置。

#### Request

```http
GET /api/v1/ui/field-schemas/client
Authorization: Bearer <token>
```

#### Response 200 OK

```json
{
  "entity_type": "client",
  "tenant_id": "org_123",
  "sections": [
    {
      "title": "基本資料",
      "description": "客戶的基本個人資訊",
      "fields": [
        {
          "key": "name",
          "label": "姓名",
          "type": "text",
          "required": true,
          "placeholder": "請輸入姓名"
        },
        {
          "key": "email",
          "label": "Email",
          "type": "email",
          "required": false,
          "placeholder": "example@email.com"
        },
        {
          "key": "phone",
          "label": "聯絡電話",
          "type": "phone",
          "required": false
        },
        {
          "key": "birth_date",
          "label": "出生日期",
          "type": "date",
          "required": false
        }
      ]
    },
    {
      "title": "背景資訊",
      "fields": [
        {
          "key": "occupation",
          "label": "職業",
          "type": "text",
          "required": false
        },
        {
          "key": "education",
          "label": "教育程度",
          "type": "single_select",
          "required": false,
          "options": ["國小", "國中", "高中職", "大學", "碩士", "博士"]
        },
        {
          "key": "notes",
          "label": "備註",
          "type": "textarea",
          "required": false,
          "help_text": "其他需要記錄的資訊"
        }
      ]
    }
  ],
  "version": "1.0.0",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

#### 欄位類型說明

| type | 說明 | 前端呈現 |
|------|------|---------|
| `text` | 單行文字 | `<input type="text">` |
| `textarea` | 多行文字 | `<textarea>` |
| `email` | Email | `<input type="email">` |
| `phone` | 電話 | `<input type="tel">` |
| `date` | 日期 | `<input type="date">` |
| `single_select` | 單選下拉 | `<select>` |

---

### 3. 取得 Case 欄位配置

**GET** `/api/v1/ui/field-schemas/case`

取得當前租戶的 Case 欄位配置。

#### Request

```http
GET /api/v1/ui/field-schemas/case
Authorization: Bearer <token>
```

#### Response 200 OK

```json
{
  "entity_type": "case",
  "tenant_id": "org_123",
  "sections": [
    {
      "title": "個案基本資訊",
      "fields": [
        {
          "key": "status",
          "label": "個案狀態",
          "type": "single_select",
          "required": true,
          "options": ["0", "1", "2"],
          "default_value": "0",
          "help_text": "0=未進行(NOT_STARTED), 1=進行中(IN_PROGRESS), 2=已完成(COMPLETED)"
        },
        {
          "key": "summary",
          "label": "個案摘要",
          "type": "textarea",
          "required": false,
          "placeholder": "簡述個案情況"
        }
      ]
    },
    {
      "title": "諮商內容",
      "fields": [
        {
          "key": "problem_description",
          "label": "問題描述",
          "type": "textarea",
          "required": false
        },
        {
          "key": "goals",
          "label": "諮商目標",
          "type": "textarea",
          "required": false
        }
      ]
    }
  ],
  "version": "1.0.0"
}
```

---

## 👥 客戶管理 API (Client)

### 1. 列出客戶

**GET** `/api/v1/clients`

列出當前租戶的所有客戶（支援分頁）。

#### Request

```http
GET /api/v1/clients?skip=0&limit=20
Authorization: Bearer <token>
```

#### Query Parameters

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| `skip` | integer | ❌ | 0 | 跳過筆數 |
| `limit` | integer | ❌ | 100 | 每頁筆數（最大 1000） |

#### Response 200 OK

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "code": "C0001",
      "name": "王小明",
      "email": "wang@example.com",
      "phone": "0912345678",
      "birth_date": "1990-01-15",
      "occupation": "工程師",
      "education": "大學",
      "notes": "初次諮詢",
      "tenant_id": "org_123",
      "counselor_id": "counselor-uuid",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 20
}
```

---

### 2. 建立客戶

**POST** `/api/v1/clients`

建立新客戶。

#### Request

```http
POST /api/v1/clients
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "王小明",
  "email": "wang@example.com",
  "phone": "0912345678",
  "birth_date": "1990-01-15",
  "occupation": "工程師",
  "education": "大學",
  "notes": "初次諮詢"
}
```

#### Request Body

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `name` | string | ✅ | 客戶姓名 |
| `code` | string | ❌ | 客戶編號（不填則自動生成 C0001, C0002...） |
| `email` | string | ❌ | Email |
| `phone` | string | ❌ | 聯絡電話 |
| `birth_date` | string | ❌ | 出生日期（YYYY-MM-DD） |
| `occupation` | string | ❌ | 職業 |
| `education` | string | ❌ | 教育程度 |
| `notes` | string | ❌ | 備註 |

**注意**：
- ✅ `code` 不填時，系統自動生成（C0001, C0002...）
- ✅ `tenant_id` 和 `counselor_id` 自動從 JWT 提取

#### Response 201 Created

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "code": "C0001",
  "name": "王小明",
  "email": "wang@example.com",
  "phone": "0912345678",
  "tenant_id": "org_123",
  "counselor_id": "counselor-uuid",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

#### Error 400 Bad Request

```json
{
  "detail": "Client code 'C0001' already exists"
}
```

---

### 3. 查看客戶

**GET** `/api/v1/clients/{id}`

取得單一客戶詳細資訊。

#### Request

```http
GET /api/v1/clients/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

#### Response 200 OK

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "code": "C0001",
  "name": "王小明",
  "email": "wang@example.com",
  "phone": "0912345678",
  "birth_date": "1990-01-15",
  "occupation": "工程師",
  "education": "大學",
  "notes": "初次諮詢",
  "tenant_id": "org_123",
  "counselor_id": "counselor-uuid",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

#### Error 404 Not Found

```json
{
  "detail": "Client 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

### 4. 更新客戶

**PATCH** `/api/v1/clients/{id}`

更新客戶資訊（部分更新）。

#### Request

```http
PATCH /api/v1/clients/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
Content-Type: application/json

{
  "phone": "0987654321",
  "notes": "已完成第三次諮詢"
}
```

#### Request Body

所有欄位均為選填，只更新提供的欄位。

#### Response 200 OK

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "code": "C0001",
  "name": "王小明",
  "phone": "0987654321",
  "notes": "已完成第三次諮詢",
  "updated_at": "2025-01-16T15:30:00Z"
}
```

---

### 5. 刪除客戶

**DELETE** `/api/v1/clients/{id}`

刪除客戶。

#### Request

```http
DELETE /api/v1/clients/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

#### Response 204 No Content

無內容返回。

#### Error 404 Not Found

```json
{
  "detail": "Client 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

## 📋 個案管理 API (Case)

### 1. 列出個案

**GET** `/api/v1/cases`

列出當前租戶的所有個案（支援分頁和過濾）。

#### Request

```http
GET /api/v1/cases?client_id=550e8400-e29b-41d4-a716-446655440000&skip=0&limit=20
Authorization: Bearer <token>
```

#### Query Parameters

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| `client_id` | UUID | ❌ | - | 過濾指定客戶的個案 |
| `skip` | integer | ❌ | 0 | 跳過筆數 |
| `limit` | integer | ❌ | 100 | 每頁筆數（最大 1000） |

#### Response 200 OK

```json
{
  "items": [
    {
      "id": "case-uuid-1",
      "case_number": "CASE0001",
      "client_id": "550e8400-e29b-41d4-a716-446655440000",
      "counselor_id": "counselor-uuid",
      "tenant_id": "org_123",
      "status": "active",
      "summary": "職涯轉換焦慮",
      "goals": "協助個案釐清職涯方向",
      "problem_description": "個案面臨職涯轉換，感到焦慮不安",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 20
}
```

---

### 2. 建立個案

**POST** `/api/v1/cases`

為客戶建立新個案。

#### Request

```http
POST /api/v1/cases
Authorization: Bearer <token>
Content-Type: application/json

{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "summary": "職涯轉換焦慮",
  "goals": "協助個案釐清職涯方向",
  "problem_description": "個案面臨職涯轉換，感到焦慮不安"
}
```

#### Request Body

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `client_id` | UUID | ✅ | 客戶 ID |
| `case_number` | string | ❌ | 個案編號（不填則自動生成 CASE0001, CASE0002...） |
| `status` | integer | ❌ | 個案狀態（0=未進行, 1=進行中, 2=已完成，預設 0） |
| `summary` | string | ❌ | 個案摘要 |
| `goals` | string | ❌ | 諮商目標 |
| `problem_description` | string | ❌ | 問題描述 |

**注意**：
- ✅ `case_number` 不填時，系統自動生成（CASE0001, CASE0002...）
- ✅ `tenant_id` 和 `counselor_id` 自動從 JWT 提取
- ✅ 系統會驗證 `client_id` 是否存在且屬於同一租戶

#### Response 201 Created

```json
{
  "id": "case-uuid-1",
  "case_number": "CASE0001",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "counselor_id": "counselor-uuid",
  "tenant_id": "org_123",
  "status": "active",
  "summary": "職涯轉換焦慮",
  "goals": "協助個案釐清職涯方向",
  "problem_description": "個案面臨職涯轉換，感到焦慮不安",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

#### Error 400 Bad Request

```json
{
  "detail": "Case number 'CASE0001' already exists"
}
```

#### Error 404 Not Found

```json
{
  "detail": "Client 550e8400-e29b-41d4-a716-446655440000 not found or doesn't belong to this tenant"
}
```

---

### 3. 查看個案

**GET** `/api/v1/cases/{id}`

取得單一個案詳細資訊。

#### Request

```http
GET /api/v1/cases/case-uuid-1
Authorization: Bearer <token>
```

#### Response 200 OK

```json
{
  "id": "case-uuid-1",
  "case_number": "CASE0001",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "counselor_id": "counselor-uuid",
  "tenant_id": "org_123",
  "status": "active",
  "summary": "職涯轉換焦慮",
  "goals": "協助個案釐清職涯方向",
  "problem_description": "個案面臨職涯轉換，感到焦慮不安",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

---

### 4. 更新個案

**PATCH** `/api/v1/cases/{id}`

更新個案資訊（部分更新）。

#### Request

```http
PATCH /api/v1/cases/case-uuid-1
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "closed",
  "summary": "個案已完成諮商，成功轉換職涯"
}
```

#### Request Body

所有欄位均為選填，只更新提供的欄位。

#### Response 200 OK

```json
{
  "id": "case-uuid-1",
  "case_number": "CASE0001",
  "status": "closed",
  "summary": "個案已完成諮商，成功轉換職涯",
  "updated_at": "2025-02-15T18:00:00Z"
}
```

---

### 5. 刪除個案

**DELETE** `/api/v1/cases/{id}`

刪除個案。

#### Request

```http
DELETE /api/v1/cases/case-uuid-1
Authorization: Bearer <token>
```

#### Response 204 No Content

無內容返回。

---

## 🔄 完整使用流程

### 流程 1: 新增客戶並建立個案

```
1. 登入取得 JWT Token
   ↓
2. GET /api/v1/ui/field-schemas/client-case
   一次取得 Client + Case 欄位配置（推薦）
   ↓
3. POST /api/v1/clients
   建立客戶（系統自動生成 code: C0001）
   ↓
4. POST /api/v1/cases
   為客戶建立個案（系統自動生成 case_number: CASE0001）
```

**舊方式（分別調用）:**
```
2a. GET /api/v1/ui/field-schemas/client
    取得客戶欄位配置
    ↓
2b. GET /api/v1/ui/field-schemas/case
    取得個案欄位配置
```

### 流程 2: 查詢客戶及其所有個案

```
1. GET /api/v1/clients
   列出所有客戶
   ↓
2. GET /api/v1/clients/{client_id}
   查看特定客戶
   ↓
3. GET /api/v1/cases?client_id={client_id}
   查詢該客戶的所有個案
```

### 流程 3: 更新個案狀態

```
1. GET /api/v1/cases/{case_id}
   查看個案當前狀態
   ↓
2. PATCH /api/v1/cases/{case_id}
   更新個案狀態（例如從 active 改為 closed）
```

---

## 📊 多租戶隔離示意圖

```
租戶 A (org_123)
├── Client C0001 (王小明)
│   ├── Case CASE0001 (職涯焦慮)
│   └── Case CASE0002 (工作壓力)
├── Client C0002 (李小華)
│   └── Case CASE0003 (人際關係)
└── Field Schema (自訂欄位)

租戶 B (org_456)
├── Client C0001 (張三)  ← 與租戶 A 的 C0001 完全隔離
│   └── Case CASE0001 (學業困擾)
└── Field Schema (不同的自訂欄位)
```

---

## ❓ 常見問題

### Q1: 如何自訂欄位？

**A**: 目前欄位配置由後端管理員設定。未來版本將提供前端自訂介面。

### Q2: Client Code 和 Case Number 的命名規則？

**A**:
- Client Code: `C0001`, `C0002`, `C0003`...（4位數字，不足補0）
- Case Number: `CASE0001`, `CASE0002`...（4位數字，不足補0）
- 租戶之間的編號互不影響

### Q3: 刪除客戶時，其個案會被刪除嗎？

**A**: 目前不會自動刪除。建議先手動處理個案後再刪除客戶。

### Q4: 可以跨租戶查詢資料嗎？

**A**: 不行。系統嚴格按 `tenant_id` 隔離，確保資料安全。

---

## 🐛 錯誤碼說明

| HTTP 狀態碼 | 錯誤情境 | 解決方法 |
|------------|---------|---------|
| 400 Bad Request | Code/Case Number 重複 | 使用不同的編號或不填讓系統自動生成 |
| 401 Unauthorized | JWT Token 無效或過期 | 重新登入取得新 Token |
| 404 Not Found | 資源不存在或不屬於當前租戶 | 確認 ID 正確且有權限存取 |
| 500 Internal Server Error | 伺服器錯誤 | 聯繫技術支援 |

---

## 🔍 測試工具

- **Swagger UI**: `http://localhost:8000/docs`
- **Console**: `http://localhost:8000/console` （內建測試介面）

---

**文件版本**: v1.0.0
**最後更新**: 2025-01-16
**維護團隊**: Career Counseling Platform Team
