# RAG Multi-Agent Architecture

## 目錄
- [概述](#概述)
- [架構設計](#架構設計)
- [資料庫設計](#資料庫設計)
- [程式碼架構](#程式碼架構)
- [遷移路徑](#遷移路徑)
- [效能監控](#效能監控)
- [FAQ](#faq)

---

## 概述

本系統支援多個 AI Agent（職涯諮詢、心理諮詢、財務規劃等），每個 Agent 擁有獨立的知識庫。

### 設計原則

1. **現階段**：單一資料庫 + `agent_id` 過濾（簡單、維護成本低）
2. **未來擴展**：可無痛遷移到多 Schema 隔離（效能優化）
3. **抽象化**：使用 Repository Pattern，業務邏輯不直接操作資料庫

### 方案對比

| 項目 | 單 Bucket + agent_id | 多 Bucket (Schemas) |
|------|---------------------|---------------------|
| **效能** | ⚡️⚡️ 需 WHERE 過濾 | ⚡️⚡️⚡️ 最快 |
| **維護** | ✅ 簡單 | ❌ 複雜 |
| **隔離性** | ⚠️ 邏輯隔離 | ✅ 物理隔離 |
| **彈性** | ✅ 高（跨 agent 查詢） | ❌ 低 |
| **適用場景** | 中小規模（<10萬 chunks/agent） | 大規模（>10萬 chunks/agent） |

---

## 架構設計

### 整體架構圖

```
┌─────────────────────────────────────────────────┐
│                  API Layer                       │
│  /api/rag/query?agent=career                    │
│  /api/rag/ingest?agent=psychology               │
└───────────────┬─────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────┐
│           Repository Factory                     │
│  get_rag_repository() → 根據設定選擇實作         │
└───────┬─────────────────────────┬───────────────┘
        │                         │
        ↓                         ↓
┌───────────────────┐   ┌───────────────────────┐
│ Single Bucket     │   │ Multi Bucket          │
│ Repository        │   │ Repository            │
│ (Phase 1)         │   │ (Phase 2)             │
└─────┬─────────────┘   └─────┬─────────────────┘
      │                       │
      ↓                       ↓
┌─────────────────────────────────────────────────┐
│              PostgreSQL Database                 │
│  Phase 1: public schema (agent_id filter)       │
│  Phase 2: career/psychology/finance schemas     │
└─────────────────────────────────────────────────┘
```

---

## 資料庫設計

### Phase 1: 單 Bucket + agent_id

#### 新增 agents 表

```sql
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,           -- "職涯諮詢"
    slug VARCHAR(50) UNIQUE NOT NULL,     -- "career"
    description TEXT,                      -- 描述
    icon VARCHAR(50),                      -- "💼"
    color VARCHAR(20),                     -- "blue"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 初始資料
INSERT INTO agents (name, slug, description, icon, color) VALUES
('職涯諮詢', 'career', '職涯規劃、求職策略、履歷面試', '💼', 'blue'),
('心理諮詢', 'psychology', '心理健康、情緒管理、壓力調適', '🧠', 'purple'),
('財務規劃', 'finance', '理財投資、退休規劃、保險配置', '💰', 'green');
```

#### 修改 datasources 表

```sql
-- 新增 agent_id 欄位
ALTER TABLE datasources
ADD COLUMN agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE;

-- 建立索引
CREATE INDEX idx_datasources_agent ON datasources(agent_id);
CREATE INDEX idx_documents_datasource ON documents(datasource_id);
```

#### ER Diagram

```
agents (1) ─────< (N) datasources
                       │
                       ↓ (1)
                  documents (N)
                       │
                       ↓ (1)
                   chunks (N)
                       │
                       ↓ (1)
                  embeddings (1)
```

### Phase 2: 多 Bucket (未來遷移)

```sql
-- 建立獨立 schemas
CREATE SCHEMA career;
CREATE SCHEMA psychology;
CREATE SCHEMA finance;

-- 在每個 schema 建立相同結構
CREATE TABLE career.datasources (...);
CREATE TABLE career.documents (...);
CREATE TABLE career.chunks (...);
CREATE TABLE career.embeddings (...);

-- 複製資料（遷移時執行）
INSERT INTO career.datasources
SELECT id, type, source_uri, created_at
FROM public.datasources
WHERE agent_id = 1;
```

---

## 程式碼架構

### 目錄結構

```
app/
├── repositories/
│   ├── __init__.py
│   ├── base.py                    # RAGRepository 抽象介面
│   ├── single_bucket_repo.py     # 單 Bucket 實作
│   ├── multi_bucket_repo.py      # 多 Bucket 實作（未來）
│   └── factory.py                 # 工廠模式：動態選擇實作
├── models/
│   └── agent.py                   # Agent model
├── api/
│   ├── rag_query.py               # 查詢 API
│   └── rag_ingest.py              # 上傳 API
└── core/
    └── config.py                  # RAG_MODE 設定
```

### 1. 抽象介面

**`app/repositories/base.py`**

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.document import Datasource, Document

class RAGRepository(ABC):
    """RAG 資料存取抽象介面"""

    @abstractmethod
    async def get_datasources(self, agent_id: int) -> List[Datasource]:
        """取得特定 agent 的所有 datasources"""
        pass

    @abstractmethod
    async def create_document(
        self,
        agent_id: int,
        title: str,
        file_content: bytes,
        **kwargs
    ) -> Document:
        """建立新文件"""
        pass

    @abstractmethod
    async def search_similar_chunks(
        self,
        agent_id: int,
        query_vector: List[float],
        limit: int = 5
    ) -> List[dict]:
        """向量相似度搜尋"""
        pass

    @abstractmethod
    async def reprocess_document(
        self,
        agent_id: int,
        doc_id: int,
        chunk_size: int,
        overlap: int
    ) -> dict:
        """重新處理文件"""
        pass

    @abstractmethod
    async def delete_document(self, agent_id: int, doc_id: int):
        """刪除文件（含安全檢查）"""
        pass

    @abstractmethod
    async def get_stats(self, agent_id: Optional[int] = None) -> dict:
        """取得統計資料"""
        pass
```

### 2. Single Bucket 實作

**`app/repositories/single_bucket_repo.py`**

```python
from sqlalchemy.orm import Session
from sqlalchemy import text, delete
from app.repositories.base import RAGRepository
from app.models.document import Datasource, Document, Chunk, Embedding

class SingleBucketRepository(RAGRepository):
    """單一資料庫 + agent_id 過濾實作"""

    def __init__(self, db: Session):
        self.db = db

    async def get_datasources(self, agent_id: int) -> List[Datasource]:
        return self.db.query(Datasource)\
            .filter(Datasource.agent_id == agent_id)\
            .all()

    async def create_document(
        self,
        agent_id: int,
        title: str,
        file_content: bytes,
        **kwargs
    ) -> Document:
        from app.services.storage import StorageService
        from app.services.pdf_service import PDFService
        from app.services.chunking import ChunkingService
        from app.services.openai_service import OpenAIService

        # 1. 上傳到 Storage
        storage = StorageService()
        storage_url = await storage.upload_file(
            file_content,
            f"documents/{agent_id}/{title}",
            content_type="application/pdf"
        )

        # 2. 建立 datasource（含 agent_id）
        datasource = Datasource(
            type="pdf",
            agent_id=agent_id,  # ← 關鍵：記錄 agent
            source_uri=storage_url
        )
        self.db.add(datasource)
        self.db.flush()

        # 3. 提取文字並建立 document
        pdf_service = PDFService()
        text = pdf_service.extract_text(file_content)
        metadata = pdf_service.extract_metadata(file_content)

        document = Document(
            datasource_id=datasource.id,
            title=title,
            bytes=len(file_content),
            pages=metadata.get("pages", 0),
            text_length=len(text),
            meta_json=metadata
        )
        self.db.add(document)
        self.db.flush()

        # 4. Chunking
        chunking = ChunkingService(
            chunk_size=kwargs.get("chunk_size", 400),
            overlap=kwargs.get("overlap", 80)
        )
        chunks = chunking.split_text(text, split_by_sentence=True)

        # 5. 生成 embeddings
        openai = OpenAIService()
        for idx, chunk_text in enumerate(chunks):
            chunk = Chunk(
                doc_id=document.id,
                ordinal=idx,
                text=chunk_text,
                meta_json={}
            )
            self.db.add(chunk)
            self.db.flush()

            embedding_vector = await openai.create_embedding(chunk_text)
            embedding = Embedding(
                chunk_id=chunk.id,
                embedding=embedding_vector
            )
            self.db.add(embedding)

        self.db.commit()
        return document

    async def search_similar_chunks(
        self,
        agent_id: int,
        query_vector: List[float],
        limit: int = 5
    ) -> List[dict]:
        """向量搜尋（含 agent_id 過濾）"""
        result = self.db.execute(text("""
            SELECT
                c.text,
                d.title,
                d.id as doc_id,
                e.embedding <=> :query_vector::vector AS distance
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.id
            JOIN documents d ON c.doc_id = d.id
            JOIN datasources ds ON d.datasource_id = ds.id
            WHERE ds.agent_id = :agent_id
            ORDER BY distance
            LIMIT :limit
        """), {
            "agent_id": agent_id,
            "query_vector": query_vector,
            "limit": limit
        })

        return [
            {
                "text": row.text,
                "title": row.title,
                "doc_id": row.doc_id,
                "distance": float(row.distance)
            }
            for row in result
        ]

    async def delete_document(self, agent_id: int, doc_id: int):
        """刪除文件（含安全檢查）"""
        # 驗證 document 是否屬於該 agent
        doc = self.db.query(Document)\
            .join(Datasource)\
            .filter(
                Document.id == doc_id,
                Datasource.agent_id == agent_id  # ← 防止跨 agent 刪除
            ).first()

        if not doc:
            raise ValueError(f"Document {doc_id} not found or access denied")

        # Cascade delete（chunks, embeddings）
        self.db.delete(doc)
        self.db.commit()

    async def get_stats(self, agent_id: Optional[int] = None) -> dict:
        """取得統計資料（可選 agent 過濾）"""
        query = text("""
            SELECT
                d.id,
                d.title,
                d.pages,
                d.bytes,
                d.text_length,
                d.created_at,
                COUNT(c.id) as chunks_count,
                COALESCE(SUM(LENGTH(c.text)), 0) as total_text_chars
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.doc_id
            JOIN datasources ds ON d.datasource_id = ds.id
            WHERE (:agent_id IS NULL OR ds.agent_id = :agent_id)
            GROUP BY d.id, d.title, d.pages, d.bytes, d.text_length, d.created_at
            ORDER BY d.created_at DESC
        """)

        result = self.db.execute(query, {"agent_id": agent_id})
        return result.fetchall()
```

### 3. Multi Bucket 實作（未來用）

**`app/repositories/multi_bucket_repo.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.repositories.base import RAGRepository
from app.core.config import settings

class MultiBucketRepository(RAGRepository):
    """多 Schema 隔離實作"""

    def __init__(self):
        # 每個 agent 對應一個 schema
        self.schema_map = {
            1: 'career',
            2: 'psychology',
            3: 'finance'
        }

        # 建立各 schema 的 engine
        self.engines = {}
        for agent_id, schema in self.schema_map.items():
            self.engines[agent_id] = create_engine(
                settings.DATABASE_URL,
                connect_args={"options": f"-csearch_path={schema}"}
            )

    def _get_session(self, agent_id: int) -> Session:
        """根據 agent_id 取得對應的 DB session"""
        if agent_id not in self.engines:
            raise ValueError(f"Unknown agent_id: {agent_id}")

        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=self.engines[agent_id])
        return SessionLocal()

    async def search_similar_chunks(
        self,
        agent_id: int,
        query_vector: List[float],
        limit: int = 5
    ) -> List[dict]:
        """向量搜尋（不需要 WHERE agent_id，因為已在不同 schema）"""
        db = self._get_session(agent_id)

        result = db.execute(text("""
            SELECT
                c.text,
                d.title,
                d.id as doc_id,
                e.embedding <=> :query_vector::vector AS distance
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.id
            JOIN documents d ON c.doc_id = d.id
            ORDER BY distance
            LIMIT :limit
        """), {"query_vector": query_vector, "limit": limit})

        return [
            {
                "text": row.text,
                "title": row.title,
                "doc_id": row.doc_id,
                "distance": float(row.distance)
            }
            for row in result
        ]

    # ... 其他方法類似實作
```

### 4. 工廠模式

**`app/repositories/factory.py`**

```python
from sqlalchemy.orm import Session
from app.repositories.base import RAGRepository
from app.repositories.single_bucket_repo import SingleBucketRepository
from app.repositories.multi_bucket_repo import MultiBucketRepository
from app.core.config import settings

def get_rag_repository(db: Session = None) -> RAGRepository:
    """
    根據設定動態選擇 Repository 實作

    環境變數 RAG_MODE:
    - "single_bucket": 使用單一資料庫 + agent_id 過濾
    - "multi_bucket": 使用多 Schema 隔離
    """
    mode = settings.RAG_MODE

    if mode == "single_bucket":
        if not db:
            raise ValueError("SingleBucketRepository requires db session")
        return SingleBucketRepository(db)

    elif mode == "multi_bucket":
        return MultiBucketRepository()

    else:
        raise ValueError(f"Unknown RAG_MODE: {mode}. Use 'single_bucket' or 'multi_bucket'")
```

### 5. 設定檔

**`app/core/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... 其他設定

    # RAG 模式：single_bucket 或 multi_bucket
    RAG_MODE: str = "single_bucket"

    class Config:
        env_file = ".env"

settings = Settings()
```

**`.env`**

```bash
# RAG 架構模式
RAG_MODE=single_bucket  # 現階段用這個

# 未來遷移時改成
# RAG_MODE=multi_bucket
```

### 6. API 層使用

**`app/api/rag_query.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.agent import Agent
from app.repositories.factory import get_rag_repository
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/api/rag", tags=["rag"])

@router.post("/query")
async def query_rag(
    query: str,
    agent_slug: str = "career",
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    RAG 查詢（自動根據 agent 過濾知識庫）

    Args:
        query: 使用者問題
        agent_slug: agent 識別碼（career/psychology/finance）
        limit: 回傳結果數量
    """
    # 1. 取得 agent
    agent = db.query(Agent).filter(Agent.slug == agent_slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")

    # 2. 取得 Repository（自動選擇實作）
    repo = get_rag_repository(db)

    # 3. 生成 query embedding
    openai_service = OpenAIService()
    query_vector = await openai_service.create_embedding(query)

    # 4. 搜尋相似 chunks（Repository 會處理 agent 隔離）
    results = await repo.search_similar_chunks(
        agent_id=agent.id,
        query_vector=query_vector,
        limit=limit
    )

    return {
        "agent": agent_slug,
        "query": query,
        "results": results
    }
```

**`app/api/rag_ingest.py`**

```python
@router.post("/ingest")
async def ingest_file(
    file: UploadFile = File(...),
    agent_slug: str = "career",  # ← 新增 agent 參數
    chunk_size: int = 400,
    overlap: int = 80,
    db: Session = Depends(get_db)
):
    """上傳文件到指定 agent 的知識庫"""

    # 1. 驗證 agent
    agent = db.query(Agent).filter(Agent.slug == agent_slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")

    # 2. 讀取檔案
    file_content = await file.read()

    # 3. 使用 Repository 建立文件
    repo = get_rag_repository(db)
    document = await repo.create_document(
        agent_id=agent.id,  # ← 關鍵：指定 agent
        title=file.filename,
        file_content=file_content,
        chunk_size=chunk_size,
        overlap=overlap
    )

    return {
        "message": f"Successfully uploaded to {agent.name}",
        "document_id": document.id,
        "agent": agent_slug
    }
```

---

## 遷移路徑

### Phase 1 → Phase 2 遷移步驟

#### 1. 資料遷移腳本

**`scripts/migrate_to_multi_bucket.py`**

```python
"""
將 Single Bucket 遷移到 Multi Bucket
執行方式：poetry run python scripts/migrate_to_multi_bucket.py
"""

import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.agent import Agent

async def migrate():
    db = SessionLocal()

    print("🚀 開始遷移...")

    # 1. 取得所有 agents
    agents = db.query(Agent).all()
    print(f"📋 找到 {len(agents)} 個 agents")

    # 2. 為每個 agent 建立 schema
    for agent in agents:
        schema = agent.slug
        print(f"\n📦 處理 agent: {agent.name} (schema: {schema})")

        # 建立 schema
        db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        print(f"  ✓ Schema '{schema}' 已建立")

        # 在新 schema 建立 tables
        db.execute(text(f"""
            CREATE TABLE {schema}.datasources (
                id SERIAL PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                source_uri TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        db.execute(text(f"""
            CREATE TABLE {schema}.documents (
                id SERIAL PRIMARY KEY,
                datasource_id INTEGER REFERENCES {schema}.datasources(id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                bytes INTEGER,
                pages INTEGER,
                text_length INTEGER,
                meta_json JSONB DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

        db.execute(text(f"""
            CREATE TABLE {schema}.chunks (
                id SERIAL PRIMARY KEY,
                doc_id INTEGER REFERENCES {schema}.documents(id) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL,
                text TEXT NOT NULL,
                meta_json JSONB DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        db.execute(text(f"""
            CREATE TABLE {schema}.embeddings (
                id SERIAL PRIMARY KEY,
                chunk_id INTEGER REFERENCES {schema}.chunks(id) ON DELETE CASCADE UNIQUE,
                embedding vector(1536),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        print(f"  ✓ Tables 已建立")

        # 3. 複製資料
        # Datasources
        db.execute(text(f"""
            INSERT INTO {schema}.datasources (id, type, source_uri, created_at)
            SELECT id, type, source_uri, created_at
            FROM public.datasources
            WHERE agent_id = :agent_id
        """), {"agent_id": agent.id})

        # Documents
        db.execute(text(f"""
            INSERT INTO {schema}.documents (id, datasource_id, title, bytes, pages, text_length, meta_json, created_at, updated_at)
            SELECT d.id, d.datasource_id, d.title, d.bytes, d.pages, d.text_length, d.meta_json, d.created_at, d.updated_at
            FROM public.documents d
            JOIN public.datasources ds ON d.datasource_id = ds.id
            WHERE ds.agent_id = :agent_id
        """), {"agent_id": agent.id})

        # Chunks
        db.execute(text(f"""
            INSERT INTO {schema}.chunks (id, doc_id, ordinal, text, meta_json, created_at)
            SELECT c.id, c.doc_id, c.ordinal, c.text, c.meta_json, c.created_at
            FROM public.chunks c
            JOIN public.documents d ON c.doc_id = d.id
            JOIN public.datasources ds ON d.datasource_id = ds.id
            WHERE ds.agent_id = :agent_id
        """), {"agent_id": agent.id})

        # Embeddings
        db.execute(text(f"""
            INSERT INTO {schema}.embeddings (id, chunk_id, embedding, created_at)
            SELECT e.id, e.chunk_id, e.embedding, e.created_at
            FROM public.embeddings e
            JOIN public.chunks c ON e.chunk_id = c.id
            JOIN public.documents d ON c.doc_id = d.id
            JOIN public.datasources ds ON d.datasource_id = ds.id
            WHERE ds.agent_id = :agent_id
        """), {"agent_id": agent.id})

        # 建立索引
        db.execute(text(f"""
            CREATE INDEX idx_{schema}_embeddings_vector
            ON {schema}.embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))

        print(f"  ✓ 資料已複製並建立索引")

    db.commit()
    db.close()

    print("\n✅ 遷移完成！")
    print("\n下一步：")
    print("1. 修改 .env: RAG_MODE=multi_bucket")
    print("2. 重啟服務: poetry run uvicorn app.main:app --reload")
    print("3. 測試查詢是否正常")
    print("4. 確認無誤後，可刪除 public schema 的舊資料")

if __name__ == "__main__":
    asyncio.run(migrate())
```

#### 2. 執行遷移

```bash
# 1. 備份資料庫
pg_dump $DATABASE_URL > backup_before_migration.sql

# 2. 執行遷移腳本
poetry run python scripts/migrate_to_multi_bucket.py

# 3. 修改設定
echo "RAG_MODE=multi_bucket" >> .env

# 4. 重啟服務
poetry run uvicorn app.main:app --reload

# 5. 測試
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "如何寫履歷？", "agent_slug": "career"}'
```

#### 3. 回滾方案

```bash
# 如果遷移後有問題，可立即回滾
echo "RAG_MODE=single_bucket" >> .env
poetry run uvicorn app.main:app --reload

# 舊資料仍在 public schema，可繼續使用
```

---

## 效能監控

### 1. 監控指標

**`app/repositories/metrics.py`**

```python
import time
import logging
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)

def track_query_performance(func: Callable):
    """追蹤查詢效能"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start

        # 記錄慢查詢（>2秒）
        if duration > 2.0:
            logger.warning(
                f"⚠️ Slow query detected: {func.__name__} "
                f"took {duration:.3f}s with args={args[1:3]}"
            )
        else:
            logger.info(f"✓ {func.__name__} completed in {duration:.3f}s")

        return result
    return wrapper

# 在 Repository 中使用
class SingleBucketRepository(RAGRepository):
    @track_query_performance
    async def search_similar_chunks(self, agent_id: int, ...):
        # ... 實作
```

### 2. 效能基準

| 指標 | Single Bucket 目標 | Multi Bucket 目標 |
|------|-------------------|------------------|
| 查詢延遲 | <2秒 | <1秒 |
| 上傳處理 | <30秒/文件 | <30秒/文件 |
| Chunks 數量 | <100,000/agent | >100,000/agent |
| 並發查詢 | 10 QPS | 50 QPS |

### 3. 遷移決策樹

```
開始監控
    ↓
查詢延遲 >2秒 ？
    ↓ Yes
Chunks 數量 >100,000 ？
    ↓ Yes
執行遷移到 Multi Bucket
    ↓
監控新環境效能
    ↓
效能改善 >50% ？
    ↓ Yes
保留 Multi Bucket
    ↓
刪除舊資料
```

---

## FAQ

### Q1: 為什麼不一開始就用 Multi Bucket？

**A:**
- 現階段資料量小（<10萬 chunks），Single Bucket 效能足夠
- 維護成本低，適合小團隊
- 保留彈性，未來需要跨 agent 查詢時不用重構

### Q2: 什麼時候該遷移到 Multi Bucket？

**A:** 當你遇到以下情況之一：
- 查詢延遲 >2秒
- 每個 agent 有 >10萬 chunks
- 需要更嚴格的資料隔離
- 有專門的 DBA 團隊維護

### Q3: 遷移會影響服務嗎？

**A:**
- 遷移過程：可以在低峰時段執行，約 10-30 分鐘
- 服務切換：修改 `.env` 並重啟，約 1 分鐘
- 回滾：改回 `RAG_MODE=single_bucket` 即可，無資料損失

### Q4: 可以混合使用嗎？

**A:** 可以！例如：
- 大量資料的 agent（career）用獨立 schema
- 小量資料的 agent（finance）留在 public schema
- 只需在 `MultiBucketRepository` 中加入 fallback 邏輯

### Q5: 跨 agent 查詢怎麼辦？

**A:**
- **Single Bucket**: 簡單，直接不帶 `agent_id` 過濾
- **Multi Bucket**: 複雜，需要 UNION ALL 多個 schema
  ```sql
  SELECT * FROM career.embeddings WHERE ...
  UNION ALL
  SELECT * FROM psychology.embeddings WHERE ...
  ```

### Q6: 如何測試兩種模式的一致性？

**A:** 使用 pytest 的 parametrize：
```python
@pytest.mark.parametrize("mode", ["single_bucket", "multi_bucket"])
async def test_repository_consistency(mode):
    # 切換模式並測試相同操作
    # 驗證結果一致
```

---

## 附錄

### 相關文件
- [RAG Chunking 架構](./RAG_CHUNKING.md)
- [Vector Search 優化](./VECTOR_SEARCH_OPTIMIZATION.md)
- [API 文件](./API.md)

### 技術棧
- PostgreSQL 15+
- pgvector extension
- SQLAlchemy 2.0
- FastAPI
- Supabase (PaaS)

### 維護者
- 架構設計：Claude Code
- 最後更新：2025-10-03
