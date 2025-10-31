from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# RAG API routers
from app.api import (
    auth,
    chunk_strategies,
    clients,
    comparison,
    evaluation_testsets,
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
    sessions,
)
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

# Include client routes
app.include_router(clients.router)

# Include reports routes
app.include_router(reports.router)

# Include sessions routes
app.include_router(sessions.router)

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

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - Homepage with entry points"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "version": settings.APP_VERSION,
    })


# RAG Ops Console (FastAPI Templates)
@app.get("/rag", response_class=HTMLResponse)
async def rag_index(request: Request):
    """RAG Ops Console - Main page"""
    return templates.TemplateResponse("rag/index.html", {"request": request})


@app.get("/rag/agents", response_class=HTMLResponse)
async def rag_agents_page(request: Request):
    """RAG Ops Console - Agents page"""
    return templates.TemplateResponse("rag/agents.html", {"request": request})


@app.get("/rag/documents", response_class=HTMLResponse)
async def rag_documents_page(request: Request):
    """RAG Ops Console - Documents page"""
    return templates.TemplateResponse("rag/documents.html", {"request": request})


@app.get("/rag/upload", response_class=HTMLResponse)
async def rag_upload(request: Request):
    """RAG Ops Console - Upload page"""
    return templates.TemplateResponse("rag/upload.html", {"request": request})


@app.get("/rag/test", response_class=HTMLResponse)
async def rag_test(request: Request):
    """RAG Ops Console - Test Bench page"""
    return templates.TemplateResponse("rag/test.html", {"request": request})


@app.get("/rag/stats", response_class=HTMLResponse)
async def rag_stats_page(request: Request):
    """RAG Ops Console - Stats page"""
    return templates.TemplateResponse("rag/stats.html", {"request": request})


@app.get("/rag/chat", response_class=HTMLResponse)
async def rag_chat_page(request: Request):
    """RAG Ops Console - Chat page"""
    return templates.TemplateResponse("rag/chat.html", {"request": request})


@app.get("/rag/report", response_class=HTMLResponse)
async def rag_report_page(request: Request):
    """RAG Ops Console - Report Generation page"""
    return templates.TemplateResponse("rag/report.html", {"request": request})


@app.get("/console", response_class=HTMLResponse)
async def console_page(request: Request):
    """Counseling System Debug Console"""
    return templates.TemplateResponse("console.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
