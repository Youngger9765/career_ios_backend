"""API endpoints for database statistics"""

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/rag/stats", tags=["rag-stats"])


class DocumentStats(BaseModel):
    id: int
    title: str
    pages: int
    bytes: int
    chunk_strategy: str  # Strategy name like "rec_400_80"
    chunk_size: int  # Extracted from strategy
    overlap: int  # Extracted from strategy
    chunks_count: int
    embeddings_count: int
    text_length: int  # Original extracted text length
    total_text_chars: int  # Sum of all chunk text lengths
    created_at: str


class DatabaseStats(BaseModel):
    total_datasources: int
    total_documents: int
    total_chunks: int
    total_embeddings: int
    total_bytes: int
    documents: List[DocumentStats]


@router.get("/", response_model=DatabaseStats)
def get_database_stats(db: Session = Depends(get_db)):
    """
    Get database statistics including counts and document details

    Returns:
        DatabaseStats with all statistics
    """

    # Get total counts
    datasources_count = db.execute(text("SELECT COUNT(*) FROM datasources")).scalar()
    documents_count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
    chunks_count = db.execute(text("SELECT COUNT(*) FROM chunks")).scalar()
    embeddings_count = db.execute(text("SELECT COUNT(*) FROM embeddings")).scalar()
    total_bytes = db.execute(
        text("SELECT COALESCE(SUM(bytes), 0) FROM documents")
    ).scalar()

    # Get document details grouped by chunk strategy
    query = text(
        """
        SELECT
            d.id,
            d.title,
            d.pages,
            d.bytes,
            d.text_length,
            d.created_at,
            COALESCE(c.chunk_strategy, 'no_chunks') as chunk_strategy,
            COUNT(c.id) as chunks_count,
            COUNT(e.id) as embeddings_count,
            COALESCE(SUM(LENGTH(c.text)), 0) as total_text_chars
        FROM documents d
        LEFT JOIN chunks c ON d.id = c.doc_id
        LEFT JOIN embeddings e ON c.id = e.chunk_id
        GROUP BY d.id, d.title, d.pages, d.bytes, d.text_length, d.created_at, c.chunk_strategy
        ORDER BY d.created_at DESC, c.chunk_strategy
    """
    )

    result = db.execute(query)
    rows = result.fetchall()

    def parse_strategy(strategy_name: str) -> tuple[int, int]:
        """Parse chunk_strategy like 'rec_400_80' to (chunk_size, overlap)"""
        if strategy_name == "no_chunks":
            return (0, 0)
        try:
            parts = strategy_name.split("_")
            if len(parts) >= 3:
                return (int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass
        return (0, 0)

    documents = [
        DocumentStats(
            id=row.id,
            title=row.title,
            pages=row.pages or 0,
            bytes=row.bytes or 0,
            chunk_strategy=row.chunk_strategy,
            chunk_size=parse_strategy(row.chunk_strategy)[0],
            overlap=parse_strategy(row.chunk_strategy)[1],
            chunks_count=row.chunks_count or 0,
            embeddings_count=row.embeddings_count or 0,
            text_length=row.text_length or 0,
            total_text_chars=row.total_text_chars or 0,
            created_at=str(row.created_at),
        )
        for row in rows
    ]

    return DatabaseStats(
        total_datasources=datasources_count or 0,
        total_documents=documents_count or 0,
        total_chunks=chunks_count or 0,
        total_embeddings=embeddings_count or 0,
        total_bytes=total_bytes or 0,
        documents=documents,
    )


class ChunkDetail(BaseModel):
    id: int
    ordinal: int
    text: str
    text_length: int
    document_title: str


@router.get("/chunks/{doc_id}", response_model=List[ChunkDetail])
def get_document_chunks(doc_id: int, db: Session = Depends(get_db)):
    """
    Get all chunks for a specific document

    Args:
        doc_id: Document ID

    Returns:
        List of chunks with details
    """

    query = text(
        """
        SELECT
            c.id,
            c.ordinal,
            c.text,
            LENGTH(c.text) as text_length,
            d.title as document_title
        FROM chunks c
        JOIN documents d ON c.doc_id = d.id
        WHERE c.doc_id = :doc_id
        ORDER BY c.ordinal
    """
    )

    result = db.execute(query, {"doc_id": doc_id})
    rows = result.fetchall()

    return [
        ChunkDetail(
            id=row.id,
            ordinal=row.ordinal,
            text=row.text,
            text_length=row.text_length,
            document_title=row.document_title,
        )
        for row in rows
    ]


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """
    Delete a document and all its related chunks and embeddings

    This will cascade delete:
    - All chunks associated with the document
    - All embeddings associated with those chunks
    - The document itself

    Args:
        doc_id: Document ID to delete

    Returns:
        Success message with deletion counts
    """

    # Get chunk count before deletion
    chunks_result = db.execute(
        text("SELECT COUNT(*) FROM chunks WHERE doc_id = :doc_id"), {"doc_id": doc_id}
    )
    chunks_count = chunks_result.scalar() or 0

    # Get embeddings count before deletion
    embeddings_result = db.execute(
        text(
            """
            SELECT COUNT(*) FROM embeddings
            WHERE chunk_id IN (SELECT id FROM chunks WHERE doc_id = :doc_id)
        """
        ),
        {"doc_id": doc_id},
    )
    embeddings_count = embeddings_result.scalar() or 0

    # Delete embeddings first (FK constraint)
    db.execute(
        text(
            """
            DELETE FROM embeddings
            WHERE chunk_id IN (SELECT id FROM chunks WHERE doc_id = :doc_id)
        """
        ),
        {"doc_id": doc_id},
    )

    # Delete chunks
    db.execute(text("DELETE FROM chunks WHERE doc_id = :doc_id"), {"doc_id": doc_id})

    # Delete document
    db.execute(text("DELETE FROM documents WHERE id = :doc_id"), {"doc_id": doc_id})

    db.commit()

    return {
        "success": True,
        "message": f"成功刪除文檔 ID {doc_id}",
        "deleted": {
            "document": 1,
            "chunks": chunks_count,
            "embeddings": embeddings_count,
        },
    }
