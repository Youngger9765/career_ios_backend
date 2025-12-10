"""
Reprocess all documents with new chunk parameters

This script will:
1. Fetch all document IDs from the database
2. Call the reprocess API endpoint for each document
3. Report progress and results
"""

import asyncio
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import async_session  # noqa: E402
from app.models.document import Document  # noqa: E402


async def get_all_document_ids() -> list[tuple[int, str]]:
    """Get all document IDs from database"""
    async with async_session() as session:
        result = await session.execute(select(Document.id, Document.title))
        docs = result.all()
        return list(docs)


async def reprocess_document(
    doc_id: int, chunk_size: int = 400, overlap: int = 80
) -> dict:
    """Call reprocess API for a single document"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"http://localhost:8000/api/ingest/reprocess/{doc_id}",
            json={"chunk_size": chunk_size, "overlap": overlap},
        )

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False,
                "error": f"{response.status_code}: {response.text}",
            }


async def main():
    print("🔄 Reprocessing All Documents with New Chunk Parameters")
    print("=" * 80)
    print("   New chunk_size: 400")
    print("   New overlap: 80")
    print("=" * 80)

    # Get all documents
    print("\n📋 Fetching document list...")
    docs = await get_all_document_ids()

    if not docs:
        print("⚠️  No documents found in database")
        return

    print(f"✅ Found {len(docs)} documents\n")

    # Reprocess each document
    results = []
    for i, (doc_id, title) in enumerate(docs, 1):
        print(f"[{i}/{len(docs)}] Processing: {title} (ID: {doc_id})")

        try:
            result = await reprocess_document(doc_id)

            if result["success"]:
                data = result["data"]
                print("   ✅ Success!")
                print(f"      Old chunks: {data['old_chunks_deleted']}")
                print(f"      New chunks: {data['new_chunks_created']}")
                print(f"      Embeddings: {data['new_embeddings_created']}")
                results.append(
                    {"doc_id": doc_id, "title": title, "success": True, "data": data}
                )
            else:
                print(f"   ❌ Failed: {result['error']}")
                results.append(
                    {
                        "doc_id": doc_id,
                        "title": title,
                        "success": False,
                        "error": result["error"],
                    }
                )

        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            results.append(
                {"doc_id": doc_id, "title": title, "success": False, "error": str(e)}
            )

        print()

    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful

    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    if successful > 0:
        total_old_chunks = sum(
            r["data"]["old_chunks_deleted"] for r in results if r["success"]
        )
        total_new_chunks = sum(
            r["data"]["new_chunks_created"] for r in results if r["success"]
        )
        print(f"\n📈 Total old chunks deleted: {total_old_chunks}")
        print(f"📈 Total new chunks created: {total_new_chunks}")
        increase = total_new_chunks - total_old_chunks
        percent = (total_new_chunks / total_old_chunks - 1) * 100
        print(f"📈 Chunk increase: {increase:+d} ({percent:.1f}%)")

    if failed > 0:
        print("\n❌ Failed documents:")
        for r in results:
            if not r["success"]:
                print(f"   - {r['title']} (ID: {r['doc_id']}): {r['error']}")


if __name__ == "__main__":
    asyncio.run(main())
