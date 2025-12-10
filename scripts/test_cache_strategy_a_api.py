#!/usr/bin/env python3
"""
測試策略 A：模擬重建 cache（每次發送完整累積對話）

透過 Staging API 測試，讓 Gemini 的 implicit caching 處理。
由於我們無法直接控制 cache 創建/刪除，這個測試主要觀察：
- 每次都發送完整累積對話
- 觀察 Gemini 如何自動處理 caching

實際場景：
- 第 1 分鐘：發送 "對話1"
- 第 2 分鐘：發送 "對話1+2" (完整)
- 第 3 分鐘：發送 "對話1+2+3" (完整)
"""

import asyncio
import json
import time
from datetime import datetime

import httpx

# API Configuration
API_BASE_URL = "https://career-app-api-staging-kxaznpplqq-uc.a.run.app/api/v1"
REALTIME_ENDPOINT = f"{API_BASE_URL}/realtime/analyze"

# 測試對話 - 10 分鐘
CONVERSATION = {
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


async def analyze_cumulative(minute: int):
    """
    發送累積對話（第 1-minute 分鐘）
    模擬「重建 cache」：每次都發送完整的累積內容
    """
    print(f"\n{'='*80}")
    print(f"📍 第 {minute} 分鐘 - 策略 A（完整累積對話）")
    print(f"{'='*80}")

    # 組合累積對話
    accumulated = "\n\n".join([CONVERSATION[m] for m in range(1, minute + 1)])
    transcript_chars = len(accumulated)
    estimated_tokens = int(transcript_chars * 0.4)  # 繁體中文約 0.4 tokens/char

    print(f"累積對話: 第 1-{minute} 分鐘")
    print(f"字符數: {transcript_chars}")
    print(f"估算 tokens: {estimated_tokens}")

    # 發送請求
    request_data = {
        "transcript": accumulated,
        "speakers": [],
        "time_range": f"0:00-{minute}:00",
    }

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                REALTIME_ENDPOINT,
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage_metadata", {})

                cached_tokens = usage.get("cached_content_token_count", 0)
                prompt_tokens = usage.get("prompt_token_count", 0)
                output_tokens = usage.get("candidates_token_count", 0)

                cache_ratio = (
                    cached_tokens / (cached_tokens + prompt_tokens) * 100
                    if (cached_tokens + prompt_tokens) > 0
                    else 0
                )

                print(f"✅ 成功 ({elapsed_time:.2f}s)")
                print(f"🎯 Cached: {cached_tokens} tokens")
                print(f"📝 Prompt: {prompt_tokens} tokens")
                print(f"💬 Output: {output_tokens} tokens")
                print(f"📊 Cache 比例: {cache_ratio:.1f}%")

                return {
                    "minute": minute,
                    "success": True,
                    "transcript_chars": transcript_chars,
                    "cached_tokens": cached_tokens,
                    "prompt_tokens": prompt_tokens,
                    "output_tokens": output_tokens,
                    "response_time": round(elapsed_time, 2),
                    "cache_ratio": round(cache_ratio, 1),
                    "strategy": "A - Full Cumulative",
                }
            else:
                print(f"❌ 失敗: HTTP {response.status_code}")
                print(f"錯誤: {response.text}")
                return {
                    "minute": minute,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ 異常: {str(e)}")
        return {
            "minute": minute,
            "success": False,
            "error": str(e),
            "response_time": round(elapsed_time, 2),
        }


async def main():
    print("=" * 80)
    print("🧪 測試策略 A：完整累積對話（模擬重建 cache）")
    print("=" * 80)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {REALTIME_ENDPOINT}")
    print("=" * 80)

    results = []

    # 測試 10 分鐘
    for minute in range(1, 11):
        result = await analyze_cumulative(minute)
        results.append(result)

        # 短暫延遲，讓 implicit cache 生效
        if minute < 10:
            await asyncio.sleep(0.1)

    # 計算統計
    successful = [r for r in results if r.get("success")]

    if successful:
        total_cached = sum(r["cached_tokens"] for r in successful)
        total_prompt = sum(r["prompt_tokens"] for r in successful)
        total_output = sum(r["output_tokens"] for r in successful)
        total_time = sum(r["response_time"] for r in successful)

        avg_cache_ratio = (
            total_cached / (total_cached + total_prompt) * 100
            if (total_cached + total_prompt) > 0
            else 0
        )

        print("\n" + "=" * 80)
        print("📊 策略 A 測試結果摘要")
        print("=" * 80)

        for r in successful:
            print(f"\n第 {r['minute']} 分鐘:")
            print(f"  🎯 Cached: {r['cached_tokens']} tokens")
            print(f"  📝 Prompt: {r['prompt_tokens']} tokens")
            print(f"  💬 Output: {r['output_tokens']} tokens")
            print(f"  📊 Cache 比例: {r['cache_ratio']}%")
            print(f"  ⏱️  響應時間: {r['response_time']}s")

        print("\n" + "=" * 80)
        print("📈 總體統計")
        print("=" * 80)
        print(f"測試次數: {len(successful)}")
        print(f"總 Cached tokens: {total_cached:,}")
        print(f"總 Prompt tokens: {total_prompt:,}")
        print(f"總 Output tokens: {total_output:,}")
        print(f"總輸入 tokens: {total_cached + total_prompt:,}")
        print(f"平均 Cache 命中率: {avg_cache_ratio:.1f}%")
        print(f"總響應時間: {total_time:.2f}s")

        # 儲存結果
        output_file = "strategy_a_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "strategy": "A - Full Cumulative (Simulated Rebuild Cache)",
                    "description": "每次發送完整累積對話，模擬重建 cache",
                    "results": results,
                    "summary": {
                        "test_count": len(successful),
                        "total_cached_tokens": total_cached,
                        "total_prompt_tokens": total_prompt,
                        "total_output_tokens": total_output,
                        "total_input_tokens": total_cached + total_prompt,
                        "avg_cache_hit_ratio": round(avg_cache_ratio, 2),
                        "total_response_time": round(total_time, 2),
                        "total_time": round(total_time, 2),
                        "total_cache_creation_time": 0,  # N/A for implicit caching
                    },
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"\n✅ 結果已保存: {output_file}")
        print("=" * 80)
    else:
        print("\n❌ 測試失敗，無成功結果")


if __name__ == "__main__":
    asyncio.run(main())
