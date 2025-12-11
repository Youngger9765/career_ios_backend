# LLM Provider Comparison Experiment

完整的實驗框架，用於比較四種 LLM 方案在親子諮詢分析場景下的表現。

## 實驗目標

比較四個 LLM 方案的**品質**、**速度**、**成本**：

1. **Gemini with Explicit Context Caching** - 現有方案（基準線）
2. **Codeer Claude Sonnet 4.5** - 新方案
3. **Codeer Gemini 2.5 Flash** - 新方案
4. **Codeer GPT-5 Mini** - 新方案

## 測試數據

三組真實的親子諮詢逐字稿（位於 `tests/data/long_transcripts.json`）：

- **8分鐘對話** (~1400字) - 主題：孩子不願意做功課
- **9分鐘對話** (~1600字) - 主題：青少年叛逆期問題
- **10分鐘對話** (~1800字) - 主題：手足衝突

每組包含：
- 完整的 `speakers` 列表（counselor/client 交替）
- 完整的 `transcript` 文字
- 時間範圍標註（time_range）

## 評估維度

### 1. 品質評估 (Quality Score: 0-100)

自動化品質評分，包含四個維度：

#### a. 結構完整性 (Structure: 20%)
- JSON 格式正確
- 包含 summary, alerts, suggestions 欄位
- 每個欄位都有內容

#### b. 相關性 (Relevance: 30%)
- 建議是否針對逐字稿內容
- 是否提到關鍵問題（功課、叛逆、衝突等）
- 是否包含親子相關術語

#### c. 專業性 (Professionalism: 30%)
- 使用正確的諮詢術語（同理、理解、引導等）
- 提供具體可行的建議
- 避免批判性語言（不當、錯誤、暴力等）
- 符合親子教養原則

#### d. 完整性 (Completeness: 20%)
- 提醒事項數量（理想：3-5點）
- 建議回應數量（理想：2-3點）
- 建議長度（理想：< 50字）
- Summary 長度適中

**加權計算**：
```
總分 = (Structure * 0.2) + (Relevance * 0.3) + (Professionalism * 0.3) + (Completeness * 0.2)
```

### 2. 速度評估 (Speed)

測量 API 回應延遲（毫秒）：
- Gemini：包含 cache 創建/查詢時間
- Codeer：包含 session pool 管理時間
- 完整的端到端延遲（從請求到收到完整回應）

### 3. 成本評估 (Cost)

#### Gemini 成本計算
基於 Gemini 2.0 Flash Experimental 定價（2024-12）：
- Input tokens: $0.075 / 1M tokens
- Cached input: $0.01875 / 1M tokens (75% discount)
- Output tokens: $0.30 / 1M tokens

#### Codeer 成本計算
**注意**：Codeer 定價尚未公開，目前使用估算值：
- 假設：$0.01 per API call
- 實際成本需向 Codeer 確認

## 使用方式

### 前置條件

1. **API Server 運行中**：
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```

2. **環境變數配置** (`.env` 文件)：
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

3. **測試數據已創建**：
   - `tests/data/long_transcripts.json` 存在
   - 包含 8/9/10 分鐘三組逐字稿

### 運行實驗

#### 1. 完整實驗（所有 provider，所有時長）
```bash
poetry run python scripts/compare_four_providers.py
```

**預期時間**：5-10 分鐘（12 個測試）

**輸出**：
- 實時進度顯示
- 三個比較表格（速度、品質、成本）
- 加權總分和推薦建議
- 結果保存到 `experiment_results.json`

#### 2. 測試特定 Provider
```bash
# 只測試 Gemini
poetry run python scripts/compare_four_providers.py --provider gemini

# 只測試 Codeer 系列
poetry run python scripts/compare_four_providers.py --provider codeer

# 只測試 Claude Sonnet
poetry run python scripts/compare_four_providers.py --provider claude-sonnet

# 只測試 Gemini Flash
poetry run python scripts/compare_four_providers.py --provider gemini-flash

# 只測試 GPT-5 Mini
poetry run python scripts/compare_four_providers.py --provider gpt5-mini
```

#### 3. 測試特定時長
```bash
# 只測試 8 分鐘逐字稿
poetry run python scripts/compare_four_providers.py --duration 8

# 只測試 10 分鐘逐字稿
poetry run python scripts/compare_four_providers.py --duration 10
```

#### 4. 組合篩選
```bash
# 只測試 Codeer Claude，只用 10 分鐘逐字稿
poetry run python scripts/compare_four_providers.py --provider claude-sonnet --duration 10
```

#### 5. 自訂輸出路徑
```bash
poetry run python scripts/compare_four_providers.py --output my_results.json
```

### 輸出範例

#### 終端輸出
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

...

⚡ Speed Comparison (Latency in milliseconds)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Duration ┃ Gemini       ┃ Codeer       ┃ Codeer       ┃ Codeer       ┃
┃          ┃ (cache)      ┃ Claude       ┃ Gemini       ┃ GPT-5        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  8 min   │ 1234         │ 2345         │ 1567         │ 1890         │
│  9 min   │ 1456         │ 2567         │ 1678         │ 1934         │
│ 10 min   │ 1678         │ 2789         │ 1789         │ 2012         │
└──────────┴──────────────┴──────────────┴──────────────┴──────────────┘

⭐ Quality Comparison (Score 0-100)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Duration ┃ Gemini       ┃ Codeer       ┃ Codeer       ┃ Codeer       ┃
┃          ┃ (cache)      ┃ Claude       ┃ Gemini       ┃ GPT-5        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  8 min   │ 85.2         │ 88.5         │ 82.1         │ 86.3         │
│  9 min   │ 84.7         │ 89.2         │ 81.5         │ 85.9         │
│ 10 min   │ 86.1         │ 90.1         │ 83.4         │ 87.2         │
└──────────┴──────────────┴──────────────┴──────────────┴──────────────┘

💰 Cost Comparison (USD)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Duration ┃ Gemini       ┃ Codeer       ┃ Codeer       ┃ Codeer       ┃
┃          ┃ (cache)      ┃ Claude       ┃ Gemini       ┃ GPT-5        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  8 min   │ $0.000123    │ $0.010000    │ $0.010000    │ $0.010000    │
│  9 min   │ $0.000145    │ $0.010000    │ $0.010000    │ $0.010000    │
│ 10 min   │ $0.000167    │ $0.010000    │ $0.010000    │ $0.010000    │
└──────────┴──────────────┴──────────────┴──────────────┴──────────────┘

╭───────────────────────────────╮
│ 🏆 Winner: Codeer Claude Sonnet │
│ Weighted Score: 87.5 / 100     │
╰───────────────────────────────╯
```

#### JSON 結果文件
保存到 `experiment_results.json`：
```json
{
  "timestamp": "2025-12-11T10:30:00",
  "test_config": {
    "durations": [8, 9, 10],
    "providers": ["gemini (with cache)", "codeer-claude-sonnet", ...]
  },
  "results": [
    {
      "provider": "gemini",
      "model": "gemini-2.0-flash-exp",
      "duration_minutes": 8,
      "topic": "孩子不願意做功課",
      "analysis": {
        "summary": "...",
        "alerts": [...],
        "suggestions": [...]
      },
      "latency_ms": 1234,
      "cache_hit": true,
      "usage_metadata": {
        "prompt_token_count": 500,
        "cached_content_token_count": 1200,
        "candidates_token_count": 150
      },
      "cost_data": {
        "total_cost": 0.000123,
        "breakdown": {...}
      },
      "quality_score": {
        "total_score": 85.2,
        "breakdown": {
          "structure": 95.0,
          "relevance": 82.3,
          "professionalism": 88.5,
          "completeness": 79.1
        }
      }
    },
    ...
  ]
}
```

## 實驗腳本架構

### 核心模組

1. **Quality Evaluation** (`evaluate_*` functions)
   - `evaluate_structure()` - 結構完整性評分
   - `evaluate_relevance()` - 相關性評分
   - `evaluate_professionalism()` - 專業性評分
   - `evaluate_completeness()` - 完整性評分
   - `evaluate_quality()` - 綜合評分

2. **Cost Calculation**
   - `calculate_gemini_cost()` - Gemini 成本計算（基於 token usage）
   - `calculate_codeer_cost()` - Codeer 成本估算（基於 API calls）

3. **Test Execution**
   - `test_gemini_with_cache()` - 測試 Gemini + cache
   - `test_codeer_model()` - 測試 Codeer 模型（支援 session pool）
   - `run_single_test()` - 單一測試執行器

4. **Experiment Runner**
   - `run_experiment()` - 主要實驗流程
   - 支援篩選條件（provider, duration）
   - 實時進度顯示

5. **Results Analysis**
   - `analyze_results()` - 結果分析和可視化
   - 生成三個比較表格（速度、品質、成本）
   - 計算加權總分
   - 推薦最佳方案

6. **Results Persistence**
   - `save_results()` - 保存 JSON 結果

### 加權評分邏輯

**Overall Winner 計算**：
```python
Quality Score: 50%  # 品質最重要
Speed Score: 30%    # 速度次之
Cost Score: 20%     # 成本最後

Weighted Total = (Quality * 0.5) + (Speed * 0.3) + (Cost * 0.2)
```

**標準化**：
- Speed Score: 延遲越短越好 → `(1 - latency/max_latency) * 100`
- Cost Score: 成本越低越好 → `(1 - cost/max_cost) * 100`
- Quality Score: 直接使用 0-100 分數

## 重要注意事項

### 1. API 成本
- 實驗會產生實際的 API 費用
- Gemini：非常便宜（< $0.001 per test）
- Codeer：需確認實際定價

### 2. 測試時間
- 完整實驗約 5-10 分鐘（12 個測試）
- 可使用 `--provider` 和 `--duration` 篩選來縮短

### 3. Cache 行為
- **Gemini**：首次 API call 創建 cache，後續 reuse
- **Codeer**：使用 session pool，首次創建 chat，後續 reuse

### 4. 失敗處理
- 如果某個 provider 失敗，實驗會繼續其他測試
- 失敗的測試會在結果中標記，但不影響成功測試的分析

### 5. 品質評分限制
- 自動評分是**估算**，可能不完全準確
- 建議搭配人工審閱實際回應內容
- 評分標準可根據需求調整（修改 `evaluate_*` 函數）

## 實驗結果分析建議

### 解讀速度比較
- **Gemini (cache)**：通常最快（cache hit 後延遲大幅降低）
- **Codeer**：速度取決於底層模型和 session pool 效率

### 解讀品質比較
- **高分 (85+)**：專業、相關、完整的建議
- **中分 (70-85)**：可用但有改進空間
- **低分 (< 70)**：可能不符合要求，需檢查

### 解讀成本比較
- **Gemini**：成本非常低（< $0.001），cache 進一步降低 75%
- **Codeer**：實際成本需確認（目前使用估算）

### 決策建議
1. **品質優先**：選擇 quality score 最高的
2. **成本敏感**：Gemini 通常最便宜
3. **平衡考量**：使用加權總分（Quality 50%, Speed 30%, Cost 20%）

## 後續改進方向

### 1. 品質評估
- [ ] 加入人工評分（Ground Truth）
- [ ] 使用 LLM 作為評審（LLM-as-Judge）
- [ ] 擴展評分維度（同理心、具體性、可行性等）

### 2. 測試數據
- [ ] 增加更多測試案例（不同主題、時長）
- [ ] 加入邊緣案例（極短、極長、特殊情境）
- [ ] 使用真實的諮詢記錄（去識別化）

### 3. 成本計算
- [ ] 確認 Codeer 實際定價
- [ ] 細分 Codeer 各模型成本（Claude, Gemini, GPT）
- [ ] 加入長期成本預估（月、年）

### 4. 實驗設計
- [ ] A/B 測試（隨機順序）
- [ ] 重複測試（測試穩定性）
- [ ] 不同 cache 策略比較（Strategy A vs B）

### 5. 結果呈現
- [ ] 生成 Markdown 報告
- [ ] 圖表可視化（延遲分佈、品質趨勢）
- [ ] 統計顯著性檢驗

## 相關文件

- **測試數據**：`tests/data/long_transcripts.json`
- **實驗腳本**：`scripts/compare_four_providers.py`
- **Codeer Client**：`app/services/codeer_client.py`
- **Cache Manager**：`app/services/cache_manager.py`
- **Gemini Service**：`app/services/gemini_service.py`
- **Realtime API**：`app/api/realtime.py`

## 問題排除

### Q: 實驗運行失敗，提示 "Agent configuration error"
A: 檢查 `.env` 文件中的 Codeer agent IDs 是否配置正確：
```bash
CODEER_AGENT_CLAUDE_SONNET=...
CODEER_AGENT_GEMINI_FLASH=...
CODEER_AGENT_GPT5_MINI=...
```

### Q: Gemini 測試失敗，提示 "Content too short for caching"
A: 這是正常情況（< 1024 tokens），會自動 fallback 到非 cache 模式。

### Q: 所有 Codeer 測試都失敗
A:
1. 檢查 `CODEER_API_KEY` 是否有效
2. 檢查 API server 是否運行（port 8000）
3. 檢查網路連線

### Q: 品質評分看起來不合理
A:
1. 檢查實際的 analysis 回應內容（在 JSON 結果中）
2. 評分標準可能需要調整（修改 `evaluate_*` 函數）
3. 自動評分有限制，建議搭配人工審閱

### Q: 如何只測試一個特定案例？
A:
```bash
# 組合 --provider 和 --duration 篩選
poetry run python scripts/compare_four_providers.py \
  --provider claude-sonnet \
  --duration 10
```

## 聯絡與貢獻

如有問題或建議，請聯繫開發團隊或提交 Issue。

---

**實驗版本**: v1.0
**最後更新**: 2025-12-11
**作者**: Claude Code + Human
