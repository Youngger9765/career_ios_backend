from typing import Dict, Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
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
from app.core.exceptions import NotFoundError
from app.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.utils.tenant import (
    detect_tenant_from_path,
    normalize_tenant_from_url,
    validate_tenant,
)

# Templates
templates = Jinja2Templates(directory="app/templates")

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    """Root endpoint - Landing Page for end users"""
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
            "version": settings.APP_VERSION,
        },
    )


@app.get("/internal", response_class=HTMLResponse)
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute per IP
async def internal_portal(
    request: Request,
    password: Optional[str] = Query(None, description="Internal portal password"),
) -> Response:
    """
    Internal Portal - Admin entry points (hidden from public)

    This route requires a password to access. Rate limited to prevent brute force.
    All admin pages still require authentication after accessing this portal.

    SECURITY: In production environment, password is REQUIRED.
    Staging/Development: Password is optional (for development convenience).
    """
    is_production = settings.ENVIRONMENT.lower() == "production"
    is_staging = settings.ENVIRONMENT.lower() == "staging"

    # Production environment: Password is REQUIRED
    if is_production:
        if not settings.INTERNAL_PORTAL_PASSWORD:
            # Production environment without password - show error
            return templates.TemplateResponse(
                "internal_error.html",
                {
                    "request": request,
                    "error": "Internal portal password is not configured. Please set INTERNAL_PORTAL_PASSWORD in environment variables.",
                    "is_production": True,
                },
            )

        # Production with password configured - require password
        if not password or password != settings.INTERNAL_PORTAL_PASSWORD:
            error_message = "Invalid password" if password else None
            return templates.TemplateResponse(
                "internal_login.html",
                {
                    "request": request,
                    "error": error_message,
                },
            )
    elif is_staging:
        # Staging environment: Password is optional (for development convenience)
        # Only require password if it's configured
        if settings.INTERNAL_PORTAL_PASSWORD:
            # Password configured - require it
            if not password or password != settings.INTERNAL_PORTAL_PASSWORD:
                error_message = "Invalid password" if password else None
                return templates.TemplateResponse(
                    "internal_login.html",
                    {
                        "request": request,
                        "error": error_message,
                    },
                )
        # No password configured in staging - allow access (development convenience)
    else:
        # Development environment: Password is optional
        if settings.INTERNAL_PORTAL_PASSWORD:
            # Password configured - require it
            if not password or password != settings.INTERNAL_PORTAL_PASSWORD:
                error_message = "Invalid password" if password else None
                return templates.TemplateResponse(
                    "internal_login.html",
                    {
                        "request": request,
                        "error": error_message,
                    },
                )
        # No password configured - allow access (development convenience)

    # Password correct or no password required (staging/dev only) - show admin portal
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
# Island Parents Routes (浮島親子) - 保留作為向後兼容
# =====================
@app.get("/island-parents", response_class=HTMLResponse)
async def island_parents_login(request: Request) -> Response:
    """Island Parents - Login page"""
    return templates.TemplateResponse("island_parents/login.html", {"request": request})


@app.get("/island-parents/login", response_class=HTMLResponse)
async def island_parents_login_alt(request: Request) -> Response:
    """Island Parents - Login page (alt)"""
    return templates.TemplateResponse("island_parents/login.html", {"request": request})


@app.get("/island-parents/forgot-password", response_class=HTMLResponse)
async def island_parents_forgot_password(request: Request) -> Response:
    """Island Parents - Forgot password page"""
    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "default_tenant": "island_parents",
        },
    )


@app.get("/island-parents/reset-password", response_class=HTMLResponse)
async def island_parents_reset_password(request: Request) -> Response:
    """Island Parents - Reset password page"""
    return templates.TemplateResponse("reset_password.html", {"request": request})


@app.get("/island-parents/terms", response_class=HTMLResponse)
async def island_parents_terms(request: Request) -> Response:
    """Island Parents - Terms of Service page"""
    return templates.TemplateResponse("island_parents/terms.html", {"request": request})


@app.get("/island-parents/privacy", response_class=HTMLResponse)
async def island_parents_privacy(request: Request) -> Response:
    """Island Parents - Privacy Policy page"""
    return templates.TemplateResponse("island_parents/privacy.html", {"request": request})


# =====================
# Dynamic Tenant Routes (支援所有租戶) - 放在硬編碼路由之後
# =====================
@app.get("/{tenant_id}/forgot-password", response_class=HTMLResponse)
async def tenant_forgot_password(
    request: Request,
    tenant_id: str,
) -> Response:
    """
    Forgot password page for any tenant

    Args:
        tenant_id: Tenant ID in URL format (kebab-case, e.g., "island-parents", "career", "island")
    """
    # Convert URL format (kebab-case) to database format (snake_case)
    normalized_tenant = normalize_tenant_from_url(tenant_id)

    if not normalized_tenant or not validate_tenant(normalized_tenant):
        raise NotFoundError(
            detail="Tenant not found",
            instance=str(request.url.path),
        )

    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "default_tenant": normalized_tenant,
        },
    )


@app.get("/{tenant_id}/reset-password", response_class=HTMLResponse)
async def tenant_reset_password(
    request: Request,
    tenant_id: str,
    token: Optional[str] = Query(None, description="Password reset token"),
) -> Response:
    """
    Reset password page for any tenant

    Args:
        tenant_id: Tenant ID in URL format (kebab-case, e.g., "island-parents", "career", "island")
        token: Optional password reset token from query parameter
    """
    # Convert URL format (kebab-case) to database format (snake_case)
    normalized_tenant = normalize_tenant_from_url(tenant_id)

    if not normalized_tenant or not validate_tenant(normalized_tenant):
        raise NotFoundError(
            detail="Tenant not found",
            instance=str(request.url.path),
        )

    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "token": token,  # Pass token to template for server-side rendering
        },
    )


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
    2. Referer header (extract from referer URL path)
    3. Default from settings.DEFAULT_TENANT

    This keeps flexibility for future multi-tenant scenarios while
    hiding the tenant selector from users.
    """
    from urllib.parse import urlparse

    from app.core.config import settings

    # Determine tenant: URL param > Referer > Default
    detected_tenant = tenant

    # Extract from referer if not provided in URL
    if not detected_tenant:
        referer = request.headers.get("referer")
        if referer:
            try:
                parsed_url = urlparse(referer)
                path = parsed_url.path

                # Use tenant utility to detect from path
                detected_tenant = detect_tenant_from_path(path)
            except Exception:
                # If parsing fails, fall back to default
                pass

    # Fall back to default if still not detected
    if not detected_tenant:
        detected_tenant = settings.DEFAULT_TENANT

    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "default_tenant": detected_tenant,
        },
    )


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: Optional[str] = Query(None, description="Password reset token"),
) -> Response:
    """Reset Password page - Set new password with token"""
    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "token": token,  # Pass token to template for server-side rendering
        },
    )


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
