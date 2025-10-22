"""Helper functions for evaluation analysis and recommendations"""

import difflib
from typing import Any, Optional


def analyze_chunk_strategy_performance(
    experiments: list[Any],
) -> dict[str, dict[str, float]]:
    """Analyze performance metrics grouped by chunk strategy

    Args:
        experiments: List of experiment objects with chunk_strategy and metric attributes

    Returns:
        Dict mapping strategy names to aggregated performance metrics
    """
    strategy_performance = {}

    for exp in experiments:
        if not exp.chunk_strategy:
            continue

        if exp.chunk_strategy not in strategy_performance:
            strategy_performance[exp.chunk_strategy] = {
                "count": 0,
                "total_faithfulness": 0,
                "total_answer_relevancy": 0,
                "total_context_recall": 0,
                "total_context_precision": 0,
            }

        perf = strategy_performance[exp.chunk_strategy]
        perf["count"] += 1

        if exp.avg_faithfulness:
            perf["total_faithfulness"] += float(exp.avg_faithfulness)
        if exp.avg_answer_relevancy:
            perf["total_answer_relevancy"] += float(exp.avg_answer_relevancy)
        if exp.avg_context_recall:
            perf["total_context_recall"] += float(exp.avg_context_recall)
        if exp.avg_context_precision:
            perf["total_context_precision"] += float(exp.avg_context_precision)

    return strategy_performance


def find_best_chunk_strategy(
    strategy_performance: dict[str, dict[str, float]],
) -> tuple[Optional[str], float]:
    """Find the chunk strategy with the highest average score

    Args:
        strategy_performance: Dict from analyze_chunk_strategy_performance

    Returns:
        Tuple of (best_strategy_name, best_average_score)
    """
    best_strategy = None
    best_avg = 0

    for strategy, perf in strategy_performance.items():
        count = perf["count"]
        if count == 0:
            continue

        avg_score = (
            perf["total_faithfulness"] / count
            + perf["total_answer_relevancy"] / count
            + perf["total_context_recall"] / count
            + perf["total_context_precision"] / count
        ) / 4

        if avg_score > best_avg:
            best_avg = avg_score
            best_strategy = strategy

    return best_strategy, best_avg


def analyze_instruction_version_performance(
    experiments: list[Any],
) -> dict[str, dict[str, float]]:
    """Analyze performance metrics grouped by instruction version

    Args:
        experiments: List of experiment objects with instruction_version and metric attributes

    Returns:
        Dict mapping version names to aggregated performance metrics
    """
    version_performance = {}

    for exp in experiments:
        if not exp.instruction_version:
            continue

        if exp.instruction_version not in version_performance:
            version_performance[exp.instruction_version] = {
                "count": 0,
                "total_score": 0,
            }

        perf = version_performance[exp.instruction_version]
        perf["count"] += 1

        score_sum = 0
        score_count = 0
        if exp.avg_faithfulness:
            score_sum += float(exp.avg_faithfulness)
            score_count += 1
        if exp.avg_answer_relevancy:
            score_sum += float(exp.avg_answer_relevancy)
            score_count += 1

        if score_count > 0:
            perf["total_score"] += score_sum / score_count

    return version_performance


def find_best_instruction_version(
    version_performance: dict[str, dict[str, float]],
) -> tuple[Optional[str], float]:
    """Find the instruction version with the highest average score

    Args:
        version_performance: Dict from analyze_instruction_version_performance

    Returns:
        Tuple of (best_version_name, best_average_score)
    """
    best_version = None
    best_version_avg = 0

    for version, perf in version_performance.items():
        if perf["count"] == 0:
            continue
        avg = perf["total_score"] / perf["count"]
        if avg > best_version_avg:
            best_version_avg = avg
            best_version = version

    return best_version, best_version_avg


def find_low_performing_strategies(
    experiments: list[Any], threshold: float = 0.5
) -> list[str]:
    """Identify strategies with faithfulness scores below threshold

    Args:
        experiments: List of experiment objects
        threshold: Minimum acceptable faithfulness score

    Returns:
        List of unique strategy names that performed below threshold
    """
    low_performers = []

    for exp in experiments:
        if exp.avg_faithfulness and float(exp.avg_faithfulness) < threshold:
            low_performers.append(exp.chunk_strategy or "unknown")

    return list(set(low_performers))


def calculate_coverage_metrics(experiments: list[Any]) -> dict[str, int | float]:
    """Calculate test coverage metrics across strategies and test sets

    Args:
        experiments: List of experiment objects

    Returns:
        Dict with total_cells, completed_cells, and coverage_percent
    """
    strategies = set()
    test_sets = set()
    completed_cells = 0

    for exp in experiments:
        has_strategy = bool(exp.chunk_strategy)
        has_testset = hasattr(exp, "test_set_name") and bool(exp.test_set_name)

        if has_strategy:
            strategies.add(exp.chunk_strategy)
        if has_testset:
            test_sets.add(exp.test_set_name)

        # Only count experiments that have both strategy and testset
        if has_strategy and has_testset:
            completed_cells += 1

    total_cells = len(strategies) * len(test_sets) if strategies and test_sets else 0
    coverage_percent = (completed_cells / total_cells * 100) if total_cells > 0 else 0

    return {
        "total_cells": total_cells,
        "completed_cells": completed_cells,
        "coverage_percent": coverage_percent,
    }


def calculate_average_metrics(experiments: list[Any]) -> dict[str, Optional[float]]:
    """Calculate average metrics across multiple experiments

    Args:
        experiments: List of experiment objects with metric attributes

    Returns:
        Dict with average values for each metric (None if no data)
    """
    metrics = {
        "faithfulness": [],
        "answer_relevancy": [],
        "context_recall": [],
        "context_precision": [],
    }

    for exp in experiments:
        if exp.avg_faithfulness is not None:
            metrics["faithfulness"].append(float(exp.avg_faithfulness))
        if exp.avg_answer_relevancy is not None:
            metrics["answer_relevancy"].append(float(exp.avg_answer_relevancy))
        if exp.avg_context_recall is not None:
            metrics["context_recall"].append(float(exp.avg_context_recall))
        if exp.avg_context_precision is not None:
            metrics["context_precision"].append(float(exp.avg_context_precision))

    return {
        "avg_faithfulness": sum(metrics["faithfulness"]) / len(metrics["faithfulness"])
        if metrics["faithfulness"]
        else None,
        "avg_answer_relevancy": sum(metrics["answer_relevancy"])
        / len(metrics["answer_relevancy"])
        if metrics["answer_relevancy"]
        else None,
        "avg_context_recall": sum(metrics["context_recall"])
        / len(metrics["context_recall"])
        if metrics["context_recall"]
        else None,
        "avg_context_precision": sum(metrics["context_precision"])
        / len(metrics["context_precision"])
        if metrics["context_precision"]
        else None,
    }


def calculate_template_diff(
    template1: Optional[str], template2: Optional[str]
) -> list[str]:
    """Calculate unified diff between two templates

    Args:
        template1: First template string
        template2: Second template string

    Returns:
        List of diff lines in unified diff format
    """
    # Handle None values
    if template1 is None:
        template1 = ""
    if template2 is None:
        template2 = ""

    # If both are empty, no diff
    if not template1 and not template2:
        return []

    template1_lines = template1.splitlines()
    template2_lines = template2.splitlines()

    diff = list(difflib.unified_diff(template1_lines, template2_lines, lineterm=""))

    return diff
