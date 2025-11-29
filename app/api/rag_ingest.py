"""API endpoints for RAG document ingestion and processing"""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.rag_ingest_service import RAGIngestService

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
        service = RAGIngestService(db)

        # Read file content
        file_content = await file.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Upload and extract PDF
        storage_url, text, metadata = await service.upload_and_extract_pdf(
            file_content, file.filename
        )

        # Create document records
        datasource, document = service.create_document_records(
            storage_url, file.filename, file_content, text, metadata
        )

        # Generate chunks and embeddings
        chunks_created = await service.generate_chunks_and_embeddings(
            document.id, text, chunk_size, overlap, chunk_strategy
        )

        db.commit()

        return IngestResponse(
            datasource_id=datasource.id,
            document_id=document.id,
            chunks_created=chunks_created,
            embeddings_created=chunks_created,
            message=f"Successfully processed {file.filename}",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to process file: {str(e)}"
        ) from e


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
        service = RAGIngestService(db)

        # Get document
        document = service.get_document_by_id(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        # Get datasource for storage URL
        datasource = service.get_datasource_by_id(document.datasource_id)
        if not datasource or not datasource.source_uri:  # type: ignore[attr-defined]
            raise HTTPException(status_code=404, detail="Document source not found")

        # Download original PDF from storage
        file_content = await service.download_from_storage(
            datasource.source_uri  # type: ignore[attr-defined]
        )

        # Count and delete old chunks
        old_chunks_count = service.delete_document_chunks(doc_id)

        # Extract text from PDF
        text = service.pdf_service.extract_text(file_content)
        text = service.clean_text(text)

        # Update document with content
        service.update_document_content(document, text)

        # Generate new chunks and embeddings
        chunks_created = await service.generate_chunks_and_embeddings(
            document.id, text, request.chunk_size, request.overlap
        )

        db.commit()

        return ReprocessResponse(
            document_id=doc_id,
            old_chunks_deleted=old_chunks_count,
            new_chunks_created=chunks_created,
            new_embeddings_created=chunks_created,
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
        service = RAGIngestService(db)

        # Get document
        document = service.get_document_by_id(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        if not document.content:
            raise HTTPException(
                status_code=400, detail="Document has no content to chunk"
            )

        # Generate strategy name if not provided
        strategy_name = request.chunk_strategy
        if not strategy_name:
            strategy_name = service.generate_strategy_name(
                request.chunk_size, request.overlap
            )

        # Check if strategy already exists
        existing_chunks = service.check_strategy_exists(doc_id, strategy_name)
        if existing_chunks:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy '{strategy_name}' already exists for document {doc_id} with {len(existing_chunks)} chunks",
            )

        # Generate chunks and embeddings
        chunks_created = await service.generate_chunks_and_embeddings(
            document.id,
            document.content,
            request.chunk_size,
            request.overlap,
            strategy_name,
        )

        db.commit()

        return GenerateStrategyResponse(
            document_id=doc_id,
            strategy_name=strategy_name,
            chunks_created=chunks_created,
            embeddings_created=chunks_created,
            message=f"Successfully generated {chunks_created} chunks for strategy '{strategy_name}'",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate strategy: {str(e)}"
        ) from e
