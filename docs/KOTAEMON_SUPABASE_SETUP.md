# Kotaemon + Supabase 完整啟動文件

## 📋 目錄

- [系統需求](#系統需求)
- [架構說明](#架構說明)
- [步驟 1: 準備 Supabase](#步驟-1-準備-supabase)
- [步驟 2: 安裝 Kotaemon](#步驟-2-安裝-kotaemon)
- [步驟 3: 設定環境變數](#步驟-3-設定環境變數)
- [步驟 4: 使用 Kotaemon](#步驟-4-使用-kotaemon)
- [步驟 5: 部署到生產環境](#步驟-5-部署到生產環境)
- [常見問題排解](#常見問題排解)

---

## 系統需求

- Python 3.10+
- Docker 20.10+ (推薦)
- 4GB+ RAM
- Supabase 帳號
- OpenAI API Key

---

## 架構說明

```
┌─────────────────────────────────────────────────────────┐
│                 Kotaemon 架構                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────┐          │
│  │     Gradio UI (使用者介面)                │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │ 上傳   │  │ 文件   │  │  Chat  │      │          │
│  │  │ 文件   │  │ 管理   │  │  介面  │      │          │
│  │  └────────┘  └────────┘  └────────┘      │          │
│  └──────────────────────────────────────────┘          │
│                      │                                   │
│                      ▼                                   │
│  ┌──────────────────────────────────────────┐          │
│  │         Kotaemon Backend                 │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │Document│→ │Chunking│→ │Embedding│     │          │
│  │  │Parser  │  │Service │  │Service │      │          │
│  │  └────────┘  └────────┘  └────────┘      │          │
│  │                               ↓           │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │Retrieval│← │ Vector │← │  Index │     │          │
│  │  │Service │  │ Search │  │Builder │      │          │
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
- **Gradio UI**: 美觀的使用者介面（上傳、管理、對話）
- **Document Parser**: 支援 PDF、Word、TXT 等格式
- **Chunking Service**: 智能文字切片
- **Embedding Service**: 調用 OpenAI 生成 embeddings
- **Vector Search**: Supabase pgvector 向量搜尋
- **Retrieval Service**: Hybrid retrieval (full-text + vector)
- **Multi-user**: 支援多使用者登入

---

## 步驟 1: 準備 Supabase

### 1.1 建立 Supabase 專案

1. 前往 https://supabase.com
2. 建立新專案：
   - **Name**: `kotaemon-rag`
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

Kotaemon 使用以下資料庫架構：

```sql
-- 1. 文件集合 (Collections)
CREATE TABLE IF NOT EXISTS collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 文件 (Documents)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- 'pdf', 'docx', 'txt'
    file_size INTEGER,
    storage_path TEXT NOT NULL,
    content TEXT,  -- 提取的文字內容
    metadata JSONB DEFAULT '{}',
    user_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 文件片段 (Chunks)
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    chunk_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Embeddings (使用 pgvector)
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small
    model_name VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 使用者 (Users)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 6. 對話歷史 (Chat History)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES collections(id) ON DELETE SET NULL,
    session_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 建立索引
CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chunk_id ON chunk_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);

-- 8. 建立向量索引 (HNSW 算法)
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_vector
ON chunk_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 9. 建立全文檢索索引 (用於 Hybrid Search)
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS content_tsvector tsvector;

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_tsvector
ON document_chunks
USING gin(content_tsvector);

-- 建立觸發器自動更新 tsvector
CREATE OR REPLACE FUNCTION document_chunks_content_trigger() RETURNS trigger AS $$
BEGIN
  NEW.content_tsvector := to_tsvector('english', COALESCE(NEW.content, ''));
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvector_update_trigger
BEFORE INSERT OR UPDATE ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION document_chunks_content_trigger();
```

---

### 1.4 建立向量搜尋函數

```sql
-- Hybrid Search 函數（結合全文檢索和向量搜尋）
CREATE OR REPLACE FUNCTION hybrid_search (
  query_text text,
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 5,
  collection_id_filter uuid DEFAULT NULL
)
RETURNS TABLE (
  chunk_id uuid,
  document_id uuid,
  filename varchar,
  content text,
  similarity_score float,
  rank float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id AS chunk_id,
    dc.document_id,
    d.filename,
    dc.content,
    (1 - (ce.embedding <=> query_embedding)) AS similarity_score,
    ts_rank(dc.content_tsvector, plainto_tsquery('english', query_text)) AS rank
  FROM document_chunks dc
  JOIN chunk_embeddings ce ON dc.id = ce.chunk_id
  JOIN documents d ON dc.document_id = d.id
  WHERE
    (collection_id_filter IS NULL OR d.collection_id = collection_id_filter)
    AND (
      -- Vector similarity
      (1 - (ce.embedding <=> query_embedding)) >= match_threshold
      OR
      -- Full-text search
      dc.content_tsvector @@ plainto_tsquery('english', query_text)
    )
  ORDER BY
    -- 結合向量相似度和全文搜尋排名
    ((1 - (ce.embedding <=> query_embedding)) * 0.7 + ts_rank(dc.content_tsvector, plainto_tsquery('english', query_text)) * 0.3) DESC
  LIMIT match_count;
END;
$$;
```

---

### 1.5 取得 Supabase 連線資訊

1. Supabase Dashboard → **Settings** → **Database**
2. 複製 **Connection String**：

```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

3. 取得 API Keys (Settings → API)：
   - **Project URL**: `https://[PROJECT-REF].supabase.co`
   - **service_role**: 後端使用

---

## 步驟 2: 安裝 Kotaemon

### 方案 A: Docker 安裝（推薦）

```bash
# 1. Pull Docker image
docker pull ghcr.io/cinnamon/kotaemon:main

# 2. 建立本地資料夾（存放設定檔）
mkdir -p ~/.kotaemon
cd ~/.kotaemon

# 3. 建立 .env 檔案（下一步驟會設定）
touch .env
```

---

### 方案 B: 從源碼安裝

```bash
# 1. Clone repo
git clone https://github.com/Cinnamon/kotaemon.git
cd kotaemon

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 建立 .env 檔案
cp .env.example .env
```

---

## 步驟 3: 設定環境變數

### 3.1 編輯 .env 檔案

```bash
# 在 ~/.kotaemon/.env 或專案根目錄的 .env
vim .env
```

---

### 3.2 設定 .env 內容

```bash
# ========================================
# 基本設定
# ========================================
APP_NAME=Kotaemon RAG
APP_HOST=0.0.0.0
APP_PORT=7860

# ========================================
# Supabase Database 設定
# ========================================
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# 或分開設定
DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.[YOUR-PROJECT-REF]
DB_PASSWORD=[YOUR-SUPABASE-PASSWORD]

# ========================================
# Supabase API 設定
# ========================================
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_SERVICE_KEY=[YOUR-SERVICE-ROLE-KEY]

# ========================================
# OpenAI API 設定
# ========================================
OPENAI_API_KEY=sk-proj-YOUR-OPENAI-API-KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-3.5-turbo

# 可選：使用 Azure OpenAI
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=your-azure-key
# AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo

# ========================================
# Vector Store 設定
# ========================================
VECTOR_STORE=supabase
VECTOR_DIMENSION=1536  # OpenAI text-embedding-3-small

# ========================================
# 文件處理設定
# ========================================
CHUNK_SIZE=400
CHUNK_OVERLAP=80
MAX_FILE_SIZE=50  # MB

# ========================================
# Retrieval 設定
# ========================================
TOP_K=5
SIMILARITY_THRESHOLD=0.5
HYBRID_SEARCH_ENABLED=true
HYBRID_VECTOR_WEIGHT=0.7
HYBRID_FULLTEXT_WEIGHT=0.3

# ========================================
# 使用者認證設定
# ========================================
ENABLE_AUTH=true
SECRET_KEY=your-secret-key-at-least-32-characters-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# 預設管理員帳號（首次啟動時建立）
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123456
DEFAULT_ADMIN_EMAIL=admin@example.com

# ========================================
# Storage 設定（檔案上傳）
# ========================================
STORAGE_TYPE=supabase
SUPABASE_BUCKET_NAME=kotaemon-files

# 或使用本地儲存
# STORAGE_TYPE=local
# LOCAL_STORAGE_PATH=./uploads

# ========================================
# 其他設定
# ========================================
LOG_LEVEL=INFO
DEBUG=false

# Gradio 介面設定
GRADIO_THEME=default  # default, soft, huggingface
GRADIO_SHARE=false
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
```

---

### 3.3 建立 Supabase Storage Bucket

1. Supabase Dashboard → **Storage**
2. 建立 Bucket：
   - **Name**: `kotaemon-files`
   - **Public**: ✅ 勾選

---

## 步驟 4: 使用 Kotaemon

### 4.1 啟動 Kotaemon

**使用 Docker**：

```bash
# 啟動（掛載 .env 檔案）
docker run -d \
  --name kotaemon \
  -p 7860:7860 \
  -v ~/.kotaemon/.env:/app/.env \
  -v ~/.kotaemon/uploads:/app/uploads \
  ghcr.io/cinnamon/kotaemon:main

# 查看日誌
docker logs -f kotaemon
```

**從源碼啟動**：

```bash
# 確保虛擬環境已啟動
source venv/bin/activate

# 啟動
python app.py

# 或使用 Gradio
gradio app.py
```

---

### 4.2 開啟 Web UI

瀏覽器前往：**http://localhost:7860**

你會看到 Kotaemon 的登入頁面。

---

### 4.3 登入

使用預設管理員帳號：
- **Username**: `admin`
- **Password**: `admin123456`

**建議**：登入後立即修改密碼！

---

### 4.4 建立文件集合 (Collection)

1. 點擊左側選單 → **Collections**
2. 點擊「New Collection」
3. 設定：
   - **Name**: `產品說明文件`
   - **Description**: `所有產品說明相關的文件`
   - **Public**: 取消勾選（私人）或勾選（公開）

4. 點擊「Create」

---

### 4.5 上傳文件

1. 進入剛建立的 Collection
2. 點擊「Upload Documents」
3. 選擇檔案（支援批次上傳）：
   - PDF
   - DOCX
   - TXT
   - Markdown
   - CSV

4. 點擊「Upload」

Kotaemon 會自動：
- 上傳檔案到 Supabase Storage
- 提取文字內容
- 切片 (Chunking)
- 調用 OpenAI API 生成 embeddings
- 儲存到 Supabase

5. 等待處理完成（右上角會顯示進度）

---

### 4.6 開始對話

1. 點擊左側選單 → **Chat**
2. 選擇一個 Collection（例如「產品說明文件」）
3. 在對話框輸入問題：
   ```
   這個產品有哪些主要功能？
   ```

4. Kotaemon 會：
   - 將問題轉成 embedding
   - 使用 Hybrid Search 搜尋相關文件 (pgvector + full-text)
   - 將檢索結果送給 OpenAI GPT
   - 返回答案，並顯示來源引用

**範例對話**：

```
👤 使用者：這個產品支援哪些付款方式？

🤖 Kotaemon：
根據文件內容，本產品支援以下付款方式：

1. **信用卡支付**：支援 Visa、Mastercard、JCB
2. **行動支付**：Apple Pay、Google Pay
3. **銀行轉帳**：提供虛擬帳號
4. **超商代碼繳費**：7-11、全家、萊爾富

📄 來源：
- 產品功能說明.pdf (第 5 頁)
- 付款方式說明.docx (第 2 頁)
```

---

### 4.7 查看引用來源 (Citations)

Kotaemon 的特色是會顯示「來源引用」：

1. 在回答下方，會列出引用的文件片段
2. 點擊可以展開查看完整內容
3. 可以直接跳轉到原始文件

---

## 步驟 5: 部署到生產環境

### 選項 1: 部署到 Cloud Run

```bash
# 1. 建立 Dockerfile（Kotaemon 已提供）
cd kotaemon

# 2. 建立 Docker image
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/kotaemon

# 3. 部署
gcloud run deploy kotaemon \
  --image gcr.io/YOUR-PROJECT-ID/kotaemon \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="YOUR-SUPABASE-URL" \
  --set-env-vars OPENAI_API_KEY="YOUR-KEY" \
  --set-env-vars SUPABASE_URL="YOUR-SUPABASE-URL" \
  --set-env-vars SUPABASE_SERVICE_KEY="YOUR-KEY"
```

---

### 選項 2: 部署到 Hugging Face Spaces

Kotaemon 提供了 Hugging Face Spaces 的 demo：

1. Fork Kotaemon repo
2. 建立 Hugging Face Space
3. 連結 GitHub repo
4. 設定 Secrets（環境變數）
5. 部署完成！

---

### 選項 3: 使用 Docker Compose

建立 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  kotaemon:
    image: ghcr.io/cinnamon/kotaemon:main
    ports:
      - "7860:7860"
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  # 可選：加入 Nginx 作為反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - kotaemon
    restart: unless-stopped
```

啟動：

```bash
docker compose up -d
```

---

## 常見問題排解

### Q1: 無法連線到 Supabase

**錯誤訊息**：`connection refused` 或 `timeout`

**解決方法**：
1. 檢查 `DATABASE_URL` 格式是否正確
2. 測試連線：
   ```bash
   psql "postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
   ```

3. 確認 Supabase 專案正常運行（Dashboard 可以打開）

---

### Q2: 上傳文件後卡在 "Processing"

**原因**：OpenAI API 調用失敗，或 Worker 沒有正常運行

**解決方法**：
1. 檢查日誌：
   ```bash
   docker logs -f kotaemon
   ```

2. 驗證 OpenAI API Key：
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. 重新上傳文件

---

### Q3: Hybrid Search 沒有效果

**原因**：全文檢索索引沒有建立，或 tsvector 沒有更新

**解決方法**：
1. 檢查 `content_tsvector` 欄位是否存在：
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'document_chunks';
   ```

2. 手動更新 tsvector：
   ```sql
   UPDATE document_chunks
   SET content_tsvector = to_tsvector('english', content);
   ```

3. 重建索引：
   ```sql
   REINDEX INDEX idx_document_chunks_content_tsvector;
   ```

---

### Q4: 搜尋沒有結果

**原因**：Similarity threshold 太高

**解決方法**：
1. 降低 `SIMILARITY_THRESHOLD`（從 0.5 改成 0.3）
2. 調整 `HYBRID_VECTOR_WEIGHT` 和 `HYBRID_FULLTEXT_WEIGHT`
3. 檢查 Supabase 中是否有資料：
   ```sql
   SELECT COUNT(*) FROM documents;
   SELECT COUNT(*) FROM document_chunks;
   SELECT COUNT(*) FROM chunk_embeddings;
   ```

---

### Q5: 多使用者登入問題

**錯誤訊息**：`Invalid credentials`

**解決方法**：
1. 確認 `ENABLE_AUTH=true`
2. 檢查 `users` 表格是否存在
3. 重設管理員密碼：
   ```sql
   UPDATE users
   SET password_hash = crypt('new-password', gen_salt('bf'))
   WHERE username = 'admin';
   ```

---

## 進階功能

### 1. 使用 OCR 提取圖片中的文字

Kotaemon 支援 OCR（需要額外安裝）：

```bash
# 安裝 Tesseract
# Mac
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr

# 安裝 Python 套件
pip install pytesseract pdf2image
```

在 `.env` 啟用：

```bash
ENABLE_OCR=true
OCR_LANGUAGE=eng+chi_tra  # 英文 + 繁體中文
```

---

### 2. 使用本地 LLM（Ollama）

```bash
# 1. 安裝 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 下載模型
ollama pull llama2
ollama pull nomic-embed-text  # Embedding model

# 3. 設定 .env
OPENAI_API_KEY=""  # 留空
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

---

### 3. 自訂 Prompt Template

在 Kotaemon UI → **Settings** → **Prompt Templates**：

```
你是一個專業的產品說明助手。
請根據以下文件內容回答使用者的問題。

文件內容：
{context}

使用者問題：
{question}

回答規則：
1. 如果文件中有相關資訊，請詳細回答
2. 如果文件中沒有，請告知「文件中沒有這個資訊」
3. 回答時請引用來源文件
4. 使用繁體中文回答
5. 保持專業但友善的語氣

回答：
```

---

### 4. 設定 Re-ranking（未來功能）

Kotaemon 計劃支援 Cohere Rerank API，提升檢索準確度。

---

## 效能優化

### 1. 調整 Chunking 策略

在 `.env` 中：

```bash
# 較小的 chunk 適合精確問答
CHUNK_SIZE=300
CHUNK_OVERLAP=50

# 較大的 chunk 適合長篇摘要
CHUNK_SIZE=600
CHUNK_OVERLAP=100
```

---

### 2. 調整 Hybrid Search 權重

```bash
# 更重視向量搜尋
HYBRID_VECTOR_WEIGHT=0.8
HYBRID_FULLTEXT_WEIGHT=0.2

# 更重視關鍵字搜尋
HYBRID_VECTOR_WEIGHT=0.5
HYBRID_FULLTEXT_WEIGHT=0.5
```

---

### 3. 優化向量索引

在 Supabase 中調整 HNSW 參數：

```sql
-- 更快的搜尋，但準確度稍低
DROP INDEX IF EXISTS idx_chunk_embeddings_vector;
CREATE INDEX idx_chunk_embeddings_vector
ON chunk_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 8, ef_construction = 32);

-- 更準確，但搜尋較慢
DROP INDEX IF EXISTS idx_chunk_embeddings_vector;
CREATE INDEX idx_chunk_embeddings_vector
ON chunk_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);
```

---

## 總結

你現在有一個完整的 Kotaemon + Supabase RAG 系統！

**功能清單**：
- ✅ 美觀的 Gradio UI
- ✅ 多使用者登入與權限管理
- ✅ 文件集合管理
- ✅ 批次上傳文件
- ✅ Hybrid Search (向量 + 全文)
- ✅ 來源引用 (Citations)
- ✅ 對話歷史記錄
- ✅ OCR 支援（可選）

**優勢**：
- 🎨 UI 美觀，使用者體驗佳
- 👥 支援多使用者
- 🔍 Hybrid Search 提升準確度
- 📄 清楚的來源引用
- 🔐 內建權限管理

**成本估算** (每月)：
- Kotaemon: $0 (開源)
- Supabase Free Plan: $0
- OpenAI API: ~$10-50
- Cloud Run (如果部署): ~$20
- **總計**: $10-70/月

**下一步**：
1. 上傳你的產品說明文件
2. 建立不同的 Collections（依產品分類）
3. 調整 Retrieval 參數
4. 測試 Hybrid Search 效果
5. 部署到生產環境

---

**需要協助？**
- Kotaemon GitHub: https://github.com/Cinnamon/kotaemon
- Kotaemon 文檔: https://cinnamon.github.io/kotaemon
- Kotaemon Demo: https://huggingface.co/spaces/cin-model/kotaemon
