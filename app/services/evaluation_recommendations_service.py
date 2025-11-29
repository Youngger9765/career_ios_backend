"""Service layer for evaluation recommendations and insights"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationExperiment


class EvaluationRecommendationsService:
    """Service for generating intelligent recommendations from evaluation results"""

    def __init__(self, db: Session):
        self.db = db

    def get_recommendations(self) -> dict[str, Any]:
        """Get intelligent recommendations based on experiment results

        Returns:
            Dictionary with recommendations, summary, and statistics
        """
        from app.services.evaluation_analysis import (
            analyze_chunk_strategy_performance,
            analyze_instruction_version_performance,
            calculate_coverage_metrics,
            find_best_chunk_strategy,
            find_best_instruction_version,
            find_low_performing_strategies,
        )

        experiments = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.status == "completed")
            .all()
        )

        if not experiments:
            return {
                "recommendations": [],
                "summary": "尚無實驗數據，建議先執行評估實驗。",
            }

        recommendations = []

        # Analyze chunk strategies
        strategy_performance = analyze_chunk_strategy_performance(experiments)
        best_strategy, best_avg = find_best_chunk_strategy(strategy_performance)

        if best_strategy:
            recommendations.append(
                {
                    "type": "best_chunk_strategy",
                    "priority": "high",
                    "title": f"推薦使用 {best_strategy} 切分策略",
                    "description": f"基於 {strategy_performance[best_strategy]['count']} 個實驗的數據，此策略平均分數最高 ({best_avg:.3f})",
                    "action": f"在新實驗中使用 chunk_strategy='{best_strategy}'",
                    "impact": "high",
                }
            )

        # Analyze instruction versions
        version_performance = analyze_instruction_version_performance(experiments)
        best_version, best_version_avg = find_best_instruction_version(
            version_performance
        )

        if best_version:
            recommendations.append(
                {
                    "type": "best_prompt_version",
                    "priority": "high",
                    "title": f"推薦使用 Prompt {best_version}",
                    "description": f"基於 {version_performance[best_version]['count']} 個實驗，此版本平均效果最佳",
                    "action": f"使用 instruction_version='{best_version}'",
                    "impact": "medium",
                }
            )

        # Check for low-performing areas
        low_performers = find_low_performing_strategies(experiments, threshold=0.5)

        if low_performers:
            recommendations.append(
                {
                    "type": "avoid_strategy",
                    "priority": "medium",
                    "title": "避免使用低效策略",
                    "description": f"以下策略表現較差: {', '.join(low_performers)}",
                    "action": "考慮更換不同的 chunk 參數組合",
                    "impact": "medium",
                }
            )

        # Check coverage
        coverage_metrics = calculate_coverage_metrics(experiments)

        if (
            coverage_metrics["coverage_percent"] < 50
            and coverage_metrics["total_cells"] > 0
        ):
            recommendations.append(
                {
                    "type": "increase_coverage",
                    "priority": "low",
                    "title": "增加測試覆蓋率",
                    "description": f"目前評估矩陣覆蓋率僅 {coverage_metrics['coverage_percent']:.1f}%",
                    "action": "執行更多策略與測試集的組合實驗",
                    "impact": "low",
                }
            )

        # Summary
        summary = (
            f"分析了 {len(experiments)} 個實驗，生成了 {len(recommendations)} 個建議"
        )

        return {
            "recommendations": recommendations,
            "summary": summary,
            "stats": {
                "total_experiments": len(experiments),
                "unique_strategies": len(strategy_performance),
                "unique_prompt_versions": len(version_performance),
                "best_strategy": best_strategy,
                "best_prompt_version": best_version,
            },
        }
