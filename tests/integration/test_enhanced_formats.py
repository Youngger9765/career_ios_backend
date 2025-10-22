"""
Integration tests for 10-section (enhanced) report formats
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


class TestEnhancedJSON:
    """Test 10-section report in JSON format"""

    @pytest.mark.asyncio
    async def test_json_structure_and_citations(self, async_client: AsyncClient):
        """
        Expected structure:
        - mode: "enhanced"
        - format: "json"
        - report.conceptualization: contains all 10 sections
        - Sections 五、七、八: must have theory citations [1][2] etc.
        """
        response = await async_client.post(
            "/api/report/generate",
            json={
                "transcript": SAMPLE_TRANSCRIPT,
                "mode": "enhanced",
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
        assert data["mode"] == "enhanced"
        assert data["format"] == "json"

        # Verify report structure
        assert "report" in data
        report = data["report"]

        assert "conceptualization" in report
        conceptualization = report["conceptualization"]

        # Check for all 10 sections
        required_sections = [
            "【一、案主基本資料】",
            "【二、主訴問題】",
            "【三、問題發展脈絡】",
            "【四、求助動機與期待】",
            "【五、多層次因素分析】",
            "【六、個案優勢與資源】",
            "【七、諮詢師的專業判斷】",
            "【八、諮商目標與介入策略】",
            "【九、預期成效與評估】",
            "【十、諮詢師自我反思】"
        ]

        for section in required_sections:
            assert section in conceptualization, f"Missing '{section}'"

        # Verify critical sections have theory citations
        # Section 五: must cite theories
        section_5_start = conceptualization.find("【五、多層次因素分析】")
        section_5_end = conceptualization.find("【六、個案優勢與資源】")
        section_5_content = conceptualization[section_5_start:section_5_end]
        assert "[1]" in section_5_content or "[2]" in section_5_content, \
            "Section 五 must cite theories [1] or [2]"

        # Section 七: must cite theories
        section_7_start = conceptualization.find("【七、諮詢師的專業判斷】")
        section_7_end = conceptualization.find("【八、諮商目標與介入策略】")
        section_7_content = conceptualization[section_7_start:section_7_end]
        assert "[3]" in section_7_content or "[4]" in section_7_content, \
            "Section 七 must cite theories [3] or [4]"

        # Section 八: must cite theories
        section_8_start = conceptualization.find("【八、諮商目標與介入策略】")
        section_8_end = conceptualization.find("【九、預期成效與評估】")
        section_8_content = conceptualization[section_8_start:section_8_end]
        assert "[5]" in section_8_content or "[6]" in section_8_content, \
            "Section 八 must cite theories [5] or [6]"

        # Verify quality_summary exists
        assert "quality_summary" in data
        assert "overall_score" in data["quality_summary"]
        assert data["quality_summary"]["overall_score"] >= 0


class TestEnhancedHTML:
    """Test 10-section report in HTML format"""

    @pytest.mark.asyncio
    async def test_html_structure(self, async_client: AsyncClient):
        """
        Expected:
        - format: "html"
        - Contains all 10 section headers in HTML
        """
        response = await async_client.post(
            "/api/report/generate",
            json={
                "transcript": SAMPLE_TRANSCRIPT,
                "mode": "enhanced",
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

        assert data["mode"] == "enhanced"
        assert data["format"] == "html"

        html_content = data["report"]
        assert isinstance(html_content, str)

        # Verify HTML structure
        assert "<html>" in html_content
        assert "<body>" in html_content

        # Verify key enhanced sections present
        assert "一、案主基本資料" in html_content or "案主基本資料" in html_content
        assert "五、多層次因素分析" in html_content or "多層次因素分析" in html_content
        assert "十、諮詢師自我反思" in html_content or "自我反思" in html_content


class TestEnhancedMarkdown:
    """Test 10-section report in Markdown format"""

    @pytest.mark.asyncio
    async def test_markdown_structure(self, async_client: AsyncClient):
        """
        Expected:
        - format: "markdown"
        - Contains all 10 section headers in Markdown
        """
        response = await async_client.post(
            "/api/report/generate",
            json={
                "transcript": SAMPLE_TRANSCRIPT,
                "mode": "enhanced",
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

        assert data["mode"] == "enhanced"
        assert data["format"] == "markdown"

        md_content = data["report"]
        assert isinstance(md_content, str)

        # Verify Markdown structure
        assert "# 個案報告" in md_content
        assert "## " in md_content

        # Verify key enhanced sections present
        assert "案主基本資料" in md_content
        assert "多層次因素分析" in md_content or "五、" in md_content
        assert "自我反思" in md_content or "十、" in md_content
