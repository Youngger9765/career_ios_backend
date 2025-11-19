# 職涯諮詢平台 API

FastAPI 後端服務，支援 iOS App 的職涯諮詢功能，整合 RAG Agent 智能報告生成。

## ✨ 核心功能

### 雙業務線架構
1. **諮商應用線** - 個案管理、會談記錄、智能報告生成
2. **RAG Ops 線** - AI Agent 管理、知識庫維護、向量搜尋

### 關鍵特性
- 🏢 **多租戶架構** - JWT 認證 + 租戶隔離，支援多組織使用
- 🎨 **動態欄位配置** - 租戶級別自訂 Client/Case 欄位
- 📋 **客戶與個案管理** - 完整 CRUD + 自動編號生成
- 🎤 **雙輸入模式** - 支援音訊上傳（STT）或直接逐字稿
- 🤖 **AI 報告生成** - RAG Agent + GPT-4 自動生成專業報告
- 🔒 **文字脫敏** - 自動識別並脫敏 6 種敏感資料
- 📝 **報告審核** - 完整的審核與版本控制流程
- 🗄️ **Migration 自動化** - Alembic 自動同步資料庫

## 🚀 快速開始

### 環境需求
- Python 3.10+
- Poetry
- Supabase 帳號（或 PostgreSQL 15+）

### 安裝步驟

```bash
# 1. 安裝依賴
poetry install

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env，填入資料庫連線和 API keys

# 3. 執行 Database Migration
make db-auto
# 或
alembic upgrade head

# 4. 啟動開發伺服器
make dev
# 或
poetry run uvicorn app.main:app --reload
```

### 使用 Mock 模式開發

```bash
# 啟用 Mock 資料（不需要真實資料庫）
MOCK_MODE=true poetry run uvicorn app.main:app --reload
```

## 📚 API 文件

啟動後訪問：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **RAG Ops Console**: http://localhost:8000/rag
- **諮商前台**: http://localhost:8000/console

詳細文件：
- **[Client & Case Management API](API_CLIENT_CASE_MANAGEMENT.md)** - 客戶與個案管理完整文件
- **[iOS API Guide](IOS_API_GUIDE.md)** - iOS 開發完整指南
- **[Report Edit API](docs/API_REPORT_EDIT.md)** - 報告編輯 API 說明
- **[iOS API Simple](docs/iOS_API_SIMPLE.md)** - iOS 開發快速上手

## 🗄️ Database Migration

### 自動化管理（推薦）

```bash
# 檢查資料庫狀態
make db-check

# 完全自動化（生成 + 執行 migration）
make db-auto

# 手動操作
make db-generate    # 從 models 生成 migration
make db-upgrade     # 執行 migration
```

### Alembic 命令

```bash
# 生成 migration（自動偵測 models 變更）
alembic revision --autogenerate -m "描述訊息"

# 執行 migration
alembic upgrade head

# 檢查當前版本
alembic current

# 回滾
alembic downgrade -1
```

**詳細文件**: 參考 `DATABASE_MIGRATION.md`

## 📁 專案結構

```
career_ios_backend/
├── app/
│   ├── api/                # API endpoints（17 個路由）
│   │   ├── sessions.py    # 會談管理（雙輸入模式）
│   │   ├── reports.py     # 報告生成與審核
│   │   ├── rag_*.py      # RAG 相關 APIs
│   │   └── ...
│   │
│   ├── models/            # SQLAlchemy Models（17 個）
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── report.py
│   │   ├── agent.py
│   │   └── ...
│   │
│   ├── services/          # 服務層（10 個）
│   │   ├── stt_service.py        # Speech-to-Text
│   │   ├── sanitizer_service.py  # 文字脫敏
│   │   ├── report_service.py     # 報告生成（RAG）
│   │   └── ...
│   │
│   ├── templates/         # FastAPI Templates
│   │   ├── rag/          # RAG Ops Console
│   │   └── console/      # 諮商前台
│   │
│   └── core/
│       ├── config.py
│       └── database.py
│
├── alembic/               # Database Migrations
│   ├── env.py            # 自動載入所有 models
│   └── versions/
│
├── scripts/
│   └── manage_db.py      # 資料庫管理自動化腳本
│
├── tests/
│   ├── test_cases.py     # API 測試（27 cases）
│   ├── test_services.py  # Service 測試
│   └── rag/              # RAG 相關測試
│
└── docs/
    ├── PRD.md                        # 產品需求文件
    ├── DATABASE_MIGRATION.md         # Migration 指南
    ├── SETUP_COMPLETE.md             # 設置完成總結
    └── ...
```

## 🧪 測試

```bash
# 執行所有測試
make test

# API 測試
make test-api

# Service 測試
make test-service

# 測試覆蓋率
poetry run pytest --cov=app --cov-report=html
```

## 🔑 環境變數

**必要設定**（`.env`）:

```bash
# Database（Supabase）
DATABASE_URL=postgresql://...
DATABASE_URL_DIRECT=postgresql://...  # 用於 migration

# Security
SECRET_KEY=your-super-secret-key

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Supabase
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
```

## 📋 Makefile 指令

### Database
```bash
make db-check      # 檢查資料庫狀態
make db-auto       # 🚀 自動生成並執行 migration
make db-generate   # 生成 migration
make db-upgrade    # 執行 migration
make db-reset      # 重置 Alembic
```

### Development
```bash
make install       # 安裝依賴
make dev          # 開發模式（Mock）
make run          # 生產模式
```

### Testing
```bash
make test         # 所有測試
make test-api     # API 測試
make test-service # Service 測試
```

### Code Quality
```bash
make format       # 格式化程式碼
make lint         # 程式碼檢查
make clean        # 清理快取
```

## 🐳 Docker

```bash
# 建置 Docker image
make docker-build
# 或
docker build -t career-backend .

# 執行容器
docker run -p 8000:8000 --env-file .env career-backend
```

## 🔄 開發工作流程

### 1. 修改 Model 並同步資料庫

```bash
# 1. 編輯 Model
vim app/models/user.py

# 2. 自動生成並執行 migration
make db-auto

# 3. 完成！資料庫已更新
```

### 2. 開發新功能

```bash
# 1. 創建 API endpoint
vim app/api/example.py

# 2. 編寫測試
vim tests/test_example.py

# 3. 執行測試
make test-api

# 4. 提交代碼
git add . && git commit -m "feat: add example endpoint"
```

## 📖 核心 API

### 🔐 認證與多租戶
所有 API 請求需包含 JWT Token：
```http
Authorization: Bearer <token>
```
系統自動從 JWT 提取 `tenant_id`，實現租戶隔離。

### 👥 客戶與個案管理 API（`/api/v1`）

#### Field Schemas（動態欄位配置）
- `GET /api/v1/field-schemas/client` - 取得 Client 欄位配置
- `GET /api/v1/field-schemas/case` - 取得 Case 欄位配置

#### Clients（客戶管理）
- `GET /api/v1/clients` - 列出客戶（分頁）
- `POST /api/v1/clients` - 建立客戶（自動生成編號 C0001）
- `GET /api/v1/clients/{id}` - 查看客戶
- `PATCH /api/v1/clients/{id}` - 更新客戶
- `DELETE /api/v1/clients/{id}` - 刪除客戶

#### Cases（個案管理）
- `GET /api/v1/cases` - 列出個案（支援 client_id 過濾）
- `POST /api/v1/cases` - 建立個案（自動生成編號 CASE0001）
- `GET /api/v1/cases/{id}` - 查看個案
- `PATCH /api/v1/cases/{id}` - 更新個案
- `DELETE /api/v1/cases/{id}` - 刪除個案

**詳細說明**: 參考 [Client & Case Management API 文件](API_CLIENT_CASE_MANAGEMENT.md)

### 📝 Sessions & Reports（會談與報告）

#### Sessions（會談管理）
- `POST /sessions/{id}/upload-audio` - 上傳音訊（Mode 1）
- `POST /sessions/{id}/upload-transcript` - 上傳逐字稿（Mode 2）
- `GET /sessions/{id}/transcript` - 取得逐字稿

#### Reports（報告管理）
- `POST /reports/generate` - 生成 AI 報告
- `PATCH /reports/{id}/review` - 審核報告（approve/reject）
- `GET /reports/{id}/download` - 下載報告

### 🤖 RAG API（`/api/rag`）

- `POST /api/rag/ingest` - 上傳知識文件
- `POST /api/rag/search` - 向量搜尋
- `POST /api/rag/chat` - RAG Agent 對話
- `GET /api/rag/agents` - Agent 管理

## 🎯 系統特色

### 1. 雙輸入模式

**Mode 1: 音訊上傳 + STT**
```
iOS App → 上傳音訊 → OpenAI Whisper → 逐字稿 → 脫敏 → 報告生成
```

**Mode 2: 直接上傳逐字稿**
```
iOS App → 已處理逐字稿 → 脫敏 → 報告生成
```

### 2. AI 報告生成流程

```
逐字稿 → RAG Agent 檢索理論 → GPT-4 生成結構化報告
       ↓
   content_json（主訴、分析、建議）+ citations_json（理論引用）
```

### 3. 文字脫敏（6 種敏感資料）

- 身分證：`A123456789` → `[身分證]`
- 手機：`0912345678` → `[電話]`
- Email：`test@example.com` → `[電子郵件]`
- 信用卡：`1234 5678 9012 3456` → `[信用卡]`
- 地址：`台北市100號` → `台北市[地址]`
- 市話：`02-12345678` → `[電話]`

## 📊 資料庫架構

### 諮商系統（9 個表）
- `counselors` - 諮商師（JWT 認證）
- `clients` - 客戶（支援動態欄位）
- `cases` - 個案（自動生成編號）
- `sessions` - 會談
- `reports` - 報告
- `field_schemas` - 動態欄位配置（租戶級別）
- `tenants` - 租戶（多租戶隔離）
- `jobs` - 異步任務
- `reminders` - 提醒事項

### RAG 系統（10 個表）
- `agents` - AI Agent
- `agent_versions` - Agent 版本
- `documents` - 文件
- `chunks` - 文本片段
- `embeddings` - 向量嵌入
- `datasources` - 資料來源
- `collections` - 文件集合
- `collection_items` - 集合項目
- `chat_logs` - 對話記錄
- `pipeline_runs` - Pipeline 執行記錄

**Migration 版本**: `d90dfbb1ef85`

## 🔗 相關資源

- **Supabase Dashboard**: https://supabase.com/dashboard/project/ehvgueyrxpvkleqidkdu
- **文件目錄**: `/docs`
- **完整設置說明**: `SETUP_COMPLETE.md`
- **Migration 指南**: `DATABASE_MIGRATION.md`
- **測試總結**: `tests/TESTING_SUMMARY.md`

## 🐛 已知問題

1. **Mock 資料欄位不匹配** - 部分測試失敗，需調整 mock generator（預計 15 分鐘修復）
2. **UUID 驗證** - 測試資料需使用 UUID 格式（預計 10 分鐘修復）

## 📝 授權

MIT License

## 👥 團隊

Career Counseling Platform Development Team

---

**快速上手**: 執行 `make db-auto && make dev` 即可開始開發！ 🚀
