"""API endpoints for RAG-powered chat"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Float, Integer, String, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
    Answer questions using RAG (Retrieval-Augmented Generation)

    Process:
    1. Generate embedding for question
    2. Search for similar chunks
    3. Construct context from top results
    4. Generate answer using LLM with context
    5. Return answer with citations

    Args:
        request: Chat question and parameters
        db: Database session

    Returns:
        ChatResponse with answer and citations
    """

    try:
        # Initialize OpenAI service
        openai_service = OpenAIService()

        # 1. Generate embedding for question
        query_embedding = await openai_service.create_embedding(request.question)

        # Convert embedding to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # 2. Search for similar chunks
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

        result = await db.execute(
            query_sql,
            {
                "query_embedding": embedding_str,
                "threshold": request.similarity_threshold,
                "top_k": request.top_k,
            },
        )

        rows = result.fetchall()

        if not rows:
            return ChatResponse(
                question=request.question,
                answer=(
                    "Sorry, I couldn't find enough relevant information in the documents to answer this question.\n\n"
                    "Suggestions:\n"
                    "1. Try rephrasing your question with more specific terms\n"
                    "2. Use career-related keywords\n"
                    "3. Ensure relevant documents have been uploaded"
                ),
                citations=[],
                total_citations=0,
            )

        # 3. Construct context from top results
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

        # 4. Generate answer using LLM with context
        system_prompt = request.system_prompt or (
            "You are a professional career counseling assistant. Answer questions based on the provided context.\n\n"
            "When answering:\n"
            "1. Base your answer primarily on the provided context and cite sources using [1], [2], etc.\n"
            "2. Maintain a professional, objective, and empathetic tone\n"
            "3. If the context doesn't contain relevant information, clearly state so without guessing\n"
            "4. Appropriately reference key concepts, theories, and best practices from the documents\n"
            "5. Consider individual differences and diverse perspectives\n"
            "6. Answer in the same language as the question (Traditional Chinese or English)"
        )

        answer = await openai_service.chat_completion_with_context(
            question=request.question,
            context=context,
            system_prompt=system_prompt,
            temperature=request.temperature,
        )

        # 5. Return answer with citations
        return ChatResponse(
            question=request.question,
            answer=answer,
            citations=citations,
            total_citations=len(citations),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}") from e
