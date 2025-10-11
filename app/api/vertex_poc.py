"""Vertex AI RAG Engine POC API endpoints"""

import asyncio
import tempfile
import os
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from vertexai import init as vertexai_init
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool
from google.cloud import aiplatform

# Configuration
PROJECT_ID = "groovy-iris-473015-h3"
LOCATION = "us-east4"  # Virginia - GA, no allowlist required (us-central1 needs allowlist)

# Initialize Vertex AI (uses Application Default Credentials)
# Make sure GOOGLE_APPLICATION_CREDENTIALS env var points to correct credentials
# or run: gcloud auth application-default login
vertexai_init(project=PROJECT_ID, location=LOCATION)
aiplatform.init(project=PROJECT_ID, location=LOCATION)

router = APIRouter(prefix="/api/rag/vertex-poc", tags=["vertex-poc"])


# ================================
# Request/Response Models
# ================================

class CreateCorpusRequest(BaseModel):
    display_name: Optional[str] = None
    description: str = "Vertex AI RAG POC Corpus"


class CreateCorpusResponse(BaseModel):
    corpus_name: str
    display_name: str
    status: str
    message: str


class UploadDefaultDocsRequest(BaseModel):
    corpus_name: str


class UploadDefaultDocsResponse(BaseModel):
    corpus_name: str
    files_count: int
    imported_count: int
    status: str


class QueryRequest(BaseModel):
    corpus_name: str
    question: str
    top_k: int = 5
    use_gemini: bool = False


class QueryContext(BaseModel):
    rank: int
    score: float
    text: str
    source: str


class QueryResponse(BaseModel):
    question: str
    method: str
    num_results: int
    contexts: List[QueryContext]
    gemini_response: Optional[str] = None
    processing_time: float


class CompareRequest(BaseModel):
    vertex_corpus_name: str
    question: str
    top_k: int = 5


class CompareResponse(BaseModel):
    question: str
    vertex_results: QueryResponse
    existing_rag_results: dict
    comparison: dict


class CorpusInfo(BaseModel):
    name: str
    display_name: str
    create_time: Optional[str] = None
    description: Optional[str] = None


class ListCorpusResponse(BaseModel):
    corpuses: List[CorpusInfo]
    total: int


# ================================
# Test Documents
# ================================

TEST_DOCUMENTS = [
    {
        "filename": "career_theory_super.txt",
        "content": """職涯發展理論 - Super's Life-Span Theory

Donald Super 提出的生涯發展階段理論，將人的一生劃分為五個主要階段：

1. 成長期（Growth, 0-14歲）
   - 發展自我概念
   - 透過家庭和學校建立對工作世界的態度

2. 探索期（Exploration, 15-24歲）
   - 試探性選擇
   - 透過學校、休閒活動和打工等經驗，縮小職業選擇範圍

3. 建立期（Establishment, 25-44歲）
   - 尋找合適領域
   - 在選定的領域中建立穩定地位

4. 維持期（Maintenance, 45-64歲）
   - 保持已達到的成就
   - 更新技能以維持競爭力

5. 衰退期（Decline, 65歲以上）
   - 逐漸減少工作參與
   - 準備退休生活

應用於諮詢：
- 協助個案了解自己處於哪個生涯階段
- 針對不同階段提供適當的介入策略
- 強調生涯是一個持續發展的過程
"""
    },
    {
        "filename": "career_theory_schein.txt",
        "content": """職涯錨理論 - Schein's Career Anchors

Edgar Schein 提出八種職涯錨（Career Anchors），代表個人在職業選擇中的核心價值：

1. 技術/功能能力（Technical/Functional Competence）
   - 專注於特定領域的專業發展
   - 希望在專業領域成為專家

2. 一般管理能力（General Managerial Competence）
   - 渴望承擔管理責任
   - 希望整合他人的工作

3. 自主/獨立（Autonomy/Independence）
   - 需要按照自己的方式工作
   - 不喜歡被規則限制

4. 安全/穩定（Security/Stability）
   - 追求工作保障
   - 偏好穩定的組織環境

5. 創業創造（Entrepreneurial Creativity）
   - 希望創建新事物
   - 願意承擔風險

6. 服務/奉獻（Service/Dedication）
   - 希望工作能幫助他人或社會
   - 價值觀導向的職業選擇

7. 純粹挑戰（Pure Challenge）
   - 追求克服困難的成就感
   - 喜歡解決複雜問題

8. 生活型態（Lifestyle）
   - 追求工作與生活平衡
   - 職業選擇配合個人生活需求

諮詢應用：
- 協助個案識別自己的職涯錨
- 評估職業選擇與內在價值的契合度
- 解決職涯轉換的內在衝突
"""
    },
    {
        "filename": "career_theory_krumboltz.txt",
        "content": """計劃性偶然理論 - Krumboltz's Planned Happenstance

John Krumboltz 提出的計劃性偶然理論，強調不確定性在職涯發展中的積極角色。

核心概念：
- 個人職涯路徑很少是完全計劃的結果
- 偶然事件對職涯發展有重大影響
- 積極創造和利用偶然機會

五種關鍵態度（OCEAN）：

1. 好奇心（Curiosity）
   - 探索新的學習機會
   - 保持對未知的開放態度

2. 堅持性（Persistence）
   - 面對挫折不放棄
   - 持續努力克服障礙

3. 彈性（Flexibility）
   - 願意改變態度和環境
   - 適應新情況

4. 樂觀（Optimism）
   - 將困難視為機會
   - 相信未來會更好

5. 冒險（Risk-taking）
   - 願意在不確定中行動
   - 接受可能的失敗

諮詢策略：
- 鼓勵個案探索新機會
- 協助個案重新框架「失敗」經驗
- 培養積極面對不確定性的態度
- 建立行動計劃創造偶然機會
"""
    }
]


# ================================
# API Endpoints
# ================================

@router.post("/corpus/create", response_model=CreateCorpusResponse)
async def create_corpus(request: CreateCorpusRequest):
    """建立 Vertex AI RAG Corpus"""
    try:
        display_name = request.display_name or f"poc-corpus-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        corpus = rag.create_corpus(
            display_name=display_name,
            description=request.description,
        )

        return CreateCorpusResponse(
            corpus_name=corpus.name,
            display_name=display_name,
            status="success",
            message=f"Corpus created successfully: {corpus.name}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create corpus: {str(e)}")


@router.delete("/corpus/{corpus_name:path}")
async def delete_corpus(corpus_name: str):
    """刪除 Vertex AI RAG Corpus"""
    try:
        rag.delete_corpus(name=corpus_name)
        return {"status": "success", "message": f"Corpus deleted: {corpus_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete corpus: {str(e)}")


@router.get("/corpus/list", response_model=ListCorpusResponse)
async def list_corpuses():
    """列出所有 POC Corpus（顯示名稱包含 'poc'）"""
    try:
        # List all corpuses
        corpuses = rag.list_corpora()

        # Filter POC corpuses
        poc_corpuses = []
        for corpus in corpuses:
            if "poc" in corpus.display_name.lower():
                poc_corpuses.append(CorpusInfo(
                    name=corpus.name,
                    display_name=corpus.display_name,
                    create_time=str(corpus.create_time) if hasattr(corpus, 'create_time') else None,
                    description=getattr(corpus, 'description', None)
                ))

        return ListCorpusResponse(
            corpuses=poc_corpuses,
            total=len(poc_corpuses)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list corpuses: {str(e)}")


@router.post("/upload/default", response_model=UploadDefaultDocsResponse)
async def upload_default_docs(request: UploadDefaultDocsRequest):
    """上傳預設測試文件（3 個職涯理論）"""
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        file_paths = []

        # Write test documents
        for doc in TEST_DOCUMENTS:
            file_path = os.path.join(temp_dir, doc["filename"])
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(doc["content"])
            file_paths.append(file_path)

        # Upload to Vertex AI
        response = rag.import_files(
            corpus_name=request.corpus_name,
            paths=file_paths,
            chunk_size=512,
            chunk_overlap=100,
        )

        # Cleanup temp files
        import shutil
        shutil.rmtree(temp_dir)

        return UploadDefaultDocsResponse(
            corpus_name=request.corpus_name,
            files_count=len(TEST_DOCUMENTS),
            imported_count=response.imported_rag_files_count,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload documents: {str(e)}")


@router.post("/upload/custom")
async def upload_custom_docs(
    corpus_name: str,
    files: List[UploadFile] = File(...)
):
    """上傳自訂文件"""
    try:
        temp_dir = tempfile.mkdtemp()
        file_paths = []

        # Save uploaded files
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_paths.append(file_path)

        # Upload to Vertex AI
        response = rag.import_files(
            corpus_name=corpus_name,
            paths=file_paths,
            chunk_size=512,
            chunk_overlap=100,
        )

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

        return {
            "status": "success",
            "files_count": len(files),
            "imported_count": response.imported_rag_files_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload custom files: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_vertex_rag(request: QueryRequest):
    """執行 Vertex AI RAG 查詢"""
    import time
    start_time = time.time()

    try:
        if request.use_gemini:
            # Method 2: RAG + Gemini generation
            rag_tool = Tool.from_retrieval(
                retrieval=rag.Retrieval(
                    source=rag.VertexRagStore(
                        rag_resources=[rag.RagResource(rag_corpus=request.corpus_name)],
                        similarity_top_k=request.top_k,
                    ),
                )
            )

            model = GenerativeModel(
                model_name="gemini-2.5-flash",
                tools=[rag_tool]
            )

            response = model.generate_content(request.question)

            processing_time = time.time() - start_time

            return QueryResponse(
                question=request.question,
                method="rag_with_gemini",
                num_results=0,
                contexts=[],
                gemini_response=response.text,
                processing_time=processing_time
            )
        else:
            # Method 1: Retrieval only
            response = rag.retrieval_query(
                rag_resources=[rag.RagResource(rag_corpus=request.corpus_name)],
                text=request.question,
                similarity_top_k=request.top_k,
            )

            contexts = [
                QueryContext(
                    rank=idx + 1,
                    score=ctx.score,
                    text=ctx.text,
                    source=ctx.source_uri if hasattr(ctx, 'source_uri') else "unknown"
                )
                for idx, ctx in enumerate(response.contexts.contexts)
            ]

            processing_time = time.time() - start_time

            result = QueryResponse(
                question=request.question,
                method="retrieval_only",
                num_results=len(contexts),
                contexts=contexts,
                gemini_response=None,
                processing_time=processing_time
            )

            print(f"DEBUG: Returning {len(contexts)} contexts")
            print(f"DEBUG: First context: {contexts[0] if contexts else 'None'}")

            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/compare", response_model=CompareResponse)
async def compare_rag_systems(request: CompareRequest):
    """對比 Vertex AI RAG vs 現有 RAG 系統"""
    try:
        # Query Vertex AI
        vertex_request = QueryRequest(
            corpus_name=request.vertex_corpus_name,
            question=request.question,
            top_k=request.top_k,
            use_gemini=False
        )
        vertex_results = await query_vertex_rag(vertex_request)

        # Query existing RAG (mock for now - you can implement real comparison)
        existing_results = {
            "method": "existing_rag",
            "num_results": 0,
            "message": "Existing RAG comparison not implemented yet"
        }

        # Compare
        comparison = {
            "vertex_avg_score": sum(c.score for c in vertex_results.contexts) / len(vertex_results.contexts) if vertex_results.contexts else 0,
            "vertex_processing_time": vertex_results.processing_time,
            "existing_avg_score": 0,
            "existing_processing_time": 0
        }

        return CompareResponse(
            question=request.question,
            vertex_results=vertex_results,
            existing_rag_results=existing_results,
            comparison=comparison
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "vertex_ai_initialized": True
    }
