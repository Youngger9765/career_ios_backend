# 職涯諮詢平台整合 PRD

> 整合版本：助人者 App 後端 + RAG Agent Ops Console

---

## 專案概覽

### 核心價值
提供一個完整的職涯諮詢平台，結合：
1. **諮商會談系統**：錄音 → 逐字稿 → AI 報告生成
2. **RAG 知識系統**：文件管理 → 向量檢索 → 理論引用

### 技術架構
- **後端**: FastAPI (Python 3.11+) 單體架構
- **資料庫**: PostgreSQL + pgvector (向量檢索)
- **儲存**: Supabase Storage / Google Cloud Storage
- **AI 服務**: OpenAI (Whisper STT, GPT-4, Embeddings)
- **部署**: Google Cloud Run + Docker

---

## 第一部分：諮商會談系統

### 1.1 產品背景與目標

**情境**：諮商師與個案在 iOS App 中對談，錄音後上傳處理

**核心流程**：
1. 會談錄音 → 上傳音訊檔
2. 語音轉文字 (STT) → 生成逐字稿
3. AI 分析逐字稿 → 產出個案報告
4. 督導審核 → 個案管理 → 追蹤提醒

### 1.2 主要功能

#### 帳號與權限
- 諮商師、督導、管理員角色
- JWT 認證系統

#### 個案管理
- 來訪者（Visitor）資料
- 個案（Case）關聯：諮商師 + 來訪者
- 會談（Session）紀錄

#### 錄音處理
- 音訊上傳 API
- 異步任務處理（Job 系統）
- OpenAI Whisper STT 轉逐字稿
- 脫敏處理（移除敏感資訊）

#### AI 報告生成
- 使用 GPT-4 分析逐字稿
- **整合 RAG 知識庫**：檢索理論框架、倫理規範
- 生成結構化報告：
  - 主訴問題
  - 成因分析（含理論引用）
  - 晤談目標
  - 介入策略
  - 成效評估
  - 關鍵對話摘錄

#### 報告審核
- 督導審核流程
- 狀態：草稿 / 通過 / 退回
- 版本歷史

#### 提醒與追蹤
- 回訪日期提醒
- 追蹤事項管理

### 1.3 資料模型（諮商系統）

```sql
-- 使用者與權限
users(id, name, email, role, created_at)

-- 來訪者與個案
visitors(id, name_alias, tags, created_at)
cases(id, counselor_id, visitor_id, status, created_at)

-- 會談與錄音
sessions(
  id, case_id, date, room,
  audio_path, transcript_path,
  created_at
)

-- 異步任務
jobs(
  id, session_id, type,  -- [audio|text]
  status,  -- [queued|processing|completed|failed]
  created_at
)

-- 報告
reports(
  id, case_id, session_id,
  version, content_json, status,
  created_at
)

-- 提醒
reminders(
  id, case_id, due_date,
  content, status, created_at
)
```

### 1.4 API 端點（諮商系統）

#### 認證
- `POST /auth/login`
- `POST /auth/refresh`

#### 使用者
- `GET /users/me`
- `PUT /users/me`

#### 來訪者與個案
- `GET /visitors`, `POST /visitors`
- `GET /cases`, `POST /cases`

#### 會談與錄音
- `POST /sessions`
- `POST /sessions/{id}/upload-audio`
- `GET /sessions/{id}/transcript`

#### 報告
- `GET /reports`
- `POST /reports/generate`
- `GET /reports/{id}`

#### 任務
- `GET /jobs/{id}` (查詢處理狀態)

---

## 第二部分：RAG Agent Ops Console

### 2.1 目標與邊界

**目的**：內部後台，管理 RAG 知識庫與 Agent

**核心功能**：
- Agent CRUD（版本管理）
- 文件上傳 → 切片 → 嵌入 → 入庫
- 語意檢索（向量相似度）
- Pipeline 可視化
- Prompt 設定 & 測試台

**邊界**：無登入版（內網/Admin-Key 限制）

### 2.2 成功指標（MVP）

1. **10 分鐘內**：建立 Agent → 上傳 PDF → 索引完成 → 測試台得到引用回覆
2. **處理失敗率** < 5%
3. **檢索延遲**（Top-K=5）< 300ms

### 2.3 頁面與流程

#### Agents 管理
- Agent CRUD（Name, Description, Slug）
- 版本管理（draft/published）
- 發佈 / 回滾

#### Upload（文件上傳）
- 支援：PDF / URL / 純文字
- Pipeline 執行：抽取 → 切片 → 嵌入 → 入庫
- 狀態追蹤

#### Documents / Collections
- 文件清單（標題、來源、頁數、集合）
- 集合 CRUD
- 重嵌入 / 刪除

#### File Search
- 關鍵字 + 語意檢索
- 過濾：集合、日期、來源
- 結果：snippet + 來源 + score

#### Pipelines（可視化）
- 狀態流：`QUEUED → EXTRACTING → CHUNKING → EMBEDDING → INDEXED → DONE/FAILED`
- 重跑機制
- 錯誤日誌

#### Prompts / Test Bench
- System Prompt 編輯（產生草稿版本）
- Agent Config：模型、溫度、Top-K、引用必須
- 測試台：問答 + 引用卡片

### 2.4 資料模型（RAG 系統）

```sql
-- Agent 管理
agents(
  id, slug, name, description,
  status, active_version_id,
  created_at, updated_at
)

agent_versions(
  id, agent_id, version, state,  -- [draft|published]
  config_json, created_at
)

-- 知識庫與向量
datasources(
  id, type,  -- [pdf|url|text]
  source_uri, created_at
)

documents(
  id, datasource_id, title,
  bytes, pages, meta_json, updated_at
)

chunks(
  id, doc_id, ordinal, text, meta_json
)

embeddings(
  id, chunk_id,
  embedding vector(1536)  -- OpenAI embeddings
)

collections(id, name, created_at)

collection_items(
  collection_id, doc_id, created_at
)

-- Pipeline 追蹤
pipeline_runs(
  id, scope,  -- [ingest|reembed]
  target_id, status, steps_json,
  started_at, ended_at, error_msg
)

-- 聊天日誌
chat_logs(
  id, agent_id, version_id,
  question, answer, citations_json,
  tokens_in, tokens_out, latency_ms,
  created_at
)
```

### 2.5 API 端點（RAG 系統）

#### Agents
- `GET /api/agents?status=&q=&page=`
- `POST /api/agents`
- `GET /api/agents/{id}/versions`
- `POST /api/agents/{id}/versions/{vid}/publish`

#### Upload & Ingest
- `POST /api/rag/ingest/files`（多檔上傳）
- `POST /api/rag/ingest/url`
- `POST /api/rag/ingest/text`

#### Documents & Collections
- `GET /api/documents?collection_id=`
- `POST /api/documents/{id}/reembed`
- `DELETE /api/documents/{id}`
- `GET /api/collections`
- `POST /api/collections/{id}/add`（加入文件）

#### Search & Chat
- `POST /api/rag/search` → 向量檢索
- `POST /api/rag/chat` → RAG 問答（含引用）

#### Pipelines
- `GET /api/pipelines/runs?target_id=`
- `POST /api/pipelines/runs/{id}/retry`

#### Stats & Report
- `GET /api/rag/stats` → 統計資料
- `GET /api/report/generate` → 個案報告生成（SSE 串流）

---

## 第三部分：整合架構

### 3.1 系統整合點

#### RAG 知識庫 → 報告生成
1. 諮商師上傳理論文獻至 RAG 系統
2. 報告生成時，使用逐字稿檢索相關理論
3. AI 結合檢索結果生成專業報告（含引用）

#### 共用服務
- **OpenAI Service**：STT、Embeddings、GPT-4
- **Storage Service**：音訊、PDF、報告統一存儲
- **Database**：PostgreSQL + pgvector

#### 前端整合
- 主 API：`/api/v1/*` (諮商系統)
- RAG Console：`/rag/*` (Next.js 靜態輸出)
- RAG API：`/api/rag/*`

### 3.2 部署架構

```
┌─────────────────────────────────────┐
│      Google Cloud Run (Single)      │
├─────────────────────────────────────┤
│  FastAPI Backend                    │
│  ├─ /api/v1/*  (諮商 API)           │
│  ├─ /api/rag/* (RAG API)            │
│  └─ /rag/*     (Next.js Static)     │
├─────────────────────────────────────┤
│  PostgreSQL + pgvector (Supabase)   │
│  Supabase Storage (文件/音訊)       │
│  OpenAI API (STT/GPT-4/Embeddings)  │
└─────────────────────────────────────┘
```

### 3.3 技術選型總覽

**後端框架**
- FastAPI (Python 3.11+)
- SQLAlchemy ORM
- Pydantic (資料驗證)

**資料庫**
- PostgreSQL 15 + pgvector
- Supabase (託管服務)

**前端**
- Next.js 14 (App Router, Static Export)
- TypeScript + Tailwind CSS

**AI 服務**
- OpenAI Whisper API (STT)
- GPT-4 / GPT-4o-mini (報告生成)
- text-embedding-3-small (向量嵌入)

**儲存**
- Supabase Storage (主要)
- Google Cloud Storage (備選)

**部署與 CI/CD**
- Docker (Multi-stage build)
- Google Cloud Run
- GitHub Actions

---

## 第四部分：開發規劃

### 4.1 MVP 範圍劃分

#### Phase 1: 基礎設施（2 週）
- [ ] 專案架構搭建
- [ ] 資料庫設計與遷移
- [ ] Docker + Cloud Run 部署
- [ ] JWT 認證系統

#### Phase 2: 諮商核心功能（4 週）
- [ ] 使用者、來訪者、個案 CRUD
- [ ] 會談錄音上傳
- [ ] Whisper STT 整合
- [ ] 異步任務處理（Job 系統）

#### Phase 3: RAG 知識系統（4 週）
- [ ] 文件上傳（PDF/URL/Text）
- [ ] 文字抽取 & 智能切片
- [ ] OpenAI Embeddings 嵌入
- [ ] pgvector 向量檢索
- [ ] Pipeline 可視化

#### Phase 4: AI 報告生成（3 週）
- [ ] RAG 檢索整合
- [ ] GPT-4 報告生成
- [ ] 結構化輸出（含引用）
- [ ] SSE 串流進度回報

#### Phase 5: 進階功能（3 週）
- [ ] 報告審核流程
- [ ] 提醒系統
- [ ] Agent 版本管理
- [ ] Test Bench 測試台

#### Phase 6: 優化與上線（2 週）
- [ ] 性能優化
- [ ] 安全加固（加密、RLS）
- [ ] 測試與文檔
- [ ] 正式部署

**總計：18 週（約 4.5 個月）**

### 4.2 成功指標

#### 技術指標
- API 回應時間 < 200ms (P95)
- STT 準確率 > 95%
- 向量檢索延遲 < 300ms
- 系統可用性 > 99.9%

#### 業務指標
- 報告生成時間 < 5 分鐘
- 理論引用準確率 > 90%
- 諮商師採用率 > 80%
- 使用者滿意度 > 4.5/5

---

## 第五部分：風險與緩解

### 5.1 技術風險

**AI API 成本**
- 緩解：使用量上限、結果快取、嵌入去重

**音訊處理延遲**
- 緩解：異步處理、進度回報、分段處理

**向量檢索準確率**
- 緩解：混合檢索（關鍵字+語意）、調整 Top-K

### 5.2 業務風險

**資料隱私合規**
- 緩解：端對端加密、脫敏處理、審計日誌

**理論引用錯誤**
- 緩解：人工審核、引用來源驗證、版本控制

**使用者採用**
- 緩解：漸進推出、教育訓練、快速迭代

### 5.3 運維風險

**資料遺失**
- 緩解：定期備份、災難復原計畫

**服務中斷**
- 緩解：多區域部署、健康檢查、自動擴展

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

- `app/models/migrations/001_add_rag_tables.sql`
- `app/models/migrations/002_complete_rag_schema.sql`
- 手動執行於 Supabase SQL Editor

### C. 參考資源

- [FastAPI 文件](https://fastapi.tiangolo.com/)
- [OpenAI API](https://platform.openai.com/docs)
- [pgvector](https://github.com/pgvector/pgvector)
- [Supabase Storage](https://supabase.com/docs/guides/storage)
- [Cloud Run 最佳實踐](https://cloud.google.com/run/docs/bestpractices)

---

**版本**: v1.0 (整合版)
**最後更新**: 2025-10-03
