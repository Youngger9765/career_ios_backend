"""UI routes for RAG evaluation system"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/rag/evaluation", tags=["rag-evaluation-ui"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def evaluation_dashboard(request: Request):
    """Redirect to evaluation matrix (old evaluation page deprecated)"""
    return RedirectResponse(url="/rag/evaluation/matrix", status_code=302)


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


@router.get("/chunks", response_class=HTMLResponse)
async def chunks_management(request: Request):
    """Chunk strategy management page"""
    return templates.TemplateResponse(
        "rag/chunks.html",
        {"request": request}
    )
