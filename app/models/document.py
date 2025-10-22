"""RAG Document Models - for PDF ingestion, chunking, and embeddings"""


from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Datasource(Base):
    """Data source for documents (PDF, URL, etc.)"""

    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)  # pdf, url, text
    source_uri = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    documents = relationship("Document", back_populates="datasource", cascade="all, delete-orphan")


class Document(Base):
    """Document metadata and content"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(
        Integer,
        ForeignKey("datasources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    bytes = Column(Integer)
    pages = Column(Integer)
    content = Column(Text, nullable=True)  # Original extracted text content
    text_length = Column(Integer)  # Original extracted text length in characters
    meta_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    datasource = relationship("Datasource", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """Text chunks from documents"""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_strategy = Column(String(100), default="rec_400_80", nullable=False, index=True)  # NEW: chunking strategy tag
    ordinal = Column(Integer, nullable=False)  # Order in document
    text = Column(Text, nullable=False)
    meta_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")
    embedding = relationship(
        "Embedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan"
    )


class Embedding(Base):
    """Vector embeddings for chunks (OpenAI text-embedding-3-small)"""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(
        Integer,
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Using text-embedding-3-small (1536 dimensions)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chunk = relationship("Chunk", back_populates="embedding")
