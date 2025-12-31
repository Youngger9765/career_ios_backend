"""
Quick test script to validate experiment functions

Tests:
1. Load test data successfully
2. Quality evaluation functions work
3. Cost calculation functions work
"""

import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.compare_four_providers import (  # noqa: E402
    calculate_codeer_cost,
    calculate_gemini_cost,
    evaluate_completeness,
    evaluate_professionalism,
    evaluate_quality,
    evaluate_relevance,
    evaluate_structure,
)


def test_load_data():
    """Test loading test data"""
    print("Testing data loading...")
    data_path = project_root / "tests" / "data" / "long_transcripts.json"

    with open(data_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    assert "8min" in test_data, "Missing 8min data"
    assert "9min" in test_data, "Missing 9min data"
    assert "10min" in test_data, "Missing 10min data"

    for key in ["8min", "9min", "10min"]:
        data = test_data[key]
        assert "transcript" in data, f"{key}: Missing transcript"
        assert "speakers" in data, f"{key}: Missing speakers"
        assert "topic" in data, f"{key}: Missing topic"
        assert len(data["transcript"]) > 0, f"{key}: Empty transcript"

    print("✓ Data loading test passed")
    return test_data


def test_quality_evaluation(test_data):
    """Test quality evaluation functions"""
    print("\nTesting quality evaluation...")

    # Mock analysis response
    mock_response = {
        "summary": "案主面臨孩子不願意做功課的困擾，感到挫折和焦慮。",
        "alerts": [
            "💡 理解到家長在教養壓力下的辛苦",
            "⚠️ 注意親子溝通方式可能影響孩子意願",
        ],
        "suggestions": [
            "💡 建立明確的作息時間表，讓孩子有休息時間",
            "💡 用正向鼓勵取代責備，增強孩子的動機",
        ],
    }

    transcript = test_data["8min"]["transcript"]

    # Test individual evaluation functions
    structure_score = evaluate_structure(mock_response)
    assert 0 <= structure_score <= 100, "Structure score out of range"
    print(f"  Structure score: {structure_score:.1f}/100")

    relevance_score = evaluate_relevance(mock_response, transcript)
    assert 0 <= relevance_score <= 100, "Relevance score out of range"
    print(f"  Relevance score: {relevance_score:.1f}/100")

    professionalism_score = evaluate_professionalism(mock_response)
    assert 0 <= professionalism_score <= 100, "Professionalism score out of range"
    print(f"  Professionalism score: {professionalism_score:.1f}/100")

    completeness_score = evaluate_completeness(mock_response)
    assert 0 <= completeness_score <= 100, "Completeness score out of range"
    print(f"  Completeness score: {completeness_score:.1f}/100")

    # Test overall quality evaluation
    quality_result = evaluate_quality(mock_response, transcript)
    assert "total_score" in quality_result, "Missing total_score"
    assert "breakdown" in quality_result, "Missing breakdown"
    assert 0 <= quality_result["total_score"] <= 100, "Total score out of range"

    print(f"  Overall quality: {quality_result['total_score']:.1f}/100")
    print(f"  Breakdown: {quality_result['breakdown']}")

    print("✓ Quality evaluation test passed")


def test_cost_calculation():
    """Test cost calculation functions"""
    print("\nTesting cost calculation...")

    # Test Gemini cost calculation
    gemini_usage = {
        "prompt_token_count": 500,
        "cached_content_token_count": 1200,
        "candidates_token_count": 150,
    }

    gemini_cost = calculate_gemini_cost(gemini_usage)
    assert "total_cost" in gemini_cost, "Missing total_cost"
    assert "breakdown" in gemini_cost, "Missing breakdown"
    assert gemini_cost["total_cost"] > 0, "Cost should be positive"

    print(f"  Gemini cost: ${gemini_cost['total_cost']:.6f}")
    print(f"  Breakdown: {gemini_cost['breakdown']}")

    # Test Codeer cost calculation
    codeer_cost = calculate_codeer_cost(api_calls=1, estimated_tokens=2000)
    assert "total_cost" in codeer_cost, "Missing total_cost"
    assert "breakdown" in codeer_cost, "Missing breakdown"
    assert codeer_cost["total_cost"] > 0, "Cost should be positive"

    print(f"  Codeer cost: ${codeer_cost['total_cost']:.6f}")
    print(f"  Breakdown: {codeer_cost['breakdown']}")
    print(f"  Note: {codeer_cost['note']}")

    print("✓ Cost calculation test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Running Experiment Function Tests")
    print("=" * 60)

    try:
        # Test 1: Data loading
        test_data = test_load_data()

        # Test 2: Quality evaluation
        test_quality_evaluation(test_data)

        # Test 3: Cost calculation
        test_cost_calculation()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
