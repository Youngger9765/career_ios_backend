#!/usr/bin/env python3
"""
Upload parenting theory documents to RAG system with category='parenting'

This script:
1. Reads all markdown files from docs/rag_knowledge/parenting_theories/
2. Uploads them to RAG system with category="parenting"
3. Generates chunks and embeddings for vector search
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_db  # noqa: E402
from app.services.rag_ingest_service import RAGIngestService  # noqa: E402


async def upload_parenting_theories():
    """Batch upload parenting theory markdown files"""

    theories_dir = project_root / "docs/rag_knowledge/parenting_theories"
    md_files = list(theories_dir.glob("*.md"))

    # Exclude helper files (starting with _ or README)
    md_files = [
        f for f in md_files if not f.name.startswith("_") and f.name != "README.md"
    ]

    print(f"Found {len(md_files)} parenting theory files to upload:")
    for f in md_files:
        print(f"  - {f.name}")
    print()

    # Get database session
    db = next(get_db())

    try:
        service = RAGIngestService(db)
        uploaded_count = 0

        for md_file in md_files:
            print(f"Processing: {md_file.name}")

            # Read markdown file
            with open(md_file, "rb") as f:
                content = f.read()

            try:
                # For markdown files, decode and use text directly
                text = content.decode("utf-8")
                text = service.clean_text(text)

                # Upload to storage
                import uuid

                safe_filename = f"{uuid.uuid4()}.md"
                file_path = f"documents/{safe_filename}"
                storage_url = await service.storage_service.upload_file(
                    content, file_path, content_type="text/markdown"
                )

                # Create metadata
                metadata = {
                    "pages": 1,  # Markdown files don't have pages
                    "title": md_file.stem,
                    "format": "markdown",
                }

                # Create document records with category="parenting"
                datasource, document = service.create_document_records(
                    storage_url=storage_url,
                    filename=md_file.name,
                    file_content=content,
                    text=text,
                    metadata=metadata,
                    category="parenting",  # 👈 Tag as parenting category
                )

                # Generate chunks and embeddings
                chunks_created = await service.generate_chunks_and_embeddings(
                    document_id=document.id,
                    text=text,
                    chunk_size=1000,  # Larger chunks for theory documents
                    overlap=200,
                )

                db.commit()

                print(
                    f"  ✅ Uploaded: {md_file.name} "
                    f"(Document ID: {document.id}, Chunks: {chunks_created})"
                )
                uploaded_count += 1

            except Exception as e:
                print(f"  ❌ Failed to upload {md_file.name}: {e}")
                db.rollback()
                continue

        print(f"\n{'='*60}")
        print(f"Upload complete: {uploaded_count}/{len(md_files)} files uploaded")
        print("Category: parenting")
        print(f"{'='*60}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(upload_parenting_theories())
