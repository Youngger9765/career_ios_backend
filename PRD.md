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

**簡化的單一步驟流程**（推薦）：

```
諮商師操作流程：
1. 在 iOS 進行會談並錄音
2. iOS 本地將音訊轉成逐字稿（前端處理）
3. iOS 發送單一 API 請求

iOS 請求：
POST /api/v1/reports/generate
Body: {
  "client_id": "uuid",              # 個案 ID（事先建立好）
  "transcript": "案主：我最近...",   # 逐字稿內容
  "session_date": "2024-10-25",
  "report_type": "enhanced",        # legacy | enhanced
  "rag_system": "openai"            # openai | gemini
}

後端自動處理：
1. 建立 session 記錄（存逐字稿）
2. 調用 RAG Agent 檢索理論文獻
3. GPT-4 生成結構化報告
4. 存報告到 DB（狀態：draft）
5. 返回完整結果

Response: {
  "session_id": "uuid",
  "report_id": "uuid",
  "report": {
    "client_info": {...},
    "conceptualization": "...",
    "theories": [...],
    "dialogue_excerpts": [...]
  },
  "quality_summary": {...}
}

後續操作：
- 查看歷史：GET /api/v1/clients/{client_id}/sessions
- 重新生成：POST /api/v1/reports/generate (同一 client_id，不同 session_date)
- 督導審核：POST /api/v1/reports/{report_id}/review
```

**為什麼是單一步驟？**
- ✅ iOS 只需發一次請求
- ✅ 後端自動處理 session + report 建立
- ✅ 減少網路往返，降低失敗率
- ✅ 交易一致性（session 和 report 同時建立）
- ✅ 簡化前端邏輯

---

### 1.4 資料模型（諮商系統）

**設計原則**：
1. **簡化關係**：不需要 visitors/cases 分離，直接 counselor → client 關聯
2. **多租戶隔離**：所有表都有 `tenant_id`（即使資料庫分開）
3. **彈性存儲**：報告內容用 JSONB，支援職游/浮島不同格式
4. **版本控制**：同一 session 可生成多個報告版本

**諮商業務資料**（獨立於 RAG 系統）
```sql
-- 諮商師/老師（多租戶隔離）
counselors (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,                    -- "career_journey" | "floating_island"
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'counselor',     -- counselor | supervisor | admin
  metadata JSONB DEFAULT '{}',                -- 彈性欄位（專業證照、專長等）
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT counselors_email_tenant_unique UNIQUE (email, tenant_id)
);
CREATE INDEX idx_counselors_tenant ON counselors(tenant_id);

-- 個案/學生（簡化設計，不需要 visitors 表）
clients (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  counselor_id UUID NOT NULL REFERENCES counselors(id) ON DELETE CASCADE,
  name_alias TEXT NOT NULL,                   -- 化名
  background_info JSONB DEFAULT '{}',         -- 彈性存儲：年齡、性別、職業、教育等
  tags TEXT[] DEFAULT '{}',                   -- 標籤：["職涯迷茫", "轉職"]
  status TEXT DEFAULT 'active',               -- active | archived
  created_by_app TEXT NOT NULL,               -- "career_journey" | "floating_island"
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_clients_counselor ON clients(counselor_id, tenant_id);
CREATE INDEX idx_clients_tenant ON clients(tenant_id);

-- 會談 Session（一個案多次會談）
sessions (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  counselor_id UUID NOT NULL REFERENCES counselors(id) ON DELETE CASCADE,
  session_date DATE NOT NULL,
  session_number INTEGER,                     -- 第幾次會談（自動計算或手動設定）
  room TEXT,                                  -- 會談地點（可選）

  -- 輸入資料
  input_type TEXT NOT NULL,                   -- "audio" | "transcript"
  audio_path TEXT,                            -- Supabase Storage 路徑
  transcript_raw TEXT,                        -- 原始逐字稿
  transcript_sanitized TEXT,                  -- 脫敏後逐字稿

  -- 處理狀態
  processing_status TEXT DEFAULT 'pending',   -- pending | processing | completed | failed

  metadata JSONB DEFAULT '{}',                -- 其他資訊（錄音時長、檔案大小等）
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sessions_client ON sessions(client_id, tenant_id);
CREATE INDEX idx_sessions_counselor ON sessions(counselor_id, tenant_id);
CREATE INDEX idx_sessions_date ON sessions(session_date DESC);

-- 異步任務（音訊模式使用）
jobs (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  job_type TEXT NOT NULL,                     -- "stt" | "sanitize" | "report_generation"
  status TEXT DEFAULT 'queued',               -- queued | processing | completed | failed
  progress INTEGER DEFAULT 0,                 -- 0-100
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_jobs_session ON jobs(session_id, tenant_id);
CREATE INDEX idx_jobs_status ON jobs(status, tenant_id);

-- 報告（含版本控制、審核流程）
reports (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,      -- 冗餘但方便查詢
  counselor_id UUID NOT NULL REFERENCES counselors(id) ON DELETE CASCADE, -- 冗餘但方便查詢

  -- 版本控制
  report_version INTEGER NOT NULL DEFAULT 1,  -- 同一 session 可重新生成
  report_type TEXT NOT NULL,                  -- "legacy" | "enhanced" | 自定義格式

  -- 報告內容（JSONB 彈性存儲，支援不同格式）
  content JSONB NOT NULL,                     -- 報告主體內容
  citations JSONB DEFAULT '[]',               -- RAG 檢索的理論引用
  quality_metrics JSONB DEFAULT '{}',         -- 質量評分（可選）

  -- RAG Agent 資訊
  agent_id TEXT,                              -- 使用的 Agent ID（可選）

  -- 審核流程
  status TEXT DEFAULT 'draft',                -- draft | under_review | approved | rejected
  reviewed_by UUID REFERENCES counselors(id), -- 督導 ID
  reviewed_at TIMESTAMPTZ,
  review_comment TEXT,                        -- 審核意見

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT reports_session_version_unique UNIQUE (session_id, report_version)
);
CREATE INDEX idx_reports_session ON reports(session_id, tenant_id);
CREATE INDEX idx_reports_client ON reports(client_id, tenant_id);
CREATE INDEX idx_reports_counselor ON reports(counselor_id, tenant_id);
CREATE INDEX idx_reports_status ON reports(status, tenant_id);

-- 提醒（回訪、追蹤事項）
reminders (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  counselor_id UUID NOT NULL REFERENCES counselors(id) ON DELETE CASCADE,
  due_date DATE NOT NULL,
  content TEXT NOT NULL,
  status TEXT DEFAULT 'pending',              -- pending | completed | cancelled
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_reminders_counselor ON reminders(counselor_id, due_date);
CREATE INDEX idx_reminders_status ON reminders(status, tenant_id);
```

**報告內容 JSONB 格式範例**：

職游 Enhanced 格式：
```json
{
  "format": "enhanced",
  "version": "2.0",
  "sections": {
    "client_info": {...},
    "main_issue": "...",
    "problem_development": "...",
    "help_seeking_motivation": "...",
    "multilevel_analysis": "...",
    "strengths_resources": "...",
    "professional_judgment": "...",
    "goals_strategies": "...",
    "expected_outcomes": "...",
    "counselor_reflection": "..."
  },
  "theories_applied": ["Super生涯發展理論", "Holland類型論"],
  "metadata": {
    "word_count": 2500,
    "generation_time": "2024-10-25T10:30:00Z"
  }
}
```

浮島教育諮詢格式（完全不同結構）：
```json
{
  "format": "education_counseling",
  "version": "1.0",
  "sections": {
    "student_profile": {...},
    "academic_performance": "...",
    "learning_challenges": "...",
    "university_planning": [...],
    "parent_involvement": "...",
    "teacher_recommendations": "...",
    "next_steps": "..."
  },
  "metadata": {
    "target_universities": ["台大", "清大"],
    "exam_scores": {...},
    "extracurricular": [...]
  }
}
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

#### 個案管理（Clients）
- `GET /api/v1/clients` - 列出諮商師的所有個案
- `POST /api/v1/clients` - 建立新個案
  ```json
  Body: {
    "name_alias": "小明",
    "background_info": {
      "age": "28歲",
      "gender": "男性",
      "occupation": "軟體工程師"
    },
    "tags": ["職涯迷茫", "轉職"]
  }
  ```
- `GET /api/v1/clients/{id}` - 取得個案詳情
- `PUT /api/v1/clients/{id}` - 更新個案資料
- `DELETE /api/v1/clients/{id}` - 刪除/封存個案

#### 報告生成（核心 API）- 單一步驟
- `POST /api/v1/reports/generate` - **生成報告（自動建立 session + report）**
  ```json
  Body: {
    "client_id": "uuid",
    "transcript": "案主：我最近工作很不順...",
    "session_date": "2024-10-25",
    "report_type": "enhanced",
    "rag_system": "openai"
  }
  Response: {
    "session_id": "uuid",
    "report_id": "uuid",
    "report": {...},
    "quality_summary": {...}
  }
  ```

#### 會談與報告查詢
- `GET /api/v1/clients/{client_id}/sessions` - 列出個案的所有會談記錄
- `GET /api/v1/sessions/{id}` - 取得會談詳情（含逐字稿）
- `GET /api/v1/sessions/{session_id}/reports` - 列出會談的所有報告版本
- `GET /api/v1/reports/{id}` - 取得特定報告完整內容

#### 報告審核（督導功能）
- `POST /api/v1/reports/{id}/review` - 督導審核報告
  ```json
  Body: {
    "status": "approved",  // approved | rejected
    "review_comment": "分析深入，建議補充..."
  }
  ```
- `GET /api/v1/reports/pending-review` - 列出待審核的報告

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