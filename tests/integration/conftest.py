"""
Integration test fixtures
"""
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# Import all models to ensure they're registered with Base.metadata
# Console models
from app.models.counselor import Counselor  # noqa: F401
from app.models.client import Client  # noqa: F401
from app.models.case import Case  # noqa: F401
from app.models.session import Session as SessionModel  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.reminder import Reminder  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401

# RAG models
from app.models.document import Datasource, Document, Chunk, Embedding  # noqa: F401
from app.models.collection import Collection, CollectionItem  # noqa: F401
from app.models.chat import ChatLog  # noqa: F401
from app.models.evaluation import (  # noqa: F401
    EvaluationExperiment,
    EvaluationResult,
    EvaluationTestSet,
    DocumentQualityMetric,
)
from app.models.agent import Agent, AgentVersion  # noqa: F401
from app.models.pipeline import PipelineRun  # noqa: F401


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for integration tests"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async test database session"""
    from app.core.config import settings

    # Convert postgresql:// to postgresql+asyncpg:// for async support
    db_url = str(settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a synchronous test database session for integration tests"""
    # Use in-memory SQLite with StaticPool for testing (works across threads)
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=True,  # Enable SQL logging for debugging
        poolclass=StaticPool  # Keep connection alive across requests
    )

    # Create all tables - this will show which tables are being created
    print(f"\nCreating tables: {list(Base.metadata.tables.keys())}")
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Override get_db dependency - CRITICAL: must return the same session
    def override_get_db():
        try:
            yield session
        finally:
            # Don't close session here, as it's managed by the fixture
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        # Clear dependency overrides
        app.dependency_overrides.clear()
        engine.dispose()
