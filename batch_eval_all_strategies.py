#!/usr/bin/env python3
"""批次評估所有 chunk strategies 的性能"""

import subprocess
import time
import json
import requests

BASE_URL = "http://localhost:8000"

# 定義所有要測試的 strategies
STRATEGIES = [
    "rec_256_50",
    "rec_400_80",
    "rec_512_100",
    "rec_1024_200",
    "rec_2048_400"
]

def check_server_health():
    """檢查 API server 是否運行"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.ok
    except:
        return False

def main():
    print("=" * 80)
    print("🚀 批次評估所有 Chunk Strategies")
    print("=" * 80)

    # 檢查 server
    if not check_server_health():
        print("\n❌ 錯誤: API server 未運行")
        print("   請先啟動 server: poetry run uvicorn app.main:app --reload")
        return

    print(f"\n✅ API server 運行中")
    print(f"   測試 {len(STRATEGIES)} 種 strategies: {', '.join(STRATEGIES)}\n")

    results = []

    for i, strategy in enumerate(STRATEGIES):
        print(f"\n{'=' * 80}")
        print(f"📊 [{i+1}/{len(STRATEGIES)}] 評估策略: {strategy}")
        print(f"{'=' * 80}\n")

        start_time = time.time()

        try:
            # 執行測試腳本
            result = subprocess.run(
                ["python3", "test_eval_flow.py", "--chunk-strategy", strategy],
                capture_output=True,
                text=True,
                timeout=600  # 10 分鐘超時
            )

            elapsed_time = time.time() - start_time

            if result.returncode == 0:
                print(f"\n✅ 策略 {strategy} 評估完成 (耗時: {elapsed_time:.1f}s)")
                results.append({
                    "strategy": strategy,
                    "status": "success",
                    "elapsed_time": elapsed_time,
                    "output": result.stdout
                })
            else:
                print(f"\n❌ 策略 {strategy} 評估失敗")
                print(f"   錯誤: {result.stderr}")
                results.append({
                    "strategy": strategy,
                    "status": "failed",
                    "elapsed_time": elapsed_time,
                    "error": result.stderr
                })

        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            print(f"\n⏱️ 策略 {strategy} 評估超時 (> 10 分鐘)")
            results.append({
                "strategy": strategy,
                "status": "timeout",
                "elapsed_time": elapsed_time
            })

        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 策略 {strategy} 執行錯誤: {str(e)}")
            results.append({
                "strategy": strategy,
                "status": "error",
                "elapsed_time": elapsed_time,
                "error": str(e)
            })

        # 等待一下再執行下一個
        if i < len(STRATEGIES) - 1:
            print("\n⏳ 等待 5 秒後執行下一個策略...")
            time.sleep(5)

    # 輸出總結
    print("\n" + "=" * 80)
    print("📈 評估總結")
    print("=" * 80)

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    timeout_count = sum(1 for r in results if r["status"] == "timeout")
    error_count = sum(1 for r in results if r["status"] == "error")

    print(f"\n✅ 成功: {success_count}")
    print(f"❌ 失敗: {failed_count}")
    print(f"⏱️  超時: {timeout_count}")
    print(f"🔥 錯誤: {error_count}")

    print("\n詳細結果:")
    for r in results:
        status_icon = {
            "success": "✅",
            "failed": "❌",
            "timeout": "⏱️",
            "error": "🔥"
        }.get(r["status"], "❓")

        print(f"{status_icon} {r['strategy']:<15} - {r['status']:<10} ({r['elapsed_time']:.1f}s)")

    # 儲存詳細結果
    output_file = "batch_eval_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 詳細結果已儲存至: {output_file}")

    # 獲取並顯示評估結果比較
    print("\n" + "=" * 80)
    print("📊 從 API 獲取評估結果比較")
    print("=" * 80)

    try:
        response = requests.get(f"{BASE_URL}/api/rag/evaluation/experiments?limit=10")
        if response.ok:
            experiments = response.json()

            # 過濾出本次批次的實驗（根據 chunk_strategy）
            batch_exps = [e for e in experiments if e.get('chunk_strategy') in STRATEGIES]

            if batch_exps:
                print(f"\n找到 {len(batch_exps)} 個本次批次的實驗:\n")
                print(f"{'Strategy':<15} {'Faithfulness':<12} {'Answer Rel.':<12} {'Context Prec.':<12} {'Queries':<8}")
                print("-" * 70)

                for exp in batch_exps:
                    strategy = exp.get('chunk_strategy', 'N/A')
                    faith = f"{exp.get('avg_faithfulness', 0):.3f}" if exp.get('avg_faithfulness') else 'N/A'
                    ans_rel = f"{exp.get('avg_answer_relevancy', 0):.3f}" if exp.get('avg_answer_relevancy') else 'N/A'
                    ctx_prec = f"{exp.get('avg_context_precision', 0):.3f}" if exp.get('avg_context_precision') else 'N/A'
                    queries = exp.get('total_queries', 0)

                    print(f"{strategy:<15} {faith:<12} {ans_rel:<12} {ctx_prec:<12} {queries:<8}")

                # 找出最佳策略
                best_faith = max(batch_exps, key=lambda x: x.get('avg_faithfulness', 0) or 0)
                best_ans_rel = max(batch_exps, key=lambda x: x.get('avg_answer_relevancy', 0) or 0)
                best_ctx_prec = max(batch_exps, key=lambda x: x.get('avg_context_precision', 0) or 0)

                print("\n🏆 最佳策略:")
                print(f"   Faithfulness: {best_faith.get('chunk_strategy')} ({best_faith.get('avg_faithfulness', 0):.3f})")
                print(f"   Answer Relevancy: {best_ans_rel.get('chunk_strategy')} ({best_ans_rel.get('avg_answer_relevancy', 0):.3f})")
                print(f"   Context Precision: {best_ctx_prec.get('chunk_strategy')} ({best_ctx_prec.get('avg_context_precision', 0):.3f})")
            else:
                print("\n⚠️  未找到本次批次的實驗結果")
        else:
            print(f"\n❌ 獲取實驗列表失敗: {response.status_code}")

    except Exception as e:
        print(f"\n❌ 獲取評估結果時發生錯誤: {str(e)}")

    print("\n" + "=" * 80)
    print("✅ 批次評估完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
