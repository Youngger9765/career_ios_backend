#!/usr/bin/env python3
"""
測試異步報告生成機制
驗證：
1. HTTP 請求立即返回 (不阻塞)
2. 多個併發請求不會塞車
3. 背景任務正確執行
"""
import asyncio
import time
from datetime import datetime
from uuid import uuid4

import httpx


BASE_URL = "http://localhost:8000"


async def login() -> str:
    """登入並取得 token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@career.com", "password": "password123"},
        )
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.text}")
        return response.json()["access_token"]


async def create_client(token: str) -> str:
    """建立測試個案"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/clients",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": f"測試個案 {datetime.now().strftime('%H:%M:%S')}",
                "code": f"TEST{int(time.time())}",
                "age": 25,
                "gender": "male",
            },
        )
        if response.status_code != 201:
            raise Exception(f"Create client failed: {response.text}")
        return response.json()["id"]


async def create_session(token: str, client_id: str) -> str:
    """建立測試逐字稿"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "client_id": client_id,
                "session_date": datetime.now().strftime("%Y-%m-%d"),
                "transcript": "Co: 你好\nCl: 我最近工作壓力很大...",
                "duration_minutes": 50,
            },
        )
        if response.status_code != 201:
            raise Exception(f"Create session failed: {response.text}")
        return response.json()["id"]


async def generate_report(token: str, session_id: str) -> dict:
    """
    提交報告生成請求
    測試：這個請求應該在 <1 秒內返回
    """
    start_time = time.time()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/reports/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": session_id,
                "report_type": "enhanced",
                "rag_system": "openai",
            },
        )

        elapsed = time.time() - start_time

        if response.status_code != 202:
            raise Exception(f"Generate report failed: {response.text}")

        result = response.json()
        result["response_time"] = elapsed

        return result


async def check_report_status(token: str, report_id: str) -> dict:
    """查詢報告狀態"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/reports/{report_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            raise Exception(f"Check report failed: {response.text}")
        return response.json()


async def poll_until_complete(token: str, report_id: str, max_attempts: int = 20) -> dict:
    """輪詢直到報告完成"""
    for attempt in range(max_attempts):
        report = await check_report_status(token, report_id)

        print(f"  [{attempt + 1}] Status: {report['status']}")

        if report["status"] == "draft":
            return report
        elif report["status"] == "failed":
            raise Exception(f"Report generation failed: {report.get('error_message')}")

        await asyncio.sleep(3)

    raise Exception("Timeout waiting for report")


async def test_single_report():
    """測試 1: 單個報告生成"""
    print("\n" + "=" * 60)
    print("測試 1: 單個報告生成")
    print("=" * 60)

    token = await login()
    print("✅ 登入成功")

    client_id = await create_client(token)
    print(f"✅ 建立個案: {client_id}")

    session_id = await create_session(token, client_id)
    print(f"✅ 建立逐字稿: {session_id}")

    print("\n提交報告生成...")
    result = await generate_report(token, session_id)

    response_time = result["response_time"]
    report_id = result["report_id"]

    print(f"✅ HTTP 返回時間: {response_time:.2f} 秒")
    print(f"   Report ID: {report_id}")
    print(f"   Status: {result['report']['status']}")

    if response_time > 2:
        print("⚠️  警告: HTTP 回應時間過長 (應該 < 1 秒)")
    else:
        print("✅ HTTP 回應速度正常 (< 2 秒)")

    print("\n開始輪詢報告狀態...")
    final_report = await poll_until_complete(token, report_id)

    print(f"\n✅ 報告生成完成!")
    print(f"   最終狀態: {final_report['status']}")
    print(f"   品質分數: {final_report.get('quality_score', 'N/A')}")


async def test_concurrent_reports():
    """測試 2: 併發報告生成 (驗證不塞車)"""
    print("\n" + "=" * 60)
    print("測試 2: 併發 3 個報告生成")
    print("=" * 60)

    token = await login()
    print("✅ 登入成功")

    # 準備 3 個 session
    sessions = []
    for i in range(3):
        client_id = await create_client(token)
        session_id = await create_session(token, client_id)
        sessions.append(session_id)
        print(f"✅ 準備 Session {i + 1}: {session_id}")

    # 併發提交 3 個報告生成請求
    print("\n同時提交 3 個報告生成請求...")
    start_time = time.time()

    tasks = [generate_report(token, sid) for sid in sessions]
    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    print(f"\n✅ 所有請求在 {total_time:.2f} 秒內返回")

    for i, result in enumerate(results):
        print(f"   Report {i + 1}: {result['response_time']:.2f} 秒")

    if total_time > 5:
        print("❌ 失敗: 3 個請求花了超過 5 秒 (可能阻塞)")
    else:
        print("✅ 成功: 所有請求快速返回 (沒有阻塞)")

    # 等待所有報告完成
    print("\n等待所有報告生成完成...")
    for i, result in enumerate(results):
        print(f"\nReport {i + 1} ({result['report_id']}):")
        await poll_until_complete(token, result["report_id"], max_attempts=30)


async def test_response_time_comparison():
    """測試 3: 比較 HTTP 回應時間 vs 實際生成時間"""
    print("\n" + "=" * 60)
    print("測試 3: HTTP 回應時間 vs 實際生成時間")
    print("=" * 60)

    token = await login()
    client_id = await create_client(token)
    session_id = await create_session(token, client_id)

    # 提交請求
    http_start = time.time()
    result = await generate_report(token, session_id)
    http_time = time.time() - http_start

    # 等待完成
    generation_start = time.time()
    await poll_until_complete(token, result["report_id"])
    generation_time = time.time() - generation_start

    print(f"\n📊 時間對比:")
    print(f"   HTTP 回應時間: {http_time:.2f} 秒")
    print(f"   實際生成時間: {generation_time:.2f} 秒")
    print(f"   差異倍數: {generation_time / http_time:.1f}x")

    if http_time < 2 and generation_time > 10:
        print("\n✅ 異步機制正常:")
        print("   - HTTP 立即返回 (< 2 秒)")
        print("   - 背景任務耗時較長 (> 10 秒)")
        print("   - HTTP Worker 沒有被阻塞")
    else:
        print("\n⚠️ 可能有問題:")
        if http_time >= 2:
            print("   - HTTP 回應過慢")
        if generation_time <= 10:
            print("   - 生成時間異常短 (可能沒有真正調用 AI)")


async def main():
    """執行所有測試"""
    print("\n🧪 開始異步報告生成測試")
    print("⚠️  請確保 server 已啟動: uvicorn app.main:app --reload")

    try:
        # 測試 1: 單個報告
        await test_single_report()

        # 測試 2: 併發報告
        await test_concurrent_reports()

        # 測試 3: 時間對比
        await test_response_time_comparison()

        print("\n" + "=" * 60)
        print("✅ 所有測試完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
