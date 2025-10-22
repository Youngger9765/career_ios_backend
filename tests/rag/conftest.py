"""Pytest fixtures for RAG tests"""

import pytest
from io import BytesIO

from pypdf import PdfWriter


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file as bytes for testing"""
    # Create a minimal PDF using pypdf
    pdf_writer = PdfWriter()
    pdf_writer.add_blank_page(width=200, height=200)

    pdf_bytes = BytesIO()
    pdf_writer.write(pdf_bytes)
    pdf_bytes.seek(0)

    return pdf_bytes.read()


@pytest.fixture
def sample_multipage_pdf_bytes():
    """Generate a multi-page PDF for testing"""
    pdf_writer = PdfWriter()

    # Add 3 blank pages
    pdf_writer.add_blank_page(width=200, height=200)
    pdf_writer.add_blank_page(width=200, height=200)
    pdf_writer.add_blank_page(width=200, height=200)

    buffer = BytesIO()
    pdf_writer.write(buffer)
    buffer.seek(0)
    return buffer.read()
