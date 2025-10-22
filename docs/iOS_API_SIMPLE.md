# iOS API 文件

**Base URL**: `https://career-app-api-staging-kxaznpplqq-uc.a.run.app`

**核心功能**: 輸入逐字稿 → 生成 AI 報告

---

## 📑 文件導覽

### 快速開始
- [生成報告 API](#-生成報告-api) - API endpoint 和基本參數
- [快速選擇指南](#-快速選擇指南) - 我該選哪個組合？
- [Swift 完整實作](#-swift-完整實作) - iOS 開發範例

### 參數說明
- [🔧 參數組合完整指南](#-參數組合完整指南) - **6種組合**的 Request 範例
- [📤 Response 範例總覽](#-response-範例總覽) - **6種組合**的完整 Response

### 報告模式詳解
- [1️⃣ 新版 10 段式報告](#1️⃣-新版-10-段式報告modeenhanced) - Enhanced mode 詳解
- [2️⃣ 舊版 5 段式報告](#2️⃣-舊版-5-段式報告modelegacy) - Legacy mode 詳解

### 比較表格
- [📊 報告類型比較](#-報告類型比較) - Legacy vs Enhanced
- [📋 輸出格式比較](#-輸出格式比較) - JSON vs Markdown vs HTML

### 疑難排解
- [❓ 常見問題](#-常見問題) - FAQ 快速解答
- [🐛 錯誤碼說明](#-錯誤碼說明) - HTTP 錯誤處理
- [🔍 測試](#-測試) - Swagger UI 和測試頁面

---

## 🎯 生成報告 API

### Endpoint

```http
POST /api/report/generate
Content-Type: application/json
```

### Request Body

```json
{
  "transcript": "完整逐字稿內容...",
  "num_participants": 2,
  "mode": "enhanced",
  "rag_system": "openai",
  "top_k": 7,
  "similarity_threshold": 0.25,
  "output_format": "json"
}
```

### 參數說明

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| `transcript` | string | ✅ Yes | - | 完整逐字稿文字 |
| `num_participants` | integer | ❌ No | 2 | 會談人數 |
| `mode` | string | ❌ No | "enhanced" | **報告模式**：`"legacy"`=舊版5段式，`"enhanced"`=新版10段式（推薦） |
| `rag_system` | string | ❌ No | "openai" | AI模型：`"openai"` 或 `"gemini"` |
| `top_k` | integer | ❌ No | 7 | RAG檢索文獻數量 |
| `similarity_threshold` | float | ❌ No | 0.25 | 相似度門檻（⚠️ 若低於此值未找到文獻，將回傳錯誤） |
| `output_format` | string | ❌ No | "json" | **輸出格式**：`"json"`, `"html"`, `"markdown"` |

---

## 📋 Response 格式說明

### 2 種報告模式

| 模式 | mode 參數 | 說明 | Response 結構 |
|------|----------|------|--------------|
| **新版10段式** | `"enhanced"` | 推薦：完整深入分析（10個段落） | 單一報告 + 品質評分 |
| **舊版5段式** | `"legacy"` | 簡化版（5個段落） | 單一報告 + 品質評分 |

### 輸出格式組合

每種模式都支援 3 種輸出格式：

| output_format | 說明 | 適用情境 |
|--------------|------|---------|
| `"json"` | **推薦**：結構化資料 | iOS App 開發 |
| `"html"` | HTML 標籤 | 網頁顯示 |
| `"markdown"` | Markdown 文字 | 文字編輯器、匯出檔案 |

---

## 🔧 參數組合完整指南

### 視覺化參數組合

```
              API 參數組合
                   │
        ┌──────────┴──────────┐
        │                     │
    mode: "legacy"      mode: "enhanced" ✅ 推薦
    (舊版 5段式)         (新版 10段式)
        │                     │
    ┌───┼───┐             ┌───┼───┐
    │   │   │             │   │   │
   JSON MD HTML         JSON MD HTML
    ↓   ↓   ↓             ↓   ↓   ↓
   組合 組合 組合          組合 組合 組合
    1   2   3             4   5   6

JSON = output_format: "json"
MD   = output_format: "markdown"
HTML = output_format: "html"
```

### 核心參數組合矩陣

API 支援 **2 種報告模式 × 3 種輸出格式 = 6 種組合**

| 組合 ID | mode | output_format | 用途 | Response 類型 |
|---------|------|---------------|------|---------------|
| 1 | `"legacy"` | `"json"` | 舊版報告 - 結構化資料 | `ReportResponse` |
| 2 | `"legacy"` | `"markdown"` | 舊版報告 - 純文字 | `MarkdownReportResponse` |
| 3 | `"legacy"` | `"html"` | 舊版報告 - HTML | `HTMLReportResponse` |
| 4 | `"enhanced"` | `"json"` | ✅ **推薦** - 新版報告 - 結構化資料 | `ReportResponse` |
| 5 | `"enhanced"` | `"markdown"` | 新版報告 - 純文字 | `MarkdownReportResponse` |
| 6 | `"enhanced"` | `"html"` | 新版報告 - HTML | `HTMLReportResponse` |

### Request 範例總覽

#### 範例 1: Legacy + JSON（舊版結構化）

```json
{
  "transcript": "完整逐字稿...",
  "num_participants": 2,
  "mode": "legacy",
  "output_format": "json"
}
```

#### 範例 2: Legacy + Markdown（舊版純文字）

```json
{
  "transcript": "完整逐字稿...",
  "mode": "legacy",
  "output_format": "markdown"
}
```

#### 範例 3: Legacy + HTML（舊版網頁）

```json
{
  "transcript": "完整逐字稿...",
  "mode": "legacy",
  "output_format": "html"
}
```

#### 範例 4: Enhanced + JSON（✅ 推薦）

```json
{
  "transcript": "完整逐字稿...",
  "mode": "enhanced",
  "output_format": "json"
}
```

#### 範例 5: Enhanced + Markdown（新版純文字）

```json
{
  "transcript": "完整逐字稿...",
  "mode": "enhanced",
  "output_format": "markdown"
}
```

#### 範例 6: Enhanced + HTML（新版網頁）

```json
{
  "transcript": "完整逐字稿...",
  "mode": "enhanced",
  "output_format": "html"
}
```

---

## 📤 Response 範例總覽

### 組合 1-3: Legacy Mode (舊版 5段式)

#### Legacy + JSON

```json
{
  "mode": "legacy",
  "report": {
    "client_info": { "name": "案主A", ... },
    "session_summary": { ... },
    "conceptualization": "【主訴問題】\n...\n【目前成效評估】",
    "main_concerns": ["職涯困惑"],
    "counseling_goals": ["釐清方向"],
    "techniques": ["引導提問"],
    "theories": [{"text": "Super理論...", "document": "...", "score": 0.5}],
    "dialogue_excerpts": [...]
  },
  "format": "json",
  "quality_summary": {
    "total_score": 72,
    "grade": "B",
    "strengths": ["結構清晰"],
    "weaknesses": ["理論引用較少"]
  }
}
```

#### Legacy + Markdown

```json
{
  "mode": "legacy",
  "report": "# 職游創新職涯發展與諮詢 - 個案報告\n\n## 概念化分析\n\n### 主訴問題\n案主表示對未來職涯方向感到困惑...\n\n### 成因分析\n根據 Super 生涯發展理論 [1]，案主目前處於探索期...",
  "format": "markdown",
  "quality_summary": { ... }
}
```

#### Legacy + HTML

```json
{
  "mode": "legacy",
  "report": "<h1>職游創新職涯發展與諮詢 - 個案報告</h1>\n<h2>概念化分析</h2>\n<h3>主訴問題</h3>\n<p>案主表示對未來職涯方向感到困惑...</p>",
  "format": "html",
  "quality_summary": { ... }
}
```

### 組合 4-6: Enhanced Mode (新版 10段式)

#### Enhanced + JSON（✅ 推薦）

```json
{
  "mode": "enhanced",
  "report": {
    "client_info": {
      "name": "案主B",
      "gender": "未提及",
      "age": "25-30",
      "occupation": "軟體工程師",
      "education": "大學",
      "location": "台北",
      "economic_status": "中等",
      "family_relations": "單身",
      "other_info": ["學習能力強", "T型通才"]
    },
    "session_summary": {
      "content": "本次晤談主要討論案主的職涯發展困境...",
      "self_evaluation": "能有效引導案主反思..."
    },
    "conceptualization": "【一、案主基本資料】\n根據逐字稿，案主為25-30歲軟體工程師...\n\n【二、主訴問題】\n- 個案陳述：對核心專業能力感到不明確...\n\n【三、問題發展脈絡】\n- 出現時間：近半年\n- 持續頻率：經常性困擾\n\n【四、求助動機與期待】\n希望釐清職涯方向...\n\n【五、多層次因素分析】⭐\n- 個人因素：根據 Super 生涯發展理論 [1]...\n- 環境因素：科技業快速變化 [2]...\n\n【六、個案優勢與資源】\n- 學習能力強\n- T型通才背景\n\n【七、諮詢師的專業判斷】⭐\n根據認知行為理論 [3]，案主可能存在...\n\n【八、諮商目標與介入策略】⭐\n- 使用引導式提問 [4][5]\n- 職涯探索活動\n\n【九、預期成效與評估】\n預期案主能在3次晤談內...\n\n【十、諮詢師自我反思】\n本次諮詢中，我有效運用了...",
    "main_concerns": [
      "核心專業能力不明確",
      "職涯方向困惑",
      "技能選擇焦慮"
    ],
    "counseling_goals": [
      "釐清職涯核心方向",
      "建立技能發展地圖",
      "降低決策焦慮"
    ],
    "techniques": [
      "引導式提問",
      "案例分享",
      "認知重構",
      "職涯探索活動"
    ],
    "theories": [
      {
        "text": "Super 生涯發展理論指出，個體在探索期會經歷職業偏好的形成...",
        "document": "05 第五天講義-心理諮詢技巧.pdf",
        "score": 0.532
      },
      {
        "text": "認知行為理論認為，個體的思考模式會影響情緒反應...",
        "document": "認知行為治療手冊.pdf",
        "score": 0.487
      }
    ],
    "dialogue_excerpts": [
      {
        "speaker": "speaker1",
        "order": 1,
        "text": "我最近一直在想，我到底應該專精在哪一個技能上..."
      },
      {
        "speaker": "speaker2",
        "order": 2,
        "text": "你提到專精，可以多說一些你對專精的理解嗎？"
      }
    ]
  },
  "format": "json",
  "quality_summary": {
    "total_score": 88,
    "grade": "A-",
    "strengths": [
      "結構完整且層次分明",
      "理論引用豐富且適切",
      "多層次因素分析深入",
      "自我反思具體"
    ],
    "weaknesses": [
      "部分段落可加入更多具體案例",
      "預期成效的評估指標可更量化"
    ]
  }
}
```

#### Enhanced + Markdown

```json
{
  "mode": "enhanced",
  "report": "# 職游創新職涯發展與諮詢 - 個案報告\n\n**諮詢練習生**：-\n**完成撰寫日期**：2025/10/21\n\n---\n\n## 一、案主基本資料\n\n| 項目 | 內容 |\n|-----|------|\n| 1. 姓名(化名) | 案主B |\n| 2. 性別 | 未提及 |\n| 3. 年齡 | 25-30 |\n| 4. 職業 | 軟體工程師 |\n\n## 二、歷程分析\n\n| 次數 | 晤談內容概述 | 諮詢師自評 |\n|-----|------------|----------|\n| 第1次 | 討論職涯困境 | 能有效引導 |\n\n## 三、概念化分析\n\n### 主訴問題\n- 核心專業能力不明確\n- 職涯方向困惑\n\n### 成因分析\n根據 Super 生涯發展理論 [1]，案主處於探索期...\n\n### 晤談目標\n- 釐清職涯核心方向\n- 建立技能發展地圖\n\n### 介入策略\n- 引導式提問\n- 認知重構\n\n### 目前成效評估\n案主開始能夠...\n\n---\n\n## 四、個人化分析\n\n【一、案主基本資料】\n根據逐字稿...\n\n【二、主訴問題】\n...\n\n【十、諮詢師自我反思】\n...\n\n---\n\n## 關鍵對話摘錄\n\n**個案**: 我最近一直在想，我到底應該專精在哪一個技能上...\n\n**諮詢師**: 你提到專精，可以多說一些你對專精的理解嗎？\n\n---\n\n## 參考理論文獻\n\n**[1]** 05 第五天講義-心理諮詢技巧.pdf (相似度: 53.2%)\n\n**[2]** 認知行為治療手冊.pdf (相似度: 48.7%)",
  "format": "markdown",
  "quality_summary": {
    "total_score": 88,
    "grade": "A-",
    "strengths": ["..."],
    "weaknesses": ["..."]
  }
}
```

#### Enhanced + HTML

```json
{
  "mode": "enhanced",
  "report": "<h1>職游創新職涯發展與諮詢 - 個案報告</h1>\n<p><strong>諮詢練習生</strong>：-</p>\n<p><strong>完成撰寫日期</strong>：2025/10/21</p>\n<hr>\n<h2>一、案主基本資料</h2>\n<table>\n  <tr><th>項目</th><th>內容</th></tr>\n  <tr><td>姓名(化名)</td><td>案主B</td></tr>\n</table>\n...",
  "format": "html",
  "quality_summary": { ... }
}
```

---

## 1️⃣ 新版 10 段式報告（mode: "enhanced"）

### Response 結構

```json
{
  "mode": "enhanced",
  "report": {
    "client_info": { ... },
    "session_summary": { ... },
    "conceptualization": "【一、案主基本資料】\n...\n【十、諮詢師自我反思】",
    "main_concerns": [...],
    "counseling_goals": [...],
    "techniques": [...],
    "theories": [...],
    "dialogue_excerpts": [...]
  },
  "format": "json|html|markdown",
  "quality_summary": { ... }
}
```

### 完整範例（JSON 格式）

```json
{
  "report": {
    "client_info": {
      "name": "案主化名",
      "gender": "未提及",
      "age": "未提及",
      "occupation": "未提及",
      "education": "未提及",
      "location": "未提及",
      "economic_status": "未提及",
      "family_relations": "未提及",
      "other_info": [
        "學習能力和理解能力快",
        "屬於T型通才"
      ]
    },
    "session_summary": {
      "content": "討論學習曲線、技能開發與職涯方向...",
      "self_evaluation": "能夠引導案主思考..."
    },
    "conceptualization": "【一、案主基本資料】\n根據逐字稿提取的資訊整理如下...\n\n【二、主訴問題】\n- 個案陳述：案主表示對核心專業能力感到不明確...\n\n【三、問題發展脈絡】\n- 出現時間：...\n- 持續頻率：...\n\n【四、求助動機與期待】\n...\n\n【五、多層次因素分析】⭐ 含理論引用\n- 個人因素：案主可能處於生涯探索期，根據 Super 生涯發展理論 [1]...\n\n【六、個案優勢與資源】\n...\n\n【七、諮詢師的專業判斷】⭐ 含理論引用\n- 根據認知行為理論 [3]，案主可能存在不當的自我評價...\n\n【八、諮商目標與介入策略】⭐ 含理論引用\n- 使用引導式提問技術 [5][6]...\n\n【九、預期成效與評估】\n...\n\n【十、諮詢師自我反思】\n在此次諮詢中，我能夠有效引導案主思考...",
    "main_concerns": [
      "核心專業能力不明確",
      "情緒困擾"
    ],
    "counseling_goals": [
      "確定職涯方向",
      "理解生涯需求"
    ],
    "techniques": [
      "引導式提問",
      "案例分享"
    ],
    "theories": [
      {
        "text": "Super 生涯發展理論指出在探索期...",
        "document": "05 第五天講義-心理諮詢技巧-誠誠.pdf",
        "score": 0.532513248847122
      }
    ],
    "dialogue_excerpts": [
      {
        "speaker": "speaker2",
        "order": 1,
        "text": "我覺得說, 那會不會其實多開幾個技能術..."
      }
    ]
  },
  "format": "json",
  "quality_summary": {
    "total_score": 85,
    "grade": "B+",
    "strengths": ["結構完整", "理論引用適當"],
    "weaknesses": ["部分段落可更深入"]
  }
}
```

### Markdown 格式範例

當 `output_format: "markdown"` 時，response 為：

```json
{
  "report": "# 職游創新職涯發展與諮詢 - 個案報告\n\n**諮詢練習生**：-\n**完成撰寫日期**：2025/10/21\n\n---\n\n## 一、案主基本資料\n\n| 項目 | 內容 |\n|-----|------|\n| 1. 姓名(化名) | 案主化名 |\n| 2. 性別 | 未提及 |\n...\n\n## 二、歷程分析\n\n| 次數/晤談時間 | 晤談內容概述 | 諮詢師自評 |\n...\n\n## 三、概念化分析\n\n### 主訴問題\n核心專業能力不明確、情緒困擾\n\n### 成因分析\n-\n\n### 晤談目標(移動主訴)\n確定職涯方向、理解生涯需求\n\n### 介入策略\n引導式提問、案例分享\n\n### 目前成效評估\n-\n\n---\n\n## 四、個人化分析\n...\n\n## 關鍵對話摘錄\n\n**個案**: 我覺得說, 那會不會其實多開幾個技能術...\n\n**諮詢師**: 我覺得應該會讓你更困惑...\n\n---\n\n## 參考理論文獻\n\n**[1]** 05 第五天講義-心理諮詢技巧-誠誠.pdf (相似度: 53.3%)\n\n...",
  "format": "markdown",
  "quality_summary": { ... }
}
```

---

## 2️⃣ 舊版 5 段式報告（mode: "legacy"）

### Response 結構（相同）

```json
{
  "mode": "legacy",
  "report": {
    "client_info": { ... },
    "session_summary": { ... },
    "conceptualization": "【主訴問題】\n...\n【目前成效評估】",
    "main_concerns": [...],
    "counseling_goals": [...],
    "techniques": [...],
    "theories": [...],
    "dialogue_excerpts": [...]
  },
  "format": "json|html|markdown",
  "quality_summary": { ... }
}
```

### 差異在於 `conceptualization` 欄位

**舊版 5 段式**：
```
【主訴問題】
個案說的，此次想要討論的議題

【成因分析】⭐ 含理論引用
諮詢師您認為，個案為何會有這些主訴問題，請結合引用的理論 [1], [2] 等進行分析

【晤談目標（移動主訴）】
諮詢師對個案諮詢目標的假設，須與個案確認

【介入策略】
諮詢師判斷會需要帶個案做的事，結合理論說明

【目前成效評估】
上述目標和策略達成的狀況如何，目前打算如何修正
```

---

## 📱 Swift 完整實作

### Data Models

```swift
// MARK: - Request

struct ReportRequest: Codable {
    let transcript: String
    let numParticipants: Int
    let mode: String
    let ragSystem: String
    let topK: Int
    let similarityThreshold: Double
    let outputFormat: String

    init(
        transcript: String,
        numParticipants: Int = 2,
        mode: String = "enhanced",  // "legacy" or "enhanced"
        ragSystem: String = "openai",
        topK: Int = 7,
        similarityThreshold: Double = 0.25,
        outputFormat: String = "json"  // "json", "html", "markdown"
    ) {
        self.transcript = transcript
        self.numParticipants = numParticipants
        self.mode = mode
        self.ragSystem = ragSystem
        self.topK = topK
        self.similarityThreshold = similarityThreshold
        self.outputFormat = outputFormat
    }
}

// MARK: - Response

struct ReportResponse: Codable {
    let mode: String
    let report: ReportData
    let format: String
    let qualitySummary: QualitySummary?
}

// 當 output_format = "json" 時
struct ReportData: Codable {
    let clientInfo: ClientInfo
    let sessionSummary: SessionSummary
    let conceptualization: String  // 核心報告內容（10段式或5段式文字）
    let mainConcerns: [String]
    let counselingGoals: [String]
    let techniques: [String]
    let theories: [Theory]
    let dialogueExcerpts: [Dialogue]
}

// 當 output_format = "markdown" 或 "html" 時
// report 欄位直接是 String（完整格式化的文字）

struct ClientInfo: Codable {
    let name: String
    let gender: String
    let age: String
    let occupation: String
    let education: String
    let location: String
    let economicStatus: String
    let familyRelations: String
    let otherInfo: [String]
}

struct SessionSummary: Codable {
    let content: String
    let selfEvaluation: String
}

struct Theory: Codable {
    let text: String
    let document: String
    let score: Double
}

struct Dialogue: Codable {
    let speaker: String
    let order: Int
    let text: String
}

struct QualitySummary: Codable {
    let totalScore: Int
    let grade: String
    let strengths: [String]
    let weaknesses: [String]
}
```

### API Service

```swift
class CareerReportService {
    private let baseURL = "https://career-app-api-staging-kxaznpplqq-uc.a.run.app"

    /// 生成 AI 報告（JSON 格式）
    func generateReport(
        transcript: String,
        mode: String = "enhanced",
        numParticipants: Int = 2
    ) async throws -> ReportResponse {

        let url = URL(string: "\(baseURL)/api/report/generate")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let requestBody = ReportRequest(
            transcript: transcript,
            numParticipants: numParticipants,
            mode: mode,
            outputFormat: "json"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(requestBody)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(ReportResponse.self, from: data)
    }

    /// 生成 Markdown 格式報告
    func generateMarkdownReport(
        transcript: String,
        mode: String = "enhanced"
    ) async throws -> String {

        let url = URL(string: "\(baseURL)/api/report/generate")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let requestBody = ReportRequest(
            transcript: transcript,
            mode: mode,
            outputFormat: "markdown"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(requestBody)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let result = try decoder.decode(MarkdownReportResponse.self, from: data)

        return result.report
    }
}

struct MarkdownReportResponse: Codable {
    let report: String  // Markdown 格式的完整報告
    let format: String
    let qualitySummary: QualitySummary?
}
```

### 使用範例

```swift
class ReportViewController: UIViewController {
    let service = CareerReportService()

    @IBAction func generateReport() {
        guard let transcript = transcriptTextView.text,
              !transcript.isEmpty else {
            showError("請輸入逐字稿")
            return
        }

        showLoading("正在生成報告...")

        Task {
            do {
                // 方式 1: JSON 格式（推薦，結構化資料）
                let mode = reportFormatSegment.selectedSegmentIndex == 0 ? "legacy" : "enhanced"

                let result = try await service.generateReport(
                    transcript: transcript,
                    mode: mode,
                    numParticipants: 2
                )

                await MainActor.run {
                    hideLoading()
                    displayJSONReport(result)
                }

            } catch {
                await MainActor.run {
                    hideLoading()
                    showError("生成報告失敗: \(error.localizedDescription)")
                }
            }
        }
    }

    func displayJSONReport(_ response: ReportResponse) {
        let report = response.report

        // 顯示完整報告文字（10段式或5段式）
        reportTextView.text = report.conceptualization

        // 顯示案主資訊
        clientNameLabel.text = report.clientInfo.name
        clientAgeLabel.text = report.clientInfo.age
        clientOccupationLabel.text = report.clientInfo.occupation

        // 顯示主訴問題
        mainConcernsLabel.text = report.mainConcerns.joined(separator: ", ")

        // 顯示品質評分
        if let quality = response.qualitySummary {
            scoreLabel.text = "\(quality.totalScore)分 (\(quality.grade))"
            strengthsTextView.text = "✅ 優點：\n" + quality.strengths.joined(separator: "\n")
            weaknessesTextView.text = "⚠️ 待改進：\n" + quality.weaknesses.joined(separator: "\n")
        }

        // 顯示引用理論
        theoriesTableView.reloadData()

        // 顯示關鍵對話
        dialoguesTableView.reloadData()
    }

    @IBAction func generateMarkdownReport() {
        Task {
            do {
                let markdown = try await service.generateMarkdownReport(
                    transcript: transcriptTextView.text,
                    mode: "enhanced"
                )

                // 直接顯示或儲存 Markdown
                await MainActor.run {
                    markdownTextView.text = markdown
                }

            } catch {
                showError(error.localizedDescription)
            }
        }
    }
}
```

---

## 🎯 快速選擇指南

### 我該用哪個組合？

| 使用情境 | 推薦組合 | 原因 |
|---------|---------|------|
| **iOS App 開發（推薦）** | `mode: "enhanced"` + `output_format: "json"` | 結構化資料，易於解析和UI顯示 |
| **匯出完整報告文字** | `mode: "enhanced"` + `output_format: "markdown"` | 純文字格式，可儲存檔案或分享 |
| **網頁/Email 顯示** | `mode: "enhanced"` + `output_format: "html"` | 直接嵌入網頁或郵件 |
| **快速簡化報告** | `mode: "legacy"` + `output_format: "json"` | 5段式，處理時間更短 |

### Response 結構差異總結

| 參數組合 | response.report 類型 | 核心欄位 |
|---------|---------------------|---------|
| `output_format: "json"` | **Object**（結構化） | `report.conceptualization`（文字）<br>`report.client_info`（物件）<br>`report.theories`（陣列）<br>`report.dialogue_excerpts`（陣列） |
| `output_format: "markdown"` | **String**（純文字） | `report`（完整 Markdown 文字） |
| `output_format: "html"` | **String**（HTML） | `report`（完整 HTML 標籤） |

### Swift 解析建議

```swift
// 根據 output_format 解析
func parseReport(data: Data, outputFormat: String) throws -> Any {
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase

    switch outputFormat {
    case "json":
        return try decoder.decode(ReportResponse.self, from: data)
    case "markdown", "html":
        return try decoder.decode(MarkdownReportResponse.self, from: data)
    default:
        throw ParseError.invalidFormat
    }
}

```

---

## 📊 報告類型比較

| 特性 | 舊版5段式 (`mode: "legacy"`) | 新版10段式 (`mode: "enhanced"`) |
|------|------------------------------|--------------------------------|
| **段落數** | 5 個 | 10 個 |
| **結構** | 【主訴問題】<br>【成因分析】<br>【晤談目標】<br>【介入策略】<br>【成效評估】 | 【一、案主基本資料】<br>【二、主訴問題】<br>【三、問題發展脈絡】<br>【四、求助動機與期待】<br>【五、多層次因素分析】⭐<br>【六、個案優勢與資源】<br>【七、諮詢師的專業判斷】⭐<br>【八、諮商目標與介入策略】⭐<br>【九、預期成效與評估】<br>【十、諮詢師自我反思】 |
| **理論引用** | 較少 | 更多更深入 |
| **詳細程度** | 簡化版 | 完整版 |
| **適用情境** | 快速報告 | 正式個案報告 |
| **評分上限** | ~75 分 | ~100 分 |
| **處理時間** | ~30-45秒 | ~30-45秒 |

---

## 📋 輸出格式比較

| 格式 | output_format | 適用情境 | response.report 類型 |
|------|---------------|---------|---------------------|
| **JSON** | `"json"` | iOS App（推薦） | Object（結構化資料） |
| **Markdown** | `"markdown"` | 文字編輯器、儲存檔案 | String（Markdown 文字） |
| **HTML** | `"html"` | 網頁顯示、Email | String（HTML 標籤） |

---

## ⚠️ 重要提醒

### iOS 開發建議

1. **推薦組合**: `mode: "enhanced"` + `output_format: "json"`
   - 新版10段式報告
   - 結構化資料，方便解析和顯示

2. **Markdown 用途**: 若需要匯出或分享報告文字
   - `output_format: "markdown"`
   - 直接得到格式化的完整報告文字

3. **核心欄位**: `report.conceptualization`
   - 包含完整的報告內容（10段式或5段式）
   - 這是報告的**主體文字**

4. **RAG 強制檢查**:
   - API 會強制檢查是否檢索到理論文獻
   - 若 `similarity_threshold` 太高導致無文獻，將回傳 HTTP 400 錯誤
   - 建議使用預設值 0.25

5. **Comparison 模式注意**:
   - 處理時間約為單一模式的兩倍
   - Response 格式不同，需使用 `ComparisonResponse` 解析
   - 適合用於評估報告品質差異

---

## 🔍 測試

### Swagger UI
https://career-app-api-staging-kxaznpplqq-uc.a.run.app/docs

找到 `POST /api/report/generate` 測試

### 前端測試頁面
https://career-app-api-staging-kxaznpplqq-uc.a.run.app/rag/report

可直接測試不同組合

---

## ❓ 常見問題

### Q1: 我該用哪個 mode？

- **新專案/正式環境** → `mode: "enhanced"` (10段式，品質更高)
- **快速測試/簡化需求** → `mode: "legacy"` (5段式，更快速)

### Q2: 我該用哪個 output_format？

- **iOS App 開發** → `"json"` (結構化資料，方便解析)
- **匯出/分享報告** → `"markdown"` (純文字，易儲存)
- **網頁/Email** → `"html"` (直接嵌入)

### Q3: 為什麼會收到 HTTP 400 錯誤？

可能原因：
1. **未檢索到理論文獻** - `similarity_threshold` 設定過高
   - 解決：降低至預設值 0.25 或更低
2. **逐字稿內容過短** - 少於 100 字
   - 解決：提供更完整的逐字稿
3. **參數格式錯誤** - JSON 格式不正確
   - 解決：檢查參數類型 (string, int, float)

### Q4: JSON 格式的 report 和 Markdown 格式的 report 有什麼差別？

```swift
// JSON 格式 - report 是 Object
let jsonReport = response.report.conceptualization  // 取得報告文字
let theories = response.report.theories  // 取得理論陣列

// Markdown/HTML 格式 - report 是 String
let markdownReport = response.report  // 直接就是完整報告文字
```

### Q5: theories 陣列的 score 代表什麼？

`score` 是 RAG 系統計算的**語意相似度分數** (0-1)：
- 0.7 以上 = 高度相關
- 0.5-0.7 = 中度相關
- 0.25-0.5 = 低度相關
- 低於 0.25 = 不相關（不會出現）

### Q6: 如何調整檢索到的文獻數量？

使用 `top_k` 參數：
- `top_k: 5` → 最多檢索 5 篇文獻
- `top_k: 7` → 預設值，推薦
- `top_k: 10` → 檢索更多文獻（但可能降低相關性）

---

## 🐛 錯誤碼說明

| HTTP Code | 錯誤原因 | 解決方法 |
|-----------|---------|---------|
| 400 | 參數格式錯誤 | 檢查 JSON 格式和參數類型 |
| 400 | 未檢索到理論文獻 | 降低 `similarity_threshold` |
| 400 | 逐字稿內容過短 | 提供更完整的逐字稿（建議 > 500 字） |
| 500 | OpenAI API 錯誤 | 稍後重試，或切換到 `rag_system: "gemini"` |
| 500 | 伺服器內部錯誤 | 稍後重試，或聯繫技術支援 |

---

**Last Updated**: 2025-10-22
**API Version**: v1.0
**Endpoint**: `POST /api/report/generate`
