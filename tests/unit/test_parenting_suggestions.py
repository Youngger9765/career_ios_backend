"""
Unit tests for parenting suggestions module

Tests the 200 expert parenting suggestions data file.
"""

import pytest

from app.config.parenting_suggestions import (
    ALL_SUGGESTIONS,
    GREEN_SUGGESTIONS,
    ORANGE_SUGGESTIONS,
    RED_SUGGESTIONS,
    STATS,
    get_suggestions_by_level,
    validate_suggestions,
)


class TestSuggestionsData:
    """Test the suggestions data integrity"""

    def test_green_suggestions_count(self):
        """綠色建議應該有 70 句"""
        assert (
            len(GREEN_SUGGESTIONS) == 70
        ), f"Expected 70 green suggestions, got {len(GREEN_SUGGESTIONS)}"

    def test_orange_suggestions_count(self):
        """橘色建議應該有 65 句"""
        assert (
            len(ORANGE_SUGGESTIONS) == 65
        ), f"Expected 65 orange suggestions, got {len(ORANGE_SUGGESTIONS)}"

    def test_red_suggestions_count(self):
        """紅色建議應該有 65 句"""
        assert (
            len(RED_SUGGESTIONS) == 65
        ), f"Expected 65 red suggestions, got {len(RED_SUGGESTIONS)}"

    def test_total_suggestions_count(self):
        """總建議數應該是 200 句"""
        total = len(GREEN_SUGGESTIONS) + len(ORANGE_SUGGESTIONS) + len(RED_SUGGESTIONS)
        assert total == 200, f"Expected 200 total suggestions, got {total}"

    def test_no_empty_suggestions(self):
        """所有建議都不應該是空字串"""
        all_suggestions = GREEN_SUGGESTIONS + ORANGE_SUGGESTIONS + RED_SUGGESTIONS
        for i, sug in enumerate(all_suggestions):
            assert sug.strip() != "", f"Suggestion at index {i} is empty"

    def test_no_duplicate_suggestions(self):
        """建議句不應該有重複"""
        all_suggestions = GREEN_SUGGESTIONS + ORANGE_SUGGESTIONS + RED_SUGGESTIONS
        unique_suggestions = set(all_suggestions)
        assert len(all_suggestions) == len(
            unique_suggestions
        ), "Found duplicate suggestions"

    def test_suggestions_are_strings(self):
        """所有建議都應該是字串"""
        all_suggestions = GREEN_SUGGESTIONS + ORANGE_SUGGESTIONS + RED_SUGGESTIONS
        for i, sug in enumerate(all_suggestions):
            assert isinstance(
                sug, str
            ), f"Suggestion at index {i} is not a string: {type(sug)}"


class TestAllSuggestions:
    """Test the ALL_SUGGESTIONS dictionary"""

    def test_all_suggestions_structure(self):
        """ALL_SUGGESTIONS 應該包含三個 key"""
        assert "green" in ALL_SUGGESTIONS
        assert "orange" in ALL_SUGGESTIONS
        assert "red" in ALL_SUGGESTIONS
        assert len(ALL_SUGGESTIONS) == 3

    def test_all_suggestions_values(self):
        """ALL_SUGGESTIONS 的值應該等於各個建議列表"""
        assert ALL_SUGGESTIONS["green"] == GREEN_SUGGESTIONS
        assert ALL_SUGGESTIONS["orange"] == ORANGE_SUGGESTIONS
        assert ALL_SUGGESTIONS["red"] == RED_SUGGESTIONS


class TestStats:
    """Test the STATS dictionary"""

    def test_stats_structure(self):
        """STATS 應該包含正確的 key"""
        assert "total" in STATS
        assert "green" in STATS
        assert "orange" in STATS
        assert "red" in STATS

    def test_stats_values(self):
        """STATS 的值應該正確"""
        assert STATS["total"] == 200
        assert STATS["green"] == 70
        assert STATS["orange"] == 65
        assert STATS["red"] == 65


class TestGetSuggestionsByLevel:
    """Test the get_suggestions_by_level function"""

    def test_get_green_suggestions(self):
        """取得綠色建議"""
        suggestions = get_suggestions_by_level("green")
        assert suggestions == GREEN_SUGGESTIONS
        assert len(suggestions) == 70

    def test_get_orange_suggestions(self):
        """取得橘色建議"""
        suggestions = get_suggestions_by_level("orange")
        assert suggestions == ORANGE_SUGGESTIONS
        assert len(suggestions) == 65

    def test_get_red_suggestions(self):
        """取得紅色建議"""
        suggestions = get_suggestions_by_level("red")
        assert suggestions == RED_SUGGESTIONS
        assert len(suggestions) == 65

    def test_get_suggestions_case_insensitive(self):
        """應該不區分大小寫"""
        assert get_suggestions_by_level("GREEN") == GREEN_SUGGESTIONS
        assert get_suggestions_by_level("Green") == GREEN_SUGGESTIONS
        assert get_suggestions_by_level("ORANGE") == ORANGE_SUGGESTIONS
        assert get_suggestions_by_level("RED") == RED_SUGGESTIONS

    def test_get_suggestions_invalid_level(self):
        """無效的等級應該回傳空列表"""
        suggestions = get_suggestions_by_level("invalid")
        assert suggestions == []

    def test_get_suggestions_empty_level(self):
        """空字串應該回傳空列表"""
        suggestions = get_suggestions_by_level("")
        assert suggestions == []


class TestValidateSuggestions:
    """Test the validate_suggestions function"""

    def test_validate_returns_dict(self):
        """驗證函數應該回傳 dict"""
        result = validate_suggestions()
        assert isinstance(result, dict)

    def test_validate_has_required_keys(self):
        """驗證結果應該包含必要的 key"""
        result = validate_suggestions()
        assert "valid" in result
        assert "errors" in result
        assert "stats" in result

    def test_validate_valid_is_bool(self):
        """valid 應該是 bool"""
        result = validate_suggestions()
        assert isinstance(result["valid"], bool)

    def test_validate_errors_is_list(self):
        """errors 應該是 list"""
        result = validate_suggestions()
        assert isinstance(result["errors"], list)

    def test_validate_stats_is_dict(self):
        """stats 應該是 dict"""
        result = validate_suggestions()
        assert isinstance(result["stats"], dict)

    def test_validate_passes(self):
        """當前的建議集應該通過驗證"""
        result = validate_suggestions()
        assert result["valid"] is True, f"Validation failed: {result['errors']}"
        assert len(result["errors"]) == 0, f"Expected no errors, got {result['errors']}"

    def test_validate_stats_correct(self):
        """驗證結果的 stats 應該正確"""
        result = validate_suggestions()
        assert result["stats"]["total"] == 200
        assert result["stats"]["green"] == 70
        assert result["stats"]["orange"] == 65
        assert result["stats"]["red"] == 65


class TestSuggestionsContent:
    """Test the content quality of suggestions"""

    def test_suggestions_not_too_long(self):
        """
        建議句不應該過長（雖然移除了字數限制，但仍應該簡潔）
        設定上限為 50 字，避免過長的建議
        """
        all_suggestions = GREEN_SUGGESTIONS + ORANGE_SUGGESTIONS + RED_SUGGESTIONS
        for i, sug in enumerate(all_suggestions):
            assert (
                len(sug) <= 50
            ), f"Suggestion at index {i} is too long ({len(sug)} chars): {sug}"

    def test_suggestions_meaningful(self):
        """建議句應該有意義（至少 4 個字）"""
        all_suggestions = GREEN_SUGGESTIONS + ORANGE_SUGGESTIONS + RED_SUGGESTIONS
        for i, sug in enumerate(all_suggestions):
            assert (
                len(sug) >= 4
            ), f"Suggestion at index {i} is too short ({len(sug)} chars): {sug}"

    def test_green_suggestions_positive(self):
        """綠色建議應該包含正向用語（抽樣檢查）"""
        # 抽樣檢查幾個綠色建議是否包含正向關鍵字
        positive_keywords = [
            "知道",
            "願意",
            "尊重",
            "理解",
            "陪",
            "安全",
            "信任",
            "支持",
        ]
        green_text = " ".join(GREEN_SUGGESTIONS)

        found_keywords = [kw for kw in positive_keywords if kw in green_text]
        assert (
            len(found_keywords) > 0
        ), "Green suggestions should contain positive keywords"

    def test_red_suggestions_warning(self):
        """紅色建議應該包含警告用語（抽樣檢查）"""
        # 抽樣檢查幾個紅色建議是否包含警告關鍵字
        warning_keywords = ["傷", "否定", "破壞", "危險", "立刻", "停", "警訊", "失去"]
        red_text = " ".join(RED_SUGGESTIONS)

        found_keywords = [kw for kw in warning_keywords if kw in red_text]
        assert (
            len(found_keywords) > 0
        ), "Red suggestions should contain warning keywords"


# Pytest configuration
@pytest.fixture(scope="module")
def all_suggestions_list():
    """Fixture: 提供所有建議的列表"""
    return GREEN_SUGGESTIONS + ORANGE_SUGGESTIONS + RED_SUGGESTIONS


@pytest.fixture(scope="module")
def suggestions_by_level():
    """Fixture: 提供按等級分類的建議"""
    return {
        "green": GREEN_SUGGESTIONS,
        "orange": ORANGE_SUGGESTIONS,
        "red": RED_SUGGESTIONS,
    }
