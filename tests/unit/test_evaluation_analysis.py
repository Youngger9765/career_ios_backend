"""Tests for evaluation analysis helper functions"""

from app.services.evaluation.evaluation_analysis import (
    analyze_chunk_strategy_performance,
    calculate_average_metrics,
    calculate_coverage_metrics,
    calculate_template_diff,
    find_best_chunk_strategy,
    find_low_performing_strategies,
)


class TestAnalyzeChunkStrategyPerformance:
    """Tests for chunk strategy performance analysis"""

    def test_empty_experiments(self):
        """Should return empty dict for no experiments"""
        result = analyze_chunk_strategy_performance([])
        assert result == {}

    def test_single_experiment_with_all_metrics(self):
        """Should calculate performance for single experiment"""
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "chunk_strategy": "recursive",
                    "avg_faithfulness": 0.8,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": 0.7,
                    "avg_context_precision": 0.85,
                },
            )()
        ]

        result = analyze_chunk_strategy_performance(experiments)

        assert "recursive" in result
        assert result["recursive"]["count"] == 1
        assert result["recursive"]["total_faithfulness"] == 0.8
        assert result["recursive"]["total_answer_relevancy"] == 0.9

    def test_multiple_experiments_same_strategy(self):
        """Should aggregate metrics for multiple experiments with same strategy"""
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "chunk_strategy": "recursive",
                    "avg_faithfulness": 0.8,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": 0.7,
                    "avg_context_precision": 0.85,
                },
            )(),
            type(
                "obj",
                (object,),
                {
                    "chunk_strategy": "recursive",
                    "avg_faithfulness": 0.6,
                    "avg_answer_relevancy": 0.7,
                    "avg_context_recall": 0.5,
                    "avg_context_precision": 0.65,
                },
            )(),
        ]

        result = analyze_chunk_strategy_performance(experiments)

        assert result["recursive"]["count"] == 2
        assert result["recursive"]["total_faithfulness"] == 1.4
        assert result["recursive"]["total_answer_relevancy"] == 1.6

    def test_experiments_with_none_values(self):
        """Should handle None metric values gracefully"""
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "chunk_strategy": "recursive",
                    "avg_faithfulness": None,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": None,
                    "avg_context_precision": 0.85,
                },
            )()
        ]

        result = analyze_chunk_strategy_performance(experiments)

        assert result["recursive"]["total_faithfulness"] == 0
        assert result["recursive"]["total_answer_relevancy"] == 0.9

    def test_experiments_without_chunk_strategy(self):
        """Should skip experiments without chunk_strategy"""
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "chunk_strategy": None,
                    "avg_faithfulness": 0.8,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": 0.7,
                    "avg_context_precision": 0.85,
                },
            )()
        ]

        result = analyze_chunk_strategy_performance(experiments)
        assert result == {}


class TestFindBestChunkStrategy:
    """Tests for finding best chunk strategy"""

    def test_empty_performance_dict(self):
        """Should return None for empty performance dict"""
        result = find_best_chunk_strategy({})
        assert result == (None, 0)

    def test_single_strategy(self):
        """Should return the only strategy"""
        performance = {
            "recursive": {
                "count": 2,
                "total_faithfulness": 1.6,
                "total_answer_relevancy": 1.8,
                "total_context_recall": 1.4,
                "total_context_precision": 1.7,
            }
        }

        strategy, score = find_best_chunk_strategy(performance)

        assert strategy == "recursive"
        assert score > 0

    def test_multiple_strategies_different_scores(self):
        """Should return strategy with highest average score"""
        performance = {
            "recursive": {
                "count": 2,
                "total_faithfulness": 1.6,
                "total_answer_relevancy": 1.8,
                "total_context_recall": 1.4,
                "total_context_precision": 1.7,
            },
            "semantic": {
                "count": 2,
                "total_faithfulness": 1.8,
                "total_answer_relevancy": 1.9,
                "total_context_recall": 1.6,
                "total_context_precision": 1.8,
            },
        }

        strategy, score = find_best_chunk_strategy(performance)

        assert strategy == "semantic"


class TestCalculateAverageMetrics:
    """Tests for calculate_average_metrics function"""

    def test_empty_experiments(self):
        """Should return all None for empty list"""
        result = calculate_average_metrics([])

        assert result["avg_faithfulness"] is None
        assert result["avg_answer_relevancy"] is None
        assert result["avg_context_recall"] is None
        assert result["avg_context_precision"] is None

    def test_single_experiment_all_metrics(self):
        """Should calculate averages for single experiment"""
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "avg_faithfulness": 0.8,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": 0.7,
                    "avg_context_precision": 0.85,
                },
            )()
        ]

        result = calculate_average_metrics(experiments)

        assert result["avg_faithfulness"] == 0.8
        assert result["avg_answer_relevancy"] == 0.9

    def test_multiple_experiments(self):
        """Should calculate correct averages for multiple experiments"""
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "avg_faithfulness": 0.8,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": 0.7,
                    "avg_context_precision": 0.85,
                },
            )(),
            type(
                "obj",
                (object,),
                {
                    "avg_faithfulness": 0.6,
                    "avg_answer_relevancy": 0.7,
                    "avg_context_recall": 0.5,
                    "avg_context_precision": 0.65,
                },
            )(),
        ]

        result = calculate_average_metrics(experiments)

        assert result["avg_faithfulness"] == 0.7
        assert result["avg_answer_relevancy"] == 0.8

    def test_experiments_with_none_values(self):
        """Should skip None values when calculating averages"""
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "avg_faithfulness": 0.8,
                    "avg_answer_relevancy": None,
                    "avg_context_recall": 0.7,
                    "avg_context_precision": None,
                },
            )(),
            type(
                "obj",
                (object,),
                {
                    "avg_faithfulness": None,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": None,
                    "avg_context_precision": 0.85,
                },
            )(),
        ]

        result = calculate_average_metrics(experiments)

        assert result["avg_faithfulness"] == 0.8
        assert result["avg_answer_relevancy"] == 0.9
        assert result["avg_context_recall"] == 0.7
        assert result["avg_context_precision"] == 0.85


class TestFindLowPerformingStrategies:
    """Tests for finding low-performing strategies"""

    def test_empty_experiments(self):
        """Should return empty list for no experiments"""
        result = find_low_performing_strategies([])
        assert result == []

    def test_no_low_performers(self):
        """Should return empty list when all strategies perform well"""
        experiments = [
            type(
                "obj",
                (object,),
                {"chunk_strategy": "recursive", "avg_faithfulness": 0.8},
            )(),
            type(
                "obj",
                (object,),
                {"chunk_strategy": "semantic", "avg_faithfulness": 0.9},
            )(),
        ]

        result = find_low_performing_strategies(experiments, threshold=0.5)
        assert result == []

    def test_single_low_performer(self):
        """Should identify low-performing strategy"""
        experiments = [
            type(
                "obj",
                (object,),
                {"chunk_strategy": "recursive", "avg_faithfulness": 0.3},
            )()
        ]

        result = find_low_performing_strategies(experiments, threshold=0.5)
        assert "recursive" in result

    def test_multiple_low_performers_deduplication(self):
        """Should deduplicate low-performing strategies"""
        experiments = [
            type(
                "obj",
                (object,),
                {"chunk_strategy": "recursive", "avg_faithfulness": 0.3},
            )(),
            type(
                "obj",
                (object,),
                {"chunk_strategy": "recursive", "avg_faithfulness": 0.4},
            )(),
            type(
                "obj",
                (object,),
                {"chunk_strategy": "semantic", "avg_faithfulness": 0.2},
            )(),
        ]

        result = find_low_performing_strategies(experiments, threshold=0.5)
        assert len(result) == 2
        assert "recursive" in result
        assert "semantic" in result


class TestCalculateCoverageMetrics:
    """Tests for coverage metrics calculation"""

    def test_empty_experiments(self):
        """Should return 0 coverage for no experiments"""
        result = calculate_coverage_metrics([])

        assert result["total_cells"] == 0
        assert result["completed_cells"] == 0
        assert result["coverage_percent"] == 0

    def test_single_strategy_single_testset(self):
        """Should calculate correct coverage"""
        experiments = [
            type(
                "obj",
                (object,),
                {"chunk_strategy": "recursive", "test_set_name": "testset1"},
            )()
        ]

        result = calculate_coverage_metrics(experiments)

        assert result["total_cells"] == 1
        assert result["completed_cells"] == 1
        assert result["coverage_percent"] == 100.0

    def test_multiple_strategies_multiple_testsets(self):
        """Should calculate matrix coverage correctly"""
        experiments = [
            type(
                "obj",
                (object,),
                {"chunk_strategy": "recursive", "test_set_name": "testset1"},
            )(),
            type(
                "obj",
                (object,),
                {"chunk_strategy": "recursive", "test_set_name": "testset2"},
            )(),
            type(
                "obj",
                (object,),
                {"chunk_strategy": "semantic", "test_set_name": "testset1"},
            )(),
        ]

        result = calculate_coverage_metrics(experiments)

        # 2 strategies * 2 testsets = 4 total cells
        # 3 completed experiments
        assert result["total_cells"] == 4
        assert result["completed_cells"] == 3
        assert result["coverage_percent"] == 75.0

    def test_experiments_without_strategy_or_testset(self):
        """Should handle experiments without strategy or testset"""
        experiments = [
            type(
                "obj", (object,), {"chunk_strategy": "recursive", "test_set_name": None}
            )(),
            type(
                "obj", (object,), {"chunk_strategy": None, "test_set_name": "testset1"}
            )(),
        ]

        result = calculate_coverage_metrics(experiments)

        # Should collect strategies and testsets separately, but only count completed when both exist
        # 1 strategy * 1 testset = 1 total cell, but 0 completed (no experiment has both)
        assert result["total_cells"] == 1
        assert result["completed_cells"] == 0
        assert result["coverage_percent"] == 0


class TestCalculateTemplateDiff:
    """Tests for template diff calculation"""

    def test_identical_templates(self):
        """Should return empty diff for identical templates"""
        template1 = "Hello\nWorld"
        template2 = "Hello\nWorld"

        diff = calculate_template_diff(template1, template2)

        assert diff == []

    def test_different_templates(self):
        """Should return unified diff for different templates"""
        template1 = "Hello\nWorld"
        template2 = "Hello\nUniverse"

        diff = calculate_template_diff(template1, template2)

        # Should contain diff markers
        assert len(diff) > 0
        assert any("-World" in line for line in diff)
        assert any("+Universe" in line for line in diff)

    def test_empty_templates(self):
        """Should handle empty templates"""
        diff = calculate_template_diff("", "")
        assert diff == []

    def test_none_templates(self):
        """Should handle None templates gracefully"""
        diff = calculate_template_diff(None, None)
        assert diff == []

        diff = calculate_template_diff("Hello", None)
        assert len(diff) > 0

        diff = calculate_template_diff(None, "Hello")
        assert len(diff) > 0
