#!/usr/bin/env python3
"""
3-Minute Realtime Test - Quick verification
測試前 3 分鐘，快速驗證流程和數據
"""
import asyncio
import os
import time
from typing import Any, Dict

import httpx
from google.cloud import bigquery
from rich.console import Console
from rich.table import Table

console = Console()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SESSION_ID = f"test-3min-{int(time.time())}"

# GBQ Configuration
PROJECT_ID = os.getenv("GCS_PROJECT", "groovy-iris-473015-h3")
DATASET_ID = os.getenv("REALTIME_DATASET_ID", "realtime_logs")
TABLE_ID = os.getenv("REALTIME_TABLE_ID", "realtime_analysis_logs")

# 3-Minute Conversation Segments
SEGMENTS = [
    {
        "time_range": "0:00-1:00",
        "transcript": """寶貝，今天在學校怎麼樣？
還好啦。
老師有說什麼嗎？
沒有特別說什麼。
那數學考試怎麼樣？
還沒發下來。
喔，那等發下來跟媽媽說一聲。
好。""",
    },
    {
        "time_range": "1:00-2:00",
        "transcript": """對了，你最近功課寫到很晚，是不是遇到困難了？
還好，就是題目比較多。
需要媽媽幫忙嗎？哪一科比較難？
都還好，我自己可以。
你確定？我看你昨天寫到11點。
媽，我真的可以，不用擔心。
好吧，但如果需要幫忙一定要說喔。
嗯，我知道。""",
    },
    {
        "time_range": "2:00-3:00",
        "transcript": """咦，這是什麼？數學考卷嗎？
啊那個
65分？你上次不是考85分嗎？
這次比較難啦
怎麼會退步這麼多？發生什麼事了？
我也不知道，就是不會寫。
不會寫怎麼不問老師？還是問同學也可以啊。
我有問，但還是不太懂。""",
    },
]


async def call_api(segment: Dict[str, Any], num: int) -> bool:
    """Call realtime API"""
    payload = {
        "transcript": segment["transcript"],
        "speakers": None,  # 前端不提供
        "time_range": segment["time_range"],
        "mode": "practice",
        "provider": "gemini",
        "use_cache": True,
        "session_id": SESSION_ID,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/realtime/analyze", json=payload
            )

        if response.status_code == 200:
            data = response.json()
            console.print(
                f"✅ Minute {num}: {data['safety_level'].upper()} "
                f"({len(data.get('suggestions', []))} suggestions)",
                style="green",
            )
            return True
        else:
            console.print(f"❌ Minute {num}: Error {response.status_code}", style="red")
            return False
    except Exception as e:
        console.print(f"❌ Minute {num}: {str(e)}", style="red")
        return False


async def verify_gbq() -> None:
    """Verify GBQ data"""
    console.print("\n📊 Checking BigQuery...", style="bold cyan")

    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE session_id = @session_id
        ORDER BY analyzed_at ASC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("session_id", "STRING", SESSION_ID)
            ]
        )

        results = list(client.query(query, job_config=job_config).result())

        if not results:
            console.print("❌ No records found!", style="bold red")
            return

        console.print(f"✅ Found {len(results)} records\n", style="bold green")

        # Check critical fields
        table = Table(title="Field Verification", show_header=True)
        table.add_column("Field", style="cyan", width=30)
        table.add_column("Status", width=10)
        table.add_column("Sample", style="dim", width=50)

        first = results[0]
        critical_fields = [
            "transcript",
            "speakers",
            "system_prompt",
            "user_prompt",
            "rag_used",
            "provider",
            "model_name",
            "safety_level",
            "prompt_tokens",
            "total_tokens",
        ]

        for field in critical_fields:
            value = first.get(field)
            status = "✅" if value is not None else "❌"
            sample = str(value)[:50] if value is not None else "NULL"
            table.add_row(field, status, sample)

        console.print(table)

    except Exception as e:
        console.print(f"❌ GBQ error: {str(e)}", style="bold red")


async def main():
    console.print("\n" + "=" * 60, style="bold magenta")
    console.print("3-Minute Realtime Test (累積逐字稿)", style="bold magenta")
    console.print("=" * 60 + "\n", style="bold magenta")

    # Check API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                console.print("❌ API not healthy!", style="bold red")
                return
    except Exception:
        console.print("❌ Cannot connect to API!", style="bold red")
        return

    console.print("✅ API healthy", style="green")
    console.print(f"📱 Session: {SESSION_ID}\n", style="cyan")

    # Test 3 minutes with ACCUMULATED transcript
    console.print("🚀 Testing 3 minutes (累積模式)...\n", style="bold yellow")

    accumulated_transcript = ""
    for i, segment in enumerate(SEGMENTS, 1):
        # 累積逐字稿
        accumulated_transcript += segment["transcript"]
        if i < len(SEGMENTS):
            accumulated_transcript += "\n"

        # 創建累積版本的 segment
        accumulated_segment = {
            "time_range": segment["time_range"],
            "transcript": accumulated_transcript,
        }

        console.print(
            f"⏱️  Minute {i}: {segment['time_range']} "
            f"(累積 {len(accumulated_transcript)} chars)",
            style="bold blue",
        )
        await call_api(accumulated_segment, i)

        if i < len(SEGMENTS):
            console.print("  ⏳ Waiting 3 seconds...", style="dim")
            await asyncio.sleep(3)

    # Wait for GBQ write
    console.print("\n⏳ Waiting 5 seconds for GBQ write...", style="yellow")
    await asyncio.sleep(5)

    # Verify
    await verify_gbq()

    console.print("\n✅ Test complete!", style="bold green")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n⚠️  Interrupted", style="yellow")
