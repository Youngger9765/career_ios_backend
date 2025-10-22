"""
Service layer tests for Career Counseling API
Tests for STT, Sanitizer, and Report Generation services
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.report_service import ReportGenerationService
from app.services.sanitizer_service import SanitizerService
from app.services.stt_service import STTService


class TestSTTService:
    """Test Speech-to-Text service"""

    @pytest.fixture
    def stt_service(self):
        return STTService()

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, stt_service):
        """Test successful audio transcription"""
        mock_audio_path = "/tmp/test_audio.m4a"

        with patch.object(stt_service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "這是測試逐字稿內容"

            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value = MagicMock()

                result = await stt_service.transcribe_audio(mock_audio_path, language="zh")

                assert isinstance(result, str)
                assert len(result) > 0
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_timestamps(self, stt_service):
        """Test transcription with timestamps"""
        mock_audio_path = "/tmp/test_audio.m4a"

        with patch.object(stt_service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
            # Create a mock response object with attributes
            mock_segment_1 = MagicMock(start=0.0, end=2.5, text="這是")
            mock_segment_2 = MagicMock(start=2.5, end=5.0, text="測試內容")
            mock_response = MagicMock(
                text="這是測試內容",
                segments=[mock_segment_1, mock_segment_2],
                language="zh",
                duration=5.0
            )
            mock_create.return_value = mock_response

            with patch("builtins.open", create=True):
                result = await stt_service.transcribe_with_timestamps(mock_audio_path)

                assert "text" in result
                assert "segments" in result

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_not_found(self, stt_service):
        """Test transcription with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await stt_service.transcribe_audio("/nonexistent/audio.m4a")

    @pytest.mark.asyncio
    async def test_supported_formats(self, stt_service):
        """Test various supported audio formats"""
        supported_formats = [".m4a", ".mp3", ".wav", ".webm", ".mp4", ".mpeg"]

        for format_ext in supported_formats:
            mock_path = f"/tmp/test_audio{format_ext}"

            with patch.object(stt_service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = "測試內容"
                with patch("builtins.open", create=True), patch("os.path.exists", return_value=True):
                    result = await stt_service.transcribe_audio(mock_path)
                    assert isinstance(result, str)


class TestSanitizerService:
    """Test text sanitization service"""

    @pytest.fixture
    def sanitizer_service(self):
        return SanitizerService()

    def test_sanitize_id_card(self, sanitizer_service):
        """Test sanitizing Taiwan ID card numbers"""
        text = "我的身分證是 A123456789 請保密"
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "A123456789" not in result
        assert "[已遮蔽身分證字號]" in result
        assert metadata["id_card_count"] == 1

    def test_sanitize_phone(self, sanitizer_service):
        """Test sanitizing phone numbers"""
        text = "我的手機是 0912345678 可以聯絡我"
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "0912345678" not in result
        assert "[已遮蔽手機號碼]" in result
        assert metadata["phone_count"] == 1

    def test_sanitize_email(self, sanitizer_service):
        """Test sanitizing email addresses"""
        text = "請寄到 test@example.com 這個信箱"
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "test@example.com" not in result
        assert "[已遮蔽電子郵件]" in result
        assert metadata["email_count"] == 1

    def test_sanitize_credit_card(self, sanitizer_service):
        """Test sanitizing credit card numbers"""
        text = "我的卡號是 1234 5678 9012 3456"
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "1234 5678 9012 3456" not in result
        assert "[已遮蔽信用卡號]" in result
        assert metadata["credit_card_count"] == 1

    def test_sanitize_address(self, sanitizer_service):
        """Test sanitizing address numbers"""
        text = "我住在台北市中山區民生東路123號"
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "123號" not in result
        assert "[已遮蔽門牌]" in result
        assert metadata["address_number_count"] == 1

    def test_sanitize_landline(self, sanitizer_service):
        """Test sanitizing landline numbers"""
        text = "公司電話是 02-12345678"
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "02-12345678" not in result
        assert "[已遮蔽市話]" in result
        assert metadata["landline_count"] == 1

    def test_sanitize_multiple_types(self, sanitizer_service):
        """Test sanitizing multiple sensitive data types"""
        text = """
        我的資料如下：
        身分證：A123456789
        手機：0912345678
        信箱：test@example.com
        地址：台北市100號
        """
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "A123456789" not in result
        assert "0912345678" not in result
        assert "test@example.com" not in result
        assert "100號" not in result

        assert metadata["removed_count"] == 4

    def test_no_sensitive_data(self, sanitizer_service):
        """Test text without sensitive data"""
        text = "今天天氣很好，我們討論了職涯發展的問題"
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert result == text
        assert metadata["removed_count"] == 0

    def test_preserve_transcript_structure(self, sanitizer_service):
        """Test that sanitization preserves transcript structure"""
        text = """
        諮商師：請問你的聯絡方式是？
        來訪者：我的電話是 0912345678
        諮商師：好的，我記下來了
        """
        result, metadata = sanitizer_service.sanitize_session_transcript(text)

        assert "諮商師：" in result
        assert "來訪者：" in result
        assert "0912345678" not in result
        assert "[已遮蔽手機號碼]" in result


class TestReportGenerationService:
    """Test report generation service with RAG"""

    @pytest.fixture
    def report_service(self):
        return ReportGenerationService()

    @pytest.mark.asyncio
    async def test_generate_report_from_transcript(self, report_service):
        """Test generating report from transcript"""
        transcript = """
        諮商師：今天想聊什麼呢？
        來訪者：我最近工作上遇到一些困難，不知道該怎麼辦...
        諮商師：可以說說看是什麼樣的困難嗎？
        來訪者：我覺得自己不適合現在的工作...
        """

        with patch.object(report_service, '_parse_transcript_info') as mock_parse:
            mock_parse.return_value = {
                "num_participants": 2,
                "session_duration": "30分鐘",
                "main_concerns": ["工作適應", "職涯方向"]
            }

            with patch.object(report_service, '_retrieve_theories') as mock_retrieve:
                mock_retrieve.return_value = [
                    {
                        "theory": "Holland 職業興趣理論",
                        "relevance": 0.89,
                        "source": "職業心理學教材"
                    }
                ]

                with patch.object(report_service, '_generate_structured_report') as mock_generate:
                    mock_generate.return_value = {
                        "main_issue": "職涯適配性困擾",
                        "causal_analysis": "興趣與工作內容不匹配",
                        "recommendations": ["進行興趣測驗", "探索職涯選項"]
                    }

                    with patch.object(report_service, '_extract_key_dialogues') as mock_extract:
                        mock_extract.return_value = [
                            {
                                "speaker": "來訪者",
                                "text": "我覺得自己不適合現在的工作",
                                "significance": "核心困擾陳述"
                            }
                        ]

                        result = await report_service.generate_report_from_transcript(
                            transcript=transcript,
                            agent_id=1,
                            num_participants=2
                        )

                        assert "content_json" in result
                        assert "citations_json" in result
                        assert "agent_id" in result
                        assert result["agent_id"] == 1

    @pytest.mark.asyncio
    async def test_parse_transcript_info(self, report_service):
        """Test parsing transcript information"""
        transcript = """
        諮商師：早安
        來訪者：早安
        第三者：我是家長
        """

        with patch.object(report_service.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"num_participants": 3, "session_duration": "50分鐘"}'
            mock_create.return_value = mock_response

            result = await report_service._parse_transcript_info(transcript)

            assert "num_participants" in result
            assert result["num_participants"] == 3

    @pytest.mark.asyncio
    async def test_retrieve_theories_with_agent(self, report_service):
        """Test retrieving theories using specific agent"""
        search_query = "職涯發展困擾"

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "answer": "根據理論...",
                "citations": [
                    {"theory": "Super 生涯發展理論", "relevance": 0.92}
                ]
            })
            mock_post.return_value = mock_response

            result = await report_service._retrieve_theories(search_query, agent_id=1)

            assert isinstance(result, list)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_structured_report(self, report_service):
        """Test generating structured report content"""
        transcript = "測試逐字稿"
        parsed_info = {"main_concerns": ["職涯困擾"]}
        citations = [{"theory": "Holland理論", "text": "Holland理論說明了六種職業類型..."}]

        with patch.object(report_service.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''
            {
                "main_issue": "職涯適配性問題",
                "causal_analysis": "興趣與工作不符",
                "recommendations": ["測驗", "諮詢"]
            }
            '''
            mock_create.return_value = mock_response

            result = await report_service._generate_structured_report(
                transcript, parsed_info, citations, num_participants=2
            )

            assert "main_issue" in result
            assert "causal_analysis" in result
            assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_extract_key_dialogues(self, report_service):
        """Test extracting key dialogue excerpts"""
        transcript = """
        諮商師：你覺得問題在哪？
        來訪者：我真的不知道自己適合什麼工作
        諮商師：我們可以一起探索
        """

        with patch.object(report_service.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''
            {
                "dialogues": [
                    {
                        "speaker": "來訪者",
                        "text": "我真的不知道自己適合什麼工作",
                        "significance": "核心困擾"
                    }
                ]
            }
            '''
            mock_create.return_value = mock_response

            result = await report_service._extract_key_dialogues(transcript, num_participants=2)

            assert isinstance(result, list)
            assert len(result) > 0
            assert result[0]["speaker"] == "來訪者"

    @pytest.mark.asyncio
    async def test_generate_report_without_agent(self, report_service):
        """Test generating report without specific agent (use default)"""
        transcript = "簡短逐字稿"

        with patch.object(report_service, '_parse_transcript_info') as mock_parse, \
             patch.object(report_service, '_retrieve_theories') as mock_retrieve, \
             patch.object(report_service, '_generate_structured_report') as mock_generate, \
             patch.object(report_service, '_extract_key_dialogues') as mock_extract:

            mock_parse.return_value = {"num_participants": 2}
            mock_retrieve.return_value = []
            mock_generate.return_value = {"main_issue": "測試"}
            mock_extract.return_value = []

            result = await report_service.generate_report_from_transcript(
                transcript=transcript,
                agent_id=None
            )

            assert "content_json" in result
            # Should use default agent
            assert result["agent_id"] is None or isinstance(result["agent_id"], int)


class TestServiceIntegration:
    """Integration tests for services working together"""

    @pytest.mark.asyncio
    async def test_full_service_pipeline(self):
        """Test complete pipeline: STT → Sanitize → Report"""
        # This is a conceptual test showing the full flow

        # Mock audio file path
        audio_path = "/tmp/test_audio.m4a"

        # Step 1: STT
        stt_service = STTService()
        with patch.object(stt_service.client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = "來訪者：我的電話是 0912345678，我遇到職涯問題"
            with patch("builtins.open", create=True), patch("os.path.exists", return_value=True):
                transcript = await stt_service.transcribe_audio(audio_path)

        # Step 2: Sanitize
        sanitizer_service = SanitizerService()
        sanitized_transcript, metadata = sanitizer_service.sanitize_session_transcript(transcript)

        assert "0912345678" not in sanitized_transcript
        assert metadata["phone_count"] == 1

        # Step 3: Generate Report
        report_service = ReportGenerationService()
        with patch.object(report_service, '_parse_transcript_info') as mock_parse, \
             patch.object(report_service, '_retrieve_theories') as mock_retrieve, \
             patch.object(report_service, '_generate_structured_report') as mock_generate, \
             patch.object(report_service, '_extract_key_dialogues') as mock_extract:

            mock_parse.return_value = {"num_participants": 2}
            mock_retrieve.return_value = [{"theory": "測試理論"}]
            mock_generate.return_value = {"main_issue": "職涯困擾"}
            mock_extract.return_value = []

            report = await report_service.generate_report_from_transcript(
                transcript=sanitized_transcript,
                agent_id=1
            )

            assert "content_json" in report
            assert "citations_json" in report
