"""API endpoints for RAG vector similarity search"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Float, Integer, String, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/api/rag/search", tags=["rag-search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    similarity_threshold: float = 0.7


class SearchResult(BaseModel):
    chunk_id: int
    doc_id: int
    document_title: str
    text: str
    similarity_score: float
    ordinal: int


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int


@router.post("/", response_model=SearchResponse)
async def search_similar(request: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Perform vector similarity search

    Args:
        request: Search query and parameters
        db: Database session

    Returns:
        SearchResponse with matching chunks
    """

    try:
        # Generate embedding for query
        openai_service = OpenAIService()
        query_embedding = await openai_service.create_embedding(request.query)

        # Convert embedding to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Perform vector similarity search using pgvector
        query_sql = text(
            """
            SELECT
                c.id as chunk_id,
                c.doc_id,
                c.text,
                c.ordinal,
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

        # Convert to SearchResult objects
        results = [
            SearchResult(
                chunk_id=row.chunk_id,
                doc_id=row.doc_id,
                document_title=row.document_title,
                text=row.text,
                similarity_score=float(row.similarity_score),
                ordinal=row.ordinal,
            )
            for row in rows
        ]

        return SearchResponse(query=request.query, results=results, total_results=len(results))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e
