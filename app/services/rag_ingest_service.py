"""Service layer for RAG document ingestion and processing"""

import urllib.parse
import uuid
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.document import Chunk, Datasource, Document, Embedding
from app.services.chunking import ChunkingService
from app.services.openai_service import OpenAIService
from app.services.pdf_service import PDFService
from app.services.storage import StorageService


class RAGIngestService:
    """Service for RAG document ingestion operations"""

    def __init__(self, db: Session):
        self.db = db
        self.openai_service = OpenAIService()
        self.storage_service = StorageService()
        self.pdf_service = PDFService()

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove NUL characters that PostgreSQL cannot store

        Args:
            text: Raw text string

        Returns:
            Cleaned text string
        """
        return text.replace("\x00", "")

    @staticmethod
    def generate_strategy_name(chunk_size: int, overlap: int) -> str:
        """Generate default strategy name from parameters

        Args:
            chunk_size: Size of text chunks
            overlap: Overlap between chunks

        Returns:
            Strategy name in format "rec_{size}_{overlap}"
        """
        return f"rec_{chunk_size}_{overlap}"

    async def upload_and_extract_pdf(
        self, file_content: bytes, filename: str
    ) -> Tuple[str, str, Dict]:
        """Upload PDF to storage and extract text and metadata

        Args:
            file_content: PDF file content bytes
            filename: Original filename

        Returns:
            Tuple of (storage_url, extracted_text, metadata_dict)
        """
        # Upload to Supabase Storage
        file_extension = filename.split(".")[-1] if "." in filename else "pdf"
        safe_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"documents/{safe_filename}"
        storage_url = await self.storage_service.upload_file(
            file_content, file_path, content_type="application/pdf"
        )

        # Extract text and metadata from PDF
        text = self.pdf_service.extract_text(file_content)
        metadata = self.pdf_service.extract_metadata(file_content)

        # Clean text
        text = self.clean_text(text)

        return storage_url, text, metadata

    def create_document_records(
        self,
        storage_url: str,
        filename: str,
        file_content: bytes,
        text: str,
        metadata: Dict,
    ) -> Tuple[Datasource, Document]:
        """Create datasource and document database records

        Args:
            storage_url: URL of file in storage
            filename: Original filename
            file_content: File content bytes (for size calculation)
            text: Extracted text
            metadata: PDF metadata dictionary

        Returns:
            Tuple of (datasource, document)
        """
        datasource = Datasource(type="pdf", source_uri=storage_url)
        self.db.add(datasource)
        self.db.flush()

        document = Document(
            datasource_id=datasource.id,
            title=filename,
            bytes=len(file_content),
            pages=metadata.get("pages", 0),
            content=text,
            text_length=len(text),
            meta_json=metadata,
        )
        self.db.add(document)
        self.db.flush()

        return datasource, document

    async def generate_chunks_and_embeddings(
        self,
        document_id: int,
        text: str,
        chunk_size: int,
        overlap: int,
        chunk_strategy: Optional[str] = None,
    ) -> int:
        """Generate text chunks and embeddings for document

        Args:
            document_id: Document ID to associate chunks with
            text: Text to chunk
            chunk_size: Size of text chunks
            overlap: Overlap between chunks
            chunk_strategy: Optional strategy name (auto-generated if not provided)

        Returns:
            Number of chunks created
        """
        # Generate strategy name if not provided
        if not chunk_strategy:
            chunk_strategy = self.generate_strategy_name(chunk_size, overlap)

        # Chunk the text
        chunking_service = ChunkingService(chunk_size=chunk_size, overlap=overlap)
        chunks = chunking_service.split_text(
            text, split_by_sentence=True, preserve_words=True
        )

        # Generate embeddings and store
        for idx, chunk_text in enumerate(chunks):
            # Clean chunk text
            clean_chunk_text = self.clean_text(chunk_text)

            # Create chunk record
            chunk = Chunk(
                doc_id=document_id,
                chunk_strategy=chunk_strategy,
                ordinal=idx,
                text=clean_chunk_text,
                meta_json={},
            )
            self.db.add(chunk)
            self.db.flush()

            # Generate embedding
            embedding_vector = await self.openai_service.create_embedding(
                clean_chunk_text
            )

            # Create embedding record
            embedding = Embedding(chunk_id=chunk.id, embedding=embedding_vector)
            self.db.add(embedding)

        return len(chunks)

    def get_document_by_id(self, doc_id: int) -> Optional[Document]:
        """Get document by ID

        Args:
            doc_id: Document ID

        Returns:
            Document or None if not found
        """
        result = self.db.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    def get_datasource_by_id(self, datasource_id: int) -> Optional[Datasource]:
        """Get datasource by ID

        Args:
            datasource_id: Datasource ID

        Returns:
            Datasource or None if not found
        """
        result = self.db.execute(
            select(Datasource).where(Datasource.id == datasource_id)
        )
        return result.scalar_one_or_none()

    def delete_document_chunks(self, doc_id: int) -> int:
        """Delete all chunks for a document

        Args:
            doc_id: Document ID

        Returns:
            Number of chunks deleted
        """
        result = self.db.execute(select(Chunk).where(Chunk.doc_id == doc_id))
        old_chunks = result.scalars().all()
        old_chunks_count = len(old_chunks)

        self.db.execute(delete(Chunk).where(Chunk.doc_id == doc_id))
        self.db.flush()

        return old_chunks_count

    async def download_from_storage(self, storage_url: str) -> bytes:
        """Download file from storage using storage URL

        Args:
            storage_url: Full storage URL

        Returns:
            File content bytes
        """
        # Parse URL to extract file path
        parsed_url = urllib.parse.urlparse(storage_url)
        path_parts = parsed_url.path.split("/")

        # Extract path after bucket name
        # URL format: .../storage/v1/object/public/{bucket}/{file_path}
        if "public" in path_parts:
            idx = path_parts.index("public")
            # Skip bucket name (next after 'public') and get the rest
            file_path = "/".join(path_parts[idx + 2 :])
        elif "documents" in path_parts:
            # Find the last occurrence of 'documents' (the bucket name)
            # and take everything after it
            idx = path_parts.index("documents")
            file_path = "/".join(path_parts[idx + 1 :])
        else:
            file_path = path_parts[-1]

        return await self.storage_service.download_file(file_path)

    def check_strategy_exists(self, doc_id: int, strategy_name: str) -> List[Chunk]:
        """Check if a chunking strategy already exists for a document

        Args:
            doc_id: Document ID
            strategy_name: Strategy name to check

        Returns:
            List of existing chunks (empty if strategy doesn't exist)
        """
        result = self.db.execute(
            select(Chunk).where(
                Chunk.doc_id == doc_id, Chunk.chunk_strategy == strategy_name
            )
        )
        return result.scalars().all()

    def update_document_content(self, document: Document, text: str) -> None:
        """Update document with extracted text content

        Args:
            document: Document instance to update
            text: Extracted text content
        """
        document.content = text
        document.text_length = len(text)
        self.db.add(document)
        self.db.flush()
