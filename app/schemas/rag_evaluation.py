"""
RAG Evaluation Schemas
Request/response models and helper functions for RAG evaluation system
"""
import math
import uuid
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel


# Helper functions
def safe_float(value: Optional[float]) -> Optional[float]:
    """Convert NaN to None for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def parse_experiment_id(experiment_id: str) -> uuid.UUID:
    """Parse experiment ID string to UUID with error handling

    Args:
        experiment_id: UUID string

    Returns:
        Parsed UUID

    Raises:
        HTTPException: If UUID format is invalid
    """
    try:
        return uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")


# Pydantic models for request/response
class CreateExperimentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    experiment_type: str = "end_to_end"
    chunking_method: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunk_strategy: Optional[str] = None
    instruction_version: Optional[str] = None
    instruction_template: Optional[str] = None
    instruction_hash: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class TestCase(BaseModel):
    question: str
    answer: Optional[str] = ""
    contexts: Optional[list[str]] = []
    ground_truth: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class RunEvaluationRequest(BaseModel):
    test_cases: list[TestCase]
    include_ground_truth: bool = True


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    experiment_type: str
    chunking_method: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunk_strategy: Optional[str] = None
    instruction_version: Optional[str] = None
    instruction_template: Optional[str] = None
    instruction_hash: Optional[str] = None
    status: str
    total_queries: int = 0
    avg_faithfulness: Optional[float] = None
    avg_answer_relevancy: Optional[float] = None
    avg_context_recall: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    mlflow_experiment_id: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ResultResponse(BaseModel):
    id: str
    question: str
    answer: str
    contexts: list[str]
    ground_truth: Optional[str]
    faithfulness: Optional[float]
    answer_relevancy: Optional[float]
    context_recall: Optional[float]
    context_precision: Optional[float]
    latency_ms: Optional[float]


class CompareExperimentsRequest(BaseModel):
    experiment_ids: list[str]


class PromptVersion(BaseModel):
    version: str
    template: str
    description: Optional[str] = None
    is_active: bool = True


def build_experiment_response(experiment) -> ExperimentResponse:
    """Build ExperimentResponse from database model

    Args:
        experiment: EvaluationExperiment model instance

    Returns:
        ExperimentResponse pydantic model
    """
    return ExperimentResponse(  # type: ignore[call-arg]
        id=str(experiment.id),
        name=experiment.name,
        description=experiment.description,
        experiment_type=experiment.experiment_type,
        chunking_method=experiment.chunking_method,
        chunk_size=experiment.chunk_size,
        chunk_overlap=experiment.chunk_overlap,
        chunk_strategy=experiment.chunk_strategy,
        instruction_version=experiment.instruction_version,
        instruction_template=experiment.instruction_template,
        instruction_hash=experiment.instruction_hash,
        status=experiment.status,
        total_queries=experiment.total_queries or 0,
        avg_faithfulness=safe_float(experiment.avg_faithfulness),
        avg_answer_relevancy=safe_float(experiment.avg_answer_relevancy),
        avg_context_recall=safe_float(experiment.avg_context_recall),
        avg_context_precision=safe_float(experiment.avg_context_precision),
        avg_latency_ms=safe_float(experiment.avg_latency_ms),
        mlflow_experiment_id=experiment.mlflow_experiment_id,
        mlflow_run_id=experiment.mlflow_run_id,
        created_at=experiment.created_at.isoformat() if experiment.created_at else None,
        updated_at=experiment.updated_at.isoformat() if experiment.updated_at else None,
    )
