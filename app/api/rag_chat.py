"""API endpoints for RAG-powered chat"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Float, Integer, String, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/api/rag/chat", tags=["rag-chat"])


class ChatRequest(BaseModel):
    question: str
    top_k: int = 7
    similarity_threshold: float = 0.55
    system_prompt: Optional[str] = None
    temperature: float = 0.6


class Citation(BaseModel):
    chunk_id: int
    doc_id: int
    document_title: str
    text: str
    similarity_score: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    total_citations: int


@router.post("/", response_model=ChatResponse)
async def chat_with_rag(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Intelligent chat with optional RAG (Retrieval-Augmented Generation)

    Process:
    1. Determine if question needs document search
    2. If yes: Search and answer with context
    3. If no: Direct answer or guide user about available content

    Args:
        request: Chat question and parameters
        db: Database session

    Returns:
        ChatResponse with answer and citations
    """

    try:
        # Initialize OpenAI service
        openai_service = OpenAIService()

        # Step 1: Determine if question needs RAG search
        intent_check = await openai_service.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": """You are a classifier. Determine if the question needs document search.

Available documents cover:
- 職涯諮詢概論與興趣熱情
- 優勢職能分析
- 生涯成熟與價值觀
- 求職策略、履歷與面試技巧
- 心理諮詢技巧
- 綜合職涯實戰錦囊

Reply ONLY with JSON (no other text):
{
  "needs_search": true/false,
  "reason": "brief explanation"
}

needs_search = true if:
- Asking about career theory, concepts, or frameworks
- Needs specific professional knowledge
- Asking about career counseling techniques
- Related to available document topics

needs_search = false if:
- Simple greetings (hi, hello, 你好)
- General chat (how are you)
- Questions clearly outside career counseling scope
- Personal opinions not requiring documents""",
                },
                {"role": "user", "content": request.question},
            ],
            temperature=0.3,
        )

        # Parse intent
        import json
        import re

        try:
            intent_data = json.loads(intent_check)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", intent_check, re.DOTALL)
            if json_match:
                intent_data = json.loads(json_match.group(0))
            else:
                intent_data = {"needs_search": True, "reason": "default to search"}

        needs_search = intent_data.get("needs_search", True)

        # If doesn't need search, respond directly
        if not needs_search:
            system_prompt = request.system_prompt or (
                "你是一位專業的職涯諮詢助理。根據問題類型回答：\n\n"
                "如果是打招呼：友善回應，並介紹你可以幫助的內容\n"
                "如果是閒聊：簡短回應，引導回到職涯相關話題\n"
                "如果超出範圍：說明你的專業範圍在職涯諮詢，資料庫包含以下主題：\n"
                "- 職涯諮詢概論與興趣熱情\n"
                "- 優勢職能分析\n"
                "- 生涯成熟與價值觀\n"
                "- 求職策略、履歷與面試技巧\n"
                "- 心理諮詢技巧\n"
                "- 綜合職涯實戰錦囊\n\n"
                "使用與問題相同的語言回答（繁體中文或英文）"
            )

            answer = await openai_service.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.question},
                ],
                temperature=request.temperature,
            )

            return ChatResponse(
                question=request.question, answer=answer, citations=[], total_citations=0
            )

        # Step 2: Perform RAG search
        query_embedding = await openai_service.create_embedding(request.question)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        query_sql = text(
            """
            SELECT
                c.id as chunk_id,
                c.doc_id,
                c.text,
                d.title as document_title,
                1 - (e.embedding <=> CAST(:query_embedding AS vector)) as similarity_score
            FROM chunks c
            JOIN embeddings e ON c.id = e.chunk_id
            JOIN documents d ON c.doc_id = d.id
            WHERE 1 - (e.embedding <=> CAST(:query_embedding AS vector)) >= :threshold
            ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """
        ).bindparams(
            bindparam("query_embedding", type_=String),
            bindparam("threshold", type_=Float),
            bindparam("top_k", type_=Integer),
        )

        result = db.execute(
            query_sql,
            {
                "query_embedding": embedding_str,
                "threshold": request.similarity_threshold,
                "top_k": request.top_k,
            },
        )

        rows = result.fetchall()

        # If no results, guide user
        if not rows:
            guide_answer = (
                "抱歉，我在資料庫中找不到與你問題直接相關的內容。\n\n"
                "📚 我的知識庫目前包含以下主題：\n"
                "1. 職涯諮詢概論與興趣熱情探索\n"
                "2. 優勢職能分析與發展\n"
                "3. 生涯成熟度與價值觀\n"
                "4. 求職策略、履歷撰寫與面試技巧\n"
                "5. 心理諮詢技巧與實務\n"
                "6. 綜合職涯實戰案例\n\n"
                "💡 建議：\n"
                "- 試著用更具體的職涯相關關鍵字重新提問\n"
                "- 例如：「如何探索職涯興趣？」、「履歷撰寫技巧」、「面試準備要點」\n"
                "- 或直接問我上述任一主題的問題"
            )

            if request.question.strip().lower() in [
                "hello",
                "hi",
                "你好",
                "嗨",
                "哈囉",
            ]:
                guide_answer = (
                    "你好！我是職涯諮詢 AI 助理 👋\n\n"
                    "我可以協助你：\n"
                    "✨ 探索職涯興趣與熱情\n"
                    "✨ 分析優勢職能\n"
                    "✨ 求職策略與履歷面試指導\n"
                    "✨ 職涯發展規劃建議\n\n"
                    "有什麼職涯問題想問我嗎？"
                )

            return ChatResponse(
                question=request.question, answer=guide_answer, citations=[], total_citations=0
            )

        # Step 3: Construct context and generate answer
        context_parts = []
        citations = []

        for idx, row in enumerate(rows):
            context_parts.append(f"[{idx + 1}] {row.text}")

            citations.append(
                Citation(
                    chunk_id=row.chunk_id,
                    doc_id=row.doc_id,
                    document_title=row.document_title,
                    text=row.text,
                    similarity_score=float(row.similarity_score),
                )
            )

        context = "\n\n".join(context_parts)

        system_prompt = request.system_prompt or (
            "你是一位專業的職涯諮詢助理。根據提供的文本來回答問題。\n\n"
            "回答時請遵循：\n"
            "1. 主要根據文本內容並用 [1]、[2] 標註來源\n"
            "2. 保持專業、客觀且具同理心的語氣\n"
            "3. 如果文本中沒有相關資訊，請明確說明\n"
            "4. 適當引用關鍵概念、理論和最佳實踐\n"
            "5. 考慮個別差異和多元觀點\n"
            "6. 使用與問題相同的語言回答（繁體中文或英文）"
        )

        answer = await openai_service.chat_completion_with_context(
            question=request.question,
            context=context,
            system_prompt=system_prompt,
            temperature=request.temperature,
        )

        return ChatResponse(
            question=request.question,
            answer=answer,
            citations=citations,
            total_citations=len(citations),
        )

    except Exception as e:
        import traceback

        error_detail = f"Chat failed: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail) from e
