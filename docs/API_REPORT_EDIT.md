# Report Edit API 使用指南

## PATCH /api/v1/reports/{id}

更新報告的編輯內容（諮商師編輯）

### 🎯 重要：前端應該直接傳 Markdown 字串

**前端編輯流程**：
1. 使用者在 iOS App 上編輯 Markdown 內容
2. 前端直接將編輯後的 Markdown 字串傳給後端
3. **不需要**前端自己生成 JSON 或從 Markdown 轉換

---

## Request Body Options

### ✅ **推薦方式 1：只傳 Markdown（前端編輯）**

前端使用者編輯 Markdown 內容後，直接傳給後端：

```json
{
  "edited_content_markdown": "# 個案報告\n\n## 個案概念化\n\n個案呈現焦慮症狀..."
}
```

**使用場景**：iOS App 的 Markdown 編輯器

---

### ✅ **方式 2：同時傳 JSON 和 Markdown**

如果前端同時維護 JSON 結構和 Markdown 顯示：

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

### ⚠️ **方式 3：只傳 JSON（向後相容）**

如果前端只傳 JSON，後端會自動生成 Markdown（為了向後相容）：

```json
{
  "edited_content_json": {
    "client_name": "個案 A",
    "conceptualization": "焦慮症狀"
  }
}
```

**不推薦**：這種方式生成的 Markdown 是固定格式，無法自訂排版

---

## Response

### Success (200)

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

### Validation Error (400)

```json
{
  "detail": "Must provide either edited_content_json or edited_content_markdown"
}
```

---

## iOS Swift 範例

### 方式 1：只傳 Markdown（推薦）

```swift
struct ReportUpdateRequest: Codable {
    let edited_content_markdown: String?
    let edited_content_json: [String: Any]?

    enum CodingKeys: String, CodingKey {
        case edited_content_markdown
        case edited_content_json
    }
}

func updateReportMarkdown(reportId: UUID, markdown: String) async throws {
    let url = URL(string: "\(baseURL)/api/v1/reports/\(reportId)")!
    var request = URLRequest(url: url)
    request.httpMethod = "PATCH"
    request.addValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body: [String: Any] = [
        "edited_content_markdown": markdown
    ]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)

    let (_, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw APIError.updateFailed
    }
}
```

### 使用範例

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
try await updateReportMarkdown(reportId: reportId, markdown: editedMarkdown)
```

---

## 測試範例

### cURL 測試

```bash
# 1. Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@career.com", "password": "password123"}' \
  | jq -r '.access_token')

# 2. Update with only markdown
curl -X PATCH "http://localhost:8000/api/v1/reports/{report_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_content_markdown": "# 測試報告\n\n這是前端編輯的內容"
  }'
```

---

## 關鍵特性

✅ **前端完全控制 Markdown 格式**
✅ **支援 Emoji、特殊字符、Code blocks**
✅ **持久化到 Supabase（使用 `flag_modified()`）**
✅ **向後相容（只傳 JSON 會自動生成 Markdown）**

---

## 相關文件

- [完整 API 指南](../IOS_API_GUIDE.md)
- [Report Model](../app/models/report.py)
- [Report Schema](../app/schemas/report.py)
- [單元測試](../tests/unit/test_report_markdown_direct_update.py)
