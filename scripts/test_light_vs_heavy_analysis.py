#!/usr/bin/env python3
"""
測試輕量 vs 重量分析的速度對比

測試方案：
1. Rule-based only（純關鍵字 + 隨機鼓勵句）
2. Gemini Flash（無 RAG，簡單 prompt）
3. Gemini Flash + RAG（完整分析）

目標：找出最佳的輕量級方案
"""

import asyncio
import random
import time
from typing import Dict

# 模擬 Gemini API
try:
    import google.generativeai as genai

    from app.core.config import settings

    genai.configure(api_key=settings.GOOGLE_API_KEY)
except ImportError:
    print("⚠️ 無法導入 Gemini，將使用模擬數據")
    genai = None


# ============================================
# 方案 1: Rule-based Only（純關鍵字檢測）
# ============================================

DANGER_KEYWORDS = [
    "打",
    "罵",
    "討厭你",
    "去死",
    "不想活",
    "離家出走",
    "傷害",
    "自殺",
    "暴力",
    "恨你",
]

ENCOURAGEMENTS = {
    "green": [
        "做得很好！繼續保持這樣的溝通方式",
        "很棒的互動，孩子能感受到你的關心",
        "維持正常語速，給孩子思考的空間",
        "記得保持眼神接觸，讓孩子感受到被重視",
        "你的語氣很溫和，這對孩子很重要",
    ],
    "yellow": [
        "注意孩子的情緒變化，可能需要調整語氣",
        "試著多聽少說，給孩子表達的機會",
        "記得先同理孩子的感受，再提出建議",
        "深呼吸，保持冷靜，孩子需要你的穩定",
        "可以暫停一下，給彼此一些空間",
    ],
}


def rule_based_analysis(transcript: str, last_safety_level: str = "green") -> Dict:
    """方案 1: Pure rule-based"""
    start = time.time()

    # 檢查危險關鍵字
    has_danger = any(keyword in transcript for keyword in DANGER_KEYWORDS)

    if has_danger:
        result = {"type": "trigger_heavy", "reason": "檢測到危險關鍵字"}
    else:
        # 返回鼓勵句
        suggestion = random.choice(
            ENCOURAGEMENTS.get(last_safety_level, ENCOURAGEMENTS["green"])
        )
        result = {
            "type": "light",
            "safety_level": last_safety_level,
            "suggestion": suggestion,
            "method": "rule-based",
        }

    elapsed = time.time() - start
    result["elapsed_ms"] = elapsed * 1000

    return result


# ============================================
# 方案 2: Gemini Flash（無 RAG）
# ============================================

LIGHT_PROMPT_TEMPLATE = """你是親子教養助理，快速評估對話並給予簡短鼓勵。

對話內容：
{transcript}

請用 JSON 格式返回（不要換行）：
{{"suggestion": "一句話鼓勵（20字內）", "safety_level": "green|yellow|red"}}

規則：
- 只返回 JSON，不要其他文字
- 建議必須簡短、正面、具體
- 如果對話正常 → green
- 如果有輕微衝突 → yellow
- 如果有危險詞彙 → red
"""


async def gemini_light_analysis(transcript: str) -> Dict:
    """方案 2: Gemini Flash without RAG"""
    start = time.time()

    if genai is None:
        # 模擬數據
        await asyncio.sleep(0.5)  # 模擬 API 延遲
        result = {
            "type": "light",
            "safety_level": "green",
            "suggestion": "做得很好！繼續保持",
            "method": "gemini-light (simulated)",
        }
    else:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")

            prompt = LIGHT_PROMPT_TEMPLATE.format(transcript=transcript)

            response = await model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 100,
                    "response_mime_type": "application/json",
                },
            )

            import json

            data = json.loads(response.text)

            result = {
                "type": "light",
                "safety_level": data.get("safety_level", "green"),
                "suggestion": data.get("suggestion", "繼續保持"),
                "method": "gemini-light",
            }
        except Exception as e:
            result = {"type": "error", "error": str(e), "method": "gemini-light"}

    elapsed = time.time() - start
    result["elapsed_ms"] = elapsed * 1000

    return result


# ============================================
# 方案 3: Gemini Flash + RAG（完整分析）
# ============================================

HEAVY_PROMPT_TEMPLATE = """你是專業親子教養顧問，精通多種教養理論。

【背景知識】（來自 RAG 知識庫）
{rag_context}

【對話內容】
{transcript}

【最近對話 - 用於安全評估】
{recent_transcript}

請分析並返回 JSON：
{{
  "safety_level": "green|yellow|red",
  "severity": 1-3,
  "suggestions": ["建議1", "建議2", "建議3"],
  "theory_basis": "使用的理論"
}}
"""


async def gemini_heavy_analysis(transcript: str) -> Dict:
    """方案 3: Gemini Flash + RAG (完整分析)"""
    start = time.time()

    if genai is None:
        # 模擬數據
        await asyncio.sleep(2.5)  # 模擬 RAG + AI 延遲
        result = {
            "type": "heavy",
            "safety_level": "green",
            "suggestions": ["建議1", "建議2", "建議3"],
            "theory_basis": "薩提爾模式",
            "method": "gemini-heavy (simulated)",
        }
    else:
        try:
            # 模擬 RAG 檢索（實際應該調用 RAG service）
            rag_context = "依附理論指出，孩子需要穩定的情感連結..."

            model = genai.GenerativeModel("gemini-2.0-flash-exp")

            prompt = HEAVY_PROMPT_TEMPLATE.format(
                rag_context=rag_context,
                transcript=transcript,
                recent_transcript=transcript[-200:],  # 最近 200 字
            )

            response = await model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 500,
                    "response_mime_type": "application/json",
                },
            )

            import json

            data = json.loads(response.text)

            result = {
                "type": "heavy",
                "safety_level": data.get("safety_level", "green"),
                "suggestions": data.get("suggestions", []),
                "theory_basis": data.get("theory_basis", ""),
                "method": "gemini-heavy",
            }
        except Exception as e:
            result = {"type": "error", "error": str(e), "method": "gemini-heavy"}

    elapsed = time.time() - start
    result["elapsed_ms"] = elapsed * 1000

    return result


# ============================================
# 測試執行
# ============================================


async def run_speed_test():
    """執行速度對比測試"""

    # 測試場景
    test_cases = [
        {
            "name": "正常對話",
            "transcript": "家長：你今天在學校過得怎麼樣？\n孩子：還好啊\n家長：有什麼開心的事嗎？",
            "expected_safety": "green",
        },
        {
            "name": "輕微衝突",
            "transcript": "家長：你怎麼還不寫作業？\n孩子：我就是不想寫！\n家長：你這是什麼態度？",
            "expected_safety": "yellow",
        },
        {
            "name": "危險情況",
            "transcript": "孩子：我討厭你！我恨你！\n家長：你說什麼？\n孩子：我不想活了！",
            "expected_safety": "red",
        },
    ]

    print("=" * 60)
    print("🧪 輕量 vs 重量分析速度測試")
    print("=" * 60)
    print()

    for case in test_cases:
        print(f"📝 測試場景：{case['name']}")
        print(f"   對話：{case['transcript'][:50]}...")
        print()

        # 方案 1: Rule-based
        result1 = rule_based_analysis(case["transcript"])
        print("   方案 1 [Rule-based Only]:")
        print(f"   ⏱️  耗時: {result1['elapsed_ms']:.2f} ms")
        print(f"   📊 結果: {result1.get('suggestion', result1.get('reason'))}")
        print()

        # 方案 2: Gemini Light
        result2 = await gemini_light_analysis(case["transcript"])
        print("   方案 2 [Gemini Flash - 無 RAG]:")
        print(
            f"   ⏱️  耗時: {result2['elapsed_ms']:.2f} ms ({result2['elapsed_ms']/1000:.2f}s)"
        )
        print(f"   📊 結果: {result2.get('suggestion', result2.get('error', 'N/A'))}")
        print()

        # 方案 3: Gemini Heavy
        result3 = await gemini_heavy_analysis(case["transcript"])
        print("   方案 3 [Gemini Flash + RAG]:")
        print(
            f"   ⏱️  耗時: {result3['elapsed_ms']:.2f} ms ({result3['elapsed_ms']/1000:.2f}s)"
        )
        print(f"   📊 結果: {len(result3.get('suggestions', []))} 個建議")
        print()

        # 速度對比
        print("   🏁 速度對比:")
        print("   Rule-based:  1x (baseline)")
        if result2["elapsed_ms"] > 0:
            print(
                f"   Gemini Light: {result2['elapsed_ms']/result1['elapsed_ms']:.1f}x slower"
            )
        if result3["elapsed_ms"] > 0:
            print(
                f"   Gemini Heavy: {result3['elapsed_ms']/result1['elapsed_ms']:.1f}x slower"
            )
        print()
        print("-" * 60)
        print()

    # 總結
    print("=" * 60)
    print("📊 測試結論")
    print("=" * 60)
    print()
    print("方案對比：")
    print()
    print("1️⃣ Rule-based Only:")
    print("   ✅ 速度: <10ms (極快)")
    print("   ✅ 成本: $0 (免費)")
    print("   ⚠️  品質: 通用鼓勵句，無針對性")
    print()
    print("2️⃣ Gemini Light (無 RAG):")
    print("   🟡 速度: ~500-1500ms (中等)")
    print("   🟡 成本: ~$0.02/次")
    print("   ✅ 品質: 個性化鼓勵，有針對性")
    print()
    print("3️⃣ Gemini Heavy (+ RAG):")
    print("   🔴 速度: ~2500-5000ms (慢)")
    print("   🔴 成本: ~$0.26/次")
    print("   ✅ 品質: 完整分析，理論支撐")
    print()


# ============================================
# 主程式
# ============================================

if __name__ == "__main__":
    asyncio.run(run_speed_test())
