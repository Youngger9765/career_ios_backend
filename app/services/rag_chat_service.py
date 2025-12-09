"""Service layer for RAG-powered chat operations"""

import json
import re
from typing import List, Optional, Tuple

from pydantic import BaseModel
from sqlalchemy import Float, Integer, String, bindparam, select, text
from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.openai_service import OpenAIService


class Citation(BaseModel):
    chunk_id: int
    doc_id: int
    document_title: str
    text: str
    similarity_score: float


class IntentResult(BaseModel):
    needs_search: bool
    reason: str


class RAGChatService:
    """Service for RAG chat operations"""

    def __init__(self, db: Session):
        self.db = db
        self.openai_service = OpenAIService()

    async def get_available_documents(self) -> List[str]:
        """Get list of available document titles from database

        Returns:
            List of unique document titles sorted alphabetically
        """
        result = self.db.execute(select(Document.title).distinct())
        doc_titles = [row[0] for row in result.fetchall()]
        return sorted(set(doc_titles))

    def _build_intent_system_prompt(self, doc_titles: List[str]) -> str:
        """Build system prompt for intent classification

        Args:
            doc_titles: List of available document titles

        Returns:
            System prompt string for intent classification
        """
        doc_list = "\n".join([f"- {title}" for title in doc_titles])

        return f"""You are a classifier for a career counseling AI assistant.

Your job: Determine if the question needs to search our professional documents.

📚 **Available documents in our database:**
{doc_list}

**Document coverage includes:**
- 職涯諮詢概論與興趣熱情 (Career counseling fundamentals & passion exploration)
- 優勢職能分析 (Strengths & competency analysis)
- 生涯成熟與價值觀 (Career maturity & values)
- 求職策略、履歷與面試技巧 (Job search strategies, resume & interview skills)
- 心理諮詢技巧 (Psychological counseling techniques)
- 綜合職涯實戰錦囊 (Comprehensive career practice toolkit)
- 主人思維 (Owner mindset and proactive thinking)
- 職遊精選文章 (Curated career development articles)

Reply ONLY with JSON:
{{"needs_search": true/false, "reason": "brief explanation"}}

✅ needs_search = TRUE for:
- Career-related questions (職涯、工作、求職、面試、履歷)
- Personal development questions (成長、發展、目標、規劃、興趣、熱情)
- Life purpose questions (人生意義、價值觀、想要的生活)
- Career confusion or exploration (迷茫、困惑、選擇、探索)
- Skill or competency questions (能力、優勢、專長、技能)
- Work-life balance (工作生活平衡、壓力)
- Career transitions (轉職、換工作、職涯轉換)
- Mindset questions (思維、心態、主人思維)
- Any question that MIGHT relate to career counseling or personal development
- **Any question that mentions topics in our document titles**

❌ needs_search = FALSE ONLY for:
- Pure greetings with no question (只是「你好」「hi」「hello」)
- System commands (重置、清除、設定)
- Completely unrelated topics (天氣、數學計算、娛樂八卦、今天吃什麼)

🔑 Key principle: When in doubt, choose TRUE.
Career counseling is broad - almost any life question can relate to career.

Examples:
- "我想要活得更好" → TRUE (relates to life purpose & career direction)
- "因為想要活得更好" → TRUE (implies career motivation)
- "如何找到熱情" → TRUE (passion exploration)
- "我很迷茫" → TRUE (career confusion)
- "主人思維是什麼" → TRUE (we have 主人思維全.pdf)
- "你好" → FALSE (just greeting)
- "今天天氣如何" → FALSE (weather)
- "1+1等於多少" → FALSE (math calculation)"""

    async def classify_intent(self, question: str) -> IntentResult:
        """Classify if question needs RAG search

        Args:
            question: User's question

        Returns:
            IntentResult with needs_search flag and reason
        """
        doc_titles = await self.get_available_documents()
        intent_system_prompt = self._build_intent_system_prompt(doc_titles)

        intent_check = await self.openai_service.chat_completion(
            messages=[
                {"role": "system", "content": intent_system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.2,  # Lower temperature for consistent classification
        )

        # Parse intent response
        try:
            intent_data = json.loads(intent_check)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", intent_check, re.DOTALL)
            if json_match:
                intent_data = json.loads(json_match.group(0))
            else:
                # Default to search if parsing fails
                intent_data = {
                    "needs_search": True,
                    "reason": "default to search on parse error",
                }

        return IntentResult(
            needs_search=intent_data.get("needs_search", True),
            reason=intent_data.get("reason", ""),
        )

    async def generate_direct_answer(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.6,
    ) -> str:
        """Generate direct answer without RAG search

        Args:
            question: User's question
            system_prompt: Optional custom system prompt
            temperature: OpenAI temperature parameter

        Returns:
            Direct answer string
        """
        default_system_prompt = (
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

        answer = await self.openai_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt or default_system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=temperature,
        )

        return answer

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int,
        similarity_threshold: float,
        chunk_strategy: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Tuple]:
        """Search for similar document chunks using vector similarity

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            chunk_strategy: Optional chunk strategy filter
            category: Optional category filter (e.g., "parenting", "career")

        Returns:
            List of result rows with (chunk_id, doc_id, text, document_title, similarity_score)
        """
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Build params dict and WHERE clause dynamically
        params = {
            "query_embedding": embedding_str,
            "threshold": similarity_threshold,
            "top_k": top_k,
        }

        # Build WHERE clause filters
        where_filters = [
            "1 - (e.embedding <=> CAST(:query_embedding AS vector)) >= :threshold"
        ]

        # Build bindparams list dynamically
        bind_params = [
            bindparam("query_embedding", type_=String),
            bindparam("threshold", type_=Float),
            bindparam("top_k", type_=Integer),
        ]

        # Only add filters and bindparams if values provided
        if chunk_strategy:
            where_filters.append("c.chunk_strategy = :chunk_strategy")
            params["chunk_strategy"] = chunk_strategy
            bind_params.append(bindparam("chunk_strategy", type_=String))

        if category:
            where_filters.append("d.category = :category")
            params["category"] = category
            bind_params.append(bindparam("category", type_=String))

        where_clause = " AND ".join(where_filters)

        # Build query with dynamic filters
        query_sql = text(
            f"""
            SELECT
                c.id as chunk_id,
                c.doc_id,
                c.text,
                d.title as document_title,
                1 - (e.embedding <=> CAST(:query_embedding AS vector)) as similarity_score
            FROM chunks c
            JOIN embeddings e ON c.id = e.chunk_id
            JOIN documents d ON c.doc_id = d.id
            WHERE {where_clause}
            ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """
        ).bindparams(*bind_params)

        result = self.db.execute(query_sql, params)
        return result.fetchall()

    def build_citations(self, rows: List[Tuple]) -> List[Citation]:
        """Build citation list from search results

        Args:
            rows: Search result rows

        Returns:
            List of Citation objects
        """
        citations = []
        for row in rows:
            citations.append(
                Citation(
                    chunk_id=row.chunk_id,
                    doc_id=row.doc_id,
                    document_title=row.document_title,
                    text=row.text,
                    similarity_score=float(row.similarity_score),
                )
            )
        return citations

    def build_context(self, rows: List[Tuple]) -> str:
        """Build context string from search results

        Args:
            rows: Search result rows

        Returns:
            Formatted context string with numbered citations
        """
        context_parts = []
        for idx, row in enumerate(rows):
            context_parts.append(f"[{idx + 1}] {row.text}")
        return "\n\n".join(context_parts)

    async def generate_rag_answer(
        self,
        question: str,
        context: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.6,
    ) -> str:
        """Generate answer using RAG context

        Args:
            question: User's question
            context: Retrieved context from documents
            system_prompt: Optional custom system prompt
            temperature: OpenAI temperature parameter

        Returns:
            Generated answer string
        """
        default_system_prompt = (
            "你是一位專業的職涯諮詢助理。根據提供的文本來回答問題。\n\n"
            "回答時請遵循：\n"
            "1. 主要根據文本內容並用 [1]、[2] 標註來源\n"
            "2. 保持專業、客觀且具同理心的語氣\n"
            "3. 如果文本中沒有相關資訊，請明確說明\n"
            "4. 適當引用關鍵概念、理論和最佳實踐\n"
            "5. 考慮個別差異和多元觀點\n"
            "6. 使用與問題相同的語言回答（繁體中文或英文）"
        )

        answer = await self.openai_service.chat_completion_with_context(
            question=question,
            context=context,
            system_prompt=system_prompt or default_system_prompt,
            temperature=temperature,
        )

        return answer

    def generate_no_results_answer(self, question: str) -> str:
        """Generate guidance answer when no search results found

        Args:
            question: User's question

        Returns:
            Guidance answer string
        """
        # Check if it's a simple greeting
        if question.strip().lower() in ["hello", "hi", "你好", "嗨", "哈囉"]:
            return (
                "你好！我是職涯諮詢 AI 助理 👋\n\n"
                "我可以協助你：\n"
                "✨ 探索職涯興趣與熱情\n"
                "✨ 分析優勢職能\n"
                "✨ 求職策略與履歷面試指導\n"
                "✨ 職涯發展規劃建議\n\n"
                "有什麼職涯問題想問我嗎？"
            )

        # Default guidance for no results
        return (
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
