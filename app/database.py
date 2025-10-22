"""Database module - import alias for backward compatibility with RAG modules"""
from app.core.database import Base, SessionLocal, engine, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
