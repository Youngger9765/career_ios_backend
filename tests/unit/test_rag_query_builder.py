"""Unit tests for RAG query builder improvements (M2.1)"""

from app.utils.rag_query_builder import (
    build_enhanced_query,
    extract_career_stage,
    extract_key_demographics,
)


class TestExtractKeyDemographics:
    """測試人口統計資料提取"""

    def test_extract_age_gender_education(self):
        """測試提取年齡、性別、教育程度"""
        parsed_data = {
            "age": 28,
            "gender": "女性",
            "education": "碩士",
            "main_concerns": ["職涯迷茫", "工作倦怠"],
        }

        result = extract_key_demographics(parsed_data)

        assert "28歲" in result
        assert "女性" in result
        assert "碩士" in result

    def test_extract_with_missing_fields(self):
        """測試部分欄位缺失"""
        parsed_data = {"age": 25, "main_concerns": ["轉職"]}

        result = extract_key_demographics(parsed_data)

        assert "25歲" in result
        assert result != ""  # 即使部分缺失也要有結果


class TestExtractCareerStage:
    """測試生涯階段識別"""

    def test_identify_exploration_stage(self):
        """測試識別探索期（20-25歲）"""
        parsed_data = {"age": 23}

        stage = extract_career_stage(parsed_data)

        assert "探索期" in stage or "試探階段" in stage

    def test_identify_establishment_stage(self):
        """測試識別建立期（25-44歲）"""
        parsed_data = {"age": 30}

        stage = extract_career_stage(parsed_data)

        assert "建立期" in stage or "立足階段" in stage

    def test_identify_maintenance_stage(self):
        """測試識別維持期（45-64歲）"""
        parsed_data = {"age": 50}

        stage = extract_career_stage(parsed_data)

        assert "維持期" in stage or "穩固階段" in stage

    def test_with_concerns_context(self):
        """測試結合主訴問題判斷"""
        parsed_data = {"age": 28, "main_concerns": ["職涯轉換", "探索新方向"]}

        stage = extract_career_stage(parsed_data)

        # 即使年齡在建立期，主訴若是探索性質也應反映
        assert stage != ""


class TestBuildEnhancedQuery:
    """測試增強版 RAG 查詢構建"""

    def test_basic_query_construction(self):
        """測試基本查詢構建"""
        parsed_data = {
            "age": 28,
            "gender": "女性",
            "main_concerns": ["職涯迷茫", "缺乏方向"],
            "counselor_techniques": [],
        }

        query = build_enhanced_query(parsed_data)

        # 應包含人口統計資料
        assert "28" in query or "28歲" in query

        # 應包含主訴問題
        assert "職涯迷茫" in query or "迷茫" in query

        # 應比原始簡單拼接更豐富
        assert len(query) > 10

    def test_query_with_techniques(self):
        """測試包含技巧的查詢"""
        parsed_data = {
            "age": 35,
            "main_concerns": ["工作倦怠"],
            "counselor_techniques": ["卡片排序", "生涯幻遊"],
        }

        query = build_enhanced_query(parsed_data)

        assert "卡片排序" in query
        assert "生涯幻遊" in query

    def test_query_prioritization(self):
        """測試查詢詞優先級排序"""
        parsed_data = {
            "age": 25,
            "main_concerns": ["議題A", "議題B", "議題C", "議題D", "議題E"],
            "counselor_techniques": ["技巧1", "技巧2", "技巧3"],
        }

        query = build_enhanced_query(parsed_data)

        # 應限制長度，只取前 3 個 concerns + 前 2 個 techniques
        words = query.split()

        # 查詢不應過長（避免噪音）
        assert len(words) <= 15

    def test_fallback_query(self):
        """測試空資料時的預設查詢"""
        parsed_data = {"main_concerns": [], "counselor_techniques": []}

        query = build_enhanced_query(parsed_data)

        # 應有預設值
        assert "職涯諮詢" in query or "生涯發展" in query
        assert query != ""

    def test_query_structure_quality(self):
        """測試查詢結構品質"""
        parsed_data = {
            "age": 30,
            "gender": "男性",
            "education": "大學",
            "main_concerns": ["轉職焦慮", "能力不足"],
            "counselor_techniques": ["敘事治療"],
        }

        query = build_enhanced_query(parsed_data)

        # 新查詢應該是結構化的，不只是簡單拼接
        # 測試：不應該只是空格分隔的詞彙列表
        assert query != "轉職焦慮 能力不足 敘事治療"

        # 應包含有意義的上下文
        assert len(query) >= 20


class TestQueryComparison:
    """對比測試：舊 vs 新查詢構建"""

    def test_old_vs_new_query_richness(self):
        """測試新舊查詢豐富度對比"""
        parsed_data = {
            "age": 28,
            "gender": "女性",
            "education": "碩士",
            "main_concerns": ["職涯迷茫", "工作倦怠"],
            "counselor_techniques": ["卡片排序"],
        }

        # 舊版查詢（模擬原有邏輯）
        old_query = " ".join(
            parsed_data["main_concerns"][:3] + parsed_data["counselor_techniques"][:2]
        )

        # 新版查詢
        new_query = build_enhanced_query(parsed_data)

        # 新查詢應該更豐富
        assert len(new_query) > len(old_query)

        # 新查詢應該包含生涯階段或人口統計資訊
        assert "28" in new_query or "探索" in new_query or "建立" in new_query
