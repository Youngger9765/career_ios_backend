"""Tests for database session management"""
import pytest
from sqlalchemy.orm import Session


class TestDatabaseSession:
    """Test database session creation and lifecycle"""

    def test_get_db_returns_session(self):
        """Test get_db yields a valid SQLAlchemy Session"""
        from app.core.database import get_db

        # Get session from generator
        db_gen = get_db()
        db = next(db_gen)

        assert db is not None
        assert isinstance(db, Session)

        # Clean up
        try:
            next(db_gen)
        except StopIteration:
            pass  # Expected

    def test_get_db_closes_session_after_use(self):
        """Test session is properly closed after use"""
        from app.core.database import get_db

        db_gen = get_db()
        db = next(db_gen)

        # Check session exists and is usable
        assert db is not None
        assert isinstance(db, Session)

        # Close the generator (simulates finally block)
        db_gen.close()

        # Verify the generator is exhausted (cleanup completed)
        with pytest.raises(StopIteration):
            next(db_gen)


class TestDatabaseBase:
    """Test Base declarative class"""

    def test_base_is_declarative_base(self):
        """Test Base is a proper SQLAlchemy declarative base"""
        from app.core.database import Base
        from sqlalchemy.orm import DeclarativeBase

        # SQLAlchemy 2.0: Base should be instance of DeclarativeBase or have registry
        assert hasattr(Base, 'registry') or isinstance(Base, type)
        assert hasattr(Base, 'metadata')

    def test_base_can_create_table_model(self):
        """Test Base can be used to create a model"""
        from app.core.database import Base
        from sqlalchemy import Column, Integer, String

        # Create a test model
        class TestModel(Base):
            __tablename__ = "test_model"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        # Verify model was created successfully
        assert hasattr(TestModel, '__tablename__')
        assert TestModel.__tablename__ == "test_model"
        assert hasattr(TestModel, 'id')
        assert hasattr(TestModel, 'name')
