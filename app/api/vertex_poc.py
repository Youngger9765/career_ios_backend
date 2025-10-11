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
    thinking_process: Optional[str] = None  # New: capture thinking/reasoning
    grounding_score: Optional[float] = None  # New: grounding quality score
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
        "filename": "holland_interest_theory.txt",
        "content": """Holland 職業興趣理論

John L. Holland 提出職業興趣理論（Holland Codes or Holland Occupational Themes）

核心概念：
• 人都在追求與其類型匹配的工作環境，這樣的環境可以施展個人才能、展示人的態度與價值、並能勝任問題解決與角色扮演。
• 人格與工作環境的適配程度，影響了工作滿意度、穩定度和職業成就。
• 職業可以改變人、人也可以改變環境。
• 每個人或多或少都有這六種類型，但是特定類型比較常被展現、顯性、優勢或是慣用。

六大類型：

1. 實踐者 R (Realistic)
性格描述：喜歡親自動手修理與製造事物、解決問題。重視行動而不是言語和觀念。獨立、強健、肢體協調、吃苦耐勞。喜歡戶外工作、使用工具與機械。喜歡處理具體問題，不喜歡抽象問題。
工作偏好：處理事物
關鍵詞：行動派、實際、手巧、機械才能
典型能力：操作工具、運動活動
工作回報：可以看到工作的實體成果
典型職業：機械/工程、工匠、廚師、農林漁牧人員、健身瑜珈教練

2. 思考者 I (Investigative)
性格描述：經常活在自己的思考中。不受成規束縛、獨立思考、充滿知性好奇、洞察力、邏輯強。喜歡透過閱讀與討論來探索觀念、喜歡複雜與抽象性的心智挑戰、透過思考與分析來解決問題。
工作偏好：處理事物與觀念
關鍵詞：分析、知性、懷疑、獨立、學者
工作回報：喜歡有自主權，能夠有自由的空間及機會來滿足自己的好奇心
典型職業：科研人員、教師、軟體/工程師、醫生、人文研究

3. 創造者 A (Artistic)
性格描述：有敏銳的感性、直覺強、富想像力。藉由富有創意的方式表達自我。在覺察顏色、聲音、情感上靈敏，容易沈浸於美的事物之中。
工作偏好：創造與創新、設計、表達展現、自由彈性、有趣
關鍵詞：複雜、想像、表現、創意
工作回報：創新與變化；美感體驗
典型職業：藝術家、音樂家、演員、設計師、作家
各產業中的研發創新端，而不是維修維運端

4. 助人者 S (Social)
性格描述：重視人際關係，對人敏感、待人真誠、對人關懷、支持他人、對人負責、處事圓融、有同理心，關注焦點放在人以及人的需求，而不是在於事物。
工作偏好：喜歡與人互動、處理他人問題
關鍵詞：樂於助人、喜歡教導、激勵別人、可被諮詢、服務別人、覺察他人需求
工作回報：助人之後的回饋與結果、主管同事關係
典型職業：教師、輔導、社工、醫護、宗教、公關

5. 影響者 E (Enterprising)
性格描述：精力充沛、熱情積極、自信、主導、政治手腕，強烈自我鞭策。能透過處理人際與管理專案的能力來達成工作目標。享受金錢、權力、地位以及主導權，願意藉由承擔風險來解決問題。
工作偏好：處理資料、與人互動
關鍵詞：企圖心、善社交、成就感、存在感
典型能力：領導、管理、組織
工作回報：成就感(來源很多：助人、升遷、收入、簽單、獲勝、創新…)
典型職業：業務銷售、行銷企畫、經營管理、司法政治

6. 組織者 C (Conventional)
性格描述：井然有序、沈靜、謹慎、精確、負責、實際、條理。強烈需要安全感與確定性。做事喜歡提前準備，有始有終，注重細節，遵循慣例。任務導向，偏好完成別人所發動的事情。
工作偏好：處理資料與事物
關鍵詞：謹慎、遵守規章、自制
典型能力：安排次序、注重細節、偵查糾正、清單與SOP
典型職業：秘書、財務金融風管、會計、行政主任、編輯、公家機關、品管品保

兩兩組合與職業興趣領域：
• SA 教師輔導諮商社工、SI 人類社會心理醫療教育諮詢
• SE 和人互動 客戶經理、SC 助理人資公務人員
• IR 學術研究、硬體工程師、IA 創新設計(產品、行銷)、IC 數據分析、軟體工程師
• EC 商管工作行銷業務管理、EI 產業分析策略研究
• EA 大眾傳播媒體主播、ER 生產管理開發業務
• AE 各種設計師、AR 藝術人、美業、AC 網站企劃/室內設計/雜誌編輯 (常矛盾)
• CR 規劃執行、SR 餐飲服務 運動教練 物治推拿按摩

理論應用：
一致和分化
• 一致性：類型之間相似的程度。相鄰(RI、RC…)、相隔、相對(RS、EI、AC)。著重在前兩碼的相對位置。相對帶來矛盾猶豫的生涯抉擇困擾。
• 分化性：內在興趣強度的差別。著重在最高分和最低分的差距。分化性高比較單純，也就是說分數差異大。分化低有兩種：普遍高或是普遍低。
"""
    },
    {
        "filename": "cip_casve_model.txt",
        "content": """認知資訊處理理論（Cognitive Information Processing, CIP）

CIP理論解釋人類如何處理資訊的心理學框架，特別適用於生涯發展與決策輔導，幫助個體更有效地處理職涯資訊並進行決策。

CIP 的資訊處理金字塔：
為了使個人成為獨立、負責任的職業問題解決者和決策者，某些資訊處理能力必須在一生中不斷發展。這些功能可以被設想為形成一個具有三個分層排列的資訊處理金字塔。知識領域位於底層，決策技能領域包含中層，而執行處理領域則位於頂端。

1. 自我和選項知識：包括個人的價值觀、興趣、技能和就業偏好，以及對職業、教育、培訓和就業的了解。

2. 決策技能：包括用於解決問題和決策的通用資訊處理技能，如理性、直覺、依賴和逃避等。CASVE 循環是其中一種理性的決策方法。

3. 執行處理：涉及後設認知功能，例如自我對話（內心的想法）、自我意識（對自己作為決策者的認知）和監控與控制（管理決策進度和負面想法的能力）

CASVE循環（發音為「ca-sah-veh」）：
CASVE模型將決策過程分為五個階段，以便逐步處理職涯資訊與問題：

1. Communication（溝通）：
發現問題或需求，確認現有狀態和期望狀態之間的差距。

2. Analysis（分析）：
使用職涯評估和資訊來澄清和增強對自我的理解，包括自我知識與選項知識，並將兩者相互關聯，建立更複雜的自我與選項的心理模型

3. Synthesis（綜合）：
擴展選項範圍 (發散思考) 後 縮小選項範圍 (收斂思考) ，目標是避免錯過選項，同時不會因選項過多而不知所措

4. Valuing（評估）：
評估選項的成本和效益，並確定初步選擇。

5. Execution（執行）：
制定並執行行動計畫，並在必要時進行現實檢驗。完成執行後會回到溝通階段，評估問題是否已解決

CASVE 循環可能因為多種原因重複：
• 在後續階段遇到困難，需要回到先前的階段。
• 發現先前的選擇不適合，或是出現了新的選擇。
• 外部環境或個人情況發生變化。
• 在溝通階段沒有充分探索問題的個人、社會和情感因素。
"""
    },
    {
        "filename": "schlossberg_transition_model.txt",
        "content": """生涯轉換模式 (Schlossberg, 1984)

生涯轉換模式包含三個主要步驟：
1. 面對 / 看待轉換（Approaching Transitions）
2. 盤點 4S 資源（Taking Stock of Coping Resources: The 4S System）
3. 掌握轉換（Taking Charge）

人們一開始看待轉換的視角，將會影響到後續的思維與行動（4S）。一開始的初級評估，會非常隱晦地影響我們的思維與行動。第一個重要的協助關鍵點，就是放慢這個初步評估的歷程，並設法將案主觀點與視角引導至較有效的方向。該事件對我是危機或轉機？

4S 系統：

1. 情況（Situation）
個體怎麼看待現在發生的事情，在情況中我們需要回答以下問題：
• 觸發 Trigger：是什麼觸發了這個轉換？
• 時機 Timing：這個轉換與個人所認定的社會時鐘（social clock）有何相關？這個轉換是來的正好還是來得不巧？
• 控制 Control：我們在這個轉換中可以控制的部分有哪些？
• 角色改變 Role Change：這個轉換是否有涉及角色的改變？
• 持續時間 Duration：這個轉換是永久性的或是暫時性的？
• 早先經驗 Previous Experience：個體過去碰到類似轉換情況時是怎麼樣的呢？
• 目前壓力 Concurrent Stress：這個轉換會讓個體現在面臨到那些壓力？這些壓力有多大的影響？
• 衡鑑 Assessment：個體認為這個轉換是正向或負向、良性或惡性？

2. 自我（Self）
個人特性：
• 社會心理能力（Psychosocial competence）
• 性別和性別角色定義（Sex and Sex-role identification）
• 年齡和生命階段（Age and life stage）
• 健康狀態（State of Health）
• 種族（Race/ethnicity）
• 社經地位（Socioeconomic status）
• 價值導向（value orientation）
• 早期轉換經驗（previous experience with a transition of a similar nature）

心理資源：
• 自我發展（Ego development）
• 樂觀及自我效能（optimism and self-efficacy）
• 承諾及價值觀（commitment and values）
• 靈性與韌性（spirituality and resiliency）

3. 支持（Support）
• 人際支持系統（Interpersonal Support Systems）：親密關係、家人、朋友網絡
• 社會支持（Institutional Supports）：職業工會、宗教機構、政治團體、社福單位、社區機構
• 物理設置（Physical Setting）：氣候溫度、居住環境、鄰居、生活規劃、工作設施
• 資訊、金錢、課程
• 弱人脈連結、推薦、求職幫助

4. 策略（Strategies）
協助步驟：
1. 首先先了解個案對於此生涯轉換的想法為何
2. 接著協助個案分析自己在此轉換中的優劣能力以及過去經驗，並在此階段了解個案對於生涯轉換的心理資源強弱如何，以及可以如何提升和運用
3. 讓個案看見自己目前所擁有支持系統有哪些，提升個案對面臨生涯轉換挑戰的自信，也安定個案的焦慮
4. 最後則是與個案一起討論因應策略，並在行動當中一邊進行現況評估，依照需要加強的地方再次進行討論和修正，不停的循環直到個案順利完成生涯轉換為止。
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


@router.delete("/corpus/{corpus_name:path}/files/all")
async def delete_all_files(corpus_name: str):
    """刪除 corpus 中的所有文件"""
    try:
        files = rag.list_files(corpus_name=corpus_name)
        deleted_count = 0

        for file in files:
            try:
                rag.delete_file(name=file.name)
                deleted_count += 1
                print(f"Deleted file: {file.name}")
            except Exception as e:
                print(f"Failed to delete {file.name}: {e}")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} files from corpus"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete files: {str(e)}")


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
        # 增加 chunk size 以提升检索效果
        response = rag.import_files(
            corpus_name=request.corpus_name,
            paths=file_paths,
            chunk_size=1024,  # 从 512 提升到 1024
            chunk_overlap=200,  # 从 100 提升到 200
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
        # 增加 chunk size 以提升检索效果
        response = rag.import_files(
            corpus_name=corpus_name,
            paths=file_paths,
            chunk_size=1024,  # 从 512 提升到 1024
            chunk_overlap=200,  # 从 100 提升到 200
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

    print(f"=== QUERY REQUEST ===")
    print(f"corpus_name: {request.corpus_name}")
    print(f"question: {request.question}")
    print(f"top_k: {request.top_k}")
    print(f"use_gemini: {request.use_gemini}")

    try:
        if request.use_gemini:
            # Method 2: RAG + Gemini generation (with retrieval contexts)
            # Step 1: Get retrieval contexts first
            retrieval_response = rag.retrieval_query(
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
                for idx, ctx in enumerate(retrieval_response.contexts.contexts)
            ]

            # Step 2: Generate with Gemini + Extract grounding metadata
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

            # Extract grounding metadata info
            grounding_chunks_count = 0
            grounding_score = None

            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    grounding_meta = candidate.grounding_metadata

                    # Count grounding chunks
                    if hasattr(grounding_meta, 'grounding_chunks'):
                        grounding_chunks_count = len(grounding_meta.grounding_chunks)
                        print(f"✅ Found {grounding_chunks_count} grounding chunks")

                    # Try to extract any quality metrics
                    if hasattr(grounding_meta, 'grounding_support'):
                        grounding_score = float(grounding_meta.grounding_support)
                        print(f"🎯 grounding_support: {grounding_score}")

                    # Check for retrieval_queries
                    if hasattr(grounding_meta, 'retrieval_queries'):
                        print(f"🔍 retrieval_queries: {grounding_meta.retrieval_queries}")

            processing_time = time.time() - start_time

            return QueryResponse(
                question=request.question,
                method="rag_with_gemini",
                num_results=len(contexts),
                contexts=contexts,
                gemini_response=response.text,
                thinking_process=None,  # Not available with standard RAG
                grounding_score=grounding_score,
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
            if contexts:
                print(f"DEBUG: First context:")
                print(f"  - Rank: {contexts[0].rank}")
                print(f"  - Score: {contexts[0].score}")
                print(f"  - Text preview: {contexts[0].text[:200]}...")
                print(f"  - Source: {contexts[0].source}")

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
