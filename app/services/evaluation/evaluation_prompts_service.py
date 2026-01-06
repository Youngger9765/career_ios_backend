"""Service layer for evaluation prompt version management"""

from collections import defaultdict
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationExperiment


class EvaluationPromptsService:
    """Service for managing evaluation prompt versions"""

    def __init__(self, db: Session):
        self.db = db

    def list_prompt_versions(self) -> list[dict[str, Any]]:
        """List all prompt versions from experiments

        Returns:
            List of prompt version metadata with usage statistics
        """
        # Get unique instruction versions from experiments
        experiments = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.instruction_version.isnot(None))
            .all()
        )

        # Group by version
        versions: dict[str, dict[str, object]] = defaultdict(
            lambda: {
                "version": None,
                "template": None,
                "hash": None,
                "experiments_count": 0,
                "first_used": None,
                "last_used": None,
            }
        )

        for exp in experiments:
            version = str(exp.instruction_version)
            if version not in versions or versions[version]["version"] is None:
                versions[version]["version"] = exp.instruction_version
                versions[version]["template"] = exp.instruction_template
                versions[version]["hash"] = exp.instruction_hash
                versions[version]["first_used"] = (
                    exp.created_at.isoformat() if exp.created_at else None
                )

            versions[version]["experiments_count"] += 1  # type: ignore[operator]
            if exp.created_at:
                last_used = exp.created_at.isoformat()
                if (
                    not versions[version]["last_used"]
                    or last_used > versions[version]["last_used"]
                ):
                    versions[version]["last_used"] = last_used

        return list(versions.values())

    def get_experiments_by_prompt_version(self, version: str) -> list[dict[str, Any]]:
        """Get all experiments using a specific prompt version

        Args:
            version: Prompt version identifier

        Returns:
            List of experiments using this prompt version
        """
        experiments = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.instruction_version == version)
            .all()
        )

        return [
            {
                "id": str(exp.id),
                "name": exp.name,
                "chunk_strategy": exp.chunk_strategy,
                "status": exp.status,
                "avg_faithfulness": self._safe_float(exp.avg_faithfulness),
                "avg_answer_relevancy": self._safe_float(exp.avg_answer_relevancy),
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
            }
            for exp in experiments
        ]

    def delete_prompt_version(
        self, version: str, force: bool = False
    ) -> dict[str, Any]:
        """Delete a prompt version and optionally its experiments

        Args:
            version: Prompt version identifier
            force: If True, delete all related experiments

        Returns:
            Deletion result with success message

        Raises:
            HTTPException: If prompt is in use and force=False
        """
        # Get all experiments using this version
        experiments = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.instruction_version == version)
            .all()
        )

        experiments_count = len(experiments)

        if experiments_count > 0:
            if not force:
                raise HTTPException(
                    status_code=400,
                    detail=f"無法刪除：此 Prompt 版本被 {experiments_count} 個實驗使用中。如要刪除所有相關實驗，請使用 force=true",
                )

            # Delete all related experiments
            for exp in experiments:
                self.db.delete(exp)

            self.db.commit()

            return {
                "success": True,
                "message": f"Prompt 版本 {version} 及其 {experiments_count} 個實驗已刪除",
            }

        # No experiments using this version
        return {"success": True, "message": f"Prompt 版本 {version} 未被使用，已移除"}

    def compare_prompt_versions(self, version1: str, version2: str) -> dict[str, Any]:
        """Compare two prompt versions with templates and performance metrics

        Args:
            version1: First prompt version
            version2: Second prompt version

        Returns:
            Comparison data with metrics and template diff

        Raises:
            HTTPException: If either version not found
        """
        from app.services.evaluation.evaluation_analysis import (
            calculate_average_metrics,
            calculate_template_diff,
        )

        # Get experiments for both versions
        exp1 = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.instruction_version == version1)
            .first()
        )

        exp2 = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.instruction_version == version2)
            .first()
        )

        if not exp1:
            raise HTTPException(status_code=404, detail=f"Version {version1} not found")
        if not exp2:
            raise HTTPException(status_code=404, detail=f"Version {version2} not found")

        # Get all experiments for each version
        all_exp1 = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.instruction_version == version1)
            .all()
        )

        all_exp2 = (
            self.db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.instruction_version == version2)
            .all()
        )

        # Calculate metrics and diff
        metrics1 = calculate_average_metrics(all_exp1)
        metrics2 = calculate_average_metrics(all_exp2)
        diff = calculate_template_diff(
            exp1.instruction_template, exp2.instruction_template
        )

        return {
            "version1": {
                "version": version1,
                "template": exp1.instruction_template,
                "hash": exp1.instruction_hash,
                "experiments_count": len(all_exp1),
                "metrics": metrics1,
            },
            "version2": {
                "version": version2,
                "template": exp2.instruction_template,
                "hash": exp2.instruction_hash,
                "experiments_count": len(all_exp2),
                "metrics": metrics2,
            },
            "diff": diff,
            "template_identical": exp1.instruction_hash == exp2.instruction_hash,
        }

    @staticmethod
    def _safe_float(value: Optional[float]) -> Optional[float]:
        """Convert NaN to None for JSON serialization"""
        if value is None:
            return None
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
        return value
