#!/usr/bin/env python3
"""
測試 8 大流派 Practice Mode Prompt

測試 5 個真實親子互動場景：
1. 孩子拒絕寫作業
2. 手足衝突
3. 情緒崩潰（哭鬧）
4. 挑戰權威（頂嘴）
5. 分離焦慮

輸出：
- Token 用量
- Response 時間
- detailed_scripts 範例
- 理論來源標註
- 與舊 prompt 的比較

使用方式：
    cd /Users/young/project/career_ios_backend
    poetry run python scripts/test_8_schools_prompt.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from app.prompts.island_parents_8_schools_emergency_v1 import (
    ISLAND_PARENTS_8_SCHOOLS_EMERGENCY_PROMPT,
)
from app.prompts.island_parents_8_schools_emergency_v1 import (
    PROMPT_METADATA as EMERGENCY_METADATA,
)
from app.prompts.island_parents_8_schools_practice_v1 import (
    ISLAND_PARENTS_8_SCHOOLS_PRACTICE_PROMPT,
)
from app.prompts.island_parents_8_schools_practice_v1 import (
    PROMPT_METADATA as PRACTICE_METADATA,
)
from app.services.gemini_service import GeminiService

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ==============================================================================
# 測試場景定義
# ==============================================================================

TEST_SCENARIOS = [
    {
        "id": 1,
        "name": "孩子拒絕寫作業",
        "context": """案主資訊: 王媽媽, 當前狀況: 7歲兒子不願意寫作業
案例目標: 改善親子溝通，減少作業衝突
會談次數: 第 2 次, 會談備註: 上次討論過正向教養技巧""",
        "full_transcript": """（之前對話）
媽媽：今天下午孩子放學回來，我叫他寫作業，他說不要。
諮詢師：那時候你怎麼回應的呢？
媽媽：我就說「不寫不行啊，老師會罵」，他就開始哭。""",
        "transcript_segment": """媽媽：我今天又試著叫他寫作業，他還是說不要。
孩子：（躺在沙發上）我不想寫！我好累！
媽媽：你每天都說累，功課還是要寫啊！
孩子：（開始煩躁）我就是不想寫啦！你每天都逼我！
媽媽：（語氣開始急躁）我不是逼你，是你自己的功課啊！""",
        "expected_severity": 2,  # YELLOW
        "expected_theories": ["薩提爾模式", "Dr. Becky Kennedy", "阿德勒正向教養"],
    },
    {
        "id": 2,
        "name": "手足衝突",
        "context": """案主資訊: 林媽媽, 當前狀況: 5歲姐姐和3歲弟弟經常搶玩具
案例目標: 建立手足相處規則，培養同理心
會談次數: 第 1 次""",
        "full_transcript": "（首次諮詢，尚無先前對話）",
        "transcript_segment": """媽媽：姐姐和弟弟又在搶玩具了。
姐姐：（大叫）這是我的！你不可以拿！
弟弟：（哭）我也要玩！
姐姐：（推開弟弟）你走開啦！
媽媽：（大聲）不要推弟弟！你是姐姐要讓弟弟！
姐姐：（委屈）為什麼每次都要我讓！""",
        "expected_severity": 2,  # YELLOW
        "expected_theories": ["情緒輔導", "協作解決問題", "社會意識與價值觀教養"],
    },
    {
        "id": 3,
        "name": "情緒崩潰（哭鬧）",
        "context": """案主資訊: 陳爸爸, 當前狀況: 4歲女兒容易情緒失控
案例目標: 學習情緒調節技巧
會談次數: 第 3 次, 會談備註: 已討論全腦教養概念""",
        "full_transcript": """（之前對話）
爸爸：上次你說的「下層腦」我有注意到，女兒生氣時真的很難講道理。
諮詢師：對，這時候要先安撫情緒，等她冷靜了再溝通。""",
        "transcript_segment": """爸爸：今天帶她去賣場，她要買玩具，我說不行。
女兒：（開始哭鬧）我要買！我要買！
爸爸：（蹲下）我知道你很想要，但是...
女兒：（大哭）你每次都說不行！我討厭你！（躺在地上打滾）
爸爸：（有點慌）好了好了，不要哭了，大家都在看...
女兒：（哭得更大聲）我就是要買！""",
        "expected_severity": 3,  # RED
        "expected_theories": ["人際神經生物學", "情緒輔導", "Dr. Becky Kennedy"],
    },
    {
        "id": 4,
        "name": "挑戰權威（頂嘴）",
        "context": """案主資訊: 張媽媽, 當前狀況: 9歲兒子開始頂嘴
案例目標: 建立溫和而堅定的界線
會談次數: 第 1 次""",
        "full_transcript": "（首次諮詢，尚無先前對話）",
        "transcript_segment": """媽媽：我叫他去洗澡，他說「等一下」。
孩子：我再玩5分鐘就去！
媽媽：現在就去，不然水會冷掉。
孩子：（不耐煩）你很煩耶！我說等一下就等一下！
媽媽：（生氣）你跟誰說話呢！你怎麼可以這樣跟媽媽講話！
孩子：你也很煩啊！每次都這樣！""",
        "expected_severity": 2,  # YELLOW
        "expected_theories": ["阿德勒正向教養", "協作解決問題", "薩提爾模式"],
    },
    {
        "id": 5,
        "name": "分離焦慮",
        "context": """案主資訊: 劉媽媽, 當前狀況: 3歲兒子送托嬰時哭鬧
案例目標: 緩解分離焦慮，建立安全感
會談次數: 第 2 次, 會談備註: 上次討論過依附理論""",
        "full_transcript": """（之前對話）
媽媽：他每次送去托嬰都哭得很慘，我也很捨不得。
諮詢師：分離焦慮是正常的，我們可以建立一些儀式來幫助他。""",
        "transcript_segment": """媽媽：今天早上送他去托嬰，他又開始哭了。
孩子：（緊抱媽媽）我不要去！我要跟媽媽！
媽媽：（溫柔但焦急）寶貝乖，媽媽下午就來接你...
孩子：（哭）不要！我不要你走！
老師：（過來接）來，我們去玩玩具...
孩子：（大哭，掙扎）媽媽不要走！媽媽！
媽媽：（眼眶泛紅，不知所措）怎麼辦...要不要今天不去了？""",
        "expected_severity": 2,  # YELLOW (雖然哭鬧，但屬於發展正常範圍)
        "expected_theories": ["現代依附與內在觀點", "情緒輔導", "人際神經生物學"],
    },
]


# ==============================================================================
# 測試函數
# ==============================================================================


async def test_practice_prompt(scenario: dict) -> dict:
    """使用 Practice Mode prompt 測試單一場景"""
    print(f"\n{'='*80}")
    print(f"場景 {scenario['id']}: {scenario['name']} (Practice Mode)")
    print(f"{'='*80}")

    # 組裝 prompt
    prompt = ISLAND_PARENTS_8_SCHOOLS_PRACTICE_PROMPT.format(
        context=scenario["context"],
        full_transcript=scenario["full_transcript"],
        transcript_segment=scenario["transcript_segment"],
    )

    # 記錄開始時間
    start_time = time.time()

    # 調用 Gemini
    gemini_service = GeminiService()
    try:
        ai_response = await gemini_service.generate_text(
            prompt, temperature=0.3, response_format={"type": "json_object"}
        )

        # 記錄結束時間
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # 解析 response
        response_text = (
            ai_response.text if hasattr(ai_response, "text") else str(ai_response)
        )

        # 提取 JSON
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            result_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗: {e}")
            result_data = {
                "error": "JSON parse failed",
                "raw_response": response_text[:500],
            }

        # 提取 token 使用量
        token_usage = getattr(ai_response, "usage_metadata", None)
        if token_usage:
            prompt_tokens = getattr(token_usage, "prompt_token_count", 0)
            completion_tokens = getattr(token_usage, "candidates_token_count", 0)
            total_tokens = getattr(token_usage, "total_token_count", 0)
        else:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

        # 計算成本 (Gemini 3 Flash: $0.50/1M input, $3/1M output)
        input_cost = prompt_tokens * 0.00000050
        output_cost = completion_tokens * 0.000003
        total_cost = input_cost + output_cost

        # 整理結果
        test_result = {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "duration_ms": duration_ms,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "cost_usd": {
                "input": round(input_cost, 6),
                "output": round(output_cost, 6),
                "total": round(total_cost, 6),
            },
            "response": result_data,
        }

        # 顯示結果
        print(f"\n⏱️  Response Time: {duration_ms} ms")
        print(
            f"📊 Token Usage: {total_tokens} tokens (prompt: {prompt_tokens}, completion: {completion_tokens})"
        )
        print(f"💰 Cost: ${total_cost:.6f} USD")
        print(f"\n🎯 Safety Level: {result_data.get('safety_level', 'N/A')}")
        print(f"📈 Severity: {result_data.get('severity', 'N/A')}")
        print(f"💬 Display Text: {result_data.get('display_text', 'N/A')}")
        print("\n📝 Action Suggestion:")
        print(f"   {result_data.get('action_suggestion', 'N/A')}")

        # 顯示 detailed_scripts
        if "detailed_scripts" in result_data and result_data["detailed_scripts"]:
            print(f"\n📖 Detailed Scripts ({len(result_data['detailed_scripts'])} 個):")
            for i, script in enumerate(result_data["detailed_scripts"], 1):
                print(f"\n   --- Script {i} ---")
                print(f"   Situation: {script.get('situation', 'N/A')}")
                print(f"   Theory Basis: {script.get('theory_basis', 'N/A')}")
                print(f"   Step: {script.get('step', 'N/A')}")
                print("\n   Parent Script:")
                parent_script = script.get("parent_script", "N/A")
                # 顯示前 300 字
                if len(parent_script) > 300:
                    print(f"   {parent_script[:300]}...")
                    print(f"   (total {len(parent_script)} chars)")
                else:
                    print(f"   {parent_script}")
                    print(f"   ({len(parent_script)} chars)")

                print("\n   Child Likely Response:")
                print(f"   {script.get('child_likely_response', 'N/A')}")
        else:
            print("\n⚠️  No detailed_scripts in response")

        # 顯示理論框架
        if (
            "theoretical_frameworks" in result_data
            and result_data["theoretical_frameworks"]
        ):
            print("\n🧠 Theoretical Frameworks:")
            for theory in result_data["theoretical_frameworks"]:
                print(f"   - {theory}")
        else:
            print("\n⚠️  No theoretical_frameworks in response")

        return test_result

    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "error": str(e),
        }


async def test_emergency_prompt(scenario: dict) -> dict:
    """使用 Emergency Mode prompt 測試單一場景"""
    print(f"\n{'='*80}")
    print(f"場景 {scenario['id']}: {scenario['name']} (Emergency Mode)")
    print(f"{'='*80}")

    # 組裝 prompt
    prompt = ISLAND_PARENTS_8_SCHOOLS_EMERGENCY_PROMPT.format(
        context=scenario["context"],
        full_transcript=scenario["full_transcript"],
        transcript_segment=scenario["transcript_segment"],
    )

    # 記錄開始時間
    start_time = time.time()

    # 調用 Gemini
    gemini_service = GeminiService()
    try:
        ai_response = await gemini_service.generate_text(
            prompt, temperature=0.3, response_format={"type": "json_object"}
        )

        # 記錄結束時間
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # 解析 response
        response_text = (
            ai_response.text if hasattr(ai_response, "text") else str(ai_response)
        )

        # 提取 JSON
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            result_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗: {e}")
            result_data = {
                "error": "JSON parse failed",
                "raw_response": response_text[:500],
            }

        # 提取 token 使用量
        token_usage = getattr(ai_response, "usage_metadata", None)
        if token_usage:
            prompt_tokens = getattr(token_usage, "prompt_token_count", 0)
            completion_tokens = getattr(token_usage, "candidates_token_count", 0)
            total_tokens = getattr(token_usage, "total_token_count", 0)
        else:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

        # 計算成本 (Gemini 3 Flash: $0.50/1M input, $3/1M output)
        input_cost = prompt_tokens * 0.00000050
        output_cost = completion_tokens * 0.000003
        total_cost = input_cost + output_cost

        # 整理結果
        test_result = {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "duration_ms": duration_ms,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "cost_usd": {
                "input": round(input_cost, 6),
                "output": round(output_cost, 6),
                "total": round(total_cost, 6),
            },
            "response": result_data,
        }

        # 顯示結果
        print(f"\n⏱️  Response Time: {duration_ms} ms")
        print(
            f"📊 Token Usage: {total_tokens} tokens (prompt: {prompt_tokens}, completion: {completion_tokens})"
        )
        print(f"💰 Cost: ${total_cost:.6f} USD")
        print(f"\n🎯 Safety Level: {result_data.get('safety_level', 'N/A')}")
        print(f"📈 Severity: {result_data.get('severity', 'N/A')}")
        print(f"💬 Display Text: {result_data.get('display_text', 'N/A')}")
        print("\n📝 Action Suggestion:")
        print(f"   {result_data.get('action_suggestion', 'N/A')}")

        # 顯示 detailed_scripts
        if "detailed_scripts" in result_data and result_data["detailed_scripts"]:
            print(f"\n📖 Detailed Scripts ({len(result_data['detailed_scripts'])} 個):")
            for i, script in enumerate(result_data["detailed_scripts"], 1):
                print(f"\n   --- Script {i} ---")
                print(f"   Situation: {script.get('situation', 'N/A')}")
                print(f"   Theory Basis: {script.get('theory_basis', 'N/A')}")
                print(f"   Step: {script.get('step', 'N/A')}")
                print("\n   Parent Script:")
                parent_script = script.get("parent_script", "N/A")
                # 顯示前 200 字 (Emergency Mode 較短)
                if len(parent_script) > 200:
                    print(f"   {parent_script[:200]}...")
                    print(f"   (total {len(parent_script)} chars)")
                else:
                    print(f"   {parent_script}")
                    print(f"   ({len(parent_script)} chars)")

                print("\n   Child Likely Response:")
                print(f"   {script.get('child_likely_response', 'N/A')}")
        else:
            print("\n⚠️  No detailed_scripts in response")

        # 顯示理論框架
        if (
            "theoretical_frameworks" in result_data
            and result_data["theoretical_frameworks"]
        ):
            print("\n🧠 Theoretical Frameworks:")
            for theory in result_data["theoretical_frameworks"]:
                print(f"   - {theory}")
        else:
            print("\n⚠️  No theoretical_frameworks in response")

        return test_result

    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "error": str(e),
        }


async def test_old_prompt(scenario: dict) -> dict:
    """使用舊 prompt 測試單一場景（作為對照）"""
    # 舊 prompt (從 keyword_analysis_service.py Line 126-171)
    old_prompt_template = """你是親子教養專家，提供詳細教學指導。這是事前練習模式，可以提供更完整的分析和建議。

背景資訊：
{context}

完整對話逐字稿（供參考，理解背景脈絡）：
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
（請根據此區塊判斷當前安全等級）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{transcript_segment}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

請分析並返回 JSON 格式：
{{
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "給家長的提示文字",
    "action_suggestion": "詳細建議（3-4句），包含 Bridge 技巧說明",
    "suggested_interval_seconds": 30,
    "keywords": ["關鍵詞1", "關鍵詞2", "關鍵詞3"],
    "categories": ["類別1", "類別2"]
}}

紅黃綠燈判斷標準：
- 🔴 RED (嚴重): 孩子情緒崩潰、家長失控、衝突升級、語言暴力
- 🟡 YELLOW (需調整): 溝通不良、情緒緊張、單向指責、忽略感受
- 🟢 GREEN (良好): 溝通順暢、情緒穩定、互相尊重、有效傾聽

⚠️ PRACTICE MODE 要求：
- 提供 3-4 句詳細建議
- 說明 Bridge 技巧和溝通策略
- 幫助家長理解孩子行為背後的需求
- 建議具體對話方式和調整方法

⚠️ CRITICAL: 安全等級評估請只根據「【最近對話 - 用於安全評估】」區塊判斷，
完整對話僅作為理解脈絡參考。如果最近對話已緩和，即使之前有危險內容，
也應評估為較低風險。

注意：
- display_text: 描述當前親子互動狀況，給家長具體的觀察提示
- action_suggestion: 具體可行的溝通調整建議，包含教學性內容
- severity: 1=輕微, 2=中等, 3=嚴重
"""

    prompt = old_prompt_template.format(
        context=scenario["context"],
        full_transcript=scenario["full_transcript"],
        transcript_segment=scenario["transcript_segment"],
    )

    start_time = time.time()
    gemini_service = GeminiService()

    try:
        ai_response = await gemini_service.generate_text(
            prompt, temperature=0.3, response_format={"type": "json_object"}
        )

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        response_text = (
            ai_response.text if hasattr(ai_response, "text") else str(ai_response)
        )

        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            result_data = json.loads(json_str)
        except json.JSONDecodeError:
            result_data = {"error": "JSON parse failed"}

        token_usage = getattr(ai_response, "usage_metadata", None)
        if token_usage:
            prompt_tokens = getattr(token_usage, "prompt_token_count", 0)
            completion_tokens = getattr(token_usage, "candidates_token_count", 0)
            total_tokens = getattr(token_usage, "total_token_count", 0)
        else:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

        total_cost = prompt_tokens * 0.00000050 + completion_tokens * 0.000003

        return {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "duration_ms": duration_ms,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "cost_usd": total_cost,
            "response": result_data,
        }

    except Exception as e:
        return {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "error": str(e),
        }


async def run_all_tests():
    """執行所有測試場景"""
    print("\n" + "=" * 80)
    print("🧪 8 大流派 Prompt 測試 (Practice Mode vs Emergency Mode)")
    print("=" * 80)
    print(f"\n📋 測試場景: {len(TEST_SCENARIOS)} 個")
    print(f"📊 Practice Mode Version: {PRACTICE_METADATA['version']}")
    print(f"📊 Emergency Mode Version: {EMERGENCY_METADATA['version']}")
    print(f"📅 Date: {PRACTICE_METADATA['date']}")

    practice_prompt_results = []
    emergency_prompt_results = []
    old_prompt_results = []

    # 測試 Practice Mode prompt
    print("\n" + "=" * 80)
    print("🆕 測試 Practice Mode Prompt (8 大流派整合版)")
    print("=" * 80)

    for scenario in TEST_SCENARIOS:
        result = await test_practice_prompt(scenario)
        practice_prompt_results.append(result)
        await asyncio.sleep(1)  # 避免 API rate limit

    # 測試 Emergency Mode prompt
    print("\n\n" + "=" * 80)
    print("🚨 測試 Emergency Mode Prompt (8 大流派簡潔版)")
    print("=" * 80)

    for scenario in TEST_SCENARIOS:
        result = await test_emergency_prompt(scenario)
        emergency_prompt_results.append(result)
        await asyncio.sleep(1)

    # 測試舊 prompt
    print("\n\n" + "=" * 80)
    print("📜 測試舊 Prompt (原版)")
    print("=" * 80)

    for scenario in TEST_SCENARIOS:
        print(f"\n場景 {scenario['id']}: {scenario['name']} (舊版)")
        result = await test_old_prompt(scenario)
        old_prompt_results.append(result)
        print(
            f"⏱️  {result['duration_ms']} ms | 📊 {result['token_usage']['total_tokens']} tokens"
        )
        await asyncio.sleep(1)

    # 生成比較報告
    print("\n\n" + "=" * 80)
    print("📊 三版本比較報告")
    print("=" * 80)

    # 計算平均值
    practice_avg_tokens = sum(
        r["token_usage"]["total_tokens"]
        for r in practice_prompt_results
        if "token_usage" in r
    ) / len(practice_prompt_results)
    emergency_avg_tokens = sum(
        r["token_usage"]["total_tokens"]
        for r in emergency_prompt_results
        if "token_usage" in r
    ) / len(emergency_prompt_results)
    old_avg_tokens = sum(
        r["token_usage"]["total_tokens"]
        for r in old_prompt_results
        if "token_usage" in r
    ) / len(old_prompt_results)

    practice_avg_time = sum(
        r["duration_ms"] for r in practice_prompt_results if "duration_ms" in r
    ) / len(practice_prompt_results)
    emergency_avg_time = sum(
        r["duration_ms"] for r in emergency_prompt_results if "duration_ms" in r
    ) / len(emergency_prompt_results)
    old_avg_time = sum(
        r["duration_ms"] for r in old_prompt_results if "duration_ms" in r
    ) / len(old_prompt_results)

    practice_avg_cost = sum(
        r["cost_usd"]["total"] for r in practice_prompt_results if "cost_usd" in r
    ) / len(practice_prompt_results)
    emergency_avg_cost = sum(
        r["cost_usd"]["total"] for r in emergency_prompt_results if "cost_usd" in r
    ) / len(emergency_prompt_results)
    old_avg_cost = sum(
        r["cost_usd"] for r in old_prompt_results if "cost_usd" in r
    ) / len(old_prompt_results)

    print("\n📈 平均 Token 使用量:")
    print(f"   Practice Mode:  {practice_avg_tokens:.0f} tokens")
    if practice_avg_tokens > 0:
        print(
            f"   Emergency Mode: {emergency_avg_tokens:.0f} tokens ({((emergency_avg_tokens / practice_avg_tokens - 1) * 100):+.1f}% vs Practice)"
        )
    else:
        print(
            f"   Emergency Mode: {emergency_avg_tokens:.0f} tokens (N/A - token data unavailable)"
        )
    print(f"   原版:           {old_avg_tokens:.0f} tokens")

    print("\n⏱️  平均 Response Time:")
    print(f"   Practice Mode:  {practice_avg_time:.0f} ms")
    if practice_avg_time > 0:
        print(
            f"   Emergency Mode: {emergency_avg_time:.0f} ms ({((emergency_avg_time / practice_avg_time - 1) * 100):+.1f}% vs Practice)"
        )
    else:
        print(f"   Emergency Mode: {emergency_avg_time:.0f} ms")
    print(f"   原版:           {old_avg_time:.0f} ms")

    print("\n💰 平均成本:")
    print(f"   Practice Mode:  ${practice_avg_cost:.6f} USD")
    if practice_avg_cost > 0:
        print(
            f"   Emergency Mode: ${emergency_avg_cost:.6f} USD ({((emergency_avg_cost / practice_avg_cost - 1) * 100):+.1f}% vs Practice)"
        )
    else:
        print(f"   Emergency Mode: ${emergency_avg_cost:.6f} USD")
    print(f"   原版:           ${old_avg_cost:.6f} USD")

    # 檢查新功能 (Practice Mode)
    practice_has_scripts = sum(
        1
        for r in practice_prompt_results
        if "response" in r and "detailed_scripts" in r["response"]
    )
    practice_has_theories = sum(
        1
        for r in practice_prompt_results
        if "response" in r and "theoretical_frameworks" in r["response"]
    )

    # 檢查新功能 (Emergency Mode)
    emergency_has_scripts = sum(
        1
        for r in emergency_prompt_results
        if "response" in r and "detailed_scripts" in r["response"]
    )
    emergency_has_theories = sum(
        1
        for r in emergency_prompt_results
        if "response" in r and "theoretical_frameworks" in r["response"]
    )

    print("\n✨ 新功能覆蓋率:")
    print("   Practice Mode:")
    print(
        f"     - detailed_scripts: {practice_has_scripts}/{len(practice_prompt_results)} ({practice_has_scripts/len(practice_prompt_results)*100:.0f}%)"
    )
    print(
        f"     - theoretical_frameworks: {practice_has_theories}/{len(practice_prompt_results)} ({practice_has_theories/len(practice_prompt_results)*100:.0f}%)"
    )
    print("   Emergency Mode:")
    print(
        f"     - detailed_scripts: {emergency_has_scripts}/{len(emergency_prompt_results)} ({emergency_has_scripts/len(emergency_prompt_results)*100:.0f}%)"
    )
    print(
        f"     - theoretical_frameworks: {emergency_has_theories}/{len(emergency_prompt_results)} ({emergency_has_theories/len(emergency_prompt_results)*100:.0f}%)"
    )

    # 計算話術長度（Emergency Mode 應該更短）
    practice_scripts_lengths = []
    emergency_scripts_lengths = []

    for r in practice_prompt_results:
        if "response" in r and "detailed_scripts" in r["response"]:
            for script in r["response"]["detailed_scripts"]:
                if "parent_script" in script:
                    practice_scripts_lengths.append(len(script["parent_script"]))

    for r in emergency_prompt_results:
        if "response" in r and "detailed_scripts" in r["response"]:
            for script in r["response"]["detailed_scripts"]:
                if "parent_script" in script:
                    emergency_scripts_lengths.append(len(script["parent_script"]))

    if practice_scripts_lengths and emergency_scripts_lengths:
        practice_avg_script_len = sum(practice_scripts_lengths) / len(
            practice_scripts_lengths
        )
        emergency_avg_script_len = sum(emergency_scripts_lengths) / len(
            emergency_scripts_lengths
        )

        print("\n📏 話術長度比較:")
        print(
            f"   Practice Mode:  平均 {practice_avg_script_len:.0f} 字 (目標: 150-300 字)"
        )
        print(
            f"   Emergency Mode: 平均 {emergency_avg_script_len:.0f} 字 (目標: 100-200 字)"
        )
        if practice_avg_script_len > 0:
            print(
                f"   差異: {((emergency_avg_script_len / practice_avg_script_len - 1) * 100):+.1f}%"
            )
        print(
            f"\n✅ Practice Mode: {len([x for x in practice_scripts_lengths if 150 <= x <= 350])}/{len(practice_scripts_lengths)} 符合目標長度"
        )
        print(
            f"✅ Emergency Mode: {len([x for x in emergency_scripts_lengths if 100 <= x <= 200])}/{len(emergency_scripts_lengths)} 符合目標長度"
        )

    # 儲存完整結果
    output_file = project_root / "scripts" / "test_8_schools_prompt_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "practice_mode": PRACTICE_METADATA,
                    "emergency_mode": EMERGENCY_METADATA,
                },
                "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "scenarios": TEST_SCENARIOS,
                "practice_prompt_results": practice_prompt_results,
                "emergency_prompt_results": emergency_prompt_results,
                "old_prompt_results": old_prompt_results,
                "summary": {
                    "practice_avg_tokens": practice_avg_tokens,
                    "emergency_avg_tokens": emergency_avg_tokens,
                    "old_avg_tokens": old_avg_tokens,
                    "practice_avg_time_ms": practice_avg_time,
                    "emergency_avg_time_ms": emergency_avg_time,
                    "old_avg_time_ms": old_avg_time,
                    "practice_avg_cost_usd": practice_avg_cost,
                    "emergency_avg_cost_usd": emergency_avg_cost,
                    "old_avg_cost_usd": old_avg_cost,
                    "emergency_vs_practice": {
                        "token_reduction_pct": (
                            ((emergency_avg_tokens / practice_avg_tokens - 1) * 100)
                            if practice_avg_tokens > 0
                            else 0
                        ),
                        "time_reduction_pct": (
                            ((emergency_avg_time / practice_avg_time - 1) * 100)
                            if practice_avg_time > 0
                            else 0
                        ),
                        "cost_reduction_pct": (
                            ((emergency_avg_cost / practice_avg_cost - 1) * 100)
                            if practice_avg_cost > 0
                            else 0
                        ),
                    },
                    "practice_mode_coverage": {
                        "detailed_scripts": practice_has_scripts
                        / len(practice_prompt_results),
                        "theories": practice_has_theories
                        / len(practice_prompt_results),
                    },
                    "emergency_mode_coverage": {
                        "detailed_scripts": emergency_has_scripts
                        / len(emergency_prompt_results),
                        "theories": emergency_has_theories
                        / len(emergency_prompt_results),
                    },
                    "script_lengths": {
                        "practice_avg": (
                            sum(practice_scripts_lengths)
                            / len(practice_scripts_lengths)
                            if practice_scripts_lengths
                            else 0
                        ),
                        "emergency_avg": (
                            sum(emergency_scripts_lengths)
                            / len(emergency_scripts_lengths)
                            if emergency_scripts_lengths
                            else 0
                        ),
                    },
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n💾 完整結果已儲存至: {output_file}")

    print("\n" + "=" * 80)
    print("✅ 測試完成")
    print("=" * 80)


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(run_all_tests())
