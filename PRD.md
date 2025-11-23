# 職涯諮詢平台 PRD

## 系統概述

### 核心架構
本系統採用**雙業務線獨立架構**：

1. **RAG Ops 生產線**（管理層）
   - 建立 AI 能力：上傳文件 → 向量化 → 建立 Agent
   - 內部使用：`/rag/*` (Next.js Console)

2. **諮商應用線**（業務層）
   - 提供諮商服務：音訊/逐字稿 → RAG Agent → 生成報告
   - 對外服務：`/api/v1/*` (iOS + API)

### 技術棧
- **後端**: Python 3.11 + FastAPI + SQLAlchemy 2.0
- **資料庫**: PostgreSQL 15 + pgvector (Supabase 託管)
- **AI**: OpenAI GPT-4 + text-embedding-3-small
- **部署**: Docker + Google Cloud Run
- **測試**: pytest + Ruff + Mypy

---

## 當前可用功能 (2025-11-24)

### ✅ 認證系統
- `POST /api/auth/login` - JWT 登入（24h 有效期）
- `GET /api/auth/me` - 取得諮商師資訊
- `PATCH /api/auth/me` - 更新諮商師資訊
- **特色**: 多租戶隔離（tenant_id）、bcrypt 密碼加密

### ✅ 客戶管理 (`/api/v1/clients/*`)
- 完整 CRUD：建立、列表、詳情、更新、刪除
- 分頁搜尋：支援 skip/limit + 姓名/代碼搜尋
- 自動生成：客戶代碼（C0001, C0002...）
- **權限隔離**: 諮商師只能訪問自己的客戶

### ✅ 案件管理 (`/api/v1/cases/*`)
- 完整 CRUD + 案件編號自動生成（CASE-20251124-001）
- 案件狀態：未開始(0) / 進行中(1) / 已結案(2)
- 關聯查詢：案件關聯客戶資訊

### ✅ 會談管理 (`/api/v1/sessions/*`)
- 建立會談記錄：逐字稿 + 錄音片段列表
- 會談歷程時間線：`GET /sessions/timeline?client_id={id}`
- 諮商師反思：4 問題結構化反思（JSONB）
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

### ✅ Web 測試控制台 (`/console`)
- 整合式 API 測試介面（包含所有 API）
- RWD 設計：支援手機 + 平板 + 桌面
- 手機模擬圖：iOS UI 預覽

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

### 諮商系統
- **counselors**: 諮商師（tenant_id, role, email, password_hash）
- **clients**: 客戶（counselor_id, name, age, gender, code [自動生成]）
- **cases**: 案件（client_id, case_number [自動], status [0/1/2]）
- **sessions**: 會談（case_id, transcript_text, recordings [JSONB], reflection [JSONB]）
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
| GET | `/auth/me` | 取得諮商師資訊 |
| PATCH | `/auth/me` | 更新諮商師資訊 |

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

### RAG 系統 (`/api/rag/*`)
- `/rag/agents` - Agent 管理
- `/rag/ingest/*` - 文件上傳
- `/rag/search` - 向量檢索
- `/rag/chat` - RAG 問答（**諮商系統調用**）
- `/rag/experiments/*` - 評估系統

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
- ✅ 諮商師反思系統

**待完成**:
- [ ] 音訊上傳 + Whisper STT
- [ ] 逐字稿脫敏串接
- [ ] 督導審核流程

### Phase 4: 進階功能（未開始）
- 提醒系統
- 集合管理（RAG）
- Pipeline 可視化
- RAG 評估系統優化

### Phase 5: 優化與上線（未開始）
- 性能優化
- 安全加固
- 測試與文檔
- 正式部署

---

## 關鍵技術決策

### 1. 資料庫連線 SSL 配置
**日期**: 2025-11-24
**問題**: Cloud Run migration 執行失敗（SSL connection closed unexpectedly）
**解決**: 在 `database.py` 和 `alembic/env.py` 加入 `connect_args={"sslmode": "require"}`

### 2. Mypy 類型檢查策略
**日期**: 2025-11-24
**決策**: 保持傳統 `Column()` 定義，在 `pyproject.toml` 抑制 `var-annotated` 錯誤
**原因**: SQLAlchemy 2.0 新版 `Mapped[]` 註解導致執行時錯誤

### 3. 測試資料庫配置
**決策**: Integration tests 使用 SQLite + `StaticPool`
**原因**: 確保 FastAPI TestClient 跨執行緒共享連線

### 4. API 架構設計
**決策**: 分離 RESTful API (`/api/v1/*`) 和 UI 整合 API (`/api/v1/ui/*`)
**原因**: iOS 需要高階 API 減少網路往返，Web 測試需要細粒度 API

---

## 部署狀態

**Cloud Run 服務**:
- 當前版本: `career-app-api-staging-00077-dmt`
- 健康狀態: ✅ Healthy
- CI/CD: ✅ All tests passing (unit + integration)
- GCP Project: `career-ios-app`
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

---

## 近期更新（2025-11-24）

### 已完成
1. ✅ 修復 SSL 連線問題（Supabase Pooler）
2. ✅ 清理冗餘 HTML 路由（只保留 `/console`）
3. ✅ 增強 OpenAPI 文檔（詳細 summary + description）
4. ✅ 更新 TODO 註解（SanitizerService 已實作）
5. ✅ CI/CD 優化（分離 unit/integration tests）
6. ✅ Console RWD 改進（支援手機 + 平板）

### 本週進度（2025-11-23 ~ 2025-11-24）
- 96 commits
- 主要工作：SSL 修復、API 清理、文檔更新、測試優化

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

- **API 文檔**: `https://<cloud-run-url>/docs` (Swagger UI)
- **ReDoc**: `https://<cloud-run-url>/redoc`
- **iOS 快速指南**: `IOS_API_GUIDE.md`
- **多租戶架構**: `MULTI_TENANT_ARCHITECTURE.md`
- **專案規範**: `CLAUDE.md` (Git workflow, TDD 原則)

---

**版本**: v2.3 (精簡版)
**最後更新**: 2025-11-24
**行數**: < 500 行
