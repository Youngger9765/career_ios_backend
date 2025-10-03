from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    items = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan"
    )


class CollectionItem(Base):
    __tablename__ = "collection_items"

    collection_id = Column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    doc_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="items")
