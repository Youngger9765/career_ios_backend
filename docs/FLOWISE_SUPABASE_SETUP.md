# Flowise + Supabase 完整啟動文件

## 📋 目錄

- [系統需求](#系統需求)
- [架構說明](#架構說明)
- [步驟 1: 準備 Supabase](#步驟-1-準備-supabase)
- [步驟 2: 安裝 Flowise](#步驟-2-安裝-flowise)
- [步驟 3: 設定環境變數](#步驟-3-設定環境變數)
- [步驟 4: 建立 RAG Flow](#步驟-4-建立-rag-flow)
- [步驟 5: 測試與部署](#步驟-5-測試與部署)
- [常見問題排解](#常見問題排解)

---

## 系統需求

- Node.js 18+
- Docker 20.10+ (可選)
- 2GB+ RAM
- Supabase 帳號
- OpenAI API Key

---

## 架構說明

```
┌─────────────────────────────────────────────────────────┐
│                  Flowise 架構                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────┐          │
│  │      Flowise UI (視覺化編輯器)            │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │ PDF    │→ │ Text   │→ │Supabase│      │          │
│  │  │ Loader │  │Splitter│  │ Vector │      │          │
│  │  └────────┘  └────────┘  └────────┘      │          │
│  │                               ↓           │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │          │
│  │  │Chatbot │← │ OpenAI │← │Retriever│     │          │
│  │  │  UI    │  │ GPT-4  │  │ Top 5  │      │          │
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
│           │  (Embeddings +   │                          │
│           │    Chat)         │                          │
│           └──────────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

**說明**：
- **Flowise UI**: 拖拉式視覺化編輯器
- **Document Loaders**: 載入各種格式的文件 (PDF, CSV, TXT 等)
- **Text Splitters**: 將文件切成 chunks
- **Vector Store**: Supabase pgvector 儲存 embeddings
- **Retrievers**: 從向量資料庫檢索相關文件
- **LLM**: OpenAI GPT 生成回答
- **Chatbot UI**: 內建的對話介面

---

## 步驟 1: 準備 Supabase

### 1.1 建立 Supabase 專案

1. 前往 https://supabase.com
2. 建立新專案：
   - **Name**: `flowise-rag`
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

Flowise 使用的資料庫架構較簡單，執行以下 SQL：

```sql
-- 1. 建立 documents 表格
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 建立 embeddings 表格（使用 pgvector）
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 建立索引
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id ON document_embeddings(document_id);

-- 4. 建立向量索引（HNSW 算法）
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector
ON document_embeddings
USING hnsw (embedding vector_cosine_ops);

-- 5. 建立 Flowise 內部表格（用於存放 Chatflows）
CREATE TABLE IF NOT EXISTS chat_flow (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    flow_data JSONB NOT NULL,
    deployed BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    api_config JSONB,
    analytics JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 建立 Chat Message History 表格
CREATE TABLE IF NOT EXISTS chat_message (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    chatflow_id UUID,
    session_id VARCHAR(255),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 建立索引
CREATE INDEX IF NOT EXISTS idx_chat_message_chatflow_id ON chat_message(chatflow_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_session_id ON chat_message(session_id);
```

---

### 1.4 取得 Supabase 連線資訊

1. Supabase Dashboard → **Settings** → **Database**
2. 複製 **Connection String (URI)**：

```
postgresql://postgres.[PROJECT-REF]:YOUR_DB_PASSWORD_HERE@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

3. 取得 API Keys (Settings → API)：
   - **Project URL**: `https://[PROJECT-REF].supabase.co`
   - **anon public**: 前端使用
   - **service_role**: 後端使用

---

## 步驟 2: 安裝 Flowise

### 方案 A: NPM 安裝（推薦開發）

```bash
# 1. 安裝 Flowise
npm install -g flowise

# 2. 啟動
npx flowise start

# 3. 開啟瀏覽器
open http://localhost:3000
```

---

### 方案 B: Docker 安裝（推薦生產）

```bash
# 1. 使用官方 Docker image
docker run -d \
  --name flowise \
  -p 3000:3000 \
  -v ~/.flowise:/root/.flowise \
  flowiseai/flowise

# 2. 開啟瀏覽器
open http://localhost:3000
```

---

### 方案 C: 從源碼安裝（開發者）

```bash
# 1. Clone repo
git clone https://github.com/FlowiseAI/Flowise.git
cd Flowise

# 2. 安裝依賴
npm install

# 3. 建立所有套件
npm run build

# 4. 啟動
npm start

# 5. 開啟瀏覽器
open http://localhost:3000
```

---

## 步驟 3: 設定環境變數

### 3.1 建立 .env 檔案

```bash
# 在 Flowise 根目錄或 ~/.flowise/ 目錄建立 .env
cd ~/.flowise
touch .env
```

---

### 3.2 設定 .env 內容

```bash
# ========================================
# 基本設定
# ========================================
PORT=3000
FLOWISE_USERNAME=admin
FLOWISE_PASSWORD=YOUR_ADMIN_PASSWORD_HERE
PASSPHRASE=your-secret-passphrase

# ========================================
# Supabase Database 設定
# ========================================
DATABASE_TYPE=postgres
DATABASE_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DATABASE_PORT=6543
DATABASE_USER=postgres.[YOUR-PROJECT-REF]
DATABASE_PASSWORD=[YOUR-SUPABASE-PASSWORD]
DATABASE_NAME=postgres

# 或直接使用 Connection String
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:YOUR_DB_PASSWORD_HERE@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# ========================================
# OpenAI API 設定
# ========================================
OPENAI_API_KEY=sk-proj-YOUR-OPENAI-API-KEY

# ========================================
# Supabase Vector Store 設定
# ========================================
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=[YOUR-SERVICE-ROLE-KEY]

# ========================================
# 其他設定
# ========================================
LOG_LEVEL=info
LOG_PATH=~/.flowise/logs

# CORS 設定（如果需要跨域）
CORS_ORIGINS=*

# 執行模式
EXECUTION_MODE=main

# Debug 模式
DEBUG=false
```

---

### 3.3 重啟 Flowise

```bash
# 如果使用 NPM
npx flowise start

# 如果使用 Docker
docker restart flowise

# 如果從源碼運行
npm start
```

---

## 步驟 4: 建立 RAG Flow

### 4.1 登入 Flowise

1. 開啟 http://localhost:3000
2. 使用設定的帳密登入：
   - **Username**: admin
   - **Password**: YOUR_ADMIN_PASSWORD_HERE

---

### 4.2 建立新的 Chatflow

1. 點擊「Add New」按鈕
2. 命名：「產品說明 RAG Chatbot」
3. 進入視覺化編輯器

---

### 4.3 拖拉建立 RAG 流程

Flowise 是視覺化的，你需要拖拉以下節點並連接：

#### **節點 1: Document Loader (PDF File)**

1. 左側選單 → **Document Loaders** → 拖拉「**PDF File**」到畫布
2. 設定：
   - **PDF File**: 上傳你的 PDF 文件
   - 或選擇「**Folder with Files**」批次上傳多個檔案

---

#### **節點 2: Text Splitter (Recursive Character Text Splitter)**

1. 左側選單 → **Text Splitters** → 拖拉「**Recursive Character Text Splitter**」
2. 設定：
   - **Chunk Size**: 400
   - **Chunk Overlap**: 80

3. 連接：**PDF File** → **Text Splitter**

---

#### **節點 3: Embeddings (OpenAI Embeddings)**

1. 左側選單 → **Embeddings** → 拖拉「**OpenAI Embeddings**」
2. 設定：
   - **Model Name**: `text-embedding-3-small`
   - **OpenAI API Key**: 輸入你的 API Key (或使用環境變數 `OPENAI_API_KEY`)

---

#### **節點 4: Vector Store (Supabase)**

1. 左側選單 → **Vector Stores** → 拖拉「**Supabase**」
2. 設定：
   - **Supabase Project URL**: `https://[YOUR-PROJECT-REF].supabase.co`
   - **Supabase API Key**: Service Role Key
   - **Table Name**: `documents`
   - **Query Name**: `match_documents` (向量搜尋函數)

3. 連接：
   - **Text Splitter** → **Supabase** (Document 輸入)
   - **OpenAI Embeddings** → **Supabase** (Embeddings 輸入)

---

#### **節點 5: Retriever (Supabase Retriever)**

1. 左側選單 → **Retrievers** → 拖拉「**Vector Store Retriever**」
2. 設定：
   - **Vector Store**: 選擇剛建立的 Supabase 節點
   - **Top K**: 5
   - **Search Type**: `similarity` (相似度搜尋)

---

#### **節點 6: LLM (ChatOpenAI)**

1. 左側選單 → **Chat Models** → 拖拉「**ChatOpenAI**」
2. 設定：
   - **Model Name**: `gpt-3.5-turbo` 或 `gpt-4`
   - **Temperature**: 0.7
   - **Max Tokens**: 1000
   - **OpenAI API Key**: 輸入你的 API Key

---

#### **節點 7: Chain (Conversational Retrieval QA Chain)**

1. 左側選單 → **Chains** → 拖拉「**Conversational Retrieval QA Chain**」
2. 設定：
   - **System Message**:
     ```
     你是一個專業的產品說明助手。
     根據提供的文件內容回答使用者問題。
     如果文件中沒有相關資訊，請誠實告知。
     回答時請使用繁體中文。
     ```

3. 連接：
   - **Retriever** → **Chain** (Retriever 輸入)
   - **ChatOpenAI** → **Chain** (LLM 輸入)

---

### 4.4 建立 Supabase Match Function（重要！）

Supabase 需要一個函數來執行向量搜尋。回到 Supabase SQL Editor 執行：

```sql
-- 建立向量相似度搜尋函數
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  page_content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.page_content,
    d.metadata,
    1 - (de.embedding <=> query_embedding) AS similarity
  FROM documents d
  JOIN document_embeddings de ON d.id = de.document_id
  WHERE 1 - (de.embedding <=> query_embedding) >= match_threshold
  ORDER BY de.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

---

### 4.5 完整的 Flow 連接圖

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│  PDF File   │ ───> │ Text Splitter    │ ───> │  Supabase   │
│  Loader     │      │ (Chunk 400)      │      │ Vector Store│
└─────────────┘      └──────────────────┘      └─────────────┘
                              │                         ▲
                              │                         │
                              ▼                         │
                     ┌──────────────────┐               │
                     │ OpenAI Embeddings│───────────────┘
                     └──────────────────┘

                     ┌─────────────────┐
                     │  Supabase       │
                     │  Retriever      │
                     │  (Top K = 5)    │
                     └─────────────────┘
                              │
                              ▼
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Chatbot    │ <─── │ Conversational   │ <─── │  ChatOpenAI │
│    UI       │      │  Retrieval Chain │      │  (GPT-3.5)  │
└─────────────┘      └──────────────────┘      └─────────────┘
```

---

### 4.6 Upsert Documents (上傳文件)

1. 點擊右上角的「**Upsert**」按鈕
2. Flowise 會：
   - 讀取 PDF 檔案
   - 切片成 chunks
   - 調用 OpenAI API 生成 embeddings
   - 儲存到 Supabase

3. 等待完成（查看右下角的進度）

---

### 4.7 測試 Chatbot

1. 點擊右上角的「**Save**」儲存 Chatflow
2. 點擊「**Chat**」按鈕開啟測試視窗
3. 輸入問題測試，例如：
   ```
   這個產品有哪些功能？
   ```

4. Chatbot 會：
   - 將問題轉成 embedding
   - 在 Supabase 中搜尋相似文件
   - 將檢索結果送給 OpenAI GPT
   - 返回答案

---

## 步驟 5: 測試與部署

### 5.1 測試向量搜尋

在 Supabase SQL Editor 測試：

```sql
-- 查看上傳的文件數量
SELECT COUNT(*) FROM documents;

-- 查看 embeddings 數量
SELECT COUNT(*) FROM document_embeddings;

-- 測試向量搜尋（需要先生成 query embedding）
-- 這裡只是範例，實際使用時由 Flowise 處理
SELECT * FROM match_documents(
  '[0.1, 0.2, ...]'::vector,  -- 這裡放 query embedding
  0.5,  -- similarity threshold
  5     -- top k
);
```

---

### 5.2 取得 API Endpoint

1. 在 Chatflow 頁面，點擊「**API**」按鈕
2. 複製 API Endpoint：
   ```
   POST http://localhost:3000/api/v1/prediction/[CHATFLOW-ID]
   ```

3. 測試 API：
   ```bash
   curl -X POST http://localhost:3000/api/v1/prediction/[CHATFLOW-ID] \
     -H "Content-Type: application/json" \
     -d '{
       "question": "這個產品有哪些功能？"
     }'
   ```

---

### 5.3 嵌入到網站

**方案 A: 使用 Flowise Embed**

```html
<script type="module">
  import Chatbot from 'https://cdn.jsdelivr.net/npm/flowise-embed/dist/web.js'
  Chatbot.init({
    chatflowid: '[YOUR-CHATFLOW-ID]',
    apiHost: 'http://localhost:3000',
  })
</script>
```

**方案 B: 使用 iframe**

```html
<iframe
  src="http://localhost:3000/chatbot/[YOUR-CHATFLOW-ID]"
  style="width: 100%; height: 600px; border: none;">
</iframe>
```

---

### 5.4 部署到生產環境

#### **選項 1: 部署到 Railway**

1. 前往 https://railway.app
2. 點擊「New Project」→「Deploy from GitHub repo」
3. 選擇 Flowise repo（或 fork 一個）
4. 設定環境變數（使用 Railway Dashboard）
5. 部署完成，取得 URL

---

#### **選項 2: 部署到 Cloud Run**

```bash
# 1. 建立 Dockerfile（Flowise 已提供）
cd Flowise

# 2. 建立 Docker image
docker build -t flowise:latest .

# 3. 推送到 Google Container Registry
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/flowise

# 4. 部署到 Cloud Run
gcloud run deploy flowise \
  --image gcr.io/YOUR-PROJECT-ID/flowise \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="YOUR-SUPABASE-URL" \
  --set-env-vars OPENAI_API_KEY="YOUR-KEY" \
  --set-env-vars SUPABASE_URL="YOUR-SUPABASE-URL" \
  --set-env-vars SUPABASE_SERVICE_ROLE_KEY="YOUR-KEY"
```

---

#### **選項 3: 部署到 Vercel（僅前端）**

Flowise 的 Web UI 可以部署到 Vercel，但後端需要另外部署。

---

## 常見問題排解

### Q1: Supabase Vector Store 連線失敗

**錯誤訊息**：`Error: Supabase client initialization failed`

**解決方法**：
1. 檢查 `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY` 是否正確
2. 確認使用的是 **Service Role Key**（不是 anon key）
3. 測試連線：
   ```bash
   curl https://[YOUR-PROJECT-REF].supabase.co/rest/v1/documents \
     -H "apikey: YOUR-SERVICE-ROLE-KEY" \
     -H "Authorization: Bearer YOUR-SERVICE-ROLE-KEY"
   ```

---

### Q2: Upsert 文件時出錯

**錯誤訊息**：`Error: Failed to upsert document`

**解決方法**：
1. 檢查 Supabase 中的 `match_documents` 函數是否建立
2. 確認 `documents` 和 `document_embeddings` 表格存在
3. 檢查 OpenAI API Key 是否有效：
   ```bash
   curl https://api.openai.com/v1/embeddings \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "input": "test",
       "model": "text-embedding-3-small"
     }'
   ```

---

### Q3: 搜尋沒有結果

**原因**：Similarity threshold 太高，或文件沒有正確上傳

**解決方法**：
1. 降低 Retriever 的 `match_threshold`（從 0.5 改成 0.3）
2. 檢查 Supabase 中的資料：
   ```sql
   SELECT COUNT(*) FROM documents;
   SELECT COUNT(*) FROM document_embeddings;
   ```

3. 重新 Upsert 文件

---

### Q4: Flowise UI 顯示空白

**原因**：環境變數設定錯誤，或資料庫連線失敗

**解決方法**：
1. 檢查 Flowise 日誌：
   ```bash
   # 如果使用 Docker
   docker logs flowise

   # 如果使用 NPM
   cat ~/.flowise/logs/flowise.log
   ```

2. 確認 `DATABASE_URL` 格式正確
3. 重啟 Flowise

---

### Q5: 如何更新文件？

**方法 1：Delete + Re-upsert**
1. 在 Supabase SQL Editor 刪除舊資料：
   ```sql
   DELETE FROM documents WHERE metadata->>'source' = 'old-doc.pdf';
   ```

2. 在 Flowise 重新 Upsert 新文件

**方法 2：使用不同的 Table Name**
- 為每個文件集合使用不同的 table (e.g., `documents_v1`, `documents_v2`)

---

## 進階功能

### 1. 使用 Memory (對話記憶)

在 Conversational Retrieval QA Chain 中：
1. 啟用「**Buffer Memory**」或「**Supabase Chat Memory**」
2. 設定 `session_id`（用於區分不同使用者）

---

### 2. 使用不同的 Embedding Model

除了 OpenAI，Flowise 還支援：
- **HuggingFace Embeddings** (免費，但效果較差)
- **Cohere Embeddings**
- **Local Embeddings** (使用 Ollama)

---

### 3. 使用本地 LLM (Ollama)

1. 安裝 Ollama: https://ollama.ai
2. 下載模型：`ollama pull llama2`
3. 在 Flowise 中使用「**Ollama**」節點替換 ChatOpenAI

---

### 4. 加入 Re-ranking (提升準確度)

1. 在 Retriever 後面加入「**Cohere Rerank**」節點
2. 設定 Cohere API Key
3. Rerank 會重新排序檢索結果，提升準確度

---

## 效能優化

### 1. 調整 Chunk Size

根據文件類型調整：
- **技術文檔**: Chunk Size 600-800
- **FAQ**: Chunk Size 200-300
- **長篇文章**: Chunk Size 400-500

---

### 2. 使用 Hybrid Search

Flowise 即將支援 Hybrid Search（結合關鍵字和向量搜尋）。

---

### 3. 優化向量索引

在 Supabase 中調整 HNSW 參數：

```sql
-- 重建索引，調整 m 和 ef_construction 參數
DROP INDEX IF EXISTS idx_document_embeddings_vector;
CREATE INDEX idx_document_embeddings_vector
ON document_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

- `m`: 每個節點的鄰居數量（越大越準確，但越慢）
- `ef_construction`: 建立索引時的搜尋深度

---

## 總結

你現在有一個完整的 Flowise + Supabase RAG 系統！

**功能清單**：
- ✅ 視覺化建立 RAG Flow
- ✅ 拖拉式設計（No-code）
- ✅ 支援多種文件格式
- ✅ Supabase pgvector 向量搜尋
- ✅ 對話記憶
- ✅ API 自動生成
- ✅ 可嵌入網站

**優勢**：
- 🎨 視覺化編輯，易於調整
- 🔧 高度可客製化（可替換任何節點）
- 🚀 快速原型開發
- 💰 開源免費

**成本估算** (每月)：
- Flowise: $0 (開源)
- Supabase Free Plan: $0
- OpenAI API: ~$10-50
- Cloud Run (如果部署): ~$20
- **總計**: $10-70/月

**下一步**：
1. 上傳你的產品說明文件
2. 調整 Retrieval 參數（Top K、Threshold）
3. 測試不同的 Prompt
4. 部署到生產環境
5. 監控使用量和成本

---

**需要協助？**
- Flowise 官方文檔: https://docs.flowiseai.com
- Flowise GitHub: https://github.com/FlowiseAI/Flowise
- Flowise Discord: https://discord.gg/jbaHfsRVBW
