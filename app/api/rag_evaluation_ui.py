"""UI routes for RAG evaluation system"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.chunk_strategies import get_all_strategies
from app.core.database import get_db
from app.models.evaluation import EvaluationExperiment, EvaluationTestSet

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag/evaluation", tags=["rag-evaluation-ui"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def evaluation_dashboard(request: Request):
    """Redirect to evaluation matrix (old evaluation page deprecated)"""
    return RedirectResponse(url="/rag/evaluation/matrix", status_code=302)


@router.get("/matrix", response_class=HTMLResponse)
async def evaluation_matrix(request: Request, db: Session = Depends(get_db)):
    """Evaluation matrix heatmap page - SERVER RENDERED"""

    logger.info("Evaluation matrix route called")

    try:
        # 1. 獲取所有testsets
        logger.debug("Step 1: Fetching testsets...")
        testsets_objs = db.query(EvaluationTestSet).filter(EvaluationTestSet.is_active.is_(True)).all()
        testsets = [{"id": str(ts.id), "name": ts.name} for ts in testsets_objs]
        logger.info(f"Found {len(testsets)} testsets")

        # 2. 獲取所有prompts (unique instruction_version from experiments)
        logger.debug("Step 2: Fetching prompts...")
        unique_versions = db.query(EvaluationExperiment.instruction_version).distinct().all()
        prompts = [{"version": v[0]} for v in unique_versions if v[0]]  # Filter out None values
        logger.info(f"Found {len(prompts)} unique prompt versions")

        # 3. 獲取所有chunk strategies
        logger.debug("Step 3: Getting chunk strategies...")
        chunk_strategies = get_all_strategies()
        logger.info(f"Found {len(chunk_strategies)} chunk strategies")

        # 4. 獲取所有completed experiments
        logger.debug("Step 4: Fetching experiments...")
        experiments = db.query(EvaluationExperiment).filter(
            EvaluationExperiment.status == "completed"
        ).all()
        logger.info(f"Found {len(experiments)} completed experiments")

        # 5. 組織matrix數據結構：matrix[chunk_strategy][prompt_version][testset_name] = experiment
        logger.debug("Step 5: Building matrix structure...")
        matrix = {}
        for cs in chunk_strategies:
            matrix[cs["name"]] = {}
            for p in prompts:
                matrix[cs["name"]][p["version"]] = {}
                for ts in testsets:
                    matrix[cs["name"]][p["version"]][ts["name"]] = None
        logger.debug("Matrix structure built")

        # 6. 填充實驗數據
        logger.debug("Step 6: Populating matrix with experiments...")
        matched_count = 0
        for exp in experiments:
            # 通過chunk_size和chunk_overlap匹配chunk_strategy
            matching_strategy = None
            for cs in chunk_strategies:
                if (exp.chunk_size == cs["chunk_size"] and
                    exp.chunk_overlap == cs["chunk_overlap"]):
                    matching_strategy = cs["name"]
                    break

            if not matching_strategy:
                continue

            prompt_ver = exp.instruction_version
            if not prompt_ver:
                continue

            # 目前實驗沒有testset關聯，先用實驗名稱猜測
            # TODO: 需要在experiment model加testset_id
            for ts in testsets:
                if ts["name"] in exp.name:
                    matrix[matching_strategy][prompt_ver][ts["name"]] = {
                        "id": str(exp.id),
                        "status": exp.status,
                        "faithfulness": exp.avg_faithfulness,
                        "answer_relevancy": exp.avg_answer_relevancy,
                        "context_recall": exp.avg_context_recall,
                        "context_precision": exp.avg_context_precision,
                    }
                    matched_count += 1
                    break
        logger.info(f"Matched {matched_count} experiments to matrix cells")

        logger.debug("Step 7: Rendering template...")
        return templates.TemplateResponse(
            "rag/matrix.html",
            {
                "request": request
            }
        )
    except Exception as e:
        logger.error(f"Error in matrix route: {e}", exc_info=True)
        raise


@router.get("/experiments/{experiment_id}", response_class=HTMLResponse)
async def experiment_detail(request: Request, experiment_id: str):
    """Experiment detail page"""
    return templates.TemplateResponse(
        "rag/experiment_detail.html",
        {"request": request, "experiment_id": experiment_id}
    )


@router.get("/prompts", response_class=HTMLResponse)
async def prompts_management(request: Request):
    """Prompt version management page"""
    return templates.TemplateResponse(
        "rag/prompts.html",
        {"request": request}
    )


@router.get("/chunks", response_class=HTMLResponse)
async def chunks_management(request: Request):
    """Chunk strategy management page"""
    return templates.TemplateResponse(
        "rag/chunks.html",
        {"request": request}
    )
