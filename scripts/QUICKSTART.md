# LLM Provider Comparison - Quick Start Guide

## TL;DR

比較四個 LLM 方案（Gemini + 3個 Codeer 模型）在親子諮詢分析場景下的表現。

**一行命令運行完整實驗**：
```bash
poetry run python scripts/compare_four_providers.py
```

---

## 5 分鐘快速開始

### Step 1: 確認環境 (30 秒)

```bash
# 檢查 Python 版本（需要 3.11+）
python --version

# 檢查 Poetry 可用
poetry --version

# 檢查 .env 配置（確保有 Codeer agent IDs）
grep CODEER_AGENT .env

# 應該看到：
# CODEER_AGENT_CLAUDE_SONNET=...
# CODEER_AGENT_GEMINI_FLASH=...
# CODEER_AGENT_GPT5_MINI=...
```

### Step 2: 驗證安裝 (30 秒)

```bash
# 運行驗證測試
poetry run python scripts/test_experiment_functions.py

# 預期輸出：
# ✓ Data loading test passed
# ✓ Quality evaluation test passed
# ✓ Cost calculation test passed
# ✓ All tests passed!
```

### Step 3: 快速測試 (1 分鐘)

```bash
# 先測試單一 provider，確保一切正常
poetry run python scripts/compare_four_providers.py \
  --provider gemini \
  --duration 8

# 預期輸出：
# [1/1] Testing GEMINI - gemini-2.0-flash-exp... OK - XXXXms, Quality: XX.X/100
# ⚡ Speed Comparison table
# ⭐ Quality Comparison table
# 💰 Cost Comparison table
# Results saved to: experiment_results.json
```

### Step 4: 完整實驗 (5-10 分鐘)

```bash
# 運行完整實驗（12 個測試）
poetry run python scripts/compare_four_providers.py

# 喝杯咖啡，等待結果...
```

### Step 5: 查看結果 (1 分鐘)

```bash
# 終端會直接顯示三個比較表格和推薦建議

# 或查看 JSON 結果
cat experiment_results.json | jq .

# 或用 Python 分析
poetry run python -c "
import json
with open('experiment_results.json') as f:
    data = json.load(f)
    print(f'Total tests: {len(data[\"results\"])}')
    print(f'Timestamp: {data[\"timestamp\"]}')
"
```

---

## 常用命令

### 測試特定 Provider

```bash
# 只測試 Gemini（有 cache）
poetry run python scripts/compare_four_providers.py --provider gemini

# 只測試所有 Codeer 模型
poetry run python scripts/compare_four_providers.py --provider codeer

# 只測試 Claude Sonnet
poetry run python scripts/compare_four_providers.py --provider claude-sonnet

# 只測試 Gemini Flash
poetry run python scripts/compare_four_providers.py --provider gemini-flash

# 只測試 GPT-5 Mini
poetry run python scripts/compare_four_providers.py --provider gpt5-mini
```

### 測試特定時長

```bash
# 只測試 8 分鐘逐字稿
poetry run python scripts/compare_four_providers.py --duration 8

# 只測試 10 分鐘逐字稿（最長）
poetry run python scripts/compare_four_providers.py --duration 10
```

### 組合篩選

```bash
# Codeer Claude + 10分鐘逐字稿（最嚴格測試）
poetry run python scripts/compare_four_providers.py \
  --provider claude-sonnet \
  --duration 10

# Gemini + 所有時長（測試 cache 效果）
poetry run python scripts/compare_four_providers.py \
  --provider gemini

# 所有 Codeer + 單一時長（比較三個模型）
poetry run python scripts/compare_four_providers.py \
  --provider codeer \
  --duration 9
```

### 自訂輸出路徑

```bash
# 保存到特定文件
poetry run python scripts/compare_four_providers.py \
  --output results_2025-12-11.json

# 多次實驗，使用時間戳
poetry run python scripts/compare_four_providers.py \
  --output "results_$(date +%Y%m%d_%H%M%S).json"
```

---

## 預期輸出

### 終端顯示範例

```
╭─────────────────────────────────────────────╮
│   Starting LLM Provider Comparison Experiment │
│ Total tests: 12                              │
│ Durations: [8, 9, 10] minutes                │
│ Providers: 4 configurations                  │
╰─────────────────────────────────────────────╯

Testing 8-minute transcript: 孩子不願意做功課
  [1/12] Testing GEMINI - gemini-2.0-flash-exp... OK - 1234ms, Quality: 85.2/100
  [2/12] Testing CODEER - claude-sonnet... OK - 2345ms, Quality: 88.5/100
  [3/12] Testing CODEER - gemini-flash... OK - 1567ms, Quality: 82.1/100
  [4/12] Testing CODEER - gpt5-mini... OK - 1890ms, Quality: 86.3/100

Testing 9-minute transcript: 青少年叛逆期問題
  [5/12] Testing GEMINI - gemini-2.0-flash-exp... OK - 1456ms, Quality: 84.7/100
  [6/12] Testing CODEER - claude-sonnet... OK - 2567ms, Quality: 89.2/100
  [7/12] Testing CODEER - gemini-flash... OK - 1678ms, Quality: 81.5/100
  [8/12] Testing CODEER - gpt5-mini... OK - 1934ms, Quality: 85.9/100

Testing 10-minute transcript: 手足衝突
  [9/12] Testing GEMINI - gemini-2.0-flash-exp... OK - 1678ms, Quality: 86.1/100
  [10/12] Testing CODEER - claude-sonnet... OK - 2789ms, Quality: 90.1/100
  [11/12] Testing CODEER - gemini-flash... OK - 1789ms, Quality: 83.4/100
  [12/12] Testing CODEER - gpt5-mini... OK - 2012ms, Quality: 87.2/100

╭───────────────────────────────────────────────╮
│         Experiment Results Analysis            │
╰───────────────────────────────────────────────╯

⚡ Speed Comparison (Latency in milliseconds)
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Duration ┃ Gemini     ┃ Codeer       ┃ Codeer       ┃ Codeer       ┃
┃          ┃ (cache)    ┃ Claude       ┃ Gemini       ┃ GPT-5        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  8 min   │ 1234       │ 2345         │ 1567         │ 1890         │
│  9 min   │ 1456       │ 2567         │ 1678         │ 1934         │
│ 10 min   │ 1678       │ 2789         │ 1789         │ 2012         │
└──────────┴────────────┴──────────────┴──────────────┴──────────────┘

⭐ Quality Comparison (Score 0-100)
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Duration ┃ Gemini     ┃ Codeer       ┃ Codeer       ┃ Codeer       ┃
┃          ┃ (cache)    ┃ Claude       ┃ Gemini       ┃ GPT-5        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  8 min   │ 85.2       │ 88.5         │ 82.1         │ 86.3         │
│  9 min   │ 84.7       │ 89.2         │ 81.5         │ 85.9         │
│ 10 min   │ 86.1       │ 90.1         │ 83.4         │ 87.2         │
└──────────┴────────────┴──────────────┴──────────────┴──────────────┘

💰 Cost Comparison (USD)
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Duration ┃ Gemini     ┃ Codeer       ┃ Codeer       ┃ Codeer       ┃
┃          ┃ (cache)    ┃ Claude       ┃ Gemini       ┃ GPT-5        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  8 min   │ $0.000123  │ $0.010000    │ $0.010000    │ $0.010000    │
│  9 min   │ $0.000145  │ $0.010000    │ $0.010000    │ $0.010000    │
│ 10 min   │ $0.000167  │ $0.010000    │ $0.010000    │ $0.010000    │
└──────────┴────────────┴──────────────┴──────────────┴──────────────┘

Average Metrics Across All Tests:

Gemini Gemini 2.0 Flash Exp:
  Speed: 1456 ms
  Quality: 85.3 / 100
  Cost: $0.000145

Codeer Claude Sonnet:
  Speed: 2567 ms
  Quality: 89.3 / 100
  Cost: $0.010000

Codeer Gemini Flash:
  Speed: 1678 ms
  Quality: 82.3 / 100
  Cost: $0.010000

Codeer Gpt5 Mini:
  Speed: 1945 ms
  Quality: 86.5 / 100
  Cost: $0.010000

Weighted Scoring (Quality 50%, Speed 30%, Cost 20%):
(Based on normalized 0-100 scores)

╭───────────────────────────────────────────╮
│ 🏆 Winner: Codeer Claude Sonnet           │
│ Weighted Score: 87.5 / 100                │
╰───────────────────────────────────────────╯

Results saved to: experiment_results.json
```

---

## 解讀結果

### 速度比較
- **越小越好**（毫秒）
- Gemini (cache) 通常最快（cache hit 後）
- Codeer Claude 可能較慢（模型複雜度）

### 品質比較
- **越高越好**（0-100 分）
- 85+ 分：優秀
- 70-85 分：良好
- < 70 分：需改進

### 成本比較
- **越低越好**（美金）
- Gemini 通常最便宜（< $0.001）
- Codeer 成本需確認（目前估算 $0.01）

### 加權總分
- **Quality 50%**：品質最重要
- **Speed 30%**：速度次之
- **Cost 20%**：成本最後

---

## 常見問題

### Q: 測試失敗了怎麼辦？
```bash
# 1. 檢查 .env 配置
grep CODEER_AGENT .env

# 2. 運行驗證測試
poetry run python scripts/test_experiment_functions.py

# 3. 查看詳細錯誤（開啟 debug logging）
export LOG_LEVEL=DEBUG
poetry run python scripts/compare_four_providers.py --provider gemini --duration 8

# 4. 檢查 experiment_results.json 中的 error 欄位
cat experiment_results.json | jq '.results[] | select(.error)'
```

### Q: 如何只測試一個特定案例？
```bash
# 組合 --provider 和 --duration 篩選
poetry run python scripts/compare_four_providers.py \
  --provider claude-sonnet \
  --duration 10
```

### Q: 成本太高怎麼辦？
```bash
# 1. 先用單一時長測試
poetry run python scripts/compare_four_providers.py --duration 8

# 2. 或只測試 Gemini（最便宜）
poetry run python scripts/compare_four_providers.py --provider gemini

# 3. Gemini 成本非常低（< $0.001 per test）
# 4. Codeer 成本需確認實際定價
```

### Q: 如何查看詳細的分析回應？
```bash
# 查看 JSON 結果中的 analysis 欄位
cat experiment_results.json | jq '.results[0].analysis'

# 輸出：
# {
#   "summary": "案主面臨...",
#   "alerts": ["💡 ...", "⚠️ ..."],
#   "suggestions": ["💡 ...", "💡 ..."]
# }
```

### Q: 如何重新運行實驗？
```bash
# 實驗會覆蓋 experiment_results.json
# 如果要保留舊結果，使用 --output 指定新文件名

poetry run python scripts/compare_four_providers.py \
  --output results_backup_$(date +%Y%m%d).json
```

---

## 進階使用

### 批次實驗
```bash
# 測試所有 provider，分別保存結果
for provider in gemini claude-sonnet gemini-flash gpt5-mini; do
  echo "Testing $provider..."
  poetry run python scripts/compare_four_providers.py \
    --provider $provider \
    --output "results_${provider}.json"
done
```

### 多次重複測試（測試穩定性）
```bash
# 運行 3 次實驗，比較結果
for i in 1 2 3; do
  echo "Run $i/3..."
  poetry run python scripts/compare_four_providers.py \
    --output "results_run${i}.json"
done

# 比較三次結果的 quality scores
jq '.results[].quality_score.total_score' results_run*.json
```

### 自訂評分權重
```python
# 編輯 scripts/compare_four_providers.py

# 找到 evaluate_quality() 函數，調整權重：
total_score = (
    scores["structure"] * 0.1      # 降低結構權重
    + scores["relevance"] * 0.4    # 提高相關性權重
    + scores["professionalism"] * 0.4  # 提高專業性權重
    + scores["completeness"] * 0.1  # 降低完整性權重
)

# 找到 analyze_results() 函數，調整總權重：
weighted_total = (
    quality_score * 0.6   # 提高品質權重
    + speed_score * 0.2   # 降低速度權重
    + cost_score * 0.2    # 維持成本權重
)
```

---

## 檔案位置

```
career_ios_backend/
├── tests/data/
│   └── long_transcripts.json          # 測試數據
├── scripts/
│   ├── compare_four_providers.py      # 主要腳本
│   ├── test_experiment_functions.py   # 驗證測試
│   ├── QUICKSTART.md                  # 本文件
│   ├── EXPERIMENT_README.md           # 完整文檔
│   ├── EXPERIMENT_DELIVERABLES.md     # 交付清單
│   └── EXPERIMENT_WORKFLOW.md         # 流程圖
└── experiment_results.json            # 結果（執行後生成）
```

---

## 下一步

1. ✅ **驗證安裝**: `poetry run python scripts/test_experiment_functions.py`
2. ✅ **快速測試**: `poetry run python scripts/compare_four_providers.py --provider gemini --duration 8`
3. ✅ **完整實驗**: `poetry run python scripts/compare_four_providers.py`
4. ✅ **分析結果**: 查看終端輸出和 `experiment_results.json`
5. 📊 **人工審閱**: 檢查實際的 analysis 回應品質
6. 🚀 **做決策**: 根據加權總分選擇最佳方案

---

**版本**: v1.0
**最後更新**: 2025-12-11
**預計時間**: 5-10 分鐘完成完整實驗

需要幫助？查看 `EXPERIMENT_README.md` 的問題排除區段。
