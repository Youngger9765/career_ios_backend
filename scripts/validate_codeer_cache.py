"""
Validate Codeer Cache Behavior

Tests if Codeer Gemini Flash's consistent 5.4s speed is due to hidden caching.

Process:
1. Cold start: Run with new test data (long_transcripts_v2.json)
2. Warm test: Immediately re-run with same v2 data
3. Compare latencies to detect cache effects

Usage:
    poetry run python scripts/validate_codeer_cache.py
"""
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the existing test infrastructure
from scripts.compare_four_providers import (  # noqa: E402
    run_single_test,
)

logger = logging.getLogger(__name__)
console = Console()


async def run_cache_validation():
    """Run cache validation test

    Returns:
        Dict with cold and warm test results
    """
    # Load v2 test data (new topic: 青少年网络成瘾)
    data_path = project_root / "tests" / "data" / "long_transcripts_v2.json"

    if not data_path.exists():
        console.print(f"[red]ERROR: Test data not found: {data_path}[/red]")
        return None

    with open(data_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    results = {
        "cold_start": [],
        "warm_test": [],
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "test_data": "long_transcripts_v2.json",
            "topic": test_data.get("8min", {}).get("topic", "Unknown"),
        },
    }

    # Test configuration: Focus on Codeer Gemini Flash (the fast one)
    test_config = [
        ("codeer", "gemini-flash"),
    ]

    durations = [8, 9, 10]

    console.print(
        Panel(
            f"[bold cyan]Codeer Cache Validation Test[/bold cyan]\n"
            f"Testing: Codeer Gemini Flash\n"
            f"Durations: {durations} minutes\n"
            f"Topic: {results['metadata']['topic']}\n"
            f"Method: Cold start → Warm test (same data)",
            title="Validation Setup",
        )
    )

    # ========================================================================
    # COLD START TEST (First run with new data)
    # ========================================================================
    console.print("\n[bold yellow]═══ COLD START TEST (First run) ═══[/bold yellow]")

    for duration in durations:
        transcript_data = test_data[f"{duration}min"]

        for provider, model in test_config:
            session_id = f"cold-start-{duration}min-{model}"

            console.print(
                f"\n[cyan]Testing {duration}min transcript (COLD)...[/cyan]", end=" "
            )

            result = await run_single_test(
                provider=provider,
                model=model,
                transcript_data=transcript_data,
                session_id=session_id,
            )

            result["duration_minutes"] = duration
            result["topic"] = transcript_data["topic"]
            result["test_type"] = "cold_start"

            results["cold_start"].append(result)

            if "error" in result:
                console.print(f"[red]FAILED[/red] - {result['error'][:50]}")
            else:
                latency = result["latency_ms"]
                quality = result.get("quality_score", {}).get("total_score", 0)
                console.print(
                    f"[green]OK[/green] - {latency}ms, Quality: {quality:.1f}/100"
                )

    # ========================================================================
    # WARM TEST (Re-run with same data immediately)
    # ========================================================================
    console.print(
        "\n[bold yellow]═══ WARM TEST (Re-run with same data) ═══[/bold yellow]"
    )

    for duration in durations:
        transcript_data = test_data[f"{duration}min"]

        for provider, model in test_config:
            # Use SAME session_id to trigger potential cache
            session_id = f"warm-test-{duration}min-{model}"

            console.print(
                f"\n[cyan]Testing {duration}min transcript (WARM)...[/cyan]", end=" "
            )

            result = await run_single_test(
                provider=provider,
                model=model,
                transcript_data=transcript_data,
                session_id=session_id,
            )

            result["duration_minutes"] = duration
            result["topic"] = transcript_data["topic"]
            result["test_type"] = "warm_test"

            results["warm_test"].append(result)

            if "error" in result:
                console.print(f"[red]FAILED[/red] - {result['error'][:50]}")
            else:
                latency = result["latency_ms"]
                quality = result.get("quality_score", {}).get("total_score", 0)
                console.print(
                    f"[green]OK[/green] - {latency}ms, Quality: {quality:.1f}/100"
                )

    return results


def analyze_cache_validation(results: dict):
    """Analyze cache validation results

    Args:
        results: Dict with cold_start and warm_test results
    """
    console.print("\n")
    console.print(
        Panel("[bold cyan]Cache Validation Analysis[/bold cyan]", expand=False)
    )

    cold_results = results["cold_start"]
    warm_results = results["warm_test"]

    # Check for failures
    cold_failures = [r for r in cold_results if "error" in r]
    warm_failures = [r for r in warm_results if "error" in r]

    if cold_failures or warm_failures:
        console.print(
            f"\n[yellow]Warning: {len(cold_failures)} cold + {len(warm_failures)} warm tests failed[/yellow]"
        )
        return

    # Comparison table
    table = Table(
        title="🔍 Cold Start vs Warm Test Latency Comparison",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Duration", style="cyan", justify="center")
    table.add_column("Cold Start\n(ms)", justify="right")
    table.add_column("Warm Test\n(ms)", justify="right")
    table.add_column("Difference\n(ms)", justify="right")
    table.add_column("Speed Change", justify="center")

    total_cold_latency = 0
    total_warm_latency = 0
    test_count = 0

    for duration in [8, 9, 10]:
        cold_result = next(
            (r for r in cold_results if r["duration_minutes"] == duration), None
        )
        warm_result = next(
            (r for r in warm_results if r["duration_minutes"] == duration), None
        )

        if cold_result and warm_result:
            cold_latency = cold_result["latency_ms"]
            warm_latency = warm_result["latency_ms"]
            diff = warm_latency - cold_latency

            total_cold_latency += cold_latency
            total_warm_latency += warm_latency
            test_count += 1

            # Determine speed change indicator
            if diff < -500:  # Faster by >500ms
                speed_indicator = "[green]⚡ MUCH FASTER[/green]"
            elif diff < -100:  # Faster by >100ms
                speed_indicator = "[green]↗ Faster[/green]"
            elif diff > 500:  # Slower by >500ms
                speed_indicator = "[red]⬇ MUCH SLOWER[/red]"
            elif diff > 100:  # Slower by >100ms
                speed_indicator = "[yellow]↘ Slower[/yellow]"
            else:
                speed_indicator = "[white]≈ Similar[/white]"

            table.add_row(
                f"{duration} min",
                f"{cold_latency}",
                f"{warm_latency}",
                f"{diff:+d}",
                speed_indicator,
            )

    console.print("\n")
    console.print(table)

    # Calculate averages
    if test_count > 0:
        avg_cold = total_cold_latency / test_count
        avg_warm = total_warm_latency / test_count
        avg_diff = avg_warm - avg_cold

        console.print("\n[bold]Average Latency:[/bold]")
        console.print(f"  Cold Start: {avg_cold:.0f} ms")
        console.print(f"  Warm Test:  {avg_warm:.0f} ms")
        console.print(
            f"  Difference: {avg_diff:+.0f} ms ({(avg_diff/avg_cold)*100:+.1f}%)"
        )

        # Conclusion
        console.print("\n")
        if abs(avg_diff) < 100:
            # No significant difference
            console.print(
                Panel(
                    f"[bold green]✅ NO CACHE DETECTED[/bold green]\n\n"
                    f"Cold vs Warm latency difference: {avg_diff:+.0f}ms ({(avg_diff/avg_cold)*100:+.1f}%)\n\n"
                    f"Codeer Gemini Flash's {avg_cold:.0f}ms speed appears to be genuine,\n"
                    f"not due to hidden caching mechanisms.\n\n"
                    f"Conclusion: The consistent 5.4s performance is real.",
                    title="Validation Result",
                    border_style="green",
                )
            )
        elif avg_diff < -100:
            # Warm is significantly faster - cache detected
            console.print(
                Panel(
                    f"[bold yellow]⚠️ CACHE DETECTED[/bold yellow]\n\n"
                    f"Warm test is {abs(avg_diff):.0f}ms faster ({abs(avg_diff/avg_cold)*100:.1f}% faster)\n\n"
                    f"This suggests Codeer may have undocumented caching.\n"
                    f"The original 5.4s speed may be cache-assisted.\n\n"
                    f"Cold start speed: {avg_cold:.0f}ms\n"
                    f"Warm speed: {avg_warm:.0f}ms",
                    title="Validation Result",
                    border_style="yellow",
                )
            )
        else:
            # Warm is slower - unexpected
            console.print(
                Panel(
                    f"[bold cyan]❓ UNEXPECTED RESULT[/bold cyan]\n\n"
                    f"Warm test is {avg_diff:.0f}ms slower ({(avg_diff/avg_cold)*100:+.1f}%)\n\n"
                    f"This is unusual - typically cache should make it faster or similar.\n"
                    f"Possible causes: API rate limiting, server load variation.\n\n"
                    f"Recommendation: Re-run test to verify consistency.",
                    title="Validation Result",
                    border_style="cyan",
                )
            )


def save_validation_results(results: dict):
    """Save validation results to JSON

    Args:
        results: Validation results dict
    """
    output_file = project_root / "cache_validation_results.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]Results saved to: {output_file}[/green]")


async def main():
    """Main entry point"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Run validation
        results = await run_cache_validation()

        if results is None:
            console.print("[red]Validation failed - no results[/red]")
            sys.exit(1)

        # Analyze results
        analyze_cache_validation(results)

        # Save results
        save_validation_results(results)

    except Exception as e:
        console.print(f"\n[red]Validation failed: {e}[/red]")
        logger.exception("Validation error")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
