"""E2E integration tests for enhanced report generation (M3)

Tests the complete flow:
1. Transcript parsing → 2. RAG query → 3. Report generation → 4. Quality validation
"""


import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.slow, pytest.mark.integration]

from app.utils.rag_query_builder import build_enhanced_query
from app.utils.report_quality import generate_quality_summary
from app.utils.report_validators import (
    calculate_quality_score,
    validate_citations,
    validate_report_structure,
)


class TestReportGenerationE2E:
    """端到端測試：從解析到品質驗證"""

    @pytest.fixture
    def sample_parsed_data(self):
        """模擬逐字稿解析結果"""
        return {
            "client_name": "小美（化名）",
            "age": 28,
            "gender": "女性",
            "education": "碩士",
            "occupation": "軟體工程師",
            "location": "台北",
            "economic_status": "穩定",
            "family_relations": "與父母同住",
            "main_concerns": ["職涯迷茫", "工作倦怠", "缺乏方向"],
            "counseling_goals": ["找到職涯方向", "提升工作動機"],
            "counselor_techniques": ["卡片排序", "生涯幻遊"],
            "session_content": "個案表示最近工作感到迷茫，不確定未來方向...",
            "counselor_self_evaluation": "本次晤談順利建立關係"
        }

    @pytest.fixture
    def sample_theories(self):
        """模擬 RAG 檢索到的理論"""
        return [
            {
                "id": 1,
                "title": "Super 生涯發展理論",
                "content": "Super 認為個體生涯發展分為五個階段：成長期、探索期、建立期...",
                "similarity": 0.85
            },
            {
                "id": 2,
                "title": "自我效能理論",
                "content": "Bandura 提出自我效能影響個人選擇與表現...",
                "similarity": 0.78
            }
        ]

    def test_enhanced_query_construction(self, sample_parsed_data):
        """測試 M2.1: 增強版 RAG 查詢構建"""
        query = build_enhanced_query(sample_parsed_data)

        # 應包含生涯階段
        assert "建立期" in query or "28" in query

        # 應包含人口統計
        assert "女性" in query or "碩士" in query

        # 應包含主訴（前3個）
        assert any(concern in query for concern in sample_parsed_data["main_concerns"][:3])

        # 應包含技巧（前2個）
        assert any(tech in query for tech in sample_parsed_data["counselor_techniques"][:2])

    def test_complete_report_validation(self):
        """測試 M1: 完整報告結構驗證"""
        complete_report = """
        【一、案主基本資料】
        姓名：小美（化名）
        年齡：28歲

        【二、主訴問題】
        - 個案陳述：感到職涯迷茫
        - 諮詢師觀察：缺乏明確目標

        【三、問題發展脈絡】
        出現時間：3個月前

        【四、求助動機與期待】
        引發因素：工作倦怠

        【五、多層次因素分析】
        根據 Super 生涯發展理論 [1]，案主 28 歲處於建立期，應開始立足職場。
        從個人因素來看，案主性格較為被動 [2]。

        【六、個案優勢與資源】
        心理優勢：積極求助

        【七、諮詢師的專業判斷】
        基於自我效能理論 [3]，問題源於過往成功經驗不足。
        從動機理論觀點 [4]，案主缺乏內在動機。

        【八、諮商目標與介入策略】
        採用卡片排序法 [5] 協助澄清價值觀，此技術適合探索階段個案。
        搭配生涯幻遊 [6] 增強自我覺察。

        【九、預期成效與評估】
        短期指標：3個月內完成價值觀澄清

        【十、諮詢師自我反思】
        本次晤談成功建立信任關係
        """

        # 結構驗證
        structure = validate_report_structure(complete_report)
        assert structure["complete"] is True
        assert structure["coverage"] == 100.0

        # 引用驗證
        citation = validate_citations(complete_report)
        assert citation["all_critical_sections_cited"] is True
        assert citation["total_citations"] >= 6
        assert citation["has_rationale"] is True

        # 品質分數
        score = calculate_quality_score(structure, citation)
        assert score >= 90.0  # 應該是優秀等級

    def test_quality_summary_generation(self, sample_parsed_data, sample_theories):
        """測試 M1.3: 品質摘要生成"""
        report_text = """
        【一、案主基本資料】姓名：小美
        【二、主訴問題】職涯迷茫
        【三、問題發展脈絡】3個月前開始
        【四、求助動機與期待】希望找到方向
        【五、多層次因素分析】根據 Super 理論 [1]，案主處於建立期。
        【六、個案優勢與資源】積極求助
        【七、諮詢師的專業判斷】基於理論 [2]，問題源於...
        【八、諮商目標與介入策略】採用卡片排序 [3]，因為...
        【九、預期成效與評估】3個月內完成
        【十、諮詢師自我反思】本次順利
        """

        report = {
            "client_name": "小美",
            "conceptualization": report_text
        }

        summary = generate_quality_summary(report, report_text, sample_theories)

        # 應包含所有關鍵指標
        assert "structure_quality" in summary
        assert "citation_quality" in summary
        assert "overall_score" in summary
        assert "grade" in summary

        # 結構應該完整
        assert summary["structure_quality"]["completeness"] == 100.0

        # 應該有評分等級
        assert summary["grade"] in ["優秀", "良好", "及格", "需改進"]

    def test_incomplete_report_detection(self):
        """測試不完整報告偵測"""
        incomplete_report = """
        【一、案主基本資料】姓名：小美
        【二、主訴問題】職涯迷茫
        【五、多層次因素分析】年齡 28 歲 [1]
        """

        structure = validate_report_structure(incomplete_report)
        citation = validate_citations(incomplete_report)

        # 應偵測到缺少段落
        assert structure["complete"] is False
        assert len(structure["missing_sections"]) == 7  # 缺少 3,4,6,7,8,9,10

        # 應偵測到引用不足
        assert citation["all_critical_sections_cited"] is False

        # 品質分數應該偏低
        score = calculate_quality_score(structure, citation)
        assert score < 60.0  # 不及格

    def test_citation_without_rationale_detection(self):
        """測試檢測缺乏理由的引用（M2.2 關鍵功能）"""
        report_with_weak_citations = """
        【五、多層次因素分析】
        案主年齡 28 歲 [1]。性格內向 [2]。

        【七、諮詢師的專業判斷】
        問題複雜 [3][4]。

        【八、諮商目標與介入策略】
        使用技術 [5][6]。
        """

        citation = validate_citations(report_with_weak_citations)

        # 雖然有引用，但缺乏說明理由
        assert citation["total_citations"] == 6
        assert citation["has_rationale"] is False  # 關鍵：沒有「根據」「基於」等理由詞

    def test_rationale_keywords_detection(self):
        """測試理由關鍵詞偵測（M2.2）"""
        report_with_rationale = """
        【五、多層次因素分析】
        根據 Super 生涯發展理論 [1]，案主 28 歲處於建立期，此階段應開始職場立足。
        基於個案陳述 [2]，可見其缺乏明確目標。

        【七、諮詢師的專業判斷】
        從自我效能理論觀點 [3]，案主過往成功經驗不足導致信心低落。

        【八、諮商目標與介入策略】
        考量案主處於價值觀探索階段 [4]，因此採用卡片排序法 [5]。
        """

        citation = validate_citations(report_with_rationale)

        # 應偵測到有理由說明
        assert citation["has_rationale"] is True


class TestParameterTuning:
    """參數調優測試"""

    def test_quality_score_thresholds(self):
        """測試品質分數門檻是否合理"""
        # 完美報告
        perfect_structure = {"coverage": 100.0, "complete": True, "missing_sections": []}
        perfect_citation = {
            "all_critical_sections_cited": True,
            "total_citations": 7,
            "has_rationale": True,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": True},
                "【八、諮商目標與介入策略】": {"has_citations": True}
            }
        }
        assert calculate_quality_score(perfect_structure, perfect_citation) == 100.0

        # 及格邊緣（60分）
        passing_structure = {"coverage": 80.0, "complete": False, "missing_sections": ["【十、諮詢師自我反思】", "【九、預期成效與評估】"]}
        passing_citation = {
            "all_critical_sections_cited": False,
            "total_citations": 3,
            "has_rationale": True,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": True},
                "【八、諮商目標與介入策略】": {"has_citations": False}
            }
        }
        score = calculate_quality_score(passing_structure, passing_citation)
        # 實際計算：80*0.4 + (2/3)*40 + 10 + (3/7)*10 = 32 + 26.7 + 10 + 4.3 = 73
        assert 70.0 <= score <= 75.0  # 良好等級（有理由加分）

    def test_citation_count_optimal_range(self):
        """測試最佳引用數量範圍（5-7個）"""
        base_structure = {"coverage": 100.0, "complete": True, "missing_sections": []}
        base_citation_template = {
            "all_critical_sections_cited": True,
            "has_rationale": True,
            "section_details": {
                "【五、多層次因素分析】": {"has_citations": True},
                "【七、諮詢師的專業判斷】": {"has_citations": True},
                "【八、諮商目標與介入策略】": {"has_citations": True}
            }
        }

        # 5個引用
        citation_5 = {**base_citation_template, "total_citations": 5}
        score_5 = calculate_quality_score(base_structure, citation_5)

        # 7個引用（理想）
        citation_7 = {**base_citation_template, "total_citations": 7}
        score_7 = calculate_quality_score(base_structure, citation_7)

        # 10個引用（過多，不加分）
        citation_10 = {**base_citation_template, "total_citations": 10}
        score_10 = calculate_quality_score(base_structure, citation_10)

        assert score_7 == 100.0
        assert score_5 >= 97.0  # 5個也很好
        assert score_10 == 100.0  # 超過7個不扣分，最多100
