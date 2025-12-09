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
- **AI**: OpenAI GPT-4 + text-embedding-3-small
- **部署**: Docker + Google Cloud Run
- **測試**: pytest + Ruff + Mypy

---

## 當前可用功能 (2025-11-29)

### ✅ 認證系統
- `POST /api/auth/login` - JWT 登入（24h 有效期）
- `GET /api/auth/me` - 取得諮詢師資訊
- `PATCH /api/auth/me` - 更新諮詢師資訊
- **特色**: 多租戶隔離（tenant_id）、bcrypt 密碼加密

### ✅ 客戶管理 (`/api/v1/clients/*`)
- 完整 CRUD：建立、列表、詳情、更新、刪除
- 分頁搜尋：支援 skip/limit + 姓名/代碼搜尋
- 自動生成：客戶代碼（C0001, C0002...）
- **權限隔離**: 諮詢師只能訪問自己的客戶

### ✅ 案件管理 (`/api/v1/cases/*`)
- 完整 CRUD + 案件編號自動生成（CASE-20251124-001）
- 案件狀態：未開始(0) / 進行中(1) / 已結案(2)
- 關聯查詢：案件關聯客戶資訊

### ✅ 會談管理 (`/api/v1/sessions/*`)
- 建立會談記錄：逐字稿 + 錄音片段列表 + 會談名稱（name）
- 會談歷程時間線：`GET /sessions/timeline?client_id={id}`
- 諮詢師反思：4 問題結構化反思（JSONB）
- **🔍 即時關鍵字分析**: `POST /sessions/{id}/analyze-keywords` - AI 驅動的關鍵字提取
- **📊 分析歷程記錄**: `GET /sessions/{id}/analysis-logs` - 查看所有分析記錄
- **🗑️ 管理分析記錄**: `DELETE /sessions/{id}/analysis-logs/{log_index}` - 刪除特定記錄
- **iOS 專用**: `POST /sessions/{id}/recordings/append` - 追加錄音片段

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

### ✅ 即時語音諮詢系統 (Realtime STT Counseling)
**功能定位**: AI 輔助即時諮詢督導系統

#### 核心功能
- ✅ **即時語音轉文字 (STT)**
  - ElevenLabs Scribe v2 Realtime API
  - 中文繁體支援（language_code: `zh`）
  - < 100ms 低延遲
  - 手動說話者切換（諮詢師/案主）
- ✅ **AI 即時分析**
  - Gemini 2.5 Flash 驅動（Implicit Caching 優化）
  - 每 60 秒自動分析對話內容
  - 提供：對話歸納、提醒事項、建議回應
  - Cache 效能追蹤：usage_metadata 記錄（cached tokens, prompt tokens, output tokens）
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
| POST | `/api/v1/realtime/analyze` | AI 分析逐字稿（每 60 秒） |

**技術選型**: ElevenLabs STT ($0.46/h) + Gemini Flash + Vanilla JS | 7種理論標籤（依附、正向教養、發展心理、家庭系統、認知行為、情緒教練、綜合）

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
| POST | `/sessions/{id}/analyze-keywords` | 🔍 即時關鍵字分析 |
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

## 關鍵技術決策

### 基礎架構決策（2025-11-24）
1. **資料庫 SSL**: Supabase 需 `sslmode=require`
2. **Mypy 策略**: 保持傳統 `Column()` 定義
3. **測試 DB**: SQLite + StaticPool（跨執行緒共享）
4. **API 架構**: 分離 RESTful (`/api/v1/*`) 和 UI (`/api/v1/ui/*`)

### Realtime STT 技術選型（2025-12-06）
**決策**: ElevenLabs Scribe v2（$0.46/h）vs AssemblyAI（不支援中文）vs Google Chirp 3（貴5倍）
**教訓**: 第三方 API 必須先讀官方文檔（語言代碼：`cmn`→`zho`→`zh`）

### RAG 理論標籤系統（2025-12-09）
**決策**: 7種教養理論標籤 + Color-coded badges | **價值**: AI建議可追溯理論框架

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

## 近期更新（2025-12-09）

### 本週完成（2025-12-08~09）🎉
1. **Realtime STT Counseling** - 本專案最複雜功能（STT + AI分析 + RAG理論標籤 + 超時保護）2週開發
2. **RAG 理論標籤** - 7種教養理論 Color-coded badges，提升專業性與可追溯性
3. **法規遵循** - 諮商→諮詢（35+檔案），符合台灣心理師法
4. **Migration修復** - No-op migration恢復Staging
5. **API文檔規範** - CLAUDE.md新增第三方API整合規則

**累積數據**: 31+ API | 106 tests (100%通過) | 12,000+行 | 12模組

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

---

**版本**: v2.5
**最後更新**: 2025-12-09
**本次更新**: 新增 Realtime STT Counseling 系統、RAG 理論標籤、法規遵循
