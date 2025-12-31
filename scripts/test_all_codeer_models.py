#!/usr/bin/env python3
"""
Test script to compare all three Codeer models (Claude, Gemini, GPT-5)

This script sends the same test input to all three Codeer models and compares:
- Response latency
- Response quality (summary, alerts, suggestions)
- JSON structure compliance

Usage:
    poetry run python scripts/test_all_codeer_models.py
"""

import asyncio
import json
import time
from typing import Dict, List

import httpx
from rich.console import Console
from rich.table import Table

console = Console()

# Test input - same for all models
TEST_TRANSCRIPT = """諮詢師：最近家裡的孩子怎麼樣？
案主：他最近很不聽話，總是跟我頂嘴。我真的很生氣，有時候真想打他。
諮詢師：聽起來你感到很挫折。
案主：是啊，我不知道該怎麼辦了。"""

TEST_SPEAKERS = [
    {"speaker": "counselor", "text": "最近家裡的孩子怎麼樣？"},
    {
        "speaker": "client",
        "text": "他最近很不聽話，總是跟我頂嘴。我真的很生氣，有時候真想打他。",
    },
    {"speaker": "counselor", "text": "聽起來你感到很挫折。"},
    {"speaker": "client", "text": "是啊，我不知道該怎麼辦了。"},
]

MODELS_TO_TEST = [
    {"name": "Claude Sonnet 4.5", "codeer_model": "claude-sonnet"},
    {"name": "Gemini 2.5 Flash", "codeer_model": "gemini-flash"},
    {"name": "GPT-5 Mini", "codeer_model": "gpt5-mini"},
]

API_URL = "http://localhost:8000/api/v1/realtime/analyze"


async def test_model(model_name: str, codeer_model: str) -> Dict:
    """Test a single Codeer model and return results."""
    console.print(f"\n[cyan]Testing {model_name}...[/cyan]")

    # Don't use session_id to avoid session pool conflicts
    # (session pool might return wrong agent from previous test)
    request_data = {
        "transcript": TEST_TRANSCRIPT,
        "speakers": TEST_SPEAKERS,
        "time_range": "0:00-1:00",
        "provider": "codeer",
        "codeer_model": codeer_model,
        # session_id omitted to create fresh chat each time
    }

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(API_URL, json=request_data)
            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                return {
                    "model": model_name,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "latency_ms": latency_ms,
                }

            data = response.json()

            # Verify JSON structure
            required_fields = ["summary", "alerts", "suggestions"]
            missing_fields = [f for f in required_fields if f not in data]

            return {
                "model": model_name,
                "success": True,
                "latency_ms": latency_ms,
                "summary": data.get("summary", ""),
                "alerts": data.get("alerts", []),
                "suggestions": data.get("suggestions", []),
                "provider_metadata": data.get("provider_metadata", {}),
                "missing_fields": missing_fields,
            }

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "model": model_name,
            "success": False,
            "error": str(e),
            "latency_ms": latency_ms,
        }


async def main():
    """Run comparison test for all models."""
    console.print("\n[bold blue]Codeer Multi-Model Comparison Test[/bold blue]")
    console.print(f"Testing {len(MODELS_TO_TEST)} models with the same input...\n")

    # Test all models
    results: List[Dict] = []
    for model_config in MODELS_TO_TEST:
        result = await test_model(model_config["name"], model_config["codeer_model"])
        results.append(result)

        # Longer delay between requests to ensure clean separation
        # (Codeer API may cache agent history)
        await asyncio.sleep(5)

    # Display results table
    console.print("\n[bold green]Test Results Summary[/bold green]\n")

    # Latency comparison table
    latency_table = Table(title="Latency Comparison")
    latency_table.add_column("Model", style="cyan")
    latency_table.add_column("Status", style="green")
    latency_table.add_column("Latency (ms)", justify="right", style="yellow")

    for result in results:
        status = "✅ Success" if result["success"] else "❌ Failed"
        latency_table.add_row(result["model"], status, str(result["latency_ms"]))

    console.print(latency_table)

    # Response quality comparison
    console.print("\n[bold green]Response Quality Comparison[/bold green]\n")

    for result in results:
        if not result["success"]:
            console.print(f"\n[red]❌ {result['model']} - Failed[/red]")
            console.print(f"   Error: {result['error']}")
            continue

        console.print(f"\n[cyan]✅ {result['model']}[/cyan]")
        console.print(f"   Provider Metadata: {result['provider_metadata']}")
        console.print(f"   Summary: {result['summary'][:100]}...")
        console.print(f"   Alerts: {len(result['alerts'])} items")
        console.print(f"   Suggestions: {len(result['suggestions'])} items")

        if result["missing_fields"]:
            console.print(f"   [red]Missing fields: {result['missing_fields']}[/red]")

    # Detailed output (optional)
    console.print("\n[bold]Detailed Responses (JSON)[/bold]")

    for result in results:
        if result["success"]:
            console.print(f"\n[cyan]{result['model']}:[/cyan]")
            detailed = {
                "summary": result["summary"],
                "alerts": result["alerts"],
                "suggestions": result["suggestions"],
            }
            console.print(json.dumps(detailed, ensure_ascii=False, indent=2))

    # Performance ranking
    console.print("\n[bold green]Performance Ranking (by latency)[/bold green]")
    successful_results = [r for r in results if r["success"]]
    successful_results.sort(key=lambda x: x["latency_ms"])

    for i, result in enumerate(successful_results, 1):
        console.print(f"{i}. {result['model']}: {result['latency_ms']} ms")

    # Summary statistics
    if successful_results:
        avg_latency = sum(r["latency_ms"] for r in successful_results) / len(
            successful_results
        )
        console.print(f"\n[bold]Average latency: {int(avg_latency)} ms[/bold]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise
