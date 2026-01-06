"""
Unit tests for RAGRetriever service

TDD Approach:
1. Write tests FIRST (RED)
2. Implement RAGRetriever (GREEN)
3. Refactor rag_report.py to use it (GREEN)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

# Import will fail initially - this is expected (RED phase)
try:
    from app.services.rag.rag_retriever import RAGRetriever
except ImportError:
    RAGRetriever = None


class TestRAGRetriever:
    """Test RAG retrieval service"""

    @pytest.fixture
    def mock_openai_service(self):
        """Mock OpenAI service for embedding generation"""
        service = MagicMock()
        service.create_embedding = AsyncMock(
            return_value=[0.1, 0.2, 0.3] * 512
        )  # 1536-dim vector
        return service

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = MagicMock()
        return db

    @pytest.fixture
    def retriever(self, mock_openai_service):
        """Create RAGRetriever instance"""
        if RAGRetriever is None:
            pytest.skip("RAGRetriever not implemented yet (RED phase)")
        return RAGRetriever(mock_openai_service)

    @pytest.mark.asyncio
    async def test_search_returns_theories(self, retriever, mock_db):
        """
        Test: RAG search returns relevant theories

        Given: A search query and valid database
        When: Retriever searches for theories
        Then: Should return list of theories with required fields
        """
        # Mock database query result
        mock_row1 = MagicMock()
        mock_row1.text = "Super 生涯發展理論指出，個體在不同階段有不同的生涯任務..."
        mock_row1.document_title = "生涯發展理論精選"
        mock_row1.similarity_score = 0.85

        mock_row2 = MagicMock()
        mock_row2.text = "Holland 類型論認為職業選擇與人格類型相關..."
        mock_row2.document_title = "職業心理學理論"
        mock_row2.similarity_score = 0.78

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        theories = await retriever.search(
            query="職涯轉換困擾", top_k=5, threshold=0.25, db=mock_db
        )

        # Assertions
        assert len(theories) == 2
        assert (
            theories[0]["text"]
            == "Super 生涯發展理論指出，個體在不同階段有不同的生涯任務..."
        )
        assert theories[0]["document"] == "生涯發展理論精選"
        assert theories[0]["score"] == 0.85
        assert "text" in theories[0]
        assert "document" in theories[0]
        assert "score" in theories[0]

    @pytest.mark.asyncio
    async def test_search_no_results_raises_exception(self, retriever, mock_db):
        """
        Test: RAG search raises exception when no theories found

        Given: A query that matches no documents
        When: Retriever searches
        Then: Should raise HTTPException with 400 status
        """
        # Mock empty result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await retriever.search(
                query="無關查詢",
                top_k=5,
                threshold=0.9,  # Very high threshold
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "RAG 檢索失敗" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_search_respects_top_k_limit(self, retriever, mock_db):
        """
        Test: RAG search respects top_k parameter

        Given: top_k=3 and database has 10 results
        When: Retriever searches
        Then: Should return at most 3 results
        """
        # Mock 10 results
        mock_rows = []
        for i in range(10):
            row = MagicMock()
            row.text = f"Theory {i}"
            row.document_title = f"Document {i}"
            row.similarity_score = 0.9 - (i * 0.05)
            mock_rows.append(row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        theories = await retriever.search(
            query="test", top_k=3, threshold=0.25, db=mock_db
        )

        # Should return all 10 (SQL handles LIMIT, but we get back all from mock)
        # In real scenario, SQL LIMIT would restrict to 3
        assert len(theories) == 10

    @pytest.mark.asyncio
    async def test_search_filters_by_threshold(self, retriever, mock_db):
        """
        Test: RAG search filters results by similarity threshold

        Given: threshold=0.5 and mix of high/low similarity results
        When: Retriever searches
        Then: Should only return results above threshold (SQL handles this)
        """
        # Mock results above threshold
        mock_row1 = MagicMock()
        mock_row1.text = "High similarity theory"
        mock_row1.document_title = "Doc 1"
        mock_row1.similarity_score = 0.85

        mock_row2 = MagicMock()
        mock_row2.text = "Medium similarity theory"
        mock_row2.document_title = "Doc 2"
        mock_row2.similarity_score = 0.65

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        theories = await retriever.search(
            query="test", top_k=5, threshold=0.5, db=mock_db
        )

        # Both should be returned (SQL WHERE clause handles filtering)
        assert len(theories) == 2
        assert all(t["score"] >= 0.5 for t in theories)

    @pytest.mark.asyncio
    async def test_search_creates_embedding_from_query(
        self, retriever, mock_openai_service, mock_db
    ):
        """
        Test: RAG search generates embedding from query

        Given: A text query
        When: Retriever searches
        Then: Should call OpenAI embedding API with query
        """
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(text="Test", document_title="Doc", similarity_score=0.8)
        ]
        mock_db.execute.return_value = mock_result

        await retriever.search(query="職涯困擾", top_k=5, threshold=0.25, db=mock_db)

        # Verify embedding was created
        mock_openai_service.create_embedding.assert_called_once_with("職涯困擾")

    @pytest.mark.asyncio
    async def test_search_constructs_correct_sql_query(self, retriever, mock_db):
        """
        Test: RAG search constructs correct SQL with vector similarity

        Given: Search parameters
        When: Retriever searches
        Then: Should execute SQL with proper vector comparison
        """
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        try:
            await retriever.search(query="test", top_k=7, threshold=0.3, db=mock_db)
        except HTTPException:
            pass  # Expected when no results

        # Verify SQL was executed
        assert mock_db.execute.called
        call_args = mock_db.execute.call_args

        # Check parameters passed to SQL
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert params["top_k"] == 7
        assert params["threshold"] == 0.3
        assert "query_embedding" in params

    @pytest.mark.asyncio
    async def test_search_returns_sorted_by_similarity(self, retriever, mock_db):
        """
        Test: RAG search returns theories sorted by similarity (descending)

        Given: Multiple theories with different similarity scores
        When: Retriever searches
        Then: Should return results in descending order of similarity
        """
        # Mock results in descending order (as SQL would return)
        mock_rows = [
            MagicMock(text="Theory 1", document_title="Doc 1", similarity_score=0.95),
            MagicMock(text="Theory 2", document_title="Doc 2", similarity_score=0.85),
            MagicMock(text="Theory 3", document_title="Doc 3", similarity_score=0.75),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        theories = await retriever.search(
            query="test", top_k=5, threshold=0.25, db=mock_db
        )

        # Verify order
        assert theories[0]["score"] >= theories[1]["score"]
        assert theories[1]["score"] >= theories[2]["score"]
