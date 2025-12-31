# Web Session Workflow - JavaScript Module

## Overview

模組化 JavaScript 實現 Web 即時諮詢的 Session workflow，整合 iOS Session API 到 Web 前端。

## Architecture

```
┌─────────────────────────────────────────────────────┐
│             realtime_counseling.html               │
│  (Existing UI)                                      │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│         session-workflow.js                         │
│  - initializeSession()                              │
│  - performAnalysis()                                │
│  - transformToRealtimeFormat()                      │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│            api-client.js                            │
│  - createClientAndCase()                            │
│  - createSession()                                  │
│  - appendRecording()                                │
│  - analyzePartial()                                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              Backend APIs                           │
│  - /api/v1/ui/client-case      (POST)              │
│  - /api/v1/sessions            (POST)              │
│  - /api/v1/sessions/{id}/recordings/append (POST)  │
│  - /api/v1/sessions/{id}/analyze-partial (POST)   │
└─────────────────────────────────────────────────────┘
```

## Files

### Core Modules

1. **`api-client.js`** - API Client
   - 統一管理所有 API 調用
   - 處理認證（JWT token, tenant ID）
   - 錯誤處理

2. **`session-workflow.js`** - Session Workflow Manager
   - 管理 Session 生命週期
   - 執行完整的 workflow（client → case → session → append → analyze）
   - 轉換 Session API response 為 Realtime API format（向後兼容）

### Helper Files

3. **`integration-example.js`** - Integration Examples
   - 展示如何整合到 `realtime_counseling.html`
   - Feature flag 範例（向後兼容）

4. **`test-session-workflow.html`** - Test Page
   - 手動測試 workflow
   - UI 範例

## Usage

### Basic Usage

```javascript
import { SessionWorkflow } from '/static/js/session-workflow.js';

// 1. Initialize workflow
const workflow = new SessionWorkflow();

// 2. Create client + case + session
const sessionId = await workflow.initializeSession({
    name: "測試孩子",
    email: "test@example.com",
    gender: "不透露",
    birth_date: "2015-01-01",
    phone: "0900000000",
    identity_option: "其他",
    current_status: "進行中",
    case_summary: "測試會談",
    case_goals: "改善溝通"
});

// 3. Perform analysis
const analysis = await workflow.performAnalysis(
    "家長：你今天在學校怎麼樣？\n孩子：還好啦...",
    "practice"  // or "emergency"
);

// 4. Display result (Realtime API format)
console.log(analysis.safety_level);  // "green" | "yellow" | "red"
console.log(analysis.summary);       // Display text
console.log(analysis.alerts);        // Action suggestions

// 5. End session
workflow.endSession();
```

### Integration with realtime_counseling.html

請參考 `integration-example.js` 中的完整範例。

#### 核心步驟：

1. **Import module**:
   ```html
   <script type="module">
       import { SessionWorkflow } from '/static/js/session-workflow.js';
   </script>
   ```

2. **Initialize on client setup**:
   ```javascript
   await sessionWorkflow.initializeSession({ ... });
   ```

3. **Replace analysis call**:
   ```javascript
   // Old:
   // const analysis = await fetch('/api/v1/island-parents/realtime-analysis', ...)

   // New:
   const analysis = await sessionWorkflow.performAnalysis(transcript, mode);
   ```

4. **Use existing display function**:
   ```javascript
   displayAnalysisCard(analysis);  // Your existing function works!
   ```

## API Reference

### `APIClient`

#### Constructor
```javascript
new APIClient()
```
自動從 localStorage 讀取 `authToken` 和 `tenantId`。

#### Methods

##### `createClientAndCase(clientData)`
創建 client + case（原子操作）

**Parameters:**
- `clientData` (Object):
  - `name` (string): 孩子名稱
  - `email` (string): Email
  - `gender` (string): 性別
  - `birth_date` (string): 生日 (YYYY-MM-DD)
  - `phone` (string): 電話
  - `identity_option` (string): 身份選項
  - `current_status` (string): 當前狀態
  - `case_summary` (string, optional): 案例摘要
  - `case_goals` (string, optional): 案例目標

**Returns:** `Promise<{client_id: string, case_id: string}>`

##### `createSession(caseId, sessionName?)`
創建 Session

**Parameters:**
- `caseId` (string): Case UUID
- `sessionName` (string, optional): Session 名稱（自動生成）

**Returns:** `Promise<{id: string}>`

##### `appendRecording(sessionId, transcript, durationSeconds?)`
附加錄音到 Session

**Parameters:**
- `sessionId` (string): Session UUID
- `transcript` (string): 逐字稿
- `durationSeconds` (number, optional): 錄音長度（默認 60）

**Returns:** `Promise<Object>`

##### `analyzePartial(sessionId, segment, mode?)`
分析部分逐字稿

**Parameters:**
- `sessionId` (string): Session UUID
- `segment` (string): 要分析的片段
- `mode` (string, optional): 分析模式 ("practice" | "emergency")

**Returns:** `Promise<Object>` - Session API response

##### `refreshAuth()`
從 localStorage 重新讀取認證資訊（登入後調用）

##### `isAuthenticated()`
檢查是否已認證

**Returns:** `boolean`

---

### `SessionWorkflow`

#### Constructor
```javascript
new SessionWorkflow()
```

#### Methods

##### `initializeSession(clientData)`
初始化 Session（創建 client + case + session）

**Parameters:**
- `clientData` (Object): 同 `APIClient.createClientAndCase()`

**Returns:** `Promise<string>` - session_id

**Throws:** `Error` - 如果初始化失敗

##### `performAnalysis(transcript, mode?)`
執行分析（append + analyze）

**Parameters:**
- `transcript` (string): 逐字稿
- `mode` (string, optional): "practice" | "emergency"

**Returns:** `Promise<Object>` - Realtime API format response

**Throws:** `Error` - 如果 session 未初始化或分析失敗

##### `transformToRealtimeFormat(sessionResponse)`
轉換 Session API response 為 Realtime API format

**Parameters:**
- `sessionResponse` (Object): Session API response

**Returns:** `Object` - Realtime API format

**Format:**
```javascript
{
    // Realtime API fields
    safety_level: "green" | "yellow" | "red",
    summary: string,
    alerts: string[],
    suggestions: string[],
    time_range: string,
    timestamp: string,
    rag_sources: Object[],
    provider_metadata: {
        provider: "gemini",
        latency_ms: number,
        model: string
    },

    // Session metadata (advanced usage)
    _session_metadata: {
        session_id: string,
        case_id: string,
        client_id: string,
        severity: number,
        suggested_interval_seconds: number,
        keywords: string[],
        categories: string[]
    }
}
```

##### `endSession()`
結束 Session 並重置狀態

##### `getCurrentSessionId()`
**Returns:** `string | null`

##### `getCurrentCaseId()`
**Returns:** `string | null`

##### `getCurrentClientId()`
**Returns:** `string | null`

##### `isSessionActive()`
**Returns:** `boolean`

##### `getSessionMetadata()`
**Returns:** `Object` - Session metadata

## Testing

### Backend Integration Tests

```bash
# Run integration tests
poetry run pytest tests/integration/test_web_session_workflow.py -v

# Test specific workflow
poetry run pytest tests/integration/test_web_session_workflow.py::TestWebSessionWorkflow::test_complete_web_session_workflow -v
```

### Manual Testing

1. 啟動開發伺服器：
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

2. 訪問測試頁面：
   ```
   http://localhost:8000/static/test-session-workflow.html
   ```

3. 測試步驟：
   - 登入系統（確保 localStorage 有 `authToken` 和 `tenantId`）
   - 點擊「初始化 Session」
   - 輸入逐字稿，點擊「執行分析」
   - 查看分析結果
   - 點擊「結束 Session」

## Error Handling

### Common Errors

#### 1. "Session 未初始化"
**原因:** 未調用 `initializeSession()` 就執行 `performAnalysis()`
**解決:** 確保先初始化 Session

#### 2. "API Error (401)"
**原因:** 未登入或 token 過期
**解決:**
- 確認 localStorage 有 `authToken` 和 `tenantId`
- 登入後調用 `apiClient.refreshAuth()`

#### 3. "API Error (422): Validation failed"
**原因:** Email 格式不正確
**解決:** 使用有效的 email 格式（例如 `test@example.com`）

#### 4. "Session 初始化失敗"
**原因:** Backend API 錯誤
**解決:**
- 檢查 console 詳細錯誤訊息
- 確認後端服務正常運行
- 檢查 tenant_id 是否正確

## Backward Compatibility

### Feature Flag Pattern

保留舊的 Realtime API 作為 fallback：

```javascript
const USE_SESSION_WORKFLOW = localStorage.getItem('useSessionWorkflow') === 'true' || true;

if (USE_SESSION_WORKFLOW && isSessionInitialized) {
    // New workflow
    try {
        const analysis = await sessionWorkflow.performAnalysis(transcript, mode);
        displayAnalysisCard(analysis);
    } catch (error) {
        // Fallback to old API
        await performRealtimeAnalysisOld(transcript, mode);
    }
} else {
    // Old workflow
    await performRealtimeAnalysisOld(transcript, mode);
}
```

### Response Format Compatibility

`transformToRealtimeFormat()` 確保：
- Session API response → Realtime API format
- 現有的 `displayAnalysisCard()` 函數無需修改
- 額外的 Session metadata 在 `_session_metadata` 中提供

## Performance

- **Cold Start**: ~2-3s（創建 client + case + session）
- **Analysis**: ~1-2s（append + analyze）
- **Token Usage**: 與 Realtime API 相同

## Security

- **Authentication**: JWT token from localStorage
- **Multi-tenant**: Tenant ID isolation
- **HTTPS**: Production 必須使用 HTTPS
- **CORS**: Same-origin policy

## Next Steps

### 整合到 realtime_counseling.html

1. 閱讀 `integration-example.js`
2. 複製相關代碼到 `realtime_counseling.html`
3. 測試 workflow
4. 保留 feature flag（向後兼容）
5. 部署前測試所有功能

### 可選增強

- [ ] 自動重試機制
- [ ] 離線支援（cache analysis）
- [ ] 進度指示（loading states）
- [ ] 錯誤監控（Sentry integration）

## Support

如有問題，請參考：
- `integration-example.js` - 完整範例
- `test-session-workflow.html` - 測試頁面
- Backend tests: `tests/integration/test_web_session_workflow.py`

---

**Version:** 1.0.0
**Created:** 2025-01-01
**Author:** AI Assistant
**License:** MIT
