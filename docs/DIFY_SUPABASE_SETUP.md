# Dify + Supabase 完整啟動文件

## 📋 目錄

- [系統需求](#系統需求)
- [架構說明](#架構說明)
- [步驟 1: 準備 Supabase](#步驟-1-準備-supabase)
- [步驟 2: 安裝 Dify](#步驟-2-安裝-dify)
- [步驟 3: 設定環境變數](#步驟-3-設定環境變數)
- [步驟 4: 啟動服務](#步驟-4-啟動服務)
- [步驟 5: 建立 RAG 應用](#步驟-5-建立-rag-應用)
- [常見問題排解](#常見問題排解)

---

## 系統需求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- Supabase 帳號
- OpenAI API Key

---

## 架構說明

```
┌─────────────────────────────────────────────────────────┐
│                    Dify 架構                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐      ┌──────────────┐               │
│  │   Web UI     │      │   API Server │               │
│  │  (Next.js)   │◄─────┤  (Python)    │               │
│  └──────────────┘      └──────────────┘               │
│         │                      │                        │
│         │                      │                        │
│         ▼                      ▼                        │
│  ┌──────────────┐      ┌──────────────┐               │
│  │   Nginx      │      │   Celery     │               │
│  │  (Reverse    │      │  (Worker)    │               │
│  │   Proxy)     │      └──────────────┘               │
│  └──────────────┘              │                        │
│         │                      │                        │
│         └──────────────────────┴────────────┐          │
│                                              ▼          │
│                                    ┌──────────────┐    │
│                                    │   Supabase   │    │
│                                    │  PostgreSQL  │    │
│                                    │   pgvector   │    │
│                                    └──────────────┘    │
│                                              │          │
│                                              ▼          │
│                                    ┌──────────────┐    │
│                                    │   OpenAI     │    │
│                                    │  Embeddings  │    │
│                                    └──────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**說明**：
- **Web UI**: 前端介面（知識庫管理、應用建立）
- **API Server**: 後端 API（處理文件上傳、RAG 查詢）
- **Celery Worker**: 非同步任務（文件處理、embedding 生成）
- **Supabase**: 儲存所有資料（文件、chunks、embeddings）
- **OpenAI**: 生成 embeddings 和回答

---

## 步驟 1: 準備 Supabase

### 1.1 建立 Supabase 專案

1. 前往 https://supabase.com
2. 點擊「Start your project」
3. 建立新組織 (Organization)
4. 建立新專案：
   - **Name**: `dify-rag`
   - **Database Password**: 設定強密碼（記下來）
   - **Region**: `Southeast Asia (Singapore)`
   - **Pricing Plan**: Free（開始時使用）

5. 等待專案建立（約 2 分鐘）

---

### 1.2 啟用 pgvector 擴充功能

1. 在 Supabase Dashboard，左側選單 → **SQL Editor**
2. 點擊「New query」
3. 執行以下 SQL：

```sql
-- 啟用 pgvector 擴充功能
CREATE EXTENSION IF NOT EXISTS vector;

-- 驗證安裝
SELECT * FROM pg_extension WHERE extname = 'vector';
```

4. 點擊「Run」，應該會看到成功訊息

---

### 1.3 建立資料庫結構

執行以下 SQL 建立 Dify 所需的表格：

```sql
-- Dify 資料庫架構

-- 1. 知識庫 (Datasets)
CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    provider VARCHAR(255) DEFAULT 'vendor',
    permission VARCHAR(255) DEFAULT 'only_me',
    data_source_type VARCHAR(255),
    indexing_technique VARCHAR(255) DEFAULT 'high_quality',
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 文件 (Documents)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    data_source_type VARCHAR(255) NOT NULL,
    data_source_info JSONB,
    dataset_process_rule_id UUID,
    batch VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_from VARCHAR(255) NOT NULL,
    created_by UUID NOT NULL,
    created_api_request_id UUID,
    processing_started_at TIMESTAMP,
    parsing_completed_at TIMESTAMP,
    cleaning_completed_at TIMESTAMP,
    splitting_completed_at TIMESTAMP,
    tokens INTEGER DEFAULT 0,
    indexing_status VARCHAR(255) DEFAULT 'waiting',
    error TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    disabled_at TIMESTAMP,
    disabled_by UUID,
    archived BOOLEAN DEFAULT FALSE,
    archived_reason TEXT,
    archived_by UUID,
    archived_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 文件段落 (Document Segments)
CREATE TABLE IF NOT EXISTS document_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    tokens INTEGER NOT NULL,
    keywords JSONB,
    index_node_id VARCHAR(255),
    index_node_hash VARCHAR(255),
    hit_count INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    disabled_at TIMESTAMP,
    disabled_by UUID,
    status VARCHAR(255) DEFAULT 'waiting',
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    indexing_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    stopped_at TIMESTAMP,
    updated_by UUID,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Embeddings (使用 pgvector)
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    hash VARCHAR(255) NOT NULL,
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 建立索引 (提升查詢效能)
CREATE INDEX IF NOT EXISTS idx_datasets_tenant_id ON datasets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_dataset_id ON documents(dataset_id);
CREATE INDEX IF NOT EXISTS idx_document_segments_document_id ON document_segments(document_id);
CREATE INDEX IF NOT EXISTS idx_document_segments_dataset_id ON document_segments(dataset_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_hash ON embeddings(hash);

-- 6. 建立向量索引 (使用 HNSW 算法，適合高維向量搜尋)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
ON embeddings
USING hnsw (embedding vector_cosine_ops);

-- 7. 建立 RLS (Row Level Security) - 可選
-- ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE document_segments ENABLE ROW LEVEL SECURITY;
```

---

### 1.4 取得連線資訊

1. Supabase Dashboard → **Settings** → **Database**
2. 複製以下資訊：

```bash
# Connection String (Session mode)
postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# 或者分開記錄：
Host: aws-0-ap-southeast-1.pooler.supabase.com
Port: 6543 (Session mode) 或 5432 (Direct connection)
Database: postgres
User: postgres.[PROJECT-REF]
Password: [YOUR-PASSWORD]
```

3. 記下這些資訊，稍後會用到

---

### 1.5 建立 Storage Bucket (存放上傳的檔案)

1. Supabase Dashboard → **Storage**
2. 點擊「Create a new bucket」
3. 設定：
   - **Name**: `dify-files`
   - **Public bucket**: ✅ (勾選，允許公開存取)
4. 點擊「Create bucket」

---

## 步驟 2: 安裝 Dify

### 2.1 Clone Dify Repository

```bash
# 1. Clone Dify
git clone https://github.com/langgenius/dify.git
cd dify

# 2. 切換到穩定版本
git checkout main
```

---

### 2.2 準備 Docker Compose 設定

Dify 使用 Docker Compose 管理多個服務。我們需要修改預設設定，改用 Supabase。

```bash
cd docker
ls -la
```

你會看到：
- `docker-compose.yaml`: 主要的 Docker Compose 設定檔
- `.env.example`: 環境變數範本

---

## 步驟 3: 設定環境變數

### 3.1 建立 .env 檔案

```bash
# 複製範本
cp .env.example .env

# 編輯 .env
vim .env
# 或
nano .env
```

---

### 3.2 修改 .env 內容

**重要**：以下是需要修改的關鍵設定

```bash
# ========================================
# 基本設定
# ========================================
CONSOLE_API_URL=http://localhost:5001
CONSOLE_WEB_URL=http://localhost:3000
SERVICE_API_URL=http://localhost:5001
APP_WEB_URL=http://localhost:3000

# ========================================
# Supabase 資料庫設定 (重點！)
# ========================================
DB_USERNAME=postgres.[YOUR-PROJECT-REF]
DB_PASSWORD=[YOUR-SUPABASE-PASSWORD]
DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DB_PORT=6543
DB_DATABASE=postgres

# 或直接使用 Connection String
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:YOUR_DB_PASSWORD_HERE@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# ========================================
# Redis 設定 (使用 Docker 內建的 Redis)
# ========================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=YOUR_REDIS_PASSWORD_HERE

# ========================================
# Celery 設定
# ========================================
CELERY_BROKER_URL=redis://:YOUR_REDIS_PASSWORD_HERE@redis:6379/1

# ========================================
# OpenAI API 設定
# ========================================
OPENAI_API_KEY=sk-proj-YOUR-OPENAI-API-KEY

# ========================================
# Storage 設定 (使用 Supabase Storage)
# ========================================
STORAGE_TYPE=supabase
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_API_KEY=[YOUR-SUPABASE-ANON-KEY]
SUPABASE_BUCKET_NAME=dify-files

# ========================================
# Vector Store 設定 (使用 Supabase pgvector)
# ========================================
VECTOR_STORE=pgvector
PGVECTOR_HOST=aws-0-ap-southeast-1.pooler.supabase.com
PGVECTOR_PORT=6543
PGVECTOR_USER=postgres.[YOUR-PROJECT-REF]
PGVECTOR_PASSWORD=[YOUR-SUPABASE-PASSWORD]
PGVECTOR_DATABASE=postgres

# ========================================
# 其他設定
# ========================================
SECRET_KEY=$(openssl rand -base64 42)
LOG_LEVEL=INFO
MIGRATION_ENABLED=true
```

---

### 3.3 取得 Supabase API Keys

1. Supabase Dashboard → **Settings** → **API**
2. 複製：
   - **Project URL**: `https://[YOUR-PROJECT-REF].supabase.co`
   - **anon public**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **service_role secret**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (用於後端)

3. 更新 `.env` 檔案：
   ```bash
   SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
   SUPABASE_API_KEY=[YOUR-SUPABASE-SERVICE-ROLE-KEY]
   ```

---

### 3.4 修改 docker-compose.yaml (重點！)

預設的 `docker-compose.yaml` 會啟動一個內建的 PostgreSQL。我們要改用 Supabase，所以需要移除 PostgreSQL 服務。

```bash
# 編輯 docker-compose.yaml
vim docker-compose.yaml
```

**找到並註解或刪除以下段落**：

```yaml
# 註解掉內建的 PostgreSQL (我們使用 Supabase)
# db:
#   image: postgres:15-alpine
#   restart: always
#   environment:
#     POSTGRES_USER: postgres
#     POSTGRES_PASSWORD: YOUR_REDIS_PASSWORD_HERE
#     POSTGRES_DB: dify
#   volumes:
#     - ./volumes/db/data:/var/lib/postgresql/data
#   ports:
#     - "5432:5432"
```

**保留 Redis 服務**（Dify 需要 Redis 作為快取和任務佇列）：

```yaml
redis:
  image: redis:6-alpine
  restart: always
  volumes:
    - ./volumes/redis/data:/data
  command: redis-server --requirepass YOUR_REDIS_PASSWORD_HERE
  ports:
    - "6379:6379"
```

---

## 步驟 4: 啟動服務

### 4.1 啟動 Dify

```bash
# 確認在 dify/docker 目錄下
cd /path/to/dify/docker

# 啟動所有服務
docker compose up -d

# 查看啟動狀態
docker compose ps
```

**應該會看到以下服務**：

```
NAME                COMMAND                  SERVICE             STATUS
dify-api            "/bin/bash /entrypoi…"   api                 Up
dify-web            "docker-entrypoint.s…"   web                 Up
dify-worker         "/bin/bash /entrypoi…"   worker              Up
dify-nginx          "/docker-entrypoint.…"   nginx               Up
dify-redis          "docker-entrypoint.s…"   redis               Up
```

---

### 4.2 檢查日誌

```bash
# 查看所有服務日誌
docker compose logs -f

# 只查看 API 服務日誌
docker compose logs -f api

# 只查看 Worker 服務日誌
docker compose logs -f worker
```

**成功的日誌應該包含**：

```
dify-api     | INFO: Application startup complete.
dify-api     | INFO: Uvicorn running on http://0.0.0.0:5001
dify-worker  | [2024-10-30 10:00:00,000: INFO/MainProcess] celery@worker ready.
```

---

### 4.3 執行資料庫遷移 (Migration)

```bash
# 進入 API 容器
docker compose exec api bash

# 執行 migration
flask db upgrade

# 退出容器
exit
```

---

### 4.4 開啟 Dify Web UI

瀏覽器前往：**http://localhost:3000**

你應該會看到 Dify 的註冊頁面。

---

## 步驟 5: 建立 RAG 應用

### 5.1 註冊管理員帳號

1. 開啟 http://localhost:3000
2. 填寫資訊：
   - **Email**: your-email@example.com
   - **Name**: Admin
   - **Password**: 設定強密碼

3. 點擊「Create Account」

---

### 5.2 設定 OpenAI API Key

1. 登入後，點擊右上角頭像 → **Settings**
2. 左側選單 → **Model Provider**
3. 找到 **OpenAI** → 點擊「Setup」
4. 輸入你的 OpenAI API Key: `sk-proj-xxx`
5. 點擊「Save」

---

### 5.3 建立知識庫 (Dataset)

1. 左側選單 → **Knowledge** (知識庫)
2. 點擊「Create Knowledge」
3. 設定：
   - **Name**: `產品說明文件`
   - **Description**: `包含所有產品說明的文件`
   - **Indexing Mode**: `High Quality` (使用 OpenAI embeddings)
   - **Embedding Model**: `text-embedding-3-small`
   - **Retrieval Setting**:
     - **Top K**: 3
     - **Score Threshold**: 0.5

4. 點擊「Create」

---

### 5.4 上傳文件

1. 進入剛建立的知識庫「產品說明文件」
2. 點擊「Upload file」或直接拖曳檔案
3. 支援的格式：
   - PDF
   - TXT
   - Markdown
   - HTML
   - XLSX / CSV
   - DOCX

4. 上傳後，Dify 會自動：
   - 提取文字
   - 切片 (Chunking)
   - 生成 Embeddings (調用 OpenAI API)
   - 儲存到 Supabase

5. 等待處理完成（狀態變成「Available」）

---

### 5.5 建立 Chatbot 應用

1. 左側選單 → **Studio** (應用)
2. 點擊「Create Application」
3. 選擇「Chat App」模板
4. 設定：
   - **Name**: `產品說明助手`
   - **Icon**: 選擇一個圖示
   - **Description**: `回答產品相關問題`

5. 點擊「Create」

---

### 5.6 設定應用

**進入應用編輯介面**：

1. **Prompt**（提示詞）：
   ```
   你是一個專業的產品說明助手。
   根據提供的產品文件回答使用者的問題。

   規則：
   1. 如果文件中有相關資訊，請詳細回答
   2. 如果文件中沒有相關資訊，請誠實告知「文件中沒有這個資訊」
   3. 回答時請引用來源文件的名稱
   4. 使用繁體中文回答
   ```

2. **Context**（連結知識庫）：
   - 點擊「Add」
   - 選擇「產品說明文件」
   - 設定 Top K: 3
   - 設定 Score Threshold: 0.5

3. **Model**（選擇模型）：
   - Model: `gpt-3.5-turbo` 或 `gpt-4`
   - Temperature: 0.7
   - Max Tokens: 1000

4. 點擊「Publish」

---

### 5.7 測試 Chatbot

1. 在應用編輯頁面右側，有一個測試區域
2. 輸入問題，例如：「這個產品有哪些功能？」
3. Chatbot 會：
   - 將問題轉換成 embedding
   - 在 Supabase 中搜尋相似的文件段落
   - 將檢索結果和問題一起發送給 OpenAI
   - 返回答案

**範例對話**：

```
👤 使用者：這個產品支援哪些付款方式？

🤖 產品說明助手：
根據《產品功能說明.pdf》第 5 頁，本產品支援以下付款方式：
1. 信用卡（Visa、Mastercard、JCB）
2. 行動支付（Apple Pay、Google Pay）
3. 銀行轉帳
4. 超商代碼繳費

來源：產品功能說明.pdf
```

---

### 5.8 發布到網站

1. 點擊「Publish」→「Share」
2. 複製嵌入代碼：

```html
<!-- 方案 A: iframe 嵌入 -->
<iframe
  src="http://localhost:3000/chat/[YOUR-APP-ID]"
  style="width: 100%; height: 600px; border: none;"
  allow="microphone">
</iframe>

<!-- 方案 B: JavaScript SDK -->
<script>
  window.difyChatbotConfig = {
    token: '[YOUR-APP-TOKEN]',
  }
</script>
<script
  src="http://localhost:3000/embed.min.js"
  id="[YOUR-APP-ID]"
  defer>
</script>
```

3. 將代碼貼到你的網站 HTML 中

---

## 常見問題排解

### Q1: 啟動失敗，提示 "connection refused"

**原因**：無法連線到 Supabase

**解決方法**：
1. 檢查 `.env` 中的 `DATABASE_URL` 是否正確
2. 檢查 Supabase 專案是否正常運行
3. 測試連線：
   ```bash
   psql "postgresql://postgres.[PROJECT-REF]:YOUR_DB_PASSWORD_HERE@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
   ```

---

### Q2: 上傳文件後一直顯示 "Processing"

**原因**：Celery Worker 沒有正常運行，或 OpenAI API 調用失敗

**解決方法**：
1. 檢查 Worker 日誌：
   ```bash
   docker compose logs -f worker
   ```

2. 檢查 OpenAI API Key 是否正確：
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. 重啟 Worker：
   ```bash
   docker compose restart worker
   ```

---

### Q3: 搜尋沒有結果

**原因**：Score Threshold 設定太高，或文件沒有正確生成 embeddings

**解決方法**：
1. 降低 Score Threshold（從 0.5 改成 0.3）
2. 檢查 Supabase 中的 `embeddings` 表格：
   ```sql
   SELECT COUNT(*) FROM embeddings;
   ```

3. 重新處理文件：
   - 刪除文件 → 重新上傳

---

### Q4: Supabase 連線池滿了

**錯誤訊息**：`FATAL: remaining connection slots are reserved for non-replication superuser connections`

**原因**：Supabase Free Plan 只有 60 個連線，Dify 可能用完了

**解決方法**：
1. 使用 Session Mode（Port 6543）而非 Direct Connection（Port 5432）
2. 減少 Dify 的連線池大小，編輯 `.env`：
   ```bash
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=5
   ```

3. 升級 Supabase 到 Pro Plan（支援更多連線）

---

### Q5: 如何備份資料？

**方法 1：使用 Supabase Dashboard**
1. Supabase Dashboard → **Database** → **Backups**
2. 點擊「Download backup」

**方法 2：使用 pg_dump**
```bash
pg_dump "postgresql://postgres.[PROJECT-REF]:YOUR_DB_PASSWORD_HERE@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres" > backup.sql
```

---

## 效能優化

### 1. 調整 Chunking 策略

知識庫設定 → **Text Preprocessing** → **Segmentation Settings**:
- **Max Segment Length**: 500 (預設 1000)
- **Overlap Length**: 50 (預設 0)

較小的 chunk 可以提升搜尋精準度，但會增加 token 消耗。

---

### 2. 使用 Hybrid Search (未來功能)

Dify 計劃支援 Hybrid Search（結合關鍵字搜尋和向量搜尋）。

---

### 3. 使用 Re-ranking (未來功能)

使用 Cohere Rerank API 對檢索結果重新排序，提升準確度。

---

## 部署到生產環境

### 選項 1: 部署到 Cloud Run

```bash
# 1. 建立 Dockerfile (Dify 已提供)
cd dify

# 2. 建立並推送 Docker image
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/dify-api

# 3. 部署到 Cloud Run
gcloud run deploy dify-api \
  --image gcr.io/YOUR-PROJECT-ID/dify-api \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="YOUR-SUPABASE-URL" \
  --set-env-vars OPENAI_API_KEY="YOUR-KEY"
```

---

### 選項 2: 使用 Dify Cloud (官方 SaaS)

最簡單的方式：https://cloud.dify.ai

優點：
- ✅ 免安裝
- ✅ 自動更新
- ✅ 官方維護

缺點：
- ⚠️ 需要付費（有免費額度）
- ⚠️ 資料存放在 Dify 的伺服器

---

## 總結

你現在有一個完整的 Dify + Supabase RAG 系統！

**功能清單**：
- ✅ No-code 建立 RAG 應用
- ✅ 美觀的 Chatbot UI
- ✅ 多文件上傳與管理
- ✅ 向量搜尋（pgvector）
- ✅ 引用來源
- ✅ 可嵌入網站

**成本估算** (每月)：
- Supabase Free Plan: $0 (500MB DB, 1GB 檔案儲存)
- OpenAI API: ~$10-50 (視使用量)
- Cloud Run (如果部署): ~$20
- **總計**: $10-70/月

**下一步**：
1. 上傳你的 10-20 份產品說明文件
2. 測試 Chatbot 回答品質
3. 調整 Prompt 和 Retrieval 設定
4. 部署到生產環境
5. 嵌入到公司網站

---

**需要協助？**
- Dify 官方文檔: https://docs.dify.ai
- Dify GitHub Issues: https://github.com/langgenius/dify/issues
- Supabase 文檔: https://supabase.com/docs
