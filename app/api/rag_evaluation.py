"""API endpoints for RAG evaluation system"""

import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.evaluation import EvaluationExperiment
from app.schemas.rag_evaluation import (
    CompareExperimentsRequest,
    CreateExperimentRequest,
    ExperimentResponse,
    PromptVersion,
    ResultResponse,
    RunEvaluationRequest,
    build_experiment_response,
    parse_experiment_id,
    safe_float,
)
from app.services.evaluation.evaluation_prompts_service import EvaluationPromptsService
from app.services.evaluation.evaluation_recommendations_service import (
    EvaluationRecommendationsService,
)
from app.services.evaluation.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/rag/evaluation", tags=["rag-evaluation"])

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
    return build_experiment_response(experiment)


@router.post("/experiments/{experiment_id}/run", response_model=ExperimentResponse)
async def run_evaluation(
    experiment_id: str,
    request: RunEvaluationRequest,
    db: Session = Depends(get_db),
):
    """Run evaluation on an experiment with test cases"""
    exp_uuid = parse_experiment_id(experiment_id)
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

    return build_experiment_response(experiment)


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
    return [build_experiment_response(exp) for exp in experiments]


@router.get("/experiments/matrix")
async def get_evaluation_matrix(
    db: Session = Depends(get_db),
):
    """Get evaluation matrix data for heatmap visualization"""
    from app.api.chunk_strategies import list_chunk_strategies
    from app.models.evaluation import EvaluationTestSet
    from app.services.evaluation.evaluation_matrix import (
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
    exp_uuid = parse_experiment_id(experiment_id)
    experiment = await eval_service.get_experiment(db=db, experiment_id=exp_uuid)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return build_experiment_response(experiment)


@router.get("/experiments/{experiment_id}/results", response_model=list[ResultResponse])
async def get_experiment_results(
    experiment_id: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get detailed results for an experiment"""
    exp_uuid = parse_experiment_id(experiment_id)
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
            faithfulness=safe_float(result.faithfulness),
            answer_relevancy=safe_float(result.answer_relevancy),
            context_recall=safe_float(result.context_recall),
            context_precision=safe_float(result.context_precision),
            latency_ms=safe_float(result.latency_ms),
        )
        for result in results
    ]


@router.post("/experiments/compare")
async def compare_experiments(
    request: CompareExperimentsRequest,
    db: Session = Depends(get_db),
):
    """Compare multiple experiments"""
    exp_uuids = [parse_experiment_id(exp_id) for exp_id in request.experiment_ids]
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
