"""
Unit tests for TranscriptParser service

TDD Approach:
1. Write tests FIRST (RED)
2. Implement TranscriptParser (GREEN)
3. Refactor rag_report.py to use it (GREEN)
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import will fail initially - this is expected (RED phase)
try:
    from app.services.analysis.transcript_parser import TranscriptParser
except ImportError:
    TranscriptParser = None


class TestTranscriptParser:
    """Test TranscriptParser service"""

    @pytest.fixture
    def mock_openai_service(self):
        """Mock OpenAI service for testing"""
        service = MagicMock()
        service.chat_completion = AsyncMock()
        return service

    @pytest.fixture
    def parser(self, mock_openai_service):
        """Create TranscriptParser instance"""
        if TranscriptParser is None:
            pytest.skip("TranscriptParser not implemented yet (RED phase)")
        return TranscriptParser(mock_openai_service)

    @pytest.mark.asyncio
    async def test_parse_basic_client_info(self, parser, mock_openai_service):
        """
        Test: Extract basic client info from transcript

        Given: A transcript with client demographics
        When: Parser extracts information
        Then: Should return structured client_info dict
        """
        transcript = """Co: 你好，今天想聊什麼？
Cl: 我28歲，在科技公司當軟體工程師，最近想轉職。"""

        # Mock LLM response
        mock_openai_service.chat_completion.return_value = json.dumps(
            {
                "client_name": "案主A",
                "gender": "未提及",
                "age": "28",
                "occupation": "軟體工程師",
                "education": "未提及",
                "location": "未提及",
                "economic_status": "未提及",
                "family_relations": "未提及",
                "other_info": [],
                "main_concerns": ["轉職"],
                "counseling_goals": ["探索職涯方向"],
                "counselor_techniques": ["開放式問句"],
                "session_content": "案主表達轉職意願",
                "counselor_self_evaluation": "建立初步關係",
            }
        )

        result = await parser.parse(transcript)

        # Assertions
        assert "client_info" in result
        assert result["client_info"]["age"] == "28"
        assert "工程師" in result["client_info"]["occupation"]
        assert "main_concerns" in result
        assert "轉職" in result["main_concerns"]

    @pytest.mark.asyncio
    async def test_parse_main_concerns(self, parser, mock_openai_service):
        """
        Test: Extract main concerns from transcript

        Given: Transcript with multiple concerns
        When: Parser extracts concerns
        Then: Should return list of main concerns
        """
        transcript = """Cl: 我工作壓力很大，常失眠，也不知道該不該轉職。"""

        mock_openai_service.chat_completion.return_value = json.dumps(
            {
                "client_name": "案主B",
                "gender": "未提及",
                "age": "未提及",
                "occupation": "未提及",
                "education": "未提及",
                "location": "未提及",
                "economic_status": "未提及",
                "family_relations": "未提及",
                "other_info": [],
                "main_concerns": ["工作壓力", "失眠", "轉職猶豫"],
                "counseling_goals": ["壓力管理", "職涯決策"],
                "counselor_techniques": [],
                "session_content": "案主表達壓力和失眠困擾",
                "counselor_self_evaluation": "需評估壓力程度",
            }
        )

        result = await parser.parse(transcript)

        assert "main_concerns" in result
        assert len(result["main_concerns"]) >= 2
        assert "工作壓力" in result["main_concerns"]
        assert "失眠" in result["main_concerns"]

    @pytest.mark.asyncio
    async def test_parse_counseling_goals(self, parser, mock_openai_service):
        """
        Test: Extract counseling goals

        Given: Transcript with explicit goals
        When: Parser extracts goals
        Then: Should return list of counseling goals
        """
        transcript = """Co: 你期待在諮詢中獲得什麼？
Cl: 我希望能找到適合的職涯方向，也想學會如何平衡工作和生活。"""

        mock_openai_service.chat_completion.return_value = json.dumps(
            {
                "client_name": "案主C",
                "gender": "未提及",
                "age": "未提及",
                "occupation": "未提及",
                "education": "未提及",
                "location": "未提及",
                "economic_status": "未提及",
                "family_relations": "未提及",
                "other_info": [],
                "main_concerns": ["職涯方向不明"],
                "counseling_goals": ["找到職涯方向", "工作生活平衡"],
                "counselor_techniques": ["目標設定"],
                "session_content": "案主期待釐清職涯方向",
                "counselor_self_evaluation": "目標明確",
            }
        )

        result = await parser.parse(transcript)

        assert "counseling_goals" in result
        assert len(result["counseling_goals"]) > 0
        assert any("職涯" in goal for goal in result["counseling_goals"])

    @pytest.mark.asyncio
    async def test_parse_invalid_json_fallback(self, parser, mock_openai_service):
        """
        Test: Handle invalid JSON response from LLM

        Given: LLM returns malformed JSON
        When: Parser attempts to parse
        Then: Should fallback to default values without crashing
        """
        transcript = "Co: 你好"

        # Mock invalid JSON response (missing closing brace)
        mock_openai_service.chat_completion.return_value = '{"client_name": "test"'

        result = await parser.parse(transcript)

        # Should not crash, should return default structure
        assert "client_info" in result
        assert result["client_info"]["name"] == "未提供"
        assert "main_concerns" in result
        assert isinstance(result["main_concerns"], list)

    @pytest.mark.asyncio
    async def test_parse_extracts_counselor_techniques(
        self, parser, mock_openai_service
    ):
        """
        Test: Extract counselor techniques used

        Given: Transcript showing counselor techniques
        When: Parser analyzes techniques
        Then: Should identify techniques used
        """
        transcript = """Co: 聽起來你壓力很大（同理心回應），可以多說一些嗎？（開放式問句）
Cl: 是的，我每天加班到很晚..."""

        mock_openai_service.chat_completion.return_value = json.dumps(
            {
                "client_name": "案主D",
                "gender": "未提及",
                "age": "未提及",
                "occupation": "未提及",
                "education": "未提及",
                "location": "未提及",
                "economic_status": "未提及",
                "family_relations": "未提及",
                "other_info": [],
                "main_concerns": ["工作壓力"],
                "counseling_goals": ["壓力管理"],
                "counselor_techniques": ["同理心回應", "開放式問句"],
                "session_content": "諮詢師使用同理和開放問句",
                "counselor_self_evaluation": "技巧運用適當",
            }
        )

        result = await parser.parse(transcript)

        assert "counselor_techniques" in result
        assert len(result["counselor_techniques"]) > 0
        assert (
            "同理心" in result["counselor_techniques"][0]
            or "開放式" in result["counselor_techniques"][0]
        )

    @pytest.mark.asyncio
    async def test_parse_json_with_extra_text(self, parser, mock_openai_service):
        """
        Test: Extract JSON from response with surrounding text

        Given: LLM returns JSON with explanation text
        When: Parser extracts JSON
        Then: Should extract only the JSON part
        """
        transcript = "Co: 你好"

        # Mock response with extra text
        mock_openai_service.chat_completion.return_value = """
        Here is the analysis:

        {"client_name": "案主E", "gender": "未提及", "age": "未提及",
         "occupation": "未提及", "education": "未提及", "location": "未提及",
         "economic_status": "未提及", "family_relations": "未提及",
         "other_info": [], "main_concerns": ["測試"],
         "counseling_goals": [], "counselor_techniques": [],
         "session_content": "測試", "counselor_self_evaluation": "測試"}

        Hope this helps!
        """

        result = await parser.parse(transcript)

        assert "client_info" in result
        assert result["client_info"]["name"] == "案主E"
        assert result["main_concerns"] == ["測試"]
