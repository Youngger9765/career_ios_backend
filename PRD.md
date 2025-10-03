# 職涯諮詢平台 PRD（雙業務線架構）

## 系統全局觀

### 核心理念
本系統採用**雙業務線獨立架構**，將 AI 能力建設與業務應用分離：

**1. RAG Ops 生產線（管理層）** - 建立 AI 能力
- 上傳知識文件 → 向量化 → 建立 Agent → 測試
- 內部使用，技術人員操作
- 路徑：`/rag/*` (Next.js Console)

**2. 諮商應用線（業務層）** - 提供諮商服務
- 接收輸入（音訊或逐字稿）→ 調用 Agent → 生成報告
- 對外服務，支援 iOS App 和 Web 前台
- 路徑：`/api/v1/*` (API) + `/console/*` (Web 前台)

### 關鍵整合點
- 諮商應用線**調用** RAG Ops 建立好的 Agent（通過 API）
- 兩條線資料獨立，通過服務層解耦

---

## 第一部分：諮商應用線（業務層）

### 1.1 產品背景與目標

**情境**：諮商師與個案進行會談，系統協助產出專業報告

**輸入來源**（二擇一）：
1. **音訊上傳**：iOS App 錄音 → 上傳後端 → STT 轉逐字稿
2. **逐字稿直傳**：iOS 端已處理好逐字稿 → 直接上傳

**處理流程**：
逐字稿 → 調用 RAG Agent（檢索理論） → GPT-4 生成報告

**輸出模式**：
1. **API 回傳**：JSON response 給 iOS App
2. **Web 前台**：簡易介面查看報告成果

**目標**：
1. 支援音訊與逐字稿雙輸入模式
2. 確保報告符合助人專業框架（含理論引用）
3. 提供完整個案管理：個案 → 會談 → 報告 → 提醒

---

### 1.2 功能需求

#### 帳號與權限
* 諮商師登入、管理員建立帳號
* 角色分級：諮商師 / 督導 / 管理員

#### 個案管理
* 建立來訪者資料
* 個案（諮商師 + 來訪者的關係）
* 會談紀錄（日期、房間、逐字稿）

#### 雙輸入模式

**模式 1：音訊上傳**
1. iOS App 上傳音訊檔
2. 建立異步任務（Job）
3. OpenAI Whisper STT 轉逐字稿
4. 脫敏處理（移除敏感資訊）
5. 保存原稿與脫敏稿

**模式 2：逐字稿直傳**
1. iOS App 直接上傳逐字稿文字
2. 跳過 STT，直接進入報告生成
3. 可選脫敏處理

#### AI 報告生成（調用 RAG Agent）
1. 接收逐字稿
2. **調用 RAG Agent API**：
   - 傳入逐字稿作為 query
   - Agent 檢索知識庫（理論、框架）
   - 返回相關理論片段 + 相似度分數
3. GPT-4 結合檢索結果生成報告：
   - 【主訴問題】
   - 【成因分析】（含理論引用）
   - 【晤談目標】
   - 【介入策略】
   - 【成效評估】
   - 【關鍵對話摘錄】
4. 保存報告與引用來源

#### 報告審核
* 督導審核流程
* 狀態：草稿 / 通過 / 退回
* 版本歷史

#### 提醒與追蹤
* 回訪日期提醒
* 追蹤事項管理

#### 隱私與安全
* 音訊與逐字稿加密保存
* 預設展示脫敏稿
* 保留政策：180 天（可調整）

---

### 1.3 使用流程（User Flow）

**流程 A：音訊上傳模式**
1. 諮商師在 iOS App 進行會談並錄音
2. 上傳音訊檔至後端 `POST /api/v1/sessions/{id}/upload-audio`
3. 後端建立異步任務（Job），狀態：queued → processing
4. Whisper STT 轉逐字稿 → 脫敏處理
5. 任務完成，狀態：completed
6. 進入報告生成流程

**流程 B：逐字稿直傳模式**
1. iOS App 已完成逐字稿處理（本地或第三方）
2. 直接上傳逐字稿 `POST /api/v1/sessions/{id}/upload-transcript`
3. 跳過 STT，直接進入報告生成流程

**報告生成流程（兩種模式共用）**
1. 後端調用 RAG Agent API `POST /api/rag/chat`
2. Agent 檢索理論知識庫，返回相關片段
3. GPT-4 結合檢索結果生成報告
4. 報告存為草稿，返回給 iOS 或顯示在 Web 前台
5. 督導審核 → 通過 → 存入個案紀錄
6. 可建立提醒與追蹤事項

---

### 1.4 資料模型（諮商系統）

**諮商業務資料**（獨立於 RAG 系統）
```sql
-- 使用者與權限
users(id, name, email, role, created_at)

-- 來訪者與個案
visitors(id, name_alias, tags, created_at)
cases(id, counselor_id, visitor_id, status, created_at)

-- 會談與逐字稿
sessions(
  id, case_id, date, room,
  audio_path,           -- 音訊檔路徑（模式 1）
  transcript_text,      -- 逐字稿內容
  transcript_sanitized, -- 脫敏後逐字稿
  source_type,          -- [audio|text] 輸入來源
  created_at
)

-- 異步任務（僅音訊模式使用）
jobs(
  id, session_id,
  type,    -- [stt|sanitize]
  status,  -- [queued|processing|completed|failed]
  error_msg, created_at
)

-- 報告（含 RAG Agent 引用）
reports(
  id, case_id, session_id,
  content_json,  -- 結構化報告內容
  citations_json, -- RAG 檢索的理論引用
  agent_id,      -- 使用的 Agent ID
  version, status, created_at
)

-- 提醒
reminders(
  id, case_id, due_date,
  content, status, created_at
)
```

---

## 第二部分：RAG Ops 生產線（管理層）

### 2.1 目標與邊界

**目的**：建立和管理 RAG Agent，供諮商應用線調用

**核心功能**：
- 上傳理論文獻（PDF/URL/Text）
- 文字切片 + 向量嵌入
- 建立 Agent（配置 Prompt、參數）
- 版本管理（draft/published）
- 測試台驗證

**使用者**：管理員/技術人員（內部使用）

**界面**：`/rag/*` - Next.js Console

### 2.2 資料模型（RAG 系統）

**RAG 知識與 Agent 資料**（獨立於諮商系統）
```sql
-- Agent 管理
agents(
  id, slug, name, description,
  status, active_version_id,
  created_at, updated_at
)

agent_versions(
  id, agent_id, version,
  state,       -- [draft|published]
  config_json, -- {model, temperature, top_k, system_prompt}
  created_at
)

-- 知識庫
datasources(id, type, source_uri, created_at)
documents(id, datasource_id, title, bytes, pages, created_at)
chunks(id, doc_id, ordinal, text, meta_json)
embeddings(id, chunk_id, embedding vector(1536))

-- 集合
collections(id, name, created_at)
collection_items(collection_id, doc_id, created_at)

-- Pipeline 追蹤
pipeline_runs(
  id, scope, target_id,
  status, steps_json,
  started_at, ended_at, error_msg
)

-- 聊天日誌（測試台使用）
chat_logs(
  id, agent_id, version_id,
  question, answer, citations_json,
  tokens_in, tokens_out, created_at
)
```

---

## 第三部分：系統整合架構

### 3.1 雙業務線解耦設計

**原則**：
1. 資料庫獨立：兩條線各自的表不相互引用
2. 服務層解耦：通過 API 調用，不直接訪問對方資料庫
3. 配置隔離：環境變數、配置文件分開管理

**整合點**：
- 諮商系統通過 `/api/rag/chat` 調用 Agent
- 僅傳遞：query (逐字稿) + agent_id
- 返回：answer + citations[]

### 3.2 部署架構

```
單一 Cloud Run 容器
├── FastAPI Backend
│   ├── /api/v1/*      諮商業務 API（iOS + Web）
│   ├── /api/rag/*     RAG Agent API（內部調用）
│   ├── /console/*     諮商前台（簡易 Web）
│   └── /rag/*         RAG Console (Next.js 靜態)
├── PostgreSQL + pgvector (Supabase)
└── Supabase Storage (音訊 + 文件)
```

### 3.3 技術選型

**後端框架**
- FastAPI (Python 3.11+)
- SQLAlchemy ORM
- Pydantic 驗證

**資料庫**
- PostgreSQL + pgvector
- Supabase 託管

**前端**
- RAG Console: Next.js 14 (靜態輸出)
- 諮商前台: FastAPI Templates（簡易）

**AI 服務**
- OpenAI Whisper (STT)
- GPT-4 / GPT-4o-mini
- text-embedding-3-small

**儲存 & 部署**
- Supabase Storage
- Docker + Google Cloud Run
- GitHub Actions CI/CD

---

## 第四部分：API 端點規劃

### 4.1 諮商業務 API (`/api/v1/*`)

#### 認證
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`

#### 使用者
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me`

#### 來訪者與個案
- `GET /api/v1/visitors`
- `POST /api/v1/visitors`
- `GET /api/v1/cases`
- `POST /api/v1/cases`

#### 會談（雙輸入模式）
- `POST /api/v1/sessions` - 建立會談
- `POST /api/v1/sessions/{id}/upload-audio` - 上傳音訊（模式 1）
- `POST /api/v1/sessions/{id}/upload-transcript` - 上傳逐字稿（模式 2）
- `GET /api/v1/sessions/{id}/transcript` - 取得逐字稿

#### 報告
- `POST /api/v1/reports/generate` - 生成報告（調用 RAG Agent）
- `GET /api/v1/reports/{id}` - 取得報告
- `PATCH /api/v1/reports/{id}/review` - 審核報告

#### 任務狀態
- `GET /api/v1/jobs/{id}` - 查詢異步任務狀態

#### 提醒
- `GET /api/v1/reminders`
- `POST /api/v1/reminders`

### 4.2 RAG Agent API (`/api/rag/*`)

**內部調用 + Console 使用**

#### Agent 管理
- `GET /api/rag/agents`
- `POST /api/rag/agents`
- `POST /api/rag/agents/{id}/versions/{vid}/publish`

#### 文件上傳
- `POST /api/rag/ingest/files`
- `POST /api/rag/ingest/url`

#### 檢索 & 聊天
- `POST /api/rag/search` - 向量檢索
- `POST /api/rag/chat` - RAG 問答（**諮商系統調用此端點**）

#### Pipeline
- `GET /api/rag/pipelines/runs`

---

## 第五部分：開發規劃

### 5.1 成功標準（MVP）

**諮商應用線**：
- 支援音訊與逐字稿雙輸入
- 報告生成包含理論引用（來自 RAG Agent）
- API 可回傳給 iOS，也可在 Web 前台展示

**RAG 生產線**：
- 10 分鐘內建立 Agent → 上傳文件 → 測試成功
- 檢索延遲 < 300ms

**系統整合**：
- 諮商系統成功調用 RAG Agent API
- 兩條線資料獨立，無耦合

### 5.2 MVP 範圍劃分

#### Phase 1: RAG 生產線基礎（2 週）
- [ ] Agent CRUD + 版本管理
- [ ] 文件上傳（PDF）+ Pipeline
- [ ] 文字切片 + OpenAI Embeddings
- [ ] pgvector 向量檢索
- [ ] RAG Chat API（供諮商系統調用）

#### Phase 2: 諮商系統基礎（3 週）
- [ ] 使用者、來訪者、個案 CRUD
- [ ] JWT 認證
- [ ] 會談建立
- [ ] **雙輸入模式**：
  - 音訊上傳 + Whisper STT
  - 逐字稿直傳
- [ ] 異步任務處理（Job 系統）

#### Phase 3: 報告生成整合（2 週）
- [ ] 報告生成服務：
  - 調用 RAG Agent API
  - GPT-4 結合檢索結果
  - 結構化輸出（含引用）
- [ ] 報告審核流程
- [ ] Web 前台展示報告

#### Phase 4: 進階功能（3 週）
- [ ] 脫敏處理
- [ ] 提醒系統
- [ ] 集合管理（RAG）
- [ ] Pipeline 可視化

#### Phase 5: 優化與上線（2 週）
- [ ] 性能優化
- [ ] 安全加固（加密、RLS）
- [ ] 測試與文檔
- [ ] 正式部署

**總計：12 週（約 3 個月）**

---

## 第六部分：風險與緩解

### 技術風險

**AI API 成本**
- 緩解：使用量上限、結果快取、嵌入去重

**音訊處理延遲**
- 緩解：異步處理、進度回報、分段處理

**向量檢索準確率**
- 緩解：混合檢索（關鍵字+語意）、調整 Top-K

**兩條業務線耦合**
- 緩解：嚴格 API 邊界、禁止跨資料庫查詢

### 業務風險

**法規合規**
- 緩解：諮詢法務、建立合規檢核表

**理論引用錯誤**
- 緩解：人工審核、引用來源驗證

**使用者採用**
- 緩解：漸進推出、教育訓練

### 運維風險

**資料遺失**
- 緩解：定期備份、災難復原計畫

**服務中斷**
- 緩解：健康檢查、自動擴展

---

## 附錄

### A. 環境變數規範

```bash
# 僅放 Secrets/Keys
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=eyJ...
SECRET_KEY=your-secret-key
```

### B. 資料庫遷移

**諮商系統表**（需新建）：
- users, visitors, cases, sessions, jobs, reports, reminders

**RAG 系統表**（已存在）：
- agents, agent_versions, datasources, documents, chunks, embeddings
- collections, collection_items, pipeline_runs, chat_logs

**執行方式**：
- 手動 SQL 遷移：`app/models/migrations/*.sql`
- 在 Supabase SQL Editor 執行

### C. 參考資源

- [FastAPI 文件](https://fastapi.tiangolo.com/)
- [OpenAI API](https://platform.openai.com/docs)
- [pgvector](https://github.com/pgvector/pgvector)
- [Supabase Storage](https://supabase.com/docs/guides/storage)
- [Cloud Run 最佳實踐](https://cloud.google.com/run/docs/bestpractices)

---

**版本**: v2.0 (雙業務線架構)
**最後更新**: 2025-10-03