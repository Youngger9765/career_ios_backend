"""
RAGRetriever Service - 檢索相關理論文獻

Extracted from app/api/rag_report.py to follow SRP (Single Responsibility Principle)
"""

from typing import List, Dict
from fastapi import HTTPException
from sqlalchemy import Float, Integer, String, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.openai_service import OpenAIService


class RAGRetriever:
    """RAG 理論檢索服務 - 使用向量相似度搜尋"""

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def search(
        self,
        query: str,
        top_k: int,
        threshold: float,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Search for relevant theories using vector similarity (RAG)

        Args:
            query: Search query text (e.g., "職涯轉換困擾")
            top_k: Maximum number of results to return
            threshold: Minimum similarity threshold (0.0-1.0)
            db: Database session

        Returns:
            List of theories:
            [
                {
                    "text": "理論內容...",
                    "document": "文獻標題",
                    "score": 0.85
                },
                ...
            ]

        Raises:
            HTTPException: If no theories found (enforces RAG usage)
        """
        # Step 1: Generate embedding for search query
        query_embedding = await self.openai_service.create_embedding(query)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Step 2: Execute vector similarity search
        query_sql = text(
            """
            SELECT
                c.id as chunk_id,
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
                "threshold": threshold,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()

        # Step 3: Transform results to standard format
        theories = [
            {
                "text": row.text,
                "document": row.document_title,
                "score": float(row.similarity_score)
            }
            for row in rows
        ]

        # Step 4: Enforce RAG usage - fail if no theories found
        if not theories:
            raise HTTPException(
                status_code=400,
                detail="❌ RAG 檢索失敗：未找到相關理論文獻，無法生成報告。請檢查資料庫或降低 similarity_threshold。"
            )

        return theories
