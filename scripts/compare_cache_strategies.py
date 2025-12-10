#!/usr/bin/env python3
"""
比較兩種 Cache 策略的效果

執行 test_cache_strategy_a.py 和 test_cache_strategy_b.py
然後比較分析結果，給出明確建議。
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime


def run_script(script_name: str):
    """執行腳本並返回結果"""
    print(f"\n{'=' * 80}")
    print(f"🚀 執行 {script_name}")
    print(f"{'=' * 80}\n")

    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,  # 讓輸出直接顯示
            text=True,
        )

        if result.returncode != 0:
            print(f"\n❌ {script_name} 執行失敗")
            return None

        print(f"\n✅ {script_name} 執行完成")
        return True

    except Exception as e:
        print(f"\n❌ 執行 {script_name} 時發生錯誤: {e}")
        return None


def load_results(filename: str):
    """載入測試結果"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 找不到檔案: {filename}")
        return None
    except json.JSONDecodeError:
        print(f"❌ 無法解析 JSON: {filename}")
        return None


def analyze_results(results_a, results_b):
    """分析並比較兩種策略"""
    print("\n" + "=" * 80)
    print("📊 比較分析：策略 A vs 策略 B")
    print("=" * 80)

    # Extract summaries
    summary_a = results_a["summary"]
    summary_b = results_b["summary"]

    print("\n" + "-" * 80)
    print("🔹 方案 A（每次重建 Cache）")
    print("-" * 80)
    print(f"描述: {results_a['description']}")
    print(f"測試次數: {summary_a['test_count']}")
    print(f"總 Cached tokens: {summary_a['total_cached_tokens']:,}")
    print(f"總 Prompt tokens: {summary_a['total_prompt_tokens']:,}")
    print(f"總輸入 tokens: {summary_a['total_input_tokens']:,}")
    print(f"總 Output tokens: {summary_a['total_output_tokens']:,}")
    print(f"平均 Cache 命中率: {summary_a['avg_cache_hit_ratio']:.1f}%")
    print(f"總響應時間: {summary_a['total_response_time']:.2f}s")
    print(f"總 Cache 創建時間: {summary_a['total_cache_creation_time']:.2f}s")
    print(f"總耗時: {summary_a['total_time']:.2f}s")

    print("\n" + "-" * 80)
    print("🔹 方案 B（固定 Cache）")
    print("-" * 80)
    print(f"描述: {results_b['description']}")
    print(f"測試次數: {summary_b['test_count']}")
    print(f"總 Cached tokens: {summary_b['total_cached_tokens']:,}")
    print(f"總 Prompt tokens: {summary_b['total_prompt_tokens']:,}")
    print(f"總輸入 tokens: {summary_b['total_input_tokens']:,}")
    print(f"總 Output tokens: {summary_b['total_output_tokens']:,}")
    print(f"平均 Cache 命中率: {summary_b['avg_cache_hit_ratio']:.1f}%")
    print(f"總響應時間: {summary_b['total_response_time']:.2f}s")
    print(f"Cache 創建時間（一次性）: {summary_b['cache_creation_time']:.2f}s")
    print(f"總耗時: {summary_b['total_time']:.2f}s")

    # 比較分析
    print("\n" + "=" * 80)
    print("📈 關鍵指標比較")
    print("=" * 80)

    # Cache 命中率
    cache_ratio_diff = (
        summary_a["avg_cache_hit_ratio"] - summary_b["avg_cache_hit_ratio"]
    )
    print("\n🎯 Cache 命中率:")
    print(f"  方案 A: {summary_a['avg_cache_hit_ratio']:.1f}%")
    print(f"  方案 B: {summary_b['avg_cache_hit_ratio']:.1f}%")
    print(
        f"  差異: {cache_ratio_diff:+.1f}% {'(A 較高)' if cache_ratio_diff > 0 else '(B 較高)'}"
    )

    # Token 成本
    input_diff = summary_a["total_input_tokens"] - summary_b["total_input_tokens"]
    input_percent = (
        (input_diff / summary_b["total_input_tokens"] * 100)
        if summary_b["total_input_tokens"] > 0
        else 0
    )
    print("\n💰 總輸入 Token 成本:")
    print(f"  方案 A: {summary_a['total_input_tokens']:,} tokens")
    print(f"  方案 B: {summary_b['total_input_tokens']:,} tokens")
    print(f"  差異: {input_diff:+,} tokens ({input_percent:+.1f}%)")
    if input_diff < 0:
        print(
            f"  💡 方案 A 節省 {abs(input_diff):,} tokens ({abs(input_percent):.1f}%)"
        )
    else:
        print(
            f"  💡 方案 B 節省 {abs(input_diff):,} tokens ({abs(input_percent):.1f}%)"
        )

    # 時間成本
    time_diff = summary_a["total_time"] - summary_b["total_time"]
    time_percent = (
        (time_diff / summary_b["total_time"] * 100)
        if summary_b["total_time"] > 0
        else 0
    )
    print("\n⏱️  總耗時:")
    print(f"  方案 A: {summary_a['total_time']:.2f}s")
    print(f"  方案 B: {summary_b['total_time']:.2f}s")
    print(f"  差異: {time_diff:+.2f}s ({time_percent:+.1f}%)")

    # Cache 創建開銷
    cache_overhead_a = summary_a["total_cache_creation_time"]
    cache_overhead_b = summary_b["cache_creation_time"]
    print("\n🔨 Cache 創建開銷:")
    print(f"  方案 A: {cache_overhead_a:.2f}s (10次重建)")
    print(f"  方案 B: {cache_overhead_b:.2f}s (1次創建)")
    print(f"  差異: {cache_overhead_a - cache_overhead_b:+.2f}s")

    # 給出建議
    print("\n" + "=" * 80)
    print("💡 建議與結論")
    print("=" * 80)

    recommendation = []

    # 基於 cache 命中率
    if summary_a["avg_cache_hit_ratio"] > summary_b["avg_cache_hit_ratio"] * 1.2:
        recommendation.append("🎯 Cache 命中率: 方案 A 顯著較高")
    elif summary_b["avg_cache_hit_ratio"] > summary_a["avg_cache_hit_ratio"] * 1.2:
        recommendation.append("🎯 Cache 命中率: 方案 B 顯著較高")
    else:
        recommendation.append("🎯 Cache 命中率: 兩種方案接近")

    # 基於 token 成本
    if abs(input_percent) < 10:
        recommendation.append("💰 Token 成本: 兩種方案差異不大 (<10%)")
    elif input_diff < 0:
        recommendation.append(f"💰 Token 成本: 方案 A 節省 {abs(input_percent):.1f}%")
    else:
        recommendation.append(f"💰 Token 成本: 方案 B 節省 {abs(input_percent):.1f}%")

    # 基於時間成本
    if abs(time_percent) < 15:
        recommendation.append("⏱️  時間成本: 兩種方案差異不大 (<15%)")
    elif time_diff < 0:
        recommendation.append(f"⏱️  時間成本: 方案 A 快 {abs(time_percent):.1f}%")
    else:
        recommendation.append(f"⏱️  時間成本: 方案 B 快 {abs(time_percent):.1f}%")

    # 實作複雜度
    recommendation.append("\n🔧 實作複雜度:")
    recommendation.append("  方案 A: 複雜（需要管理 cache 生命週期，每次重建）")
    recommendation.append("  方案 B: 簡單（一次性創建，只管理 prompt）")

    # 適用場景
    recommendation.append("\n📝 適用場景:")
    recommendation.append("  方案 A 優勢:")
    recommendation.append("    - 對話累積很長（30+ 分鐘）")
    recommendation.append("    - Cache 命中率顯著提升時")
    recommendation.append("    - 可以接受 cache 重建開銷")
    recommendation.append("\n  方案 B 優勢:")
    recommendation.append("    - 對話較短（10-20 分鐘）")
    recommendation.append("    - 實作簡單，維護容易")
    recommendation.append("    - 即時性要求高（無需等待 cache 重建）")

    # 最終推薦
    recommendation.append("\n🎯 最終推薦:")

    # 決策邏輯
    if summary_a["avg_cache_hit_ratio"] > summary_b["avg_cache_hit_ratio"] * 1.3:
        recommendation.append("  ✅ **推薦方案 A** - Cache 命中率顯著較高")
    elif abs(input_percent) < 10 and abs(time_percent) < 15:
        recommendation.append("  ✅ **推薦方案 B** - 效果接近但實作簡單")
    elif input_diff < 0 and abs(input_percent) > 15:
        recommendation.append("  ✅ **推薦方案 A** - Token 成本顯著較低")
    elif time_diff > 0 and abs(time_percent) > 20:
        recommendation.append("  ✅ **推薦方案 B** - 時間成本顯著較低")
    else:
        recommendation.append("  ✅ **推薦方案 B** - 實作簡單，效果相近")

    # 輸出所有建議
    for line in recommendation:
        print(line)

    # 儲存比較結果
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "strategy_a": results_a,
        "strategy_b": results_b,
        "comparison": {
            "cache_hit_ratio_diff": round(cache_ratio_diff, 2),
            "input_tokens_diff": input_diff,
            "input_tokens_diff_percent": round(input_percent, 2),
            "time_diff_seconds": round(time_diff, 2),
            "time_diff_percent": round(time_percent, 2),
            "cache_creation_overhead_diff": round(
                cache_overhead_a - cache_overhead_b, 2
            ),
        },
        "recommendation": "\n".join(recommendation),
    }

    output_file = "cache_strategy_comparison.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 比較結果已保存: {output_file}")
    print("=" * 80)


async def main():
    print("=" * 80)
    print("🧪 Cache 策略比較實驗")
    print("=" * 80)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Step 1: 執行策略 A
    print("\n📍 步驟 1/3: 測試策略 A")
    result_a = run_script("scripts/test_cache_strategy_a_api.py")
    if result_a is None:
        print("❌ 策略 A 測試失敗，終止比較")
        return

    await asyncio.sleep(2)

    # Step 2: 執行策略 B
    print("\n📍 步驟 2/3: 測試策略 B")
    result_b = run_script("scripts/test_cache_strategy_b_api.py")
    if result_b is None:
        print("❌ 策略 B 測試失敗，終止比較")
        return

    await asyncio.sleep(2)

    # Step 3: 載入並比較結果
    print("\n📍 步驟 3/3: 比較分析")

    results_a = load_results("strategy_a_results.json")
    results_b = load_results("strategy_b_results.json")

    if results_a is None or results_b is None:
        print("❌ 無法載入測試結果，終止比較")
        return

    analyze_results(results_a, results_b)

    print("\n" + "=" * 80)
    print("✅ 實驗完成")
    print(f"結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
