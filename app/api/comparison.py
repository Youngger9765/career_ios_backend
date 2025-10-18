"""Report comparison endpoint for A/B testing"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()


@router.get("/comparison", response_class=HTMLResponse)
async def show_comparison_page():
    """顯示報告對比頁面（靜態展示，無需切分支）"""
    html_path = Path(__file__).parent.parent / "templates" / "static_comparison.html"
    return html_path.read_text(encoding="utf-8")
