"""
手動測試腳本：比較 Rule-Based 和 AI Prompt 兩種方案
"""

import asyncio
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def test_rule_based_service():
    """測試方案 A: Rule-Based"""
    from app.services.encouragement_service import encouragement_service

    print("\n" + "=" * 60)
    print("方案 A: Rule-Based 雞湯文服務")
    print("=" * 60)

    test_cases = [
        ("家長：你再這樣我就打死你！", "danger"),
        ("家長：你覺得這樣好嗎？", "question"),
        ("家長：我看到你好像不太開心", "neutral"),
        ("孩子：我不想去學校... 家長：為什麼呢？", "question"),
        ("家長：你給我閉嘴！", "danger"),
    ]

    for transcript, expected_type in test_cases:
        start = time.time()
        result = encouragement_service.get_encouragement(transcript)
        latency = (time.time() - start) * 1000

        print(f"\n逐字稿: {transcript}")
        print(f"訊息類型: {result['type']} (預期: {expected_type})")
        print(f"鼓勵訊息: {result['message']}")
        print(f"延遲: {latency:.2f} ms")

        assert (
            result["type"] == expected_type
        ), f"類型錯誤：預期 {expected_type}，實際 {result['type']}"

    print("\n✅ 方案 A 測試通過")


async def test_ai_prompt_service():
    """測試方案 B: AI Prompt"""
    from app.services.quick_feedback_service import quick_feedback_service

    print("\n" + "=" * 60)
    print("方案 B: 輕量 AI Prompt 服務")
    print("=" * 60)

    test_cases = [
        "家長：你再這樣我就打死你！",
        "家長：你覺得這樣好嗎？",
        "家長：我看到你好像不太開心",
        "孩子：我不想去學校... 家長：為什麼呢？",
    ]

    latencies = []

    for transcript in test_cases:
        result = await quick_feedback_service.get_quick_feedback(transcript)

        print(f"\n逐字稿: {transcript}")
        print(f"訊息類型: {result['type']}")
        print(f"鼓勵訊息: {result['message']}")
        print(f"延遲: {result.get('latency_ms', 0)} ms")

        if "latency_ms" in result:
            latencies.append(result["latency_ms"])

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"\n平均延遲: {avg_latency:.2f} ms")
        print(f"最大延遲: {max(latencies)} ms")
        print(f"最小延遲: {min(latencies)} ms")

    print("\n✅ 方案 B 測試完成")


def test_performance_comparison():
    """效能比較"""
    print("\n" + "=" * 60)
    print("效能比較：方案 A vs 方案 B")
    print("=" * 60)

    from app.services.encouragement_service import encouragement_service

    # 方案 A 效能測試
    test_transcript = "家長：你覺得這樣好嗎？孩子：我不知道..."

    iterations = 100

    # 測試方案 A
    start = time.time()
    for _ in range(iterations):
        encouragement_service.get_encouragement(test_transcript)
    rule_based_time = (time.time() - start) * 1000

    print("\n方案 A (Rule-Based):")
    print(f"  100 次呼叫總時間: {rule_based_time:.2f} ms")
    print(f"  平均每次: {rule_based_time/iterations:.2f} ms")
    print("  ✅ 優點: 極快、可預測、不需網路")
    print("  ⚠️  缺點: 較機械化、有限彈性")

    print("\n方案 B (AI Prompt):")
    print("  預估平均每次: ~1000-2000 ms (需 AI 呼叫)")
    print("  ✅ 優點: 更靈活、更自然")
    print("  ⚠️  缺點: 慢、需網路、成本")


if __name__ == "__main__":
    # 測試方案 A
    test_rule_based_service()

    # 測試方案 B（需要 async）
    asyncio.run(test_ai_prompt_service())

    # 效能比較
    test_performance_comparison()

    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)
    print("\n建議：")
    print("- 如果要求 < 100ms 響應 → 使用方案 A (Rule-Based)")
    print("- 如果要求更自然的回饋 → 使用方案 B (AI Prompt)")
    print("- 混合方案：方案 A 為主，方案 B 為輔（定期更新句庫）")
