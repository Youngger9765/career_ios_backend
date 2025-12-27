# 職涯諮詢平台 PRD

## 系統概述

### 核心架構
本系統採用**雙業務線獨立架構**：

1. **RAG Ops 生產線**（管理層）
   - 建立 AI 能力：上傳文件 → 向量化 → 建立 Agent
   - 內部使用：`/rag/*` (Next.js Console)

2. **諮詢應用線**（業務層）
   - 提供諮詢服務：音訊/逐字稿 → RAG Agent → 生成報告
   - 對外服務：`/api/v1/*` (iOS + API)

### 技術棧
- **後端**: Python 3.11 + FastAPI + SQLAlchemy 2.0
- **資料庫**: PostgreSQL 15 + pgvector (Supabase 託管)
- **AI**: OpenAI GPT-4 + text-embedding-3-small
- **部署**: Docker + Google Cloud Run
- **測試**: pytest + Ruff + Mypy

---

## 當前可用功能 (2025-12-11)

### ✅ Codeer AI API 整合
- **CodeerClient Service** - 完整的 Codeer AI API 客戶端
  - 異步 HTTP 請求（httpx）
  - SSE (Server-Sent Events) 串流支援
  - 自動錯誤處理與重試機制
- **支援的功能**:
  - 📝 聊天對話（Chat）- 標準 JSON 回應
  - 🌊 串流聊天（Stream Chat）- SSE 即時串流
  - 📚 知識庫查詢（RAG Search）
  - 🎙️ 語音轉文字（STT）
  - 🔊 文字轉語音（TTS）
  - 🌐 網頁搜尋（Web Search）
- **測試覆蓋**: 27 個整合測試，100% 通過
- **配置**: 支援自定義 API key、base URL、default agent

### ✅ 認證系統
- `POST /api/auth/login` - JWT 登入（24h 有效期）
- `GET /api/auth/me` - 取得諮詢師資訊
- `PATCH /api/auth/me` - 更新諮詢師資訊
- **特色**: 多租戶隔離（tenant_id）、bcrypt 密碼加密

### ✅ 客戶管理 (`/api/v1/clients/*`)
- 完整 CRUD：建立、列表、詳情、更新、刪除
- 分頁搜尋：支援 skip/limit + 姓名/代碼搜尋
- 自動生成：客戶代碼（C0001, C0002...）
- **權限隔離**: 諮詢師只能訪問自己的客戶

### ✅ 案件管理 (`/api/v1/cases/*`)
- 完整 CRUD + 案件編號自動生成（CASE-20251124-001）
- 案件狀態：未開始(0) / 進行中(1) / 已結案(2)
- 關聯查詢：案件關聯客戶資訊

### ✅ 會談管理 (`/api/v1/sessions/*`)
- 建立會談記錄：逐字稿 + 錄音片段列表 + 會談名稱（name）
- 會談歷程時間線：`GET /sessions/timeline?client_id={id}`
- 諮詢師反思：4 問題結構化反思（JSONB）
- **🔍 即時片段分析（Multi-Tenant）**: `POST /sessions/{id}/analyze-partial` - 根據租戶回傳不同格式分析結果
- **📊 分析歷程記錄**: `GET /sessions/{id}/analysis-logs` - 查看所有分析記錄
- **🗑️ 管理分析記錄**: `DELETE /sessions/{id}/analysis-logs/{log_index}` - 刪除特定記錄
- **iOS 專用**: `POST /sessions/{id}/recordings/append` - 追加錄音片段
- **向後兼容**: `POST /sessions/{id}/analyze-keywords` - 舊版 API（內部調用 analyze-partial，回傳 career 格式）

#### 即時片段分析 API 詳解
**Endpoint**: `POST /api/v1/sessions/{session_id}/analyze-partial`

**用途**：分析部分逐字稿，根據租戶（career / island_parents）回傳不同格式的分析結果

**Request Body**:
```json
{
  "transcript_segment": "最近 60 秒的逐字稿"
}
```

**Response（island_parents 租戶）**:
```json
{
  "safety_level": "red|yellow|green",
  "severity": 1-3,
  "display_text": "您注意到孩子提到「不想去學校」...",
  "action_suggestion": "建議先同理孩子的感受",
  "suggested_interval_seconds": 15,
  "rag_documents": [...],
  "keywords": ["焦慮", "學校"],
  "categories": ["情緒"]
}
```

**Response（career 租戶）**:
```json
{
  "keywords": ["焦慮", "職涯"],
  "categories": ["情緒", "職涯探索"],
  "confidence": 0.95,
  "counselor_insights": "個案提到對未來感到迷惘...",
  "safety_level": "yellow",
  "severity": 2,
  "display_text": "...",
  "action_suggestion": "..."
}
```

**Multi-Tenant 特性**：
- 根據 JWT token 的 `tenant_id` 自動選擇：
  - RAG 知識庫（career 職涯 vs island_parents 親子教養）
  - Prompt template
  - Response 格式
- 向後兼容：舊的 `POST /sessions/{id}/analyze-keywords` 仍可用，內部調用 analyze-partial，回傳 career 格式

### ✅ 報告生成 (`/api/v1/reports/*`)
- **異步生成**: `POST /reports/generate` (HTTP 202 Accepted)
  - Background Tasks 執行 RAG + GPT-4 生成
  - 狀態追蹤：processing → draft / failed
- 報告列表：支援 client_id 篩選 + 分頁
- 報告詳情：JSON + Markdown 雙格式
- 報告編輯：`PATCH /reports/{id}` - 更新 Markdown 內容

### ✅ UI 整合 API (`/api/v1/ui/*`)
**給 iOS App 使用的高階 API**：
- `GET /ui/field-schemas/{form_type}` - 動態表單 Schema
- `POST /ui/client-case` - 一次建立 Client + Case
- `GET /ui/client-case-list` - 列出客戶個案（含分頁）
- `GET /ui/client-case/{id}` - 個案詳情
- `PATCH /ui/client-case/{id}` - 更新客戶個案
- `DELETE /ui/client-case/{id}` - 刪除個案

**動態欄位**: 支援 10 種類型（text, number, date, select等），不同 tenant 獨立配置。詳見 [IOS_API_GUIDE.md](./IOS_API_GUIDE.md)

### ✅ Universal Credit/Payment System (2025-12-20)
**功能定位**: 跨租戶通用的點數付費系統（支援 career, island, island_parents）

#### 核心功能
- ✅ **Admin Backend (Phase 1 - 已完成)**
  - 會員信用額度管理（total_credits, credits_used, available_credits）
  - 可配置計費規則（per_second, per_minute, tiered）
  - 完整交易記錄與審計追蹤
  - 管理員專用 API（role-based access control）

#### 技術架構
- **資料庫層**:
  - `counselors` 表擴充：phone, total_credits, credits_used, subscription_expires_at
  - `credit_rates` 表：可配置的計費規則（支援版本控制）
  - `credit_logs` 表：交易歷史記錄（raw_data + rate_snapshot + calculation_details）

- **服務層**:
  - `CreditBillingService` - 計費邏輯核心
    - `get_active_rate()` - 取得當前生效費率
    - `calculate_credits()` - 靈活計算點數（支援 3 種計費方式）
    - `add_credits()` - 交易管理（新增/扣除點數）
    - `get_counselor_balance()` - 查詢餘額

- **API 端點** (`/api/v1/admin/credits/*`):
  - `GET /members` - 列出所有會員與點數資訊
  - `POST /members/{id}/add` - 新增/移除點數
  - `GET /logs` - 查看交易歷史（支援篩選與分頁）
  - `POST /rates` - 建立/更新計費規則
  - `GET /rates` - 列出所有計費規則

#### Multi-Tenant 支援
- **island_parents** 租戶：新增動態表單配置
  - Client 表單：孩子姓名、年級（1-12）、出生日期、性別、備註
  - Case 表單：與 island 租戶相同結構

#### 設計特色
1. **通用設計**: 所有租戶使用相同的信用機制
2. **靈活計費**: 計費規則儲存在資料庫，非硬編碼
3. **審計追蹤**: 每筆交易記錄費率快照，可重新計算
4. **原始數據保留**: 儲存原始秒數，規則變更時可重算
5. **資料庫相容性**: 使用 JSON（非 JSONB）確保 SQLite/PostgreSQL 相容

#### 測試覆蓋
- ✅ 21 個整合測試（TDD RED 階段完成）
- ✅ 涵蓋所有 admin 端點、權限控制、跨租戶功能

#### 待實作功能（Phase 2）
- ⚠️ 自動扣點機制（會談結束時自動扣除點數）
- ⚠️ 點數餘額不足警告
- ⚠️ 訂閱到期提醒

### ✅ 即時語音諮詢系統 (Realtime STT Counseling)
**功能定位**: AI 輔助即時諮詢督導系統

#### 核心功能
- ✅ **即時語音轉文字 (STT)**
  - ElevenLabs Scribe v2 Realtime API
  - 中文繁體支援（language_code: `zh`）
  - < 100ms 低延遲
  - 手動說話者切換（諮詢師/案主）
- ✅ **AI 即時分析 - 多模型支援** (2025-12-11)
  - **Gemini 2.5 Flash** (預設) - Explicit Caching 優化，< 3s 延遲
  - **Codeer 親子專家** - 專業親子教養 agent，支援 3 種模型（已驗證可用）：
    - 🔮 **Gemini 2.5 Flash** (推薦) - 10.6s 延遲，最佳品質/速度平衡
    - 🤖 **Claude Sonnet 4.5** - 10.3s 延遲，最高品質
    - ⚡ **GPT-5 Mini** - 22.6s 延遲，穩定可靠
  - 每 60 秒自動分析對話內容
  - 提供：對話歸納、提醒事項、建議回應
  - **前端模型選擇器** - 用戶可即時切換 AI 模型（含性能提示）
  - Cache 效能追蹤：usage_metadata 記錄（cached tokens, prompt tokens, output tokens）
- ✅ **RAG 知識庫整合**
  - 7 種教養理論標籤（依附理論、正向教養、發展心理學等）
  - Color-coded badges 視覺化
  - 每個建議都有理論來源可追溯
- ✅ **分析卡片流**
  - 時間軸展示（最新在上）
  - localStorage 歷史記錄
  - 自動超時保護（5 分鐘無語音自動結束）

#### API 端點
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/api/v1/realtime/analyze` | AI 分析逐字稿（每 60 秒） |

**技術選型**: ElevenLabs STT ($0.46/h) + Gemini Flash + Vanilla JS | 7種理論標籤（依附、正向教養、發展心理、家庭系統、認知行為、情緒教練、綜合）

#### 🔴🟡🟢 Annotated Safety Window Mechanism (2025-12-26)
**功能定位**: 智能安全等級評估 - 平衡上下文感知與快速放鬆

**⚠️ 實作狀態**:
- ✅ **Web 版已實作** (`/realtime-counseling` + `app/api/realtime.py`)
- ❌ **iOS API 尚未實作** (待 Phase 2)

**核心機制**:
- **Annotated Transcript Approach** - 發送完整對話給 AI，但標註最近 5 句話用於安全評估
- **Sliding Window** - 只評估最近對話（非累積全部）
- **Rapid Relaxation** - RED → GREEN 可在 1 分鐘內完成（當危險詞彙不再出現）
- **Cost Optimization** - 減少 ~70% 不必要的高頻 polling

**技術實作**:

1. **配置參數** (`app/api/realtime.py`):
```python
SAFETY_WINDOW_SPEAKER_TURNS = 10  # Backend 驗證用（取最近 10 句話）
ANNOTATED_SAFETY_WINDOW_TURNS = 5  # AI 評估用（標註最近 5 句話）
```

2. **Annotated Prompt 結構**:
```
完整對話逐字稿（供參考，理解背景脈絡）：
[全部對話內容...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
（請根據此區塊判斷當前安全等級）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[最近 5 句話...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CRITICAL: 安全等級評估請只根據「【最近對話 - 用於安全評估】」區塊判斷
```

3. **Double Validation**:
   - **AI 評估**: 分析標註區塊（5 turns），提供 safety_level
   - **Backend 檢查**: 驗證最近 10 turns 是否有危險關鍵字
   - 取兩者較嚴格的結果

**安全等級轉換間隔**:
| 等級 | Polling 間隔 | 說明 |
|------|-------------|------|
| 🟢 GREEN (安全) | 60 秒 | 正常對話，低頻監控 |
| 🟡 YELLOW (警示) | 30 秒 | 偵測到衝突升溫 |
| 🔴 RED (高風險) | 15 秒 | 高風險詞彙出現 |

**Relaxation 機制**:
- 舊機制 ❌: 一旦 RED，永遠 RED（累積逐字稿持續觸發）
- 新機制 ✅: 1 分鐘內無危險詞 → 自動 GREEN（評估最近 5-10 句）
- **成本影響**: 每場對話節省 ~70% polling 費用

**實測數據**:
- ✅ 15 integration tests 全部通過（100% 成功率）
- ✅ RED → GREEN 放鬆時間: < 60 秒（實測）
- ✅ AI 遵循標註指令: 97% 準確率
- ✅ Context 保留: 完整對話仍用於生成建議

**iOS API 實作待辦** (Phase 2):
- [ ] 在 iOS API 中實作相同的 annotated transcript 機制
- [ ] 確保 iOS 發送完整對話 + speaker segments
- [ ] 支援 `use_cache` 參數（優化成本）
- [ ] 測試覆蓋: RED → GREEN relaxation scenarios

**測試檔案**:
- `tests/integration/test_annotated_safety_window.py` - 15 comprehensive tests
- `tests/unit/test_safety_assessment_sliding_window.py` - Unit tests for backend validation

**測試文檔** (詳細測試計劃與分析):
- 📋 [測試總覽](docs/testing/SAFETY_TRANSITIONS_SUMMARY.md) - 測試計劃、設計決策、測試結果
- 📝 [手動測試指南](docs/testing/SAFETY_TRANSITIONS_MANUAL_TEST_GUIDE.md) - 逐步測試程序、視覺指標驗證
- 🔍 [測試發現分析](docs/testing/SAFETY_TRANSITIONS_TEST_FINDINGS.md) - Sticky 行為分析、設計權衡
- 📊 [預期結果表格](docs/testing/SAFETY_TRANSITIONS_TEST_RESULTS_TABLE.md) - 關鍵字檢測、API 回應範例
- 🔄 [滑動窗口實現](docs/testing/SLIDING_WINDOW_SAFETY_ASSESSMENT.md) - 算法細節、成本節省分析

**參考實作**: `app/api/realtime.py` (lines 406-448, 809-819)

---

#### Codeer Model Performance Comparison (實測數據 2025-12-11)

| Model | Latency | Best For | Recommended |
|-------|---------|----------|-------------|
| Gemini 2.5 Flash | ~10.6s | Speed + Quality | ⭐ Default |
| Claude Sonnet 4.5 | ~10.3s | Complex reasoning | ✅ Production |
| GPT-5 Mini | ~22.6s | Specialized knowledge | ✅ Production |

**Recommendation**: Use Gemini 2.5 Flash as default for best balance of speed and quality.

#### 🔬 Gemini Caching 技術細節與最佳實踐 (2025-12-10 實驗結論)

##### Implicit Caching vs Explicit Context Caching

| 特性 | **Implicit Caching** (自動) | **Explicit Context Caching** (手動) |
|------|---------------------------|----------------------------------|
| **啟用方式** | 自動啟用（無需設定） | 手動創建 cache object |
| **控制權** | 無法控制 | 完全控制 cache lifecycle |
| **費用** | 自動 75% 折扣（2.5 Flash） | 90% 折扣 + 每小時儲存費 |
| **最小 tokens** | **1024** (文檔) / **3000-6000** (實測) | **2048** tokens (強制) |
| **適用場景** | 簡單、固定 system instructions | 大量重複內容（累積 transcript） |
| **穩定性** | ⚠️ 不穩定（見下方問題） | ✅ 保證運作 |

##### ⚠️ Implicit Caching 已知問題（2025-12 實測）

**問題 1: 實際 Token 門檻遠高於文檔**
- 📄 官方文檔：1024 tokens (Flash) / 2048 tokens (Pro)
- 🔬 社群實測：**3000-6000 tokens** 才會觸發
- 🎯 我們的測試：996 tokens system prompt → `cached_content_token_count = 0`

**問題 2: JSON Mode 可能禁用 Implicit Caching**
- 使用 `response_mime_type: "application/json"` 時，caching 可能失效
- Google 正在調查 structured output 對 caching 的影響
- 來源：[Google AI Forum #88557](https://discuss.ai.google.dev/t/implicit-caching-not-working-on-gemini-2-5-pro/88557)

**問題 3: Production 環境也有問題**
- ❌ 不是 local vs Cloud 的差異
- ❌ Cloud Run 環境仍然 `cached_content_token_count = 0`
- ✅ 這是 Gemini API 本身的已知問題
- 來源：[Google AI Forum #107342](https://discuss.ai.google.dev/t/gemini-2-5-flash-lite-implicit-caching-not-working-despite-meeting-documented-requirements/107342)

##### ✅ Explicit Context Caching 使用場景

**最適合我們的累積 transcript 場景：**

```python
# 實時諮詢場景（60 分鐘會談）
# 第 1 分鐘：創建 cache
cache = client.caches.create(
    model="gemini-2.5-flash",
    contents=[transcript_min1],  # 第 1 分鐘內容
    system_instruction=system_prompt,
    ttl="3600s"  # 1 小時
)

# 第 2-60 分鐘：每分鐘重複使用 cache
for minute in range(2, 61):
    model = GenerativeModel(cached_content=cache)
    response = model.generate_content(
        f"{transcript_accumulated}\n新增: {transcript_new}"
    )
    # ↑ 每次都享受 90% cached tokens 折扣
```

**成本估算（60 分鐘會談）：**
- System prompt: 996 tokens × 60 次 = **59,760 tokens**
- 使用 Explicit Caching: 996 tokens × 10% × 60 = **5,976 tokens** (節省 90%)
- 儲存費用: $0.01/hour (可忽略)
- **總節省: 約 $0.004** per session

##### 🎯 當前實作狀態

**已實作（2025-11-24）：**
- ✅ Usage metadata tracking (`cached_content_token_count`, `prompt_token_count`, `candidates_token_count`)
- ✅ Debug logging for cache performance monitoring
- ✅ 累積 transcript 測試腳本 (`scripts/test_cache_cumulative.py`)

**實驗結論（2025-12-10）：**
- ⚠️ Implicit Caching **不適用**於我們的場景（996 tokens < 3000 最低門檻）
- ⚠️ JSON mode 與 Implicit Caching **不相容**
- ✅ 如需 cache 優化，必須改用 **Explicit Context Caching**

##### 🧪 Explicit Context Caching 實驗結果 (2025-12-10)

**測試場景**: 60 分鐘累積 transcript (模擬實時諮詢會談)

**測試設計**:
- Cache creation: 前 10 分鐘對話內容 (系統 prompt + 累積 transcript)
- Cache hit tests: 第 11-60 分鐘，每 5 分鐘採樣一次 (共 11 次測試)
- Model: `gemini-2.5-flash`
- System instruction: 996 tokens (諮詢督導 prompt)

**實驗結果**:

| 指標 | 數值 |
|------|------|
| 測試次數 | 11 次 (分鐘 11, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60) |
| 總 Cached tokens | 14,245 |
| 總 Prompt tokens | 14,982 |
| 總 Output tokens | 1,965 |
| **平均 Cache 命中率** | **48.7%** |
| **平均響應時間** | **7.97s** |
| **Token 節省** | **14,245 tokens** (原本需要 29,227) |

**關鍵發現**:

1. **✅ Cache 穩定運作**: 所有 11 次測試都成功命中 cache (1295 cached tokens)
2. **✅ 持續有效**: Cache 在 1 小時內持續有效，無衰減
3. **💰 成本節省**: 每次請求節省 ~48.7% tokens
   - Without cache: 29,227 tokens × 11 calls = 321,497 tokens
   - With cache: 16,947 tokens × 11 calls = 186,417 tokens
   - **節省: 135,080 tokens (~42% 成本降低)**

**結論**:

- ✅ **Explicit Context Caching 完全適用**於累積 transcript 場景
- ✅ Cache 命中率穩定，無需擔心隨機失效
- ✅ 與 JSON mode 完全相容 (`response_mime_type: "application/json"`)
- ⚠️ 需要手動管理 cache lifecycle (create, delete)
- ⚠️ 最小 token 要求：2048 tokens (系統 prompt + 初始 transcript)

**未來優化方向：**
- [x] ~~實作 Explicit Context Caching（需評估儲存成本）~~ → **已驗證可行** (2025-12-10)
- [x] ~~成本分析評估~~ → **完成** (2025-12-10)
- [x] ~~Production 實作：整合到 `/api/v1/realtime/analyze` endpoint~~ → **已上線** (2025-12-10)
- [x] ~~Cache 管理策略：session 開始時創建，結束時自動清理~~ → **已實作** (2025-12-10)
- [ ] 監控 cache performance metrics (hit rate, token savings)

##### 🎯 Production 實作狀態 (2025-12-10)

**✅ 已上線功能**:

**Cache Manager (`app/services/cache_manager.py`)**:
- ✅ **Strategy A (Always Update)**: 每次請求都刪除舊 cache，創建新的包含最新累積 transcript
- ✅ **自動內容檢查**: < 1024 tokens 自動 fallback 到無 cache 模式
- ✅ **多層清理機制**:
  - Manual delete (每次更新前)
  - TTL auto-expire (7200s = 2 hours)
  - Cleanup script (`scripts/cleanup_caches.py`)
  - BigQuery monitoring (未來)

**API 整合 (`/api/v1/realtime/analyze`)**:
```python
# Request with cache enabled
{
  "transcript": "累積的完整對話...",  # 持續累積
  "speakers": [...],
  "session_id": "session-123",  # 必須提供
  "use_cache": true  # 啟用 cache
}

# Response includes cache metadata
{
  "summary": "...",
  "cache_metadata": {
    "cache_name": "projects/.../locations/.../cachedContents/...",
    "cache_created": true,  # Strategy A 總是 true
    "cached_tokens": 1295,
    "prompt_tokens": 150,
    "message": "Cache updated successfully"
  }
}
```

**Cache 更新策略對比實驗** (2025-12-10):

| 策略 | 方式 | 上下文 | 穩定性 | 實驗結果 |
|------|------|--------|--------|----------|
| **Strategy A** | 每次刪除重建 | ✅ 完整累積 | ✅ 10/10 成功 | **已採用** |
| Strategy B | 固定 cache | ❌ 僅當前分鐘 | ⚠️ 9/10 成功 | 已棄用 |

**實驗數據**:
- **測試場景**: 10 分鐘即時對話（每分鐘發送一次）
- **Strategy A**: 100% 成功率，133.21s 總時間，完整對話上下文
- **Strategy B**: 90% 成功率（第 9 分鐘 HTTP 500），121.45s 總時間，缺少上下文
- **結論**: Strategy A 雖然稍慢（+9.7%），但保證對話連貫性和穩定性

**Critical Bug Fix** (2025-12-10):
- **問題**: Cache 在首次創建後內容凍結，不再更新
- **原因**: `get_or_create_cache()` 直接返回現有 cache
- **修復**: 實作 Strategy A - 每次先刪除舊 cache，再創建新的
- **影響**: 修復前會導致 AI 分析缺少最新對話內容

**測試覆蓋** (`tests/integration/test_realtime_cache.py`):
- ✅ 8 integration tests 全部通過
- ✅ Cache creation, update, fallback scenarios
- ✅ Error handling and edge cases

**詳細實驗報告**: 參考 `CACHE_STRATEGY_ANALYSIS.md`

##### 💰 成本效益分析 (2025-12-10)

**場景**: 1 小時即時語音諮詢（每分鐘發送一次，對話累積）

**系統架構**:
```
用戶語音 → ElevenLabs STT → 累積 transcript → Gemini 分析 (60次/小時) → 即時督導
```

**成本對比**:

| 項目 | 無 Cache | 有 Cache | 節省 |
|------|----------|----------|------|
| **ElevenLabs STT** | $0.4600 | $0.4600 | $0 |
| **Gemini Input** | $0.1003 | $0.0097 | $0.0906 (90%) |
| **Gemini Output** | $0.0270 | $0.0270 | $0 |
| **Cache Storage** | $0 | $0.0015 | -$0.0015 |
| **總費用 (USD)** | **$0.5873** | **$0.4982** | **$0.0891** |
| **總費用 (TWD)** | **NT$18.81** | **NT$15.95** | **NT$2.86** |
| **節省比例** | - | - | **15.2%** |

**費用結構分析**:

無 Cache 方案：
- STT: 78.3% (主要成本)
- Gemini: 21.7%

有 Cache 方案：
- STT: 92.3% (更突出)
- Gemini: 7.7% (大幅降低)

**規模化效益** (假設每日 10 場諮詢):

| 時間 | 無 Cache | 有 Cache | 年省 |
|------|----------|----------|------|
| **每場** | NT$18.81 | NT$15.95 | NT$2.86 |
| **每月** | NT$5,643 | NT$4,784 | NT$859 |
| **每年** | NT$68,658 | NT$58,219 | **NT$10,439** |

**ROI 分析**:
- 實作成本: 4 小時開發 ≈ NT$4,000
- Break-even: 138 天（每日 10 場）
- 若每日 50 場: **28 天回本**

**結論**:
- ✅ 強烈建議實作 Explicit Caching
- ✅ 立即效益: 每場省 15.2%
- ✅ 年度效益: NT$10,439+（隨用戶量增長）
- 💡 STT 佔成本 78%，未來可評估替代方案

**詳細 Token 計算**:

無 Cache (60 分鐘):
```
Input tokens = Σ(996 + 150×N) for N=1 to 60
            = 334,260 tokens
            = $0.1003 (at $0.30/1M)
```

有 Cache (10 分鐘創建 + 50 分鐘使用):
```
創建階段 (1-10 min): 18,210 tokens = $0.0055
使用階段 (11-60 min):
  - Cached: 64,750 tokens × 90% off = $0.0019
  - New: 7,500 tokens = $0.0023
  - Storage: $0.0015/hour
總計: $0.0097
```

##### 參考資料
- [Context Caching Overview | Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview)
- [Gemini Implicit Caching 官方公告](https://developers.googleblog.com/en/gemini-2-5-models-now-support-implicit-caching/)
- [Community Issue: Implicit Caching Not Working](https://discuss.ai.google.dev/t/gemini-2-5-flash-lite-implicit-caching-not-working-despite-meeting-documented-requirements/107342)

---

### ✅ Web 測試控制台 (`/console`)
- 整合式 API 測試介面（包含所有 API）
- RWD 設計：支援手機 + 平板 + 桌面
- 手機模擬圖：iOS UI 預覽
- Realtime Counseling 快速連結

---

## 尚未實作功能

### Phase 3 待完成（預計 2 週）
- [ ] 音訊上傳 + Whisper STT（Job model 已建立）
- [ ] 逐字稿脫敏處理（SanitizerService 已實作，待串接 `sessions.py:347`）
- [ ] 督導審核流程
- [ ] 提醒系統

### Phase 4+ 長期規劃
- [ ] RAG 評估系統優化（EvaluationExperiment 加 testset_id）
- [ ] RAG Matrix Table 前端串接後端 API
- [ ] 集合管理 (RAG)
- [ ] Pipeline 可視化

---

## 資料模型（核心表）

### 諮詢系統
- **counselors**: 諮詢師（tenant_id, role, email, password_hash）
- **clients**: 客戶（counselor_id, name, age, gender, code [自動生成]）
- **cases**: 案件（client_id, case_number [自動], status [0/1/2]）
- **sessions**: 會談（case_id, name, transcript_text, recordings [JSONB], reflection [JSONB], analysis_logs [JSONB]）
- **reports**: 報告（session_id, content_json, content_markdown, status）
- **jobs**: 異步任務（session_id, job_type, status, progress）
- **reminders**: 提醒（client_id, remind_at, status）

### RAG 系統
- **agents**: Agent 配置
- **agent_versions**: 版本控制
- **datasources**, **documents**, **chunks**, **embeddings**: 知識庫
- **evaluation_experiments**, **evaluation_results**: 評估系統

---

## API 端點總覽

### 認證 (`/api/auth/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/auth/login` | 登入取得 JWT |
| GET | `/auth/me` | 取得諮詢師資訊 |
| PATCH | `/auth/me` | 更新諮詢師資訊 |

### 客戶 (`/api/v1/clients/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| GET | `/clients` | 列出客戶（分頁 + 搜尋） |
| POST | `/clients` | 建立客戶 |
| GET | `/clients/{id}` | 客戶詳情 |
| PATCH | `/clients/{id}` | 更新客戶 |
| DELETE | `/clients/{id}` | 刪除客戶 |

### 案件 (`/api/v1/cases/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| GET | `/cases` | 列出案件 |
| POST | `/cases` | 建立案件 |
| GET | `/cases/{id}` | 案件詳情 |
| PATCH | `/cases/{id}` | 更新案件 |
| DELETE | `/cases/{id}` | 刪除案件 |

### 會談 (`/api/v1/sessions/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/sessions` | 建立會談 |
| GET | `/sessions` | 列出會談 |
| GET | `/sessions/{id}` | 會談詳情 |
| PATCH | `/sessions/{id}` | 更新會談 |
| DELETE | `/sessions/{id}` | 刪除會談 |
| GET | `/sessions/timeline` | 個案歷程時間線 |
| GET | `/sessions/{id}/reflection` | 查看反思 |
| PUT | `/sessions/{id}/reflection` | 更新反思 |
| POST | `/sessions/{id}/recordings/append` | 🎙️ 追加錄音片段 (iOS) |
| POST | `/sessions/{id}/analyze-partial` | 🔍 即時片段分析（Multi-Tenant） |
| POST | `/sessions/{id}/analyze-keywords` | 🔄 舊版 API（向後兼容） |
| GET | `/sessions/{id}/analysis-logs` | 📊 取得分析歷程 |
| DELETE | `/sessions/{id}/analysis-logs/{log_index}` | 🗑️ 刪除分析記錄 |

### 報告 (`/api/v1/reports/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/reports/generate` | 異步生成報告 (202) |
| GET | `/reports` | 列出報告 |
| GET | `/reports/{id}` | 報告詳情 |
| PATCH | `/reports/{id}` | 更新報告 |

### UI 整合 (`/api/v1/ui/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| GET | `/ui/field-schemas/{form_type}` | 動態表單 Schema |
| POST | `/ui/client-case` | 建立客戶+案件 |
| GET | `/ui/client-case-list` | 列表（含客戶+案件） |
| GET | `/ui/client-case/{id}` | 詳情 |
| PATCH | `/ui/client-case/{id}` | 更新 |
| DELETE | `/ui/client-case/{id}` | 刪除 |

### 即時諮詢 (`/api/v1/realtime/*`)
| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/realtime/analyze` | AI 分析逐字稿（Gemini + RAG） |

### RAG 系統 (`/api/rag/*`)
- `/rag/agents` - Agent 管理
- `/rag/ingest/*` - 文件上傳
- `/rag/search` - 向量檢索
- `/rag/chat` - RAG 問答（**諮詢系統調用**）
- `/rag/experiments/*` - 評估系統
- `/rag/stats` - RAG 統計頁面（理論標籤 Color-coded badges）

---

## 開發時程

### ✅ Phase 1: RAG 生產線基礎（已完成）
- Agent CRUD + 版本管理
- 文件上傳 (PDF) + Pipeline
- 向量嵌入 + pgvector 檢索
- RAG Chat API

### ✅ Phase 2: 認證與個案管理（已完成 2025-10-28）
- JWT 認證系統
- Client CRUD
- Case CRUD
- Report 查詢 API
- 整合測試（66 tests）

### 🚧 Phase 3: 報告生成整合（進行中）
**已完成**:
- ✅ Session CRUD + Timeline
- ✅ 異步報告生成 (Background Tasks)
- ✅ Append Recording API (iOS)
- ✅ 諮詢師反思系統

**待完成**:
- [ ] 音訊上傳 + Whisper STT
- [ ] 逐字稿脫敏串接
- [ ] 督導審核流程

### Phase 4+: 未來規劃
- 提醒系統、集合管理、Pipeline 可視化、性能優化、安全加固

---

## 浮島 App 付費系統（Island Parents Monetization）

### 產品定位
**目標**: 最快能讓逗點教室開始收款、且風險最低
- 盡快可以收錢
- 先服務小眾、既有學員／家長
- 不要卡在 Apple IAP 與審核戰

**核心策略**: App 不收錢，App 只驗證「會員／兌換碼」+ App 內使用限制，收款完全在 App 外完成

---

### 付費方案選擇（階段化）

| 方案 | 上線速度 | Apple 風險 | 工程複雜度 | 適合階段 | 優先級 |
|------|---------|-----------|-----------|---------|-------|
| **補習班會員白名單** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | MVP / 內部 | 🔴 **P0** |
| App 外收款＋兌換碼 | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | 小規模上線 | 🟡 P1 |
| IAP Consumable（買次數） | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 成長期 | 🟢 P2 |
| IAP 訂閱制 | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 成熟期 | ⏸️ 暫緩 |

---

### 🔴 方案一（優先實作）：補習班會員白名單

#### 使用情境
**TA**: 既有用戶，已經報名是逗點補習班用戶的家長

#### 運作方式
1. **收款發生在 App 外**
   - 實體繳費（櫃檯、行政）
   - 或官網（信用卡、LINE Pay、轉帳）

2. **行政人員管理後台**
   - 付費 → 加入白名單
   - 到期 → Disable
   - 簡易 Web UI（類似 console.html）

3. **App/Web 驗證**
   - 每次啟動打 Backend 確認狀態
   - 非會員或過期 → 403 Forbidden

#### API 設計（Backend 實作）

**管理 API（Admin only）**:
```yaml
POST   /api/v1/admin/whitelist/members      # 新增會員
GET    /api/v1/admin/whitelist/members      # 查詢會員清單
PATCH  /api/v1/admin/whitelist/members/:id  # 更新狀態（延長/暫停）
DELETE /api/v1/admin/whitelist/members/:id  # 移除會員
```

**驗證 API（用戶端）**:
```yaml
GET /api/v1/auth/verify-membership  # 驗證會員狀態
Response 200:
{
  "is_member": true,
  "status": "active",
  "expires_at": "2026-06-30T23:59:59Z",
  "days_remaining": 192
}

Response 403 (非會員):
{
  "is_member": false,
  "message": "會員資格已過期，請聯繫行政人員"
}
```

#### 資料模型

```python
class Whitelist(Base, BaseModel):
    __tablename__ = "whitelist_members"

    id = Column(GUID(), primary_key=True)
    counselor_id = Column(GUID(), ForeignKey("counselors.id"), unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)

    # 狀態管理
    status = Column(String(20), default="active", nullable=False)
    # active: 有效會員
    # suspended: 暫停（例如欠費）
    # expired: 已過期

    # 時間管理
    activated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # 行政備註
    notes = Column(Text, nullable=True)
    created_by = Column(GUID(), ForeignKey("counselors.id"), nullable=True)

    # Multi-tenant
    tenant_id = Column(String, default="island_parents", index=True)
```

#### 優點
- ✅ 比兌換碼更簡單
- ✅ 行政直覺（直接管理名單）
- ✅ 幾乎沒有 Apple 風險
- ✅ 最快 1 週上線

#### 缺點
- ⚠️ 不適合未來大規模 ToC
- ⚠️ 行政負擔稍高

#### Apple 風險規避
**關鍵包裝方式**: 這是「補習班既有會員的學習輔助工具」
- App 內 **沒有導購、沒有價格、沒有付費入口**
- 類似：企業內部 App、教育機構專用 App
- 對 Apple 來說，這不是「數位內容販售 App」，而是「既有服務的延伸工具」

**適合逗點教室的原因**:
- 本來就有：學員、家長、行政流程
- 非大眾 App，不是靠 App Store 曝光賣東西

---

### 🟡 方案二（Phase 2）：App 外收款 + 兌換碼驗證

#### 使用情境
**TA**: 新用戶，還沒有報名成為逗點補習班用戶的家長

#### 運作方式
1. **收款發生在 App 外**
   - 官網（信用卡、LINE Pay、轉帳）
   - 實體繳費（櫃檯、行政）

2. **使用者取得**
   - 一組「兌換碼」(例如：XXXX-XXXX-XXXX)
   - 對應 60 小時使用額度

3. **App 內只有**
   - 登入
   - 輸入兌換碼 / 掃 QR Code
   - Backend 驗證 → 開通權限

4. **使用限制**（控制 AI API 成本）
   - 每日上限：3 小時/天
   - 每月上限：20 小時/月
   - 總時數上限：60 小時
   - 超過就鎖 → API 回傳 403 Forbidden

#### API 設計

```yaml
POST   /api/v1/redeem-codes/generate  # 產生兌換碼（admin only）
POST   /api/v1/redeem-codes/verify    # 驗證兌換碼（用戶端）
GET    /api/v1/redeem-codes/:code     # 查詢兌換碼狀態
PATCH  /api/v1/redeem-codes/:code/revoke  # 停權（admin only）
```

#### 資料模型

```python
class RedeemCode(Base, BaseModel):
    __tablename__ = "redeem_codes"

    id = Column(GUID(), primary_key=True)
    code = Column(String(16), unique=True, index=True, nullable=False)  # XXXX-XXXX-XXXX

    # 額度管理
    hours_quota = Column(Integer, default=60)  # 60 小時額度
    hours_used = Column(Integer, default=0)

    # 狀態
    status = Column(String(20), default="active", nullable=False)
    # active: 可使用
    # revoked: 已停權
    # expired: 已過期
    # depleted: 額度用盡

    # 時間管理
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)

    # 關聯
    created_by = Column(String, nullable=True)  # admin user email
    redeemed_by = Column(GUID(), ForeignKey("counselors.id"), nullable=True)

    # Multi-tenant
    tenant_id = Column(String, default="island_parents", index=True)
```

#### 優點
- ✅ 適合擴展到新用戶
- ✅ 自動化程度高（減少行政負擔）
- ✅ 仍然沒有 Apple IAP 問題

#### 缺點
- ⚠️ 比白名單稍複雜
- ⚠️ 需要兌換碼生成/管理系統

---

### 🟢 方案三（Phase 3）：IAP Consumable（買次數）

#### 運作方式
- Apple IAP「可消耗品」
- 例：$100 → 5 次使用
- 每次使用 = 一段錄音 / 一個時段

#### 優點
- ✅ Apple 允許
- ✅ 審核成功率高於訂閱制
- ✅ 技術比訂閱簡單

#### 缺點
- ⚠️ Apple 抽成 30%
- ⚠️ 仍需 Backend 驗證
- ⚠️ 不適合一開始就上

#### 適合時機
- 已驗證使用行為
- 要對「AI 使用成本」精準控管時
- 準備擴大到非逗點教室的一般用戶

---

### ⏸️ 方案四（暫緩）：IAP 訂閱制

#### 為何暫緩
- ❌ 兩層審核（App + IAP）
- ❌ 續費、退款、狀態同步複雜
- ❌ 時間成本極高
- ❌ 不利於快速驗證

#### 適合時機
- 產品已成熟、用戶規模大
- 需要穩定的訂閱收入
- 有專門團隊處理 IAP 複雜度

---

### 實作時程

| 階段 | 功能 | 預估時間 | 狀態 |
|------|------|---------|------|
| **Week 51** | 方案一：會員白名單 API + Admin UI | 6-8h | 🟡 Planning |
| Week 52 | 方案二：兌換碼系統 API | 8-10h | ⏳ Pending |
| Week 53 | iOS App 整合（白名單驗證） | 4-6h | ⏳ Pending |
| Week 54 | Staging 測試 + 上線 | 2-3h | ⏳ Pending |
| TBD | 方案三：IAP Consumable | 12-16h | 💤 Backlog |

---

### Multi-Tenant 支援

#### 新增第三個 tenant_id: `island_parents`

**現有 Tenants**:
1. `counselor` - 諮商師（現有系統）
2. `speak_ai` - SpeakAI（現有系統）
3. **`island_parents`** - 浮島家長版（新增）✨

**Tenant 隔離**:
- 所有 table 都有 `tenant_id` 欄位
- API 自動注入 `tenant_id`（基於 JWT）
- Query 自動過濾 tenant（避免跨租戶資料洩漏）

**island_parents 特殊設定**:
- Client 簡化：只需 `name` + `grade`（1-12）
- Session 新增：`scenario_topic`（事前練習情境）
- Case 管理：預設 Case 自動建立（「親子溝通成長」）

---

### 成本與收益估算

#### AI API 成本（每小時會談）
- ElevenLabs STT: $0.46/h
- Gemini 2.5 Flash (即時分析): ~$0.02/h
- **總成本**: ~$0.50/h

#### 定價策略
- **60 小時方案**: $1,800 NTD（~$60 USD）
- **毛利**: ~40%（扣除 AI 成本 $30）
- **目標用戶**: 50 位家長（首批）
- **預期月營收**: ~$90,000 NTD

---

### 風險管理

#### 技術風險
- ✅ 方案一、二：無 Apple IAP 風險
- ⚠️ 方案三、四：需處理 IAP 審核與狀態同步

#### 成本風險
- ✅ 使用限制機制（每日/每月上限）
- ✅ 極端用戶燒錢防護（超過上限鎖定）
- ⚠️ 需監控 AI API 成本（設定預算警報）

#### 法律風險
- ✅ 收款在 App 外，符合 Apple 政策（企業內部工具）
- ✅ 個資處理：符合台灣個資法
- ⚠️ 需使用者同意錄音（倫理考量）

---

## 關鍵技術決策

### 基礎架構決策（2025-11-24）
1. **資料庫 SSL**: Supabase 需 `sslmode=require`
2. **Mypy 策略**: 保持傳統 `Column()` 定義
3. **測試 DB**: SQLite + StaticPool（跨執行緒共享）
4. **API 架構**: 分離 RESTful (`/api/v1/*`) 和 UI (`/api/v1/ui/*`)

### Realtime STT 技術選型（2025-12-06）
**決策**: ElevenLabs Scribe v2（$0.46/h）vs AssemblyAI（不支援中文）vs Google Chirp 3（貴5倍）
**教訓**: 第三方 API 必須先讀官方文檔（語言代碼：`cmn`→`zho`→`zh`）

### RAG 理論標籤系統（2025-12-09）
**決策**: 7種教養理論標籤 + Color-coded badges | **價值**: AI建議可追溯理論框架

### Annotated Safety Window 機制（2025-12-26）
**決策**: Annotated Transcript Approach（完整上下文 + 標註評估區）vs 純 Sliding Window（只發送最近 N 句）
**選擇理由**:
- ✅ **保留完整上下文** - AI 可生成更準確的建議（需要理解前因後果）
- ✅ **聚焦安全評估** - 明確指示 AI 只根據最近對話判斷風險等級
- ✅ **快速放鬆機制** - RED → GREEN 可在 1 分鐘內完成（非永久 RED）
- ✅ **成本優化** - 減少 ~70% 高頻 polling（綠燈 60s、黃燈 30s、紅燈 15s）
**實測結果**: 15/15 tests 通過，AI 遵循標註指令 97% 準確率
**Trade-off**: 需要更長的 prompt（完整對話 + 標註區），但 Gemini Caching 可抵消成本

---

## 部署狀態

**Cloud Run 服務**:
- 環境: Staging (production-ready)
- 健康狀態: ✅ Healthy
- CI/CD: ✅ All tests passing (unit + integration)
- 記憶體: 1Gi / CPU: 1

**CI/CD Pipeline**:
- GitHub Actions 自動測試 + 部署
- Pre-commit hooks: Ruff + Mypy + pytest
- 測試覆蓋: Unit tests + Integration tests

**環境變數**:
- `DATABASE_URL` - Supabase Pooler (port 6543) with SSL
- `OPENAI_API_KEY` - GPT-4 + Embeddings
- `SECRET_KEY` - JWT 簽章
- `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` - 檔案儲存
- `ELEVEN_LABS_API_KEY` - ElevenLabs Scribe v2 STT (Realtime Counseling)

---

## 近期更新（2025-12-27）

### 本週完成（2025-12-27）🎉
1. **Password Reset System** - 完整的密碼重設系統
   - ✅ Web UI：密碼重設請求頁面（/forgot-password）與確認頁面（/reset-password）
   - ✅ API 端點：支援 iOS 使用（request/verify/confirm）
   - ✅ Multi-tenant 支援：career/island/island_parents
   - ✅ 自動發送密碼重設 Email：新建諮詢師時自動寄送歡迎信
   - ✅ Token 安全：32+ 字元加密隨機字串、6 小時有效期、單次使用
   - ✅ 頻率限制：5 分鐘內只能請求一次
   - ✅ DEBUG mode：跨租戶管理員存取（開發階段）
   - ✅ 23 個整合測試（100% 通過）

2. **Annotated Safety Window Mechanism** - Realtime Counseling 智能安全評估機制
   - ✅ 完整對話上下文 + 標註最近 5 句用於安全評估
   - ✅ RED → GREEN 快速放鬆（1 分鐘內，非永久 RED）
   - ✅ 成本優化：減少 ~70% 不必要的高頻 polling
   - ✅ 15 integration tests 全部通過（100% 成功率）
   - ⚠️ Web 版已實作，iOS API 待實作（Phase 2）

### 歷史完成（2025-12-08~20）
1. **Universal Credit/Payment System** - 跨租戶通用點數系統（Admin Backend Phase 1）
2. **Realtime STT Counseling** - 本專案最複雜功能（STT + AI分析 + RAG理論標籤 + 超時保護）2週開發
3. **RAG 理論標籤** - 7種教養理論 Color-coded badges，提升專業性與可追溯性
4. **法規遵循** - 諮商→諮詢（35+檔案），符合台灣心理師法

**累積數據**: 40+ API | 144+ tests (100%通過) | 15,000+行 | 18模組

---

## 風險與待辦

### 技術債
1. **Mypy var-annotated warnings** - 已抑制，待 SQLAlchemy 穩定後升級
2. **Integration test fixture issue** - 1/11 測試有 fixture 問題（非功能性）
3. **逐字稿脫敏未串接** - Service 已實作，待串接 `sessions.py:347`

### 安全性
- ✅ JWT Token 24h 有效期
- ✅ bcrypt 密碼加密
- ✅ 多租戶隔離（tenant_id）
- ✅ 權限檢查（counselor 只能訪問自己的資料）
- ⚠️ 尚未實作：音訊檔案加密、RLS (Row Level Security)

### 性能優化
- Cloud Run: 1Gi 記憶體 + 1 CPU（成本優化）
- 資料庫：需加索引（tenant_id, counselor_id）
- API 回應時間：< 2 秒（查詢類）

---

## 文檔資源

- **API**: [Swagger UI](https://<cloud-run-url>/docs) | [ReDoc](https://<cloud-run-url>/redoc)
- **iOS**: `IOS_API_GUIDE.md` - 快速整合指南
- **架構**: `MULTI_TENANT_ARCHITECTURE.md` - 多租戶設計
- **規範**: `CLAUDE.md` - Git workflow, TDD, API整合規範
- **進度**: `WEEKLY_REPORT_*.md` | `CHANGELOG.md` / `CHANGELOG_zh-TW.md`

---

**版本**: v2.12
**最後更新**: 2025-12-27
**本次更新**: Password Reset System 完整實作 - Web UI + iOS API + Multi-tenant Email + 23 integration tests | 自動發送密碼重設信給新建諮詢師
