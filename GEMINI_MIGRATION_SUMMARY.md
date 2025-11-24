# Gemini 遷移完成摘要

**遷移日期**: 2025-11-25
**狀態**: ✅ 完成 Phase 1 + Phase 2

---

## 📋 變更摘要

### ✅ 已完成的變更

#### 1. **基礎設施準備**
- ✅ `app/core/config.py` - 添加 Gemini 配置
  - `GEMINI_PROJECT_ID`, `GEMINI_LOCATION`, `GEMINI_CHAT_MODEL`
  - `DEFAULT_LLM_PROVIDER` = `"gemini"` (預設)

- ✅ `app/services/gemini_service.py` - 擴展功能
  - 支援 `chat_completion_with_messages()` (OpenAI 格式)
  - 支援 `response_format={"type": "json_object"}` (JSON mode)
  - 支援 `model_name` 參數（可切換模型）

#### 2. **服務遷移（雙 Provider 支援）**
所有服務都支援 `provider` 參數：`"openai"` 或 `"gemini"`

- ✅ `app/services/session_summary_service.py`
  - 新增 `provider` 參數
  - 預設使用 Gemini (從 `settings.DEFAULT_LLM_PROVIDER`)
  - Gemini 失敗自動 fallback 到 OpenAI

- ✅ `app/services/report_service.py`
  - 新增 `provider` 參數
  - 所有方法支援雙 provider：
    - `_parse_transcript_info()` - 解析逐字稿
    - `_generate_structured_report()` - 生成報告
    - `_extract_key_dialogues()` - 提取對話

- ✅ `app/utils/report_grader.py`
  - 新增 `provider` 參數
  - 預設使用 Gemini (省 94% 成本)
  - OpenAI 保留為備用（使用 gpt-4o）

- ✅ `app/api/rag_report.py`
  - 預設 `rag_system="gemini"` (原為 `"openai"`)

#### 3. **環境變數更新**
- ✅ `.env.example` - 添加 Gemini 配置說明

---

## 📂 檔案變更清單

```
app/core/config.py                          # 新增 Gemini 配置
app/services/gemini_service.py              # 擴展功能
app/services/session_summary_service.py     # 支援雙 provider
app/services/report_service.py              # 支援雙 provider
app/utils/report_grader.py                  # 支援雙 provider
app/api/rag_report.py                       # 預設改為 Gemini
.env.example                                # 更新環境變數說明
```

---

## 🔧 環境變數設置

### 新增的環境變數

```bash
# Gemini / Vertex AI (主要 LLM)
GEMINI_PROJECT_ID=groovy-iris-473015-h3
GEMINI_LOCATION=us-central1
GEMINI_CHAT_MODEL=gemini-2.5-flash

# LLM Provider Selection (預設使用 Gemini)
DEFAULT_LLM_PROVIDER=gemini  # "openai" or "gemini"
```

### 保留的 OpenAI 設置
```bash
# OpenAI (用於 Embeddings, Whisper STT, RAG Chat)
OPENAI_API_KEY=sk-xxx
```

---

## ✅ 保留 OpenAI 的功能（未變更）

1. **Whisper STT** (`app/services/stt_service.py`)
   - 語音轉文字
   - 無需變更

2. **Text Embeddings** (`app/services/openai_service.py`)
   - `create_embedding()`
   - `create_embeddings_batch()`
   - RAG 向量搜尋

3. **RAG Chat** (`app/services/openai_service.py`)
   - `chat_completion_with_context()`
   - 與現有 embeddings 配合使用

---

## 🎯 預設行為變更

### 變更前 (OpenAI)
```python
# 所有服務都使用 OpenAI
SessionSummaryService()  # → gpt-4o-mini
ReportGenerationService()  # → gpt-4o-mini
grade_report_with_llm()  # → gpt-4o
rag_report.py: rag_system="openai"  # → gpt-4o-mini
```

### 變更後 (Gemini 預設)
```python
# 所有服務預設使用 Gemini
SessionSummaryService()  # → gemini-2.5-flash
ReportGenerationService()  # → gemini-2.5-flash
grade_report_with_llm()  # → gemini-2.5-flash
rag_report.py: rag_system="gemini"  # → gemini-2.5-flash
```

### 如何切換回 OpenAI
```python
# 方法 1: 環境變數
DEFAULT_LLM_PROVIDER=openai

# 方法 2: 初始化時指定
SessionSummaryService(provider="openai")
ReportGenerationService(provider="openai")
grade_report_with_llm(provider="openai")

# 方法 3: API 參數
POST /api/report/generate
{
  "rag_system": "openai"
}
```

---

## 💰 成本影響

### 變更前（全 OpenAI）
- 會談摘要: `gpt-4o-mini` ($0.15/$0.60)
- 報告生成: `gpt-4o-mini` ($0.15/$0.60)
- 報告評分: `gpt-4o` ($2.50/$10.00) ⚠️ 最貴
- RAG 報告: `gpt-4o-mini` ($0.15/$0.60)

### 變更後（預設 Gemini）
- 會談摘要: `gemini-2.5-flash` ($0.15/$0.60) - 同價
- 報告生成: `gemini-2.5-flash` ($0.15/$0.60) - 同價
- 報告評分: `gemini-2.5-flash` ($0.15/$0.60) - **省 94%** 🎉
- RAG 報告: `gemini-2.5-flash` ($0.15/$0.60) - 同價

**結論**: 報告評分省 94% 成本，其他功能同價但可能性能更好

---

## 🧪 測試建議

### 1. 單元測試
```bash
# 確保現有測試通過
poetry run pytest tests/unit/ -v
```

### 2. Integration Tests
```bash
# 測試 RAG 報告生成
poetry run pytest tests/integration/test_reports_api.py -v

# 測試所有 integration tests
poetry run pytest tests/integration/ -v
```

### 3. 手動測試
```bash
# 測試 Gemini 報告生成
curl -X POST http://localhost:8000/api/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "...",
    "rag_system": "gemini"
  }'

# 測試 OpenAI 報告生成（fallback）
curl -X POST http://localhost:8000/api/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "...",
    "rag_system": "openai"
  }'
```

### 4. 品質驗證
- [ ] 抽樣 20 份會談摘要比較 Gemini vs OpenAI
- [ ] 抽樣 20 份報告比較品質
- [ ] 驗證報告評分一致性（50 份歷史報告）

---

## 🚀 部署步驟

### Staging 環境

1. **更新環境變數**
```bash
# 添加到 .env
GEMINI_PROJECT_ID=groovy-iris-473015-h3
GEMINI_LOCATION=us-central1
GEMINI_CHAT_MODEL=gemini-2.5-flash
DEFAULT_LLM_PROVIDER=gemini
```

2. **重啟服務**
```bash
# Docker
docker-compose restart

# Cloud Run (會自動重新部署)
git push origin staging
```

3. **驗證 Gemini 可用**
```bash
# 檢查 logs
tail -f logs/app.log | grep -i gemini

# 測試 API
curl http://staging-url/api/report/generate \
  -d '{"transcript": "test", "rag_system": "gemini"}'
```

### Production 環境（漸進式切換）

**Week 1: 10% 流量**
```bash
# 保持預設 OpenAI，手動測試 Gemini
DEFAULT_LLM_PROVIDER=openai
```

**Week 2: 50% 流量**
```bash
# 切換預設為 Gemini
DEFAULT_LLM_PROVIDER=gemini
```

**Week 3: 100% 流量**
```bash
# 全面使用 Gemini
DEFAULT_LLM_PROVIDER=gemini
# OpenAI 僅用於 Embeddings + Whisper
```

---

## 🔄 回滾計畫

### 緊急回滾（如果 Gemini 出現問題）

**方法 1: 環境變數**
```bash
# 改變環境變數，重啟服務
DEFAULT_LLM_PROVIDER=openai
```

**方法 2: API 層級**
```python
# app/api/rag_report.py
rag_system: str = "openai"  # 改回預設 OpenAI
```

**方法 3: 程式碼熱修復**
```python
# app/core/config.py
DEFAULT_LLM_PROVIDER: str = "openai"
```

---

## 📊 監控指標

### 需要監控的指標

1. **API 延遲**
   - Gemini vs OpenAI 回應時間
   - 目標: < 5 秒 (報告生成)

2. **錯誤率**
   - Gemini API 錯誤率
   - Fallback 到 OpenAI 的頻率

3. **成本**
   - Vertex AI (Gemini) 月費用
   - OpenAI 月費用比較

4. **品質**
   - 報告評分分佈（人工抽查）
   - 使用者回饋

### 監控工具
```bash
# GCP Billing
gcloud billing accounts list

# Application Logs
tail -f logs/app.log | grep -E "(gemini|openai|error)"

# API 健康檢查
curl http://localhost:8000/health
```

---

## 🎉 完成狀態

✅ Phase 1: 基礎設施準備
✅ Phase 2: 服務遷移
✅ 程式碼品質檢查 (ruff check)
⏸️ Phase 3: 測試與驗證 (待執行)
⏸️ Phase 4: 部署 (待執行)

---

## 📝 後續步驟

1. **測試驗證** (預計 2-3 天)
   - [ ] 執行 integration tests
   - [ ] 品質比較 (Gemini vs OpenAI)
   - [ ] 成本監控設置

2. **Staging 部署** (預計 1-2 天)
   - [ ] 部署到 Staging
   - [ ] 手動測試所有功能
   - [ ] 驗證 Gemini fallback 機制

3. **Production 漸進式切換** (預計 2-3 週)
   - [ ] Week 1: 10% 流量測試
   - [ ] Week 2: 50% 流量測試
   - [ ] Week 3: 100% 切換完成

---

## 🔗 相關文檔

- [COST_ANALYSIS.md](./COST_ANALYSIS.md) - 成本分析
- [GEMINI_MIGRATION_PLAN.md](./GEMINI_MIGRATION_PLAN.md) - 詳細遷移計畫
- [CLAUDE.md](./CLAUDE.md) - 開發策略

---

**遷移完成**！Gemini 現為預設 LLM，OpenAI 保留用於 Embeddings/Whisper/RAG。
