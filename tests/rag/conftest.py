"""Pytest configuration and shared fixtures"""

from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@pytest.fixture
def mock_embedding_response():
    """Mock OpenAI embedding response"""
    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "embedding": [0.1] * 1536,  # Mock 1536-dim vector
                "index": 0,
            }
        ],
        "model": "text-embedding-3-small",
        "usage": {"prompt_tokens": 8, "total_tokens": 8},
    }


@pytest.fixture
async def client() -> AsyncGenerator:
    """HTTP client for testing FastAPI endpoints"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_pdf_content():
    """Sample PDF text content for testing"""
    return """
    This is a sample PDF document for testing.
    It contains multiple paragraphs of text.

    This is the second paragraph with some important information.
    We will use this to test chunking and embedding functionality.

    The third paragraph contains more details about the test data.
    This should be enough content to create multiple chunks.
    """


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file as bytes for testing"""
    # Create a minimal PDF using PyPDF2
    from io import BytesIO

    from PyPDF2 import PdfWriter

    pdf_writer = PdfWriter()
    pdf_writer.add_blank_page(width=200, height=200)

    pdf_bytes = BytesIO()
    pdf_writer.write(pdf_bytes)
    pdf_bytes.seek(0)

    return pdf_bytes.read()
