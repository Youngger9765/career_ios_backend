# Gemini 遷移計畫

## 目標
將 Gemini 2.5 Flash 設為主力模型，保留 OpenAI 的 RAG (Embeddings)、Whisper STT

---

## Phase 1: 基礎設施準備 ✅

### 1.1 更新 Config (app/core/config.py)
```python
# Gemini / Vertex AI
GEMINI_PROJECT_ID: str = "groovy-iris-473015-h3"
GEMINI_LOCATION: str = "us-central1"
GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"  # 或 gemini-2.5-flash-lite

# LLM Provider 選擇
DEFAULT_LLM_PROVIDER: str = "gemini"  # "openai" or "gemini"
```

### 1.2 擴展 GeminiService (app/services/gemini_service.py)
需要支援：
- ✅ `chat_completion()` - 已存在
- ✅ `generate_text()` - 已存在
- ⚠️ `chat_completion_with_messages()` - 需新增（支援 OpenAI 格式的 messages）
- ⚠️ `structured_output()` - 需新增（JSON schema 輸出）

---

## Phase 2: 服務遷移 (優先順序)

### 2.1 會談摘要生成 (優先度: 高)
**檔案**: `app/services/session_summary_service.py`

**當前**:
```python
self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
self.model = "gpt-4o-mini"
```

**變更**:
```python
from app.services.gemini_service import gemini_service

# 改用 Gemini
response = await gemini_service.chat_completion(
    prompt=prompt,
    temperature=0.3,
    max_tokens=200
)
```

**風險**: 低
**測試**: 抽樣 50 個會談比較品質

---

### 2.2 報告生成服務 (優先度: 高)
**檔案**: `app/services/report_service.py`

**當前**:
```python
self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
self.chat_model = settings.OPENAI_CHAT_MODEL or "gpt-4o-mini"
```

**變更**:
```python
from app.services.gemini_service import gemini_service

# 使用 Gemini 作為預設
self.chat_model = settings.DEFAULT_LLM_PROVIDER  # "gemini"
```

**涉及方法**:
1. `_parse_transcript_info()` - 解析逐字稿 ✅
2. `_generate_structured_report()` - 生成報告 ✅
3. `_extract_key_dialogues()` - 提取對話 ✅

**風險**: 中（需確保 JSON 格式輸出正確）
**測試**: Integration tests 驗證報告結構

---

### 2.3 報告品質評分 (優先度: 中)
**檔案**: `app/utils/report_grader.py`

**當前**:
```python
# 使用 GPT-4o ($2.50/$10.00)
response = await client.chat.completions.create(
    model="gpt-4o",
    ...
)
```

**變更選項 1**: Gemini 2.5 Flash ($0.15/$0.60) - 省 94%
```python
response = await gemini_service.chat_completion(
    prompt=grading_prompt,
    temperature=0.3,
    response_format={"type": "json_object"}
)
```

**變更選項 2**: Gemini 2.5 Pro ($1.25/$5.00) - 省 50%
```python
# 需在 gemini_service 支援模型切換
gemini_service.set_model("gemini-2.5-pro")
```

**風險**: 高（評分標準準確性）
**測試**:
- 用 50 份歷史報告驗證評分一致性
- 計算 OpenAI vs Gemini 評分相關係數

---

### 2.4 RAG 報告生成 API (優先度: 中)
**檔案**: `app/api/rag_report.py`

**當前**: 已支援 `rag_system` 參數切換
```python
if request.rag_system == "gemini":
    report_content = await gemini_service.chat_completion(...)
else:
    report_content = await openai_service.chat_completion(...)
```

**變更**: 改為預設使用 Gemini
```python
class ReportRequest(BaseModel):
    rag_system: str = "gemini"  # 改為預設 "gemini"
```

**風險**: 低（已有實作）
**測試**: 現有 integration tests 應該都能通過

---

### 2.5 RAG 評估服務 (優先度: 低)
**檔案**: `app/services/evaluation_service.py`

**當前**: 使用 OpenAI 進行 RAG 答案生成和 RAGAS 評估
```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
```

**變更**: 切換至 Gemini (RAGAS 支援 Gemini)
```python
from langchain_google_vertexai import ChatVertexAI
llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0)
```

**注意**: Embeddings 仍用 OpenAI (text-embedding-3-small)

**風險**: 低（RAGAS 官方支援）
**測試**: 跑一次完整評估驗證結果

---

## Phase 3: 保留 OpenAI 的功能 ❌

### 3.1 Whisper STT (不變更)
**檔案**: `app/services/stt_service.py`
**理由**: Google Speech-to-Text 價格相近但 Whisper 準確度更高

### 3.2 Text Embeddings (不變更)
**檔案**: `app/services/openai_service.py` - `create_embedding()`
**理由**:
- 已有大量嵌入資料 (pgvector)
- Gemini 不提供獨立 embedding API
- 價格便宜 ($0.02/1M tokens)

### 3.3 RAG Chat (不變更)
**檔案**: `app/services/openai_service.py` - `chat_completion_with_context()`
**理由**: 與現有 embeddings 配合使用

---

## Phase 4: 測試與驗證

### 4.1 Integration Tests
確保所有測試通過：
```bash
poetry run pytest tests/integration/ -v
```

**需要更新的測試**:
- `tests/integration/test_reports_api.py` - 驗證報告生成
- `tests/integration/test_rag_*.py` - 驗證 RAG 功能

### 4.2 品質驗證
1. **會談摘要**: 抽樣 50 個會談比較 OpenAI vs Gemini
2. **報告生成**: A/B 測試 20 份報告比較結構和品質
3. **報告評分**: 用 50 份歷史報告驗證評分一致性

### 4.3 成本監控
使用 GCP Billing 監控 Vertex AI 費用：
```bash
gcloud billing accounts list
gcloud billing projects describe PROJECT_ID
```

---

## Phase 5: 部署與回滾計畫

### 5.1 環境變數設置
**Staging**:
```bash
DEFAULT_LLM_PROVIDER=gemini
GEMINI_PROJECT_ID=groovy-iris-473015-h3
GEMINI_LOCATION=us-central1
GEMINI_CHAT_MODEL=gemini-2.5-flash

# 保留 OpenAI (RAG + Whisper)
OPENAI_API_KEY=sk-xxx
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

**Production** (漸進式切換):
```bash
# Week 1: 10% traffic to Gemini
DEFAULT_LLM_PROVIDER=openai  # 90% 仍用 OpenAI
# 手動測試 rag_system=gemini

# Week 2: 50% traffic to Gemini
DEFAULT_LLM_PROVIDER=gemini  # 預設 Gemini
# 支援 fallback 到 OpenAI

# Week 3: 100% traffic to Gemini
DEFAULT_LLM_PROVIDER=gemini
# OpenAI 只用於 RAG + Whisper
```

### 5.2 回滾計畫
如果 Gemini 出現問題：
```bash
# 緊急回滾：改環境變數
DEFAULT_LLM_PROVIDER=openai

# 或在 API 層級回滾
class ReportRequest(BaseModel):
    rag_system: str = "openai"  # 改回預設 OpenAI
```

---

## Phase 6: 長期優化

### 6.1 考慮 Flash-Lite (更省成本)
對於非關鍵任務 (會談摘要、對話提取)，可用 `gemini-2.5-flash-lite` 省 33% 成本

### 6.2 探索 Batch Processing
Gemini 支援 batch mode 省 50% (但有延遲)，適合：
- 歷史報告批次重新生成
- 大量評估任務

### 6.3 監控與調整
- 追蹤 Gemini vs OpenAI 的品質差異
- 監控 API 延遲和錯誤率
- 根據成本效益調整模型選擇

---

## 實作 Checklist

### Phase 1: 基礎設施
- [ ] 更新 `app/core/config.py` 添加 Gemini 配置
- [ ] 擴展 `app/services/gemini_service.py` 支援 messages 格式
- [ ] 添加 structured output 支援 (JSON schema)
- [ ] 添加模型切換功能 (Flash vs Flash-Lite vs Pro)

### Phase 2: 服務遷移
- [ ] 遷移 `session_summary_service.py` 到 Gemini
- [ ] 遷移 `report_service.py` 到 Gemini
- [ ] 更新 `rag_report.py` 預設為 Gemini
- [ ] (可選) 遷移 `report_grader.py` 到 Gemini Flash/Pro
- [ ] (可選) 遷移 `evaluation_service.py` 到 Gemini

### Phase 3: 測試
- [ ] 更新 integration tests
- [ ] 品質驗證 (摘要、報告、評分)
- [ ] 成本監控設置

### Phase 4: 部署
- [ ] Staging 環境測試
- [ ] Production 漸進式切換 (10% → 50% → 100%)
- [ ] 準備回滾計畫

---

## 預期結果

### ✅ 成本
- 短期: 與 OpenAI 相近 (主要省在評分功能)
- 長期: 如用 Flash-Lite 可省 1-2%

### ✅ 品質
- Gemini 2.5 Flash 在長文本生成上可能更優秀
- 需實際測試驗證

### ✅ 風險
- 低風險: 報告生成、會談摘要 (可快速回滾)
- 中風險: 報告評分 (需驗證準確性)
- 高風險: 無 (關鍵功能保留 OpenAI)

---

## 時程規劃

| 階段 | 時間 | 任務 |
|------|------|------|
| **Week 1** | 1-2 天 | Phase 1: 基礎設施準備 |
| **Week 2** | 2-3 天 | Phase 2: 服務遷移 (報告生成、摘要) |
| **Week 3** | 2-3 天 | Phase 3: 測試與驗證 |
| **Week 4** | 1-2 天 | Phase 4: Staging 部署測試 |
| **Week 5** | 1 週 | Phase 5: Production 漸進式切換 |

**總時程**: 約 3-4 週

---

**建議**: 先做 Phase 1 + Phase 2.1-2.2 (報告生成、摘要)，測試品質後再決定是否遷移評分功能。
