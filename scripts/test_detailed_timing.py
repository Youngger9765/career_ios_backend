#!/usr/bin/env python3
"""
詳細計時測試 - 分解每個環節的耗時
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


async def test_detailed_timing():
    """測試每個環節的詳細計時"""

    db = SessionLocal()

    try:
        print("=" * 60)
        print("🔍 詳細計時測試")
        print("=" * 60)
        print()

        # 準備測試數據
        print("📝 準備測試數據...")
        session = (
            db.query(SessionModel).filter(SessionModel.tenant_id == "island").first()
        )

        if not session:
            print("❌ 找不到測試 session")
            return

        case = db.query(Case).filter(Case.id == session.case_id).first()
        client = db.query(Client).filter(Client.id == case.client_id).first()

        test_transcript = """
        家長：你今天在學校過得怎麼樣？
        孩子：還好啊
        家長：有什麼開心的事嗎？
        孩子：沒有
        家長：那有什麼不開心的事嗎？
        孩子：也沒有
        """

        print(f"   Session ID: {session.id}")
        print(f"   Client: {client.name}")
        print()

        # 開始詳細計時
        print("🚀 開始詳細計時測試")
        print("-" * 60)

        total_start = time.time()
        timings = {}

        # 1. 建立 context
        step_start = time.time()
        context_str = _build_context(session, client, case)
        timings["context_building"] = (time.time() - step_start) * 1000
        print(f"   1. 建立 Context: {timings['context_building']:.2f} ms")

        # 2. 建立 prompt
        step_start = time.time()
        full_transcript = session.transcript_text or "（尚無完整逐字稿）"
        prompt_template = """你是親子教養專家，分析家長與孩子的對話。

背景資訊：
{context}

完整對話逐字稿：
{full_transcript}

最近對話：
{transcript_segment}

請分析並返回 JSON 格式：
{{
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "給家長的提示文字",
    "action_suggestion": "建議採取的行動"
}}
"""
        prompt = prompt_template.format(
            context=context_str,
            full_transcript=full_transcript,
            transcript_segment=test_transcript[:500],
        )
        timings["prompt_building"] = (time.time() - step_start) * 1000
        print(f"   2. 建立 Prompt: {timings['prompt_building']:.2f} ms")

        # 3. Gemini API 調用
        step_start = time.time()
        gemini = GeminiService()
        ai_response = await gemini.generate_text(
            prompt, temperature=0.3, response_format={"type": "json_object"}
        )
        timings["gemini_api"] = (time.time() - step_start) * 1000
        print(
            f"   3. Gemini API 調用: {timings['gemini_api']:.2f} ms ({timings['gemini_api']/1000:.2f}s)"
        )

        # 4. 解析 AI response
        step_start = time.time()
        import json

        result_data = json.loads(ai_response)
        timings["response_parsing"] = (time.time() - step_start) * 1000
        print(f"   4. 解析 Response: {timings['response_parsing']:.2f} ms")

        # 5. RAG 檢索
        step_start = time.time()
        openai_service = OpenAIService()
        rag_retriever = RAGRetriever(openai_service)
        try:
            rag_results = await rag_retriever.search(
                query=test_transcript[:200],
                top_k=3,
                threshold=0.7,
                db=db,
                category="parenting",
            )
            timings["rag_retrieval"] = (time.time() - step_start) * 1000
            print(
                f"   5. RAG 檢索: {timings['rag_retrieval']:.2f} ms ({timings['rag_retrieval']/1000:.2f}s)"
            )
        except Exception as e:
            timings["rag_retrieval"] = (time.time() - step_start) * 1000
            rag_results = []
            print(
                f"   5. RAG 檢索: {timings['rag_retrieval']:.2f} ms (失敗: {str(e)[:50]}...)"
            )

        # 6. 組裝結果
        step_start = time.time()
        rag_documents = [
            {
                "doc_id": None,
                "title": r["document"],
                "content": r["text"],
                "relevance_score": r["score"],
                "chunk_id": None,
            }
            for r in rag_results
        ]
        result_data["rag_documents"] = rag_documents
        timings["result_assembly"] = (time.time() - step_start) * 1000
        print(f"   6. 組裝結果: {timings['result_assembly']:.2f} ms")

        # 總計
        total_time = (time.time() - total_start) * 1000
        timings["total"] = total_time

        print()
        print("=" * 60)
        print("📊 時間分解")
        print("=" * 60)
        print()

        # 計算所有已知步驟的時間
        known_time = sum(
            [
                timings["context_building"],
                timings["prompt_building"],
                timings["gemini_api"],
                timings["response_parsing"],
                timings["rag_retrieval"],
                timings["result_assembly"],
            ]
        )

        # 未知時間（可能是網路延遲、Python 等待等）
        unknown_time = total_time - known_time

        print(
            f"1. Context 建立:     {timings['context_building']:>8.2f} ms ({timings['context_building']/total_time*100:>5.1f}%)"
        )
        print(
            f"2. Prompt 建立:      {timings['prompt_building']:>8.2f} ms ({timings['prompt_building']/total_time*100:>5.1f}%)"
        )
        print(
            f"3. Gemini API:       {timings['gemini_api']:>8.2f} ms ({timings['gemini_api']/total_time*100:>5.1f}%) ⭐"
        )
        print(
            f"4. Response 解析:    {timings['response_parsing']:>8.2f} ms ({timings['response_parsing']/total_time*100:>5.1f}%)"
        )
        print(
            f"5. RAG 檢索:         {timings['rag_retrieval']:>8.2f} ms ({timings['rag_retrieval']/total_time*100:>5.1f}%) ⭐"
        )
        print(
            f"6. 結果組裝:         {timings['result_assembly']:>8.2f} ms ({timings['result_assembly']/total_time*100:>5.1f}%)"
        )
        print(
            f"7. 其他/未知:        {unknown_time:>8.2f} ms ({unknown_time/total_time*100:>5.1f}%)"
        )
        print("-" * 60)
        print(f"   總計:             {total_time:>8.2f} ms ({total_time/1000:.2f}s)")
        print()

        # 關鍵發現
        print("🔍 關鍵發現:")
        print(f"   • Gemini API 耗時: {timings['gemini_api']/1000:.2f}s")
        print(f"   • RAG 檢索耗時: {timings['rag_retrieval']/1000:.2f}s")
        print(
            f"   • 這兩項合計: {(timings['gemini_api'] + timings['rag_retrieval'])/1000:.2f}s"
        )
        print(f"   • 其他時間: {unknown_time/1000:.2f}s")

        if unknown_time > 1000:
            print()
            print("⚠️  警告: 有大量未知時間，可能原因：")
            print("   - 網路延遲")
            print("   - Python async/await 調度開銷")
            print("   - JSON 序列化/反序列化")
            print("   - 其他系統開銷")

    finally:
        db.close()


def _build_context(session, client, case) -> str:
    """建立 context string"""
    context_parts = []

    client_info = f"案主資訊: {client.name}"
    if client.current_status:
        client_info += f", 當前狀況: {client.current_status}"
    context_parts.append(client_info)

    case_info = f"案例目標: {case.goals or '未設定'}"
    if case.problem_description:
        case_info += f", 問題敘述: {case.problem_description}"
    context_parts.append(case_info)

    session_info = f"會談次數: 第 {session.session_number} 次"
    if session.notes:
        session_info += f", 會談備註: {session.notes}"
    context_parts.append(session_info)

    return "\n".join(context_parts)


if __name__ == "__main__":
    asyncio.run(test_detailed_timing())
