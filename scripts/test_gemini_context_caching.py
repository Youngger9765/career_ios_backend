#!/usr/bin/env python3
"""
測試 Gemini Context Caching 是否真的能省 50% 時間
"""

import asyncio
import os
import sys
import time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import google.generativeai as genai
    from google.generativeai import caching

    from app.core.config import settings

    genai.configure(api_key=settings.GOOGLE_API_KEY)
    GEMINI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 無法導入 Gemini: {e}")
    GEMINI_AVAILABLE = False


async def test_without_caching():
    """測試：沒有使用 Caching（基準線）"""
    print("\n" + "=" * 60)
    print("🧪 測試 1: 沒有使用 Context Caching（基準線）")
    print("=" * 60)

    # 模擬完整的 context（8 大流派理論 + 完整對話）
    full_context = """你是專業親子教養顧問，精通 8 大流派：
1. 阿德勒正向教養
2. 薩提爾模式（冰山理論）
3. 行為分析學派 (ABA)
4. 人際神經生物學 (Dan Siegel)
5. 情緒輔導 (John Gottman)
6. 協作解決問題 (Ross Greene)
7. 現代依附與內在觀點 (Dr. Becky Kennedy)
8. 社會意識與價值觀教養

完整對話逐字稿：
家長：你今天在學校過得怎麼樣？
孩子：還好啊
家長：有什麼開心的事嗎？
孩子：沒有
家長：那有什麼不開心的事嗎？
孩子：也沒有
家長：你確定嗎？感覺你好像有點不開心？
孩子：就還好啊，沒什麼特別的
（約 500 字的完整對話...省略）
"""

    times = []

    for i in range(3):
        print(f"\n   🔄 第 {i+1} 次請求:")

        # 完整 prompt（每次都包含完整 context）
        prompt = f"""{full_context}

最近對話：
家長：你確定嗎？感覺你好像有點不開心？
孩子：就還好啊，沒什麼特別的

請分析並返回 JSON：
{{"safety_level": "green|yellow|red", "severity": 1-3, "display_text": "提示"}}
"""

        start = time.time()

        model = genai.GenerativeModel("gemini-3-flash-preview")
        await model.generate_content_async(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 200,
                "response_mime_type": "application/json",
            },
        )

        elapsed = time.time() - start
        times.append(elapsed)

        print(f"      耗時: {elapsed*1000:.0f} ms ({elapsed:.2f}s)")

        # 等待避免 rate limiting
        if i < 2:
            await asyncio.sleep(2)

    avg = sum(times) / len(times)
    print(f"\n   📊 平均耗時: {avg:.2f}s ({avg*1000:.0f} ms)")
    return avg


async def test_with_caching():
    """測試：使用 Context Caching"""
    print("\n" + "=" * 60)
    print("🧪 測試 2: 使用 Context Caching")
    print("=" * 60)

    # 不變的 context（可以緩存）
    system_instruction = """你是專業親子教養顧問，精通 8 大流派：
1. 阿德勒正向教養
2. 薩提爾模式（冰山理論）
3. 行為分析學派 (ABA)
4. 人際神經生物學 (Dan Siegel)
5. 情緒輔導 (John Gottman)
6. 協作解決問題 (Ross Greene)
7. 現代依附與內在觀點 (Dr. Becky Kennedy)
8. 社會意識與價值觀教養
"""

    cached_content = """完整對話逐字稿：
家長：你今天在學校過得怎麼樣？
孩子：還好啊
家長：有什麼開心的事嗎？
孩子：沒有
家長：那有什麼不開心的事嗎？
孩子：也沒有
家長：你確定嗎？感覺你好像有點不開心？
孩子：就還好啊，沒什麼特別的
（約 500 字的完整對話...省略）
"""

    times = []
    cache_obj = None

    for i in range(3):
        print(f"\n   🔄 第 {i+1} 次請求:")

        start = time.time()

        if i == 0:
            # 第一次：建立緩存
            print("      建立緩存...")
            try:
                cache_obj = caching.CachedContent.create(
                    model="gemini-3-flash-preview",
                    system_instruction=system_instruction,
                    contents=[cached_content],
                    ttl=timedelta(minutes=60),
                )
                print(f"      ✅ 緩存建立成功，ID: {cache_obj.name}")
            except Exception as e:
                print(f"      ❌ 緩存建立失敗: {e}")
                print(f"      錯誤詳情: {type(e).__name__}")
                import traceback

                traceback.print_exc()
                return None
        else:
            # 第 2-3 次：使用緩存
            print(f"      使用緩存: {cache_obj.name}")

        # 使用緩存的模型
        try:
            model = genai.GenerativeModel.from_cached_content(cache_obj)
        except Exception as e:
            print(f"      ❌ 無法使用緩存: {e}")
            return None

        # 只需要傳新的對話片段
        prompt = """最近對話：
家長：你確定嗎？感覺你好像有點不開心？
孩子：就還好啊，沒什麼特別的

請分析並返回 JSON：
{"safety_level": "green|yellow|red", "severity": 1-3, "display_text": "提示"}
"""

        try:
            response = await model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 200,
                    "response_mime_type": "application/json",
                },
            )

            elapsed = time.time() - start
            times.append(elapsed)

            # 顯示 token 使用量
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                cached_tokens = getattr(usage, "cached_content_token_count", 0)
                prompt_tokens = getattr(usage, "prompt_token_count", 0)
                print(f"      耗時: {elapsed*1000:.0f} ms ({elapsed:.2f}s)")
                print(f"      Token: prompt={prompt_tokens}, cached={cached_tokens}")
            else:
                print(f"      耗時: {elapsed*1000:.0f} ms ({elapsed:.2f}s)")

        except Exception as e:
            print(f"      ❌ 請求失敗: {e}")
            return None

        # 等待避免 rate limiting
        if i < 2:
            await asyncio.sleep(2)

    # 清理緩存
    if cache_obj:
        try:
            cache_obj.delete()
            print("\n   🗑️  緩存已刪除")
        except Exception:
            pass

    avg = sum(times) / len(times)
    first_call = times[0]
    subsequent_avg = sum(times[1:]) / len(times[1:]) if len(times) > 1 else times[0]

    print(f"\n   📊 第一次（建立緩存）: {first_call:.2f}s ({first_call*1000:.0f} ms)")
    print(
        f"   📊 後續平均（使用緩存）: {subsequent_avg:.2f}s ({subsequent_avg*1000:.0f} ms)"
    )
    print(f"   📊 總平均: {avg:.2f}s ({avg*1000:.0f} ms)")

    return {"first": first_call, "subsequent": subsequent_avg, "average": avg}


async def main():
    """主測試流程"""

    if not GEMINI_AVAILABLE:
        print("❌ Gemini SDK 不可用，無法執行測試")
        return

    print("=" * 60)
    print("🚀 Gemini Context Caching 真實測試")
    print("=" * 60)
    print()
    print("目的：驗證 Context Caching 是否真的能省 50% 時間")
    print()

    # 測試 1: 沒有 caching（基準線）
    baseline = await test_without_caching()

    # 測試 2: 使用 caching
    caching_result = await test_with_caching()

    # 比較結果
    if baseline and caching_result:
        print("\n" + "=" * 60)
        print("📊 測試結果比較")
        print("=" * 60)
        print()

        print("沒有 Caching（基準線）:")
        print(f"   平均耗時: {baseline:.2f}s ({baseline*1000:.0f} ms)")
        print()

        print("使用 Caching:")
        print(
            f"   第一次（建立緩存）: {caching_result['first']:.2f}s ({caching_result['first']*1000:.0f} ms)"
        )
        print(
            f"   後續請求（使用緩存）: {caching_result['subsequent']:.2f}s ({caching_result['subsequent']*1000:.0f} ms)"
        )
        print()

        # 計算節省百分比
        savings = (baseline - caching_result["subsequent"]) / baseline * 100
        speedup = baseline / caching_result["subsequent"]

        print("🎯 關鍵結論:")
        print(f"   基準線: {baseline:.2f}s")
        print(f"   使用緩存: {caching_result['subsequent']:.2f}s")
        print(f"   節省時間: {baseline - caching_result['subsequent']:.2f}s")
        print(f"   節省比例: {savings:.1f}%")
        print(f"   加速倍數: {speedup:.2f}x")
        print()

        # 判斷是否達到預期
        if savings >= 40:
            print("✅ 驗證成功！Context Caching 確實能省 40% 以上時間！")
        elif savings >= 20:
            print("🟡 部分有效：省了 {:.1f}%，但沒達到 50% 目標".format(savings))
        else:
            print(f"❌ 效果不佳：只省了 {savings:.1f}%，可能不值得實作")

        # 實際應用場景估算
        print()
        print("💡 實際應用場景估算（1 小時會談）:")
        print(
            f"   當前（無緩存）: {baseline:.2f}s × 60 次 = {baseline*60:.0f}s ({baseline*60/60:.1f} 分鐘)"
        )
        print("   優化後（有緩存）:")
        print(f"      第 1 次: {caching_result['first']:.2f}s")
        print(
            f"      第 2-60 次: {caching_result['subsequent']:.2f}s × 59 = {caching_result['subsequent']*59:.0f}s"
        )
        print(
            f"      總計: {caching_result['first'] + caching_result['subsequent']*59:.0f}s ({(caching_result['first'] + caching_result['subsequent']*59)/60:.1f} 分鐘)"
        )
        print(
            f"   節省: {baseline*60 - (caching_result['first'] + caching_result['subsequent']*59):.0f}s ({(baseline*60 - (caching_result['first'] + caching_result['subsequent']*59))/60:.1f} 分鐘)"
        )


if __name__ == "__main__":
    asyncio.run(main())
