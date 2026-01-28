"""
RAG prompt building utilities for keyword analysis.

Handles RAG document retrieval and context formatting.
"""

import logging
from typing import List, Tuple

from sqlalchemy.orm import Session as DBSession

from app.services.external.openai_service import OpenAIService
from app.services.rag.rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)


class RAGPromptBuilder:
    """Builds prompts with RAG context for keyword analysis"""

    # RAG category mapping for tenants
    TENANT_RAG_CATEGORIES = {
        "career": "career",
        "island": "parenting",
        "island_parents": "parenting",
    }

    def __init__(self, openai_service: OpenAIService):
        self.rag_retriever = RAGRetriever(openai_service)

    async def retrieve_rag_context(
        self,
        transcript_segment: str,
        resolved_tenant: str,
        db_session: DBSession,
        top_k: int = 7,
        threshold: float = 0.35,
    ) -> Tuple[List[dict], List[str], str]:
        """
        Retrieve RAG documents and format context string.

        Args:
            transcript_segment: Recent transcript text
            resolved_tenant: Resolved tenant identifier
            db_session: Database session
            top_k: Number of documents to retrieve
            threshold: Similarity threshold

        Returns:
            Tuple of (rag_documents, rag_sources, rag_context_string)
        """
        rag_documents = []
        rag_sources = []
        rag_context = ""

        try:
            rag_category = self.TENANT_RAG_CATEGORIES.get(resolved_tenant)
            if rag_category:
                rag_results = await self.rag_retriever.search(
                    query=transcript_segment[:200],
                    top_k=top_k,
                    threshold=threshold,
                    db=db_session,
                    category=rag_category,
                )
                rag_documents = [
                    {
                        "doc_id": None,
                        "title": r["document"],
                        "content": r["text"],
                        "relevance_score": r["score"],
                        "chunk_id": None,
                    }
                    for r in rag_results
                ]
                rag_sources = [r["document"] for r in rag_results]

                if rag_documents:
                    rag_context = "\n\n## 參考知識庫\n" + "\n\n".join(
                        [
                            f"【{doc['title']}】\n{doc['content']}"
                            for doc in rag_documents[:top_k]
                        ]
                    )
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

        return rag_documents, rag_sources, rag_context
