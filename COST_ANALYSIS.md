# Island Parents 成本分析

> 基準：60 分鐘親子對話練習
>
> **幣別：美金 (USD)**
>
> **最後更新**: 2026-02-07 v3.0

---

## 1. 服務架構（以代碼為準）

| 服務 | 模型 | 呼叫頻率 | 用途 | 代碼位置 |
|------|------|---------|------|---------|
| **ElevenLabs STT** | Scribe v2 Realtime | 持續串流 | 語音轉文字 | WebSocket 連線 |
| **Emotion** | `gemini-flash-lite-latest` | 每 3 秒 = 1200 次/hr | 即時情緒紅綠燈 | `app/services/analysis/emotion_service.py` |
| **Report** | `gemini-3-flash-preview` | 每 session 1 次 | 結束後深度報告 | `app/services/analysis/parents_report_service.py` |
| **RAG Embedding** | OpenAI `text-embedding-3-small` | 每 session 1 次 | 教養理論檢索 | `app/services/rag/rag_retriever.py` |
| **Cloud Run** | FastAPI | 持續 | API Server | GCP |
| **Supabase** | PostgreSQL + pgvector | 持續 | 資料庫 | Supabase Pro |

---

## 2. 60 分鐘成本總覽

| 服務 | 60 分鐘成本 (USD) | 佔比 | 計算方式 |
|------|------------------|------|---------|
| **ElevenLabs STT** | **$0.400** | 68.1% | $0.40/hr 固定 |
| **Emotion (Gemini)** | **$0.100** | 17.0% | 1200 calls × token 成本 |
| **Report (Gemini)** | **$0.035** | 6.0% | 55K input + 2K output tokens |
| **Cloud Run** | **$0.050** | 8.5% | vCPU + Memory + Network |
| **RAG Embedding** | **$0.001** | 0.2% | OpenAI embedding |
| **Supabase DB** | **$0.001** | 0.2% | R/W 操作 |
| **總計** | **~$0.587** | 100% | |

---

## 3. 各服務詳細分析

### 3.1 ElevenLabs Speech-to-Text — $0.40/hr

| 指標 | 數值 |
|------|------|
| 模型 | Scribe v2 Realtime |
| 計價方式 | **$0.40/hr**（按音頻時長） |
| Enterprise 方案 | $0.22/hr（需聯繫銷售） |
| 延遲 | 150ms |
| 準確率 | 96.7%（英文），中文表現優秀 |

**來源**: [ElevenLabs API Pricing](https://elevenlabs.io/pricing/api)

### 3.2 Emotion 分析（Gemini Flash Lite）— $0.10/hr

| 指標 | 數值 | 說明 |
|------|------|------|
| 模型 | `gemini-flash-lite-latest` | 最低延遲 |
| 平台 | Vertex AI | `from vertexai.generative_models` |
| 定價 | **$0.10/1M input, $0.40/1M output** | |
| 呼叫頻率 | 每 3 秒 = **1200 次/hr** | |
| 每次 input | ~750 tokens | system prompt 350 + context 350 + target 50 |
| 每次 output | ~20 tokens | `"3\|試著同理孩子的挫折感"` |
| Input/hr | 900K tokens → $0.09 | 1200 × 750 |
| Output/hr | 24K tokens → $0.01 | 1200 × 20 |
| **小計** | **$0.10/hr** | |

**來源**: [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)

### 3.3 Report 報告（Gemini 3 Flash）— $0.035/session

#### 逐字稿長度估算（60 分鐘）

| 指標 | 數值 | 說明 |
|------|------|------|
| 中文口語語速 | 200-300 字/分鐘 | 正常對話 |
| 有效說話時間 | ~70%（42 分鐘） | 扣除沉默/思考 |
| 對話雙方 | 家長 + AI 孩子 | 雙向 |
| 原始文字量 | 42 min × 250 字 × 2 人 = **21,000 字** | |
| 加時間戳/標籤 | ×1.2 = **~25,000 字** | |
| Token 轉換 | 25,000 × 2 = **~50,000 tokens** | 中文 ≈ 1.5-2 tokens/字 |

#### Token 明細

| 組成 | Token 數 |
|------|---------|
| System prompt + 指令 | ~3,000 |
| 完整逐字稿（60 min） | ~50,000 |
| RAG 教養理論（5 篇） | ~2,000 |
| 情境描述 | ~500 |
| **Total Input** | **~55,500** |
| **Total Output** | **~2,100** |

#### 成本計算

| 指標 | 數值 |
|------|------|
| 模型 | `gemini-3-flash-preview`（Gemini 3 Flash） |
| 定價 | **$0.50/1M input, $3.00/1M output** |
| Input 成本 | 0.0555M × $0.50 = **$0.028** |
| Output 成本 | 0.0021M × $3.00 = **$0.006** |
| RAG Embedding | ~$0.001 |
| **Report 小計** | **~$0.035/session** |

**來源**: [Gemini 3 Flash Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)

### 3.4 基礎設施 — $0.052/hr

| 服務 | 成本/hr |
|------|--------|
| GCP Cloud Run (1 vCPU + 512MB) | ~$0.050 |
| Supabase DB R/W | ~$0.001 |
| 網路出站 | ~$0.001 |

---

## 4. 成本結構

```
ElevenLabs STT ████████████████████████████████ 68%  ($0.40)
Emotion (LLM)  ████████ 17%                          ($0.10)
基礎設施        ████ 9%                               ($0.052)
Report (LLM)   ███ 6%                                ($0.035)
```

**結論**：ElevenLabs STT 是最大成本驅動因素（68%）。Gemini LLM 合計佔 23%。

---

## 5. API 定價參考（2026, Vertex AI）

| 服務 | Input 定價 | Output 定價 | 來源 |
|------|-----------|------------|------|
| Gemini Flash Lite | $0.10/1M | $0.40/1M | [Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/pricing) |
| Gemini 3 Flash | $0.50/1M | $3.00/1M | 同上 |
| Gemini 2.5 Flash（備選） | $0.30/1M | $2.50/1M | [Gemini API](https://ai.google.dev/gemini-api/docs/pricing) |
| ElevenLabs Scribe v2 | $0.40/hr | - | [ElevenLabs](https://elevenlabs.io/pricing/api) |
| ElevenLabs Enterprise | $0.22/hr | - | 需聯繫銷售 |
| OpenAI Embedding | $0.02/1M | - | [OpenAI](https://openai.com/pricing) |

---

## 6. 與舊版比較

| 指標 | v2.0（舊版） | v3.0（修正版） | 差異 |
|------|-------------|--------------|------|
| Gemini 服務 | Quick + Deep + Report (3 個) | Emotion + Report (2 個) | 架構修正 |
| Emotion 模型 | Gemini 2.5 Flash | `gemini-flash-lite-latest` | 更便宜 |
| Emotion 頻率 | 60 次/hr | 1200 次/hr（每 3 秒） | ×20 |
| Report 模型定價 | $0.30/1M input | $0.50/1M input（Gemini 3） | 更貴 |
| 逐字稿 tokens | ~8,000 | ~50,000 | 修正估算 |
| Report 成本 | $0.015/session | $0.035/session | +133% |
| **每小時總成本** | **$0.72** | **$0.587** | **-18%** |

---

## 7. Billing 上限設計

> 詳見 `docs/billing/BILLING_CAP_DESIGN.md`

---

## 參考來源

- [ElevenLabs API Pricing](https://elevenlabs.io/pricing/api)
- [ElevenLabs Scribe v2 Realtime](https://elevenlabs.io/realtime-speech-to-text)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
- [Gemini Developer API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [GCP Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [OpenAI Pricing](https://openai.com/pricing)
