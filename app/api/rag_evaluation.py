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

    # Get all testsets
    testsets_db = db.query(EvaluationTestSet).filter(
        EvaluationTestSet.is_active.is_(True)
    ).all()
    testsets = [{"id": str(ts.id), "name": ts.name} for ts in testsets_db]

    # Get all chunk strategies from API
    chunk_strategies_data = await list_chunk_strategies()
    # chunk_strategies_data is already a list of dicts
    chunk_strategies = chunk_strategies_data

    # Get all prompt versions
    prompts_list = await list_prompt_versions(db)
    prompts = [{"version": p["version"]} for p in prompts_list]

    # Get all experiments
    experiments = db.query(EvaluationExperiment).all()

    # Build matrix: strategy -> prompt -> testset -> experiment
    # matrix = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))

    # For now, create a simpler matrix structure
    # Future: add testset_id to EvaluationExperiment model
    experiments_list = []
    for exp in experiments:
        experiments_list.append({
            "experiment_id": str(exp.id),
            "name": exp.name,
            "status": exp.status,
            "chunk_strategy": exp.chunk_strategy,
            "instruction_version": exp.instruction_version,
            "avg_faithfulness": safe_float(exp.avg_faithfulness),
            "avg_answer_relevancy": safe_float(exp.avg_answer_relevancy),
            "avg_context_recall": safe_float(exp.avg_context_recall),
            "avg_context_precision": safe_float(exp.avg_context_precision),
            "total_queries": exp.total_queries or 0,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "chunking_method": exp.chunking_method,
            "chunk_size": exp.chunk_size,
            "chunk_overlap": exp.chunk_overlap,
        })

    # Convert to structured format for frontend
    return {
        "testsets": testsets,
        "prompts": prompts,
        "chunk_strategies": chunk_strategies,
        "experiments": experiments_list  # Return the list, not the matrix dict
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

    def calc_avg_metrics(experiments):
        metrics = {
            'faithfulness': [],
            'answer_relevancy': [],
            'context_recall': [],
            'context_precision': []
        }

        for exp in experiments:
            if exp.avg_faithfulness is not None:
                metrics['faithfulness'].append(float(exp.avg_faithfulness))
            if exp.avg_answer_relevancy is not None:
                metrics['answer_relevancy'].append(float(exp.avg_answer_relevancy))
            if exp.avg_context_recall is not None:
                metrics['context_recall'].append(float(exp.avg_context_recall))
            if exp.avg_context_precision is not None:
                metrics['context_precision'].append(float(exp.avg_context_precision))

        return {
            'avg_faithfulness': sum(metrics['faithfulness']) / len(metrics['faithfulness']) if metrics['faithfulness'] else None,
            'avg_answer_relevancy': sum(metrics['answer_relevancy']) / len(metrics['answer_relevancy']) if metrics['answer_relevancy'] else None,
            'avg_context_recall': sum(metrics['context_recall']) / len(metrics['context_recall']) if metrics['context_recall'] else None,
            'avg_context_precision': sum(metrics['context_precision']) / len(metrics['context_precision']) if metrics['context_precision'] else None,
        }

    # Calculate text diff
    import difflib
    template1_lines = (exp1.instruction_template or "").splitlines()
    template2_lines = (exp2.instruction_template or "").splitlines()
    diff = list(difflib.unified_diff(template1_lines, template2_lines, lineterm=''))

    return {
        "version1": {
            "version": version1,
            "template": exp1.instruction_template,
            "hash": exp1.instruction_hash,
            "experiments_count": len(all_exp1),
            "metrics": calc_avg_metrics(all_exp1)
        },
        "version2": {
            "version": version2,
            "template": exp2.instruction_template,
            "hash": exp2.instruction_hash,
            "experiments_count": len(all_exp2),
            "metrics": calc_avg_metrics(all_exp2)
        },
        "diff": diff,
        "template_identical": exp1.instruction_hash == exp2.instruction_hash
    }


@router.get("/recommendations")
async def get_recommendations(db: Session = Depends(get_db)):
    """Get intelligent recommendations based on experiment results"""

    experiments = db.query(EvaluationExperiment).filter(
        EvaluationExperiment.status == "completed"
    ).all()

    if not experiments:
        return {
            "recommendations": [],
            "summary": "尚無實驗數據，建議先執行評估實驗。"
        }

    recommendations = []

    # Analyze by chunk strategy
    strategy_performance = {}
    for exp in experiments:
        if not exp.chunk_strategy:
            continue

        if exp.chunk_strategy not in strategy_performance:
            strategy_performance[exp.chunk_strategy] = {
                'count': 0,
                'total_faithfulness': 0,
                'total_answer_relevancy': 0,
                'total_context_recall': 0,
                'total_context_precision': 0
            }

        perf = strategy_performance[exp.chunk_strategy]
        perf['count'] += 1

        if exp.avg_faithfulness:
            perf['total_faithfulness'] += float(exp.avg_faithfulness)
        if exp.avg_answer_relevancy:
            perf['total_answer_relevancy'] += float(exp.avg_answer_relevancy)
        if exp.avg_context_recall:
            perf['total_context_recall'] += float(exp.avg_context_recall)
        if exp.avg_context_precision:
            perf['total_context_precision'] += float(exp.avg_context_precision)

    # Calculate averages and find best strategy
    best_strategy = None
    best_avg = 0

    for strategy, perf in strategy_performance.items():
        count = perf['count']
        avg_score = (
            perf['total_faithfulness'] / count +
            perf['total_answer_relevancy'] / count +
            perf['total_context_recall'] / count +
            perf['total_context_precision'] / count
        ) / 4

        if avg_score > best_avg:
            best_avg = avg_score
            best_strategy = strategy

    if best_strategy:
        recommendations.append({
            "type": "best_chunk_strategy",
            "priority": "high",
            "title": f"推薦使用 {best_strategy} 切分策略",
            "description": f"基於 {strategy_performance[best_strategy]['count']} 個實驗的數據，此策略平均分數最高 ({best_avg:.3f})",
            "action": f"在新實驗中使用 chunk_strategy='{best_strategy}'",
            "impact": "high"
        })

    # Analyze by instruction version
    version_performance = {}
    for exp in experiments:
        if not exp.instruction_version:
            continue

        if exp.instruction_version not in version_performance:
            version_performance[exp.instruction_version] = {
                'count': 0,
                'total_score': 0
            }

        perf = version_performance[exp.instruction_version]
        perf['count'] += 1

        score_sum = 0
        score_count = 0
        if exp.avg_faithfulness:
            score_sum += float(exp.avg_faithfulness)
            score_count += 1
        if exp.avg_answer_relevancy:
            score_sum += float(exp.avg_answer_relevancy)
            score_count += 1

        if score_count > 0:
            perf['total_score'] += score_sum / score_count

    # Find best prompt version
    best_version = None
    best_version_avg = 0

    for version, perf in version_performance.items():
        if perf['count'] == 0:
            continue
        avg = perf['total_score'] / perf['count']
        if avg > best_version_avg:
            best_version_avg = avg
            best_version = version

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
    low_performers = []
    for exp in experiments:
        if exp.avg_faithfulness and float(exp.avg_faithfulness) < 0.5:
            low_performers.append(exp.chunk_strategy or "unknown")

    if low_performers:
        unique_low = set(low_performers)
        recommendations.append({
            "type": "avoid_strategy",
            "priority": "medium",
            "title": "避免使用低效策略",
            "description": f"以下策略表現較差: {', '.join(unique_low)}",
            "action": "考慮更換不同的 chunk 參數組合",
            "impact": "medium"
        })

    # Check coverage
    total_cells = 0
    completed_cells = 0
    strategies = set()
    test_sets = set()

    for exp in experiments:
        if exp.chunk_strategy:
            strategies.add(exp.chunk_strategy)
        if hasattr(exp, 'test_set_name') and exp.test_set_name:
            test_sets.add(exp.test_set_name)

    if strategies and test_sets:
        total_cells = len(strategies) * len(test_sets)
        completed_cells = len(experiments)
        coverage = (completed_cells / total_cells) * 100

        if coverage < 50:
            recommendations.append({
                "type": "increase_coverage",
                "priority": "low",
                "title": "增加測試覆蓋率",
                "description": f"目前評估矩陣覆蓋率僅 {coverage:.1f}%",
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
