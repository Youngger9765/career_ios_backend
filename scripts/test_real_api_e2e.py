#!/usr/bin/env python3
"""
真實 API 端到端速度測試

測試完整流程：
前端 → 後端 → DB 查詢 → RAG 檢索 → Gemini 分析 → GBQ 寫入 → 回傳前端
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.models.counselor import Counselor  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.services.keyword_analysis_service import KeywordAnalysisService  # noqa: E402


async def test_real_api_flow():
    """測試真實的 analyze-partial 完整流程"""

    db = SessionLocal()

    try:
        print("=" * 60)
        print("🧪 真實 API 端到端速度測試")
        print("=" * 60)
        print()

        # 步驟 1: 準備測試數據（模擬真實場景）
        print("📝 準備測試數據...")

        # 找一個真實的 session（island 租戶）
        session = (
            db.query(SessionModel).filter(SessionModel.tenant_id == "island").first()
        )

        if not session:
            print("❌ 找不到 island 租戶的 session")
            return

        # 獲取關聯的 client 和 case
        case = db.query(Case).filter(Case.id == session.case_id).first()
        client = db.query(Client).filter(Client.id == case.client_id).first()
        counselor = (
            db.query(Counselor).filter(Counselor.id == case.counselor_id).first()
        )

        print(f"   Session ID: {session.id}")
        print(f"   Client: {client.name}")
        print(f"   Tenant: {session.tenant_id}")
        print()

        # 步驟 2: 測試 analyze-partial API（完整流程）
        print("🚀 測試 analyze-partial API 完整流程")
        print("-" * 60)

        test_transcript = """
        家長：你今天在學校過得怎麼樣？
        孩子：還好啊
        家長：有什麼開心的事嗎？
        孩子：沒有
        家長：那有什麼不開心的事嗎？
        孩子：也沒有
        家長：你確定嗎？感覺你好像有點不開心？
        孩子：就還好啊，沒什麼特別的
        """

        service = KeywordAnalysisService(db)

        # 測試 3 次取平均
        times = []
        for i in range(3):
            print(f"\n   🔄 第 {i+1} 次測試:")

            start = time.time()

            # 完整流程（包含所有步驟）
            result = await service.analyze_partial(
                session=session,
                client=client,
                case=case,
                transcript_segment=test_transcript,
                counselor_id=counselor.id,
                tenant_id=session.tenant_id,
            )

            elapsed = time.time() - start
            times.append(elapsed)

            print(f"   ⏱️  總耗時: {elapsed*1000:.0f} ms ({elapsed:.2f}s)")
            print(f"   📊 Safety Level: {result.get('safety_level')}")
            print(f"   📊 建議數: {len(result.get('suggested_responses', []))}")

            # 等待 2 秒再測下一次（避免 rate limiting）
            if i < 2:
                await asyncio.sleep(2)

        # 統計
        print()
        print("=" * 60)
        print("📊 測試結果統計")
        print("=" * 60)
        print()

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"平均耗時: {avg_time:.2f}s ({avg_time*1000:.0f} ms)")
        print(f"最快: {min_time:.2f}s ({min_time*1000:.0f} ms)")
        print(f"最慢: {max_time:.2f}s ({max_time*1000:.0f} ms)")
        print()

        # 分解時間（估算）
        print("⏱️  時間分解（估算）:")
        print("   1. DB 查詢（Session, Client, Case）: ~100-200ms")
        print("   2. RAG 檢索: ~500-1000ms")
        print("   3. Gemini 分析: ~3000-5000ms")
        print("   4. GBQ 寫入: ~200-500ms")
        print("   5. Response 組裝: ~50-100ms")
        print(f"   總計: {avg_time*1000:.0f} ms（實測）")
        print()

        # 與用戶報告的 15 秒對比
        if avg_time > 10:
            print("⚠️  警告: 實測時間超過 10 秒")
            print("   用戶報告: ~15 秒")
            print(f"   實測: ~{avg_time:.1f} 秒")
            print(f"   差異: {15 - avg_time:.1f} 秒（可能是網路延遲或前端處理）")
        else:
            print("✅ 實測時間合理")
            if avg_time < 15:
                print("   用戶報告: ~15 秒")
                print(f"   實測（後端）: ~{avg_time:.1f} 秒")
                print(f"   缺少的時間: ~{15 - avg_time:.1f} 秒")
                print("   可能原因: 網路延遲 + 前端處理 + DB 連線建立")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_real_api_flow())
