#!/usr/bin/env python3
"""測試完整評估流程"""

import argparse

import requests

BASE_URL = "http://localhost:8000"


def main(chunk_strategy=None):
    # Step 1: 獲取測試集
    print("📋 步驟 1: 獲取測試集...")
    response = requests.get(f"{BASE_URL}/api/rag/evaluation/testsets/?is_active=true")
    testsets = response.json()
    print(f"   ✓ 找到 {len(testsets)} 個測試集")

    if not testsets:
        print("   ✗ 沒有測試集，退出")
        return

    # 使用第一個測試集
    testset = testsets[0]
    testset_id = testset["id"]
    print(f"   → 使用測試集: {testset['name']} (ID: {testset_id})")

    # Step 2: 獲取測試集詳細資料
    print("\n📊 步驟 2: 獲取測試集詳細資料...")
    response = requests.get(f"{BASE_URL}/api/rag/evaluation/testsets/{testset_id}")
    testset_detail = response.json()
    test_cases = testset_detail["test_cases"]
    print(f"   ✓ 測試集包含 {len(test_cases)} 個測試案例")

    # Step 3: 檢查是否需要生成答案
    print("\n🤖 步驟 3: 檢查測試案例...")
    needs_answer = []
    for i, tc in enumerate(test_cases):
        if not tc.get("answer") or tc["answer"] == "":
            needs_answer.append(i)
            print(f"   ⚠ 測試案例 {i+1} 缺少答案")

    if needs_answer:
        print(f"\n   → 需要為 {len(needs_answer)} 個測試案例生成答案")

        for idx in needs_answer:
            tc = test_cases[idx]
            print(
                f"\n   生成答案 {idx+1}/{len(needs_answer)}: {tc['question'][:50]}..."
            )

            # Call RAG API
            rag_payload = {"question": tc["question"], "top_k": 3}
            if chunk_strategy:
                rag_payload["chunk_strategy"] = chunk_strategy

            rag_response = requests.post(f"{BASE_URL}/api/rag/chat/", json=rag_payload)

            if rag_response.ok:
                rag_result = rag_response.json()
                tc["answer"] = rag_result["answer"]
                tc["contexts"] = tc.get("contexts") or [
                    c["text"] for c in rag_result.get("citations", [])
                ]
                print("   ✓ 答案已生成")
            else:
                print(f"   ✗ 生成答案失敗: {rag_response.status_code}")
                print(f"     {rag_response.text}")
                return
    else:
        print("   ✓ 所有測試案例都有答案")

    # Step 4: 建立實驗
    print("\n🧪 步驟 4: 建立實驗...")
    exp_data = {
        "name": f"測試流程 - {testset['name']}"
        + (f" ({chunk_strategy})" if chunk_strategy else ""),
        "description": f"完整流程測試 - 使用測試集「{testset['name']}」"
        + (f"，策略: {chunk_strategy}" if chunk_strategy else ""),
        "experiment_type": "end_to_end",
        "chunking_method": "recursive",
        "chunk_size": 400,
        "chunk_overlap": 80,
        "chunk_strategy": chunk_strategy,  # NEW: include strategy in experiment
    }

    response = requests.post(
        f"{BASE_URL}/api/rag/evaluation/experiments", json=exp_data
    )

    if not response.ok:
        print(f"   ✗ 建立實驗失敗: {response.status_code}")
        print(f"     {response.text}")
        return

    experiment = response.json()
    experiment_id = experiment["id"]
    print(f"   ✓ 實驗已建立 (ID: {experiment_id})")

    # Step 5: 執行評估
    print("\n🚀 步驟 5: 執行評估...")
    print(f"   → 準備 {len(test_cases)} 個測試案例")

    eval_data = {
        "test_cases": test_cases,
        "include_ground_truth": any(tc.get("ground_truth") for tc in test_cases),
    }

    print("\n   開始 RAGAS 評估...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/rag/evaluation/experiments/{experiment_id}/run",
            json=eval_data,
            timeout=300,  # 5 minutes timeout
        )

        if response.ok:
            result = response.json()
            print("\n✅ 評估完成！")
            print(f"   - 狀態: {result['status']}")
            print(f"   - 總查詢數: {result['total_queries']}")
            print(f"   - Faithfulness: {result.get('avg_faithfulness', 'N/A')}")
            print(f"   - Answer Relevancy: {result.get('avg_answer_relevancy', 'N/A')}")
            print(f"   - Context Recall: {result.get('avg_context_recall', 'N/A')}")
            print(
                f"   - Context Precision: {result.get('avg_context_precision', 'N/A')}"
            )
            print(f"   - MLflow Run ID: {result.get('mlflow_run_id', 'N/A')}")
        else:
            print(f"\n✗ 評估失敗: {response.status_code}")
            print(f"   錯誤: {response.text}")

    except requests.exceptions.Timeout:
        print("\n✗ 評估超時 (> 5 分鐘)")
    except Exception as e:
        print(f"\n✗ 執行錯誤: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="測試完整評估流程")
    parser.add_argument(
        "--chunk-strategy",
        type=str,
        help="Chunk strategy to use (e.g., rec_400_80, rec_512_100)",
    )
    args = parser.parse_args()

    main(chunk_strategy=args.chunk_strategy)
