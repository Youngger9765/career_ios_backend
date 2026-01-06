# Island Parents iOS App 開發指南

> **版本**: v1.4
> **適用對象**: iOS 開發者
> **後端版本**: career_ios_backend

---

## 1. 系統概述

### 1.1 產品定位
Island Parents 是一款 **AI 親子教養助手**，幫助家長在與孩子互動時獲得即時指導。

### 1.2 核心功能
| 功能 | 說明 | API |
|------|------|-----|
| 即時轉錄 | 語音轉文字 (Scribe v2) | ElevenLabs SDK |
| 快速回饋 | 15 秒一次的鼓勵訊息 | `POST /sessions/{id}/quick-feedback` |
| 深度分析 | 紅黃綠燈安全評估 | `POST /sessions/{id}/deep-analyze` |
| 諮詢報告 | 完整對話分析報告 | `POST /sessions/{id}/report` |

### 1.3 技術架構
```
┌─────────────────────────────────────────────┐
│                   iOS App                    │
├─────────────────────────────────────────────┤
│ ElevenLabs SDK        │ Backend API Client  │
│ (Scribe v2 Realtime)  │ (REST + JSON)       │
└──────────┬────────────┴──────────┬──────────┘
           │                       │
           ▼                       ▼
┌──────────────────┐    ┌─────────────────────┐
│ ElevenLabs Cloud │    │ career_ios_backend  │
│ STT: 150ms 延遲  │    │ FastAPI + Gemini    │
└──────────────────┘    └─────────────────────┘
```

---

## 2. 認證系統

### 2.1 登入
```
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "tenant_id": "island_parents"
}
```

**⚠️ 注意**：
- 使用 `email` 而非 `username`
- 必須傳入 `tenant_id: "island_parents"`

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "user123",
    "full_name": "Test User",
    "role": "counselor",
    "tenant_id": "island_parents",
    "is_active": true,
    "available_credits": 100.0,
    "last_login": "2025-01-05T10:00:00Z",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-05T10:00:00Z"
  }
}
```

### 2.2 Token 使用
所有需認證的 API 都需要在 Header 加上：
```
Authorization: Bearer <access_token>
```

### 2.3 Token 有效期
- **有效期**: 24 小時
- **建議**: 儲存於 Keychain，到期前自動更新

---

## 3. Session Workflow

### 3.1 完整流程
```
1. 選擇情境 (scenario)
   ↓
2. 建立 Session (POST /api/v1/sessions)
   ↓
3. 取得會談 (GET /api/v1/sessions/{id}) ← 確認 Session 資料
   ↓
4. 開始錄音 (ElevenLabs Scribe v2)
   ↓
5. 即時上傳逐字稿 (append)
   ↓
6. 觸發分析 (Quick / Deep)
   ↓
7. 結束錄音
   ↓
8. 生成報告 (Report)
```

### 3.2 建立 Session
```
POST /api/v1/sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "client_id": "uuid-of-client",
  "case_id": "uuid-of-case",
  "session_mode": "practice",
  "scenario": "homework",
  "scenario_description": "孩子回家後不願意寫功課，一直玩手機"
}
```

**session_mode 選項:**
| session_mode | 說明 | 適用場景 |
|--------------|------|----------|
| `practice` | 練習模式 | 家長獨自練習，沒有孩子在場 |
| `emergency` | 對談模式 | 真實親子互動現場 |

**Response (201):**
```json
{
  "id": "session-uuid",
  "client_id": "client-uuid",
  "case_id": "case-uuid",
  "session_mode": "practice",
  "scenario": "homework",
  "scenario_description": "孩子回家後不願意寫功課，一直玩手機",
  "status": "active",
  "created_at": "2025-01-05T10:00:00Z"
}
```

### 3.3 取得會談 (Get Session)
建立 Session 後，可透過此 API 取得完整 Session 資料。

```
GET /api/v1/sessions/{session_id}
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": "session-uuid",
  "client_id": "client-uuid",
  "client_name": "小明",
  "client_code": "CHILD001",
  "case_id": "case-uuid",
  "session_number": 5,
  "session_date": "2025-01-05T10:00:00Z",
  "name": "諮詢 - 2025-01-05 10:00",
  "start_time": "2025-01-05T10:00:00Z",
  "end_time": null,
  "transcript_text": "",
  "summary": null,
  "duration_minutes": null,
  "notes": null,
  "reflection": {},
  "recordings": [],
  "session_mode": "practice",
  "scenario": "homework",
  "scenario_description": "孩子回家後不願意寫功課，一直玩手機",
  "has_report": false,
  "created_at": "2025-01-05T10:00:00Z",
  "updated_at": "2025-01-05T10:00:00Z"
}
```

**用途:**
- 錄音頁面載入時確認 Session 狀態
- 確認 scenario 設定是否正確
- 查看累積的 transcript_text

### 3.4 上傳逐字稿片段
```
POST /api/v1/sessions/{session_id}/recordings/append
Authorization: Bearer <token>
Content-Type: application/json

{
  "transcript_segment": "媽媽：寶貝，功課寫完了嗎？\n孩子：還沒，我想先玩一下。",
  "start_time": "2025-01-05T10:00:00.000Z",
  "end_time": "2025-01-05T10:00:15.000Z"
}
```

**注意**: `start_time` 和 `end_time` 必須是 **ISO 8601 格式的字串**（非數字），例如 `new Date().toISOString()`。

**Response (200):**
```json
{
  "success": true,
  "session_id": "session-uuid",
  "total_duration_seconds": 15.0,
  "transcript_length": 45
}
```

**上傳頻率建議:**
- 每 **10-15 秒** 上傳一次
- 配合 ElevenLabs Scribe v2 的 chunk 輸出

---

## 4. AI 分析 APIs

### 4.1 Quick Feedback (快速回饋)
**用途**: 每 15 秒提供即時鼓勵訊息

```
POST /api/v1/sessions/{session_id}/quick-feedback?session_mode=practice
Authorization: Bearer <token>
```

**注意**: 此 API 不需要 request body，會自動從 session 讀取最近 15 秒的逐字稿。

**Query Parameters:**
- `session_mode`: `practice` (練習模式，預設) 或 `emergency` (對談模式)

**Response (200):**
```json
{
  "message": "很好！用「寶貝」開頭是溫和的開場方式",
  "type": "ai_generated",
  "timestamp": "2025-01-05T10:00:15Z",
  "latency_ms": 850
}
```

**觸發時機:**
- 每 15 秒自動觸發
- Buffer 有新內容時才觸發
- 避免重複分析相同內容

### 4.2 Deep Analyze (深度分析)
**用途**: 紅黃綠燈評估 + 專家建議

```
POST /api/v1/sessions/{session_id}/deep-analyze
Authorization: Bearer <token>
Content-Type: application/json
```

**注意**: 此 API 不需要 request body，會自動使用 session 中累積的逐字稿。

**Response (200):**
```json
{
  "safety_level": "yellow",
  "summary": "家長嘗試與孩子溝通功課問題，但孩子有些抗拒",
  "alerts": [
    "⚠️ 孩子顯示抗拒情緒",
    "⚠️ 注意溝通方式是否給孩子壓力"
  ],
  "suggestions": [
    "可以先問「今天在學校有什麼好玩的事嗎？」",
    "建立連結後再談功課"
  ],
  "time_range": "0:00-2:00",
  "timestamp": "2026-01-07T10:00:00+00:00",
  "rag_sources": [
    {
      "title": "正向教養：同理心優先",
      "content": "先同理孩子的感受，再引導行為...",
      "score": 0.85,
      "theory": "正向教養"
    }
  ],
  "cache_metadata": null,
  "provider_metadata": {
    "provider": "gemini",
    "latency_ms": 1200,
    "model": "gemini-3-flash-preview"
  }
}
```

**⚠️ 重要：`suggestions` 和 `alerts` 都是字串陣列 `List[str]`，不是物件陣列！**

**safety_level 說明:**
| Level | 顏色 | 說明 | UI 顯示 |
|-------|------|------|---------|
| `green` | 綠燈 | 安全：平和、正向互動 | 綠色指示燈 |
| `yellow` | 黃燈 | 注意：衝突升級、挫折感 | 黃色指示燈 |
| `red` | 紅燈 | 警示：暴力語言、極端情緒 | 紅色指示燈 + 震動 |

**動態呼叫間隔:**
| Safety Level | 下次分析間隔 |
|--------------|-------------|
| `green` | 60 秒 |
| `yellow` | 45 秒 |
| `red` | 30 秒 |

### 4.3 Report (諮詢報告)
**用途**: 對話結束後生成完整分析報告

```
POST /api/v1/sessions/{session_id}/report
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "session_id": "session-uuid",
  "report": {
    "encouragement": "今天的對話中，您展現了對孩子的關心和耐心...",
    "issue": "在討論功課時，孩子出現了抗拒反應...",
    "analyze": "從正向教養的角度來看，孩子的抗拒可能源於...\n\n根據情緒教養理論，當孩子感受到壓力時...",
    "suggestion": "下次遇到類似情況，您可以試試：\n1. 「我看到你想玩手機，是不是今天在學校很累？」\n2. 「我們一起想想，怎麼安排時間讓你可以玩也可以寫功課？」"
  },
  "rag_sources": [...],
  "generated_at": "2025-01-05T11:00:00Z"
}
```

**內容長度:**
- 動態調整：根據對話長度自動調整報告深度
- 短對話 (<500字): 簡潔報告
- 中對話 (500-2000字): 標準報告
- 長對話 (>2000字): 詳細報告

---

## 5. ElevenLabs Scribe v2 整合

### 5.1 SDK 設定
```swift
import ElevenLabsSDK

let scribe = ElevenLabsScribe(
    apiKey: "YOUR_API_KEY",
    model: .scribeV2Realtime,
    language: "zh-TW"
)
```

### 5.2 即時轉錄
```swift
scribe.startTranscription { result in
    switch result {
    case .success(let transcript):
        // 累積逐字稿
        self.transcriptBuffer.append(transcript.text)

        // 每 10 秒上傳到後端
        if shouldUpload() {
            await sessionAPI.appendRecording(
                sessionId: currentSessionId,
                transcript: self.transcriptBuffer
            )
        }

    case .failure(let error):
        print("Transcription error: \(error)")
    }
}
```

### 5.3 效能指標
| 指標 | 數值 |
|------|------|
| 延遲 | 150ms |
| 準確率 | 96.7% (英文) / 95%+ (中文) |
| 支援語言 | 90+ |
| 成本 | $0.40/小時 |

---

## 6. 情境 (Scenario) 系統

### 6.1 預設情境
```swift
enum ParentingScenario: String {
    case homework = "homework"       // 功課問題
    case sibling = "sibling"         // 手足衝突
    case screen = "screen"           // 3C 使用
    case bedtime = "bedtime"         // 就寢時間
    case meal = "meal"               // 用餐問題
    case emotion = "emotion"         // 情緒管理
    case school = "school"           // 學校問題
    case other = "other"             // 其他
}
```

### 6.2 情境 UI
建議提供情境選擇 UI：
1. 預設情境列表 (上述 8 種)
2. 「其他」選項讓家長自行描述
3. 情境描述文字框 (`scenario_description`)

### 6.3 情境的重要性
- **Quick Feedback**: 根據情境提供更針對性的鼓勵
- **Deep Analyze**: 圍繞情境分析問題根源
- **Report**: 聚焦情境提供具體建議

---

## 7. 錯誤處理

### 7.1 HTTP 狀態碼
| 狀態碼 | 說明 | 處理建議 |
|--------|------|----------|
| 200 | 成功 | 正常處理 |
| 201 | 建立成功 | Session 建立成功 |
| 400 | 請求錯誤 | 檢查參數格式 |
| 401 | 未授權 | Token 過期，重新登入 |
| 403 | 禁止存取 | 無權限存取此資源 |
| 404 | 找不到 | Session/Client 不存在 |
| 422 | 驗證失敗 | 請求內容不符合規範 |
| 500 | 伺服器錯誤 | 顯示錯誤訊息，建議重試 |

### 7.2 錯誤回應格式
```json
{
  "detail": "Session not found",
  "error_code": "SESSION_NOT_FOUND"
}
```

### 7.3 重試策略
```swift
// 指數退避重試
func retry<T>(
    maxAttempts: Int = 3,
    initialDelay: TimeInterval = 1.0,
    operation: () async throws -> T
) async throws -> T {
    var delay = initialDelay
    for attempt in 1...maxAttempts {
        do {
            return try await operation()
        } catch {
            if attempt == maxAttempts { throw error }
            try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            delay *= 2
        }
    }
    throw APIError.maxRetriesExceeded
}
```

---

## 8. UI/UX 建議

### 8.1 即時回饋顯示
```
┌─────────────────────────────────┐
│ 🟢 安全          [暫停] [結束]  │
├─────────────────────────────────┤
│                                 │
│  💬 "很好！用「寶貝」開頭      │
│      是溫和的開場方式"          │
│                                 │
│  ⏱️ 已錄音 2:35                │
│                                 │
└─────────────────────────────────┘
```

### 8.2 安全燈號
| 燈號 | 顏色 | 動作 |
|------|------|------|
| 🟢 | 綠色 | 無 |
| 🟡 | 黃色 | 輕微震動 |
| 🔴 | 紅色 | 強烈震動 + 聲音 |

### 8.3 報告呈現
建議採用卡片式設計：
1. **鼓勵卡片** (綠色) - encouragement
2. **問題卡片** (黃色) - issue
3. **分析卡片** (藍色) - analyze
4. **建議卡片** (紫色) - suggestion

---

## 9. 最佳實踐

### 9.1 網路處理
- [ ] 離線時緩存逐字稿，恢復後上傳
- [ ] 弱網環境顯示提示
- [ ] 後台模式繼續錄音

### 9.2 電池優化
- [ ] 螢幕關閉時降低 UI 更新頻率
- [ ] 批次上傳減少網路請求
- [ ] 避免過度震動

### 9.3 隱私安全
- [ ] 不在本地儲存完整逐字稿
- [ ] Token 儲存於 Keychain
- [ ] 傳輸使用 HTTPS
- [ ] 敏感操作需要生物辨識

### 9.4 測試建議
- [ ] 模擬 15 分鐘以上對話
- [ ] 測試紅黃綠燈轉換
- [ ] 測試網路中斷恢復
- [ ] 測試後台錄音

---

## 10. 對話歷史 (History Page)

### 10.1 功能概述
家長可以在首頁查看孩子的所有對話歷史，並依照模式分類篩選。

### 10.2 頁面流程
```
首頁 (選擇孩子)
    ↓ 點擊「查看對話歷史」
對話歷史頁面
    ├── 顯示該孩子所有 Sessions
    ├── 可切換孩子 (Modal)
    └── 可篩選模式 (全部/練習/對談)
    ↓ 點擊某個 Session
報告詳情頁面
    └── 底部有「返回對話歷史」按鈕
```

### 10.3 列出 Sessions API
```
GET /api/v1/sessions?client_id=<client_uuid>
Authorization: Bearer <token>
```

**Query 參數:**
| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `client_id` | UUID | 否 | 依孩子篩選 |
| `case_id` | UUID | 否 | 依案例篩選 |
| `session_mode` | string | 否 | 依模式篩選: `practice` / `emergency` |
| `search` | string | 否 | 搜尋孩子名稱或代碼 |
| `skip` | int | 否 | 分頁偏移 (default: 0) |
| `limit` | int | 否 | 每頁筆數 (default: 20, max: 100) |

**範例請求:**
```bash
# 取得某個孩子的所有 Sessions
GET /api/v1/sessions?client_id=abc-123

# 只取得練習模式的 Sessions
GET /api/v1/sessions?client_id=abc-123&session_mode=practice

# 只取得對談模式的 Sessions
GET /api/v1/sessions?client_id=abc-123&session_mode=emergency

# 分頁取得
GET /api/v1/sessions?client_id=abc-123&skip=20&limit=20
```

**Response (200):**
```json
{
  "total": 15,
  "items": [
    {
      "id": "session-uuid-1",
      "client_id": "client-uuid",
      "client_name": "小明",
      "client_code": "CHILD001",
      "case_id": "case-uuid",
      "session_number": 5,
      "session_date": "2025-01-05T10:00:00Z",
      "name": "諮詢 - 2025-01-05 10:00",
      "session_mode": "practice",
      "scenario": "homework",
      "scenario_description": "孩子不願意寫功課",
      "has_report": true,
      "created_at": "2025-01-05T10:00:00Z",
      "updated_at": "2025-01-05T11:00:00Z"
    },
    {
      "id": "session-uuid-2",
      "client_id": "client-uuid",
      "client_name": "小明",
      "client_code": "CHILD001",
      "case_id": "case-uuid",
      "session_number": 4,
      "session_date": "2025-01-04T18:30:00Z",
      "name": "諮詢 - 2025-01-04 18:30",
      "session_mode": "emergency",
      "scenario": "emotion",
      "scenario_description": "孩子在學校被同學欺負",
      "has_report": true,
      "created_at": "2025-01-04T18:30:00Z",
      "updated_at": "2025-01-04T19:30:00Z"
    }
  ]
}
```

### 10.4 session_mode 篩選邏輯
| session_mode 值 | 說明 | UI 標籤建議 |
|-----------------|------|------------|
| `null` 或不傳 | 顯示全部 | 「全部」 |
| `practice` | 對話練習 | 「🎯 練習」 |
| `emergency` | 親子溝通 | 「🔴 對談」 |

**iOS 實作建議:**
```swift
enum SessionMode: String {
    case all = ""             // 不傳，顯示全部
    case practice = "practice" // 練習模式
    case emergency = "emergency" // 對談模式
}

// 切換篩選
func fetchSessions(clientId: UUID, sessionMode: SessionMode) async {
    var url = "/api/v1/sessions?client_id=\(clientId)"
    if !sessionMode.rawValue.isEmpty {
        url += "&session_mode=\(sessionMode.rawValue)"
    }
    // ... fetch
}
```

### 10.5 切換孩子 (Modal)
建議使用 Modal 讓家長快速切換不同孩子：

```swift
// 列出所有孩子
GET /api/v1/clients

// Response
{
  "items": [
    {"id": "uuid-1", "name": "小明", "code": "CHILD001"},
    {"id": "uuid-2", "name": "小華", "code": "CHILD002"}
  ]
}
```

**UI 建議:**
```
┌────────────────────────────┐
│  選擇孩子              [X] │
├────────────────────────────┤
│  ○ 小明 (CHILD001)         │
│  ● 小華 (CHILD002) ✓       │
│  ○ 小美 (CHILD003)         │
└────────────────────────────┘
```

### 10.6 取得會談報告 (NEW!)

用 session_id 取得報告內容，用於 History Page 點擊會談時顯示報告：

```
GET /api/v1/sessions/{session_id}/report
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": "report-uuid",
  "session_id": "session-uuid",
  "client_name": "小明",
  "session_number": 5,
  "status": "completed",
  "content_json": {
    "encouragement": "這次你已經做了一件重要的事：願意好好跟孩子談。",
    "issue": "對話陷入無效重複，缺乏雙向互動。",
    "analyze": "重複相同的指令容易讓孩子產生「聽而不聞」...",
    "suggestion": "「我知道你還想玩，要停下來很難。你是想...」"
  },
  "citations_json": [...]
}
```

**Error Response (404):**
- Session 不存在
- Session 沒有報告 (`has_report: false`)

**iOS History Page 流程:**
```swift
// 1. 列出會談
let sessions = await api.listSessions(clientId: selectedClient.id)

// 2. 點擊有報告的會談
if session.hasReport {
    // 3. 取得報告
    let report = await api.getSessionReport(sessionId: session.id)
    // 4. 顯示報告
    showReportDetail(report)
}
```

### 10.7 報告詳情返回
從報告詳情頁面返回對話歷史：

**UI 建議:**
```
┌────────────────────────────┐
│ < 返回對話歷史    報告詳情  │
├────────────────────────────┤
│                            │
│   [報告內容...]            │
│                            │
└────────────────────────────┘
```

---

## 11. API 端點總覽

### 11.1 認證
| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/api/auth/login` | 登入 (需要 email + tenant_id) |
| GET | `/api/auth/me` | 取得用戶資訊 |
| POST | `/api/v1/auth/password-reset/request` | 請求重設密碼 |
| POST | `/api/v1/auth/password-reset/confirm` | 確認重設密碼 |

### 11.2 Session
| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/api/v1/sessions` | 建立 Session |
| GET | `/api/v1/sessions` | 列出 Sessions (支援篩選) |
| GET | `/api/v1/sessions/{id}` | 取得 Session |
| GET | `/api/v1/sessions/{id}/report` | 取得報告 (by session_id) ⭐ NEW |
| POST | `/api/v1/sessions/{id}/recordings/append` | 上傳逐字稿 |
| POST | `/api/v1/sessions/{id}/quick-feedback` | 快速回饋 |
| POST | `/api/v1/sessions/{id}/deep-analyze` | 深度分析 |
| POST | `/api/v1/sessions/{id}/report` | 生成報告 |
| PUT | `/api/v1/sessions/{id}/complete` | 結束 Session |

### 11.3 Client & Case
| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/api/v1/clients` | 建立 Client |
| GET | `/api/v1/clients` | 列出 Clients |
| POST | `/api/v1/cases` | 建立 Case |
| GET | `/api/v1/clients/{id}/cases` | 列出 Client 的 Cases |

---

## 12. 成本估算

### 12.1 單次對話成本 (60 分鐘)
| 項目 | 成本 |
|------|------|
| ElevenLabs Scribe v2 | $0.40 |
| Quick Feedback (60次) | $0.06 |
| Deep Analyze (60次) | $0.18 |
| Report (1次) | $0.015 |
| 其他 (DB, GCP) | $0.06 |
| **總計** | **~$0.72** |

### 12.2 月成本估算
| 使用頻率 | 月成本 |
|----------|--------|
| 每週 1 次 (4次/月) | ~$2.88 |
| 每週 3 次 (12次/月) | ~$8.64 |
| 每天 1 次 (30次/月) | ~$21.60 |

---

## 13. 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.4 | 2026-01-05 | 修正: Deep Analyze 使用 `/deep-analyze` (非 analyze-partial)；錄音 append 的 start_time/end_time 為 ISO 8601 格式字串 |
| v1.3 | 2025-01-05 | 新增 GET /api/v1/sessions/{id}/report - 用 session_id 取得報告 (History Page) |
| v1.2 | 2025-01-05 | 重命名 mode 為 session_mode (避免 PostgreSQL 保留字衝突)；新增取得會談 API 文檔 |
| v1.1 | 2025-01-05 | 新增 History Page API (session_mode 篩選、client_id 篩選) |
| v1.0 | 2025-01-05 | 初版發布 |

---

## 14. 聯絡與支援

- **後端 Repo**: career_ios_backend
- **API 文檔**: `/docs` (Swagger UI)
- **問題回報**: GitHub Issues

---

**最後更新**: 2026-01-05
