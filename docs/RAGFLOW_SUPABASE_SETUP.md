# RAGFlow + Supabase 完整啟動文件

## 📋 目錄

- [系統需求](#系統需求)
- [架構說明](#架構說明)
- [步驟 1: 準備 Supabase](#步驟-1-準備-supabase)
- [步驟 2: 安裝 RAGFlow](#步驟-2-安裝-ragflow)
- [步驟 3: 設定環境變數](#步驟-3-設定環境變數)
- [步驟 4: 使用 RAGFlow](#步驟-4-使用-ragflow)
- [步驟 5: 部署到生產環境](#步驟-5-部署到生產環境)
- [常見問題排解](#常見問題排解)

---

## 系統需求

**硬體需求**：
- CPU: 4+ cores
- RAM: 16GB+ (推薦)
- Disk: 50GB+
- Docker 24.0.0+
- Docker Compose 2.26.1+

**軟體需求**：
- Supabase 帳號
- OpenAI API Key

**注意**：RAGFlow 是企業級解決方案，資源需求較高。

---

## 架構說明

```
┌─────────────────────────────────────────────────────────┐
│                  RAGFlow 架構                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────┐          │
│  │     RAGFlow Web UI (React)               │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │Knowledge│ │Template│  │  Chat  │      │          │
│  │  │  Base  │  │Builder │  │ Agent  │      │          │
│  │  └────────┘  └────────┘  └────────┘      │          │
│  └──────────────────────────────────────────┘          │
│                      │                                   │
│                      ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │       RAGFlow API Server (Python)        │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │Document│→ │Template│→ │Chunking│      │          │
│  │  │Parser  │  │Engine  │  │Service │      │          │
│  │  └────────┘  └────────┘  └────────┘      │          │
│  │                               ↓           │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │Embedding│ │ Vector │  │ Agent  │      │          │
│  │  │Service │  │ Search │  │Reasoning│     │          │
│  │  └────────┘  └────────┘  └────────┘      │          │
│  └──────────────────────────────────────────┘          │
│                      │                                   │
│                      ▼                                   │
│           ┌──────────────────┐                          │
│           │   Supabase       │                          │
│           │  PostgreSQL +    │                          │
│           │   pgvector       │                          │
│           └──────────────────┘                          │
│                      │                                   │
│                      ▼                                   │
│           ┌──────────────────┐                          │
│           │   OpenAI API     │                          │
│           │  (GPT + Embed)   │                          │
│           └──────────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

**說明**：
- **Template Engine**: 智能切片模板（根據文件類型）
- **Document Parser**: 深度文件理解（表格、圖片、OCR）
- **Agent Reasoning**: 多步驟推理（Planning + Execution）
- **Grounded Citations**: 減少 AI 幻覺，提供可驗證的引用
- **Multi-modal**: 支援 Word、Excel、PPT、圖片、網頁等

---

## 步驟 1: 準備 Supabase

### 1.1 建立 Supabase 專案

1. 前往 https://supabase.com
2. 建立新專案：
   - **Name**: `ragflow-rag`
   - **Database Password**: 設定強密碼（記下來）
   - **Region**: `Southeast Asia (Singapore)`

3. 等待專案建立完成

---

### 1.2 啟用 pgvector

在 Supabase Dashboard → **SQL Editor** 執行：

```sql
-- 啟用 pgvector 擴充功能
CREATE EXTENSION IF NOT EXISTS vector;

-- 驗證
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

### 1.3 建立資料庫結構

RAGFlow 使用複雜的資料庫架構，支援模板化切片和 Agent 推理：

```sql
-- 1. Knowledge Bases (知識庫)
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    language VARCHAR(50) DEFAULT 'zh-TW',
    chunk_method VARCHAR(50) DEFAULT 'template',  -- 'naive', 'qa', 'template', 'book'
    parser_config JSONB DEFAULT '{}',
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kb_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- 'pdf', 'docx', 'xlsx', 'pptx', 'txt', 'md', 'html', 'url', 'image'
    location TEXT NOT NULL,  -- Supabase Storage path
    size INTEGER,
    token_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    parser_method VARCHAR(50),  -- 'pdf', 'docx', 'ocr', 'table', 'web'
    parser_config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'CREATED',  -- 'CREATED', 'PARSING', 'PARSED', 'CHUNKING', 'INDEXED', 'FAILED'
    progress INTEGER DEFAULT 0,
    error_msg TEXT,
    run_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Document Chunks (使用模板化切片)
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    kb_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_with_weight TEXT,  -- 加權後的內容（用於搜尋）
    important_keywords JSONB DEFAULT '[]',
    doc_name VARCHAR(500),
    position INTEGER NOT NULL,
    token_count INTEGER,
    chunk_method VARCHAR(50),
    chunk_template VARCHAR(100),  -- 切片模板名稱
    available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Embeddings (pgvector)
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small
    model_name VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Chunk Templates (切片模板)
CREATE TABLE IF NOT EXISTS chunk_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    doc_types VARCHAR(255),  -- 'pdf,docx,txt'
    template_config JSONB NOT NULL,
    is_builtin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Conversations (對話)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    name VARCHAR(255),
    dialog_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user', 'assistant'
    content TEXT NOT NULL,
    reference JSONB DEFAULT '[]',  -- 引用的 chunks
    thumbup BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Agents (Multi-agent 推理)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    avatar TEXT,
    llm_id VARCHAR(100),
    prompt TEXT,
    kb_ids JSONB DEFAULT '[]',  -- 關聯的知識庫
    tools JSONB DEFAULT '[]',  -- Agent 可用的工具
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. 建立索引
CREATE INDEX IF NOT EXISTS idx_knowledge_bases_tenant_id ON knowledge_bases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_kb_id ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id ON document_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_kb_id ON document_chunks(kb_id);
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chunk_id ON chunk_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- 10. 建立向量索引 (HNSW)
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_vector
ON chunk_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 11. 全文檢索（用於 Hybrid Search）
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS content_tsvector tsvector;

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_tsvector
ON document_chunks
USING gin(content_tsvector);

CREATE OR REPLACE FUNCTION document_chunks_content_trigger() RETURNS trigger AS $$
BEGIN
  NEW.content_tsvector := to_tsvector('simple', COALESCE(NEW.content, ''));
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvector_update_trigger
BEFORE INSERT OR UPDATE ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION document_chunks_content_trigger();
```

---

### 1.4 插入預設的 Chunk Templates

RAGFlow 的核心功能是模板化切片，以下是幾個內建模板：

```sql
-- 插入內建切片模板
INSERT INTO chunk_templates (name, description, doc_types, template_config, is_builtin)
VALUES
(
  'General',
  '通用切片模板：適合大部分文件',
  'pdf,docx,txt,md',
  '{
    "chunk_token_num": 400,
    "delimiter": "\\n!?;。！？；",
    "html4excel": false,
    "layout_recognize": true,
    "raptor": {"use_raptor": false}
  }'::jsonb,
  true
),
(
  'Q&A',
  'Q&A 切片模板：適合問答對格式',
  'txt,md,docx',
  '{
    "chunk_token_num": 200,
    "delimiter": "\\n",
    "html4excel": false,
    "layout_recognize": false,
    "qa_pattern": "(?i)q[\\s\\:]*|(?i)question[\\s\\:]*"
  }'::jsonb,
  true
),
(
  'Table',
  '表格切片模板：適合 Excel、結構化資料',
  'xlsx,csv',
  '{
    "chunk_token_num": 600,
    "delimiter": "",
    "html4excel": true,
    "layout_recognize": false
  }'::jsonb,
  true
),
(
  'Book',
  '書籍切片模板：適合長篇文章、書籍',
  'pdf,docx,txt',
  '{
    "chunk_token_num": 600,
    "delimiter": "\\n",
    "html4excel": false,
    "layout_recognize": true,
    "book_mode": true,
    "use_chapter": true
  }'::jsonb,
  true
);
```

---

### 1.5 建立向量搜尋函數

```sql
-- Hybrid Search 函數（向量 + 全文）
CREATE OR REPLACE FUNCTION hybrid_search (
  query_embedding vector(1536),
  query_text text,
  kb_id_filter uuid DEFAULT NULL,
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  chunk_id uuid,
  doc_id uuid,
  doc_name varchar,
  content text,
  similarity_score float,
  fulltext_rank float,
  combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id AS chunk_id,
    dc.doc_id,
    dc.doc_name,
    dc.content,
    (1 - (ce.embedding <=> query_embedding)) AS similarity_score,
    ts_rank(dc.content_tsvector, plainto_tsquery('simple', query_text)) AS fulltext_rank,
    ((1 - (ce.embedding <=> query_embedding)) * 0.7 + ts_rank(dc.content_tsvector, plainto_tsquery('simple', query_text)) * 0.3) AS combined_score
  FROM document_chunks dc
  JOIN chunk_embeddings ce ON dc.id = ce.chunk_id
  WHERE
    dc.available = TRUE
    AND (kb_id_filter IS NULL OR dc.kb_id = kb_id_filter)
    AND (
      (1 - (ce.embedding <=> query_embedding)) >= match_threshold
      OR dc.content_tsvector @@ plainto_tsquery('simple', query_text)
    )
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$;
```

---

### 1.6 取得 Supabase 連線資訊

1. Supabase Dashboard → **Settings** → **Database**
2. 複製 **Connection String**
3. 複製 **API Keys** (Settings → API)

---

## 步驟 2: 安裝 RAGFlow

### 方案 A: Docker Compose（推薦）

```bash
# 1. Clone RAGFlow repo
git clone https://github.com/infiniflow/ragflow.git
cd ragflow

# 2. 查看系統需求
cat README.md
```

---

### 2.1 準備 Docker Compose 設定

RAGFlow 使用複雜的 Docker Compose 架構，包含多個服務。

```bash
# 檢查 docker-compose.yml
cat docker-compose.yml
```

你會看到以下服務：
- **ragflow-api**: 後端 API server
- **ragflow-web**: 前端 Web UI (React)
- **ragflow-worker**: 後台任務處理（文件解析、embedding）
- **redis**: 快取和任務佇列
- **minio** (可選): 檔案儲存（我們用 Supabase Storage）

---

### 2.2 修改 docker-compose.yml

**重點**：移除內建的 PostgreSQL，改用 Supabase。

```bash
# 編輯 docker-compose.yml
vim docker-compose.yml
```

**註解掉以下服務**（我們用 Supabase）：

```yaml
# 註解掉內建的 PostgreSQL
# postgres:
#   image: postgres:15-alpine
#   ...

# 保留 Redis
redis:
  image: redis:7-alpine
  restart: always
  command: redis-server --requirepass ragflow123
  ports:
    - "6379:6379"

# 可選：註解掉 MinIO（改用 Supabase Storage）
# minio:
#   image: minio/minio
#   ...
```

---

## 步驟 3: 設定環境變數

### 3.1 建立 .env 檔案

```bash
# 複製範本
cp .env.example .env

# 編輯
vim .env
```

---

### 3.2 設定 .env 內容

```bash
# ========================================
# 基本設定
# ========================================
RAGFLOW_VERSION=latest
API_HOST=0.0.0.0
API_PORT=9380
WEB_PORT=80

# ========================================
# Supabase Database 設定
# ========================================
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# 或分開設定
DB_TYPE=postgresql
DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.[YOUR-PROJECT-REF]
DB_PASSWORD=[YOUR-SUPABASE-PASSWORD]

# ========================================
# Supabase API & Storage 設定
# ========================================
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_SERVICE_KEY=[YOUR-SERVICE-ROLE-KEY]
SUPABASE_BUCKET_NAME=ragflow-files

# Storage Type
STORAGE_TYPE=supabase  # 'local' or 'minio' or 'supabase'

# ========================================
# Redis 設定
# ========================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=ragflow123
REDIS_DB=0

# ========================================
# OpenAI API 設定
# ========================================
OPENAI_API_KEY=sk-proj-YOUR-OPENAI-API-KEY
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-3.5-turbo

# 可選：Azure OpenAI
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=your-azure-key
# AZURE_OPENAI_DEPLOYMENT=gpt-35-turbo

# ========================================
# Vector Store 設定
# ========================================
VECTOR_STORE=supabase  # 'elasticsearch' or 'milvus' or 'supabase'
VECTOR_DIMENSION=1536

# ========================================
# RAGFlow 功能設定
# ========================================
# Template-based Chunking
ENABLE_TEMPLATE_CHUNKING=true

# Deep Document Understanding
ENABLE_LAYOUT_RECOGNITION=true
ENABLE_OCR=true
ENABLE_TABLE_DETECTION=true

# Agent Reasoning
ENABLE_AGENT=true
MAX_REASONING_STEPS=5

# Grounded Citations
ENABLE_GROUNDED_CITATION=true

# ========================================
# 文件處理設定
# ========================================
MAX_FILE_SIZE=100  # MB
SUPPORTED_FILE_TYPES=pdf,docx,xlsx,pptx,txt,md,html,csv,jpg,png

# OCR 設定
OCR_ENGINE=tesseract  # 'tesseract' or 'paddle'
OCR_LANGUAGE=eng+chi_tra

# ========================================
# Retrieval 設定
# ========================================
TOP_K=5
SIMILARITY_THRESHOLD=0.5
HYBRID_SEARCH_ENABLED=true
HYBRID_VECTOR_WEIGHT=0.7
HYBRID_FULLTEXT_WEIGHT=0.3

# Re-ranking
ENABLE_RERANK=false
# RERANK_MODEL=BAAI/bge-reranker-large

# ========================================
# 使用者認證設定
# ========================================
ENABLE_AUTH=true
SECRET_KEY=your-secret-key-at-least-32-characters-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# 預設管理員
DEFAULT_ADMIN_EMAIL=admin@ragflow.io
DEFAULT_ADMIN_PASSWORD=admin123456

# ========================================
# 其他設定
# ========================================
LOG_LEVEL=INFO
DEBUG=false
TIMEZONE=Asia/Taipei

# Celery Worker 設定
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=50
```

---

### 3.3 建立 Supabase Storage Bucket

1. Supabase Dashboard → **Storage**
2. 建立 Bucket：
   - **Name**: `ragflow-files`
   - **Public**: ✅ 勾選

---

## 步驟 4: 使用 RAGFlow

### 4.1 啟動 RAGFlow

```bash
# 確保在 ragflow 目錄下
cd ragflow

# 啟動所有服務
docker compose up -d

# 查看啟動狀態
docker compose ps

# 查看日誌
docker compose logs -f
```

**成功啟動後，你會看到**：

```
NAME              COMMAND                  SERVICE        STATUS
ragflow-api       "python api/ragflow_…"   api            Up
ragflow-web       "nginx -g 'daemon of…"   web            Up
ragflow-worker    "celery -A tasks wor…"   worker         Up
ragflow-redis     "redis-server --requ…"   redis          Up
```

---

### 4.2 開啟 Web UI

瀏覽器前往：**http://localhost**

你會看到 RAGFlow 的登入頁面。

---

### 4.3 註冊/登入

使用預設管理員帳號：
- **Email**: `admin@ragflow.io`
- **Password**: `admin123456`

或點擊「Sign up」註冊新帳號。

---

### 4.4 建立 Knowledge Base

1. 登入後，點擊「Knowledge Base」→「Create」
2. 設定：
   - **Name**: `產品說明文件`
   - **Description**: `所有產品說明相關的文件`
   - **Language**: `Chinese (Traditional)`
   - **Chunk Method**: `Template` (推薦)
   - **Parser**: 根據檔案類型自動選擇

3. 點擊「Create」

---

### 4.5 上傳文件

1. 進入剛建立的 Knowledge Base
2. 點擊「Upload」→「Select Files」
3. 支援的格式：
   - 📄 PDF
   - 📝 DOCX, TXT, MD
   - 📊 XLSX, CSV
   - 🎨 PPTX
   - 🖼️ JPG, PNG (需要 OCR)
   - 🌐 URL (網頁抓取)

4. 選擇 **Chunk Template**：
   - **General**: 通用文件
   - **Q&A**: 問答格式
   - **Table**: 表格資料
   - **Book**: 長篇書籍

5. 點擊「Upload」

RAGFlow 會自動：
- 上傳檔案到 Supabase Storage
- 使用 Deep Document Understanding 提取內容
  - Layout Recognition (版面識別)
  - Table Detection (表格檢測)
  - OCR (光學字元識別)
- 根據模板智能切片
- 調用 OpenAI API 生成 embeddings
- 儲存到 Supabase

6. 等待處理完成（可以在 Dashboard 查看進度）

---

### 4.6 查看處理結果

1. 點擊文件名稱，查看詳細資訊
2. 可以看到：
   - **Chunks**: 切片結果（每個 chunk 都可以編輯）
   - **Metadata**: 文件元資訊
   - **Preview**: 文件預覽（標註出切片邊界）

3. RAGFlow 的特色：
   - 可視化切片邊界
   - 保留文件的結構（標題、段落、表格）
   - 自動提取關鍵詞

---

### 4.7 建立 Chat Agent

1. 點擊「Agent」→「Create」
2. 設定：
   - **Name**: `產品說明助手`
   - **Avatar**: 選擇圖示
   - **LLM**: `gpt-3.5-turbo` 或 `gpt-4`
   - **Prompt**:
     ```
     你是一個專業的產品說明助手。
     根據知識庫中的文件回答使用者問題。

     規則：
     1. 如果文件中有相關資訊，請詳細回答
     2. 如果文件中沒有，請告知「文件中沒有這個資訊」
     3. 回答時必須引用來源文件，並標註頁數或段落
     4. 使用繁體中文回答
     5. 保持專業但友善的語氣
     ```
   - **Knowledge Bases**: 選擇「產品說明文件」
   - **Tools**: 可以加入外部工具（API、搜尋引擎等）

3. 點擊「Save」

---

### 4.8 開始對話

1. 點擊「Chat」→ 選擇剛建立的 Agent
2. 輸入問題：
   ```
   這個產品有哪些主要功能？
   ```

3. RAGFlow 會：
   - **Step 1: Planning**: Agent 分析問題，決定檢索策略
   - **Step 2: Retrieval**: 使用 Hybrid Search 檢索相關文件
   - **Step 3: Re-ranking** (可選): 重新排序檢索結果
   - **Step 4: Generation**: GPT 生成回答
   - **Step 5: Grounded Citation**: 驗證回答，提供可驗證的引用

4. 回答格式：

```
🤖 產品說明助手：

根據文件內容，本產品的主要功能包括：

1. **使用者管理**
   - 多使用者登入
   - 權限管理
   - 個人化設定

2. **資料分析**
   - 即時報表
   - 視覺化圖表
   - 數據匯出

3. **整合功能**
   - API 介面
   - 第三方串接
   - Webhook 支援

📚 來源引用：
[1] 產品功能說明.pdf - 第 3 頁，段落 2
[2] 技術規格書.docx - 第 1 頁，表格 1
[3] API 文檔.md - 第 5 頁

💡 可信度評分：95% (基於 3 個可驗證的來源)
```

---

### 4.9 查看 Agent Reasoning 過程

RAGFlow 的特色是透明的推理過程，點擊「Show Reasoning」可以看到：

```
🧠 Agent Reasoning Process:

Step 1: Question Analysis
- User intent: 詢問產品功能
- Query type: Informational
- Required knowledge: Product features, specifications

Step 2: Retrieval Planning
- Strategy: Hybrid search (vector + full-text)
- Top K: 5
- Similarity threshold: 0.5

Step 3: Document Retrieval
- Found 5 relevant chunks
- Sources: 3 documents
- Average similarity: 0.82

Step 4: Re-ranking (optional)
- Re-ranked top 3 chunks
- Relevance scores: [0.95, 0.89, 0.83]

Step 5: Answer Generation
- LLM: gpt-3.5-turbo
- Temperature: 0.7
- Max tokens: 1000

Step 6: Citation Verification
- All citations verified ✅
- No hallucinations detected ✅
```

---

## 步驟 5: 部署到生產環境

### 選項 1: 部署到 Cloud Run

RAGFlow 較複雜，建議分別部署 API 和 Web：

```bash
# 1. 建立 Docker images
cd ragflow

# API Server
docker build -t ragflow-api -f Dockerfile.api .
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/ragflow-api

# Web UI
docker build -t ragflow-web -f Dockerfile.web .
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/ragflow-web

# 2. 部署 API
gcloud run deploy ragflow-api \
  --image gcr.io/YOUR-PROJECT-ID/ragflow-api \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="YOUR-SUPABASE-URL" \
  --set-env-vars OPENAI_API_KEY="YOUR-KEY" \
  --memory 4Gi \
  --cpu 2

# 3. 部署 Web UI
gcloud run deploy ragflow-web \
  --image gcr.io/YOUR-PROJECT-ID/ragflow-web \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars API_URL="https://ragflow-api-xxx.run.app"
```

---

### 選項 2: 使用 Kubernetes (推薦企業級)

RAGFlow 提供 Helm charts：

```bash
# 1. 安裝 Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 2. 部署 RAGFlow
helm install ragflow ./helm/ragflow \
  --set database.url="YOUR-SUPABASE-URL" \
  --set openai.apiKey="YOUR-KEY" \
  --set supabase.url="YOUR-SUPABASE-URL" \
  --set supabase.serviceKey="YOUR-KEY"
```

---

## 常見問題排解

### Q1: 文件解析失敗

**錯誤訊息**：`Document parsing failed`

**原因**：PDF 格式複雜，或 OCR 引擎沒有正確安裝

**解決方法**：
1. 檢查文件格式是否支援
2. 嘗試不同的 Parser:
   - **PDF Parser**: 適合文字型 PDF
   - **OCR Parser**: 適合掃描型 PDF
   - **Table Parser**: 適合表格型 PDF

3. 調整 Parser 設定（在 Upload 時選擇）

---

### Q2: Chunk 切得不好

**問題**：切片邊界不合理，切斷了句子或段落

**解決方法**：
1. 選擇不同的 Chunk Template
2. 自訂切片模板：
   - 調整 `chunk_token_num`
   - 調整 `delimiter`
   - 啟用 `layout_recognize`

3. 手動編輯 Chunks（RAGFlow 支援）

---

### Q3: Agent 回答不準確

**問題**：Agent 回答與文件內容不符，或產生幻覺

**解決方法**：
1. 啟用 `Grounded Citation`（強制引用來源）
2. 調整 Retrieval 參數：
   - 增加 `Top K`（從 5 改成 10）
   - 降低 `Similarity Threshold`（從 0.5 改成 0.3）

3. 啟用 Re-ranking
4. 調整 Agent Prompt（加入「必須基於文件回答」）

---

### Q4: 記憶體不足

**錯誤訊息**：`OOM (Out of Memory)`

**原因**：RAGFlow 需要較多記憶體（16GB+）

**解決方法**：
1. 增加系統記憶體
2. 調整 Celery Worker 並發數：
   ```bash
   CELERY_WORKER_CONCURRENCY=2  # 從 4 改成 2
   ```

3. 使用較小的 Embedding Model
4. 分批處理文件（不要一次上傳太多）

---

### Q5: Supabase 連線池滿了

**錯誤訊息**：`remaining connection slots are reserved`

**解決方法**：
1. 使用 Session Mode (Port 6543)
2. 升級 Supabase 到 Pro Plan
3. 使用連線池：
   ```bash
   DB_POOL_SIZE=20
   DB_MAX_OVERFLOW=10
   ```

---

## 進階功能

### 1. 自訂 Chunk Template

在 Web UI → **Settings** → **Chunk Templates** → **Create**：

```json
{
  "name": "產品說明書模板",
  "chunk_token_num": 400,
  "delimiter": "\\n###",  # 以三級標題作為分隔
  "layout_recognize": true,
  "html4excel": false,
  "important_keywords": ["產品", "功能", "規格", "價格"],
  "raptor": {
    "use_raptor": false
  }
}
```

---

### 2. 使用 Multi-agent Workflow

建立多個 Agent，協同工作：

```yaml
Agent 1: 產品功能專家
- Knowledge Base: 產品說明文件
- Role: 回答產品功能相關問題

Agent 2: 技術支援專家
- Knowledge Base: 技術規格書、故障排除
- Role: 回答技術問題

Agent 3: 價格方案專家
- Knowledge Base: 價格表、方案說明
- Role: 回答價格和方案問題

Orchestrator Agent: 總協調
- 根據使用者問題，決定轉發給哪個 Agent
- 整合多個 Agent 的回答
```

---

### 3. 整合外部工具

在 Agent 設定中加入 Tools：

- **Web Search**: Google, Bing
- **API Call**: 調用公司內部 API
- **Calculator**: 計算價格
- **Code Execution**: 執行 Python 代碼

---

## 總結

你現在有一個完整的 RAGFlow + Supabase 企業級 RAG 系統！

**功能清單**：
- ✅ Template-based 智能切片
- ✅ Deep Document Understanding
- ✅ Multi-modal 支援 (Word/Excel/PPT/圖片/網頁)
- ✅ Agent Reasoning (多步驟推理)
- ✅ Grounded Citations (減少幻覺)
- ✅ Hybrid Search (向量 + 全文)
- ✅ Re-ranking (提升準確度)
- ✅ 可視化切片邊界

**優勢**：
- 🏢 企業級功能
- 🧠 Agent 推理透明
- 📊 支援複雜文件格式
- 🔍 Hybrid Search 更準確
- 💯 Grounded Citations 減少幻覺

**成本估算** (每月)：
- RAGFlow: $0 (開源)
- Supabase: $0-25 (Free/Pro)
- OpenAI API: ~$20-100
- Cloud Run: ~$50-100 (16GB RAM)
- **總計**: $70-225/月

**適合場景**：
- ✅ 企業內部知識庫
- ✅ 複雜文件格式（表格、圖片）
- ✅ 需要高準確度（grounded citations）
- ✅ 需要 Agent 推理
- ❌ 小型個人項目（資源需求高）

---

**需要協助？**
- RAGFlow GitHub: https://github.com/infiniflow/ragflow
- RAGFlow 文檔: https://ragflow.io/docs
- RAGFlow Discord: https://discord.gg/ragflow
