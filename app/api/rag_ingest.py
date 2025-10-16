"""API endpoints for RAG document ingestion and processing"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Chunk, Datasource, Document, Embedding
from app.services.chunking import ChunkingService
from app.services.openai_service import OpenAIService
from app.services.pdf_service import PDFService
from app.services.storage import StorageService

router = APIRouter(prefix="/api/rag/ingest", tags=["rag-ingest"])


class IngestResponse(BaseModel):
    datasource_id: int
    document_id: int
    chunks_created: int
    embeddings_created: int
    message: str


@router.post("/files", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    chunk_size: int = 400,
    overlap: int = 80,
    chunk_strategy: str = None,  # NEW: optional strategy name
    db: Session = Depends(get_db),
):
    """
    Upload and process a PDF file:
    1. Upload to Supabase Storage
    2. Extract text from PDF
    3. Chunk the text
    4. Generate embeddings
    5. Store in database

    Args:
        file: PDF file to upload
        chunk_size: Size of text chunks
        overlap: Overlap between chunks
        db: Database session

    Returns:
        IngestResponse with processing details
    """

    # Validate file type
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Read file content
        file_content = await file.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # 1. Upload to Supabase Storage
        storage_service = StorageService()
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "pdf"
        safe_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"documents/{safe_filename}"
        storage_url = await storage_service.upload_file(
            file_content, file_path, content_type="application/pdf"
        )

        # 2. Extract text from PDF
        pdf_service = PDFService()
        text = pdf_service.extract_text(file_content)
        metadata = pdf_service.extract_metadata(file_content)

        # Remove NUL characters that PostgreSQL cannot store
        text = text.replace('\x00', '')

        # 3. Create datasource and document records
        datasource = Datasource(type="pdf", source_uri=storage_url)
        db.add(datasource)
        db.flush()

        document = Document(
            datasource_id=datasource.id,
            title=file.filename,
            bytes=len(file_content),
            pages=metadata.get("pages", 0),
            content=text,  # Save original extracted text
            text_length=len(text),  # Save original text length
            meta_json=metadata,
        )
        db.add(document)
        db.flush()

        # 4. Chunk the text
        chunking_service = ChunkingService(chunk_size=chunk_size, overlap=overlap)
        chunks = chunking_service.split_text(text, split_by_sentence=True, preserve_words=True)

        # Generate strategy name if not provided
        if not chunk_strategy:
            chunk_strategy = f"rec_{chunk_size}_{overlap}"

        # 5. Generate embeddings and store
        openai_service = OpenAIService()

        for idx, chunk_text in enumerate(chunks):
            # Remove NUL characters from chunk text
            clean_chunk_text = chunk_text.replace('\x00', '')

            # Create chunk record with strategy tag
            chunk = Chunk(
                doc_id=document.id,
                chunk_strategy=chunk_strategy,
                ordinal=idx,
                text=clean_chunk_text,
                meta_json={}
            )
            db.add(chunk)
            db.flush()

            # Generate embedding
            embedding_vector = await openai_service.create_embedding(clean_chunk_text)

            # Create embedding record
            embedding = Embedding(chunk_id=chunk.id, embedding=embedding_vector)
            db.add(embedding)

        db.commit()

        return IngestResponse(
            datasource_id=datasource.id,
            document_id=document.id,
            chunks_created=len(chunks),
            embeddings_created=len(chunks),
            message=f"Successfully processed {file.filename}",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}") from e


# Also add a simpler endpoint for the frontend at /api/rag/ingest
@router.post("", response_model=IngestResponse)
async def ingest_file_simple(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Simplified upload endpoint for frontend compatibility"""
    return await ingest_file(file=file, chunk_size=400, overlap=80, db=db)


class ReprocessRequest(BaseModel):
    chunk_size: int = 400
    overlap: int = 80


class ReprocessResponse(BaseModel):
    document_id: int
    old_chunks_deleted: int
    new_chunks_created: int
    new_embeddings_created: int
    message: str


@router.post("/reprocess/{doc_id}", response_model=ReprocessResponse)
async def reprocess_document(
    doc_id: int, request: ReprocessRequest, db: Session = Depends(get_db)
):
    """
    Reprocess an existing document with new chunking parameters

    Args:
        doc_id: Document ID to reprocess
        request: New chunking parameters
        db: Database session

    Returns:
        ReprocessResponse with reprocessing details
    """
    try:
        # 1. Get document
        result = db.execute(select(Document).where(Document.id == doc_id))
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        # Get datasource for storage URL
        result = db.execute(select(Datasource).where(Datasource.id == document.datasource_id))
        datasource = result.scalar_one_or_none()

        if not datasource or not datasource.source_uri:
            raise HTTPException(status_code=404, detail="Document source not found")

        # 2. Download original PDF from storage
        storage_service = StorageService()
        import urllib.parse

        parsed_url = urllib.parse.urlparse(datasource.source_uri)
        # Extract path after bucket name
        # URL format: .../storage/v1/object/public/{bucket}/{file_path}
        path_parts = parsed_url.path.split("/")

        # Find 'public' or bucket name and get everything after it
        if "public" in path_parts:
            idx = path_parts.index("public")
            # Skip bucket name (next after 'public') and get the rest
            file_path = "/".join(path_parts[idx + 2:])
        elif "documents" in path_parts:
            # Find the last occurrence of 'documents' (the bucket name)
            # and take everything after it
            idx = path_parts.index("documents")
            file_path = "/".join(path_parts[idx + 1:])
        else:
            file_path = path_parts[-1]

        file_content = await storage_service.download_file(file_path)

        # 3. Count and delete old chunks
        result = db.execute(select(Chunk).where(Chunk.doc_id == doc_id))
        old_chunks = result.scalars().all()
        old_chunks_count = len(old_chunks)

        db.execute(delete(Chunk).where(Chunk.doc_id == doc_id))
        db.flush()

        # 4. Extract text from PDF
        pdf_service = PDFService()
        text = pdf_service.extract_text(file_content)

        # Update document with content and text_length
        document.content = text
        document.text_length = len(text)
        db.add(document)
        db.flush()

        # 5. Re-chunk with new parameters
        chunking_service = ChunkingService(chunk_size=request.chunk_size, overlap=request.overlap)
        chunks = chunking_service.split_text(text, split_by_sentence=True, preserve_words=True)

        # 6. Generate new embeddings and store
        openai_service = OpenAIService()

        for idx, chunk_text in enumerate(chunks):
            # Remove NUL characters from chunk text
            clean_chunk_text = chunk_text.replace('\x00', '')

            # Create chunk record
            chunk = Chunk(doc_id=document.id, ordinal=idx, text=clean_chunk_text, meta_json={})
            db.add(chunk)
            db.flush()

            # Generate embedding
            embedding_vector = await openai_service.create_embedding(clean_chunk_text)

            # Create embedding record
            embedding = Embedding(chunk_id=chunk.id, embedding=embedding_vector)
            db.add(embedding)

        db.commit()

        return ReprocessResponse(
            document_id=doc_id,
            old_chunks_deleted=old_chunks_count,
            new_chunks_created=len(chunks),
            new_embeddings_created=len(chunks),
            message=f"Successfully reprocessed {document.title} with chunk_size={request.chunk_size}",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to reprocess document: {str(e)}"
        ) from e


class GenerateStrategyRequest(BaseModel):
    chunk_size: int = 400
    overlap: int = 80
    chunk_strategy: Optional[str] = None  # If not provided, will be auto-generated


class GenerateStrategyResponse(BaseModel):
    document_id: int
    strategy_name: str
    chunks_created: int
    embeddings_created: int
    message: str


@router.post("/generate_strategy/{doc_id}", response_model=GenerateStrategyResponse)
async def generate_strategy_for_document(
    doc_id: int, request: GenerateStrategyRequest, db: Session = Depends(get_db)
):
    """
    Generate chunks for a specific strategy without deleting existing chunks

    Args:
        doc_id: Document ID to process
        request: Chunking parameters and optional strategy name
        db: Database session

    Returns:
        GenerateStrategyResponse with generation details
    """
    try:
        # 1. Get document
        result = db.execute(select(Document).where(Document.id == doc_id))
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        if not document.content:
            raise HTTPException(status_code=400, detail="Document has no content to chunk")

        # 2. Generate strategy name if not provided
        strategy_name = request.chunk_strategy
        if not strategy_name:
            strategy_name = f"rec_{request.chunk_size}_{request.overlap}"

        # 3. Check if this strategy already exists for this document
        result = db.execute(
            select(Chunk).where(
                Chunk.doc_id == doc_id, Chunk.chunk_strategy == strategy_name
            )
        )
        existing_chunks = result.scalars().all()

        if existing_chunks:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy '{strategy_name}' already exists for document {doc_id} with {len(existing_chunks)} chunks",
            )

        # 4. Chunk the text
        chunking_service = ChunkingService(chunk_size=request.chunk_size, overlap=request.overlap)
        chunks = chunking_service.split_text(
            document.content, split_by_sentence=True, preserve_words=True
        )

        # 5. Generate embeddings and store
        openai_service = OpenAIService()

        for idx, chunk_text in enumerate(chunks):
            # Remove NUL characters from chunk text
            clean_chunk_text = chunk_text.replace('\x00', '')

            # Create chunk record
            chunk = Chunk(
                doc_id=document.id,
                chunk_strategy=strategy_name,
                ordinal=idx,
                text=clean_chunk_text,
                meta_json={},
            )
            db.add(chunk)
            db.flush()

            # Generate embedding
            embedding_vector = await openai_service.create_embedding(clean_chunk_text)

            # Create embedding record
            embedding = Embedding(chunk_id=chunk.id, embedding=embedding_vector)
            db.add(embedding)

        db.commit()

        return GenerateStrategyResponse(
            document_id=doc_id,
            strategy_name=strategy_name,
            chunks_created=len(chunks),
            embeddings_created=len(chunks),
            message=f"Successfully generated {len(chunks)} chunks for strategy '{strategy_name}'",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate strategy: {str(e)}"
        ) from e
