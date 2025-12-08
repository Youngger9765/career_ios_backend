"""Unit tests for STTService - Speech-to-Text 服務測試"""

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from app.services.stt_service import STTService


class TestSTTService:
    """測試語音轉文字服務的各種功能"""

    @pytest.fixture
    def stt_service(self):
        """建立 STTService 實例"""
        with patch("app.services.stt_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-api-key"
            return STTService()

    @pytest.mark.asyncio
    async def test_transcribe_audio_success_text_format(self, stt_service):
        """測試成功轉錄音訊（text 格式）"""
        mock_response = "這是測試的轉錄文字"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_audio(
                audio_file_path="/fake/path/audio.mp3",
                language="zh",
                response_format="text",
            )

            assert result == "這是測試的轉錄文字"

            # 驗證 API 被正確呼叫
            stt_service.client.audio.transcriptions.create.assert_called_once()
            call_kwargs = (
                stt_service.client.audio.transcriptions.create.call_args.kwargs
            )
            assert call_kwargs["model"] == "whisper-1"
            assert call_kwargs["language"] == "zh"
            assert call_kwargs["response_format"] == "text"

    @pytest.mark.asyncio
    async def test_transcribe_audio_success_json_format(self, stt_service):
        """測試成功轉錄音訊（json 格式）"""
        mock_response = MagicMock()
        mock_response.text = "這是 JSON 格式的轉錄文字"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_audio(
                audio_file_path="/fake/path/audio.mp3",
                language="zh",
                response_format="json",
            )

            # json 格式應該返回 response.text
            assert result == "這是 JSON 格式的轉錄文字"

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_not_found(self, stt_service):
        """測試音訊檔案不存在的錯誤處理"""
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError) as exc_info:
                await stt_service.transcribe_audio(
                    audio_file_path="/nonexistent/audio.mp3"
                )

            assert "Audio file not found" in str(exc_info.value)
            assert "/nonexistent/audio.mp3" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_english_language(self, stt_service):
        """測試英文語言參數"""
        mock_response = "This is an English transcription"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_audio(
                audio_file_path="/fake/path/audio.mp3",
                language="en",
                response_format="text",
            )

            assert result == "This is an English transcription"

            # 驗證語言參數
            call_kwargs = (
                stt_service.client.audio.transcriptions.create.call_args.kwargs
            )
            assert call_kwargs["language"] == "en"

    @pytest.mark.asyncio
    async def test_transcribe_audio_srt_format(self, stt_service):
        """測試 SRT 字幕格式輸出"""
        mock_response = MagicMock()
        mock_response.text = "1\n00:00:00,000 --> 00:00:02,000\n測試字幕"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_audio(
                audio_file_path="/fake/path/audio.mp3",
                language="zh",
                response_format="srt",
            )

            assert "00:00:00,000 --> 00:00:02,000" in result
            assert "測試字幕" in result

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_success(self, stt_service):
        """測試帶時間戳的轉錄"""
        # 模擬 OpenAI API 回應
        mock_segment_1 = MagicMock()
        mock_segment_1.start = 0.0
        mock_segment_1.end = 2.5
        mock_segment_1.text = "第一段文字"

        mock_segment_2 = MagicMock()
        mock_segment_2.start = 2.5
        mock_segment_2.end = 5.0
        mock_segment_2.text = "第二段文字"

        mock_response = MagicMock()
        mock_response.text = "第一段文字 第二段文字"
        mock_response.segments = [mock_segment_1, mock_segment_2]
        mock_response.language = "zh"
        mock_response.duration = 5.0

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_with_timestamps(
                audio_file_path="/fake/path/audio.mp3", language="zh"
            )

            # 驗證回應結構
            assert result["text"] == "第一段文字 第二段文字"
            assert result["language"] == "zh"
            assert result["duration"] == 5.0
            assert len(result["segments"]) == 2

            # 驗證第一段
            assert result["segments"][0]["start"] == 0.0
            assert result["segments"][0]["end"] == 2.5
            assert result["segments"][0]["text"] == "第一段文字"

            # 驗證第二段
            assert result["segments"][1]["start"] == 2.5
            assert result["segments"][1]["end"] == 5.0
            assert result["segments"][1]["text"] == "第二段文字"

            # 驗證 API 呼叫參數
            call_kwargs = (
                stt_service.client.audio.transcriptions.create.call_args.kwargs
            )
            assert call_kwargs["response_format"] == "verbose_json"
            assert call_kwargs["timestamp_granularities"] == ["segment"]

    @pytest.mark.asyncio
    async def test_transcribe_with_timestamps_file_not_found(self, stt_service):
        """測試帶時間戳轉錄時檔案不存在"""
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError) as exc_info:
                await stt_service.transcribe_with_timestamps(
                    audio_file_path="/nonexistent/audio.mp3"
                )

            assert "Audio file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_audio_api_error(self, stt_service):
        """測試 OpenAI API 錯誤處理"""
        from openai import RateLimitError

        # 模擬 OpenAI RateLimitError
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_body = {"error": {"message": "Rate limit exceeded"}}

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            side_effect=RateLimitError(
                "Rate limit exceeded", response=mock_response, body=mock_body
            ),
        ):
            with pytest.raises(RateLimitError) as exc_info:
                await stt_service.transcribe_audio(
                    audio_file_path="/fake/path/audio.mp3"
                )

            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_multiple_formats(self, stt_service):
        """測試多種音訊格式支援"""
        formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
        mock_response = "轉錄成功"

        for audio_format in formats:
            with patch("os.path.exists", return_value=True), patch(
                "builtins.open", mock_open(read_data=b"fake audio data")
            ), patch.object(
                stt_service.client.audio.transcriptions,
                "create",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                result = await stt_service.transcribe_audio(
                    audio_file_path=f"/fake/path/audio.{audio_format}"
                )

                assert result == "轉錄成功"

    def test_stt_service_initialization(self, stt_service):
        """測試 STTService 初始化"""
        assert stt_service.model == "whisper-1"
        assert stt_service.client is not None
        assert hasattr(stt_service.client, "audio")


class TestSTTServiceRealWorldScenarios:
    """真實場景測試"""

    @pytest.fixture
    def stt_service(self):
        with patch("app.services.stt_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-api-key"
            return STTService()

    @pytest.mark.asyncio
    async def test_counseling_session_recording(self, stt_service):
        """測試諮詢會談錄音轉錄場景"""
        # 模擬一段諮詢對話的轉錄
        mock_response = MagicMock()
        mock_response.text = """
        諮詢師：今天想聊些什麼？
        案主：最近工作壓力很大，感覺快撐不下去了。
        諮詢師：能具體說說是什麼讓你感到壓力嗎？
        案主：老闆一直加派任務，同事也不太配合。
        """

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_audio(
                audio_file_path="/counseling/session_2024_01_15.m4a",
                language="zh",
                response_format="json",
            )

            # 驗證轉錄內容包含對話
            assert "諮詢師：" in result
            assert "案主：" in result
            assert "工作壓力" in result

    @pytest.mark.asyncio
    async def test_long_session_with_segments(self, stt_service):
        """測試長時間會談的分段轉錄"""
        # 模擬 60 分鐘會談的 10 個片段
        segments = []
        for i in range(10):
            segment = MagicMock()
            segment.start = i * 360.0  # 每 6 分鐘一段
            segment.end = (i + 1) * 360.0
            segment.text = f"第 {i+1} 段對話內容"
            segments.append(segment)

        mock_response = MagicMock()
        mock_response.text = " ".join([f"第 {i+1} 段對話內容" for i in range(10)])
        mock_response.segments = segments
        mock_response.language = "zh"
        mock_response.duration = 3600.0  # 60 分鐘

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_with_timestamps(
                audio_file_path="/counseling/long_session.wav"
            )

            # 驗證總時長
            assert result["duration"] == 3600.0

            # 驗證片段數量
            assert len(result["segments"]) == 10

            # 驗證第一段和最後一段
            assert result["segments"][0]["start"] == 0.0
            assert result["segments"][-1]["end"] == 3600.0

    @pytest.mark.asyncio
    async def test_mixed_language_transcription(self, stt_service):
        """測試中英混合語音轉錄"""
        mock_response = "我今天用了 Python 和 FastAPI 來開發 API"

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=b"fake audio data")
        ), patch.object(
            stt_service.client.audio.transcriptions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await stt_service.transcribe_audio(
                audio_file_path="/test/mixed_language.mp3",
                language="zh",  # 主要語言設為中文
            )

            # 應該能夠識別中英混合
            assert "Python" in result
            assert "FastAPI" in result
            assert "開發" in result
