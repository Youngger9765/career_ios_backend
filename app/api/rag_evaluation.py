"""API endpoints for RAG evaluation system"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/rag/evaluation", tags=["rag-evaluation"])


# Pydantic models for request/response
class CreateExperimentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    experiment_type: str = "end_to_end"
    chunking_method: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    config: Optional[dict[str, Any]] = None


class TestCase(BaseModel):
    question: str
    answer: Optional[str] = ""  # Make answer optional with empty string default
    contexts: Optional[list[str]] = []  # Make contexts optional with empty list default
    ground_truth: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class RunEvaluationRequest(BaseModel):
    test_cases: list[TestCase]
    include_ground_truth: bool = False


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    experiment_type: str
    chunking_method: Optional[str]
    chunk_size: Optional[int]
    chunk_overlap: Optional[int]
    status: str
    total_queries: int
    avg_faithfulness: Optional[float]
    avg_answer_relevancy: Optional[float]
    avg_context_recall: Optional[float]
    avg_context_precision: Optional[float]
    avg_latency_ms: Optional[float]
    mlflow_experiment_id: Optional[str]
    mlflow_run_id: Optional[str]
    created_at: str
    updated_at: Optional[str]


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
        config=request.config,
    )

    return ExperimentResponse(
        id=str(experiment.id),
        name=experiment.name,
        description=experiment.description,
        experiment_type=experiment.experiment_type,
        chunking_method=experiment.chunking_method,
        chunk_size=experiment.chunk_size,
        chunk_overlap=experiment.chunk_overlap,
        status=experiment.status,
        total_queries=experiment.total_queries or 0,
        avg_faithfulness=experiment.avg_faithfulness,
        avg_answer_relevancy=experiment.avg_answer_relevancy,
        avg_context_recall=experiment.avg_context_recall,
        avg_context_precision=experiment.avg_context_precision,
        avg_latency_ms=experiment.avg_latency_ms,
        mlflow_experiment_id=experiment.mlflow_experiment_id,
        mlflow_run_id=experiment.mlflow_run_id,
        created_at=experiment.created_at.isoformat() if experiment.created_at else None,
        updated_at=experiment.updated_at.isoformat() if experiment.updated_at else None,
    )


@router.post("/experiments/{experiment_id}/run", response_model=ExperimentResponse)
async def run_evaluation(
    experiment_id: str,
    request: RunEvaluationRequest,
    db: Session = Depends(get_db),
):
    """Run evaluation on an experiment with test cases"""
    try:
        exp_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")

    # Convert Pydantic models to dicts
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

    return ExperimentResponse(
        id=str(experiment.id),
        name=experiment.name,
        description=experiment.description,
        experiment_type=experiment.experiment_type,
        chunking_method=experiment.chunking_method,
        chunk_size=experiment.chunk_size,
        chunk_overlap=experiment.chunk_overlap,
        status=experiment.status,
        total_queries=experiment.total_queries or 0,
        avg_faithfulness=experiment.avg_faithfulness,
        avg_answer_relevancy=experiment.avg_answer_relevancy,
        avg_context_recall=experiment.avg_context_recall,
        avg_context_precision=experiment.avg_context_precision,
        avg_latency_ms=experiment.avg_latency_ms,
        mlflow_experiment_id=experiment.mlflow_experiment_id,
        mlflow_run_id=experiment.mlflow_run_id,
        created_at=experiment.created_at.isoformat() if experiment.created_at else None,
        updated_at=experiment.updated_at.isoformat() if experiment.updated_at else None,
    )


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

    return [
        ExperimentResponse(
            id=str(exp.id),
            name=exp.name,
            description=exp.description,
            experiment_type=exp.experiment_type,
            chunking_method=exp.chunking_method,
            chunk_size=exp.chunk_size,
            chunk_overlap=exp.chunk_overlap,
            status=exp.status,
            total_queries=exp.total_queries or 0,
            avg_faithfulness=exp.avg_faithfulness,
            avg_answer_relevancy=exp.avg_answer_relevancy,
            avg_context_recall=exp.avg_context_recall,
            avg_context_precision=exp.avg_context_precision,
            avg_latency_ms=exp.avg_latency_ms,
            mlflow_run_id=exp.mlflow_run_id,
            created_at=exp.created_at.isoformat() if exp.created_at else None,
            updated_at=exp.updated_at.isoformat() if exp.updated_at else None,
        )
        for exp in experiments
    ]


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific experiment by ID"""
    try:
        exp_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")

    experiment = await eval_service.get_experiment(db=db, experiment_id=exp_uuid)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return ExperimentResponse(
        id=str(experiment.id),
        name=experiment.name,
        description=experiment.description,
        experiment_type=experiment.experiment_type,
        chunking_method=experiment.chunking_method,
        chunk_size=experiment.chunk_size,
        chunk_overlap=experiment.chunk_overlap,
        status=experiment.status,
        total_queries=experiment.total_queries or 0,
        avg_faithfulness=experiment.avg_faithfulness,
        avg_answer_relevancy=experiment.avg_answer_relevancy,
        avg_context_recall=experiment.avg_context_recall,
        avg_context_precision=experiment.avg_context_precision,
        avg_latency_ms=experiment.avg_latency_ms,
        mlflow_experiment_id=experiment.mlflow_experiment_id,
        mlflow_run_id=experiment.mlflow_run_id,
        created_at=experiment.created_at.isoformat() if experiment.created_at else None,
        updated_at=experiment.updated_at.isoformat() if experiment.updated_at else None,
    )


@router.get("/experiments/{experiment_id}/results", response_model=list[ResultResponse])
async def get_experiment_results(
    experiment_id: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get detailed results for an experiment"""
    try:
        exp_uuid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")

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
            faithfulness=result.faithfulness,
            answer_relevancy=result.answer_relevancy,
            context_recall=result.context_recall,
            context_precision=result.context_precision,
            latency_ms=result.latency_ms,
        )
        for result in results
    ]


class CompareExperimentsRequest(BaseModel):
    experiment_ids: list[str]


@router.post("/experiments/compare")
async def compare_experiments(
    request: CompareExperimentsRequest,
    db: Session = Depends(get_db),
):
    """Compare multiple experiments"""
    try:
        exp_uuids = [uuid.UUID(exp_id) for exp_id in request.experiment_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")

    comparison = await eval_service.compare_experiments(db=db, experiment_ids=exp_uuids)

    return comparison
