"""
Integration tests for 5-section (legacy) report formats
Tests JSON, HTML, and Markdown output formats
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.asyncio, pytest.mark.slow, pytest.mark.integration]

# Sample transcript for testing
SAMPLE_TRANSCRIPT = """Co: 你好，今天想聊什麼？
Cl: 我最近工作壓力很大，不知道該不該轉職。我在一家科技公司當工程師已經三年了，薪水還可以，但每天加班到很晚,感覺快撐不下去了。
Co: 聽起來你工作壓力很大，可以多說一些嗎？
Cl: 我今年28歲，大學資訊工程畢業。家裡經濟還好，但父母希望我有穩定工作。最近常失眠，也沒時間運動。
Co: 你提到想轉職，那你期待的工作是什麼樣子？
Cl: 我希望能有work-life balance，也想做有意義的事，不只是寫code。"""


class TestLegacyJSON:
    """Test 5-section report in JSON format"""

    @pytest.mark.asyncio
    async def test_json_structure(self, async_client: AsyncClient):
        """
        Expected structure:
        - mode: "legacy"
        - format: "json"
        - report.conceptualization: contains 5 sections
        - report.theories: RAG retrieved theories
        """
        response = await async_client.post(
            "/api/report/generate",
            json={
                "transcript": SAMPLE_TRANSCRIPT,
                "mode": "legacy",
                "output_format": "json",
                "rag_system": "openai",
                "num_participants": 2,
                "top_k": 7,
                "similarity_threshold": 0.25
            },
            timeout=120.0
        )

        assert response.status_code == 200
        data = response.json()

        # Verify mode and format
        assert data["mode"] == "legacy"
        assert data["format"] == "json"

        # Verify report structure
        assert "report" in data
        report = data["report"]

        # Verify client_info exists
        assert "client_info" in report
        assert "name" in report["client_info"]

        # Verify conceptualization contains 5 sections
        assert "conceptualization" in report
        conceptualization = report["conceptualization"]

        # Check for 5 key sections
        assert "【主訴問題】" in conceptualization
        assert "【成因分析】" in conceptualization
        assert "【晤談目標" in conceptualization
        assert "【介入策略】" in conceptualization
        assert "【成效評估】" in conceptualization or "【目前成效評估】" in conceptualization

        # Verify theories were retrieved
        assert "theories" in report
        assert len(report["theories"]) > 0

        # Verify theory structure
        for theory in report["theories"]:
            assert "text" in theory
            assert "document" in theory
            assert "score" in theory


class TestLegacyHTML:
    """Test 5-section report in HTML format"""

    @pytest.mark.asyncio
    async def test_html_structure(self, async_client: AsyncClient):
        """
        Expected:
        - format: "html"
        - Valid HTML structure with tags
        - Contains 5 section headers
        """
        response = await async_client.post(
            "/api/report/generate",
            json={
                "transcript": SAMPLE_TRANSCRIPT,
                "mode": "legacy",
                "output_format": "html",
                "rag_system": "openai",
                "num_participants": 2,
                "top_k": 5,
                "similarity_threshold": 0.25
            },
            timeout=120.0
        )

        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "legacy"
        assert data["format"] == "html"
        assert "report" in data

        html_content = data["report"]
        assert isinstance(html_content, str)

        # Verify HTML structure
        assert "<html>" in html_content
        assert "<body>" in html_content
        assert "</html>" in html_content

        # Verify sections present
        assert "個案報告" in html_content or "案主基本資料" in html_content
        assert "主訴問題" in html_content
        assert "相關理論文獻" in html_content or "theories" in html_content


class TestLegacyMarkdown:
    """Test 5-section report in Markdown format"""

    @pytest.mark.asyncio
    async def test_markdown_structure(self, async_client: AsyncClient):
        """
        Expected:
        - format: "markdown"
        - Valid Markdown with headers
        - Contains 5 section headers
        """
        response = await async_client.post(
            "/api/report/generate",
            json={
                "transcript": SAMPLE_TRANSCRIPT,
                "mode": "legacy",
                "output_format": "markdown",
                "rag_system": "openai",
                "num_participants": 2,
                "top_k": 5,
                "similarity_threshold": 0.25
            },
            timeout=120.0
        )

        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "legacy"
        assert data["format"] == "markdown"
        assert "report" in data

        md_content = data["report"]
        assert isinstance(md_content, str)

        # Verify Markdown structure
        assert "# 個案報告" in md_content
        assert "## " in md_content

        # Verify sections present
        assert "主訴問題" in md_content
        assert "案主基本資料" in md_content or "client_info" in md_content
