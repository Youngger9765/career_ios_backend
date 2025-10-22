"""API endpoints for RAG evaluation system"""

import math
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.evaluation import EvaluationExperiment
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/rag/evaluation", tags=["rag-evaluation"])


def safe_float(value: Optional[float]) -> Optional[float]:
    """Convert NaN to None for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


# Pydantic models for request/response
class CreateExperimentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    experiment_type: str = "end_to_end"
    chunking_method: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunk_strategy: Optional[str] = None  # NEW: strategy to use for evaluation
    instruction_version: Optional[str] = None  # NEW: instruction prompt version
    instruction_template: Optional[str] = None  # NEW: instruction prompt template
    instruction_hash: Optional[str] = None  # NEW: instruction prompt hash
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
    include_ground_truth: bool = True  # Changed default to True to enable all RAGAS metrics


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    experiment_type: str
    chunking_method: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunk_strategy: Optional[str] = None  # Allow None for backward compatibility
    instruction_version: Optional[str] = None  # NEW
    instruction_template: Optional[str] = None  # NEW
    instruction_hash: Optional[str] = None  # NEW
    status: str
    total_queries: int = 0
    avg_faithfulness: Optional[float] = None
    avg_answer_relevancy: Optional[float] = None
    avg_context_recall: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    mlflow_experiment_id: Optional[str] = None  # Allow None for backward compatibility
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
        chunk_strategy=request.chunk_strategy,  # NEW
        instruction_version=request.instruction_version,  # NEW
        instruction_template=request.instruction_template,  # NEW
        instruction_hash=request.instruction_hash,  # NEW
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
            chunk_strategy=exp.chunk_strategy,
            instruction_version=exp.instruction_version,
            instruction_template=exp.instruction_template,
            instruction_hash=exp.instruction_hash,
            status=exp.status,
            total_queries=exp.total_queries or 0,
            avg_faithfulness=safe_float(exp.avg_faithfulness),
            avg_answer_relevancy=safe_float(exp.avg_answer_relevancy),
            avg_context_recall=safe_float(exp.avg_context_recall),
            avg_context_precision=safe_float(exp.avg_context_precision),
            avg_latency_ms=safe_float(exp.avg_latency_ms),
            mlflow_experiment_id=exp.mlflow_experiment_id,
            mlflow_run_id=exp.mlflow_run_id,
            created_at=exp.created_at.isoformat() if exp.created_at else None,
            updated_at=exp.updated_at.isoformat() if exp.updated_at else None,
        )
        for exp in experiments
    ]


@router.get("/experiments/matrix")
async def get_evaluation_matrix(
    db: Session = Depends(get_db),
):
    """Get evaluation matrix data for heatmap visualization

    Returns a matrix combining:
    - Test Sets (from evaluation_testsets table)
    - Prompt Versions (from experiments)
    - Chunk Strategies (from chunk_strategies API)
    - Experiments results
    """
    from app.api.chunk_strategies import list_chunk_strategies
    from app.models.evaluation import EvaluationTestSet
    from app.services.evaluation_matrix import (
        format_experiments,
        format_prompts,
        format_testsets,
    )

    # Get all testsets
    testsets_db = db.query(EvaluationTestSet).filter(
        EvaluationTestSet.is_active.is_(True)
    ).all()
    testsets = format_testsets(testsets_db)

    # Get all chunk strategies from API
    chunk_strategies = await list_chunk_strategies()

    # Get all prompt versions
    prompts_list = await list_prompt_versions(db)
    prompts = format_prompts(prompts_list)

    # Get all experiments
    experiments_db = db.query(EvaluationExperiment).all()
    experiments = format_experiments(experiments_db)

    # Convert to structured format for frontend
    return {
        "testsets": testsets,
        "prompts": prompts,
        "chunk_strategies": chunk_strategies,
        "experiments": experiments
    }


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
            faithfulness=safe_float(result.faithfulness),
            answer_relevancy=safe_float(result.answer_relevancy),
            context_recall=safe_float(result.context_recall),
            context_precision=safe_float(result.context_precision),
            latency_ms=safe_float(result.latency_ms),
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


class PromptVersion(BaseModel):
    version: str
    template: str
    description: Optional[str] = None
    is_active: bool = True


@router.post("/prompts")
async def create_prompt_version(
    prompt: PromptVersion,
    db: Session = Depends(get_db),
):
    """Create a new prompt version"""
    import hashlib

    # Calculate hash
    prompt_hash = hashlib.sha256(prompt.template.encode('utf-8')).hexdigest()

    # Store in simple JSON format (could be a separate table in production)
    # For now, we'll return the structured data
    return {
        "version": prompt.version,
        "template": prompt.template,
        "description": prompt.description,
        "hash": prompt_hash,
        "is_active": prompt.is_active,
        "created_at": datetime.now().isoformat()
    }


@router.get("/prompts")
async def list_prompt_versions(
    db: Session = Depends(get_db),
):
    """List all prompt versions from experiments"""
    from collections import defaultdict

    # Get unique instruction versions from experiments
    experiments = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.instruction_version.isnot(None)
    ).all()

    # Group by version
    versions = defaultdict(lambda: {
        "version": None,
        "template": None,
        "hash": None,
        "experiments_count": 0,
        "first_used": None,
        "last_used": None
    })

    for exp in experiments:
        version = exp.instruction_version
        if version not in versions or versions[version]["version"] is None:
            versions[version]["version"] = version
            versions[version]["template"] = exp.instruction_template
            versions[version]["hash"] = exp.instruction_hash
            versions[version]["first_used"] = exp.created_at.isoformat() if exp.created_at else None

        versions[version]["experiments_count"] += 1
        if exp.created_at:
            last_used = exp.created_at.isoformat()
            if not versions[version]["last_used"] or last_used > versions[version]["last_used"]:
                versions[version]["last_used"] = last_used

    return list(versions.values())


@router.get("/prompts/{version}/experiments")
async def get_experiments_by_prompt_version(
    version: str,
    db: Session = Depends(get_db),
):
    """Get all experiments using a specific prompt version"""
    experiments = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.instruction_version == version
    ).all()

    return [
        {
            "id": str(exp.id),
            "name": exp.name,
            "chunk_strategy": exp.chunk_strategy,
            "status": exp.status,
            "avg_faithfulness": safe_float(exp.avg_faithfulness),
            "avg_answer_relevancy": safe_float(exp.avg_answer_relevancy),
            "created_at": exp.created_at.isoformat() if exp.created_at else None
        }
        for exp in experiments
    ]


@router.delete("/prompts/{version}")
async def delete_prompt_version(
    version: str,
    force: bool = False,
    db: Session = Depends(get_db),
):
    """Delete a prompt version and optionally its experiments"""
    # Get all experiments using this version
    experiments = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.instruction_version == version
    ).all()

    experiments_count = len(experiments)

    if experiments_count > 0:
        if not force:
            raise HTTPException(
                status_code=400,
                detail=f"無法刪除：此 Prompt 版本被 {experiments_count} 個實驗使用中。如要刪除所有相關實驗，請使用 force=true"
            )

        # Delete all related experiments
        for exp in experiments:
            db.delete(exp)

        db.commit()

        return {
            "success": True,
            "message": f"Prompt 版本 {version} 及其 {experiments_count} 個實驗已刪除"
        }

    # No experiments using this version
    return {
        "success": True,
        "message": f"Prompt 版本 {version} 未被使用，已移除"
    }


@router.get("/prompts/compare")
async def compare_prompt_versions(
    version1: str,
    version2: str,
    db: Session = Depends(get_db),
):
    """Compare two prompt versions with their templates and performance metrics"""
    from app.services.evaluation_analysis import (
        calculate_average_metrics,
        calculate_template_diff,
    )

    # Get experiments for both versions
    exp1 = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.instruction_version == version1
    ).first()

    exp2 = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.instruction_version == version2
    ).first()

    if not exp1:
        raise HTTPException(status_code=404, detail=f"Version {version1} not found")
    if not exp2:
        raise HTTPException(status_code=404, detail=f"Version {version2} not found")

    # Get all experiments for each version to calculate average metrics
    all_exp1 = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.instruction_version == version1
    ).all()

    all_exp2 = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.instruction_version == version2
    ).all()

    # Calculate metrics and diff
    metrics1 = calculate_average_metrics(all_exp1)
    metrics2 = calculate_average_metrics(all_exp2)
    diff = calculate_template_diff(exp1.instruction_template, exp2.instruction_template)

    return {
        "version1": {
            "version": version1,
            "template": exp1.instruction_template,
            "hash": exp1.instruction_hash,
            "experiments_count": len(all_exp1),
            "metrics": metrics1
        },
        "version2": {
            "version": version2,
            "template": exp2.instruction_template,
            "hash": exp2.instruction_hash,
            "experiments_count": len(all_exp2),
            "metrics": metrics2
        },
        "diff": diff,
        "template_identical": exp1.instruction_hash == exp2.instruction_hash
    }


@router.get("/recommendations")
async def get_recommendations(db: Session = Depends(get_db)):
    """Get intelligent recommendations based on experiment results"""
    from app.services.evaluation_analysis import (
        analyze_chunk_strategy_performance,
        analyze_instruction_version_performance,
        calculate_coverage_metrics,
        find_best_chunk_strategy,
        find_best_instruction_version,
        find_low_performing_strategies,
    )

    experiments = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.status == "completed"
    ).all()

    if not experiments:
        return {
            "recommendations": [],
            "summary": "尚無實驗數據，建議先執行評估實驗。"
        }

    recommendations = []

    # Analyze chunk strategies
    strategy_performance = analyze_chunk_strategy_performance(experiments)
    best_strategy, best_avg = find_best_chunk_strategy(strategy_performance)

    if best_strategy:
        recommendations.append({
            "type": "best_chunk_strategy",
            "priority": "high",
            "title": f"推薦使用 {best_strategy} 切分策略",
            "description": f"基於 {strategy_performance[best_strategy]['count']} 個實驗的數據，此策略平均分數最高 ({best_avg:.3f})",
            "action": f"在新實驗中使用 chunk_strategy='{best_strategy}'",
            "impact": "high"
        })

    # Analyze instruction versions
    version_performance = analyze_instruction_version_performance(experiments)
    best_version, best_version_avg = find_best_instruction_version(version_performance)

    if best_version:
        recommendations.append({
            "type": "best_prompt_version",
            "priority": "high",
            "title": f"推薦使用 Prompt {best_version}",
            "description": f"基於 {version_performance[best_version]['count']} 個實驗，此版本平均效果最佳",
            "action": f"使用 instruction_version='{best_version}'",
            "impact": "medium"
        })

    # Check for low-performing areas
    low_performers = find_low_performing_strategies(experiments, threshold=0.5)

    if low_performers:
        recommendations.append({
            "type": "avoid_strategy",
            "priority": "medium",
            "title": "避免使用低效策略",
            "description": f"以下策略表現較差: {', '.join(low_performers)}",
            "action": "考慮更換不同的 chunk 參數組合",
            "impact": "medium"
        })

    # Check coverage
    coverage_metrics = calculate_coverage_metrics(experiments)

    if coverage_metrics['coverage_percent'] < 50 and coverage_metrics['total_cells'] > 0:
        recommendations.append({
            "type": "increase_coverage",
            "priority": "low",
            "title": "增加測試覆蓋率",
            "description": f"目前評估矩陣覆蓋率僅 {coverage_metrics['coverage_percent']:.1f}%",
            "action": "執行更多策略與測試集的組合實驗",
            "impact": "low"
        })

    # Summary
    summary = f"分析了 {len(experiments)} 個實驗，生成了 {len(recommendations)} 個建議"

    return {
        "recommendations": recommendations,
        "summary": summary,
        "stats": {
            "total_experiments": len(experiments),
            "unique_strategies": len(strategy_performance),
            "unique_prompt_versions": len(version_performance),
            "best_strategy": best_strategy,
            "best_prompt_version": best_version
        }
    }
