"""API routes"""

from fastapi import APIRouter
from app.api import auth, users, visitors, cases, sessions, jobs, reports, reminders, pipeline

router = APIRouter()

# Include all route modules
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(visitors.router, prefix="/visitors", tags=["Visitors"])
router.include_router(cases.router, prefix="/cases", tags=["Cases"])
router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
router.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])