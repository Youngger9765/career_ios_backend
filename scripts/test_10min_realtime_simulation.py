#!/usr/bin/env python3
"""
10-Minute Realtime Conversation Simulation

模擬真實的 realtime 分析流程：
- 10 分鐘的親子對話
- 每分鐘發送一次 API 請求
- 驗證 GBQ 所有欄位都有正確的資料（不是 NULL）
"""
import asyncio
import os
import time
from typing import Any, Dict

import httpx
from google.cloud import bigquery
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

console = Console()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SESSION_ID = f"realtime-10min-{int(time.time())}"

# GBQ Configuration
PROJECT_ID = os.getenv("GCS_PROJECT", "groovy-iris-473015-h3")
DATASET_ID = os.getenv("REALTIME_DATASET_ID", "realtime_logs")
TABLE_ID = os.getenv("REALTIME_TABLE_ID", "realtime_analysis_logs")

# 10-Minute Parent-Child Conversation (Realistic Scenario)
# 情境：媽媽發現孩子成績下滑，從關心到焦慮到指責的過程
CONVERSATION_SEGMENTS = [
    # Minute 1: 平靜開場
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
    # Minute 2: 開始發現問題
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
    # Minute 3: 發現成績
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
    # Minute 4: 焦慮升高
    {
        "time_range": "3:00-4:00",
        "transcript": """這樣下去不行啊，馬上就要段考了。
我知道
知道還考這樣？你到底有沒有認真讀書？
有啊，我每天都有讀。
那怎麼會退步20分？你老實說，是不是上課沒專心？
我有專心只是有些地方真的聽不懂。
聽不懂要舉手問啊！老師就在那邊，你不問怎麼會？
我我不敢問。""",
    },
    # Minute 5: 開始比較
    {
        "time_range": "4:00-5:00",
        "transcript": """不敢問？有什麼好不敢的？你看隔壁小明，成績一直都很好。
小明本來就比較聰明
什麼叫比較聰明？你們同一個老師教的，怎麼人家就會你就不會？
我也不知道
是不是下課都在玩，沒有複習？
沒有啦，我有複習。
那複習怎麼還是不會？你到底有沒有用心？
媽，你不要一直唸我好不好""",
    },
    # Minute 6: 情緒升溫
    {
        "time_range": "5:00-6:00",
        "transcript": """什麼叫不要一直唸你？媽媽這是為你好！
我知道，可是
可是什麼？你知道補習費多貴嗎？結果你還考這樣？
對不起
對不起有什麼用？你爸爸那麼辛苦賺錢，你就這樣浪費？
我沒有浪費，我真的有努力
努力？努力的人會考65分？你看看人家班上前三名，哪個不是努力的？
我真的我真的有努力""",
    },
    # Minute 7: 達到高峰（RED zone）
    {
        "time_range": "6:00-7:00",
        "transcript": """哭什麼哭！哭能解決問題嗎？
嗚嗚嗚
你就是太軟弱了！遇到困難就只會哭！
我我不想這樣
不想這樣就去讀書啊！整天就知道玩手機，成績當然爛！
我沒有一直玩手機
沒有？那你成績怎麼會這麼差？你是不是覺得自己很笨？
我就是笨！我什麼都做不好！
你給我閉嘴！再哭我就把你手機沒收！""",
    },
    # Minute 8: 開始冷靜（但仍有問題）
    {
        "time_range": "7:00-8:00",
        "transcript": """嗚嗚
好了好了，不要哭了。
媽媽知道你有壓力，但是你要理解媽媽的苦心。
嗯
下次考試要加油，不能再這樣了，知道嗎？
知道了
去把眼淚擦一擦，等一下吃飯。
好。""",
    },
    # Minute 9: 嘗試修復關係（但方法不當）
    {
        "time_range": "8:00-9:00",
        "transcript": """對了，媽媽幫你報名了數學加強班。
什麼？我已經有補習了
那個不夠，這個是專門針對你這種成績不好的。
可是我已經很累了
累什麼累？你看人家資優班的，課程更多還不是一樣應付？
我不是資優班的
所以你才更需要補習啊！不然怎麼追得上？
可是媽，我真的好累
累也要撐著！以後你就知道媽媽是為你好。""",
    },
    # Minute 10: 結束（問題未解決）
    {
        "time_range": "9:00-10:00",
        "transcript": """怎麼不說話？
沒什麼
好了，去洗手準備吃飯。下週六開始上課，記得空出時間。
知道了
還有，這週末把數學第三章全部複習一遍。
好
不要再讓媽媽失望了，聽到沒有？
聽到了我去洗手了。
嗯，去吧。""",
    },
]


async def call_realtime_api(segment: Dict[str, Any], segment_num: int) -> bool:
    """Call realtime API for one conversation segment"""
    payload = {
        "transcript": segment["transcript"],
        "speakers": None,  # 前端不會提供 speaker 身份識別
        "time_range": segment["time_range"],
        "mode": "practice",  # 使用 practice mode 進行分析
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
                f"  Segment {segment_num}: ✅ {data['safety_level'].upper()} "
                f"({len(data.get('suggestions', []))} suggestions)",
                style="green",
            )
            return True
        else:
            console.print(
                f"  Segment {segment_num}: ❌ Error {response.status_code}",
                style="red",
            )
            return False

    except Exception as e:
        console.print(f"  Segment {segment_num}: ❌ {str(e)}", style="red")
        return False


async def verify_gbq_data() -> None:
    """Verify all records are in BigQuery with non-NULL values"""
    console.print("\n📊 Verifying BigQuery data...", style="bold cyan")

    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

        # Query all records for this session
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

        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())

        if not results:
            console.print("❌ No records found in BigQuery!", style="bold red")
            return

        console.print(
            f"✅ Found {len(results)} records in BigQuery\n", style="bold green"
        )

        # Check for NULL values in critical fields
        critical_fields = [
            "transcript",
            "speakers",
            "system_prompt",
            "user_prompt",
            "rag_used",
            "provider",
            "model_name",
            "start_time",
            "end_time",
            "duration_ms",
            "safety_level",
            "llm_raw_response",
            "analysis_result",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "use_cache",
            "mode",
        ]

        # Create verification table
        table = Table(
            title="📋 GBQ Data Verification",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Field", style="cyan", width=30)
        table.add_column("Non-NULL Count", style="green", width=15)
        table.add_column("NULL Count", style="red", width=15)
        table.add_column("Status", style="yellow", width=10)

        null_fields = []

        for field in critical_fields:
            non_null_count = sum(1 for row in results if row.get(field) is not None)
            null_count = len(results) - non_null_count
            status = "✅" if null_count == 0 else "❌"

            if null_count > 0:
                null_fields.append(field)

            table.add_row(
                field,
                str(non_null_count),
                str(null_count),
                status,
                style="green" if null_count == 0 else "red",
            )

        console.print(table)

        # Summary
        if null_fields:
            console.print(
                f"\n⚠️ Found NULL values in {len(null_fields)} fields:",
                style="bold yellow",
            )
            for field in null_fields:
                console.print(f"  - {field}", style="yellow")
        else:
            console.print(
                "\n🎉 All critical fields have data! No NULLs found.",
                style="bold green",
            )

        # Show sample data from first record
        console.print("\n📝 Sample Record (First Segment):", style="bold cyan")
        first_record = results[0]

        sample_table = Table(show_header=True, header_style="bold magenta")
        sample_table.add_column("Field", style="cyan", width=30)
        sample_table.add_column("Value", style="white", width=80)

        for field in critical_fields:
            value = first_record.get(field)
            if value is None:
                display_value = "NULL"
            elif isinstance(value, str) and len(value) > 100:
                display_value = f"{value[:100]}..."
            else:
                display_value = str(value)[:100]

            sample_table.add_row(field, display_value)

        console.print(sample_table)

    except Exception as e:
        console.print(f"❌ GBQ verification failed: {str(e)}", style="bold red")


async def main():
    """Main test flow"""
    console.print("\n" + "=" * 80, style="bold magenta")
    console.print("10-Minute Realtime Conversation Simulation", style="bold magenta")
    console.print("=" * 80 + "\n", style="bold magenta")

    # Check API health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                console.print("❌ API is not healthy!", style="bold red")
                return
    except Exception as e:
        console.print(f"❌ Cannot connect to API: {str(e)}", style="bold red")
        return

    console.print("✅ API is healthy", style="bold green")
    console.print(f"📱 Session ID: {SESSION_ID}\n", style="bold cyan")

    # Send 10 segments (1 per minute simulation)
    console.print(
        "🚀 Starting 10-minute conversation simulation (累積模式)...\n",
        style="bold yellow",
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Sending segments...", total=len(CONVERSATION_SEGMENTS)
        )

        success_count = 0
        # Test 10 minutes with ACCUMULATED transcript (累積模式)
        accumulated_transcript = ""
        for i, segment in enumerate(CONVERSATION_SEGMENTS, 1):
            # 累積逐字稿
            accumulated_transcript += segment["transcript"]
            if i < len(CONVERSATION_SEGMENTS):
                accumulated_transcript += "\n"

            # 創建累積版本的 segment
            accumulated_segment = {
                "time_range": segment["time_range"],
                "transcript": accumulated_transcript,
            }

            console.print(
                f"\n⏱️  Minute {i}: {segment['time_range']} "
                f"(累積 {len(accumulated_transcript)} chars)",
                style="bold blue",
            )

            # Call API with accumulated transcript
            success = await call_realtime_api(accumulated_segment, i)
            if success:
                success_count += 1

            # Wait for background task to complete (GBQ write)
            if i < len(CONVERSATION_SEGMENTS):
                console.print("  ⏳ Waiting 3 seconds for GBQ write...", style="dim")
                await asyncio.sleep(3)

            progress.update(task, advance=1)

    # Final wait for last segment
    console.print("\n⏳ Waiting 5 seconds for final GBQ write...", style="yellow")
    await asyncio.sleep(5)

    # Summary
    console.print("\n" + "=" * 80, style="bold magenta")
    console.print(
        f"✅ Sent {success_count}/{len(CONVERSATION_SEGMENTS)} segments successfully",
        style="bold green",
    )
    console.print("=" * 80 + "\n", style="bold magenta")

    # Verify GBQ data
    await verify_gbq_data()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n⚠️ Test interrupted by user", style="bold yellow")
