"""
Unit tests for DialogueExtractor service

TDD Approach:
1. Write tests FIRST (RED)
2. Implement DialogueExtractor (GREEN)
3. Refactor rag_report.py to use it (GREEN)
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import will fail initially - this is expected (RED phase)
try:
    from app.services.dialogue_extractor import DialogueExtractor
except ImportError:
    DialogueExtractor = None


class TestDialogueExtractor:
    """Test dialogue extraction service"""

    @pytest.fixture
    def mock_openai_service(self):
        """Mock OpenAI service"""
        service = MagicMock()
        service.chat_completion = AsyncMock()
        return service

    @pytest.fixture
    def extractor(self, mock_openai_service):
        """Create DialogueExtractor instance"""
        if DialogueExtractor is None:
            pytest.skip("DialogueExtractor not implemented yet (RED phase)")
        return DialogueExtractor(mock_openai_service)

    @pytest.mark.asyncio
    async def test_extract_dialogues_2_speakers(self, extractor, mock_openai_service):
        """
        Test: Extract key dialogues for 2-person session

        Given: Transcript with 2 speakers (counselor + client)
        When: Extractor extracts dialogues
        Then: Should return 5-10 key exchanges with speaker labels
        """
        transcript = """Co: 你好，今天想聊什麼？
Cl: 我最近工作壓力很大，不知道該不該轉職。
Co: 聽起來你壓力很大，可以多說一些嗎？
Cl: 我每天加班到很晚，感覺快撐不下去了。"""

        # Mock LLM response
        mock_openai_service.chat_completion.return_value = json.dumps({
            "dialogues": [
                {"speaker": "speaker1", "order": 1, "text": "你好，今天想聊什麼？"},
                {"speaker": "speaker2", "order": 2, "text": "我最近工作壓力很大，不知道該不該轉職。"},
                {"speaker": "speaker1", "order": 3, "text": "聽起來你壓力很大，可以多說一些嗎？"},
                {"speaker": "speaker2", "order": 4, "text": "我每天加班到很晚，感覺快撐不下去了。"}
            ]
        })

        dialogues = await extractor.extract(transcript, num_participants=2)

        # Assertions
        assert len(dialogues) >= 4
        assert dialogues[0]["speaker"] in ["speaker1", "speaker2"]
        assert "order" in dialogues[0]
        assert "text" in dialogues[0]
        assert dialogues[0]["text"] == "你好，今天想聊什麼？"

    @pytest.mark.asyncio
    async def test_extract_dialogues_3_speakers(self, extractor, mock_openai_service):
        """
        Test: Extract key dialogues for 3-person session

        Given: Transcript with 3 speakers
        When: Extractor extracts dialogues
        Then: Should handle 3 speaker labels correctly
        """
        transcript = """S1: 歡迎兩位來到職涯諮詢
S2: 謝謝
S3: 很高興參加"""

        mock_openai_service.chat_completion.return_value = json.dumps({
            "dialogues": [
                {"speaker": "speaker1", "order": 1, "text": "歡迎兩位來到職涯諮詢"},
                {"speaker": "speaker2", "order": 2, "text": "謝謝"},
                {"speaker": "speaker3", "order": 3, "text": "很高興參加"}
            ]
        })

        dialogues = await extractor.extract(transcript, num_participants=3)

        assert len(dialogues) == 3
        assert dialogues[0]["speaker"] == "speaker1"
        assert dialogues[1]["speaker"] == "speaker2"
        assert dialogues[2]["speaker"] == "speaker3"

    @pytest.mark.asyncio
    async def test_extract_respects_5_to_10_range(self, extractor, mock_openai_service):
        """
        Test: Extract 5-10 dialogues (prompt requirement)

        Given: Long transcript
        When: Extractor extracts dialogues
        Then: Should return between 5 and 10 dialogues
        """
        transcript = "Co: Line 1\nCl: Line 2\n" * 50  # Very long transcript

        # Mock exactly 7 dialogues (within 5-10 range)
        mock_dialogues = [
            {"speaker": f"speaker{i%2+1}", "order": i+1, "text": f"Dialogue {i+1}"}
            for i in range(7)
        ]
        mock_openai_service.chat_completion.return_value = json.dumps({
            "dialogues": mock_dialogues
        })

        dialogues = await extractor.extract(transcript, num_participants=2)

        assert 5 <= len(dialogues) <= 10

    @pytest.mark.asyncio
    async def test_extract_handles_invalid_json(self, extractor, mock_openai_service):
        """
        Test: Handle invalid JSON from LLM

        Given: LLM returns malformed JSON
        When: Extractor attempts to parse
        Then: Should fallback to empty list without crashing
        """
        transcript = "Co: Hello"

        # Mock invalid JSON
        mock_openai_service.chat_completion.return_value = '{"dialogues": ['

        dialogues = await extractor.extract(transcript, num_participants=2)

        # Should not crash, should return empty list
        assert isinstance(dialogues, list)
        assert len(dialogues) == 0

    @pytest.mark.asyncio
    async def test_extract_with_json_in_text(self, extractor, mock_openai_service):
        """
        Test: Extract JSON from response with surrounding text

        Given: LLM returns JSON with explanation
        When: Extractor parses response
        Then: Should extract only the JSON part
        """
        transcript = "Co: Hello"

        # Mock response with extra text
        mock_openai_service.chat_completion.return_value = """
        Here are the key dialogues:

        {"dialogues": [
            {"speaker": "speaker1", "order": 1, "text": "Test dialogue"}
        ]}

        These are the most important exchanges.
        """

        dialogues = await extractor.extract(transcript, num_participants=2)

        assert len(dialogues) == 1
        assert dialogues[0]["text"] == "Test dialogue"

    @pytest.mark.asyncio
    async def test_extract_preserves_order(self, extractor, mock_openai_service):
        """
        Test: Dialogues maintain correct order

        Given: Multiple dialogues
        When: Extractor returns results
        Then: Should preserve order field
        """
        transcript = "Multi-line transcript"

        mock_openai_service.chat_completion.return_value = json.dumps({
            "dialogues": [
                {"speaker": "speaker1", "order": 1, "text": "First"},
                {"speaker": "speaker2", "order": 2, "text": "Second"},
                {"speaker": "speaker1", "order": 3, "text": "Third"}
            ]
        })

        dialogues = await extractor.extract(transcript, num_participants=2)

        assert dialogues[0]["order"] == 1
        assert dialogues[1]["order"] == 2
        assert dialogues[2]["order"] == 3

    @pytest.mark.asyncio
    async def test_extract_uses_correct_temperature(self, extractor, mock_openai_service):
        """
        Test: Extraction uses temperature=0.3 for consistency

        Given: Extraction request
        When: LLM is called
        Then: Should use low temperature for consistent results
        """
        transcript = "Test"

        mock_openai_service.chat_completion.return_value = json.dumps({
            "dialogues": [{"speaker": "speaker1", "order": 1, "text": "Test"}]
        })

        await extractor.extract(transcript, num_participants=2)

        # Verify temperature=0.3 was used
        call_kwargs = mock_openai_service.chat_completion.call_args[1]
        assert call_kwargs.get("temperature") == 0.3
