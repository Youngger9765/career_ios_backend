#!/usr/bin/env python3
"""
Benchmark script for LLM provider comparison (Gemini vs Codeer)

Usage:
    poetry run python scripts/benchmark_llm_providers.py [--runs N] [--provider gemini|codeer|both]

Example:
    # Benchmark both providers with 10 requests each
    poetry run python scripts/benchmark_llm_providers.py --runs 10 --provider both

    # Benchmark only Gemini with 100 requests
    poetry run python scripts/benchmark_llm_providers.py --runs 100 --provider gemini
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime
from typing import Dict

import httpx

# API endpoint (adjust for your environment)
API_BASE_URL = "http://localhost:8000"  # or staging URL


# Test transcript (consistent for both providers)
TEST_TRANSCRIPT = """諮詢師：早安，今天想跟我聊什麼呢？
案主：老師，我最近真的很煩惱。我家的小孩現在小學三年級，最近變得很叛逆，完全不聽話。
諮詢師：聽起來你感到很困擾。可以多說一些嗎？具體發生了什麼事情？
案主：就是每次叫他寫功課，他都說等一下，然後一直玩手機。跟他講道理也不聽，有時候我真的氣到想揍他。
諮詢師：理解你的挫折感。教養孩子確實不容易，尤其當他們開始有自己的想法時。
案主：對啊，我有時候真的不知道該怎麼辦。打也不是，罵也不是。
諮詢師：你提到想揍他的念頭，這是很誠實的分享。很多父母都會有這樣的情緒，這是正常的。
"""

TEST_SPEAKERS = [
    {"speaker": "counselor", "text": "早安，今天想跟我聊什麼呢？"},
    {
        "speaker": "client",
        "text": "老師，我最近真的很煩惱。我家的小孩現在小學三年級，最近變得很叛逆，完全不聽話。",
    },
    {
        "speaker": "counselor",
        "text": "聽起來你感到很困擾。可以多說一些嗎？具體發生了什麼事情？",
    },
    {
        "speaker": "client",
        "text": "就是每次叫他寫功課，他都說等一下，然後一直玩手機。跟他講道理也不聽，有時候我真的氣到想揍他。",
    },
    {
        "speaker": "counselor",
        "text": "理解你的挫折感。教養孩子確實不容易，尤其當他們開始有自己的想法時。",
    },
    {
        "speaker": "client",
        "text": "對啊，我有時候真的不知道該怎麼辦。打也不是，罵也不是。",
    },
    {
        "speaker": "counselor",
        "text": "你提到想揍他的念頭，這是很誠實的分享。很多父母都會有這樣的情緒，這是正常的。",
    },
]


async def benchmark_provider(
    provider: str, num_runs: int, use_cache: bool = True
) -> Dict:
    """Benchmark a single provider with multiple requests

    Args:
        provider: "gemini" or "codeer"
        num_runs: Number of requests to run
        use_cache: Whether to enable caching (Gemini only)

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking {provider.upper()} ({num_runs} runs)")
    print(f"{'='*60}\n")

    results = {
        "provider": provider,
        "num_runs": num_runs,
        "latencies": [],
        "errors": [],
        "responses": [],
        "cache_hits": [],  # Gemini only
    }

    session_id = f"benchmark-{provider}-{int(time.time())}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}...", end=" ", flush=True)

            payload = {
                "transcript": TEST_TRANSCRIPT,
                "speakers": TEST_SPEAKERS,
                "time_range": "0:00-1:00",
                "provider": provider,
                "session_id": session_id,
            }

            # Add use_cache for Gemini
            if provider == "gemini" and use_cache:
                payload["use_cache"] = True

            start_time = time.time()

            try:
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/realtime/analyze",
                    json=payload,
                )

                latency_ms = int((time.time() - start_time) * 1000)
                results["latencies"].append(latency_ms)

                if response.status_code == 200:
                    data = response.json()
                    results["responses"].append(
                        {
                            "summary": data.get("summary", ""),
                            "alerts_count": len(data.get("alerts", [])),
                            "suggestions_count": len(data.get("suggestions", [])),
                        }
                    )

                    # Track cache metadata for Gemini
                    if provider == "gemini" and "cache_metadata" in data:
                        cache_meta = data["cache_metadata"]
                        results["cache_hits"].append(
                            {
                                "cached_tokens": cache_meta.get("cached_tokens", 0),
                                "prompt_tokens": cache_meta.get("prompt_tokens", 0),
                                "cache_created": cache_meta.get("cache_created", False),
                            }
                        )

                    print(f"✅ {latency_ms}ms")
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                    results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")

            except Exception as e:
                error_msg = f"Exception: {str(e)[:100]}"
                results["errors"].append(error_msg)
                print(f"❌ {error_msg}")

            # Small delay between requests
            await asyncio.sleep(0.1)

    return results


def analyze_results(results: Dict) -> None:
    """Analyze and print benchmark results

    Args:
        results: Benchmark results dictionary
    """
    provider = results["provider"]
    latencies = results["latencies"]
    errors = results["errors"]

    print(f"\n{'='*60}")
    print(f"Results for {provider.upper()}")
    print(f"{'='*60}\n")

    if not latencies:
        print("❌ No successful requests")
        return

    # Latency statistics
    print("📊 Latency Statistics:")
    print(f"  - Total runs: {results['num_runs']}")
    print(f"  - Successful: {len(latencies)}")
    print(f"  - Failed: {len(errors)}")
    print(f"  - Success rate: {len(latencies) / results['num_runs'] * 100:.1f}%")
    print()
    print(f"  - Mean: {statistics.mean(latencies):.0f} ms")
    print(f"  - Median (P50): {statistics.median(latencies):.0f} ms")
    print(f"  - Min: {min(latencies):.0f} ms")
    print(f"  - Max: {max(latencies):.0f} ms")

    if len(latencies) > 1:
        print(f"  - StdDev: {statistics.stdev(latencies):.0f} ms")

        # Percentiles
        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)
        print(f"  - P95: {sorted_latencies[p95_idx]:.0f} ms")
        print(f"  - P99: {sorted_latencies[p99_idx]:.0f} ms")

    # Cache performance (Gemini only)
    if provider == "gemini" and results["cache_hits"]:
        print()
        print("🎯 Cache Performance:")
        cache_hits = results["cache_hits"]
        avg_cached = statistics.mean([c["cached_tokens"] for c in cache_hits])
        avg_prompt = statistics.mean([c["prompt_tokens"] for c in cache_hits])
        cache_created_count = sum([c["cache_created"] for c in cache_hits])

        print(f"  - Avg cached tokens: {avg_cached:.0f}")
        print(f"  - Avg prompt tokens: {avg_prompt:.0f}")
        print(f"  - Cache created count: {cache_created_count}")

        if avg_cached + avg_prompt > 0:
            cache_ratio = avg_cached / (avg_cached + avg_prompt) * 100
            print(f"  - Cache hit ratio: {cache_ratio:.1f}%")

    # Error summary
    if errors:
        print()
        print("⚠️ Errors:")
        error_counts = {}
        for err in errors:
            # Group similar errors
            error_type = err.split(":")[0]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        for error_type, count in error_counts.items():
            print(f"  - {error_type}: {count} occurrences")

    # Response quality (sample)
    if results["responses"]:
        print()
        print("📝 Response Quality (sample):")
        sample = results["responses"][0]
        print(f"  - Summary: {sample['summary'][:80]}...")
        print(f"  - Alerts count: {sample['alerts_count']}")
        print(f"  - Suggestions count: {sample['suggestions_count']}")


def compare_results(gemini_results: Dict, codeer_results: Dict) -> None:
    """Compare results between Gemini and Codeer

    Args:
        gemini_results: Gemini benchmark results
        codeer_results: Codeer benchmark results
    """
    print(f"\n{'='*60}")
    print("COMPARISON: Gemini vs Codeer")
    print(f"{'='*60}\n")

    gemini_latencies = gemini_results["latencies"]
    codeer_latencies = codeer_results["latencies"]

    if not gemini_latencies or not codeer_latencies:
        print("⚠️ Cannot compare - missing data")
        return

    # Latency comparison
    gemini_median = statistics.median(gemini_latencies)
    codeer_median = statistics.median(codeer_latencies)
    speedup = codeer_median / gemini_median

    print("⚡ Performance:")
    print(f"  - Gemini median: {gemini_median:.0f} ms")
    print(f"  - Codeer median: {codeer_median:.0f} ms")
    print(
        f"  - Speedup: {speedup:.1f}x {'(Gemini faster)' if speedup > 1 else '(Codeer faster)'}"
    )

    # Success rate comparison
    gemini_success_rate = len(gemini_latencies) / gemini_results["num_runs"] * 100
    codeer_success_rate = len(codeer_latencies) / codeer_results["num_runs"] * 100

    print()
    print("✅ Reliability:")
    print(f"  - Gemini success rate: {gemini_success_rate:.1f}%")
    print(f"  - Codeer success rate: {codeer_success_rate:.1f}%")

    # Cost estimate (Gemini only, requires cache data)
    if gemini_results["cache_hits"]:
        print()
        print("💰 Estimated Cost (Gemini):")
        cache_hits = gemini_results["cache_hits"]
        avg_cached = statistics.mean([c["cached_tokens"] for c in cache_hits])
        avg_prompt = statistics.mean([c["prompt_tokens"] for c in cache_hits])
        avg_output = 250  # Estimated output tokens

        # Pricing (as of Dec 2024)
        cached_cost = avg_cached * 0.01875 / 1_000_000
        prompt_cost = avg_prompt * 0.075 / 1_000_000
        output_cost = avg_output * 0.30 / 1_000_000
        total_cost = cached_cost + prompt_cost + output_cost

        print(f"  - Cost per request: ${total_cost:.6f}")
        print(f"  - Cost per 1000 requests: ${total_cost * 1000:.3f}")
        print(f"  - Cost per 10000 requests: ${total_cost * 10000:.2f}")

    # Winner summary
    print()
    print("🏆 Winner:")
    if speedup > 1.5 and gemini_success_rate >= codeer_success_rate:
        print("  ✅ Gemini (significantly faster with comparable reliability)")
    elif speedup > 1.2:
        print("  ✅ Gemini (faster)")
    elif speedup < 0.8:
        print("  ✅ Codeer (faster)")
    else:
        print("  🟰 Tie (similar performance)")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark LLM providers")
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of benchmark runs per provider (default: 10)",
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "codeer", "both"],
        default="both",
        help="Which provider to benchmark (default: both)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching for Gemini (default: enabled)",
    )

    args = parser.parse_args()

    global API_BASE_URL
    API_BASE_URL = args.api_url.rstrip("/")

    print(f"\n{'='*60}")
    print("LLM Provider Benchmark")
    print(f"{'='*60}")
    print(f"API URL: {API_BASE_URL}")
    print(f"Runs per provider: {args.runs}")
    print(f"Caching: {'Disabled' if args.no_cache else 'Enabled (Gemini only)'}")
    print(f"{'='*60}\n")

    results = {}

    # Benchmark Gemini
    if args.provider in ["gemini", "both"]:
        results["gemini"] = await benchmark_provider(
            "gemini", args.runs, use_cache=not args.no_cache
        )
        analyze_results(results["gemini"])

    # Benchmark Codeer
    if args.provider in ["codeer", "both"]:
        results["codeer"] = await benchmark_provider(
            "codeer", args.runs, use_cache=False
        )
        analyze_results(results["codeer"])

    # Compare if both were tested
    if args.provider == "both":
        compare_results(results["gemini"], results["codeer"])

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"benchmark_results_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "args": vars(args),
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Benchmark interrupted by user")
        sys.exit(1)
