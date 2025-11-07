# Vertex AI RAG POC 整合完成 ✅

## 🎉 完成項目

1. ✅ **啟用 Vertex AI API** - `aiplatform.googleapis.com`
2. ✅ **安裝 SDK** - `google-cloud-aiplatform ^1.120.0`
3. ✅ **建立 API Endpoints** - `/api/rag/vertex-poc/*`
4. ✅ **建立前端頁面** - `/rag/vertex-poc`
5. ✅ **整合到 RAG Console** - 側邊欄「開發工具」區塊
6. ✅ **測試驗證** - 伺服器正常啟動，API 正常回應

## 🚀 使用方式

### 啟動伺服器

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

### 訪問 POC 頁面

開啟瀏覽器：**http://localhost:8000/rag/vertex-poc**

或從 RAG Console 側邊欄點選：**🧪 Vertex AI POC**

## 📋 POC 功能

### 步驟 1: 管理 Corpus

- **建立 Corpus** - 輸入名稱（如 `poc-corpus-20250411`）並建立
- **選擇 Corpus** - 從下拉選單選擇已存在的 POC corpus
- **刪除 Corpus** - 刪除不再需要的測試 corpus

### 步驟 2: 上傳文件

#### 預設測試文件（推薦）

點選「⬆️ 上傳預設文件」會自動上傳 3 個職涯理論文件：

1. **Super's Life-Span Theory** - 生涯發展階段理論
2. **Schein's Career Anchors** - 職涯錨理論
3. **Krumboltz's Planned Happenstance** - 計劃性偶然理論

#### 自訂文件

選擇您自己的 `.txt`, `.pdf`, `.docx` 檔案上傳測試。

⚠️ **重要**：上傳後請等待 10 秒讓 Vertex AI 建立索引。

### 步驟 3: 查詢與對比

#### 快速測試按鈕

- **測試 1**: "個案正在探索職涯方向，不確定未來要做什麼，我該如何協助？"
- **測試 2**: "個案重視工作與生活平衡，但公司要求加班，如何諮詢？"
- **測試 3**: "個案遇到職涯瓶頸，覺得工作沒有挑戰性，有哪些理論可以參考？"

#### 查詢參數

- **Top-K**: 返回結果數（1-10）
- **生成方式**:
  - **僅檢索** - 純向量檢索，適合接 OpenAI GPT-4 生成
  - **檢索 + Gemini 生成** - 使用 Gemini 直接生成回答

#### 對比測試（開發中）

未來將同時查詢 Vertex AI 和現有 RAG 系統，並顯示對比結果。

## 📊 查詢結果

### 僅檢索模式

顯示內容：
- 檢索到的相關片段（按相似度排序）
- 每個片段的相似度分數
- 來源文件資訊
- 處理時間

### 檢索 + Gemini 模式

顯示內容：
- Gemini 生成的完整回答
- 處理時間

## 💰 成本估算

POC 頁面底部顯示 Vertex AI 計費資訊：

| 項目 | 價格 |
|------|------|
| Storage | $0.30 / GB / month |
| Queries | $0.01 / 1K queries |
| Embedding | 免費（內建 text-embedding-004） |

💡 **建議整合方案**：Vertex RAG 檢索 + OpenAI GPT-4 生成報告

## 🔧 API 端點

### Corpus 管理

```bash
# 建立 Corpus
POST /api/rag/vertex-poc/corpus/create
{
  "display_name": "poc-corpus-test",
  "description": "Test corpus"
}

# 列出所有 POC Corpus
GET /api/rag/vertex-poc/corpus/list

# 刪除 Corpus
DELETE /api/rag/vertex-poc/corpus/{corpus_name}
```

### 文件上傳

```bash
# 上傳預設文件
POST /api/rag/vertex-poc/upload/default
{
  "corpus_name": "projects/.../corpora/..."
}

# 上傳自訂文件
POST /api/rag/vertex-poc/upload/custom?corpus_name=...
[FormData with files]
```

### 查詢

```bash
# 執行查詢
POST /api/rag/vertex-poc/query
{
  "corpus_name": "projects/.../corpora/...",
  "question": "問題內容",
  "top_k": 5,
  "use_gemini": false
}

# 對比查詢（開發中）
POST /api/rag/vertex-poc/compare
{
  "vertex_corpus_name": "projects/.../corpora/...",
  "question": "問題內容",
  "top_k": 5
}
```

### 健康檢查

```bash
GET /api/rag/vertex-poc/health
```

## 📝 測試流程範例

### 完整測試流程

1. **建立 Corpus**
   - 輸入名稱：`poc-test-20250411`
   - 點選「➕ 建立 Corpus」
   - 確認狀態列顯示新建立的 corpus

2. **上傳測試文件**
   - 點選「⬆️ 上傳預設文件」
   - 等待上傳完成
   - **等待 10 秒**讓系統建立索引

3. **執行測試查詢**
   - 點選「測試 1: 探索職涯方向」
   - 確認 Top-K = 5
   - 選擇「僅檢索」模式
   - 點選「🚀 查詢 Vertex AI」

4. **檢視結果**
   - 查看檢索到的理論片段
   - 檢查相似度分數（應該 > 0.5）
   - 確認回應時間（通常 < 2 秒）

5. **清理資源**
   - 從下拉選單選擇 corpus
   - 點選「🗑️ 刪除」
   - 確認刪除

## ⚠️ 注意事項

### 索引等待時間

上傳文件後，Vertex AI 需要時間建立向量索引：
- 小型文件（< 1MB）: 約 5-10 秒
- 大型文件（> 10MB）: 可能需要 1-2 分鐘

建議上傳後等待 10 秒再查詢。

### Corpus 命名規範

- 建議使用 `poc-` 前綴（POC 列表會自動過濾）
- 範例：`poc-corpus-20250411`, `poc-test-theories`

### 刪除 Corpus

- 刪除操作無法復原
- 請確認不再需要後再刪除
- 如忘記刪除，可能產生小額儲存費用（$0.30/GB/月）

## 🎯 評估要點

### 優勢 ✅

1. **快速建立** - 幾分鐘內建立完整 RAG 系統
2. **自動化** - Chunking、Embedding、Indexing 全自動
3. **託管服務** - 不需維護資料庫和向量引擎
4. **支援中文** - 檢索品質良好
5. **內建 Embedding** - 不需額外付費給 OpenAI embeddings

### 需考慮 ⚠️

1. **LLM 選擇** - 預設 Gemini，但可以只用檢索 + 自己用 GPT-4
2. **成本** - 需評估 vs Supabase + OpenAI Embeddings
3. **遷移** - 現有知識庫需遷移到 Vertex AI
4. **Vendor Lock-in** - 綁定 GCP 生態系
5. **Region 限制** - 某些功能僅特定 region 支援

### 整合建議

**混合方案**（最佳實踐）:

```python
# 在 app/services/report_service.py

async def _retrieve_theories(self, query: str) -> List[Dict]:
    """使用 Vertex AI RAG 檢索（取代現有實現）"""
    from vertexai.preview import rag

    response = rag.retrieval_query(
        rag_resources=[rag.RagResource(rag_corpus=CORPUS_NAME)],
        text=query,
        similarity_top_k=5
    )

    # 轉換為現有格式，保持 API 接口不變
    return [
        {
            "text": ctx.text,
            "score": ctx.score,
            "source": ctx.source_uri
        }
        for ctx in response.contexts.contexts
    ]

# 報告生成仍用 OpenAI GPT-4
# _generate_structured_report 方法保持不變
```

**優點**：
- 底層換成 Vertex AI（更穩定、免維護）
- 上層 API 接口不變（iOS App 不需改動）
- 仍使用 GPT-4 生成報告（品質保證）

## 🔄 下一步

### 如果決定採用

1. **評估現有知識庫大小** - 計算遷移成本
2. **製作遷移腳本** - 批量上傳文件到 Vertex AI
3. **整合到 report_service.py** - 替換底層實現
4. **保留舊系統作備份** - 分階段遷移
5. **監控成本** - 設定 GCP 預算警報

### 如果決定不採用

- 刪除 POC 相關檔案：
  ```bash
  rm app/api/vertex_poc.py
  rm app/templates/rag/vertex_poc.html
  rm VERTEX_POC_GUIDE.md
  poetry remove google-cloud-aiplatform
  ```
- 還原 `main.py` 和 `base_sidebar.html` 的修改
- 不影響現有系統

## 📚 相關資源

- [Vertex AI RAG Engine 官方文件](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview)
- [Python SDK 參考](https://cloud.google.com/python/docs/reference/aiplatform/latest)
- [定價說明](https://cloud.google.com/vertex-ai/pricing#generative-ai-models)
- [最佳實踐](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/best-practices)

## 🐛 問題排查

### 錯誤: "API not enabled"

```bash
gcloud services enable aiplatform.googleapis.com --project=groovy-iris-473015-h3
```

### 錯誤: "Permission denied"

確認 GCP 帳號權限：

```bash
gcloud projects add-iam-policy-binding groovy-iris-473015-h3 \
  --member="user:dev02@careercreator.tw" \
  --role="roles/aiplatform.user"
```

### 錯誤: "Region not supported"

改用 `us-central1`:

```python
# 修改 app/api/vertex_poc.py
LOCATION = "us-central1"
```

### 查詢無結果

- 確認文件已上傳成功
- 等待 10 秒讓索引建立完成
- 檢查問題是否與文件內容相關

---

**準備好了嗎？啟動伺服器開始測試！** 🚀

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

然後訪問：**http://localhost:8000/rag/vertex-poc**
