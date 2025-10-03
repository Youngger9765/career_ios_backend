"""Evaluation Test Sets UI Routes"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/rag/evaluation/testsets", tags=["evaluation-testsets-ui"])

templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def testsets_management_page(request: Request):
    """測試集管理頁面"""
    return templates.TemplateResponse("rag/testsets.html", {"request": request})
