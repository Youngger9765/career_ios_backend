"""API endpoints for RAG vector similarity search"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Float, Integer, String, bindparam, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/api/rag/search", tags=["rag-search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    similarity_threshold: float = 0.7
    chunk_strategy: Optional[str] = None  # NEW: filter by chunk strategy


class SearchResult(BaseModel):
    chunk_id: int
    doc_id: int
    document_title: str
    text: str
    similarity_score: float
    ordinal: int
    chunk_strategy: str  # NEW: include strategy in results


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int


@router.post("/", response_model=SearchResponse)
async def search_similar(request: SearchRequest, db: Session = Depends(get_db)):
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

        # Build SQL query based on strategy filter
        params = {
            "query_embedding": embedding_str,
            "threshold": request.similarity_threshold,
            "top_k": request.top_k,
        }

        if request.chunk_strategy:
            # Query with strategy filter
            query_sql = text(
                """
                SELECT
                    c.id as chunk_id,
                    c.doc_id,
                    c.text,
                    c.ordinal,
                    c.chunk_strategy,
                    d.title as document_title,
                    1 - (e.embedding <=> CAST(:query_embedding AS vector)) as similarity_score
                FROM chunks c
                JOIN embeddings e ON c.id = e.chunk_id
                JOIN documents d ON c.doc_id = d.id
                WHERE 1 - (e.embedding <=> CAST(:query_embedding AS vector)) >= :threshold
                    AND c.chunk_strategy = :chunk_strategy
                ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
            """
            )
            params["chunk_strategy"] = request.chunk_strategy
        else:
            # Query without strategy filter
            query_sql = text(
                """
                SELECT
                    c.id as chunk_id,
                    c.doc_id,
                    c.text,
                    c.ordinal,
                    c.chunk_strategy,
                    d.title as document_title,
                    1 - (e.embedding <=> CAST(:query_embedding AS vector)) as similarity_score
                FROM chunks c
                JOIN embeddings e ON c.id = e.chunk_id
                JOIN documents d ON c.doc_id = d.id
                WHERE 1 - (e.embedding <=> CAST(:query_embedding AS vector)) >= :threshold
                ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
            """
            )

        result = db.execute(query_sql, params)

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
                chunk_strategy=row.chunk_strategy,
            )
            for row in rows
        ]

        return SearchResponse(query=request.query, results=results, total_results=len(results))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e
