"""API endpoints for RAG-powered chat"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.rag_chat_service import Citation, RAGChatService

router = APIRouter(prefix="/api/rag/chat", tags=["rag-chat"])


class ChatRequest(BaseModel):
    question: str
    top_k: int = 7
    similarity_threshold: float = 0.45
    system_prompt: Optional[str] = None
    temperature: float = 0.6
    chunk_strategy: Optional[str] = None  # NEW: filter by chunk strategy


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
        service = RAGChatService(db)

        # Step 1: Classify intent
        intent_result = await service.classify_intent(request.question)

        # If doesn't need search, respond directly
        if not intent_result.needs_search:
            answer = await service.generate_direct_answer(
                question=request.question,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
            )

            return ChatResponse(
                question=request.question,
                answer=answer,
                citations=[],
                total_citations=0,
            )

        # Step 2: Perform RAG search
        query_embedding = await service.openai_service.create_embedding(
            request.question
        )

        rows = await service.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            chunk_strategy=request.chunk_strategy,
        )

        # If no results, guide user
        if not rows:
            guide_answer = service.generate_no_results_answer(request.question)

            return ChatResponse(
                question=request.question,
                answer=guide_answer,
                citations=[],
                total_citations=0,
            )

        # Step 3: Construct context and generate answer
        citations = service.build_citations(rows)
        context = service.build_context(rows)

        answer = await service.generate_rag_answer(
            question=request.question,
            context=context,
            system_prompt=request.system_prompt,
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
