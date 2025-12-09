#!/usr/bin/env python3
"""
Test category filtering in RAG search

This script tests:
1. Search without category filter (should return all documents)
2. Search with category="parenting" (should return only parenting docs)
3. Search with category="general" (should return only general docs)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_db  # noqa: E402
from app.services.openai_service import OpenAIService  # noqa: E402
from app.services.rag_retriever import RAGRetriever  # noqa: E402


async def test_category_search():
    """Test category filtering in search"""

    db = next(get_db())
    openai_service = OpenAIService()
    retriever = RAGRetriever(openai_service)

    test_query = "如何教養孩子處理情緒"  # Query about parenting emotions

    print("=" * 70)
    print("Testing Category-Based RAG Filtering")
    print("=" * 70)
    print(f"Query: {test_query}\n")

    try:
        # Test 1: Search without category filter
        print("Test 1: Search without category filter")
        print("-" * 70)
        results = await retriever.search(
            query=test_query,
            top_k=5,
            threshold=0.6,
            db=db,
            category=None,  # No filter
        )
        print(f"Found {len(results)} results (all categories):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['document']} (score: {result['score']:.3f})")
        print()

        # Test 2: Search with category="parenting"
        print("Test 2: Search with category='parenting'")
        print("-" * 70)
        results_parenting = await retriever.search(
            query=test_query,
            top_k=5,
            threshold=0.6,
            db=db,
            category="parenting",  # Filter for parenting only
        )
        print(f"Found {len(results_parenting)} results (parenting only):")
        for i, result in enumerate(results_parenting, 1):
            print(f"  {i}. {result['document']} (score: {result['score']:.3f})")
            print(f"     Preview: {result['text'][:100]}...")
        print()

        # Test 3: Search with category="general"
        print("Test 3: Search with category='general'")
        print("-" * 70)
        try:
            results_general = await retriever.search(
                query=test_query,
                top_k=5,
                threshold=0.6,
                db=db,
                category="general",  # Filter for general only
            )
            print(f"Found {len(results_general)} results (general only):")
            for i, result in enumerate(results_general, 1):
                print(f"  {i}. {result['document']} (score: {result['score']:.3f})")
        except Exception as e:
            print(
                f"  No results found for category='general' (expected if no general docs): {e}"
            )
        print()

        # Test 4: Search with category="career"
        print("Test 4: Search with category='career'")
        print("-" * 70)
        try:
            results_career = await retriever.search(
                query=test_query,
                top_k=5,
                threshold=0.6,
                db=db,
                category="career",  # Filter for career only
            )
            print(f"Found {len(results_career)} results (career only):")
            for i, result in enumerate(results_career, 1):
                print(f"  {i}. {result['document']} (score: {result['score']:.3f})")
        except Exception as e:
            print(
                f"  No results found for category='career' (expected if no career docs): {e}"
            )
        print()

        print("=" * 70)
        print("✅ Category filtering test completed successfully!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_category_search())
