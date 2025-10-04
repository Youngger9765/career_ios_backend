"""UI routes for RAG evaluation system"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/rag/evaluation", tags=["rag-evaluation-ui"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def evaluation_dashboard(request: Request):
    """Evaluation dashboard page"""
    return templates.TemplateResponse(
        "rag/evaluation.html",
        {"request": request}
    )


@router.get("/matrix", response_class=HTMLResponse)
async def evaluation_matrix(request: Request):
    """Evaluation matrix heatmap page"""
    return templates.TemplateResponse(
        "rag/matrix.html",
        {"request": request}
    )


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
