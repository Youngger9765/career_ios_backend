"""API endpoints for RAG evaluation system"""

import hashlib
import math
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.evaluation import EvaluationExperiment
from app.services.evaluation_prompts_service import EvaluationPromptsService
from app.services.evaluation_recommendations_service import (
    EvaluationRecommendationsService,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/rag/evaluation", tags=["rag-evaluation"])


# Helper functions
def _safe_float(value: Optional[float]) -> Optional[float]:
    """Convert NaN to None for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _parse_experiment_id(experiment_id: str) -> uuid.UUID:
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


def _build_experiment_response(
    experiment: EvaluationExperiment
) -> "ExperimentResponse":
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
        avg_faithfulness=_safe_float(experiment.avg_faithfulness),
        avg_answer_relevancy=_safe_float(experiment.avg_answer_relevancy),
        avg_context_recall=_safe_float(experiment.avg_context_recall),
        avg_context_precision=_safe_float(experiment.avg_context_precision),
        avg_latency_ms=_safe_float(experiment.avg_latency_ms),
        mlflow_experiment_id=experiment.mlflow_experiment_id,
        mlflow_run_id=experiment.mlflow_run_id,
        created_at=experiment.created_at.isoformat() if experiment.created_at else None,
        updated_at=experiment.updated_at.isoformat() if experiment.updated_at else None,
    )


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


# Initialize evaluation service
eval_service = EvaluationService()


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    request: CreateExperimentRequest,
    db: Session = Depends(get_db),
):
    """Create a new evaluation experiment"""
    experiment = await eval_service.create_experiment(
        db=db,
        name=request.name,
        description=request.description,
        experiment_type=request.experiment_type,
        chunking_method=request.chunking_method,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        chunk_strategy=request.chunk_strategy,
        instruction_version=request.instruction_version,
        instruction_template=request.instruction_template,
        instruction_hash=request.instruction_hash,
        config=request.config,
    )
    return _build_experiment_response(experiment)


@router.post("/experiments/{experiment_id}/run", response_model=ExperimentResponse)
async def run_evaluation(
    experiment_id: str,
    request: RunEvaluationRequest,
    db: Session = Depends(get_db),
):
    """Run evaluation on an experiment with test cases"""
    exp_uuid = _parse_experiment_id(experiment_id)
    test_cases = [case.model_dump() for case in request.test_cases]

    try:
        experiment = await eval_service.run_evaluation(
            db=db,
            experiment_id=exp_uuid,
            test_cases=test_cases,
            include_ground_truth=request.include_ground_truth,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

    return _build_experiment_response(experiment)


@router.get("/experiments", response_model=list[ExperimentResponse])
async def list_experiments(
    limit: int = 50,
    offset: int = 0,
    experiment_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all experiments with optional filters"""
    experiments = await eval_service.list_experiments(
        db=db,
        limit=limit,
        offset=offset,
        experiment_type=experiment_type,
        status=status,
    )
    return [_build_experiment_response(exp) for exp in experiments]


@router.get("/experiments/matrix")
async def get_evaluation_matrix(
    db: Session = Depends(get_db),
):
    """Get evaluation matrix data for heatmap visualization"""
    from app.api.chunk_strategies import list_chunk_strategies
    from app.models.evaluation import EvaluationTestSet
    from app.services.evaluation_matrix import (
        format_experiments,
        format_prompts,
        format_testsets,
    )

    # Get all testsets
    testsets_db = (
        db.query(EvaluationTestSet).filter(EvaluationTestSet.is_active.is_(True)).all()
    )
    testsets = format_testsets(testsets_db)

    # Get all chunk strategies from API
    chunk_strategies = await list_chunk_strategies()

    # Get all prompt versions
    prompts_service = EvaluationPromptsService(db)
    prompts_list = prompts_service.list_prompt_versions()
    prompts = format_prompts(prompts_list)

    # Get all experiments
    experiments_db = db.query(EvaluationExperiment).all()
    experiments = format_experiments(experiments_db)

    return {
        "testsets": testsets,
        "prompts": prompts,
        "chunk_strategies": chunk_strategies,
        "experiments": experiments,
    }


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific experiment by ID"""
    exp_uuid = _parse_experiment_id(experiment_id)
    experiment = await eval_service.get_experiment(db=db, experiment_id=exp_uuid)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return _build_experiment_response(experiment)


@router.get("/experiments/{experiment_id}/results", response_model=list[ResultResponse])
async def get_experiment_results(
    experiment_id: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get detailed results for an experiment"""
    exp_uuid = _parse_experiment_id(experiment_id)
    results = await eval_service.get_experiment_results(
        db=db,
        experiment_id=exp_uuid,
        limit=limit,
        offset=offset,
    )

    return [
        ResultResponse(
            id=str(result.id),
            question=result.question,
            answer=result.answer,
            contexts=result.contexts,
            ground_truth=result.ground_truth,
            faithfulness=_safe_float(result.faithfulness),
            answer_relevancy=_safe_float(result.answer_relevancy),
            context_recall=_safe_float(result.context_recall),
            context_precision=_safe_float(result.context_precision),
            latency_ms=_safe_float(result.latency_ms),
        )
        for result in results
    ]


@router.post("/experiments/compare")
async def compare_experiments(
    request: CompareExperimentsRequest,
    db: Session = Depends(get_db),
):
    """Compare multiple experiments"""
    exp_uuids = [_parse_experiment_id(exp_id) for exp_id in request.experiment_ids]
    comparison = await eval_service.compare_experiments(db=db, experiment_ids=exp_uuids)
    return comparison


@router.post("/prompts")
async def create_prompt_version(
    prompt: PromptVersion,
    db: Session = Depends(get_db),
):
    """Create a new prompt version"""
    prompt_hash = hashlib.sha256(prompt.template.encode("utf-8")).hexdigest()

    return {
        "version": prompt.version,
        "template": prompt.template,
        "description": prompt.description,
        "hash": prompt_hash,
        "is_active": prompt.is_active,
        "created_at": datetime.now().isoformat(),
    }


@router.get("/prompts")
async def list_prompt_versions(
    db: Session = Depends(get_db),
):
    """List all prompt versions from experiments"""
    prompts_service = EvaluationPromptsService(db)
    return prompts_service.list_prompt_versions()


@router.get("/prompts/{version}/experiments")
async def get_experiments_by_prompt_version(
    version: str,
    db: Session = Depends(get_db),
):
    """Get all experiments using a specific prompt version"""
    prompts_service = EvaluationPromptsService(db)
    return prompts_service.get_experiments_by_prompt_version(version)


@router.delete("/prompts/{version}")
async def delete_prompt_version(
    version: str,
    force: bool = False,
    db: Session = Depends(get_db),
):
    """Delete a prompt version and optionally its experiments"""
    prompts_service = EvaluationPromptsService(db)
    return prompts_service.delete_prompt_version(version, force)


@router.get("/prompts/compare")
async def compare_prompt_versions(
    version1: str,
    version2: str,
    db: Session = Depends(get_db),
):
    """Compare two prompt versions with their templates and performance metrics"""
    prompts_service = EvaluationPromptsService(db)
    return prompts_service.compare_prompt_versions(version1, version2)


@router.get("/recommendations")
async def get_recommendations(db: Session = Depends(get_db)):
    """Get intelligent recommendations based on experiment results"""
    recommendations_service = EvaluationRecommendationsService(db)
    return recommendations_service.get_recommendations()
