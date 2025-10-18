"""Unit tests for report validators"""

import pytest
from app.utils.report_validators import (
    validate_report_structure,
    validate_citations,
    extract_section,
    calculate_quality_score
)


class TestValidateReportStructure:
    """測試報告結構驗證功能"""

    def test_complete_report(self):
        """測試完整報告結構驗證"""
        report_text = """
        【一、案主基本資料】
        姓名：張三

        【二、主訴問題】
        - 個案陳述：工作迷茫
        - 諮詢師觀察：缺乏目標

        【三、問題發展脈絡】
        出現時間：3個月前

        【四、求助動機與期待】
        引發因素：升遷失敗

        【五、多層次因素分析】
        個人因素：年齡28歲

        【六、個案優勢與資源】
        心理優勢：積極主動

        【七、諮詢師的專業判斷】
        問題假設：生涯發展停滯

        【八、諮商目標與介入策略】
        諮商目標：找到方向

        【九、預期成效與評估】
        短期指標：明確目標

        【十、諮詢師自我反思】
        反思內容
        """

        result = validate_report_structure(report_text)

        assert result["complete"] is True
        assert result["coverage"] == 100.0
        assert len(result["missing_sections"]) == 0

    def test_incomplete_report(self):
        """測試不完整報告（缺少段落）"""
        report_text = """
        【一、案主基本資料】
        姓名：張三

        【二、主訴問題】
        - 個案陳述：工作迷茫

        【五、多層次因素分析】
        個人因素：年齡28歲
        """

        result = validate_report_structure(report_text)

        assert result["complete"] is False
        assert result["coverage"] == 30.0  # 3/10 = 30%
        assert len(result["missing_sections"]) == 7
        assert "【三、問題發展脈絡】" in result["missing_sections"]
        assert "【四、求助動機與期待】" in result["missing_sections"]

    def test_empty_report(self):
        """測試空報告"""
        result = validate_report_structure("")

        assert result["complete"] is False
        assert result["coverage"] == 0.0
        assert len(result["missing_sections"]) == 10

    def test_legacy_complete_report(self):
        """測試舊版完整報告（5段式）"""
        report_text = """
        【主訴問題】
        案主在此次諮詢中主要表達了對未來職涯方向的困惑。

        【成因分析】
        根據諮詢過程中的觀察，案主的主訴問題可能源於對自身能力的認知不足。

        【晤談目標（移動主訴）】
        在理解案主的需求後，諮詢師假設此次晤談的目標為協助案主探索職涯與生涯的關聯。

        【介入策略】
        為了達成上述目標，諮詢師計劃運用引導式提問的方式深入探索案主的內在特質。

        【目前成效評估】
        截至目前，案主對於自我認識的深度有所提高。
        """

        result = validate_report_structure(report_text, use_legacy=True)

        assert result["complete"] is True
        assert result["coverage"] == 100.0
        assert len(result["missing_sections"]) == 0

    def test_legacy_incomplete_report(self):
        """測試舊版不完整報告（缺少段落）"""
        report_text = """
        【主訴問題】
        案主在此次諮詢中主要表達了對未來職涯方向的困惑。

        【成因分析】
        根據諮詢過程中的觀察，案主的主訴問題可能源於對自身能力的認知不足。
        """

        result = validate_report_structure(report_text, use_legacy=True)

        assert result["complete"] is False
        assert result["coverage"] == 40.0  # 2/5 = 40%
        assert len(result["missing_sections"]) == 3
        assert "【晤談目標（移動主訴）】" in result["missing_sections"]
        assert "【介入策略】" in result["missing_sections"]
        assert "【目前成效評估】" in result["missing_sections"]


class TestValidateCitations:
    """測試理論引用驗證功能"""

    def test_all_critical_sections_cited(self):
        """測試所有核心段落都有引用"""
        report_text = """
        【五、多層次因素分析】
        根據 Super 理論 [1]，案主處於探索期。
        從發展觀點 [2] 來看，這是正常現象。

        【七、諮詢師的專業判斷】
        基於動機理論 [3][4]，我認為案主缺乏內在動機。

        【八、諮商目標與介入策略】
        採用卡片排序 [5] 和生涯幻遊 [6]。
        """

        result = validate_citations(report_text)

        assert result["all_critical_sections_cited"] is True
        assert result["total_citations"] == 6
        assert result["has_rationale"] is True

        # 檢查各段落詳情
        assert result["section_details"]["【五、多層次因素分析】"]["has_citations"] is True
        assert result["section_details"]["【五、多層次因素分析】"]["citation_count"] == 2
        assert result["section_details"]["【七、諮詢師的專業判斷】"]["has_citations"] is True
        assert result["section_details"]["【八、諮商目標與介入策略】"]["has_citations"] is True

    def test_partial_citations(self):
        """測試部分段落有引用"""
        report_text = """
        【五、多層次因素分析】
        根據 Super 理論 [1]，案主處於探索期。

        【七、諮詢師的專業判斷】
        我認為案主缺乏內在動機。（無引用）

        【八、諮商目標與介入策略】
        採用卡片排序 [2]。
        """

        result = validate_citations(report_text)

        assert result["all_critical_sections_cited"] is False
        assert result["total_citations"] == 2

        # 第七段落缺少引用
        assert result["section_details"]["【七、諮詢師的專業判斷】"]["has_citations"] is False
        assert result["section_details"]["【七、諮詢師的專業判斷】"]["status"] == "❌"

    def test_no_citations(self):
        """測試完全沒有引用"""
        report_text = """
        【五、多層次因素分析】
        案主年齡 28 歲。

        【七、諮詢師的專業判斷】
        問題很複雜。

        【八、諮商目標與介入策略】
        使用一些技術。
        """

        result = validate_citations(report_text)

        assert result["all_critical_sections_cited"] is False
        assert result["total_citations"] == 0
        assert all(
            not detail["has_citations"]
            for detail in result["section_details"].values()
        )

    def test_has_rationale_detection(self):
        """測試引用理由檢測"""
        # 有理由
        report_with_rationale = """
        【五、多層次因素分析】
        根據 Super 理論 [1]，案主...
        """
        result = validate_citations(report_with_rationale)
        assert result["has_rationale"] is True

        # 無理由（只有引用數字）
        report_without_rationale = """
        【五、多層次因素分析】
        案主處於探索期 [1]。
        """
        result = validate_citations(report_without_rationale)
        assert result["has_rationale"] is False

    def test_legacy_citations(self):
        """測試舊版報告引用檢查（2個核心段落）"""
        report_text = """
        【主訴問題】
        案主在此次諮詢中主要表達了對未來職涯方向的困惑。

        【成因分析】
        根據職涯規劃三角形的理論 [1]，職涯的發展需要平衡。
        薩提爾冰山理論 [2] 所指出的，表面上的迷茫可能掩蓋更深層問題。

        【晤談目標（移動主訴）】
        在理解案主的需求後，諮詢師假設此次晤談的目標。

        【介入策略】
        諮詢師計劃運用引導式提問 [3] 的方式深入探索案主的內在特質。

        【目前成效評估】
        截至目前，案主對於自我認識的深度有所提高。
        """

        result = validate_citations(report_text, use_legacy=True)

        # Legacy version only has 2 critical sections
        assert len(result["section_details"]) == 2
        assert "【成因分析】" in result["section_details"]
        assert "【介入策略】" in result["section_details"]

        # Both sections have citations
        assert result["section_details"]["【成因分析】"]["has_citations"] is True
        assert result["section_details"]["【成因分析】"]["citation_count"] == 2
        assert result["section_details"]["【介入策略】"]["has_citations"] is True
        assert result["section_details"]["【介入策略】"]["citation_count"] == 1

        assert result["all_critical_sections_cited"] is True
        assert result["total_citations"] == 3
        assert result["has_rationale"] is True


class TestExtractSection:
    """測試段落提取功能"""

    def test_extract_middle_section(self):
        """測試提取中間段落"""
        report_text = """
        【一、案主基本資料】
        姓名：張三

        【二、主訴問題】
        個案陳述：工作迷茫
        諮詢師觀察：缺乏目標

        【三、問題發展脈絡】
        出現時間：3個月前
        """

        section = extract_section(report_text, "【二、主訴問題】")

        assert "個案陳述：工作迷茫" in section
        assert "諮詢師觀察：缺乏目標" in section
        assert "【三、問題發展脈絡】" not in section

    def test_extract_last_section(self):
        """測試提取最後段落"""
        report_text = """
        【九、預期成效與評估】
        短期指標：明確目標

        【十、諮詢師自我反思】
        本次晤談順利
        反思：可以更深入
        """

        section = extract_section(report_text, "【十、諮詢師自我反思】")

        assert "本次晤談順利" in section
        assert "反思：可以更深入" in section

    def test_extract_nonexistent_section(self):
        """測試提取不存在的段落"""
        report_text = "【一、案主基本資料】姓名：張三"

        section = extract_section(report_text, "【九十九、不存在】")

        assert section == ""


class TestCalculateQualityScore:
    """測試品質分數計算功能"""

    def test_perfect_score(self):
        """測試完美報告的分數"""
        structure = {
            "coverage": 100.0,
            "complete": True,
            "missing_sections": []
        }

        citation = {
            "all_critical_sections_cited": True,
            "total_citations": 7,
            "has_rationale": True,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": True},
                "【八、諮商目標與介入策略】": {"has_citations": True}
            }
        }

        score = calculate_quality_score(structure, citation)

        assert score == 100.0

    def test_good_score(self):
        """測試良好報告的分數"""
        structure = {
            "coverage": 100.0,
            "complete": True,
            "missing_sections": []
        }

        citation = {
            "all_critical_sections_cited": True,
            "total_citations": 5,  # 少一點引用
            "has_rationale": True,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": True},
                "【八、諮商目標與介入策略】": {"has_citations": True}
            }
        }

        score = calculate_quality_score(structure, citation)

        # 結構 100 * 0.4 = 40
        # 引用覆蓋 100% = 40
        # 有理由 = 10
        # 引用數量 5/7 * 10 = 7.1
        # 總分約 97.1
        assert 95.0 <= score <= 100.0

    def test_incomplete_structure(self):
        """測試結構不完整的分數"""
        structure = {
            "coverage": 70.0,  # 缺少 3 個段落
            "complete": False,
            "missing_sections": ["【三、問題發展脈絡】", "【四、求助動機與期待】", "【六、個案優勢與資源】"]
        }

        citation = {
            "all_critical_sections_cited": True,
            "total_citations": 6,
            "has_rationale": True,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": True},
                "【八、諮商目標與介入策略】": {"has_citations": True}
            }
        }

        score = calculate_quality_score(structure, citation)

        # 結構 70 * 0.4 = 28
        # 引用覆蓋 100% = 40
        # 有理由 = 10
        # 引用數量 6/7 * 10 = 8.6
        # 總分約 86.6
        assert 85.0 <= score <= 90.0

    def test_poor_citations(self):
        """測試引用不足的分數"""
        structure = {
            "coverage": 100.0,
            "complete": True,
            "missing_sections": []
        }

        citation = {
            "all_critical_sections_cited": False,  # 只有部分段落有引用
            "total_citations": 2,
            "has_rationale": False,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": False},
                "【八、諮商目標與介入策略】": {"has_citations": True}
            }
        }

        score = calculate_quality_score(structure, citation)

        # 結構 100 * 0.4 = 40
        # 引用覆蓋 2/3 * 40 = 26.7
        # 無理由 = 0
        # 引用數量 2/7 * 10 = 2.9
        # 總分約 69.6
        assert 65.0 <= score <= 75.0

    def test_failing_score(self):
        """測試不及格報告的分數"""
        structure = {
            "coverage": 50.0,  # 缺少一半段落
            "complete": False,
            "missing_sections": ["【三、問題發展脈絡】", "【四、求助動機與期待】", "【六、個案優勢與資源】", "【九、預期成效與評估】", "【十、諮詢師自我反思】"]
        }

        citation = {
            "all_critical_sections_cited": False,
            "total_citations": 1,
            "has_rationale": False,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": False},
                "【八、諮商目標與介入策略】": {"has_citations": False}
            }
        }

        score = calculate_quality_score(structure, citation)

        # 結構 50 * 0.4 = 20
        # 引用覆蓋 1/3 * 40 = 13.3
        # 無理由 = 0
        # 引用數量 1/7 * 10 = 1.4
        # 總分約 34.7
        assert score < 60.0
