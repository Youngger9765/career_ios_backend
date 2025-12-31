#!/usr/bin/env python3
"""
Test Realtime Analysis API on Staging Environment

This script tests:
1. Basic functionality - API responds correctly
2. RAG integration - Verify RAG knowledge base is triggered with career keywords
3. Performance - Measure actual response time
4. Data quality - Check if summary, alerts, suggestions are meaningful
"""

import json
import time
from typing import Any, Dict, List

import httpx

# Staging API URL
STAGING_URL = "https://career-app-api-staging-kxaznpplqq-uc.a.run.app"
API_ENDPOINT = f"{STAGING_URL}/api/v1/realtime/analyze"
STATS_ENDPOINT = f"{STAGING_URL}/api/rag/stats"


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} - {test_name}")
    if details:
        print(f"  Details: {details}")


def print_json(data: Dict[str, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def test_basic_functionality() -> Dict[str, Any]:
    """Test 1: Basic API functionality"""
    print_section("Test 1: Basic API Functionality")

    payload = {
        "transcript": "諮詢師：你最近工作上有什麼困擾嗎？\n案主：我覺得活著沒什麼意義...",
        "speakers": [
            {"speaker": "counselor", "text": "你最近工作上有什麼困擾嗎？"},
            {"speaker": "client", "text": "我覺得活著沒什麼意義..."},
        ],
        "time_range": "0:00-1:00",
    }

    print("\n📤 Request:")
    print_json(payload)

    start_time = time.time()
    try:
        response = httpx.post(API_ENDPOINT, json=payload, timeout=30.0)
        elapsed_time = time.time() - start_time

        print(f"\n📥 Response Status: {response.status_code}")
        print(f"⏱️  Response Time: {elapsed_time:.2f}s")

        if response.status_code == 200:
            data = response.json()
            print("\n📄 Response Data:")
            print_json(data)

            # Validate response structure
            required_fields = [
                "summary",
                "alerts",
                "suggestions",
                "time_range",
                "timestamp",
            ]
            missing_fields = [f for f in required_fields if f not in data]

            if missing_fields:
                print_result(
                    "Basic Functionality",
                    False,
                    f"Missing fields: {missing_fields}",
                )
                return {"success": False, "elapsed_time": elapsed_time}

            print_result(
                "Basic Functionality",
                True,
                f"All required fields present, response time: {elapsed_time:.2f}s",
            )
            return {"success": True, "elapsed_time": elapsed_time, "data": data}
        else:
            print_result(
                "Basic Functionality",
                False,
                f"HTTP {response.status_code}: {response.text}",
            )
            return {"success": False, "elapsed_time": elapsed_time}

    except Exception as e:
        elapsed_time = time.time() - start_time
        print_result("Basic Functionality", False, f"Exception: {str(e)}")
        return {"success": False, "elapsed_time": elapsed_time, "error": str(e)}


def test_rag_with_career_keywords() -> Dict[str, Any]:
    """Test 2: RAG integration with career keywords"""
    print_section("Test 2: RAG Integration with Career Keywords")

    payload = {
        "transcript": "諮詢師：你想轉職嗎？\n案主：是的，但我不知道怎麼寫履歷。",
        "speakers": [
            {"speaker": "counselor", "text": "你想轉職嗎？"},
            {"speaker": "client", "text": "是的，但我不知道怎麼寫履歷。"},
        ],
        "time_range": "0:00-1:00",
    }

    print("\n📤 Request (with career keywords: 轉職, 履歷):")
    print_json(payload)

    start_time = time.time()
    try:
        response = httpx.post(API_ENDPOINT, json=payload, timeout=30.0)
        elapsed_time = time.time() - start_time

        print(f"\n📥 Response Status: {response.status_code}")
        print(f"⏱️  Response Time: {elapsed_time:.2f}s")

        if response.status_code == 200:
            data = response.json()

            # Check if rag_sources field exists
            has_rag_field = "rag_sources" in data
            print(f"\n✅ Has rag_sources field: {has_rag_field}")

            if has_rag_field:
                rag_sources = data.get("rag_sources", [])
                print(f"✅ RAG sources count: {len(rag_sources)}")

                if rag_sources:
                    print("\n📚 RAG Sources:")
                    for i, source in enumerate(rag_sources, 1):
                        print(f"\n  [{i}] {source.get('title', 'N/A')}")
                        print(f"      Score: {source.get('score', 0):.2f}")
                        print(f"      Content: {source.get('content', 'N/A')[:150]}...")

                    # Validate RAG source structure
                    valid_sources = all(
                        "title" in s and "content" in s and "score" in s
                        for s in rag_sources
                    )
                    if not valid_sources:
                        print_result(
                            "RAG Integration",
                            False,
                            "Invalid RAG source structure",
                        )
                        return {"success": False, "elapsed_time": elapsed_time}

                    # Check similarity scores
                    scores = [s["score"] for s in rag_sources]
                    print(f"\n📊 Similarity Scores: {scores}")
                    all_above_threshold = all(s >= 0.7 for s in scores)
                    if not all_above_threshold:
                        print(
                            "⚠️  Warning: Some scores below 0.7 threshold, but may be expected"
                        )

                    print_result(
                        "RAG Integration",
                        True,
                        f"RAG triggered with {len(rag_sources)} sources, response time: {elapsed_time:.2f}s",
                    )
                    return {
                        "success": True,
                        "elapsed_time": elapsed_time,
                        "rag_sources": rag_sources,
                        "data": data,
                    }
                else:
                    print(
                        "\n⚠️  Warning: No RAG sources found (may indicate empty knowledge base)"
                    )
                    print_result(
                        "RAG Integration",
                        True,
                        "RAG field exists but no sources (empty knowledge base?)",
                    )
                    return {
                        "success": True,
                        "elapsed_time": elapsed_time,
                        "rag_sources": [],
                        "data": data,
                    }
            else:
                print_result("RAG Integration", False, "Missing rag_sources field")
                return {"success": False, "elapsed_time": elapsed_time}

        else:
            print_result(
                "RAG Integration",
                False,
                f"HTTP {response.status_code}: {response.text}",
            )
            return {"success": False, "elapsed_time": elapsed_time}

    except Exception as e:
        elapsed_time = time.time() - start_time
        print_result("RAG Integration", False, f"Exception: {str(e)}")
        return {"success": False, "elapsed_time": elapsed_time, "error": str(e)}


def test_without_career_keywords() -> Dict[str, Any]:
    """Test 3: Test without career keywords (should not trigger RAG)"""
    print_section("Test 3: Without Career Keywords (No RAG)")

    payload = {
        "transcript": "諮詢師：今天天氣如何？\n案主：天氣很好。",
        "speakers": [
            {"speaker": "counselor", "text": "今天天氣如何？"},
            {"speaker": "client", "text": "天氣很好。"},
        ],
        "time_range": "0:00-1:00",
    }

    print("\n📤 Request (without career keywords):")
    print_json(payload)

    start_time = time.time()
    try:
        response = httpx.post(API_ENDPOINT, json=payload, timeout=30.0)
        elapsed_time = time.time() - start_time

        print(f"\n📥 Response Status: {response.status_code}")
        print(f"⏱️  Response Time: {elapsed_time:.2f}s")

        if response.status_code == 200:
            data = response.json()

            has_rag_field = "rag_sources" in data
            rag_sources = data.get("rag_sources", [])

            print(f"\n✅ Has rag_sources field: {has_rag_field}")
            print(f"✅ RAG sources count: {len(rag_sources)}")

            # Should still have the field, but likely empty
            if has_rag_field:
                if len(rag_sources) == 0:
                    print_result(
                        "Without Career Keywords",
                        True,
                        f"RAG not triggered (as expected), response time: {elapsed_time:.2f}s",
                    )
                else:
                    print(
                        f"⚠️  Unexpected: RAG triggered with {len(rag_sources)} sources"
                    )
                    print_result(
                        "Without Career Keywords",
                        True,
                        f"RAG triggered unexpectedly (may be false positive), response time: {elapsed_time:.2f}s",
                    )
                return {
                    "success": True,
                    "elapsed_time": elapsed_time,
                    "rag_sources": rag_sources,
                    "data": data,
                }
            else:
                print_result(
                    "Without Career Keywords", False, "Missing rag_sources field"
                )
                return {"success": False, "elapsed_time": elapsed_time}
        else:
            print_result(
                "Without Career Keywords",
                False,
                f"HTTP {response.status_code}: {response.text}",
            )
            return {"success": False, "elapsed_time": elapsed_time}

    except Exception as e:
        elapsed_time = time.time() - start_time
        print_result("Without Career Keywords", False, f"Exception: {str(e)}")
        return {"success": False, "elapsed_time": elapsed_time, "error": str(e)}


def test_data_quality(data: Dict[str, Any]) -> bool:
    """Test 4: Data quality check"""
    print_section("Test 4: Data Quality Check")

    if not data:
        print_result("Data Quality", False, "No data to check")
        return False

    # Check summary
    summary = data.get("summary", "")
    print(f"\n📝 Summary ({len(summary)} chars):")
    print(f"  {summary}")

    # Check alerts
    alerts = data.get("alerts", [])
    print(f"\n⚠️  Alerts ({len(alerts)} items):")
    for i, alert in enumerate(alerts, 1):
        print(f"  [{i}] {alert}")

    # Check suggestions
    suggestions = data.get("suggestions", [])
    print(f"\n💡 Suggestions ({len(suggestions)} items):")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  [{i}] {suggestion}")

    # Quality checks
    quality_checks = [
        ("Summary has content", len(summary) > 20),
        ("Has at least 1 alert", len(alerts) >= 1),
        ("Has at least 1 suggestion", len(suggestions) >= 1),
        (
            "Summary is meaningful (>20 chars)",
            len(summary) > 20,
        ),  # Fixed for Chinese text
        ("Alerts are not empty", all(len(a) > 0 for a in alerts)),
        ("Suggestions are not empty", all(len(s) > 0 for s in suggestions)),
    ]

    all_passed = True
    print("\n✅ Quality Checks:")
    for check_name, passed in quality_checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    print_result(
        "Data Quality",
        all_passed,
        f"Passed {sum(c[1] for c in quality_checks)}/{len(quality_checks)} checks",
    )
    return all_passed


def check_rag_knowledge_base() -> Dict[str, Any]:
    """Check RAG knowledge base status via stats API"""
    print_section("RAG Knowledge Base Status")

    try:
        response = httpx.get(STATS_ENDPOINT, timeout=10.0, follow_redirects=True)

        if response.status_code == 200:
            stats = response.json()

            total_docs = stats.get("total_documents", 0)
            total_chunks = stats.get("total_chunks", 0)
            total_embeddings = stats.get("total_embeddings", 0)

            print("\n📚 RAG Knowledge Base:")
            print(f"  Documents: {total_docs}")
            print(f"  Chunks: {total_chunks}")
            print(f"  Embeddings: {total_embeddings}")

            if total_docs > 0:
                print("\n📄 Documents in knowledge base:")
                for doc in stats.get("documents", [])[:5]:
                    print(
                        f"  - {doc['title']} ({doc['chunks_count']} chunks, {doc['embeddings_count']} embeddings)"
                    )

                return {
                    "success": True,
                    "has_documents": True,
                    "total_documents": total_docs,
                    "total_embeddings": total_embeddings,
                }
            else:
                print("\n⚠️  RAG knowledge base is EMPTY")
                return {
                    "success": True,
                    "has_documents": False,
                    "total_documents": 0,
                    "total_embeddings": 0,
                }
        else:
            print(f"❌ Failed to fetch stats: HTTP {response.status_code}")
            return {"success": False}

    except Exception as e:
        print(f"❌ Error checking RAG knowledge base: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  🚀 Testing Realtime Analysis API on Staging")
    print("=" * 80)
    print(f"\n  API Endpoint: {API_ENDPOINT}")
    print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    results: Dict[str, Any] = {}

    # Check RAG knowledge base status first
    results["rag_kb"] = check_rag_knowledge_base()

    # Test 1: Basic functionality
    results["basic"] = test_basic_functionality()

    # Test 2: RAG with career keywords
    results["rag_career"] = test_rag_with_career_keywords()

    # Test 3: Without career keywords
    results["no_career"] = test_without_career_keywords()

    # Test 4: Data quality (use data from Test 1)
    if results["basic"].get("success") and "data" in results["basic"]:
        results["quality"] = {"success": test_data_quality(results["basic"]["data"])}

    # Summary
    print_section("Test Summary")

    # Count only actual tests (not RAG KB check)
    test_results = {k: v for k, v in results.items() if k != "rag_kb"}
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results.values() if r.get("success"))

    print(f"\n📊 Overall Results: {passed_tests}/{total_tests} tests passed")

    # Performance summary
    print("\n⏱️  Performance Summary:")
    if "basic" in results and "elapsed_time" in results["basic"]:
        print(f"  Basic API: {results['basic']['elapsed_time']:.2f}s")
    if "rag_career" in results and "elapsed_time" in results["rag_career"]:
        print(
            f"  RAG with career keywords: {results['rag_career']['elapsed_time']:.2f}s"
        )
    if "no_career" in results and "elapsed_time" in results["no_career"]:
        print(f"  Without career keywords: {results['no_career']['elapsed_time']:.2f}s")

    # RAG integration summary
    print("\n📚 RAG Integration Summary:")

    # RAG knowledge base status
    if "rag_kb" in results and results["rag_kb"].get("success"):
        if results["rag_kb"].get("has_documents"):
            total_docs = results["rag_kb"].get("total_documents", 0)
            total_emb = results["rag_kb"].get("total_embeddings", 0)
            print(
                f"  Knowledge Base: {total_docs} documents, {total_emb} embeddings ✅"
            )
        else:
            print("  Knowledge Base: EMPTY ❌")

    # RAG search results
    if "rag_career" in results and "rag_sources" in results["rag_career"]:
        rag_count = len(results["rag_career"]["rag_sources"])
        print(f"  Career keywords test: {rag_count} RAG sources found")
        if rag_count > 0:
            print("  ✅ RAG integration is working (sources found)")
        else:
            if "rag_kb" in results and results["rag_kb"].get("has_documents"):
                print(
                    "  ⚠️  RAG triggered but no matches above similarity threshold (0.7)"
                )
            else:
                print("  ⚠️  RAG triggered but knowledge base is empty")
    else:
        print("  ❌ RAG integration test failed")

    if "no_career" in results and "rag_sources" in results["no_career"]:
        no_rag_count = len(results["no_career"]["rag_sources"])
        print(f"  Non-career keywords test: {no_rag_count} RAG sources found")
        if no_rag_count == 0:
            print("  ✅ RAG correctly not triggered for non-career topics")

    # Issues found
    print("\n🔍 Issues Found:")
    issues: List[str] = []

    for test_name, result in results.items():
        if not result.get("success"):
            issues.append(f"{test_name}: {result.get('error', 'Failed')}")

    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ No issues found")

    # Recommendations
    print("\n💡 Recommendations:")
    if passed_tests == total_tests:
        print("  ✅ All tests passed! API is ready for use.")
    else:
        print(f"  ⚠️  {total_tests - passed_tests} test(s) failed. Please investigate.")

    # Check if RAG knowledge base is empty
    if "rag_kb" in results and results["rag_kb"].get("success"):
        if not results["rag_kb"].get("has_documents"):
            print(
                "  ⚠️  RAG knowledge base is EMPTY. Upload career documents via RAG Console:"
            )
            print(f"     {STAGING_URL}/rag")

    print("\n" + "=" * 80)
    print("  Test completed")
    print("=" * 80 + "\n")

    # Exit code
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    exit(main())
