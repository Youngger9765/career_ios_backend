"""
Keyword Analysis Service with RAG Support

This service provides fast keyword extraction from transcripts using:
1. Vector similarity search to find similar past sessions
2. AI-powered analysis with context from session -> case -> client
3. Caching of analysis results for future reuse
"""

import json
import logging
from typing import Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.client import Client
from app.models.session import Session
from app.schemas.session import KeywordAnalysisResponse
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)


class KeywordAnalysisService:
    """Service for analyzing transcript keywords with RAG acceleration"""

    def __init__(self):
        self.gemini_service = GeminiService()
        self.openai_service = OpenAIService()
        self.rag_retriever = RAGRetriever(self.openai_service)

    async def analyze_with_rag(
        self,
        transcript_segment: str,
        session: Session,
        case: Case,
        client: Client,
        db: AsyncSession,
        use_rag: bool = True,
    ) -> KeywordAnalysisResponse:
        """
        Analyze transcript segment with RAG acceleration.

        Process:
        1. Search for similar past sessions using vector similarity
        2. Extract successful keyword patterns from similar sessions
        3. Use AI to analyze current segment with context
        4. Store results for future RAG queries

        Args:
            transcript_segment: The transcript text to analyze
            session: Current session object
            case: Associated case object
            client: Associated client object
            db: Database session (async)
            use_rag: Whether to use RAG for acceleration (default: True)

        Returns:
            KeywordAnalysisResponse with keywords and insights
        """
        similar_analyses = []

        if use_rag:
            try:
                # Step 1: Find similar past sessions using RAG
                similar_analyses = await self._find_similar_analyses(
                    transcript_segment, db
                )
                logger.info(f"Found {len(similar_analyses)} similar past analyses")
            except Exception as e:
                logger.warning(f"RAG search failed, falling back to direct AI: {e}")
                similar_analyses = []

        # Step 2: Build context for AI analysis
        context = self._build_context(session, case, client, similar_analyses)

        # Step 3: Generate keywords and insights
        response = await self._generate_analysis(transcript_segment, context)

        # Step 4: Store embedding for future RAG queries (async, non-blocking)
        # This happens in background to keep response fast
        try:
            await self._store_analysis_embedding(
                transcript_segment, response, session.id, db
            )
        except Exception as e:
            logger.warning(f"Failed to store embedding: {e}")

        return response

    async def _find_similar_analyses(
        self, transcript_segment: str, db: AsyncSession, top_k: int = 3
    ) -> List[Dict]:
        """
        Find similar past transcript analyses using vector search.

        Args:
            transcript_segment: Current transcript to find similarities for
            db: Database session
            top_k: Number of similar results to return

        Returns:
            List of similar analyses with their keywords and insights
        """
        # Use RAGRetriever to find similar content
        # Note: We search for similar transcript segments that have been analyzed before
        try:
            similar_chunks = await self.rag_retriever.search(
                query=transcript_segment,
                top_k=top_k,
                threshold=0.7,  # Higher threshold for more relevant matches
                db=db,
            )

            # Extract analysis metadata from similar chunks
            analyses = []
            for chunk in similar_chunks:
                # Check if this chunk has associated keyword analysis
                # (stored in meta_json of the chunk)
                if "keywords" in chunk.get("meta_json", {}):
                    analyses.append(
                        {
                            "keywords": chunk["meta_json"]["keywords"],
                            "categories": chunk["meta_json"]["categories"],
                            "insights": chunk["meta_json"].get(
                                "counselor_insights", ""
                            ),
                            "similarity": chunk["score"],
                        }
                    )

            return analyses

        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []

    def _build_context(
        self,
        session: Session,
        case: Case,
        client: Client,
        similar_analyses: List[Dict],
    ) -> str:
        """Build context string for AI analysis"""
        context_parts = []

        # Add client information
        client_info = f"案主資訊: {client.name}"
        if client.current_status:
            client_info += f", 當前狀況: {client.current_status}"
        if client.notes:
            client_info += f", 備註: {client.notes}"
        context_parts.append(client_info)

        # Add case information
        case_info = f"案例目標: {case.goals or '未設定'}"
        if case.problem_description:
            case_info += f", 問題敘述: {case.problem_description}"
        context_parts.append(case_info)

        # Add session information
        session_info = f"會談次數: 第 {session.session_number} 次"
        if session.notes:
            session_info += f", 會談備註: {session.notes}"
        context_parts.append(session_info)

        # Add similar analyses for reference (if available)
        if similar_analyses:
            similar_info = "參考相似案例分析："
            for i, analysis in enumerate(similar_analyses[:3], 1):
                similar_info += f"\n{i}. 關鍵詞: {', '.join(analysis['keywords'][:5])}"
                if analysis.get("insights"):
                    similar_info += f"\n   洞見: {analysis['insights'][:100]}..."
            context_parts.append(similar_info)

        return "\n".join(context_parts)

    async def _generate_analysis(
        self, transcript_segment: str, context: str
    ) -> KeywordAnalysisResponse:
        """Generate keyword analysis using AI"""
        prompt = f"""基於以下背景資訊，從逐字稿片段中提取關鍵詞和主題，並提供諮商師洞見。

{context}

逐字稿片段:
{transcript_segment}

請提取:
1. 關鍵詞 (keywords): 重要的詞彙或概念（5-10個）
2. 類別 (categories): 這些關鍵詞所屬的主題分類（3-5個）
3. 信心分數 (confidence): 0-1之間，表示提取的可信度
4. 諮商師洞見 (counselor_insights): 根據案主背景、案例目標和逐字稿內容，提醒諮商師應該注意的重點

以JSON格式回應:
{{
    "keywords": ["關鍵詞1", "關鍵詞2", ...],
    "categories": ["類別1", "類別2", ...],
    "confidence": 0.85,
    "counselor_insights": "諮商師應注意：..."
}}
"""

        try:
            # Use Gemini for analysis
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.5, response_format={"type": "json_object"}
            )

            # Parse response
            if isinstance(ai_response, str):
                try:
                    json_start = ai_response.find("{")
                    json_end = ai_response.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        result_data = json.loads(ai_response[json_start:json_end])
                    else:
                        raise ValueError("No JSON found in response")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse AI response: {e}")
                    result_data = self._get_fallback_response()
            else:
                result_data = ai_response

            return KeywordAnalysisResponse(
                keywords=result_data.get("keywords", ["無法提取"]),
                categories=result_data.get("categories", ["一般"]),
                confidence=result_data.get("confidence", 0.5),
                counselor_insights=result_data.get(
                    "counselor_insights", "無法生成洞見，請諮商師根據經驗判斷。"
                ),
            )

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return KeywordAnalysisResponse(**self._get_fallback_response())

    def _get_fallback_response(self) -> Dict:
        """Get fallback response when AI fails"""
        return {
            "keywords": ["分析處理中"],
            "categories": ["待分類"],
            "confidence": 0.3,
            "counselor_insights": "AI 分析暫時無法使用，請根據經驗判斷。",
        }

    async def _store_analysis_embedding(
        self,
        transcript_segment: str,
        analysis: KeywordAnalysisResponse,
        session_id: UUID,
        db: AsyncSession,
    ):
        """
        Store the analysis result with embedding for future RAG queries.

        This creates a searchable chunk with the transcript and its analysis,
        allowing future similar transcripts to benefit from this analysis.

        Args:
            transcript_segment: The analyzed transcript text
            analysis: The analysis results to store
            session_id: The session this analysis belongs to
            db: Database session
        """
        try:
            # Create embedding for the transcript segment
            _embedding = await self.openai_service.create_embedding(transcript_segment)

            # Store as a chunk with analysis metadata
            # Note: We might need to create a new document type for session analyses
            # or extend the existing document model to support session-based content

            # For now, log that we would store this
            logger.info(
                f"Would store embedding for session {session_id} with "
                f"{len(analysis.keywords)} keywords"
            )

            # TODO: Implement actual storage when database schema is extended
            # This would involve:
            # 1. Creating a Document entry for the session (if not exists)
            # 2. Creating a Chunk for this transcript segment
            # 3. Storing the Embedding with the chunk
            # 4. Storing analysis results in chunk's meta_json

        except Exception as e:
            logger.error(f"Failed to store analysis embedding: {e}")


# Singleton instance
_keyword_service_instance = None


def get_keyword_analysis_service() -> KeywordAnalysisService:
    """Get singleton instance of keyword analysis service"""
    global _keyword_service_instance
    if _keyword_service_instance is None:
        _keyword_service_instance = KeywordAnalysisService()
    return _keyword_service_instance
