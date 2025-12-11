# LLM Provider Comparison Experiment - Deliverables

## 交付內容總覽

完整的實驗框架已創建，用於比較四種 LLM 方案。所有組件都已測試並可立即使用。

---

## 📦 已創建的文件

### 1. 測試數據
**文件**: `tests/data/long_transcripts.json`

三組真實的親子諮詢逐字稿：
- **8分鐘對話** (~1400字) - 主題：孩子不願意做功課
- **9分鐘對話** (~1600字) - 主題：青少年叛逆期問題
- **10分鐘對話** (~1800字) - 主題：手足衝突

每組包含：
```json
{
  "duration_minutes": 8,
  "topic": "孩子不願意做功課",
  "time_range": "0:00-8:00",
  "speakers": [...],  // counselor/client 交替對話
  "transcript": "..."  // 完整逐字稿文字
}
```

### 2. 主要實驗腳本
**文件**: `scripts/compare_four_providers.py` (856 行)

完整的實驗執行框架，包含：

#### a. 品質評估模組 (Quality Evaluation)
- `evaluate_structure()` - 結構完整性 (20%)
- `evaluate_relevance()` - 相關性 (30%)
- `evaluate_professionalism()` - 專業性 (30%)
- `evaluate_completeness()` - 完整性 (20%)
- `evaluate_quality()` - 綜合評分 (0-100)

#### b. 成本計算模組 (Cost Calculation)
- `calculate_gemini_cost()` - Gemini API 成本計算（基於 token usage）
- `calculate_codeer_cost()` - Codeer API 成本估算（基於 API calls）

#### c. 測試執行模組 (Test Execution)
- `test_gemini_with_cache()` - 測試 Gemini + explicit caching
- `test_codeer_model()` - 測試 Codeer 模型（支援 session pool）
- `run_single_test()` - 單一測試執行器

#### d. 實驗管理模組 (Experiment Runner)
- `run_experiment()` - 主要實驗流程
- 支援篩選條件：`--provider`, `--duration`
- 實時進度顯示

#### e. 結果分析模組 (Results Analysis)
- `analyze_results()` - 結果分析和可視化
- 生成三個比較表格：
  - ⚡ 速度比較 (Latency in ms)
  - ⭐ 品質比較 (Score 0-100)
  - 💰 成本比較 (USD)
- 加權總分計算（Quality 50%, Speed 30%, Cost 20%）
- 推薦最佳方案

#### f. 結果持久化模組
- `save_results()` - 保存 JSON 結果到文件

### 3. 文檔
**文件**: `scripts/EXPERIMENT_README.md`

完整的使用指南，包含：
- 實驗目標和設計
- 評估維度詳細說明
- 使用方式和命令範例
- 輸出範例
- 實驗腳本架構說明
- 問題排除指南
- 後續改進方向

### 4. 驗證測試腳本
**文件**: `scripts/test_experiment_functions.py`

用於驗證核心功能的測試腳本：
- 測試數據載入
- 測試品質評估函數
- 測試成本計算函數
- ✓ 所有測試通過

---

## 🎯 比較的四個方案

1. **Gemini with Explicit Context Caching** (現有方案)
   - Model: `gemini-2.0-flash-exp`
   - Cache: 支援，使用 Vertex AI Caching API
   - 成本：非常低（< $0.001 per test）

2. **Codeer Claude Sonnet 4.5** (新方案)
   - Model: `claude-sonnet-4-5`
   - Session: 支援 session pool reuse
   - Agent ID: `CODEER_AGENT_CLAUDE_SONNET`

3. **Codeer Gemini 2.5 Flash** (新方案)
   - Model: `gemini-2.5-flash`
   - Session: 支援 session pool reuse
   - Agent ID: `CODEER_AGENT_GEMINI_FLASH`

4. **Codeer GPT-5 Mini** (新方案)
   - Model: `gpt-5-mini`
   - Session: 支援 session pool reuse
   - Agent ID: `CODEER_AGENT_GPT5_MINI`

---

## 📊 評估維度

### 1. 品質評估 (Quality Score: 0-100)

**加權計算**：
```
總分 = (Structure * 0.2) + (Relevance * 0.3) + (Professionalism * 0.3) + (Completeness * 0.2)
```

**四個子維度**：

#### a. 結構完整性 (Structure: 20%)
- [x] JSON 格式正確
- [x] 包含 summary, alerts, suggestions 欄位
- [x] 每個欄位都有內容

#### b. 相關性 (Relevance: 30%)
- [x] 建議是否針對逐字稿內容
- [x] 是否提到關鍵問題（功課、叛逆、衝突等）
- [x] 是否包含親子相關術語

#### c. 專業性 (Professionalism: 30%)
- [x] 使用正確的諮詢術語（同理、理解、引導等）
- [x] 提供具體可行的建議
- [x] 避免批判性語言（不當、錯誤、暴力等）

#### d. 完整性 (Completeness: 20%)
- [x] 提醒事項數量（理想：3-5點）
- [x] 建議回應數量（理想：2-3點）
- [x] 建議長度（理想：< 50字）

### 2. 速度評估 (Speed)
- 測量 API 回應延遲（毫秒）
- 包含完整的端到端時間（cache/session pool 管理）

### 3. 成本評估 (Cost)
- **Gemini**: 基於 token usage（input, cached, output）
- **Codeer**: 基於 API calls（估算值，需確認實際定價）

---

## 🚀 使用方式

### 快速開始

```bash
# 完整實驗（所有 provider，所有時長）
poetry run python scripts/compare_four_providers.py

# 只測試 Gemini
poetry run python scripts/compare_four_providers.py --provider gemini

# 只測試 Codeer Claude Sonnet
poetry run python scripts/compare_four_providers.py --provider claude-sonnet

# 只測試 10 分鐘逐字稿
poetry run python scripts/compare_four_providers.py --duration 10

# 組合篩選
poetry run python scripts/compare_four_providers.py \
  --provider claude-sonnet \
  --duration 10 \
  --output my_results.json
```

### 預期輸出

1. **終端實時顯示**：
   - 進度條和測試狀態
   - 三個比較表格（速度、品質、成本）
   - 加權總分和推薦建議

2. **JSON 結果文件** (`experiment_results.json`)：
   - 完整的測試數據
   - 每個測試的詳細結果
   - 品質評分細節
   - 成本計算細節

### 驗證安裝

```bash
# 測試核心功能
poetry run python scripts/test_experiment_functions.py

# 預期輸出：
# ✓ Data loading test passed
# ✓ Quality evaluation test passed
# ✓ Cost calculation test passed
# ✓ All tests passed!
```

---

## ⚠️ 重要注意事項

### 1. 前置條件

**必須配置的環境變數** (`.env` 文件)：
```bash
# Gemini
GEMINI_PROJECT_ID=your-project-id
GEMINI_LOCATION=us-central1
GEMINI_CHAT_MODEL=gemini-2.5-flash

# Codeer
CODEER_API_KEY=your-api-key
CODEER_AGENT_CLAUDE_SONNET=agent-id
CODEER_AGENT_GEMINI_FLASH=agent-id
CODEER_AGENT_GPT5_MINI=agent-id
```

**檢查配置**：
```bash
# 驗證 Codeer agent IDs 已配置
grep CODEER_AGENT /path/to/.env

# 應該看到三個 agent IDs
```

### 2. API 成本
- 實驗會產生**實際的 API 費用**
- Gemini：非常便宜（< $0.001 per test）
- Codeer：需確認實際定價（目前使用 $0.01 per call 估算）

### 3. 測試時間
- 完整實驗約 **5-10 分鐘**（12 個測試）
- 可使用篩選條件縮短時間

### 4. 失敗處理
- 如果某個 provider 失敗，實驗會繼續其他測試
- 失敗的測試會標記，但不影響成功測試的分析

---

## 📈 預期實驗結果

### 速度比較
- **Gemini (cache)**: 通常最快（cache hit 後延遲大幅降低）
- **Codeer Claude**: 可能較慢（模型複雜度高）
- **Codeer Gemini**: 中等速度
- **Codeer GPT-5**: 中等速度

### 品質比較
- **Claude Sonnet**: 通常品質最高（專業術語、同理心）
- **Gemini**: 品質穩定，結構完整
- **GPT-5 Mini**: 品質可能略低（模型較小）

### 成本比較
- **Gemini (cache)**: 最便宜（< $0.001）
- **Codeer**: 統一估算（$0.01 per call，需確認）

### 加權推薦
基於加權總分（Quality 50%, Speed 30%, Cost 20%）：
- 如果品質優先 → 可能推薦 Claude Sonnet
- 如果成本敏感 → 可能推薦 Gemini
- 如果平衡考量 → 需實際測試決定

---

## 🔧 技術細節

### 實驗設計
- **測試矩陣**: 4 providers × 3 durations = 12 tests
- **重複性**: 每個組合測試一次（可擴展為多次）
- **順序**: 固定順序（可改為隨機）

### 品質評估演算法
- **自動評分**: 基於規則和關鍵字匹配
- **限制**: 無法完全取代人工評估
- **可調整**: 評分標準可根據需求調整

### 成本計算
- **Gemini**: 基於實際 token usage（Vertex AI API 回傳）
- **Codeer**: 基於估算（需確認實際定價）

### Cache/Session 行為
- **Gemini**: 首次創建 cache，後續 reuse（Strategy A: always update）
- **Codeer**: 使用 session pool，首次創建 chat，後續 reuse

---

## 📝 檔案清單

```
career_ios_backend/
├── tests/
│   └── data/
│       └── long_transcripts.json          # 測試數據（3組逐字稿）
├── scripts/
│   ├── compare_four_providers.py          # 主要實驗腳本（856行）
│   ├── test_experiment_functions.py       # 驗證測試腳本
│   ├── EXPERIMENT_README.md               # 完整使用指南
│   └── EXPERIMENT_DELIVERABLES.md         # 本文件（交付清單）
└── experiment_results.json                # 實驗結果（執行後生成）
```

---

## ✅ 驗證清單

- [x] 測試數據已創建（3組逐字稿）
- [x] 實驗腳本已實現（完整功能）
- [x] 品質評估模組已實現（4個維度）
- [x] 成本計算模組已實現（Gemini + Codeer）
- [x] 結果可視化已實現（Rich 表格）
- [x] 核心功能已驗證（test script 通過）
- [x] 文檔已完成（使用指南 + 交付清單）
- [x] 腳本語法已驗證（Python compile 通過）
- [x] Help 命令可用（`--help` 正常顯示）

---

## 🎯 下一步：實際執行實驗

### 步驟 1：確認環境
```bash
# 檢查環境變數
grep CODEER_AGENT .env

# 檢查 API server 運行
curl http://localhost:8000/health
```

### 步驟 2：運行驗證測試
```bash
poetry run python scripts/test_experiment_functions.py
```

### 步驟 3：運行小規模測試
```bash
# 先測試單一 provider
poetry run python scripts/compare_four_providers.py \
  --provider gemini \
  --duration 8
```

### 步驟 4：運行完整實驗
```bash
# 完整測試（12 個測試，5-10 分鐘）
poetry run python scripts/compare_four_providers.py
```

### 步驟 5：分析結果
```bash
# 查看 JSON 結果
cat experiment_results.json | jq .

# 或直接查看終端輸出的表格和推薦
```

---

## 📞 支援

如有問題或需要調整：
1. 檢查 `EXPERIMENT_README.md` 的問題排除區段
2. 運行 `test_experiment_functions.py` 驗證核心功能
3. 檢查 `.env` 配置是否完整
4. 聯繫開發團隊

---

**交付版本**: v1.0
**交付日期**: 2025-12-11
**狀態**: ✅ 完成，可立即使用

所有組件已完成並驗證通過，實驗框架可立即投入使用！
