# Billing 上限設計 & 成本試算

> 基準：2000 用戶 x 100 TWD 月費
>
> **幣別：USD / TWD（1 USD ≈ 32 TWD）**
>
> **最後更新**: 2026-02-07

---

## 1. 實際架構（以代碼為準）

本系統每小時使用以下 API：

| 服務 | 模型 | 呼叫頻率 | 用途 |
|------|------|---------|------|
| **ElevenLabs STT** | Scribe v2 Realtime | 持續串流 | 語音轉文字 |
| **Emotion** | `gemini-flash-lite-latest` | 每 3 秒 1 次 = **1200 次/hr** | 即時情緒紅綠燈 |
| **Report** | `gemini-3-flash-preview` | 每 session 1 次 | 結束後深度分析報告 |
| **RAG Embedding** | OpenAI `text-embedding-3-small` | 每 session 1 次 | 教養理論檢索 |
| **Cloud Run** | FastAPI | 持續 | API Server |
| **Supabase** | PostgreSQL + pgvector | 持續 | 資料庫 |

> 代碼位置：`app/services/analysis/emotion_service.py`、`app/services/analysis/parents_report_service.py`

---

## 2. 每小時 API 成本（詳細推導）

### 2.1 ElevenLabs STT — $0.40/hr

按小時計費，無需推算 token。

| 指標 | 數值 |
|------|------|
| 計價方式 | $0.40/hr（標準），$0.22/hr（Enterprise） |
| 60 分鐘成本 | **$0.40** |

### 2.2 Emotion（Gemini Flash Lite）— $0.10/hr

| 指標 | 數值 | 說明 |
|------|------|------|
| 模型 | `gemini-flash-lite-latest` | Flash Lite，最低延遲 |
| 定價 | $0.10/1M input, $0.40/1M output | [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) |
| 呼叫頻率 | 每 3 秒 1 次 = **1200 次/hr** | |
| 每次 input | ~750 tokens | system prompt 350 + context 350 + target 50 |
| 每次 output | ~20 tokens | `"3\|試著同理孩子的挫折感"` |
| **Input/hr** | 1200 × 750 = **900K tokens** | 0.9M × $0.10 = **$0.09** |
| **Output/hr** | 1200 × 20 = **24K tokens** | 0.024M × $0.40 = **$0.01** |
| **Emotion 合計** | | **$0.10/hr** |

### 2.3 Report（Gemini 3 Flash）— $0.036/session

#### 逐字稿長度估算（60 分鐘 session）

| 指標 | 數值 | 說明 |
|------|------|------|
| 中文口語語速 | 200-300 字/分鐘 | 一般對話 |
| 有效說話時間 | ~70%（42 分鐘） | 扣除沉默、思考 |
| 說話人數 | 2（家長 + AI 孩子） | 雙向對話 |
| 原始文字量 | 42 min × 250 字 × 2 人 = **21,000 字** | |
| 加上時間戳/標籤 | ×1.2 = **~25,000 字** | `[00:01:23] 媽媽：...` |
| Token 轉換 | 25,000 × 2 tokens/字 = **~50,000 tokens** | 中文 ≈ 1.5-2 tokens/字 |

#### Report 輸入 Token 明細

| 組成 | Token 數 | 說明 |
|------|---------|------|
| System prompt + 分析指令 | ~3,000 | 固定模板（262 行 prompt） |
| 完整逐字稿（60 min） | ~50,000 | 見上方推算 |
| RAG 教養理論（5 篇 × 200 字） | ~2,000 | pgvector 檢索結果 |
| 情境描述 | ~500 | scenario + scenario_description |
| **Total Input** | **~55,500 tokens** | |

#### Report 輸出 Token 明細

| 欄位 | 估算字數 | Token 數 |
|------|---------|---------|
| encouragement | ≤15 字 | ~30 |
| issue | 200-400 字 | ~600 |
| analyze | 300-500 字 | ~800 |
| suggestion | 200-400 字 | ~600 |
| JSON 結構 | - | ~100 |
| **Total Output** | | **~2,100 tokens** |

#### Report 成本計算

| 指標 | 數值 | 說明 |
|------|------|------|
| 模型 | `gemini-3-flash-preview` | Gemini 3 Flash |
| Input 定價 | **$0.50/1M tokens** | [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) |
| Output 定價 | **$3.00/1M tokens** | |
| Input 成本 | 0.0555M × $0.50 = **$0.028** | |
| Output 成本 | 0.0021M × $3.00 = **$0.006** | |
| RAG Embedding | ~$0.001 | OpenAI text-embedding-3-small |
| **Report 合計** | | **~$0.035/session** |

### 2.4 基礎設施 — $0.052/hr

| 服務 | 成本/hr | 說明 |
|------|--------|------|
| GCP Cloud Run | ~$0.05 | 1 vCPU + 512MB |
| Supabase DB | ~$0.001 | R/W 操作 |
| 網路出站 | ~$0.001 | |
| **基礎設施合計** | **~$0.052** | |

### 2.5 總成本彙總

| 服務 | 模型 | 每小時成本 (USD) | 佔比 |
|------|------|-----------------|------|
| **ElevenLabs STT** | Scribe v2 Realtime | **$0.400** | 68.0% |
| **Emotion** | Gemini Flash Lite (1200 calls) | **$0.100** | 17.0% |
| **Report** | Gemini 3 Flash (1 call) | **$0.035** | 6.0% |
| **基礎設施** | Cloud Run + DB | **$0.052** | 9.0% |
| **合計** | | **~$0.587/hr** | 100% |

### 成本結構

```
ElevenLabs STT ████████████████████████████████ 68.0%  ($0.40)
Emotion (LLM)  ████████ 17.0%                          ($0.10)
基礎設施        ████ 9.0%                               ($0.052)
Report (LLM)   ███ 6.0%                                ($0.035)
```

> **結論**：ElevenLabs STT 佔總成本 68%，是最大成本驅動因素。Gemini LLM 合計佔 23%。

---

## 3. API 定價參考（2026, Vertex AI）

| 服務 | 定價 | 來源 |
|------|------|------|
| ElevenLabs Scribe v2 Realtime | $0.40/hr（標準），$0.22/hr（Enterprise） | [elevenlabs.io/pricing/api](https://elevenlabs.io/pricing/api) |
| Gemini Flash Lite（Emotion） | $0.10/1M input, $0.40/1M output | [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) |
| Gemini 3 Flash（Report） | $0.50/1M input, $3.00/1M output | [Gemini 3 Flash Pricing](https://www.glbgpt.com/hub/how-much-does-the-gemini-3-flash-cost/) |
| Gemini 2.5 Flash（備選） | $0.30/1M input, $2.50/1M output | [ai.google.dev/pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| OpenAI Embedding | $0.02/1M tokens | [openai.com/pricing](https://openai.com/pricing) |

---

## 4. 關鍵數字

| 指標 | 數值 |
|------|------|
| 每小時 API 成本 | **$0.587 ≈ $0.59** |
| 每分鐘 API 成本 | $0.0098 ≈ **0.31 TWD** |
| 100 TWD 盈虧平衡點 | 100 / 0.31 = **323 分鐘 ≈ 5.4 小時/月** |
| 目標毛利率 | **30-50%** |
| 安全上限（40% 毛利） | 100 × 0.6 / 0.31 = **194 min ≈ 3.2 小時/月** |
| 月營收（2000人） | 200,000 TWD ≈ **$6,250 USD** |

---

## 5. 使用量情境分析

### 5.1 單用戶成本

| 使用量 | 頻率 | API 成本 (USD) | TWD | 毛利率 |
|--------|------|---------------|-----|--------|
| **輕度** | 30min × 2次 = 1hr | $0.59 | 19 TWD | **81%** |
| **一般** | 30min × 4次 = 2hr | $1.17 | 38 TWD | **62%** |
| **活躍** | 60min × 4次 = 4hr | $2.35 | 75 TWD | **25%** |
| **重度** | 60min × 8次 = 8hr | $4.70 | 150 TWD | **-50%** |

> 超過 5.4 小時/月，100 TWD 方案即虧損。

### 5.2 全平台總成本（2000 用戶）

| 平均使用量 | API 總成本/月 (USD) | 固定成本 | 總支出 | 月利潤 | 毛利率 |
|------------|-------------------|---------|--------|--------|--------|
| 1hr/user | $1,174 | $80 | $1,254 | **$4,996** | **80%** |
| 2hr/user | $2,348 | $80 | $2,428 | **$3,822** | **61%** |
| 3hr/user | $3,522 | $80 | $3,602 | **$2,648** | **42%** |
| 4hr/user | $4,696 | $80 | $4,776 | **$1,474** | **24%** |
| 5hr/user | $5,870 | $80 | $5,950 | **$300** | **5%** |

固定成本：Supabase Pro $25 + Cloud Run base ~$50 + 其他 ~$5 ≈ **$80/月**

---

## 6. Billing 上限方案

### 方案 A：時間上限制

以目標 40% 毛利率為設計基準：

| 方案 | 月費 (TWD) | 時間上限 | API 成本 (TWD) | 毛利率 |
|------|-----------|---------|---------------|--------|
| **基本** | 100 | 3 小時/月 | 57 | **43%** |
| **標準** | 300 | 10 小時/月 | 189 | **37%** |
| **專業** | 500 | 20 小時/月 | 377 | **25%** |

**優點**：簡單直覺，用戶容易理解
**缺點**：需要新增時間追蹤邏輯

### 方案 B：Session 次數制

| 方案 | 月費 (TWD) | 次數上限 | 每次上限 | 額外購買 |
|------|-----------|---------|---------|---------|
| **基本** | 100 | 4 次/月 | 45 min | 30 TWD/次 |
| **標準** | 300 | 15 次/月 | 45 min | 25 TWD/次 |
| **專業** | 500 | 30 次/月 | 60 min | 20 TWD/次 |

**優點**：按次計費符合諮商場景
**缺點**：每次時間限制可能影響用戶體驗

### 方案 C：Credit 制（推薦）

兼容現有 Incremental Billing 系統（1 credit = 1 分鐘）：

| 方案 | 月費 (TWD) | Credits | 等於 | 超額價 |
|------|-----------|---------|------|--------|
| **基本** | 100 | 180 credits | 3 hr | 0.8 TWD/min |
| **標準** | 300 | 600 credits | 10 hr | 0.6 TWD/min |
| **專業** | 500 | 1200 credits | 20 hr | 0.5 TWD/min |

**優點**：
- 已有基礎設施（Incremental Billing 已實作完成）
- 靈活度高，用戶自己控制使用節奏
- 超額可購買，不會硬性中斷服務

**缺點**：
- 需向用戶解釋 Credit 概念

---

## 7. 推薦方案：Credit 制（方案 C）

### 7.1 為什麼選方案 C？

1. **已有基礎設施** — Incremental Billing 系統已實作（`app/services/billing/`）
2. **1 credit = 1 分鐘** — 概念簡單，無需額外轉換
3. **超額可購** — 不會硬性中斷，軟性提醒
4. **100 TWD → 180 credits（3 hr）** — 目標 43% 毛利
5. **可與現有 `available_credits` 欄位直接對接**

### 7.2 100 TWD 方案損益分析

```
月費收入:            100 TWD ($3.13 USD)
API 成本 (3hr):      57 TWD ($1.77 USD)
  ├─ ElevenLabs:     38 TWD ($1.20)   ← 佔 67%
  ├─ Emotion LLM:    10 TWD ($0.30)
  ├─ Report LLM:      3 TWD ($0.11)
  └─ 基礎設施:        5 TWD ($0.16)
─────────────────────────────────────────
毛利:                 43 TWD ($1.36 USD)
毛利率:               43%
```

---

## 8. 各服務 Billing 上限（結論）

### 8.1 ElevenLabs 月度上限

| 場景 | 用量 | 月費用 | 說明 |
|------|------|--------|------|
| 保守（avg 2hr/user） | 4,000 hr | $1,600 | |
| 正常（avg 3hr/user） | 6,000 hr | $2,400 | |
| **建議上限** | **5,000 hr** | **$2,000** | **留 25% buffer** |
| 絕對硬上限 | 6,250 hr | $2,500 | 超過此值必虧 |

> **ElevenLabs 設定：月度 $2,000 USD 上限**（超過發 alert，不自動斷）

### 8.2 Gemini (Vertex AI) 月度上限

| 服務 | 用量估算（avg 2hr/user） | 月費用 |
|------|------------------------|--------|
| Emotion (Flash Lite) | 2000人 × 2hr × 1200calls × 770tokens | ~$400 |
| Report (3 Flash) | 2000人 × 2次 × 57.6K tokens | ~$140 |
| **Gemini 合計** | | **~$540** |

| 設定 | 金額 |
|------|------|
| **Gemini 建議上限** | **$1,000 USD**（留 85% buffer） |
| 絕對硬上限 | $1,500 |

> **Gemini 設定：月度 $1,000 USD 上限**（整數好管理，超過發 alert，不自動斷）

### 8.3 完整 Billing 上限一覽

| 服務 | 預估費用 | 建議上限 | 硬上限 |
|------|---------|---------|--------|
| **ElevenLabs STT** | $1,600 | **$2,000** | $2,500 |
| **Gemini (Vertex AI)** | $540 | **$1,000** | $1,500 |
| Cloud Run | $100 | $200 | $300 |
| Supabase | $25 | $25 | $25（固定） |
| OpenAI Embedding | $2 | $10 | $20 |
| **總計** | **$2,267** | **$3,235** | **$4,345** |
| | | | |
| 月營收 | | $6,250 | |
| **毛利** | **$3,983** | **$3,015** | **$1,905** |
| **毛利率** | **64%** | **48%** | **30%** |

### 8.4 單用戶上限

| 規則 | 目前 Code 設定 | 建議值 | 說明 |
|------|---------------|--------|------|
| 月度使用時長 | **6 小時 (360 min)** | 3 小時 (180 min) | 見下方 ⚠️ 說明 |
| 單日使用上限 | 無限制 | 3 小時 | 異常偵測，超過發 alert |
| 單次 session 上限 | 無限制 | 60 分鐘 | 防止忘關 |
| 重置週期 | **每 30 天**（從註冊日起算） | 每月 1 日 | 目前為 Lazy Reset |

> **代碼位置**：`app/models/counselor.py:80-84`（`monthly_usage_limit_minutes = 360`）
> **重置邏輯**：`app/services/billing/usage_tracker.py`（`PERIOD_DAYS = 30`，Lazy Reset — 用戶下次使用時才觸發重置）

### ⚠️ 8.5 重要：目前 Code 設定 vs 毛利率的落差

**目前後端程式設定每人每月上限為 6 小時（360 分鐘），但 6 小時會導致虧損。**

| 情境 | 每人用量 | 單用戶 API 成本 | 100 TWD 毛利率 | 2000 人平台毛利率 |
|------|---------|---------------|---------------|-----------------|
| 輕度使用（多數用戶） | 1 hr | $0.59 = 19 TWD | **81%** | **80%** |
| 一般使用 | 2 hr | $1.17 = 38 TWD | **62%** | **61%** |
| 活躍使用 | 4 hr | $2.35 = 75 TWD | **25%** | **24%** |
| **目前 Code 上限** | **6 hr** | **$3.52 = 113 TWD** | **-13%（虧損）** | 視平均而定 |

**關鍵結論**：
1. **48% 毛利率是基於「平均每人用 2hr/月」的平台級估算**，不是每人都用 6hr
2. **如果所有用戶都用滿 6 小時，100 TWD 方案會虧損 13%**
3. 實際上多數用戶不會用滿上限（業界平均使用率約 30-50%），所以平台級仍可獲利
4. 但需要密切監控平均使用量，如果平均超過 3hr 就要考慮調整

**風險控管建議**：
- 監控每月「平均每人使用時數」，如果 > 3hr → 發出預警
- 若平均使用量持續 > 4hr → 考慮將上限從 6hr 降至 4hr，或月費調漲至 150+ TWD
- 若要維持 6hr 上限且保持 30% 毛利 → 月費需漲至 **160 TWD**
- 若要維持 6hr 上限且保本（0% 毛利）→ 月費至少 **113 TWD**

### 8.7 100 TWD 方案時長 vs 毛利率

| 目標毛利率 | 可給時長 | 說明 |
|-----------|---------|------|
| 50% | 2.7 hr | 高利潤 |
| **40%** | **3.2 hr** | **推薦** |
| 30% | 3.8 hr | 可接受 |
| 20% | 4.3 hr | 薄利 |
| 0% | 5.4 hr | 保本 |
| **-13%** | **6.0 hr** | **⚠️ 虧損（目前 Code 設定）** |

> **100 TWD 月費最多給 5.4 小時（保本），推薦 3-4 小時（30-40% 毛利）。**
> **6 小時會虧 13%，若要給 6 小時，月費需漲到 160-190 TWD。**

### 8.8 GCP Billing Budget 設定（✅ 已完成）

**設定日期**: 2026-02-07
**Budget ID**: `6c8955d8-f430-4d41-a6a0-7bb1a3f71599`
**適用範圍**: GCP Project `groovy-iris-473015-h3`（包含 Vertex AI + Cloud Run + 所有 GCP 服務）

| 層級 | 月度金額 (USD) | 觸發條件 | 動作 |
|------|--------------|---------|------|
| **提醒** | **$750** | 達 50% ($1,500 × 50%) | Email 通知到 `CC_BDS@careercreator.tw` + `dev02@careercreator.tw` |
| **警告** | **$1,125** | 達 75% ($1,500 × 75%) | Email 通知（需人工審查用量） |
| **危險** | **$1,500** | 達 100%（建議上限） | Email 通知（緊急審查，考慮限流） |

**涵蓋服務**：
- Vertex AI (Gemini Flash Lite + Gemini 3 Flash): 預估 $540/月，建議上限 $1,000
- Cloud Run (FastAPI): 預估 $100/月，建議上限 $200
- 其他 GCP 服務（網路、儲存等）: 預估 $20/月，建議上限 $50
- **合計**: 預估 $660/月，建議上限 $1,250，設定 $1,500（留 20% buffer）

**不涵蓋服務**（需另外監控）：
- ❌ ElevenLabs STT（獨立平台，見 8.11）
- ❌ OpenAI Embedding（獨立平台，用量極低 ~$2/月）
- ❌ Supabase（獨立平台，固定 $25/月）

**為何只能整個 GCP Project 設定？**
- GCP Billing Budget API 不支援針對單一服務（如 Vertex AI）設定上限
- 只能針對整個 Project 或 Billing Account 設定
- Vertex AI 本身的 Quota 系統只能限制 QPM（每分鐘請求數），無法限制月度花費

**查詢指令**：
```bash
gcloud beta billing budgets describe 6c8955d8-f430-4d41-a6a0-7bb1a3f71599 \
  --billing-account=01A2A2-486C62-38898F
```

### 8.9 ElevenLabs Billing Cap 設定（⚠️ 需手動完成）

**平台**: ElevenLabs Dashboard
**設定位置**: https://elevenlabs.io/app/settings/billing

**建議上限**: **$2,000 USD/月**

| 指標 | 金額 |
|------|------|
| 預估月費（2000 人 × avg 2hr） | $1,600 |
| 建議上限（留 25% buffer） | **$2,000** |
| 硬上限（極端情況） | $2,500 |

**設定方式**：
1. 登入 ElevenLabs Dashboard
2. 進入 Settings → Billing
3. 設定 Monthly Spending Limit: **$2,000**
4. 啟用超額通知到 `CC_BDS@careercreator.tw` 和 `dev02@careercreator.tw`

**為何需手動設定？**
- ElevenLabs 無提供 API 來設定 billing cap
- 必須透過網頁 Dashboard 手動操作

**優化方案（長期）**：
- 若能談成 Enterprise 方案（$0.22/hr），可降至 $1,200/月（節省 40%）

### 8.10 異常偵測

| 規則 | 閾值 | 動作 |
|------|------|------|
| 單用戶日使用量 | > 3 小時 | 觸發審查 |
| 單用戶月使用量 | > 10 小時 | 自動限流通知 |
| 單小時 Emotion 呼叫 | > 1500 次 | Rate limit |
| ElevenLabs 日費用 | > $100 | Email 警報 |

### 8.11 使用額度重置機制

每位用戶每月有固定使用額度（目前設定 6 小時）。額度重置由後端自動處理：

- **零前端負擔**：前端不需要做任何計算或倒數計時，不會佔用手機資源或造成卡頓
- **零運營成本**：不需要排程任務（cron job）或人工介入，完全自動化
- **即時精確**：每次用戶啟動對話時，後端會即時檢查：
  1. 是否已到新週期（≥ 30 天）→ 自動重置額度
  2. 本週期是否還有剩餘額度 → 允許或拒絕
- **不會有漏洞**：因為每次對話前都會檢查，不存在「額度已用完但系統沒擋」的情況

> 技術細節：採用 Lazy Reset 模式，在用戶發起 session 請求時即時計算，無需後台排程。
> 額度不足時回傳 HTTP 429（`MONTHLY_USAGE_LIMIT_EXCEEDED`），前端可據此顯示提示。
> 前端若需查詢剩餘額度，可透過 Usage Stats API 取得。

---

## 9. 未來優化路徑

### 短期（降低 API 成本）

| 優化項目 | 預估節省 | 影響 |
|----------|----------|------|
| ElevenLabs Enterprise ($0.22/hr) | 45% STT 成本 | 需談合約 |
| Report 改用 Gemini 2.5 Flash | 40% Report 成本 | 需驗證品質 |
| Gemini Context Caching | 30-50% LLM 成本 | 無負面影響 |

**優化後成本預估**：

```
ElevenLabs Enterprise:  $0.22/hr  (原 $0.40, -45%)
Emotion (Flash Lite):   $0.10/hr  (不變)
Report (2.5 Flash):     $0.025/hr (原 $0.035, -29%)
基礎設施:               $0.052/hr (不變)
─────────────────────────────────────
優化後:                  ~$0.40/hr (原 $0.59, 節省 32%)
```

優化後 100 TWD 方案 3hr 上限：
- API 成本：$1.20 = 38 TWD
- 毛利率提升至 **62%**

### 中期（提升 ARPU）

| 策略 | 說明 |
|------|------|
| 高級功能加購 | 深度報告、歷史趨勢分析 |
| 團體方案 | 學校/機構批量折扣 |
| 年繳優惠 | 年繳 9 折（提升 LTV） |

### 長期（架構調整）

| 策略 | 說明 |
|------|------|
| 自訓練 STT 模型 | 大幅降低 STT 成本 |
| 邊緣運算推論 | 降低延遲 + 成本 |
| 多供應商備援 | 防止單一供應商風險 |

---

## 10. 決策摘要

| 項目 | 決定 |
|------|------|
| **每小時 API 成本** | **$0.59**（ElevenLabs 68% + Gemini 23% + 基礎設施 9%） |
| **ElevenLabs 月度上限** | **$2,000 USD**（5,000 hr） |
| **Gemini 月度上限** | **$1,000 USD** |
| **GCP 總月度硬上限** | **$5,000 USD** |
| **定價方案** | Credit 制（1 credit = 1 分鐘） |
| **目前 Code 單用戶上限** | **6 小時/月 (360 min)**，每 30 天 reset |
| **建議單用戶上限** | 3 小時/月 (180 min)，毛利 43% |
| **單次 session 上限** | 建議 60 分鐘（防止忘關） |
| **超額處理** | 軟性提醒 + 可購買額外 credits |
| **目標毛利率** | 40-50%（基於平均用量 2hr 估算） |
| **近期優化重點** | ElevenLabs Enterprise 合約（可降至 $0.22/hr） |

> **一句話總結：ElevenLabs 設 $2,000/月，Gemini 設 $1,000/月。目前 Code 設定單用戶上限 6hr/月，但 6hr 用滿會虧損 13%。平台級 48% 毛利率是基於平均每人 2hr 的估算。建議密切監控平均使用量，超過 3hr 需預警。**

---

## 參考文件

- `INCREMENTAL_BILLING_PRD.md` — Billing 系統技術設計
- `INCREMENTAL_BILLING_SUMMARY.md` — Billing 系統摘要
- `SESSION_USAGE_CREDIT_DESIGN.md` — Usage + Credit 設計

## 參考來源

- [ElevenLabs API Pricing](https://elevenlabs.io/pricing/api)
- [ElevenLabs Scribe v2 Realtime](https://elevenlabs.io/realtime-speech-to-text)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
- [Gemini 3 Flash Pricing](https://www.glbgpt.com/hub/how-much-does-the-gemini-3-flash-cost/)
- [Gemini Developer API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [GCP Cloud Run Pricing](https://cloud.google.com/run/pricing)
