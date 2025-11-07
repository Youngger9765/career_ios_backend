# iOS App API 完整指南

**Base URL:** `http://localhost:8080` (開發環境)

**認證方式:** Bearer Token (JWT)

---

## 📋 目錄

1. [認證 APIs](#認證-apis) (1-3)
2. [個案管理 APIs](#個案管理-apis) (4-9)
3. [會談記錄管理 APIs](#會談記錄管理-apis) (10-17)
4. [諮商師反思 APIs](#諮商師反思-apis) (18-19)
5. [報告 APIs](#報告-apis) (20-24)
6. [完整使用流程](#完整使用流程)
7. [錯誤處理](#錯誤處理)

## API 列表

### 👤 認證 APIs
1. POST /api/auth/login - 登入
2. GET /api/auth/me - 取得諮商師資訊
3. PATCH /api/auth/me - 更新諮商師資訊

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

### 🧠 諮商師反思 APIs ⭐️ NEW
15. GET /api/v1/sessions/{id}/reflection - 取得反思內容
16. PUT /api/v1/sessions/{id}/reflection - 更新反思內容

### 📄 報告 APIs
17. POST /api/v1/reports/generate - 生成報告 (從已儲存的會談記錄生成，需提供 session_id)
18. GET /api/v1/reports - 列出報告
19. GET /api/v1/reports/{id} - 取得單一報告
20. PATCH /api/v1/reports/{id} - 更新報告 (編輯)
21. GET /api/v1/reports/{id}/formatted - 取得格式化報告 (Markdown/HTML)

---

## 🔐 認證 APIs

### 1. 登入

**Endpoint:** `POST /api/auth/login`

**Request:**
```json
{
  "email": "test@career.com",
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
    let email: String
    let password: String
}

struct LoginResponse: Codable {
    let access_token: String
    let token_type: String
    let expires_in: Int
}

func login(email: String, password: String) async throws -> String {
    let url = URL(string: "\(baseURL)/api/auth/login")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = LoginRequest(email: email, password: password)
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

### 3. 更新諮商師資訊

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

**描述:** 取得個案的所有會談記錄時間線，包含會談次數、日期、時間範圍、摘要、是否有報告等資訊。適合在個案詳情頁面顯示完整的諮商歷程。

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

**描述:** 儲存會談逐字稿（不立即生成報告）。諮商師可以先儲存逐字稿，稍後再決定是否生成報告。

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
  "start_time": "2024-01-15 14:00",        // optional，會談開始時間
  "end_time": "2024-01-15 15:00",          // optional，會談結束時間
  "transcript": "逐字稿內容...",             // 必填
  "duration_minutes": 50,                  // optional (保留向下兼容)
  "notes": "備註說明",                       // optional，諮商師人工撰寫的備註
  "reflection": {                          // ⭐️ NEW optional，諮商師反思（人類撰寫）
    "working_with_client": "整體過程流暢輕鬆，逐漸贏得信任...",
    "feeling_source": "個案從緊張到逐步放鬆...",
    "current_challenges": "當肯定個案時，仍會有自我懷疑反應...",
    "supervision_topics": "如何在支持與挑戰間拿捏節奏..."
  }
}
```

**📝 欄位說明:**
- `notes`: 諮商師對本次會談的簡短備註
- `reflection`: ⭐️ 諮商師對本次會談的深度反思，包含 4 個反思問題（選填）
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
  "session_date": "2024-01-15T00:00:00Z",
  "start_time": "2024-01-15T14:00:00Z",   // 會談開始時間
  "end_time": "2024-01-15T15:00:00Z",     // 會談結束時間
  "transcript_text": "逐字稿內容...",
  "duration_minutes": 50,
  "notes": "備註說明",
  "has_report": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

**Swift Example:**
```swift
struct SessionCreateRequest: Codable {
    let client_id: UUID
    let session_date: String      // "YYYY-MM-DD"
    let start_time: String?       // "YYYY-MM-DD HH:MM"
    let end_time: String?         // "YYYY-MM-DD HH:MM"
    let transcript: String
    let duration_minutes: Int?    // 保留向下兼容
    let notes: String?
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

## 🧠 諮商師反思 APIs

### 15. 取得反思內容 ⭐️ NEW

**Endpoint:** `GET /api/v1/sessions/{session_id}/reflection`

**描述:** 取得諮商師對特定會談的反思內容。反思是諮商師人工撰寫的內容，用於深度自我覺察和督導討論。

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

**描述:** 更新或新增諮商師對特定會談的反思。可以只填寫部分問題，未填寫的問題不會被儲存。

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
1. **撰寫反思**: 會談後諮商師填寫反思問題
2. **補充反思**: 稍後回顧時補充遺漏的問題
3. **督導前整理**: 督導前重新整理反思內容
4. **生成報告時**: 反思內容會被包含在報告的「四、個人化分析」章節

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
- `edited_content_markdown`: 諮商師編輯後的 Markdown 格式 (編輯後才會有值)
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

### 20. 更新報告 (諮商師編輯)

**Endpoint:** `PATCH /api/v1/reports/{report_id}`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

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

**Response (200):**
```json
{
  "id": "uuid",
  "edited_content_json": {...},
  "edited_content_markdown": "# 個案報告\n\n## 案主基本資料\n...",  // ⭐️ UPDATED: 儲存的 Markdown (不再是動態生成)
  "edited_at": "2025-10-29T10:30:00Z",
  "edit_count": 1
}
```

**Swift 範例:**
```swift
struct UpdateReportRequest: Codable {
    let edited_content_json: [String: Any]
}

struct UpdateReportResponse: Codable {
    let id: UUID
    let edited_content_json: [String: Any]
    let edited_content_markdown: String  // ⭐️ UPDATED: 儲存的 Markdown
    let edited_at: String
    let edit_count: Int
}

func updateReport(token: String, reportId: UUID, editedContent: [String: Any]) async throws -> UpdateReportResponse {
    let url = URL(string: "\(baseURL)/api/v1/reports/\(reportId)")!
    var request = URLRequest(url: url)
    request.httpMethod = "PATCH"
    request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = ["edited_content_json": editedContent]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(UpdateReportResponse.self, from: data)
}
```

**重要說明:**
- AI 原始生成的報告保存在 `content_json` 和 `content_markdown` (不可變)
- 諮商師編輯的版本保存在 `edited_content_json` 和 `edited_content_markdown`
- **推薦使用 Markdown 欄位直接渲染**，無需解析 JSON
- 可用於實現報告編輯器功能

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
let token = try await login(email: "test@career.com", password: "password123")

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

**Email:** `test@career.com`
**Password:** `password123`
**Role:** `counselor`
**Tenant:** `career`

---

## 🔗 相關連結

- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc
- **Debug Console:** http://localhost:8080/console

---

**最後更新:** 2025-10-29
