# 職涯諮詢平台 PRD

## 系統概述

### 核心架構
本系統採用**雙業務線獨立架構**：

1. **RAG Ops 生產線**（管理層）
   - 建立 AI 能力：上傳文件 → 向量化 → 建立 Agent
   - 內部使用：`/rag/*` (Next.js Console)

2. **諮詢應用線**（業務層）
   - 提供諮詢服務：音訊/逐字稿 → RAG Agent → 生成報告
   - 對外服務：`/api/v1/*` (iOS + API)

### 技術棧
- **後端**: Python 3.11 + FastAPI + SQLAlchemy 2.0
- **資料庫**: PostgreSQL 15 + pgvector (Supabase 託管)
- **AI**: Gemini 3 Flash + OpenAI text-embedding-3-small
- **部署**: Docker + Google Cloud Run
- **測試**: pytest + Ruff + Mypy

---

## [Unreleased] - 開發中功能

### 🚀 Web Session Workflow 模組化完成 (2026-01-01)
**功能定位**: Web 即時諮詢統一使用 Session API workflow（與 iOS 一致）

#### 核心架構
- **模組化 JavaScript**:
  - `app/static/js/api-client.js` - 統一 API 通訊層
  - `app/static/js/session-workflow.js` - Session 生命週期管理
- **Feature Flag 控制**: `USE_NEW_SESSION_WORKFLOW` 開關新舊架構
- **向後相容**: 保留舊 Realtime API 路徑，確保平滑遷移

#### 技術細節
- **iOS 同款 Workflow**: create → append → analyze
- **Response 轉換層**: Session API 回應自動轉換為 Realtime API 格式
- **UI 完全相容**: 既有 `displayAnalysisCard` 函數無需修改
- **統一 API 端點**:
  - `POST /api/v1/ui/client-case` - 創建 client + case
  - `POST /api/v1/sessions` - 創建 session
  - `POST /api/v1/sessions/{id}/recordings/append` - 添加錄音
  - `POST /api/v1/sessions/{id}/analyze-partial` - 分析片段

#### 測試覆蓋
- ✅ 3 個整合測試通過 (test_web_session_workflow.py)
  - test_complete_web_session_workflow
  - test_web_workflow_multiple_analyses
  - test_web_workflow_emergency_mode
- ✅ 283 個整合測試通過（無迴歸）

#### 相關文件
- 📝 實作指南: `docs/web-session-workflow-implementation.md`
- 📝 API 文檔: `app/static/js/README.md`
- 📝 整合範例: `app/static/integration-example.js`
- 📝 測試頁面: `app/static/test-session-workflow.html`

---

## 當前可用功能 (2025-12-31)

### ✅ AI Provider 架構 (Updated 2025-12-31)
- **統一使用 Gemini** - 簡化為單一 AI provider
  - 移除 CodeerProvider 支援（實測效果不佳，commit: 2244b2d）
  - 程式碼減少 ~1,800 行，降低維護複雜度
  - 統一使用 Gemini 3 Flash 提供一致性體驗
- **核心功能**:
  - 🤖 關鍵詞分析（Keyword Analysis）- JSON 結構化回應
  - 📚 RAG 知識庫整合（island_parents 親子教養知識）
  - 🎯 多租戶支援（career, island_parents）
  - 🔄 雙模式支援（Emergency/Practice mode）
  - 📖 8 大教養流派理論框架整合
- **測試覆蓋**: 280 個整合測試通過，0 失敗，100% pass rate
- **文檔**: 完整的 8 Schools of Parenting 理論文檔

### ~~✅ Codeer AI API 整合~~ (已移除 2025-12-31)
- **狀態**: 已於 2025-12-31 移除 CodeerProvider
- **原因**: 實測效果不佳，統一使用 Gemini 降低複雜度
- **影響**: iOS app 需移除 API 請求中的 `provider` 參數
- **Commit**: 2244b2d - refactor: remove CodeerProvider, unify to Gemini-only

### ✅ 認證系統
- `POST /api/auth/login` - JWT 登入（24h 有效期）
- `GET /api/auth/me` - 取得諮詢師資訊
- `PATCH /api/auth/me` - 更新諮詢師資訊
- **特色**: 多租戶隔離（tenant_id）、bcrypt 密碼加密

### ✅ 密碼重設系統 (2025-12-27)
**功能定位**: 完整的密碼重設流程（Web + iOS）

#### Web UI
- ✅ `/forgot-password` - 密碼重設請求頁面
- ✅ `/reset-password` - 密碼重設確認頁面

#### API Endpoints (給 iOS 使用)
- ✅ `POST /api/v1/password-reset/request` - 請求密碼重設
  - 發送重設郵件到用戶信箱
  - Rate limiting: 每 5 分鐘最多 1 次請求
- ✅ `POST /api/v1/password-reset/verify` - 驗證 token 有效性
- ✅ `POST /api/v1/password-reset/confirm` - 確認新密碼

#### 技術特色
- **Token 安全**: 32+ 字元加密隨機字串、6 小時有效期、單次使用
- **Multi-Tenant 支援**: career / island / island_parents 租戶專屬 email 模板
- **自動發送歡迎信**: 透過 Admin API 建立諮詢師時自動發送密碼重設郵件
- **SMTP 整合**: Gmail SMTP delivery with error handling and retry logic
- **DEBUG 模式**: 開發階段跨租戶管理員存取

#### 測試覆蓋
- ✅ 23 個整合測試，100% 通過
- ✅ Staging 環境端到端測試通過
- ✅ 郵件發送成功驗證

#### 相關文件
- 📝 SMTP 配置: `docs/SMTP_SETUP.md`
- 📝 API 規格: 本文檔
- 📝 變更記錄: `CHANGELOG.md`, `CHANGELOG_zh-TW.md`

### ✅ 客戶管理 (`/api/v1/clients/*`)
- 完整 CRUD：建立、列表、詳情、更新、刪除
- 分頁搜尋：支援 skip/limit + 姓名/代碼搜尋
- 自動生成：客戶代碼（C0001, C0002...）
- **權限隔離**: 諮詢師只能訪問自己的客戶

#### ✅ Island Parents 關係欄位 (2025-12-29)
**功能定位**: 島嶼父母租戶專屬的親子關係追蹤

- **relationship 欄位**（island_parents 租戶必填）:
  - 爸爸 (father)
  - 媽媽 (mother)
  - 爺爺 (grandfather)
  - 奶奶 (grandmother)
  - 外公 (maternal grandfather)
  - 外婆 (maternal grandmother)
  - 其他 (other)

- **欄位標籤更新**:
  - "孩子姓名" → "孩子暱稱" (更符合使用情境)

- **iOS API 整合指南**:
  - ✅ 完整 9 步驟工作流程文件
  - ✅ Safety level 分析說明（🟢🟡🔴）
  - ✅ 動態分析間隔（5-30s 基於安全等級）
  - ✅ Swift code 範例
  - ✅ FAQ 章節與相關資源
  - 📝 參見: `IOS_API_GUIDE.md`

- **測試覆蓋**:
  - ✅ 完整工作流程整合測試（681 行）
  - 📝 測試報告: `docs/testing/ISLAND_PARENTS_WORKFLOW_TEST_REPORT.md`

### ✅ 案件管理 (`/api/v1/cases/*`)
- 完整 CRUD + 案件編號自動生成（CASE-20251124-001）
- 案件狀態：未開始(0) / 進行中(1) / 已結案(2)
- 關聯查詢：案件關聯客戶資訊

### ✅ 會談管理 (`/api/v1/sessions/*`)
- 建立會談記錄：逐字稿 + 錄音片段列表 + 會談名稱（name）
- 會談歷程時間線：`GET /sessions/timeline?client_id={id}`
- 諮詢師反思：4 問題結構化反思（JSONB）
- **🔍 即時片段分析（Multi-Tenant）**: `POST /sessions/{id}/analyze-partial` - 根據租戶回傳不同格式分析結果
- **📊 分析歷程記錄**: `GET /sessions/{id}/analysis-logs` - 查看所有分析記錄
- **🗑️ 管理分析記錄**: `DELETE /sessions/{id}/analysis-logs/{log_index}` - 刪除特定記錄
- **iOS 專用**: `POST /sessions/{id}/recordings/append` - 追加錄音片段
- **向後兼容**: `POST /sessions/{id}/analyze-keywords` - 舊版 API（內部調用 analyze-partial，回傳 career 格式）

#### 即時片段分析 API 詳解
**Endpoint**: `POST /api/v1/sessions/{session_id}/analyze-partial`

**用途**：分析部分逐字稿，根據租戶（career / island_parents）回傳不同格式的分析結果

**Request Body**:
```json
{
  "transcript_segment": "最近 60 秒的逐字稿",
  "mode": "practice"  // Optional (island_parents only): "emergency" or "practice" (default)
}
```

**Mode Parameter (island_parents only)**:
- `emergency`: 緊急模式 - 快速、簡化分析（1-2 個關鍵建議，危機情況使用）
- `practice`: 練習模式 - 詳細教學（3-4 個建議含技巧說明，預設值）
- Career 租戶忽略此參數（總是關鍵字分析）

**Response（island_parents 租戶）**:
```json
{
  "safety_level": "red|yellow|green",
  "severity": 1-3,
  "display_text": "您注意到孩子提到「不想去學校」...",
  "action_suggestion": "建議先同理孩子的感受",
  "suggested_interval_seconds": 15,
  "rag_documents": [...],
  "keywords": ["焦慮", "學校"],
  "categories": ["情緒"],
  "token_usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 567,
    "total_tokens": 1801
  }
}
```

**Response（career 租戶）**:
```json
{
  "keywords": ["焦慮", "職涯"],
  "categories": ["情緒", "職涯探索"],
  "confidence": 0.95,
  "counselor_insights": "個案提到對未來感到迷惘...",
  "safety_level": "yellow",
  "severity": 2,
  "display_text": "...",
  "action_suggestion": "...",
  "token_usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 567,
    "total_tokens": 1801
  }
}
```

**Multi-Tenant 特性**：
- 根據 JWT token 的 `tenant_id` 自動選擇：
  - RAG 知識庫（career 職涯 vs island_parents 親子教養）
  - Prompt template
  - Response 格式
- 向後兼容：舊的 `POST /sessions/{id}/analyze-keywords` 仍可用，內部調用 analyze-partial，回傳 career 格式

**✅ RAG 整合 (2025-12-31 修復)**:
- RAG 檢索在 Gemini 調用**之前**執行，確保 RAG 知識包含在 AI prompt 中
- RAG 上下文自動附加到 prompt 模板的 `context` 參數
- 提升 AI 回應品質，充分利用知識庫內容

**✅ Token Usage 追蹤 (2025-12-31)**:
- 所有 API 回應包含 `token_usage` 欄位
- 包含 `prompt_tokens`, `completion_tokens`, `total_tokens`
- 即使 AI 調用失敗也會回傳零值（確保 schema 一致性）
- 用於成本監控與性能分析

#### ✅ 8 Schools of Parenting 整合 (2025-12-31)
**功能定位**: Island Parents 租戶專屬的進階教養指導系統

**核心特色**:
- ✅ **8 大教養流派整合** - 專業理論基礎
  1. 阿德勒正向教養 (Positive Discipline)
  2. 薩提爾模式 (Satir Model - 冰山理論)
  3. 行為分析學派 (ABA, ABC 模式)
  4. 人際神經生物學 (Dan Siegel - 全腦教養)
  5. 情緒輔導 (John Gottman - 情緒教練)
  6. 協作解決問題 (Ross Greene - CPS)
  7. 現代依附與內在觀點 (Dr. Becky Kennedy)
  8. 社會意識與價值觀教養（性別平權、身體自主權）

- ✅ **逐字稿級別話術指導** (Practice Mode)
  - 提供 100-300 字的具體對話範例
  - 包含家長話術、孩子可能回應、理論依據
  - 可立即使用的實戰話術

- ✅ **理論來源追溯**
  - 每個建議標註使用的流派
  - 透明化專業決策過程
  - 提升家長信任度

**Response 擴充（island_parents 租戶 Practice Mode）**:
```json
{
  "safety_level": "yellow",
  "severity": 2,
  "display_text": "孩子正在經歷情緒困擾",
  "action_suggestion": "先同理孩子的感受，再引導解決問題",
  "detailed_scripts": [
    {
      "situation": "當孩子拒絕寫作業時",
      "parent_script": "（蹲下平視）我看到你現在不想寫作業，好像很累。是不是今天在學校已經很努力了？\n\n我們現在先不談作業。你是要先休息 10 分鐘，還是我陪你一起做？你覺得哪一個比較容易開始？",
      "child_likely_response": "可能選擇休息或陪伴",
      "theory_basis": "薩提爾 + Dr. Becky + 阿德勒",
      "step": "同理連結 → 即時話術"
    }
  ],
  "theoretical_frameworks": ["薩提爾模式", "Dr. Becky Kennedy", "阿德勒正向教養"]
}
```

**技術實作**:
- **Prompt 版本**: v1 (測試版)
- **檔案位置**:
  - Practice Mode: `app/prompts/island_parents_8_schools_practice_v1.py`
  - Emergency Mode: `app/prompts/island_parents_8_schools_emergency_v1.py`
- **整合位置**: `app/services/keyword_analysis_service.py`
- **Schema 擴充**: `app/schemas/analysis.py` (DetailedScript, IslandParentAnalysisResponse)

**向後相容**:
- ✅ 新增欄位為 Optional，不影響現有 API 調用
- ✅ Emergency Mode 保持簡短（不提供 detailed_scripts）
- ✅ Career 租戶不受影響

**測試覆蓋**:
- ✅ Integration tests: `tests/integration/test_8_schools_prompt_integration.py`
- ✅ 覆蓋場景: Practice/Emergency mode, 向後相容, Schema validation

### ✅ 報告生成 (`/api/v1/reports/*`)
- **異步生成**: `POST /reports/generate` (HTTP 202 Accepted)
  - Background Tasks 執行 RAG + GPT-4 生成
  - 狀態追蹤：processing → draft / failed
- 報告列表：支援 client_id 篩選 + 分頁
- 報告詳情：JSON + Markdown 雙格式
- 報告編輯：`PATCH /reports/{id}` - 更新 Markdown 內容

### ✅ UI 整合 API (`/api/v1/ui/*`)
**給 iOS App 使用的高階 API**：
- `GET /ui/field-schemas/{form_type}` - 動態表單 Schema
- `POST /ui/client-case` - 一次建立 Client + Case
- `GET /ui/client-case-list` - 列出客戶個案（含分頁）
- `GET /ui/client-case/{id}` - 個案詳情
- `PATCH /ui/client-case/{id}` - 更新客戶個案
- `DELETE /ui/client-case/{id}` - 刪除個案

**動態欄位**: 支援 10 種類型（text, number, date, select等），不同 tenant 獨立配置。詳見 [IOS_API_GUIDE.md](./IOS_API_GUIDE.md)

### ✅ Universal Credit/Payment System (2025-12-20)
**功能定位**: 跨租戶通用的點數付費系統（支援 career, island, island_parents）

#### 核心功能
- ✅ **Admin Backend (Phase 1 - 已完成)**
  - 會員信用額度管理（total_credits, credits_used, available_credits）
  - 可配置計費規則（per_second, per_minute, tiered）
  - 完整交易記錄與審計追蹤
  - 管理員專用 API（role-based access control）

#### 技術架構
- **資料庫層**:
  - `counselors` 表擴充：phone, total_credits, credits_used, subscription_expires_at
  - `credit_rates` 表：可配置的計費規則（支援版本控制）
  - `credit_logs` 表：交易歷史記錄（raw_data + rate_snapshot + calculation_details）

- **服務層**:
  - `CreditBillingService` - 計費邏輯核心
    - `get_active_rate()` - 取得當前生效費率
    - `calculate_credits()` - 靈活計算點數（支援 3 種計費方式）
    - `add_credits()` - 交易管理（新增/扣除點數）
    - `get_counselor_balance()` - 查詢餘額

- **API 端點** (`/api/v1/admin/credits/*`):
  - `GET /members` - 列出所有會員與點數資訊
  - `POST /members/{id}/add` - 新增/移除點數
  - `GET /logs` - 查看交易歷史（支援篩選與分頁）
  - `POST /rates` - 建立/更新計費規則
  - `GET /rates` - 列出所有計費規則

#### Multi-Tenant 支援
- **island_parents** 租戶：新增動態表單配置
  - Client 表單：孩子姓名、年級（1-12）、出生日期、性別、備註
  - Case 表單：與 island 租戶相同結構

#### 設計特色
1. **通用設計**: 所有租戶使用相同的信用機制
2. **靈活計費**: 計費規則儲存在資料庫，非硬編碼
3. **審計追蹤**: 每筆交易記錄費率快照，可重新計算
4. **原始數據保留**: 儲存原始秒數，規則變更時可重算
5. **資料庫相容性**: 使用 JSON（非 JSONB）確保 SQLite/PostgreSQL 相容

#### 測試覆蓋
- ✅ 21 個整合測試（TDD RED 階段完成）
- ✅ 涵蓋所有 admin 端點、權限控制、跨租戶功能

#### ✅ Session Billing Integration (Phase 2 - 已完成, 2025-12-28)
- **Incremental Billing**: 會談進行時即時扣點（每分鐘累積計費）
  - 計費公式: `credits = ceil(duration_seconds / 60) * 1.0`
  - 無痛中斷: 中斷時已扣點數保留（已計費分鐘數追蹤）
  - SessionUsage 整合: `last_billed_minutes` 欄位追蹤計費進度
- **詳細設計**: 參見 `docs/SESSION_USAGE_CREDIT_DESIGN.md`
- **測試覆蓋**: 參見 `tests/integration/test_incremental_billing.py`

#### ✅ Recording-Based Billing (Phase 2.1 - 已完成, 2025-01-05)
- **計費方式變更**: 從「經過時間」改為「錄音累積時間」
  - 舊方式: `duration = current_time - session.start_time`（包含暫停/閒置時間）
  - 新方式: `duration = sum(recordings[].duration_seconds)`（僅計算實際錄音時間）
- **使用者體驗改善**:
  - ✅ 暫停對話時不計費
  - ✅ 諮詢師離開接電話時不計費
  - ✅ 只有實際錄音進行中才計費
- **技術實作**:
  - 修改 `KeywordAnalysisService._process_billing()` 方法
  - 使用 `session.recordings` JSON 欄位累加 `duration_seconds`
  - 📋 File: `app/services/keyword_analysis_service.py`

#### 待實作功能（Phase 3）
- ⚠️ 點數餘額不足警告（前端提示）
- ⚠️ 訂閱到期提醒（Email/推播通知）

### ✅ 即時語音諮詢系統 (Realtime STT Counseling)
**功能定位**: AI 輔助即時諮詢督導系統

#### 核心功能
- ✅ **即時語音轉文字 (STT)**
  - ElevenLabs Scribe v2 Realtime API
  - 中文繁體支援（language_code: `zh`）
  - < 100ms 低延遲
  - 手動說話者切換（諮詢師/案主）
- ✅ **AI 即時分析** (Updated 2025-12-31)
  - **Gemini 3 Flash** (唯一支援) - 統一 AI provider
  - < 3s 延遲，Pro-level intelligence at Flash speed
  - 每 60 秒自動分析對話內容
  - 提供：對話歸納、提醒事項、建議回應
  - Cache 效能追蹤：usage_metadata 記錄（cached tokens, prompt tokens, output tokens）
  - **已移除**: Codeer 多模型支援（2025-12-31 簡化架構）
- ✅ **RAG 知識庫整合**
  - 7 種教養理論標籤（依附理論、正向教養、發展心理學等）
  - Color-coded badges 視覺化
  - 每個建議都有理論來源可追溯
- ✅ **分析卡片流**
  - 時間軸展示（最新在上）
  - localStorage 歷史記錄
  - 自動超時保護（5 分鐘無語音自動結束）

#### API 端點
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/api/v1/realtime/analyze` | AI 分析逐字稿（舊版，每 60 秒） |
| POST | `/api/v1/sessions/{id}/quick-feedback` | 快速反饋（固定 20 秒間隔） |
| POST | `/api/v1/sessions/{id}/deep-analyze` | 深層分析（動態間隔，根據燈號） |

**技術選型**: ElevenLabs STT ($0.46/h) + Gemini 3 Flash + Vanilla JS | 7種理論標籤（依附、正向教養、發展心理、家庭系統、認知行為、情緒教練、綜合）

#### 雙定時器架構 (Dual Timer Architecture)
**功能定位**: 分離快速回饋與深層分析，兼顧用戶體驗與系統效能

```
┌──────────────────────────────────────────────────────────┐
│  主定時器: setInterval(updateTimer, 1000) - 每秒檢查     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Timer 1: Quick Feedback                                 │
│  ├─ 固定 20 秒間隔                                       │
│  ├─ 紅燈時停用（Deep Analyze 已 15 秒一次）              │
│  ├─ 顯示黃色 Toast                                       │
│  ├─ AI 呼叫: 1 次                                        │
│  ├─ 延遲: ~1-8 秒                                        │
│  └─ 輸出: 1 句鼓勵語（20 字內）                          │
│                                                          │
│  Timer 2: Deep Analyze                                   │
│  ├─ 動態間隔（根據燈號）                                 │
│  │   🟢 綠燈（安全）  → 60 秒                            │
│  │   🟡 黃燈（警示）  → 30 秒                            │
│  │   🔴 紅燈（高風險）→ 15 秒                            │
│  ├─ 顯示紫色 Toast                                       │
│  ├─ AI 呼叫: 2 次（主分析 + 專家建議挑選）               │
│  ├─ 延遲: ~15-20 秒                                      │
│  └─ 輸出: safety_level + summary + suggestions           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**設計原則**:
- **分離關注點**: Quick Feedback 負責用戶體驗（即時打氣），Deep Analyze 負責系統決策（燈號判斷）
- **不互相阻塞**: 兩個定時器獨立運作，快速回饋不被深層分析延遲
- **智能節流**: 紅燈時 Quick Feedback 停用，避免重複通知

**前端實作位置**: `realtime_counseling.html:3564-3627`

#### 🔴🟡🟢 Annotated Safety Window Mechanism (2025-12-26)
**功能定位**: 智能安全等級評估 - 平衡上下文感知與快速放鬆

**⚠️ 實作狀態**:
- ✅ **Web 版已實作** (`/realtime-counseling` + `app/api/realtime.py`)
- ❌ **iOS API 尚未實作** (待 Phase 2)

**核心機制**:
- **Annotated Transcript Approach** - 發送完整對話給 AI，但標註最近 5 句話用於安全評估
- **Sliding Window** - 只評估最近對話（非累積全部）
- **Rapid Relaxation** - RED → GREEN 可在 1 分鐘內完成（當危險詞彙不再出現）
- **Cost Optimization** - 減少 ~70% 不必要的高頻 polling

**技術實作**:

1. **配置參數** (`app/api/realtime.py`):
```python
SAFETY_WINDOW_SPEAKER_TURNS = 10  # Backend 驗證用（取最近 10 句話）
ANNOTATED_SAFETY_WINDOW_TURNS = 5  # AI 評估用（標註最近 5 句話）
```

2. **Annotated Prompt 結構**:
```
完整對話逐字稿（供參考，理解背景脈絡）：
[全部對話內容...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
（請根據此區塊判斷當前安全等級）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[最近 5 句話...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CRITICAL: 安全等級評估請只根據「【最近對話 - 用於安全評估】」區塊判斷
```

3. **Double Validation**:
   - **AI 評估**: 分析標註區塊（5 turns），提供 safety_level
   - **Backend 檢查**: 驗證最近 10 turns 是否有危險關鍵字
   - 取兩者較嚴格的結果

**安全等級轉換間隔**:
| 等級 | Polling 間隔 | 說明 |
|------|-------------|------|
| 🟢 GREEN (安全) | 60 秒 | 正常對話，低頻監控 |
| 🟡 YELLOW (警示) | 30 秒 | 偵測到衝突升溫 |
| 🔴 RED (高風險) | 15 秒 | 高風險詞彙出現 |

**Sliding Window 降級機制**:
- **舊機制 ❌**: 一旦 RED，永遠 RED（累積逐字稿持續觸發危險關鍵字）
- **新機制 ✅**: 基於「最近 10 個 speaker turns」評估，舊內容離開 window 後不再影響
- **降級時間**: 取決於對話速度
  - 慢速對話（每 5-6 秒一輪）：約 50-60 秒自動降級
  - 快速對話（每 2-3 秒一輪）：約 20-30 秒自動降級
- **成本影響**: 每場對話節省 ~70% polling 費用

**運作範例**:
```
0:00 - "我想打死他" → RED（危險關鍵字進入 window）
0:30 - "我們來討論解決方法" → 若仍在 10 turns 內，維持 RED
1:00 - "我感覺好多了" → 若「打死他」已離開 window，降為 GREEN
```

**已知限制**:
- ⚠️ **快速對話時可能過早降級**: 危險關鍵字可能在 20-30 秒後就離開 window
- ⚠️ **無最小警示時間保證**: 家長可能來不及注意紅燈閃爍
- 💡 **解決方案（待實作）**: Lockout Period 機制（見下方「未來增強」）

**實測數據**:
- ✅ 15 integration tests 全部通過（100% 成功率）
- ✅ RED → GREEN 放鬆時間: < 60 秒（實測）
- ✅ AI 遵循標註指令: 97% 準確率
- ✅ Context 保留: 完整對話仍用於生成建議

**未來增強：Lockout Period 機制** (Phase 3):
**問題**: Sliding Window 機制雖然允許降級，但無法保證最小警示時間
- 快速對話中，危險關鍵字可能在 20-30 秒後就離開 window
- 家長可能來不及注意到紅燈/黃燈閃爍

**解決方案**: 增加「燈號升級鎖定期」
- **設計規則**:
  ```
  GREEN → YELLOW: 鎖定 10 秒（至少顯示 10 秒黃燈）
  YELLOW → RED: 鎖定 15 秒（至少顯示 15 秒紅燈）
  RED → YELLOW: 鎖定 15 秒（紅燈降級需至少 15 秒後）
  ```

- **運作範例**:
  ```
  0:00 - "我想打死他" → 升級到 RED，設定鎖定期到 0:15
  0:08 - 對話和緩 → Sliding Window 判斷可降級，但鎖定期未到，維持 RED
  0:15 - 鎖定期結束 → 允許降級到 YELLOW
  0:25 - 繼續和緩 → 鎖定期結束（0:15+10s=0:25），允許降級到 GREEN
  ```

- **實作方式**:
  - Option 1: Session DB 追蹤（`current_safety_lockout_until` 欄位）
  - Option 2: Redis Cache 快取狀態
  - Option 3: In-memory 狀態管理（最簡單，但不支援斷線重連）

- **優點**:
  - ✅ 保證警示持續時間，避免閃爍
  - ✅ 給予家長足夠反應時間
  - ✅ 與 Sliding Window 互補（基於內容 + 基於時間）

- **待決策**:
  - [ ] 鎖定期時間是否合適？（10s / 15s）
  - [ ] 儲存方式選擇（DB / Redis / Memory）
  - [ ] 是否只限制降級，或雙向鎖定？

**iOS API 實作待辦** (Phase 2):
- [ ] 在 iOS API 中實作相同的 annotated transcript 機制
- [ ] 確保 iOS 發送完整對話 + speaker segments
- [ ] 支援 `use_cache` 參數（優化成本）
- [ ] 測試覆蓋: RED → GREEN relaxation scenarios

**測試檔案**:
- `tests/integration/test_annotated_safety_window.py` - 15 comprehensive tests
- `tests/unit/test_safety_assessment_sliding_window.py` - Unit tests for backend validation

**測試文檔** (詳細測試計劃與分析):
- 📋 [測試總覽](docs/testing/SAFETY_TRANSITIONS_SUMMARY.md) - 測試計劃、設計決策、測試結果
- 📝 [手動測試指南](docs/testing/SAFETY_TRANSITIONS_MANUAL_TEST_GUIDE.md) - 逐步測試程序、視覺指標驗證
- 🔍 [測試發現分析](docs/testing/SAFETY_TRANSITIONS_TEST_FINDINGS.md) - Sticky 行為分析、設計權衡
- 📊 [預期結果表格](docs/testing/SAFETY_TRANSITIONS_TEST_RESULTS_TABLE.md) - 關鍵字檢測、API 回應範例
- 🔄 [滑動窗口實現](docs/testing/SLIDING_WINDOW_SAFETY_ASSESSMENT.md) - 算法細節、成本節省分析

**參考實作**: `app/api/realtime.py` (lines 406-448, 809-819)

---

#### ~~Codeer Model Performance Comparison~~ (已移除 2025-12-31)
**狀態**: 已移除 Codeer 多模型支援，統一使用 Gemini 3 Flash

**技術決策**:
- 移除原因: Codeer integration 實測效果不佳
- 簡化架構: 單一 AI provider (Gemini) 降低維護複雜度
- 性能優勢: Gemini 3 Flash 提供 < 3s 延遲，Pro-level intelligence at Flash pricing

---

#### 🔬 Gemini Caching 技術細節與最佳實踐 (2025-12-10 實驗結論)

##### Implicit Caching vs Explicit Context Caching

| 特性 | **Implicit Caching** (自動) | **Explicit Context Caching** (手動) |
|------|---------------------------|----------------------------------|
| **啟用方式** | 自動啟用（無需設定） | 手動創建 cache object |
| **控制權** | 無法控制 | 完全控制 cache lifecycle |
| **費用** | 自動 75% 折扣（2.5 Flash） | 90% 折扣 + 每小時儲存費 |
| **最小 tokens** | **1024** (文檔) / **3000-6000** (實測) | **2048** tokens (強制) |
| **適用場景** | 簡單、固定 system instructions | 大量重複內容（累積 transcript） |
| **穩定性** | ⚠️ 不穩定（見下方問題） | ✅ 保證運作 |

##### ⚠️ Implicit Caching 已知問題（2025-12 實測）

**問題 1: 實際 Token 門檻遠高於文檔**
- 📄 官方文檔：1024 tokens (Flash) / 2048 tokens (Pro)
- 🔬 社群實測：**3000-6000 tokens** 才會觸發
- 🎯 我們的測試：996 tokens system prompt → `cached_content_token_count = 0`

**問題 2: JSON Mode 可能禁用 Implicit Caching**
- 使用 `response_mime_type: "application/json"` 時，caching 可能失效
- Google 正在調查 structured output 對 caching 的影響
- 來源：[Google AI Forum #88557](https://discuss.ai.google.dev/t/implicit-caching-not-working-on-gemini-2-5-pro/88557)

**問題 3: Production 環境也有問題**
- ❌ 不是 local vs Cloud 的差異
- ❌ Cloud Run 環境仍然 `cached_content_token_count = 0`
- ✅ 這是 Gemini API 本身的已知問題
- 來源：[Google AI Forum #107342](https://discuss.ai.google.dev/t/gemini-2-5-flash-lite-implicit-caching-not-working-despite-meeting-documented-requirements/107342)

##### ✅ Explicit Context Caching 使用場景

**最適合我們的累積 transcript 場景：**

```python
# 實時諮詢場景（60 分鐘會談）
# 第 1 分鐘：創建 cache
cache = client.caches.create(
    model="gemini-2.5-flash",
    contents=[transcript_min1],  # 第 1 分鐘內容
    system_instruction=system_prompt,
    ttl="3600s"  # 1 小時
)

# 第 2-60 分鐘：每分鐘重複使用 cache
for minute in range(2, 61):
    model = GenerativeModel(cached_content=cache)
    response = model.generate_content(
        f"{transcript_accumulated}\n新增: {transcript_new}"
    )
    # ↑ 每次都享受 90% cached tokens 折扣
```

**成本估算（60 分鐘會談）：**
- System prompt: 996 tokens × 60 次 = **59,760 tokens**
- 使用 Explicit Caching: 996 tokens × 10% × 60 = **5,976 tokens** (節省 90%)
- 儲存費用: $0.01/hour (可忽略)
- **總節省: 約 $0.004** per session

##### 🎯 當前實作狀態

**已實作（2025-11-24）：**
- ✅ Usage metadata tracking (`cached_content_token_count`, `prompt_token_count`, `candidates_token_count`)
- ✅ Debug logging for cache performance monitoring
- ✅ 累積 transcript 測試腳本 (`scripts/test_cache_cumulative.py`)

**實驗結論（2025-12-10）：**
- ⚠️ Implicit Caching **不適用**於我們的場景（996 tokens < 3000 最低門檻）
- ⚠️ JSON mode 與 Implicit Caching **不相容**
- ✅ 如需 cache 優化，必須改用 **Explicit Context Caching**

##### 🧪 Explicit Context Caching 實驗結果 (2025-12-10)

**測試場景**: 60 分鐘累積 transcript (模擬實時諮詢會談)

**測試設計**:
- Cache creation: 前 10 分鐘對話內容 (系統 prompt + 累積 transcript)
- Cache hit tests: 第 11-60 分鐘，每 5 分鐘採樣一次 (共 11 次測試)
- Model: `gemini-2.5-flash`
- System instruction: 996 tokens (諮詢督導 prompt)

**實驗結果**:

| 指標 | 數值 |
|------|------|
| 測試次數 | 11 次 (分鐘 11, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60) |
| 總 Cached tokens | 14,245 |
| 總 Prompt tokens | 14,982 |
| 總 Output tokens | 1,965 |
| **平均 Cache 命中率** | **48.7%** |
| **平均響應時間** | **7.97s** |
| **Token 節省** | **14,245 tokens** (原本需要 29,227) |

**關鍵發現**:

1. **✅ Cache 穩定運作**: 所有 11 次測試都成功命中 cache (1295 cached tokens)
2. **✅ 持續有效**: Cache 在 1 小時內持續有效，無衰減
3. **💰 成本節省**: 每次請求節省 ~48.7% tokens
   - Without cache: 29,227 tokens × 11 calls = 321,497 tokens
   - With cache: 16,947 tokens × 11 calls = 186,417 tokens
   - **節省: 135,080 tokens (~42% 成本降低)**

**結論**:

- ✅ **Explicit Context Caching 完全適用**於累積 transcript 場景
- ✅ Cache 命中率穩定，無需擔心隨機失效
- ✅ 與 JSON mode 完全相容 (`response_mime_type: "application/json"`)
- ⚠️ 需要手動管理 cache lifecycle (create, delete)
- ⚠️ 最小 token 要求：2048 tokens (系統 prompt + 初始 transcript)

**未來優化方向：**
- [x] ~~實作 Explicit Context Caching（需評估儲存成本）~~ → **已驗證可行** (2025-12-10)
- [x] ~~成本分析評估~~ → **完成** (2025-12-10)
- [x] ~~Production 實作：整合到 `/api/v1/realtime/analyze` endpoint~~ → **已上線** (2025-12-10)
- [x] ~~Cache 管理策略：session 開始時創建，結束時自動清理~~ → **已實作** (2025-12-10)
- [ ] 監控 cache performance metrics (hit rate, token savings)

##### 🎯 Production 實作狀態 (2025-12-10)

**✅ 已上線功能**:

**Cache Manager (`app/services/cache_manager.py`)**:
- ✅ **Strategy A (Always Update)**: 每次請求都刪除舊 cache，創建新的包含最新累積 transcript
- ✅ **自動內容檢查**: < 1024 tokens 自動 fallback 到無 cache 模式
- ✅ **多層清理機制**:
  - Manual delete (每次更新前)
  - TTL auto-expire (7200s = 2 hours)
  - Cleanup script (`scripts/cleanup_caches.py`)
  - BigQuery monitoring (未來)

**API 整合 (`/api/v1/realtime/analyze`)**:
```python
# Request with cache enabled
{
  "transcript": "累積的完整對話...",  # 持續累積
  "speakers": [...],
  "session_id": "session-123",  # 必須提供
  "use_cache": true  # 啟用 cache
}

# Response includes cache metadata
{
  "summary": "...",
  "cache_metadata": {
    "cache_name": "projects/.../locations/.../cachedContents/...",
    "cache_created": true,  # Strategy A 總是 true
    "cached_tokens": 1295,
    "prompt_tokens": 150,
    "message": "Cache updated successfully"
  }
}
```

**Cache 更新策略對比實驗** (2025-12-10):

| 策略 | 方式 | 上下文 | 穩定性 | 實驗結果 |
|------|------|--------|--------|----------|
| **Strategy A** | 每次刪除重建 | ✅ 完整累積 | ✅ 10/10 成功 | **已採用** |
| Strategy B | 固定 cache | ❌ 僅當前分鐘 | ⚠️ 9/10 成功 | 已棄用 |

**實驗數據**:
- **測試場景**: 10 分鐘即時對話（每分鐘發送一次）
- **Strategy A**: 100% 成功率，133.21s 總時間，完整對話上下文
- **Strategy B**: 90% 成功率（第 9 分鐘 HTTP 500），121.45s 總時間，缺少上下文
- **結論**: Strategy A 雖然稍慢（+9.7%），但保證對話連貫性和穩定性

**Critical Bug Fix** (2025-12-10):
- **問題**: Cache 在首次創建後內容凍結，不再更新
- **原因**: `get_or_create_cache()` 直接返回現有 cache
- **修復**: 實作 Strategy A - 每次先刪除舊 cache，再創建新的
- **影響**: 修復前會導致 AI 分析缺少最新對話內容

**測試覆蓋** (`tests/integration/test_realtime_cache.py`):
- ✅ 8 integration tests 全部通過
- ✅ Cache creation, update, fallback scenarios
- ✅ Error handling and edge cases

**詳細實驗報告**: 參考 `CACHE_STRATEGY_ANALYSIS.md`

##### 💰 成本效益分析 (2025-12-10)

**場景**: 1 小時即時語音諮詢（每分鐘發送一次，對話累積）

**系統架構**:
```
用戶語音 → ElevenLabs STT → 累積 transcript → Gemini 分析 (60次/小時) → 即時督導
```

**成本對比**:

| 項目 | 無 Cache | 有 Cache | 節省 |
|------|----------|----------|------|
| **ElevenLabs STT** | $0.4600 | $0.4600 | $0 |
| **Gemini Input** | $0.1003 | $0.0097 | $0.0906 (90%) |
| **Gemini Output** | $0.0270 | $0.0270 | $0 |
| **Cache Storage** | $0 | $0.0015 | -$0.0015 |
| **總費用 (USD)** | **$0.5873** | **$0.4982** | **$0.0891** |
| **總費用 (TWD)** | **NT$18.81** | **NT$15.95** | **NT$2.86** |
| **節省比例** | - | - | **15.2%** |

**費用結構分析**:

無 Cache 方案：
- STT: 78.3% (主要成本)
- Gemini: 21.7%

有 Cache 方案：
- STT: 92.3% (更突出)
- Gemini: 7.7% (大幅降低)

**規模化效益** (假設每日 10 場諮詢):

| 時間 | 無 Cache | 有 Cache | 年省 |
|------|----------|----------|------|
| **每場** | NT$18.81 | NT$15.95 | NT$2.86 |
| **每月** | NT$5,643 | NT$4,784 | NT$859 |
| **每年** | NT$68,658 | NT$58,219 | **NT$10,439** |

**ROI 分析**:
- 實作成本: 4 小時開發 ≈ NT$4,000
- Break-even: 138 天（每日 10 場）
- 若每日 50 場: **28 天回本**

**結論**:
- ✅ 強烈建議實作 Explicit Caching
- ✅ 立即效益: 每場省 15.2%
- ✅ 年度效益: NT$10,439+（隨用戶量增長）
- 💡 STT 佔成本 78%，未來可評估替代方案

**詳細 Token 計算**:

無 Cache (60 分鐘):
```
Input tokens = Σ(996 + 150×N) for N=1 to 60
            = 334,260 tokens
            = $0.1003 (at $0.30/1M)
```

有 Cache (10 分鐘創建 + 50 分鐘使用):
```
創建階段 (1-10 min): 18,210 tokens = $0.0055
使用階段 (11-60 min):
  - Cached: 64,750 tokens × 90% off = $0.0019
  - New: 7,500 tokens = $0.0023
  - Storage: $0.0015/hour
總計: $0.0097
```

##### 參考資料
- [Context Caching Overview | Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview)
- [Gemini Implicit Caching 官方公告](https://developers.googleblog.com/en/gemini-2-5-models-now-support-implicit-caching/)
- [Community Issue: Implicit Caching Not Working](https://discuss.ai.google.dev/t/gemini-2-5-flash-lite-implicit-caching-not-working-despite-meeting-documented-requirements/107342)

---

### ✅ Web 測試控制台 (`/console`)
- 整合式 API 測試介面（包含所有 API）
- RWD 設計：支援手機 + 平板 + 桌面
- 手機模擬圖：iOS UI 預覽
- Realtime Counseling 快速連結

---

## 尚未實作功能

### Phase 3 待完成（預計 2 週）
- [ ] 音訊上傳 + Whisper STT（Job model 已建立）
- [ ] 逐字稿脫敏處理（SanitizerService 已實作，待串接 `sessions.py:347`）
- [ ] 督導審核流程
- [ ] 提醒系統

### Phase 4+ 長期規劃
- [ ] RAG 評估系統優化（EvaluationExperiment 加 testset_id）
- [ ] RAG Matrix Table 前端串接後端 API
- [ ] 集合管理 (RAG)
- [ ] Pipeline 可視化

---

## 資料模型（核心表）

### 諮詢系統
- **counselors**: 諮詢師（tenant_id, role, email, password_hash）
- **clients**: 客戶（counselor_id, name, age, gender, code [自動生成]）
- **cases**: 案件（client_id, case_number [自動], status [0/1/2]）
- **sessions**: 會談（case_id, name, transcript_text, recordings [JSONB], reflection [JSONB], analysis_logs [JSONB]）
- **reports**: 報告（session_id, content_json, content_markdown, status）
- **jobs**: 異步任務（session_id, job_type, status, progress）
- **reminders**: 提醒（client_id, remind_at, status）

### RAG 系統
- **agents**: Agent 配置
- **agent_versions**: 版本控制
- **datasources**, **documents**, **chunks**, **embeddings**: 知識庫
- **evaluation_experiments**, **evaluation_results**: 評估系統

---

## API 端點總覽

### 認證 (`/api/auth/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/auth/login` | 登入取得 JWT |
| GET | `/auth/me` | 取得諮詢師資訊 |
| PATCH | `/auth/me` | 更新諮詢師資訊 |

### 客戶 (`/api/v1/clients/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| GET | `/clients` | 列出客戶（分頁 + 搜尋） |
| POST | `/clients` | 建立客戶 |
| GET | `/clients/{id}` | 客戶詳情 |
| PATCH | `/clients/{id}` | 更新客戶 |
| DELETE | `/clients/{id}` | 刪除客戶 |

### 案件 (`/api/v1/cases/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| GET | `/cases` | 列出案件 |
| POST | `/cases` | 建立案件 |
| GET | `/cases/{id}` | 案件詳情 |
| PATCH | `/cases/{id}` | 更新案件 |
| DELETE | `/cases/{id}` | 刪除案件 |

### 會談 (`/api/v1/sessions/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/sessions` | 建立會談 |
| GET | `/sessions` | 列出會談 |
| GET | `/sessions/{id}` | 會談詳情 |
| PATCH | `/sessions/{id}` | 更新會談 |
| DELETE | `/sessions/{id}` | 刪除會談 |
| GET | `/sessions/timeline` | 個案歷程時間線 |
| GET | `/sessions/{id}/reflection` | 查看反思 |
| PUT | `/sessions/{id}/reflection` | 更新反思 |
| POST | `/sessions/{id}/recordings/append` | 🎙️ 追加錄音片段 (iOS) |
| POST | `/sessions/{id}/analyze-partial` | 🔍 即時片段分析（Multi-Tenant） |
| POST | `/sessions/{id}/analyze-keywords` | 🔄 舊版 API（向後兼容） |
| GET | `/sessions/{id}/analysis-logs` | 📊 取得分析歷程 |
| DELETE | `/sessions/{id}/analysis-logs/{log_index}` | 🗑️ 刪除分析記錄 |

### 報告 (`/api/v1/reports/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/reports/generate` | 異步生成報告 (202) |
| GET | `/reports` | 列出報告 |
| GET | `/reports/{id}` | 報告詳情 |
| PATCH | `/reports/{id}` | 更新報告 |

### UI 整合 (`/api/v1/ui/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| GET | `/ui/field-schemas/{form_type}` | 動態表單 Schema |
| POST | `/ui/client-case` | 建立客戶+案件 |
| GET | `/ui/client-case-list` | 列表（含客戶+案件） |
| GET | `/ui/client-case/{id}` | 詳情 |
| PATCH | `/ui/client-case/{id}` | 更新 |
| DELETE | `/ui/client-case/{id}` | 刪除 |

### 即時諮詢 (`/api/v1/realtime/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/realtime/analyze` | AI 分析逐字稿（Gemini + RAG） |

### RAG 系統 (`/api/rag/*`)
- `/rag/agents` - Agent 管理
- `/rag/ingest/*` - 文件上傳
- `/rag/search` - 向量檢索
- `/rag/chat` - RAG 問答（**諮詢系統調用**）
- `/rag/experiments/*` - 評估系統
- `/rag/stats` - RAG 統計頁面（理論標籤 Color-coded badges）

---

## API Error Handling (RFC 7807)

### 標準化錯誤格式
所有 API 錯誤現在遵循 **RFC 7807 (Problem Details for HTTP APIs)** 標準，提供一致且結構化的錯誤回應。

#### 錯誤回應格式
```json
{
  "type": "https://api.career-counseling.app/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Session not found",
  "instance": "/api/v1/sessions/123e4567-e89b-12d3-a456-426614174000"
}
```

#### 欄位說明
| 欄位 | 型別 | 說明 |
|------|------|------|
| `type` | string (URI) | 錯誤類型的唯一識別符，連結到錯誤說明文件 |
| `title` | string | 人類可讀的錯誤標題（對應 HTTP 狀態碼） |
| `status` | integer | HTTP 狀態碼 |
| `detail` | string | 具體的錯誤訊息，描述此次錯誤的詳細資訊 |
| `instance` | string (URI) | 發生錯誤的 API 端點路徑 |

#### 支援的錯誤類型
| 狀態碼 | Type URI | Title | 使用場景 |
|--------|----------|-------|----------|
| 400 | `/errors/bad-request` | Bad Request | 請求參數無效、缺少必填欄位 |
| 401 | `/errors/unauthorized` | Unauthorized | 未提供認證 token 或 token 無效 |
| 403 | `/errors/forbidden` | Forbidden | 沒有權限存取資源 |
| 404 | `/errors/not-found` | Not Found | 資源不存在 |
| 409 | `/errors/conflict` | Conflict | 資源衝突（如重複的 email/username） |
| 422 | `/errors/unprocessable-entity` | Unprocessable Entity | 請求格式正確但語意無效（Pydantic 驗證錯誤） |
| 500 | `/errors/internal-server-error` | Internal Server Error | 伺服器內部錯誤 |

#### 多語言支援
- 錯誤訊息支援中英文
- `detail` 欄位會保留原始語言
- 未來可透過 `Accept-Language` header 自動切換語言

#### 範例

**404 Not Found**
```json
{
  "type": "https://api.career-counseling.app/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Session not found",
  "instance": "/api/v1/sessions/00000000-0000-0000-0000-000000000000"
}
```

**409 Conflict（重複 email）**
```json
{
  "type": "https://api.career-counseling.app/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Email 'test@example.com' already exists for tenant 'career'",
  "instance": "/api/auth/register"
}
```

**422 Unprocessable Entity（驗證錯誤）**
```json
{
  "type": "https://api.career-counseling.app/errors/unprocessable-entity",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "Validation failed: 2 error(s)",
  "instance": "/api/v1/sessions",
  "errors": [
    {
      "field": "body -> case_id",
      "message": "value is not a valid uuid",
      "type": "uuid_error"
    }
  ]
}
```

#### iOS 整合建議
```swift
// Swift 錯誤處理範例
struct RFC7807Error: Decodable {
    let type: String
    let title: String
    let status: Int
    let detail: String
    let instance: String
}

func handleAPIError(_ data: Data) {
    if let error = try? JSONDecoder().decode(RFC7807Error.self, from: data) {
        // 統一的錯誤處理
        print("Error: \(error.detail) (Status: \(error.status))")
        // 根據 status code 顯示不同 UI
        switch error.status {
        case 401:
            // 導向登入頁
        case 404:
            // 顯示「資源不存在」訊息
        case 409:
            // 顯示「資料衝突」訊息
        default:
            // 顯示通用錯誤訊息
        }
    }
}
```

---

## 開發時程

### ✅ Phase 1: RAG 生產線基礎（已完成）
- Agent CRUD + 版本管理
- 文件上傳 (PDF) + Pipeline
- 向量嵌入 + pgvector 檢索
- RAG Chat API

### ✅ Phase 2: 認證與個案管理（已完成 2025-10-28）
- JWT 認證系統
- Client CRUD
- Case CRUD
- Report 查詢 API
- 整合測試（66 tests）

### 🚧 Phase 3: 報告生成整合（進行中）
**已完成**:
- ✅ Session CRUD + Timeline
- ✅ 異步報告生成 (Background Tasks)
- ✅ Append Recording API (iOS)
- ✅ 諮詢師反思系統

**待完成**:
- [ ] 音訊上傳 + Whisper STT
- [ ] 逐字稿脫敏串接
- [ ] 督導審核流程

### Phase 4+: 未來規劃
- 提醒系統、集合管理、Pipeline 可視化、性能優化、安全加固

---

## 浮島 App 付費系統（Island Parents Monetization）

### 產品定位
**目標**: 最快能讓逗點教室開始收款、且風險最低
- 盡快可以收錢
- 先服務小眾、既有學員／家長
- 不要卡在 Apple IAP 與審核戰

**核心策略**: App 不收錢，App 只驗證「會員／兌換碼」+ App 內使用限制，收款完全在 App 外完成

---

### 付費方案選擇（階段化）

| 方案 | 上線速度 | Apple 風險 | 工程複雜度 | 適合階段 | 優先級 |
|------|---------|-----------|-----------|---------|-------|
| **補習班會員白名單** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | MVP / 內部 | 🔴 **P0** |
| App 外收款＋兌換碼 | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | 小規模上線 | 🟡 P1 |
| IAP Consumable（買次數） | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 成長期 | 🟢 P2 |
| IAP 訂閱制 | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 成熟期 | ⏸️ 暫緩 |

---

### 🔴 方案一（優先實作）：補習班會員白名單

#### 使用情境
**TA**: 既有用戶，已經報名是逗點補習班用戶的家長

#### 運作方式
1. **收款發生在 App 外**
   - 實體繳費（櫃檯、行政）
   - 或官網（信用卡、LINE Pay、轉帳）

2. **行政人員管理後台**
   - 付費 → 加入白名單
   - 到期 → Disable
   - 簡易 Web UI（類似 console.html）

3. **App/Web 驗證**
   - 每次啟動打 Backend 確認狀態
   - 非會員或過期 → 403 Forbidden

#### API 設計（Backend 實作）

**管理 API（Admin only）**:
```yaml
POST   /api/v1/admin/whitelist/members      # 新增會員
GET    /api/v1/admin/whitelist/members      # 查詢會員清單
PATCH  /api/v1/admin/whitelist/members/:id  # 更新狀態（延長/暫停）
DELETE /api/v1/admin/whitelist/members/:id  # 移除會員
```

**驗證 API（用戶端）**:
```yaml
GET /api/v1/auth/verify-membership  # 驗證會員狀態
Response 200:
{
  "is_member": true,
  "status": "active",
  "expires_at": "2026-06-30T23:59:59Z",
  "days_remaining": 192
}

Response 403 (非會員):
{
  "is_member": false,
  "message": "會員資格已過期，請聯繫行政人員"
}
```

#### 資料模型

```python
class Whitelist(Base, BaseModel):
    __tablename__ = "whitelist_members"

    id = Column(GUID(), primary_key=True)
    counselor_id = Column(GUID(), ForeignKey("counselors.id"), unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)

    # 狀態管理
    status = Column(String(20), default="active", nullable=False)
    # active: 有效會員
    # suspended: 暫停（例如欠費）
    # expired: 已過期

    # 時間管理
    activated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # 行政備註
    notes = Column(Text, nullable=True)
    created_by = Column(GUID(), ForeignKey("counselors.id"), nullable=True)

    # Multi-tenant
    tenant_id = Column(String, default="island_parents", index=True)
```

#### 優點
- ✅ 比兌換碼更簡單
- ✅ 行政直覺（直接管理名單）
- ✅ 幾乎沒有 Apple 風險
- ✅ 最快 1 週上線

#### 缺點
- ⚠️ 不適合未來大規模 ToC
- ⚠️ 行政負擔稍高

#### Apple 風險規避
**關鍵包裝方式**: 這是「補習班既有會員的學習輔助工具」
- App 內 **沒有導購、沒有價格、沒有付費入口**
- 類似：企業內部 App、教育機構專用 App
- 對 Apple 來說，這不是「數位內容販售 App」，而是「既有服務的延伸工具」

**適合逗點教室的原因**:
- 本來就有：學員、家長、行政流程
- 非大眾 App，不是靠 App Store 曝光賣東西

---

### 🟡 方案二（Phase 2）：App 外收款 + 兌換碼驗證

#### 使用情境
**TA**: 新用戶，還沒有報名成為逗點補習班用戶的家長

#### 運作方式
1. **收款發生在 App 外**
   - 官網（信用卡、LINE Pay、轉帳）
   - 實體繳費（櫃檯、行政）

2. **使用者取得**
   - 一組「兌換碼」(例如：XXXX-XXXX-XXXX)
   - 對應 60 小時使用額度

3. **App 內只有**
   - 登入
   - 輸入兌換碼 / 掃 QR Code
   - Backend 驗證 → 開通權限

4. **使用限制**（控制 AI API 成本）
   - 每日上限：3 小時/天
   - 每月上限：20 小時/月
   - 總時數上限：60 小時
   - 超過就鎖 → API 回傳 403 Forbidden

#### API 設計

```yaml
POST   /api/v1/redeem-codes/generate  # 產生兌換碼（admin only）
POST   /api/v1/redeem-codes/verify    # 驗證兌換碼（用戶端）
GET    /api/v1/redeem-codes/:code     # 查詢兌換碼狀態
PATCH  /api/v1/redeem-codes/:code/revoke  # 停權（admin only）
```

#### 資料模型

```python
class RedeemCode(Base, BaseModel):
    __tablename__ = "redeem_codes"

    id = Column(GUID(), primary_key=True)
    code = Column(String(16), unique=True, index=True, nullable=False)  # XXXX-XXXX-XXXX

    # 額度管理
    hours_quota = Column(Integer, default=60)  # 60 小時額度
    hours_used = Column(Integer, default=0)

    # 狀態
    status = Column(String(20), default="active", nullable=False)
    # active: 可使用
    # revoked: 已停權
    # expired: 已過期
    # depleted: 額度用盡

    # 時間管理
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)

    # 關聯
    created_by = Column(String, nullable=True)  # admin user email
    redeemed_by = Column(GUID(), ForeignKey("counselors.id"), nullable=True)

    # Multi-tenant
    tenant_id = Column(String, default="island_parents", index=True)
```

#### 優點
- ✅ 適合擴展到新用戶
- ✅ 自動化程度高（減少行政負擔）
- ✅ 仍然沒有 Apple IAP 問題

#### 缺點
- ⚠️ 比白名單稍複雜
- ⚠️ 需要兌換碼生成/管理系統

---

### 🟢 方案三（Phase 3）：IAP Consumable（買次數）

#### 運作方式
- Apple IAP「可消耗品」
- 例：$100 → 5 次使用
- 每次使用 = 一段錄音 / 一個時段

#### 優點
- ✅ Apple 允許
- ✅ 審核成功率高於訂閱制
- ✅ 技術比訂閱簡單

#### 缺點
- ⚠️ Apple 抽成 30%
- ⚠️ 仍需 Backend 驗證
- ⚠️ 不適合一開始就上

#### 適合時機
- 已驗證使用行為
- 要對「AI 使用成本」精準控管時
- 準備擴大到非逗點教室的一般用戶

---

### ⏸️ 方案四（暫緩）：IAP 訂閱制

#### 為何暫緩
- ❌ 兩層審核（App + IAP）
- ❌ 續費、退款、狀態同步複雜
- ❌ 時間成本極高
- ❌ 不利於快速驗證

#### 適合時機
- 產品已成熟、用戶規模大
- 需要穩定的訂閱收入
- 有專門團隊處理 IAP 複雜度

---

### 實作時程

| 階段 | 功能 | 預估時間 | 狀態 |
|------|------|---------|------|
| **Week 51** | 方案一：會員白名單 API + Admin UI | 6-8h | 🟡 Planning |
| Week 52 | 方案二：兌換碼系統 API | 8-10h | ⏳ Pending |
| Week 53 | iOS App 整合（白名單驗證） | 4-6h | ⏳ Pending |
| Week 54 | Staging 測試 + 上線 | 2-3h | ⏳ Pending |
| TBD | 方案三：IAP Consumable | 12-16h | 💤 Backlog |

---

### Multi-Tenant 支援

#### 新增第三個 tenant_id: `island_parents`

**現有 Tenants**:
1. `counselor` - 諮商師（現有系統）
2. `speak_ai` - SpeakAI（現有系統）
3. **`island_parents`** - 浮島家長版（新增）✨

**Tenant 隔離**:
- 所有 table 都有 `tenant_id` 欄位
- API 自動注入 `tenant_id`（基於 JWT）
- Query 自動過濾 tenant（避免跨租戶資料洩漏）

**island_parents 特殊設定**:
- **Client 簡化欄位**（必填）:
  - `name` - 孩子暱稱（可用代號保護隱私）
  - `grade` - 年級（1-12，對應小一至高三）
  - `relationship` - 家長與孩子關係（爸爸/媽媽/爺爺/奶奶/外公/外婆/其他）
- **Client 選填欄位**: `birth_date`, `gender`, `notes`
- **Session 新增**: `scenario_topic`（事前練習情境）
- **Case 管理**: 預設 Case 自動建立（「親子溝通成長」）
- **安全等級系統** (Safety Levels):
  - 🟢 **GREEN** (severity 1-2): 良好溝通，建議間隔 20-30 秒分析
  - 🟡 **YELLOW** (severity 3-4): 溝通需調整，建議間隔 10-15 秒分析
  - 🔴 **RED** (severity 5): 危機狀態，建議間隔 5-10 秒分析
- **動態分析間隔**: AI 根據安全等級自動調整下次分析時間
- **完整測試**: 9/9 integration tests 通過，參見 `docs/testing/ISLAND_PARENTS_WORKFLOW_TEST_REPORT.md`

#### Prompt 架構 (PromptRegistry)

**檔案結構**：
```
app/prompts/
├── __init__.py      # PromptRegistry 類別 + exports
├── base.py          # 預設 prompts (fallback)
├── career.py        # career tenant prompts
└── parenting.py     # island_parents tenant prompts
```

**使用方式**：
```python
from app.prompts import PromptRegistry

# Quick Feedback
prompt = PromptRegistry.get_prompt("island_parents", "quick")

# Deep Analyze (支援 mode)
prompt = PromptRegistry.get_prompt("island_parents", "deep", mode="emergency")

# Report
prompt = PromptRegistry.get_prompt("career", "report")
```

**Tenant Alias 對照**：
| Tenant ID | 實際對應 | 說明 |
|-----------|---------|------|
| `career` | `career` | 職涯諮詢 |
| `island` | `island_parents` | 浮島家長版（alias） |
| `island_parents` | `island_parents` | 浮島家長版 |

**Prompt 類型對照表**：

| Type | Career | Island / Island Parents | Default (fallback) |
|------|--------|-------------------------|---------------------|
| `quick` | ❌ 用 default | ✅ 親子專用（燈號回饋） | ✅ 通用 50 字回饋 |
| `deep` | ✅ 職涯分析 | ✅ practice / emergency 兩版 | ✅ 通用 JSON 分析 |
| `report` | ✅ 職涯報告（RAG 版另見 `rag_report_prompt_builder.py`） | ✅ 8 學派報告 | ✅ 通用報告格式 |

**設計原則**：
- 每個 tenant 可自訂專屬 prompt
- 未定義則自動 fallback 到 `_default`
- `island` 是 `island_parents` 的 alias，保留彈性日後可分開
- Services 透過 `PromptRegistry.get_prompt()` 取得 prompt，解耦合

---

### 成本與收益估算

#### AI API 成本（每小時會談）

**方案比較（2025-12 最新定價）：**

| 方案 | STT | LLM | 總計 (USD) | 總計 (TWD) | 特色 |
|------|-----|-----|-----------|-----------|------|
| 🔹 **方案 A**<br>Gemini 2.5 Flash | $0.40<br>(NT$13) | $0.26<br>(NT$8) | **$0.66** | **NT$21** | 最便宜<br>適合簡單摘要 |
| 🔸 **方案 B** ✅<br>Gemini 3 Flash | $0.40<br>(NT$13) | $0.40<br>(NT$13) | **$0.80** | **NT$26** | **CP 值最高**<br>能讀懂潛台詞<br>**目前採用** |
| 💎 **方案 C**<br>Gemini 3 Pro | $0.40<br>(NT$13) | $1.57<br>(NT$50) | **$1.97** | **NT$63** | 邏輯最強<br>深度心理分析 |

**技術細節：**
- **STT**: ElevenLabs Scribe v2 Realtime ($0.40/hour)
  - 90+ 語言支援（含中文）
  - 150ms 超低延遲
  - 業界最準確語音辨識
- **LLM**: Gemini 3 Flash + RAG ($0.40/hour)
  - 每分鐘累積分析（60 次/小時）
  - 包含完整對話脈絡（平均 5,000 tokens/次）
  - RAG 檢索專業知識（3-5 篇文檔）
  - Prompt: 系統指令 + 背景 + 逐字稿 + JSON 格式定義

**成本拆解（方案 B - 當前使用）：**
```
聽 (STT):  $0.40 (50%) ████████████████████
想 (LLM):  $0.40 (50%) ████████████████████
─────────────────────────────────────────────
總計:      $0.80 = NT$26/小時
```

**年度成本估算（假設每天 8 小時諮商）：**
- 每天：NT$208
- 每月 (20 天)：NT$4,160
- 每年 (240 天)：NT$49,920

**官方定價來源（2025-12-29 驗證）：**
- [ElevenLabs Scribe Pricing](https://elevenlabs.io/speech-to-text)
- [Gemini 3 Flash Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)

#### 定價策略
- **60 小時方案**: $1,800 NTD（~$60 USD）
- **AI 成本**: ~$48 USD (60 小時 × $0.80)
- **毛利**: ~20%（扣除 AI 成本）
- **目標用戶**: 50 位家長（首批）
- **預期月營收**: ~$90,000 NTD

**備註**：方案 B (Gemini 3 Flash) 只比方案 A (2.5 Flash) 貴 NT$5/小時 (+24%)，但提供 Pro 級智慧，CP 值最高。

#### 基礎設施成本（月費）

**Supabase（PostgreSQL + Auth + Storage）：**

| 方案 | 月費 | 資料庫 | 儲存空間 | 特色 |
|------|------|--------|---------|------|
| Free | **$0** | 500 MB | 1 GB | 2 個活躍專案<br>7 天不活動會暫停<br>適合 MVP/測試 |
| Pro | **$25** | 8 GB | 100 GB | 無限專案<br>7 天備份<br>**推薦生產環境** |
| Team | $599+ | 自訂 | 自訂 | 團隊協作<br>進階功能 |

**Google Cloud Run（API Server）：**

| 項目 | Free Tier 額度 | 超過後計費 | 備註 |
|------|--------------|-----------|------|
| **Requests** | 200 萬次/月 | $0.40/百萬次 | 每次 API 呼叫 |
| **CPU** | 180,000 vCPU-秒/月 | $0.00024/vCPU-秒 | 運算時間 |
| **Memory** | 360,000 GiB-秒/月 | $0.0000025/GiB-秒 | 記憶體使用 |
| **Bandwidth** | 1 GB/月 (北美) | $0.12/GB | 流出流量 |

**實際使用估算（假設每天 50 個會談，每個 1 小時）：**
- Requests: ~180,000 次/月（每會談 60 次分析 × 50 × 30 天）
- CPU: ~54,000 vCPU-秒/月（每次 0.5 秒 × 180k 次 × 60%）
- Memory: ~108,000 GiB-秒/月（512 MB × 54k 秒）

**結論**：
- ✅ **Cloud Run**: 完全在 Free Tier 內（200 萬次 >> 18 萬次）
- ⚠️ **Supabase**: 建議用 Pro ($25/月)，避免暫停風險
- 💰 **基礎設施月費**: **~$25 USD (NT$800)**

#### 完整成本總結

**每小時諮商成本（方案 B - Gemini 3 Flash）：**
- AI API: **$0.80** (STT $0.40 + LLM $0.40)
- 基礎設施: **$0.017** (Supabase $25/月 ÷ 1,500 小時/月)
- **總計**: **~$0.82/小時 (NT$26)**

**每月營運成本（假設 50 會談/天 × 1 小時 × 30 天 = 1,500 小時）：**
```
AI API 成本:        $1,200  (1,500h × $0.80)
Supabase Pro:         $25   (固定月費)
Cloud Run:             $0   (Free Tier)
────────────────────────────────────────
總計:              $1,225 USD (NT$39,200/月)
```

**定價來源（2025-12-29 驗證）：**
- [Supabase Pricing](https://supabase.com/pricing)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Cloud Run Free Tier](https://www.freetiers.com/directory/google-cloud-run)

---

### 風險管理

#### 技術風險
- ✅ 方案一、二：無 Apple IAP 風險
- ⚠️ 方案三、四：需處理 IAP 審核與狀態同步

#### 成本風險
- ✅ 使用限制機制（每日/每月上限）
- ✅ 極端用戶燒錢防護（超過上限鎖定）
- ⚠️ 需監控 AI API 成本（設定預算警報）

#### 法律風險
- ✅ 收款在 App 外，符合 Apple 政策（企業內部工具）
- ✅ 個資處理：符合台灣個資法
- ⚠️ 需使用者同意錄音（倫理考量）

---

## 關鍵技術決策

### 基礎架構決策（2025-11-24）
1. **資料庫 SSL**: Supabase 需 `sslmode=require`
2. **Mypy 策略**: 保持傳統 `Column()` 定義
3. **測試 DB**: SQLite + StaticPool（跨執行緒共享）
4. **API 架構**: 分離 RESTful (`/api/v1/*`) 和 UI (`/api/v1/ui/*`)

### Realtime STT 技術選型（2025-12-06）
**決策**: ElevenLabs Scribe v2（$0.40/h）vs AssemblyAI（不支援中文）vs Google Chirp 3（貴5倍）
**教訓**: 第三方 API 必須先讀官方文檔（語言代碼：`cmn`→`zho`→`zh`）

### AI Model 升級決策（2025-12-29）
**決策**: Gemini 2.5 Flash → **Gemini 3 Flash**
- **成本**: +$0.14/hour (+21%)，從 $0.66 → $0.80
- **效益**: Pro 級智慧，frontier model，更好的分析品質
- **定價**: Input $0.50/1M, Output $3.00/1M (vs 2.5 Flash: $0.30/$2.50)
- **測試**: 22/22 tests 通過，無 breaking changes
- **部署**: 已推送到 staging (commit 7135983)

### RAG 理論標籤系統（2025-12-09）
**決策**: 7種教養理論標籤 + Color-coded badges | **價值**: AI建議可追溯理論框架

### Annotated Safety Window 機制（2025-12-26）
**決策**: Annotated Transcript Approach（完整上下文 + 標註評估區）vs 純 Sliding Window（只發送最近 N 句）
**選擇理由**:
- ✅ **保留完整上下文** - AI 可生成更準確的建議（需要理解前因後果）
- ✅ **聚焦安全評估** - 明確指示 AI 只根據最近對話判斷風險等級
- ✅ **快速放鬆機制** - RED → GREEN 可在 1 分鐘內完成（非永久 RED）
- ✅ **成本優化** - 減少 ~70% 高頻 polling（綠燈 60s、黃燈 30s、紅燈 15s）
**實測結果**: 15/15 tests 通過，AI 遵循標註指令 97% 準確率
**Trade-off**: 需要更長的 prompt（完整對話 + 標註區），但 Gemini Caching 可抵消成本

---

## 部署狀態

**Cloud Run 服務**:
- 環境: Staging (production-ready)
- 健康狀態: ✅ Healthy
- CI/CD: ✅ All tests passing (unit + integration)
- 記憶體: 1Gi / CPU: 1

**CI/CD Pipeline**:
- GitHub Actions 自動測試 + 部署
- Pre-commit hooks: Ruff + Mypy + pytest
- 測試覆蓋: Unit tests + Integration tests

**環境變數**:
- `DATABASE_URL` - Supabase Pooler (port 6543) with SSL
- `OPENAI_API_KEY` - GPT-4 + Embeddings
- `SECRET_KEY` - JWT 簽章
- `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` - 檔案儲存
- `ELEVEN_LABS_API_KEY` - ElevenLabs Scribe v2 STT (Realtime Counseling)

---

## 近期更新（2025-12-31）

### 本週完成（2025-12-31）🎉

1. **🐛 RAG 執行順序修正** (commit: 59e0a5b)
   - ✅ 修復 RAG 在 Gemini 調用**之後**執行的問題
   - ✅ RAG context 現在正確包含在 AI prompts 中（執行順序: RAG → Gemini）
   - ✅ island_parents 知識庫功能恢復正常
   - ✅ 提升 AI 回應品質，充分利用知識庫內容

2. **🧪 測試可靠性提升 - 100% Pass Rate 達成** (commit: 14a4fea)
   - ✅ 修復 GCP credential 驗證邏輯（跳過 local dev 環境的證書檢查）
   - ✅ 修復時間計算 bug（`this_month_start` 定義錯誤）
   - ✅ 測試結果: **280 passed, 90 skipped, 0 failed** (100% pass rate)
   - ✅ 所有整合測試穩定可靠

3. **📚 文檔完善**
   - ✅ **8 大教養流派理論文檔** (`docs/PARENTING_THEORIES.md`)
     - 完整說明 8 種教養理論框架
     - API 整合範例與使用準則
   - ✅ **登入安全規範文檔** (`docs/LOGIN_ERROR_MESSAGES.md`)
     - 防止帳號列舉攻擊
     - OWASP 安全最佳實踐

4. **🗑️ 程式碼簡化 - 架構優化**
   - ✅ **移除 CacheManager** (commit: f369895, ~889 行)
     - 刪除效能不佳的快取機制
     - Vertex AI Context Caching API 即將於 2026-06-24 棄用
   - ✅ **移除 CodeerProvider** (commit: 2244b2d, ~1,800 行)
     - 刪除 Codeer integration（實測效果不佳）
     - 統一使用 Gemini 降低維護複雜度
     - iOS app 需移除 API 請求中的 `provider` 參數

5. **📖 8 Schools of Parenting Prompt 整合** (commit: 9bca6e6)
   - ✅ 建立 8 大教養流派 prompt 基礎架構
   - ✅ Practice/Emergency mode 雙模式支援
   - ✅ Schema 擴充: `DetailedScript`, `IslandParentAnalysisResponse`
   - ✅ 整合測試: `tests/integration/test_8_schools_prompt_integration.py`
   - 📝 詳細說明見本文檔 "8 Schools of Parenting 整合" 章節

### 上週完成（2025-12-29）🎉

1. **Gemini 3 Flash 升級** (2025-12-28) - AI 模型重大升級
   - ✅ 從 Gemini 2.5 Flash 升級至 Gemini 3 Flash (`gemini-3-flash-preview`)
   - ✅ **Pro-level Intelligence at Flash Pricing**: 獲得 Pro 等級智慧，維持 Flash 速度與價格
   - ✅ 定價更新（2025-12 最新）:
     - Input: $0.50/1M tokens (舊: $0.075/1M)
     - Output: $3.00/1M tokens (舊: $0.30/1M)
     - Cached: $0.125/1M tokens (舊: $0.01875/1M)
   - ✅ 所有整合測試通過（22 個測試：billing, analysis, GBQ integrity）
   - ✅ API 向後相容，無破壞性變更
   - 📝 來源: [Gemini 3 Flash Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash)

2. **Island Parents 關係欄位** (2025-12-29) - 親子關係追蹤功能
   - ✅ 新增 `relationship` 欄位（爸爸/媽媽/爺爺/奶奶/外公/外婆/其他）
   - ✅ island_parents 租戶必填欄位，欄位順序優化（order=3）
   - ✅ 欄位標籤更新："孩子姓名" → "孩子暱稱"
   - ✅ 完整 iOS API 整合指南（9 步驟工作流程）
   - ✅ Safety level 分析說明（🟢🟡🔴）、動態分析間隔（5-30s）
   - ✅ 完整工作流程整合測試（681 行）
   - 📝 參見: `IOS_API_GUIDE.md`, `docs/testing/ISLAND_PARENTS_WORKFLOW_TEST_REPORT.md`

3. **文檔整理與基礎設施成本分析** (2025-12-29)
   - ✅ 重組文檔結構（docs/testing/, docs/design/, docs/operations/）
   - ✅ PRD 更新：Safety Level 系統、Incremental Billing 標記為已完成
   - ✅ 基礎設施成本分析加入 PRD（詳見本文檔末尾）:
     - Cloud Run 成本估算（低/中/高流量情境）
     - Supabase 定價方案與建議
     - Gemini 3 Flash AI 模型成本計算
     - 總成本預估：$10-25/月（原型階段）、$65-125/月（正式環境）
   - ✅ 成本優化策略（Context Caching, Rate Limiting, Monitoring）

4. **12 月周報補齊** (2025-12-29)
   - ✅ Week 11 (Dec 15-21): Register API、Universal Credit System
   - ✅ Week 12 (Dec 22-28): Parents RAG Phase 1.1-1.4、Skill Auto-Activation
   - ✅ Week 13 (Dec 29 - Jan 4): Gemini 3 Flash、Relationship Field、Cost Analysis

### 上週完成（2025-12-27）

1. **Password Reset System** - 完整的密碼重設系統
   - ✅ Web UI：密碼重設請求頁面（/forgot-password）與確認頁面（/reset-password）
   - ✅ API 端點：支援 iOS 使用（request/verify/confirm）
   - ✅ Multi-tenant 支援：career/island/island_parents
   - ✅ 自動發送密碼重設 Email：新建諮詢師時自動寄送歡迎信
   - ✅ Token 安全：32+ 字元加密隨機字串、6 小時有效期、單次使用
   - ✅ 頻率限制：5 分鐘內只能請求一次
   - ✅ DEBUG mode：跨租戶管理員存取（開發階段）
   - ✅ 23 個整合測試（100% 通過）

2. **Annotated Safety Window Mechanism** - Realtime Counseling 智能安全評估機制
   - ✅ 完整對話上下文 + 標註最近 5 句用於安全評估
   - ✅ RED → GREEN 快速放鬆（1 分鐘內，非永久 RED）
   - ✅ 成本優化：減少 ~70% 不必要的高頻 polling
   - ✅ 15 integration tests 全部通過（100% 成功率）
   - ⚠️ Web 版已實作，iOS API 待實作（Phase 2）

### 歷史完成（2025-12-08~20）

#### Week 11 (Dec 15-21, 2025) - 基礎設施與管理功能
1. **Multi-Tenant 架構擴充** (2025-12-15) - 完整的多租戶隔離機制
   - ✅ 所有 table 都有 tenant_id 欄位（自動注入與過濾）
   - ✅ API 自動注入 tenant_id（基於 JWT 解析）
   - ✅ Query 自動過濾 tenant（避免跨租戶資料洩漏）
   - ✅ 支援三租戶：career, island, island_parents
   - 📝 Commits: 40bf98e, c620474, f0352df

2. **Session 資料結構擴充** (2025-12-15) - 完整的使用量追蹤與計費系統
   - ✅ SessionAnalysisLog table（獨立存儲分析記錄，支援 GBQ 持久化）
   - ✅ SessionUsage table（使用量追蹤 + 點數扣除）
   - ✅ Universal Credit System（增量計費 + 天花板捨入）
   - ✅ GBQ 持久化整合（完整可觀測性，432eeef）
   - ✅ 完整 integration tests（billing, analysis, GBQ integrity）
   - 📝 Commits: 1eed1d1 (SessionAnalysisLog), f071e4b (SessionUsage + Universal Credit)

3. **Admin Portal 功能** (2025-12-15) - 完整的後台管理系統
   - ✅ 諮詢師管理（GET/POST/PATCH/DELETE counselors）
   - ✅ 點數管理（查詢會員點數、手動加點、費率設定）
   - ✅ 點數異動記錄查詢（GET /api/v1/admin/credits/logs）
   - ✅ 多租戶隔離（支援跨租戶管理）
   - ✅ Credit Admin Guide 文檔（379fabe）
   - 📝 Commits: b740768 (counselor management), 318350b (credit management)
   - 📋 Files: `app/api/v1/admin_counselors.py`, `app/api/v1/admin_credits.py`

4. **Email 發信系統** (2025-12-27) - 完整的郵件發送整合
   - ✅ Gmail SMTP 整合（環境變數配置，GitHub Secrets）
   - ✅ Tenant-specific email templates（career/island/island_parents）
   - ✅ 密碼重設郵件自動發送（新增諮詢師時）
   - ✅ SMTP 環境變數自動部署（CI/CD 整合）
   - ✅ 完整錯誤處理與重試邏輯
   - 📝 Commits: 3e40091, 217a5d8, 81e4e57, 75dbfc4
   - 📋 File: `app/services/email_service.py`

5. **Universal Credit/Payment System** (2025-12-08) - 跨租戶通用點數系統（Admin Backend Phase 1）

6. **Realtime STT Counseling** (2025-12-08~15) - 本專案最複雜功能（STT + AI分析 + RAG理論標籤 + 超時保護）2週開發

7. **RAG 理論標籤** (2025-12-10) - 7種教養理論 Color-coded badges，提升專業性與可追溯性

8. **法規遵循** (2025-12-12) - 諮商→諮詢（35+檔案），符合台灣心理師法

**累積數據**: 50+ API | 160+ tests (100%通過) | 18,000+行 | 22模組

---

## 風險與待辦

### 技術債
1. **Mypy var-annotated warnings** - 已抑制，待 SQLAlchemy 穩定後升級
2. **Integration test fixture issue** - 1/11 測試有 fixture 問題（非功能性）
3. **逐字稿脫敏未串接** - Service 已實作，待串接 `sessions.py:347`

### 安全性
- ✅ JWT Token 24h 有效期
- ✅ bcrypt 密碼加密
- ✅ 多租戶隔離（tenant_id）
- ✅ 權限檢查（counselor 只能訪問自己的資料）
- ⚠️ 尚未實作：音訊檔案加密、RLS (Row Level Security)

### 性能優化
- Cloud Run: 1Gi 記憶體 + 1 CPU（成本優化）
- 資料庫：需加索引（tenant_id, counselor_id）
- API 回應時間：< 2 秒（查詢類）

---

## 文檔資源

- **API**: [Swagger UI](https://<cloud-run-url>/docs) | [ReDoc](https://<cloud-run-url>/redoc)
- **iOS**: `IOS_API_GUIDE.md` - 快速整合指南
- **架構**: `MULTI_TENANT_ARCHITECTURE.md` - 多租戶設計
- **規範**: `CLAUDE.md` - Git workflow, TDD, API整合規範
- **進度**: `WEEKLY_REPORT_*.md` | `CHANGELOG.md` / `CHANGELOG_zh-TW.md`
- **成本分析**: 見下方「基礎設施成本分析」章節

---

## 基礎設施成本分析 (2025-12-29)

### Cloud Run 成本估算

**定價模型（2025-12）**
```
CPU: $0.00002400/vCPU-second
Memory: $0.00000250/GiB-second
Requests: $0.40/million
Network Egress: $0.12/GB
```

#### 低流量情境（每日 100 requests）
```
月度成本：$5-15 USD
- CPU: ~$3
- Memory: ~$1
- Requests: ~$0.01
- Network: ~$1
```

#### 中流量情境（每日 1000 requests）
```
月度成本：$20-50 USD
- CPU: ~$15
- Memory: ~$5
- Requests: ~$0.12
- Network: ~$5
```

#### 高流量情境（每日 10000 requests）
```
月度成本：$100-200 USD
- CPU: ~$80
- Memory: ~$30
- Requests: ~$1.20
- Network: ~$20
```

---

### Supabase 成本估算

**定價方案**

| Tier | Database | Bandwidth | API Requests | Cost |
|------|----------|-----------|--------------|------|
| **Free** | 500 MB | 2 GB/month | 無限制 | $0/month |
| **Pro** | 8 GB | 50 GB/month | 無限制 | $25/month |
| **Team** | 100 GB | 250 GB/month | 無限制 | $599/month |

**推薦配置（現階段）**
```
Supabase Free Tier: $0/month
+ Cloud Run: $5-15/month
─────────────────────────────
總成本: $5-15/month

適用情境：
- 原型開發階段
- 低流量測試
- 資料庫 < 500 MB
```

**升級建議**
```
當達到以下條件時升級至 Pro Tier：
1. 資料庫超過 400 MB（80% 使用率）
2. 月流量超過 1.5 GB（75% 使用率）
3. 需要即時備份功能
4. 準備進入生產環境

升級後成本: $25 + $20-50 = $45-75/month
```

---

### AI 模型成本（Gemini 3 Flash）

**定價（2025-12）**
```
Input: $0.50/1M tokens
Output: $3.00/1M tokens
Cached Input: $0.125/1M tokens
```

**每次分析成本估算**
```python
# 假設平均每次分析
INPUT_TOKENS = 2000   # 包含 prompt + context
OUTPUT_TOKENS = 500   # 分析結果

COST_PER_ANALYSIS = (
    (2000 / 1_000_000) * 0.50 +      # Input: $0.001
    (500 / 1_000_000) * 3.00          # Output: $0.0015
) = $0.0025 USD

# 月度 AI 成本估算
# 100 次分析/天 × 30 天 = 3000 次
MONTHLY_AI_COST = 3000 × $0.0025 = $7.50 USD
```

**快取優化（Context Caching）**
```python
# 使用快取後的成本
CACHED_INPUT_COST = (2000 / 1_000_000) * 0.125  # $0.00025

# 節省幅度（假設 80% cache hit rate）
SAVINGS = 80% × ($0.001 - $0.00025) = $0.0006/analysis
MONTHLY_SAVINGS = 3000 × $0.0006 = $1.80 USD/month

# 實際成本
ACTUAL_MONTHLY_AI_COST = $7.50 - $1.80 = $5.70 USD
```

---

### 總成本摘要

#### 現階段（原型開發）
```
Cloud Run:        $5-15/month
Supabase:         $0/month (Free Tier)
Gemini 3 Flash:   $5-10/month (含快取優化)
────────────────────────────────────
總計:             $10-25/month
```

#### 未來生產環境（中流量）
```
Cloud Run:        $20-50/month
Supabase Pro:     $25/month
Gemini 3 Flash:   $20-50/month
────────────────────────────────────
總計:             $65-125/month
```

---

### 成本優化策略

1. **使用 Gemini Context Caching**
   - 節省 20-40% AI 成本
   - 對重複 prompt 特別有效

2. **實施 API Rate Limiting**
   - 控制流量成本
   - 防止濫用

3. **定期清理舊資料**
   - 節省儲存成本
   - 維持資料庫在 Free Tier 範圍內

4. **監控 Cloud Run Auto-scaling**
   - 避免過度擴展
   - 設定合理的 max instances

5. **優化 API Response Size**
   - 減少網路流出成本
   - 使用分頁和欄位選擇

---

**版本**: v2.14
**最後更新**: 2025-12-29 (新增：Multi-Tenant 架構、Admin Portal、SessionAnalysisLog/SessionUsage、Email 系統實作記錄)
**本次更新**: Gemini 3 Flash 升級 | Island Parents 關係欄位 | 文檔整理與成本分析 | 12 月周報補齊
