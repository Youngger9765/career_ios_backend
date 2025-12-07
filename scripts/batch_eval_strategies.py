#!/usr/bin/env python3
"""
批次評估所有 Chunk Strategies 並生成比較報告
使用 API 直接執行，不依賴外部腳本
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List

import requests

BASE_URL = "http://localhost:8000"

# 定義所有要測試的 strategies
STRATEGIES = [
    {"name": "rec_256_50", "size": 256, "overlap": 50},
    {"name": "rec_400_80", "size": 400, "overlap": 80},
    {"name": "rec_512_100", "size": 512, "overlap": 100},
    {"name": "rec_1024_200", "size": 1024, "overlap": 200},
    {"name": "rec_2048_400", "size": 2048, "overlap": 400},
]

# 測試問題集（可自定義）
TEST_QUESTIONS = [
    "如何探索自己的職涯興趣？",
    "轉職到科技業需要什麼準備？",
    "如何準備軟體工程師面試？",
    "職涯發展遇到瓶頸怎麼辦？",
    "如何在職場建立個人品牌？",
]


def check_server_health() -> bool:
    """檢查 API server 是否運行"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.ok
    except Exception:
        return False


def generate_test_cases_with_rag(chunk_strategy: str) -> List[Dict[str, Any]]:
    """使用 RAG API 生成測試案例的答案和上下文"""
    print(f"   📝 生成測試案例答案 (使用策略: {chunk_strategy})...")

    test_cases = []
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"      [{i}/{len(TEST_QUESTIONS)}] {question[:30]}...")

        try:
            response = requests.post(
                f"{BASE_URL}/api/rag/chat/",
                json={
                    "question": question,
                    "top_k": 3,
                    "chunk_strategy": chunk_strategy,
                },
                timeout=30,
            )

            if response.ok:
                rag_result = response.json()
                test_cases.append(
                    {
                        "question": question,
                        "answer": rag_result["answer"],
                        "contexts": [
                            c["text"] for c in rag_result.get("citations", [])
                        ],
                    }
                )
            else:
                print(f"         ❌ RAG 生成失敗: {response.status_code}")
                return []

        except Exception as e:
            print(f"         ❌ 錯誤: {str(e)}")
            return []

    print(f"   ✅ 成功生成 {len(test_cases)} 個測試案例")
    return test_cases


def create_experiment(strategy: Dict[str, Any]) -> str:
    """建立評估實驗"""
    print("   🔬 建立實驗...")

    exp_data = {
        "name": f"批次評估 - {strategy['name']} - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": f"批次評估 chunk strategy: {strategy['name']} (size={strategy['size']}, overlap={strategy['overlap']})",
        "experiment_type": "end_to_end",
        "chunking_method": "recursive",
        "chunk_size": strategy["size"],
        "chunk_overlap": strategy["overlap"],
        "chunk_strategy": strategy["name"],
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/rag/evaluation/experiments", json=exp_data, timeout=10
        )

        if response.ok:
            experiment = response.json()
            exp_id = experiment["id"]
            print(f"   ✅ 實驗已建立: {exp_id}")
            return exp_id
        else:
            print(f"   ❌ 建立實驗失敗: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ 錯誤: {str(e)}")
        return None


def run_evaluation(experiment_id: str, test_cases: List[Dict[str, Any]]) -> bool:
    """執行評估"""
    print("   ⚡ 執行 RAGAS 評估...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/rag/evaluation/experiments/{experiment_id}/run",
            json={"test_cases": test_cases, "include_ground_truth": False},
            timeout=300,  # 5 分鐘超時
        )

        if response.ok:
            result = response.json()
            print("   ✅ 評估完成!")
            print(f"      - Faithfulness: {result.get('avg_faithfulness', 0):.3f}")
            print(
                f"      - Answer Relevancy: {result.get('avg_answer_relevancy', 0):.3f}"
            )
            print(f"      - Total Queries: {result.get('total_queries', 0)}")
            return True
        else:
            print(f"   ❌ 評估失敗: {response.status_code} - {response.text}")
            return False

    except requests.Timeout:
        print("   ⏱️  評估超時 (> 5 分鐘)")
        return False
    except Exception as e:
        print(f"   ❌ 錯誤: {str(e)}")
        return False


def get_experiment_results(experiment_id: str) -> Dict[str, Any]:
    """獲取實驗結果"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/rag/evaluation/experiments/{experiment_id}", timeout=10
        )

        if response.ok:
            return response.json()
        else:
            return None

    except Exception as e:
        print(f"   ❌ 獲取結果錯誤: {str(e)}")
        return None


def evaluate_strategy(strategy: Dict[str, Any]) -> Dict[str, Any]:
    """評估單一策略"""
    print(f"\n{'=' * 80}")
    print(
        f"📊 評估策略: {strategy['name']} (size={strategy['size']}, overlap={strategy['overlap']})"
    )
    print(f"{'=' * 80}\n")

    start_time = time.time()

    # Step 1: 生成測試案例
    test_cases = generate_test_cases_with_rag(strategy["name"])
    if not test_cases:
        return {
            "strategy": strategy["name"],
            "status": "failed",
            "error": "Failed to generate test cases",
            "elapsed_time": time.time() - start_time,
        }

    # Step 2: 建立實驗
    exp_id = create_experiment(strategy)
    if not exp_id:
        return {
            "strategy": strategy["name"],
            "status": "failed",
            "error": "Failed to create experiment",
            "elapsed_time": time.time() - start_time,
        }

    # Step 3: 執行評估
    success = run_evaluation(exp_id, test_cases)
    if not success:
        return {
            "strategy": strategy["name"],
            "status": "failed",
            "error": "Evaluation failed",
            "elapsed_time": time.time() - start_time,
            "experiment_id": exp_id,
        }

    # Step 4: 獲取結果
    result = get_experiment_results(exp_id)
    elapsed_time = time.time() - start_time

    if result:
        return {
            "strategy": strategy["name"],
            "status": "success",
            "elapsed_time": elapsed_time,
            "experiment_id": exp_id,
            "metrics": {
                "faithfulness": result.get("avg_faithfulness"),
                "answer_relevancy": result.get("avg_answer_relevancy"),
                "context_recall": result.get("avg_context_recall"),
                "context_precision": result.get("avg_context_precision"),
                "total_queries": result.get("total_queries", 0),
                "avg_latency_ms": result.get("avg_latency_ms"),
            },
        }
    else:
        return {
            "strategy": strategy["name"],
            "status": "failed",
            "error": "Failed to get results",
            "elapsed_time": elapsed_time,
            "experiment_id": exp_id,
        }


def print_comparison_table(results: List[Dict[str, Any]]):
    """列印比較表格"""
    print("\n" + "=" * 80)
    print("📊 策略比較表")
    print("=" * 80 + "\n")

    # 表頭
    print(
        f"{'Strategy':<15} {'Status':<10} {'Faithfulness':<13} {'Answer Rel.':<13} {'Queries':<8} {'Time(s)':<8}"
    )
    print("-" * 80)

    # 表格內容
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "❌"
        strategy = r["strategy"]
        status = r["status"]
        time_str = f"{r['elapsed_time']:.1f}"

        if r["status"] == "success" and "metrics" in r:
            m = r["metrics"]
            faith = f"{m['faithfulness']:.3f}" if m["faithfulness"] else "N/A"
            ans_rel = f"{m['answer_relevancy']:.3f}" if m["answer_relevancy"] else "N/A"
            queries = str(m["total_queries"])
        else:
            faith = ans_rel = queries = "N/A"

        print(
            f"{status_icon} {strategy:<13} {status:<10} {faith:<13} {ans_rel:<13} {queries:<8} {time_str:<8}"
        )


def recommend_best_strategy(results: List[Dict[str, Any]]):
    """推薦最佳策略"""
    print("\n" + "=" * 80)
    print("🏆 最佳策略推薦")
    print("=" * 80 + "\n")

    successful_results = [
        r for r in results if r["status"] == "success" and "metrics" in r
    ]

    if not successful_results:
        print("❌ 沒有成功的評估結果，無法推薦")
        return

    # 找出各項指標最佳的策略
    best_faith = max(
        successful_results, key=lambda x: x["metrics"]["faithfulness"] or 0
    )
    best_ans_rel = max(
        successful_results, key=lambda x: x["metrics"]["answer_relevancy"] or 0
    )

    # 計算綜合分數（faithfulness 60% + answer_relevancy 40%）
    for r in successful_results:
        m = r["metrics"]
        faith = m["faithfulness"] or 0
        ans_rel = m["answer_relevancy"] or 0
        r["composite_score"] = faith * 0.6 + ans_rel * 0.4

    best_overall = max(successful_results, key=lambda x: x["composite_score"])

    print(f"🥇 **最佳綜合策略**: {best_overall['strategy']}")
    print(f"   - 綜合分數: {best_overall['composite_score']:.3f}")
    print(f"   - Faithfulness: {best_overall['metrics']['faithfulness']:.3f}")
    print(f"   - Answer Relevancy: {best_overall['metrics']['answer_relevancy']:.3f}")
    print(f"   - 執行時間: {best_overall['elapsed_time']:.1f}s")

    print("\n📈 各項指標最佳:")
    print(
        f"   - Faithfulness: {best_faith['strategy']} ({best_faith['metrics']['faithfulness']:.3f})"
    )
    print(
        f"   - Answer Relevancy: {best_ans_rel['strategy']} ({best_ans_rel['metrics']['answer_relevancy']:.3f})"
    )

    # 分析效能 vs 品質
    fastest = min(successful_results, key=lambda x: x["elapsed_time"])
    print(f"\n⚡ 執行最快: {fastest['strategy']} ({fastest['elapsed_time']:.1f}s)")

    # 提供建議
    print("\n💡 建議:")
    if best_overall["strategy"] == fastest["strategy"]:
        print(f"   ✅ {best_overall['strategy']} 兼顧品質與效能，強烈推薦！")
    else:
        print(f"   - 追求品質: 使用 {best_overall['strategy']}")
        print(f"   - 追求速度: 使用 {fastest['strategy']}")


def generate_report(results: List[Dict[str, Any]]):
    """生成詳細報告檔案"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"batch_eval_report_{timestamp}.json"

    # 計算統計資料
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]

    report = {
        "timestamp": timestamp,
        "summary": {
            "total_strategies": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_time": sum(r["elapsed_time"] for r in results),
        },
        "test_configuration": {
            "test_questions": TEST_QUESTIONS,
            "strategies": STRATEGIES,
        },
        "results": results,
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 詳細報告已儲存至: {report_file}")

    # 同時生成 Markdown 報告
    md_file = f"batch_eval_report_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# Chunk Strategy 批次評估報告\n\n")
        f.write(f"**評估時間**: {timestamp}\n\n")
        f.write("## 測試配置\n\n")
        f.write(f"- 策略數量: {len(STRATEGIES)}\n")
        f.write(f"- 測試問題: {len(TEST_QUESTIONS)} 個\n\n")

        f.write("## 結果總覽\n\n")
        f.write("| 策略 | 狀態 | Faithfulness | Answer Relevancy | 執行時間(s) |\n")
        f.write("|------|------|--------------|------------------|-------------|\n")

        for r in results:
            if r["status"] == "success" and "metrics" in r:
                m = r["metrics"]
                f.write(
                    f"| {r['strategy']} | ✅ | {m['faithfulness']:.3f} | {m['answer_relevancy']:.3f} | {r['elapsed_time']:.1f} |\n"
                )
            else:
                f.write(
                    f"| {r['strategy']} | ❌ | N/A | N/A | {r['elapsed_time']:.1f} |\n"
                )

        f.write("\n## 推薦策略\n\n")
        if successful:
            best = max(
                successful,
                key=lambda x: (x["metrics"]["faithfulness"] or 0) * 0.6
                + (x["metrics"]["answer_relevancy"] or 0) * 0.4,
            )
            f.write(f"**推薦**: {best['strategy']}\n\n")
            f.write(f"- Faithfulness: {best['metrics']['faithfulness']:.3f}\n")
            f.write(f"- Answer Relevancy: {best['metrics']['answer_relevancy']:.3f}\n")

    print(f"📄 Markdown 報告已儲存至: {md_file}")


def main():
    print("=" * 80)
    print("🚀 批次評估所有 Chunk Strategies (API 直接版)")
    print("=" * 80)

    # 檢查 server
    if not check_server_health():
        print("\n❌ 錯誤: API server 未運行")
        print("   請先啟動 server: poetry run uvicorn app.main:app --reload")
        return

    print("\n✅ API server 運行中")
    print(
        f"   測試 {len(STRATEGIES)} 種策略: {', '.join([s['name'] for s in STRATEGIES])}"
    )
    print(f"   測試問題數: {len(TEST_QUESTIONS)}\n")

    # 執行評估
    results = []
    total_start_time = time.time()

    for i, strategy in enumerate(STRATEGIES):
        result = evaluate_strategy(strategy)
        results.append(result)

        # 等待一下再執行下一個
        if i < len(STRATEGIES) - 1:
            print("\n⏳ 等待 3 秒後執行下一個策略...")
            time.sleep(3)

    total_elapsed_time = time.time() - total_start_time

    # 列印比較表格
    print_comparison_table(results)

    # 推薦最佳策略
    recommend_best_strategy(results)

    # 生成報告
    generate_report(results)

    print("\n" + "=" * 80)
    print(f"✅ 批次評估完成！總耗時: {total_elapsed_time:.1f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
