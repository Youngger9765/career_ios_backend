#!/usr/bin/env python3
"""
真實 Gemini API 速度測試
"""

import asyncio
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gemini_service import GeminiService  # noqa: E402


async def test_gemini_light():
    """測試 Gemini Flash（無 RAG）- 輕量版"""

    gemini = GeminiService()

    prompt = """你是親子教養助理，快速評估對話並給予簡短鼓勵。

對話內容：
家長：你今天在學校過得怎麼樣？
孩子：還好啊
家長：有什麼開心的事嗎？

請用 JSON 格式返回：
{"suggestion": "一句話鼓勵（20字內）", "safety_level": "green"}

規則：
- 只返回 JSON
- 建議必須簡短、正面、具體
"""

    print("🧪 測試 Gemini Light（無 RAG）")
    print("-" * 60)

    # 測試 3 次取平均
    times = []
    for i in range(3):
        start = time.time()

        try:
            response = await gemini.generate_text(
                prompt=prompt,
                temperature=0.3,
                max_tokens=100,
                response_format={"type": "json_object"},
            )

            elapsed = time.time() - start
            times.append(elapsed)

            print(f"   第 {i+1} 次: {elapsed*1000:.0f} ms ({elapsed:.2f}s)")
            print(f"   回應: {response[:100]}...")
            print()

        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
            break

    if times:
        avg_time = sum(times) / len(times)
        print(f"   📊 平均耗時: {avg_time*1000:.0f} ms ({avg_time:.2f}s)")

    return times


async def test_gemini_heavy():
    """測試 Gemini Flash + RAG（完整版）"""

    gemini = GeminiService()

    # 模擬包含 RAG context 的完整 prompt
    prompt = """你是專業親子教養顧問，精通多種教養理論。

【背景知識】（來自 RAG 知識庫）
依附理論指出，孩子需要穩定的情感連結。當家長能夠敏感地回應孩子的需求時，孩子會發展出安全型依附。薩提爾模式強調冰山理論，表面行為底下有感受、觀點、期待和渴望。阿德勒正向教養主張溫和且堅定，使用自然後果取代懲罰。

【完整對話逐字稿】
家長：你今天在學校過得怎麼樣？
孩子：還好啊
家長：有什麼開心的事嗎？
孩子：沒有
家長：那有什麼不開心的事嗎？
孩子：也沒有

【最近對話 - 用於安全評估】
家長：有什麼開心的事嗎？
孩子：沒有
家長：那有什麼不開心的事嗎？
孩子：也沒有

請分析並返回 JSON：
{
  "safety_level": "green",
  "severity": 1,
  "suggestions": ["建議1", "建議2", "建議3"],
  "theory_basis": "使用的理論"
}
"""

    print("🧪 測試 Gemini Heavy（+ RAG）")
    print("-" * 60)

    # 測試 3 次取平均
    times = []
    for i in range(3):
        start = time.time()

        try:
            response = await gemini.generate_text(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            elapsed = time.time() - start
            times.append(elapsed)

            print(f"   第 {i+1} 次: {elapsed*1000:.0f} ms ({elapsed:.2f}s)")
            print(f"   回應: {response[:100]}...")
            print()

        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
            break

    if times:
        avg_time = sum(times) / len(times)
        print(f"   📊 平均耗時: {avg_time*1000:.0f} ms ({avg_time:.2f}s)")

    return times


async def main():
    """主測試流程"""

    print("=" * 60)
    print("🚀 真實 Gemini API 速度測試")
    print("=" * 60)
    print()

    # 測試輕量版
    light_times = await test_gemini_light()
    print()

    # 測試重量版
    heavy_times = await test_gemini_heavy()
    print()

    # 總結
    if light_times and heavy_times:
        light_avg = sum(light_times) / len(light_times)
        heavy_avg = sum(heavy_times) / len(heavy_times)

        print("=" * 60)
        print("📊 測試總結")
        print("=" * 60)
        print()
        print(f"輕量版（無 RAG）: {light_avg:.2f}s ({light_avg*1000:.0f} ms)")
        print(f"重量版（+ RAG）:  {heavy_avg:.2f}s ({heavy_avg*1000:.0f} ms)")
        print()
        print(f"速度差異: {heavy_avg/light_avg:.1f}x")
        print()
        print("建議的間隔時間：")
        print(f"  輕量提示: {max(5, int(light_avg))} 秒")
        print(f"  重度分析: {max(30, int(heavy_avg*1.5))} 秒")


if __name__ == "__main__":
    asyncio.run(main())
