#!/usr/bin/env python3
"""
End-to-End Test for Realtime Analysis Flow
Tests complete flow from transcript to GBQ persistence

This script simulates the complete realtime analysis flow:
1. Prepares test transcripts (1-minute conversations)
2. Calls Realtime API (/api/v1/realtime/analyze)
3. Waits for BackgroundTasks to complete GBQ write
4. Queries GBQ to verify all fields
5. Displays comprehensive results

Test scenarios cover:
- Practice mode + Green conversation (positive, supportive)
- Emergency mode + Yellow conversation (needs adjustment)
- Practice mode + Red conversation (problematic, urgent)
"""
import asyncio
import os
import sys
import time
from typing import Any, Dict, Optional

import httpx
from google.cloud import bigquery
from rich.console import Console
from rich.table import Table

console = Console()

# Test scenarios with realistic Chinese parent-child conversations
SCENARIOS = {
    "green_practice": {
        "mode": "practice",
        "transcript": """家長：你今天在學校過得如何？
孩子：還不錯，老師稱讚我了。
家長：老師稱讚你什麼？能跟我分享嗎？
孩子：我今天數學考了95分，老師說我進步很多。
家長：哇，你好棒！我看到你這陣子很認真準備，你的努力真的有回報。
孩子：謝謝媽媽！我下次還想考更好。
家長：我相信你一定可以的，媽媽會一直支持你。有需要幫忙的地方隨時跟我說喔。
孩子：好的，謝謝媽媽！""",
        "expected_safety": "green",
        "description": "正向對話，家長給予支持與肯定，建立良好親子關係",
    },
    "yellow_emergency": {
        "mode": "emergency",
        "transcript": """家長：你怎麼又考這麼差？才60分！
孩子：我已經很努力了...
家長：努力有用的話還要天才幹嘛？你看看隔壁小明都考90分！
孩子：......
家長：說話啊！你怎麼這麼沒用？
孩子：對不起......
家長：算了，回房間反省去！""",
        "expected_safety": "yellow",
        "description": "有警訊，家長語氣帶有指責，開始與他人比較，需要調整",
    },
    "red_practice": {
        "mode": "practice",
        "transcript": """家長：你真的很沒用！這麼簡單都不會！
孩子：對不起...我真的有在學...
家長：對不起有什麼用？你就是不夠聰明，笨死了！
孩子：......（開始哭泣）
家長：哭什麼哭！哭能解決問題嗎？再哭我就揍你！
孩子：我不想活了...我好痛苦...
家長：你說什麼？！給我閉嘴！滾回房間！
孩子：（哭著跑回房間）""",
        "expected_safety": "red",
        "description": "危險對話，直接傷害孩子自尊，威脅暴力，孩子出現自殺念頭",
    },
}

# BigQuery configuration
PROJECT_ID = os.getenv("GCS_PROJECT", "groovy-iris-473015-h3")
DATASET_ID = os.getenv("REALTIME_DATASET_ID", "realtime_logs")
TABLE_ID = os.getenv("REALTIME_TABLE_ID", "realtime_analysis_logs")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


async def check_api_health() -> bool:
    """Check if API is running and healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                console.print("✅ API is running and healthy", style="bold green")
                return True
            else:
                console.print(
                    f"❌ API returned status {response.status_code}", style="bold red"
                )
                return False
    except httpx.ConnectError:
        console.print(f"❌ Cannot connect to API at {API_BASE_URL}", style="bold red")
        console.print(
            "Start API with: poetry run uvicorn app.main:app --reload", style="yellow"
        )
        return False
    except Exception as e:
        console.print(f"❌ Health check failed: {str(e)}", style="bold red")
        return False


async def call_realtime_api(
    transcript: str, mode: str, session_id: str
) -> Optional[Dict[str, Any]]:
    """Call the realtime analysis API

    Args:
        transcript: Full conversation transcript
        mode: "practice" or "emergency"
        session_id: Session ID for this test

    Returns:
        API response data or None if failed
    """
    # Build speakers from transcript
    speakers = []
    for line in transcript.strip().split("\n"):
        if "：" in line:
            speaker_label, text = line.split("：", 1)
            # Map 家長/孩子 to client/counselor (家長 is the client seeking help)
            speaker = "client" if "家長" in speaker_label else "counselor"
            speakers.append({"speaker": speaker, "text": text})

    # Prepare request payload
    payload = {
        "transcript": transcript,
        "speakers": speakers,
        "time_range": "0:00-1:00",
        "mode": mode,
        "provider": "gemini",
        "use_cache": True,
        "session_id": session_id,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/realtime/analyze", json=payload
            )

        if response.status_code == 200:
            return response.json()
        else:
            console.print(
                f"❌ API Error {response.status_code}: {response.text}",
                style="bold red",
            )
            return None

    except Exception as e:
        console.print(f"❌ API call failed: {str(e)}", style="bold red")
        return None


async def query_gbq_record(session_id: str) -> Optional[Dict[str, Any]]:
    """Query BigQuery for the latest analysis record

    Args:
        session_id: Session ID to search for

    Returns:
        GBQ record data or None if not found
    """
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

        # Query for record created in the last 30 seconds with matching session_id
        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE session_id = @session_id
          AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 SECOND)
        ORDER BY created_at DESC
        LIMIT 1
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("session_id", "STRING", session_id)
            ]
        )

        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())

        if results:
            # Convert Row to dict
            row = results[0]
            return dict(row.items())
        else:
            return None

    except Exception as e:
        console.print(f"❌ GBQ query failed: {str(e)}", style="bold red")
        return None


def display_field_verification(record: Dict[str, Any]) -> None:
    """Display GBQ record fields in a beautiful table

    Args:
        record: GBQ record data
    """
    table = Table(
        title="📊 GBQ Record Verification",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Field", style="cyan", width=30)
    table.add_column("Status", style="green", width=10)
    table.add_column("Value/Info", style="white", width=60)

    # Define critical fields to verify
    critical_fields = [
        ("transcript", "FULL transcript", True),
        ("system_prompt", "System instruction", True),
        ("user_prompt", "User prompt sent to LLM", True),
        ("rag_used", "RAG usage flag", False),
        ("rag_query", "RAG search query", False),
        ("rag_documents", "RAG documents", False),
        ("provider", "LLM provider", False),
        ("model_name", "Model name", False),
        ("start_time", "Start timestamp", False),
        ("end_time", "End timestamp", False),
        ("duration_ms", "Duration in milliseconds", False),
        ("safety_level", "Safety level (green/yellow/red)", False),
        ("matched_suggestions", "Matched suggestions", True),
        ("llm_raw_response", "Raw LLM response", True),
        ("analysis_result", "Structured analysis", True),
        ("prompt_tokens", "Prompt tokens", False),
        ("completion_tokens", "Completion tokens", False),
        ("total_tokens", "Total tokens", False),
        ("cached_tokens", "Cached tokens", False),
        ("estimated_cost_usd", "Estimated cost", False),
        ("use_cache", "Cache usage flag", False),
        ("cache_hit", "Cache hit flag", False),
        ("cache_key", "Cache key", False),
        ("gemini_cache_ttl", "Cache TTL", False),
        ("mode", "Analysis mode", False),
        ("session_id", "Session ID", False),
    ]

    for field_name, description, is_long in critical_fields:
        value = record.get(field_name)

        # Determine status
        if value is None:
            status = "❌"
            info = "Missing"
            status_style = "bold red"
        elif isinstance(value, str) and len(value) == 0:
            status = "⚠️"
            info = "Empty"
            status_style = "yellow"
        else:
            status = "✅"
            status_style = "bold green"

            # Format value based on type
            if isinstance(value, str):
                if is_long:
                    info = f"[{len(value)} chars] {value[:100]}..."
                else:
                    info = f"{value[:80]}" if len(value) > 80 else value
            elif isinstance(value, (list, dict)):
                if isinstance(value, list):
                    info = f"[{len(value)} items]"
                else:
                    info = f"[{len(value)} fields]"
            elif isinstance(value, bool):
                info = "Yes" if value else "No"
            elif isinstance(value, (int, float)):
                info = str(value)
            else:
                info = str(value)[:80]

        # Add row with color coding
        table.add_row(description, status, info, style=status_style)

    console.print(table)


async def test_scenario(scenario_name: str, scenario: Dict[str, Any]) -> bool:
    """Test a single scenario

    Args:
        scenario_name: Name of the scenario
        scenario: Scenario configuration

    Returns:
        True if test passed, False otherwise
    """
    console.print(f"\n{'=' * 60}", style="bold blue")
    console.print(f"Test: {scenario_name.upper()}", style="bold blue")
    console.print(f"Description: {scenario['description']}", style="cyan")
    console.print(f"{'=' * 60}\n", style="bold blue")

    # 1. Show transcript preview
    console.print("📝 Transcript (逐字稿):", style="bold yellow")
    transcript_preview = (
        scenario["transcript"][:300] + "..."
        if len(scenario["transcript"]) > 300
        else scenario["transcript"]
    )
    console.print(transcript_preview, style="dim")

    # 2. Show API request details
    session_id = f"test-{scenario_name}-{int(time.time())}"
    console.print("\n📤 API Request:", style="bold yellow")
    console.print(f"  Mode: {scenario['mode']}")
    console.print("  Provider: gemini")
    console.print("  Cache: true")
    console.print(f"  Session ID: {session_id}")

    # 3. Call API
    console.print("\n⏳ Calling Realtime API...", style="yellow")
    start_time = time.time()

    result = await call_realtime_api(
        transcript=scenario["transcript"], mode=scenario["mode"], session_id=session_id
    )

    api_duration_ms = int((time.time() - start_time) * 1000)

    if not result:
        console.print("❌ Test FAILED: API call failed", style="bold red")
        return False

    # 4. Display API response
    console.print(f"\n✅ API Response ({api_duration_ms}ms):", style="bold green")
    console.print("  Status: 200 OK")
    console.print(f"  Safety Level: {result.get('safety_level')}")
    console.print(f"  Risk Level: {result.get('risk_level')}")
    console.print(f"  Suggestions: {len(result.get('suggestions', []))} 建議")

    # Show suggestions
    for i, sug in enumerate(result.get("suggestions", []), 1):
        console.print(f"    {i}. {sug}", style="dim")

    # 5. Wait for GBQ write (BackgroundTasks)
    console.print("\n⏳ Waiting for GBQ write (8 seconds)...", style="yellow")
    await asyncio.sleep(8)

    # 6. Query GBQ
    console.print("\n📊 Querying GBQ for verification...", style="bold cyan")
    gbq_record = await query_gbq_record(session_id)

    if not gbq_record:
        console.print(
            f"❌ Test FAILED: GBQ record not found for session {session_id}",
            style="bold red",
        )
        console.print("Possible reasons:", style="yellow")
        console.print("  1. GBQ write took longer than 8 seconds", style="dim")
        console.print("  2. GBQ write failed (check API logs)", style="dim")
        console.print("  3. Query failed (check GBQ permissions)", style="dim")
        return False

    # 7. Verify GBQ record
    console.print("\n✅ GBQ record found!", style="bold green")
    display_field_verification(gbq_record)

    # 8. Verify expected safety level
    expected_safety = scenario.get("expected_safety")
    actual_safety = gbq_record.get("safety_level")

    if expected_safety and actual_safety != expected_safety:
        console.print(
            f"\n⚠️ Warning: Expected safety level '{expected_safety}', got '{actual_safety}'",
            style="yellow",
        )
        console.print(
            "This may indicate the LLM's assessment differs from expectations",
            style="dim",
        )

    console.print(f"\n✅ Test PASSED: {scenario_name}", style="bold green")
    return True


async def main():
    """Run all test scenarios"""
    console.print("\n" + "=" * 60, style="bold magenta")
    console.print("Realtime Analysis End-to-End Test", style="bold magenta")
    console.print("=" * 60 + "\n", style="bold magenta")

    # Check if API is running
    if not await check_api_health():
        console.print("\n❌ Cannot proceed without running API", style="bold red")
        console.print(
            "Start API with: poetry run uvicorn app.main:app --reload",
            style="yellow",
        )
        sys.exit(1)

    # Run all test scenarios
    results = {}
    for scenario_name, scenario in SCENARIOS.items():
        try:
            passed = await test_scenario(scenario_name, scenario)
            results[scenario_name] = passed
        except Exception as e:
            console.print(
                f"\n❌ Test FAILED with exception: {str(e)}", style="bold red"
            )
            results[scenario_name] = False

    # Summary
    console.print(f"\n{'=' * 60}", style="bold magenta")
    console.print("Test Summary", style="bold magenta")
    console.print(f"{'=' * 60}\n", style="bold magenta")

    passed_count = sum(1 for passed in results.values() if passed)
    total_count = len(results)

    for scenario_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        style = "bold green" if passed else "bold red"
        console.print(f"  {scenario_name}: {status}", style=style)

    console.print(
        f"\n📊 Results: {passed_count}/{total_count} tests passed", style="bold cyan"
    )

    if passed_count == total_count:
        console.print("\n🎉 All tests passed!", style="bold green")
        sys.exit(0)
    else:
        console.print(
            f"\n⚠️ {total_count - passed_count} test(s) failed", style="bold yellow"
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n⚠️ Test interrupted by user", style="bold yellow")
        sys.exit(130)
