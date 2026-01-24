from typing import Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    reports,
    session_analysis,
    sessions,
    sessions_analysis,
    sessions_keywords,
    transcript,
    ui_client_case_list,
)
from app.api.v1 import admin_counselors, admin_credits, password_reset, session_usage
from app.core.config import settings
from app.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

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

# Add RFC 7807 error handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include auth routes
app.include_router(auth.router, prefix="/api")

# Include password reset routes (v1 API)
app.include_router(password_reset.router, prefix="/api/v1")

# Include admin credit management routes
app.include_router(admin_credits.router, prefix="/api/v1")

# Include admin counselor management routes
app.include_router(admin_counselors.router, prefix="/api/v1")

# Include session usage routes
app.include_router(session_usage.router)

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
app.include_router(session_analysis.router)

# Include analyze routes
app.include_router(analyze.router)

# Transcript API (elevenlabs-token only - for iOS STT)
app.include_router(transcript.router)

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


# =====================
# Island Parents Routes (浮島親子)
# =====================
@app.get("/island-parents", response_class=HTMLResponse)
async def island_parents_login(request: Request) -> Response:
    """Island Parents - Login page"""
    return templates.TemplateResponse("island_parents/login.html", {"request": request})


@app.get("/island-parents/login", response_class=HTMLResponse)
async def island_parents_login_alt(request: Request) -> Response:
    """Island Parents - Login page (alt)"""
    return templates.TemplateResponse("island_parents/login.html", {"request": request})


@app.get("/island-parents/clients", response_class=HTMLResponse)
async def island_parents_clients(request: Request) -> Response:
    """Island Parents - Client selection page"""
    return templates.TemplateResponse(
        "island_parents/clients.html", {"request": request}
    )


@app.get("/island-parents/clients/create", response_class=HTMLResponse)
async def island_parents_clients_create(request: Request) -> Response:
    """Island Parents - Create new client page"""
    return templates.TemplateResponse(
        "island_parents/clients_create.html", {"request": request}
    )


@app.get("/island-parents/clients/{client_id}/edit", response_class=HTMLResponse)
async def island_parents_clients_edit(request: Request, client_id: str) -> Response:
    """Island Parents - Edit client page"""
    return templates.TemplateResponse(
        "island_parents/clients_edit.html",
        {"request": request, "client_id": client_id},
    )


@app.get("/island-parents/clients/{client_id}/history", response_class=HTMLResponse)
async def island_parents_clients_history(request: Request, client_id: str) -> Response:
    """Island Parents - Client session history page"""
    return templates.TemplateResponse(
        "island_parents/clients_history.html",
        {"request": request, "client_id": client_id},
    )


@app.get("/island-parents/mode", response_class=HTMLResponse)
async def island_parents_session_mode(request: Request) -> Response:
    """Island Parents - Session mode selection page"""
    return templates.TemplateResponse(
        "island_parents/session_mode.html", {"request": request}
    )


@app.get("/island-parents/session", response_class=HTMLResponse)
async def island_parents_session(request: Request) -> Response:
    """Island Parents - Session/scenario selection page"""
    return templates.TemplateResponse(
        "island_parents/session.html", {"request": request}
    )


@app.get("/island-parents/scenario-detail", response_class=HTMLResponse)
async def island_parents_scenario_detail(request: Request) -> Response:
    """Island Parents - Scenario detail input page"""
    return templates.TemplateResponse(
        "island_parents/scenario_detail.html", {"request": request}
    )


@app.get("/island-parents/emergency-hint", response_class=HTMLResponse)
async def island_parents_emergency_hint(request: Request) -> Response:
    """Island Parents - Emergency mode hint page"""
    return templates.TemplateResponse(
        "island_parents/emergency_hint.html", {"request": request}
    )


@app.get("/island-parents/recording", response_class=HTMLResponse)
async def island_parents_recording(request: Request) -> Response:
    """Island Parents - Recording page with color orb"""
    return templates.TemplateResponse(
        "island_parents/recording.html", {"request": request}
    )


@app.get("/island-parents/generating", response_class=HTMLResponse)
async def island_parents_generating(request: Request) -> Response:
    """Island Parents - Report generating page"""
    return templates.TemplateResponse(
        "island_parents/generating.html", {"request": request}
    )


@app.get("/island-parents/complete", response_class=HTMLResponse)
async def island_parents_complete(request: Request) -> Response:
    """Island Parents - Session complete page"""
    return templates.TemplateResponse(
        "island_parents/complete.html", {"request": request}
    )


@app.get("/island-parents/report/{session_id}", response_class=HTMLResponse)
async def island_parents_report(request: Request, session_id: str) -> Response:
    """Island Parents - Session report page"""
    return templates.TemplateResponse(
        "island_parents/report.html", {"request": request}
    )


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(
    request: Request,
    tenant: Optional[str] = None,
) -> Response:
    """
    Forgot Password page - Request password reset
    
    Tenant can be specified via:
    1. URL query parameter: ?tenant=island_parents
    2. Referer header (future: extract from subdomain or referer)
    3. Default from settings.DEFAULT_TENANT
    
    This keeps flexibility for future multi-tenant scenarios while
    hiding the tenant selector from users.
    """
    from app.core.config import settings
    
    # Determine tenant: URL param > Referer detection > Default
    detected_tenant = tenant
    
    # Future: Extract from referer or subdomain if needed
    # For now, use URL param or default
    if not detected_tenant:
        # Check referer for tenant hint (optional, for future use)
        referer = request.headers.get("referer", "")
        # Could extract tenant from referer URL here if needed
        
        # Use default tenant
        detected_tenant = settings.DEFAULT_TENANT
    
    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "default_tenant": detected_tenant,
        },
    )


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
