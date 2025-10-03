"""PDF processing service for text extraction"""

from io import BytesIO

import PyPDF2


class PDFService:
    """Service for extracting text and metadata from PDF files"""

    def extract_text(self, pdf_bytes: bytes) -> str:
        """
        Extract all text from PDF

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Extracted text as string

        Raises:
            ValueError: If PDF content is empty
        """
        if not pdf_bytes:
            raise ValueError("PDF content cannot be empty")

        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return "\n".join(text_parts)

        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}") from e

    def extract_text_by_page(self, pdf_bytes: bytes) -> list[str]:
        """
        Extract text from PDF page by page

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            List of strings, one per page
        """
        if not pdf_bytes:
            raise ValueError("PDF content cannot be empty")

        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            pages = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                pages.append(text if text else "")

            return pages

        except Exception as e:
            raise Exception(f"Failed to extract text by page: {str(e)}") from e

    def get_page_count(self, pdf_bytes: bytes) -> int:
        """
        Get number of pages in PDF

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Number of pages
        """
        if not pdf_bytes:
            raise ValueError("PDF content cannot be empty")

        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return len(pdf_reader.pages)

        except Exception as e:
            raise Exception(f"Failed to get page count: {str(e)}") from e

    def extract_metadata(self, pdf_bytes: bytes) -> dict:
        """
        Extract metadata from PDF

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Dictionary containing metadata
        """
        if not pdf_bytes:
            raise ValueError("PDF content cannot be empty")

        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            metadata = {
                "pages": len(pdf_reader.pages),
                "title": None,
                "author": None,
                "subject": None,
                "creator": None,
            }

            # Extract metadata if available
            if pdf_reader.metadata:
                metadata["title"] = pdf_reader.metadata.get("/Title")
                metadata["author"] = pdf_reader.metadata.get("/Author")
                metadata["subject"] = pdf_reader.metadata.get("/Subject")
                metadata["creator"] = pdf_reader.metadata.get("/Creator")

            return metadata

        except Exception as e:
            raise Exception(f"Failed to extract metadata: {str(e)}") from e
