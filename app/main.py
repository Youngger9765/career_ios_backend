from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# API routers
from app.api import (
    analyze,
    auth,
    billing_reports,
    cases,
    chunk_strategies,
    clients,
    comparison,
    evaluation_testsets,
    field_schemas,
    rag_agents,
    rag_chat,
    rag_evaluation,
    rag_evaluation_testsets_ui,
    rag_evaluation_ui,
    rag_ingest,
    rag_report,
    rag_search,
    rag_stats,
    realtime,
    reports,
    sessions,
    sessions_analysis,
    sessions_keywords,
    ui_client_case_list,
)
from app.api.v1 import admin_counselors, admin_credits, password_reset
from app.core.config import settings

# Templates
templates = Jinja2Templates(directory="app/templates")

# Create FastAPI instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth.router, prefix="/api")

# Include password reset routes (v1 API)
app.include_router(password_reset.router, prefix="/api/v1")

# Include admin credit management routes
app.include_router(admin_credits.router, prefix="/api/v1")

# Include admin counselor management routes
app.include_router(admin_counselors.router, prefix="/api/v1")

# Include client routes
app.include_router(clients.router)

# Include case routes
app.include_router(cases.router)

# Include field schema routes
app.include_router(field_schemas.router)

# Include reports routes
app.include_router(reports.router)

# Include sessions routes
app.include_router(sessions.router)
app.include_router(sessions_keywords.router)
app.include_router(sessions_analysis.router)

# Include analyze routes
app.include_router(analyze.router)

# Include realtime STT counseling routes (Demo Feature)
app.include_router(realtime.router)

# Include UI API routes
app.include_router(ui_client_case_list.router)

# Include RAG API routes
app.include_router(rag_ingest.router)
app.include_router(rag_search.router)
app.include_router(rag_chat.router)
app.include_router(rag_agents.router)
app.include_router(rag_stats.router)
app.include_router(rag_report.router)
app.include_router(rag_evaluation.router)
app.include_router(rag_evaluation_ui.router)
app.include_router(evaluation_testsets.router)
app.include_router(rag_evaluation_testsets_ui.router)
app.include_router(chunk_strategies.router)
app.include_router(comparison.router, tags=["comparison"])

# Include Billing API routes
app.include_router(billing_reports.router)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> Response:
    """Root endpoint - Homepage with entry points"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "version": settings.APP_VERSION,
        },
    )


# RAG Ops Console (FastAPI Templates)
@app.get("/rag", response_class=HTMLResponse)
async def rag_index(request: Request) -> Response:
    """RAG Ops Console - Main page"""
    return templates.TemplateResponse("rag/index.html", {"request": request})


@app.get("/rag/agents", response_class=HTMLResponse)
async def rag_agents_page(request: Request) -> Response:
    """RAG Ops Console - Agents page"""
    return templates.TemplateResponse("rag/agents.html", {"request": request})


@app.get("/rag/documents", response_class=HTMLResponse)
async def rag_documents_page(request: Request) -> Response:
    """RAG Ops Console - Documents page"""
    return templates.TemplateResponse("rag/documents.html", {"request": request})


@app.get("/rag/upload", response_class=HTMLResponse)
async def rag_upload(request: Request) -> Response:
    """RAG Ops Console - Upload page"""
    return templates.TemplateResponse("rag/upload.html", {"request": request})


@app.get("/rag/test", response_class=HTMLResponse)
async def rag_test(request: Request) -> Response:
    """RAG Ops Console - Test Bench page"""
    return templates.TemplateResponse("rag/test.html", {"request": request})


@app.get("/rag/stats", response_class=HTMLResponse)
async def rag_stats_page(request: Request) -> Response:
    """RAG Ops Console - Stats page"""
    return templates.TemplateResponse("rag/stats.html", {"request": request})


@app.get("/rag/chat", response_class=HTMLResponse)
async def rag_chat_page(request: Request) -> Response:
    """RAG Ops Console - Chat page"""
    return templates.TemplateResponse("rag/chat.html", {"request": request})


@app.get("/rag/report", response_class=HTMLResponse)
async def rag_report_page(request: Request) -> Response:
    """RAG Ops Console - Report Generation page"""
    return templates.TemplateResponse("rag/report.html", {"request": request})


@app.get("/console", response_class=HTMLResponse)
async def console_page(request: Request) -> Response:
    """Counseling System Debug Console - All API testing in one place"""
    return templates.TemplateResponse("console.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request) -> Response:
    """Admin Portal - Multi-Tenant Management"""
    return templates.TemplateResponse(
        "admin.html", {"request": request, "debug_mode": settings.DEBUG}
    )


@app.get("/realtime-counseling", response_class=HTMLResponse)
async def realtime_counseling_page(request: Request) -> Response:
    """Realtime STT Counseling page - AI-powered live counseling assistant"""
    return templates.TemplateResponse("realtime_counseling.html", {"request": request})


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request) -> Response:
    """Forgot Password page - Request password reset"""
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request) -> Response:
    """Reset Password page - Set new password with token"""
    return templates.TemplateResponse("reset_password.html", {"request": request})


@app.get("/test-elevenlabs", response_class=HTMLResponse)
async def test_elevenlabs_page(request: Request) -> Response:
    """ElevenLabs WebSocket connection test page"""
    return templates.TemplateResponse("test_elevenlabs_ws.html", {"request": request})


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return empty response for favicon to avoid 404"""
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
