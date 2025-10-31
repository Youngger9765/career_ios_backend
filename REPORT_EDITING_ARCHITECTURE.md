# 報告編輯架構設計

## 📋 概述

本系統採用**雙版本存儲架構**,分離保存 AI 生成的原始報告和諮商師手動編輯的版本。

## 🗄️ 數據庫架構

### Report Model 新增欄位

```python
# app/models/report.py

class Report(Base, BaseModel):
    # AI 原始生成的報告 (不可變)
    content_json = Column(JSON)  # AI 生成的原始報告,永遠保留

    # 諮商師編輯後的版本
    edited_content_json = Column(JSON)  # 手動編輯的報告內容
    edited_at = Column(String)  # ISO 8601 timestamp
    edit_count = Column(Integer, default=0)  # 編輯次數
```

### 優點

1. **可追溯性**: 永遠保留 AI 原始版本
2. **可比對性**: 可以看出諮商師做了哪些調整
3. **可回溯性**: 如果改壞了可以重置回 AI 版本
4. **審計友好**: 符合醫療/諮商記錄規範

## 🔌 API 端點

### 1. 更新報告 (諮商師編輯)

**Endpoint:** `PATCH /api/v1/reports/{report_id}`

**Request:**
```json
{
  "edited_content_json": {
    "report": {
      "client_info": {...},
      "main_concerns": [...],
      "conceptualization": "...",
      ...
    }
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "edited_content_json": {...},
  "edited_at": "2025-10-29T10:30:00Z",
  "edit_count": 1,
  "formatted_markdown": "# 個案報告\n\n## 案主基本資料\n..."
}
```

**功能:**
- 保存諮商師編輯後的報告內容
- 自動更新 `edited_at` 時間戳
- 遞增 `edit_count` 計數器
- 返回格式化的 Markdown (供 iOS 顯示)

### 2. 取得格式化報告 (增強版)

**Endpoint:** `GET /api/v1/reports/{report_id}/formatted`

**Query Parameters:**
- `format`: `markdown` | `html` (預設: `markdown`)
- `use_edited`: `true` | `false` (預設: `true`)

**Response:**
```json
{
  "report_id": "uuid",
  "format": "markdown",
  "formatted_content": "# 報告內容...",
  "is_edited": true,
  "edited_at": "2025-10-29T10:30:00Z"
}
```

**行為:**
- 當 `use_edited=true` 且存在 `edited_content_json` 時,返回編輯版本
- 當 `use_edited=false` 或沒有編輯版本時,返回 AI 原始版本
- 返回 `is_edited` 標記告訴客戶端當前顯示的是哪個版本

## 📱 iOS App 使用流程

### 標準流程

```swift
// 1. 生成報告
let reportResponse = try await generateReport(...)

// 2. 取得格式化報告 (自動使用編輯版本)
let formatted = try await getFormattedReport(
    reportId: reportResponse.report_id,
    format: "markdown",
    useEdited: true  // 預設會用編輯版本
)

// 3. 在編輯器中顯示
editor.setMarkdown(formatted.formatted_content)

// 4. 諮商師編輯後,更新報告
let updatedReport = try await updateReport(
    reportId: reportResponse.report_id,
    editedContent: modifiedJSON
)

// 5. 顯示更新後的 Markdown
editor.setMarkdown(updatedReport.formatted_markdown)
```

### 比對 AI 原始版本

```swift
// 取得 AI 原始版本
let aiVersion = try await getFormattedReport(
    reportId: reportId,
    format: "markdown",
    useEdited: false  // 強制使用 AI 原始版本
)

// 取得編輯版本
let editedVersion = try await getFormattedReport(
    reportId: reportId,
    format: "markdown",
    useEdited: true
)

// 顯示 Diff
showDiff(original: aiVersion, edited: editedVersion)
```

### 重置為 AI 版本

```swift
// 讀取 AI 原始版本
let report = try await getReport(reportId: reportId)

// 用 AI 原始版本覆蓋編輯版本
let reset = try await updateReport(
    reportId: reportId,
    editedContent: report.content_json
)
```

## 🎯 測試控制台

訪問 `http://localhost:8080/console` 第 11 步:

1. 選擇要更新的報告
2. 在 JSON 編輯框中貼上修改後的報告內容
3. 點擊「更新報告」
4. 查看返回的 Markdown 格式化結果

## 📊 數據流程圖

```
┌─────────────────┐
│  AI 生成報告     │
│ content_json    │ ← 永遠不變,用於審計
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  諮商師編輯      │
│edited_content   │ ← 可多次更新
│   _json         │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  iOS App 顯示   │
│   (Markdown)    │ ← 預設顯示編輯版本
└─────────────────┘
```

## 🔒 安全性

- ✅ RLS (Row Level Security): 只能編輯自己的報告
- ✅ 審計追蹤: `edit_count` 和 `edited_at` 記錄所有變更
- ✅ 原始保留: `content_json` 永遠不被修改
- ✅ 版本比對: 可隨時比對 AI 原始版本和編輯版本

## 📝 Schema 更新

執行以下命令應用數據庫遷移:

```bash
alembic upgrade head
```

遷移文件: `alembic/versions/20251029_1826_d8c67e925aa7_add_report_editing_fields.py`

## 🧠 諮商師反思整合 ⭐️ NEW

### 反思在報告中的角色

諮商師反思是報告「四、個人化分析」章節的重要組成部分。

**資料來源:**
- **反思內容**: 來自 `GET /api/v1/sessions/{id}/reflection`
- **儲存位置**: `sessions.reflection` (JSON 欄位)
- **撰寫方式**: 諮商師人工撰寫，非 AI 生成

**反思問題結構:**
```json
{
  "working_with_client": "我和這個人工作的感受是？",
  "feeling_source": "這個感受的原因是？",
  "current_challenges": "目前的困難／想更深入的地方是？",
  "supervision_topics": "我會想找督導討論的問題是？"
}
```

### 在報告中顯示反思

**方案 1: 從 Session 取得反思（推薦）**
```swift
// 1. 取得報告
let report = try await getReport(reportId: reportId, useEdited: true)

// 2. 取得該報告對應的 session_id
let sessionId = report.session_id

// 3. 取得反思內容
let reflection = try await getReflection(sessionId: sessionId)

// 4. 在報告 UI 中顯示反思章節
```

**方案 2: 未來可考慮在報告 API 中包含反思**
```json
// GET /api/v1/reports/{id}?include_reflection=true
{
  "report": {...},
  "session": {
    "id": "uuid",
    "reflection": {...}
  }
}
```

### 編輯流程

1. **反思獨立編輯**: 使用 `PUT /api/v1/sessions/{id}/reflection` 更新
2. **與報告分離**: 反思不屬於報告內容，是會談記錄的一部分
3. **顯示在報告中**: 報告查看時動態取得並顯示反思內容

### 資料一致性

- 反思存在 `sessions` 表，與會談記錄綁定
- 報告存在 `reports` 表，通過 `session_id` 關聯
- 修改反思不影響報告版本，但查看報告時會顯示最新反思

---

## 🚀 下一步

建議在 iOS App 實作:

1. **Markdown 編輯器**: 使用 MarkdownUI 或 Down 框架
2. **版本比對**: 實作 Diff 視圖顯示 AI vs 編輯版本
3. **自動保存**: 編輯時每 30 秒自動保存草稿
4. **離線編輯**: 本地緩存,網路恢復時同步
5. **編輯歷史**: 顯示編輯次數和最後編輯時間
6. **反思編輯器**: ⭐️ 實作獨立的反思撰寫/編輯介面
7. **報告+反思整合視圖**: ⭐️ 查看報告時動態載入並顯示反思內容

---

**最後更新:** 2025-10-31
**架構設計:** 雙版本存儲 (AI Original + User Edited)
