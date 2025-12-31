#!/usr/bin/env python3
"""
多次測試取平均值 - 找出真實的時間分布
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.services.gemini_service import GeminiService  # noqa: E402
from app.services.openai_service import OpenAIService  # noqa: E402
from app.services.rag_retriever import RAGRetriever  # noqa: E402


async def test_single_run(
    gemini, rag_retriever, db, session, client, case, test_transcript, run_num
):
    """單次測試"""
    print(f"\n   🔄 第 {run_num} 次測試:")

    total_start = time.time()
    timings = {}

    # Context + Prompt
    context_str = _build_context(session, client, case)
    full_transcript = session.transcript_text or "（尚無完整逐字稿）"
    prompt_template = """你是親子教養專家。

背景: {context}
完整對話: {full_transcript}
最近對話: {transcript_segment}

JSON: {{"safety_level": "green|yellow|red", "severity": 1-3}}
"""
    prompt = prompt_template.format(
        context=context_str,
        full_transcript=full_transcript,
        transcript_segment=test_transcript[:500],
    )

    # Gemini API
    gemini_start = time.time()
    await gemini.generate_text(
        prompt, temperature=0.3, response_format={"type": "json_object"}
    )
    timings["gemini"] = (time.time() - gemini_start) * 1000

    # RAG 檢索
    rag_start = time.time()
    try:
        await rag_retriever.search(
            query=test_transcript[:200],
            top_k=3,
            threshold=0.7,
            db=db,
            category="parenting",
        )
        timings["rag"] = (time.time() - rag_start) * 1000
    except Exception:
        timings["rag"] = (time.time() - rag_start) * 1000

    timings["total"] = (time.time() - total_start) * 1000

    print(f"      Gemini: {timings['gemini']:.0f} ms ({timings['gemini']/1000:.2f}s)")
    print(f"      RAG:    {timings['rag']:.0f} ms ({timings['rag']/1000:.2f}s)")
    print(f"      總計:   {timings['total']:.0f} ms ({timings['total']/1000:.2f}s)")

    return timings


async def test_timing_average():
    """測試多次取平均"""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("📊 多次測試取平均值")
        print("=" * 60)

        # 準備數據
        session = (
            db.query(SessionModel).filter(SessionModel.tenant_id == "island").first()
        )
        case = db.query(Case).filter(Case.id == session.case_id).first()
        client = db.query(Client).filter(Client.id == case.client_id).first()

        test_transcript = """
        家長：你今天在學校過得怎麼樣？
        孩子：還好啊
        家長：有什麼開心的事嗎？
        孩子：沒有
        """

        # 初始化服務
        gemini = GeminiService()
        openai_service = OpenAIService()
        rag_retriever = RAGRetriever(openai_service)

        # 測試 5 次
        print("\n🚀 開始測試（5 次）")
        print("-" * 60)

        all_results = []
        for i in range(5):
            result = await test_single_run(
                gemini, rag_retriever, db, session, client, case, test_transcript, i + 1
            )
            all_results.append(result)

            # 等待 2 秒避免 rate limiting
            if i < 4:
                await asyncio.sleep(2)

        # 統計
        print()
        print("=" * 60)
        print("📊 統計結果")
        print("=" * 60)
        print()

        gemini_times = [r["gemini"] for r in all_results]
        rag_times = [r["rag"] for r in all_results]
        total_times = [r["total"] for r in all_results]

        print("Gemini API 時間:")
        print(f"   最快: {min(gemini_times)/1000:.2f}s ({min(gemini_times):.0f} ms)")
        print(f"   最慢: {max(gemini_times)/1000:.2f}s ({max(gemini_times):.0f} ms)")
        print(
            f"   平均: {sum(gemini_times)/len(gemini_times)/1000:.2f}s ({sum(gemini_times)/len(gemini_times):.0f} ms)"
        )
        print()

        print("RAG 檢索時間:")
        print(f"   最快: {min(rag_times)/1000:.2f}s ({min(rag_times):.0f} ms)")
        print(f"   最慢: {max(rag_times)/1000:.2f}s ({max(rag_times):.0f} ms)")
        print(
            f"   平均: {sum(rag_times)/len(rag_times)/1000:.2f}s ({sum(rag_times)/len(rag_times):.0f} ms)"
        )
        print()

        print("總時間:")
        print(f"   最快: {min(total_times)/1000:.2f}s ({min(total_times):.0f} ms)")
        print(f"   最慢: {max(total_times)/1000:.2f}s ({max(total_times):.0f} ms)")
        print(
            f"   平均: {sum(total_times)/len(total_times)/1000:.2f}s ({sum(total_times)/len(total_times):.0f} ms)"
        )
        print()

        # 關鍵結論
        avg_total = sum(total_times) / len(total_times) / 1000
        avg_gemini = sum(gemini_times) / len(gemini_times) / 1000
        avg_rag = sum(rag_times) / len(rag_times) / 1000

        print("🎯 關鍵結論:")
        print(f"   ✅ 平均總時間: {avg_total:.2f}s")
        print(f"   ├─ Gemini API: {avg_gemini:.2f}s ({avg_gemini/avg_total*100:.1f}%)")
        print(f"   └─ RAG 檢索:   {avg_rag:.2f}s ({avg_rag/avg_total*100:.1f}%)")
        print()
        print(
            f"   ⚠️  Gemini 變異範圍: {min(gemini_times)/1000:.2f}s - {max(gemini_times)/1000:.2f}s"
        )
        print(
            f"        變異幅度: ±{(max(gemini_times) - min(gemini_times))/2/1000:.2f}s"
        )

    finally:
        db.close()


def _build_context(session, client, case) -> str:
    context_parts = []
    context_parts.append(f"案主: {client.name}")
    context_parts.append(f"目標: {case.goals or '未設定'}")
    context_parts.append(f"會談: 第 {session.session_number} 次")
    return "\n".join(context_parts)


if __name__ == "__main__":
    asyncio.run(test_timing_average())
