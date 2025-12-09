#!/usr/bin/env python3
"""
Test category functionality via API endpoints

This script tests:
1. POST /api/rag/search - Search with category filter
2. Verify category filtering works at API level
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx  # noqa: E402


async def test_category_api():
    """Test category filtering via API"""

    # Use local development server
    base_url = "http://localhost:8000"

    print("=" * 70)
    print("Testing Category API Endpoints")
    print("=" * 70)
    print()

    async with httpx.AsyncClient() as client:
        # Test 1: Search without category (should return all matching docs)
        print("Test 1: Search without category filter")
        print("-" * 70)
        response = await client.post(
            f"{base_url}/api/rag/search/",
            json={
                "query": "如何教養孩子處理情緒",
                "top_k": 3,
                "similarity_threshold": 0.6,
            },
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total results: {data['total_results']}")
            for i, result in enumerate(data["results"], 1):
                print(
                    f"  {i}. {result['document_title']} (score: {result['similarity_score']:.3f})"
                )
        else:
            print(f"Error: {response.text}")
        print()

        # Test 2: Search with category="parenting"
        print("Test 2: Search with category='parenting'")
        print("-" * 70)
        response = await client.post(
            f"{base_url}/api/rag/search/",
            json={
                "query": "如何教養孩子處理情緒",
                "top_k": 3,
                "similarity_threshold": 0.6,
                "category": "parenting",
            },
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total results: {data['total_results']}")
            for i, result in enumerate(data["results"], 1):
                print(
                    f"  {i}. {result['document_title']} (score: {result['similarity_score']:.3f})"
                )
                print(f"     Preview: {result['text'][:80]}...")
        else:
            print(f"Error: {response.text}")
        print()

        # Test 3: Search with category="general" (career counseling docs)
        print("Test 3: Search with category='general' (career docs)")
        print("-" * 70)
        response = await client.post(
            f"{base_url}/api/rag/search/",
            json={
                "query": "職涯興趣探索",
                "top_k": 3,
                "similarity_threshold": 0.6,
                "category": "general",
            },
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total results: {data['total_results']}")
            for i, result in enumerate(data["results"], 1):
                print(
                    f"  {i}. {result['document_title']} (score: {result['similarity_score']:.3f})"
                )
        else:
            print(f"Error: {response.text}")
        print()

        # Test 4: Search with invalid category
        print("Test 4: Search with non-existent category='nonexistent'")
        print("-" * 70)
        response = await client.post(
            f"{base_url}/api/rag/search/",
            json={
                "query": "test query",
                "top_k": 3,
                "similarity_threshold": 0.6,
                "category": "nonexistent",
            },
        )
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Expected error (no results found): {response.status_code}")
        print()

        print("=" * 70)
        print("✅ API category filtering test completed!")
        print("=" * 70)


if __name__ == "__main__":
    print(
        "\n⚠️  Note: Make sure the development server is running on http://localhost:8000"
    )
    print("    Run: poetry run uvicorn app.main:app --reload\n")

    try:
        asyncio.run(test_category_api())
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to development server.")
        print(
            "   Please start the server first: poetry run uvicorn app.main:app --reload\n"
        )
        sys.exit(1)
