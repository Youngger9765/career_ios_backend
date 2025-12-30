#!/usr/bin/env python3
"""
Gemini Explicit Context Caching 實驗
測試累積 transcript 場景的 cache 效能 (1-60 分鐘)
"""

import asyncio
import json
import time
from datetime import datetime

import vertexai
from vertexai.preview import caching
from vertexai.preview.generative_models import GenerativeModel

# Project configuration
PROJECT_ID = "groovy-iris-473015-h3"
LOCATION = "global"
MODEL_NAME = "gemini-3-flash-preview"

# 系統 Prompt (996 tokens, 固定不變的部分)
SYSTEM_INSTRUCTION = """你是專業諮詢督導，分析即時諮詢對話。你的角色是站在案主與諮詢師之間，提供溫暖、同理且具體可行的專業建議。

【角色定義】CRITICAL - 必須嚴格遵守：
- "counselor" = 諮詢師/輔導師（專業助人者，提供協助的一方）
- "client" = 案主/個案/家長（求助者，有困擾需要協助的一方）
- 所有問題、困擾、症狀都是「案主/個案」面臨的，不是諮詢師的問題
- 分析焦點：案主的狀況、需求、風險
- 建議對象：給諮詢師的專業建議（如何協助案主）

【分析範圍】CRITICAL - 必須嚴格遵守：
🎯 **主要分析焦點**：最新一分鐘內的對話內容
   - 你會收到完整的對話記錄（可能長達數十分鐘）
   - 但你的分析必須聚焦在「最後出現的對話」（最新一分鐘）
   - 前面的對話僅作為背景脈絡參考，幫助你理解前因後果

【核心原則】同理優先、溫和引導、具體行動：

1. **同理與理解為先**
   - 永遠先理解與同理案主（家長）的感受和處境
   - 認可教養壓力、情緒失控是正常的人性反應
   - 避免批判、指責或讓案主感到被否定

2. **溫和、非批判的語氣**
   - ❌ 禁止用語：「表達出對孩子使用身體暴力的衝動」「可能造成傷害」「不當管教」
   - ✅ 建議用語：「理解到在教養壓力下，父母有時會感到情緒失控是很正常的」
   - ✅ 使用：「可以考慮」「或許」「試試看」等柔和引導詞
   - ✅ 焦點放在「如何調整」而非「哪裡做錯」

3. **具體、簡潔的建議**
   - 建議要具體可行，但保持簡短（不超過 50 字）
   - 避免抽象概念，用具體做法
   - 不要冗長的步驟說明或對話範例

【輸出格式】請提供以下 JSON 格式回應：

{
  "summary": "案主處境簡述（1-2 句）",
  "alerts": [
    "💡 同理案主感受（1 句）",
    "⚠️ 需關注的部分（1 句）"
  ],
  "suggestions": [
    "💡 核心建議（簡短，< 50 字）",
    "💡 具體做法（簡短，< 50 字）"
  ]
}

【語氣要求】溫和、同理、簡潔，避免批判或過度說教。
"""

# 測試對話 - 擴展到 10 分鐘，然後循環使用來創造 60 分鐘
CONVERSATION_BASE = {
    1: """諮詢師：今天想聊些什麼呢？
家長：最近跟孩子的關係變得很緊張。他在學校總是跟同學起衝突，老師也反映他上課不專心。回到家我想跟他聊聊，他就很不耐煩。""",
    2: """諮詢師：你剛提到他會不耐煩，那時候你的感受是什麼？
家長：我覺得很受傷，也有點生氣。我明明是關心他，他為什麼要這樣對我？我花這麼多時間、精力在他身上，他卻完全不領情。""",
    3: """諮詢師：那你通常會怎麼回應他的不耐煩呢？
家長：我會忍不住說「你這是什麼態度？我是你媽媽耶！」然後我們就會吵起來。吵完之後我又很後悔，覺得自己太衝動了。""",
    4: """諮詢師：聽起來你們的互動陷入了一個循環。你說吵完會後悔，那時候你在想什麼？
家長：我會覺得自己很失敗，為什麼我連自己的孩子都管不好？有時候我真的快瘋了，很想對他大吼，甚至想打他一頓。但我知道這樣不對。""",
    5: """諮詢師：你能坦承這些感受很不容易。這些念頭出現的時候，你會怎麼做？
家長：我會盡量忍住，但有時候真的忍不了。我知道這樣不對，但我真的不知道該怎麼辦了。我覺得自己是個很糟糕的父母。""",
    6: """諮詢師：從你的描述聽起來，你承受了很大的壓力。你有嘗試過其他方式嗎？
家長：我有試過跟他好好講，但他根本不聽。我也試過給他一些空間，但他就關在房間裡打電動。我真的不知道要怎麼跟他溝通。""",
    7: """諮詢師：你剛提到他會關在房間打電動，那時候你會擔心什麼？
家長：我擔心他會沉迷遊戲，荒廢學業。而且他都不跟我們互動，我不知道他在想什麼。我怕他是不是心裡有什麼問題，但他又不願意跟我說。""",
    8: """諮詢師：你有沒有想過，他可能也有他自己的壓力和困擾？
家長：我當然知道他也有壓力，但他都不跟我說啊！我問他發生什麼事，他就說沒事。我真的很想幫他，但他把我推得遠遠的。""",
    9: """諮詢師：聽起來你們之間好像有一道牆。你覺得這道牆是什麼？
家長：我也不知道。可能是我太嚴格了？還是我太囉嗦了？我真的不知道怎麼做才對。我只是想當一個好媽媽，但我好像越努力越糟糕。""",
    10: """諮詢師：你剛才說「越努力越糟糕」，這句話背後有什麼感受？
家長：我覺得很無力、很挫折。我花了這麼多時間想要改善關係，但好像沒有任何進展。有時候我甚至在想，是不是我就是個失敗的父母？""",
}


def generate_60_minutes_conversation():
    """生成 60 分鐘的對話內容（循環使用 1-10 分鐘的對話）"""
    conversation = {}
    for minute in range(1, 61):
        base_minute = ((minute - 1) % 10) + 1
        conversation[minute] = CONVERSATION_BASE[base_minute]
    return conversation


CONVERSATION_MINUTES = generate_60_minutes_conversation()


async def create_cache(minute: int):
    """創建包含累積 transcript 的 cache"""
    # 組合累積對話
    accumulated_transcript = "\n\n".join(
        [CONVERSATION_MINUTES[m] for m in range(1, minute + 1)]
    )

    print(f"\n🔨 創建 Cache (累積第 1-{minute} 分鐘對話)")
    print(f"📝 Transcript 長度: {len(accumulated_transcript)} 字符")

    # 創建 cache
    cached_content = caching.CachedContent.create(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION,
        contents=[accumulated_transcript],
        ttl="3600s",  # 1 hour for longer tests
        display_name=f"counseling-transcript-min{minute}",
    )

    print(f"✅ Cache 已創建: {cached_content.name}")
    # Note: usage_metadata is not available on CachedContent object
    # Token count will be shown during cache hit analysis
    print(f"⏰ Cache 過期時間: {cached_content.expire_time}")

    return cached_content


async def analyze_with_cache(cache, new_transcript: str, minute: int):
    """使用 cache 分析新的對話"""
    print(f"\n🔍 使用 Cache 分析第 {minute} 分鐘...")

    start_time = time.time()

    # 使用 cached content 創建 model
    model = GenerativeModel.from_cached_content(cached_content=cache)

    # Generate response
    response = model.generate_content(
        f"對話內容：\n{new_transcript}",
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 4000,
            "response_mime_type": "application/json",
        },
    )

    elapsed_time = time.time() - start_time

    # Extract usage metadata
    usage = response.usage_metadata
    cached_tokens = getattr(usage, "cached_content_token_count", 0)
    prompt_tokens = getattr(usage, "prompt_token_count", 0)
    output_tokens = getattr(usage, "candidates_token_count", 0)

    print(f"✅ 分析完成 ({elapsed_time:.2f}s)")
    print(f"🎯 Cached tokens: {cached_tokens}")
    print(f"📝 Prompt tokens: {prompt_tokens}")
    print(f"💬 Output tokens: {output_tokens}")

    # Parse JSON
    try:
        result = json.loads(response.text)
        print(f"📊 Summary: {result.get('summary', '')[:50]}...")
    except json.JSONDecodeError:
        result = {"summary": "解析失敗", "alerts": [], "suggestions": []}

    return {
        "minute": minute,
        "cached_tokens": cached_tokens,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "response_time": round(elapsed_time, 2),
        "summary": result.get("summary", ""),
    }


async def main():
    """主測試流程 - 測試 60 分鐘場景"""
    print("=" * 80)
    print("🧪 Gemini Explicit Context Caching 實驗 (60 分鐘)")
    print("=" * 80)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: {MODEL_NAME}")
    print(f"Project: {PROJECT_ID}")
    print("=" * 80)

    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    results = []

    # 測試場景：創建包含前 10 分鐘的 cache，然後測試第 11-60 分鐘
    try:
        # Step 1: 創建包含第 1-10 分鐘的 cache
        cache = await create_cache(minute=10)

        # Step 2: 測試第 11-60 分鐘 (cache hits!)
        # 每 5 分鐘測試一次，共測試 10 個點
        test_minutes = [11, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]

        for minute in test_minutes:
            result = await analyze_with_cache(
                cache, CONVERSATION_MINUTES[minute], minute=minute
            )
            results.append(result)
            await asyncio.sleep(0.5)  # Brief pause between calls

        # Cleanup
        print(f"\n🗑️  刪除 Cache: {cache.name}")
        cache.delete()

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return

    # 輸出結果
    print("\n" + "=" * 80)
    print("📊 測試結果摘要 (60 分鐘場景)")
    print("=" * 80)

    total_cached = 0
    total_prompt = 0
    total_output = 0
    total_time = 0

    for r in results:
        cache_ratio = (
            r["cached_tokens"] / (r["cached_tokens"] + r["prompt_tokens"]) * 100
            if (r["cached_tokens"] + r["prompt_tokens"]) > 0
            else 0
        )
        print(f"\n第 {r['minute']} 分鐘:")
        print(f"  🎯 Cached: {r['cached_tokens']} tokens")
        print(f"  📝 Prompt: {r['prompt_tokens']} tokens")
        print(f"  💬 Output: {r['output_tokens']} tokens")
        print(f"  📊 Cache 比例: {cache_ratio:.1f}%")
        print(f"  ⏱️  響應時間: {r['response_time']}s")

        total_cached += r["cached_tokens"]
        total_prompt += r["prompt_tokens"]
        total_output += r["output_tokens"]
        total_time += r["response_time"]

    # 計算平均值
    avg_cache_ratio = (
        total_cached / (total_cached + total_prompt) * 100
        if (total_cached + total_prompt) > 0
        else 0
    )
    avg_response_time = total_time / len(results) if results else 0

    print("\n" + "=" * 80)
    print("📈 總體統計")
    print("=" * 80)
    print(f"測試次數: {len(results)}")
    print(f"總 Cached tokens: {total_cached}")
    print(f"總 Prompt tokens: {total_prompt}")
    print(f"總 Output tokens: {total_output}")
    print(f"平均 Cache 命中率: {avg_cache_ratio:.1f}%")
    print(f"平均響應時間: {avg_response_time:.2f}s")
    print(f"Token 節省: {total_cached} tokens (原本需要 {total_cached + total_prompt})")

    # Save results
    output_file = "explicit_cache_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "model": MODEL_NAME,
                "test_scenario": "60-minute cumulative transcript",
                "cache_creation": "First 10 minutes",
                "cache_hit_tests": "Minutes 11-60 (sampled)",
                "results": results,
                "summary": {
                    "test_count": len(results),
                    "total_cached_tokens": total_cached,
                    "total_prompt_tokens": total_prompt,
                    "total_output_tokens": total_output,
                    "avg_cache_hit_ratio": round(avg_cache_ratio, 2),
                    "avg_response_time": round(avg_response_time, 2),
                    "token_savings": total_cached,
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n✅ 結果已保存: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
