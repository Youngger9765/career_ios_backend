"""
Tests for report formatters (TDD-driven refactoring)

Testing approach:
1. Test existing behavior (regression tests)
2. Test new refactored behavior (should produce identical output)
3. Test edge cases and error conditions
"""

import pytest


# Sample report data for testing
@pytest.fixture
def sample_report():
    """Standard test report with all fields populated"""
    return {
        "client_info": {
            "name": "小明",
            "age": "28歲",
            "gender": "男性",
            "occupation": "軟體工程師",
        },
        "main_concerns": ["職涯迷茫", "缺乏工作動力"],
        "counseling_goals": ["釐清職涯方向", "提升工作滿意度"],
        "techniques": ["同理心傾聽", "開放式提問"],
        "conceptualization": "案主處於職涯探索期，面臨價值觀衝突...",
        "theories": [
            {
                "document": "Super生涯發展理論",
                "score": 0.85,
                "text": "個體在不同生涯階段會經歷成長、探索、建立、維持和衰退等階段...",
            },
            {
                "document": "Holland類型論",
                "score": 0.78,
                "text": "職業興趣可分為實際型(R)、研究型(I)、藝術型(A)等六種類型...",
            },
        ],
        "dialogue_excerpts": [
            {"order": 1, "speaker": "案主", "text": "我不知道自己真正想要什麼..."},
            {"order": 2, "speaker": "諮詢師", "text": "可以多說一些你的感受嗎？"},
        ],
    }


@pytest.fixture
def minimal_report():
    """Minimal report with only required fields"""
    return {
        "client_info": {"name": "匿名"},
        "main_concerns": ["未提供"],
        "counseling_goals": [],
        "techniques": [],
        "conceptualization": "",
        "theories": [],
        "dialogue_excerpts": [],
    }


class TestFormatReportAsHTML:
    """Test HTML formatting (existing behavior must be preserved)"""

    def test_html_contains_all_sections(self, sample_report):
        """HTML should contain all major sections"""
        from app.api.rag_report import format_report_as_html

        html = format_report_as_html(sample_report)

        assert "<h1>個案報告</h1>" in html
        assert "<h2>案主基本資料</h2>" in html
        assert "<h2>主訴問題</h2>" in html
        assert "<h2>晤談目標</h2>" in html
        assert "<h2>諮詢技巧</h2>" in html
        assert "<h2>個案概念化</h2>" in html
        assert "<h2>相關理論文獻</h2>" in html
        assert "<h2>關鍵對話摘錄</h2>" in html

    def test_html_client_info_as_table(self, sample_report):
        """Client info should be formatted as HTML table"""
        from app.api.rag_report import format_report_as_html

        html = format_report_as_html(sample_report)

        assert "<table border='1'>" in html
        assert "<tr><th>name</th><td>小明</td></tr>" in html
        assert "<tr><th>age</th><td>28歲</td></tr>" in html

    def test_html_list_values_joined(self, sample_report):
        """List values in client_info should be comma-separated"""
        from app.api.rag_report import format_report_as_html

        report_with_list = sample_report.copy()
        report_with_list["client_info"]["skills"] = ["Python", "Java", "C++"]

        html = format_report_as_html(report_with_list)

        assert "Python, Java, C++" in html

    def test_html_concerns_as_unordered_list(self, sample_report):
        """Main concerns should be formatted as <ul>"""
        from app.api.rag_report import format_report_as_html

        html = format_report_as_html(sample_report)

        assert "<ul>" in html
        assert "<li>職涯迷茫</li>" in html
        assert "<li>缺乏工作動力</li>" in html

    def test_html_theories_with_score(self, sample_report):
        """Theories should show document name and similarity score"""
        from app.api.rag_report import format_report_as_html

        html = format_report_as_html(sample_report)

        assert "Super生涯發展理論" in html
        assert "相似度: 0.85" in html
        assert "Holland類型論" in html
        assert "相似度: 0.78" in html

    def test_html_dialogues_as_ordered_list(self, sample_report):
        """Dialogues should be formatted as <ol>"""
        from app.api.rag_report import format_report_as_html

        html = format_report_as_html(sample_report)

        assert "<ol>" in html
        assert "<li><b>案主</b>: 我不知道自己真正想要什麼...</li>" in html

    def test_html_valid_structure(self, sample_report):
        """HTML should have valid structure"""
        from app.api.rag_report import format_report_as_html

        html = format_report_as_html(sample_report)

        assert html.startswith("<html><body>")
        assert html.endswith("</body></html>")

    def test_html_empty_lists_handled(self, minimal_report):
        """Should handle empty lists gracefully"""
        from app.api.rag_report import format_report_as_html

        html = format_report_as_html(minimal_report)

        # Should still contain section headers even if empty
        assert "<h2>主訴問題</h2>" in html
        assert "<h2>晤談目標</h2>" in html


class TestFormatReportAsMarkdown:
    """Test Markdown formatting (existing behavior must be preserved)"""

    def test_markdown_contains_all_sections(self, sample_report):
        """Markdown should contain all major sections"""
        from app.api.rag_report import format_report_as_markdown

        md = format_report_as_markdown(sample_report)

        assert "# 個案報告" in md
        assert "## 案主基本資料" in md
        assert "## 主訴問題" in md
        assert "## 晤談目標" in md
        assert "## 諮詢技巧" in md
        assert "## 個案概念化" in md
        assert "## 相關理論文獻" in md
        assert "## 關鍵對話摘錄" in md

    def test_markdown_client_info_as_list(self, sample_report):
        """Client info should be formatted as markdown list"""
        from app.api.rag_report import format_report_as_markdown

        md = format_report_as_markdown(sample_report)

        assert "- **name**: 小明" in md
        assert "- **age**: 28歲" in md

    def test_markdown_list_values_joined(self, sample_report):
        """List values in client_info should be comma-separated"""
        from app.api.rag_report import format_report_as_markdown

        report_with_list = sample_report.copy()
        report_with_list["client_info"]["skills"] = ["Python", "Java", "C++"]

        md = format_report_as_markdown(report_with_list)

        assert "Python, Java, C++" in md

    def test_markdown_concerns_as_list(self, sample_report):
        """Main concerns should be bullet points"""
        from app.api.rag_report import format_report_as_markdown

        md = format_report_as_markdown(sample_report)

        assert "- 職涯迷茫" in md
        assert "- 缺乏工作動力" in md

    def test_markdown_theories_as_subsections(self, sample_report):
        """Theories should be formatted as h3 subsections"""
        from app.api.rag_report import format_report_as_markdown

        md = format_report_as_markdown(sample_report)

        assert "### [1] Super生涯發展理論" in md
        assert "**相似度**: 0.85" in md
        assert "### [2] Holland類型論" in md
        assert "**相似度**: 0.78" in md

    def test_markdown_dialogues_numbered(self, sample_report):
        """Dialogues should show order numbers"""
        from app.api.rag_report import format_report_as_markdown

        md = format_report_as_markdown(sample_report)

        assert "1. **案主**: 我不知道自己真正想要什麼..." in md
        assert "2. **諮詢師**: 可以多說一些你的感受嗎？" in md

    def test_markdown_empty_lists_handled(self, minimal_report):
        """Should handle empty lists gracefully"""
        from app.api.rag_report import format_report_as_markdown

        md = format_report_as_markdown(minimal_report)

        # Should still contain section headers even if empty
        assert "## 主訴問題" in md
        assert "## 晤談目標" in md


class TestWrappedJSONHandling:
    """Test handling of wrapped JSON from RAG API (Bug fix for markdown generation)

    Context: RAG API returns wrapped JSON like {"mode": ..., "report": {...}, ...}
    but formatters expect unwrapped report data.
    This was causing content_markdown to be empty (only skeleton headers).
    """

    @pytest.fixture
    def wrapped_rag_response(self, sample_report):
        """Simulates actual RAG API response structure"""
        return {
            "mode": "enhanced",
            "report": sample_report,  # Actual report nested here
            "format": "json",
            "quality_summary": {"overall_score": 85, "grade": "良好"},
        }

    def test_formatter_with_wrapped_json_produces_empty_skeleton(
        self, wrapped_rag_response
    ):
        """
        Document the bug: Formatter with wrapped JSON produces only headers (85 chars)

        This test documents what happens when wrapped JSON is passed to formatter.
        It should produce empty skeleton, which is the BUG we're fixing.
        """
        from app.utils.report_formatters import create_formatter

        formatter = create_formatter("markdown")

        # Passing wrapped JSON directly (wrong behavior)
        buggy_markdown = formatter.format(wrapped_rag_response)

        # This is what HAPPENS (not what we want)
        assert (
            len(buggy_markdown) == 85
        ), "Wrapped JSON produces empty skeleton (85 chars)"
        assert "小明" not in buggy_markdown, "Wrapped JSON loses actual content"

    def test_unwrap_helper_extracts_report_from_wrapped_json(
        self, wrapped_rag_response
    ):
        """
        Test the unwrap_report() helper function

        This is the ACTUAL FIX we're testing in TDD fashion.
        """
        from app.utils.report_formatters import unwrap_report

        # The fix: use unwrap_report() helper
        actual_report = unwrap_report(wrapped_rag_response)

        # Verify unwrap worked correctly
        assert "client_info" in actual_report, "Should extract actual report"
        assert "main_concerns" in actual_report
        assert actual_report["client_info"]["name"] == "小明"

    def test_unwrap_helper_is_idempotent(self, sample_report):
        """unwrap_report() should be safe to call on already-unwrapped data"""
        from app.utils.report_formatters import unwrap_report

        # Calling unwrap on already-unwrapped data should return same data
        result = unwrap_report(sample_report)
        assert result == sample_report

    def test_formatter_with_unwrapped_json_produces_full_content(
        self, wrapped_rag_response
    ):
        """
        Test that formatter works correctly with unwrapped data

        This is the EXPECTED BEHAVIOR after the fix.
        """
        from app.utils.report_formatters import create_formatter, unwrap_report

        formatter = create_formatter("markdown")

        # Apply the fix: unwrap before formatting (using helper function)
        correct_markdown = formatter.format(unwrap_report(wrapped_rag_response))

        # These assertions verify the fix works
        assert len(correct_markdown) > 200, "Should generate full markdown content"
        assert "小明" in correct_markdown, "Should contain client name"
        assert "職涯迷茫" in correct_markdown, "Should contain main concerns"
        assert "Super生涯發展理論" in correct_markdown, "Should contain theories"


class TestReportFormatterRefactoring:
    """Test refactored formatter with common logic extraction"""

    def test_html_output_unchanged_after_refactoring(self, sample_report):
        """HTML output should remain identical after refactoring"""
        from app.api.rag_report import format_report_as_html

        # This test will initially PASS (using old implementation)
        # After refactoring, it must still PASS
        html = format_report_as_html(sample_report)

        # Key assertions to ensure backward compatibility
        assert "個案報告" in html
        assert "小明" in html
        assert "職涯迷茫" in html
        assert "Super生涯發展理論" in html

    def test_markdown_output_unchanged_after_refactoring(self, sample_report):
        """Markdown output should remain identical after refactoring"""
        from app.api.rag_report import format_report_as_markdown

        # This test will initially PASS (using old implementation)
        # After refactoring, it must still PASS
        md = format_report_as_markdown(sample_report)

        # Key assertions to ensure backward compatibility
        assert "# 個案報告" in md
        assert "- **name**: 小明" in md
        assert "- 職涯迷茫" in md
        assert "### [1] Super生涯發展理論" in md

    def test_both_formatters_handle_same_data_consistently(self, sample_report):
        """Both formatters should process the same data structure"""
        from app.api.rag_report import format_report_as_html, format_report_as_markdown

        html = format_report_as_html(sample_report)
        md = format_report_as_markdown(sample_report)

        # Both should contain the same content (different formats)
        for value in ["小明", "職涯迷茫", "Super生涯發展理論"]:
            assert value in html
            assert value in md
