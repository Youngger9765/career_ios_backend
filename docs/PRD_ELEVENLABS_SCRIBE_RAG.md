# PRD: Eleven Labs Scribe v2 + RAG 整合

**版本**: v1.0
**最後更新**: 2025-12-07
**狀態**: Planning
**負責人**: Backend Team

---

## 目錄
- [1. 產品概述](#1-產品概述)
- [2. 目標與成功指標](#2-目標與成功指標)
- [3. 功能需求](#3-功能需求)
- [4. 技術架構](#4-技術架構)
- [5. API 設計](#5-api-設計)
- [6. 資料模型](#6-資料模型)
- [7. 實作計劃](#7-實作計劃)
- [8. 風險與挑戰](#8-風險與挑戰)
- [9. 測試策略](#9-測試策略)

---

## 1. 產品概述

### 1.1 背景

**當前痛點**:
- 諮商師需等待會談結束才能取得逐字稿
- 即時互動缺乏 AI 智慧回應
- 無法在會談中即時查詢職涯知識庫
- 諮商效率受限於人工記憶與經驗

**解決方案**:
整合 Eleven Labs Scribe v2 實時轉錄 API 與 RAG 知識庫，打造**即時 AI 輔助諮商系統**

### 1.2 核心價值

```
即時轉錄 (Scribe v2) → 語意理解 (RAG) → 智慧建議 (LLM)
```

**對諮商師**:
- ✅ 即時取得會談逐字稿
- ✅ AI 提供職涯知識建議
- ✅ 自動標記關鍵議題
- ✅ 會談後報告自動生成

**對案主**:
- ✅ 更精準的職涯建議
- ✅ 諮商師能專注傾聽（AI 輔助記錄）
- ✅ 更快取得會談報告

### 1.3 產品定位

**不是**: 取代諮商師的自動回答機器人
**而是**: 即時輔助諮商師的智能助手

---

## 2. 目標與成功指標

### 2.1 業務目標

| 目標 | 指標 | 基準 | 目標值 |
|------|------|------|--------|
| **提升諮商效率** | 報告生成時間 | 人工 30 分鐘 | AI 輔助 < 5 分鐘 |
| **改善諮商品質** | 知識引用準確率 | - | > 85% |
| **增加諮商頻次** | 每日可接案量 | 4 案/天 | 6 案/天 (+50%) |
| **降低諮商師負擔** | 手動記錄時間 | 15 分鐘/會談 | < 2 分鐘/會談 |

### 2.2 技術目標

| 目標 | 指標 | 目標值 |
|------|------|--------|
| **即時性** | 轉錄延遲 | < 2 秒 |
| **準確性** | 轉錄 WER | < 5% |
| **RAG 回應速度** | P95 延遲 | < 3 秒 |
| **系統穩定性** | 可用性 | > 99.5% |
| **成本控制** | 每會談成本 | < $2 USD |

---

## 3. 功能需求

### 3.1 核心功能

#### F1: 即時轉錄 (Scribe v2)

**使用者故事**:
> 作為諮商師，我希望在會談進行時即時看到逐字稿，以便專注傾聽而非記錄

**功能描述**:
- WebSocket 連接 Eleven Labs Scribe v2 API
- 支援中文+英文混合語音
- 即時回傳轉錄文本（< 2 秒延遲）
- 自動偵測說話者（Speaker Diarization）
- 支援斷線重連與錯誤恢復

**技術規格**:
```yaml
Input: Audio stream (16kHz, mono, PCM)
Output:
  - transcript: str (即時文本)
  - speaker: str (說話者 ID)
  - timestamp: float (時間戳)
  - is_final: bool (是否為最終版本)
```

**驗收標準**:
- [ ] 轉錄準確率 > 95%（中文）
- [ ] 延遲 < 2 秒
- [ ] 支援 60 分鐘連續會談
- [ ] 斷線後 5 秒內自動重連

---

#### F2: RAG 知識庫查詢

**使用者故事**:
> 作為諮商師，當案主提到「轉職」或「職涯規劃」時，我希望 AI 自動提供相關職涯文章建議

**功能描述**:
- 即時分析逐字稿語意
- 觸發條件：偵測到關鍵詞（轉職、履歷、面試...）
- 查詢 RAG 知識庫（職遊文章 + 職涯理論）
- 回傳 Top-3 相關知識片段

**技術規格**:
```yaml
Input:
  - transcript_segment: str (最近 5 句話)
  - keywords: List[str] (關鍵字)
Output:
  - results: List[RAGResult]
    - content: str (知識片段)
    - source: str (來源文章)
    - relevance_score: float (相關性分數)
```

**驗收標準**:
- [ ] 查詢延遲 < 1 秒
- [ ] Top-1 結果相關性 > 0.7
- [ ] 支援繁體中文語意理解

---

#### F3: AI 智慧建議生成

**使用者故事**:
> 作為諮商師，我希望 AI 根據會談內容自動生成建議，讓我可以參考或修改

**功能描述**:
- 結合逐字稿 + RAG 知識庫結果
- 使用 GPT-4 生成建議（提問方向、職涯資源）
- 以卡片形式即時顯示在諮商師介面
- 諮商師可選擇性採用或忽略

**技術規格**:
```yaml
Input:
  - transcript: str (會談逐字稿)
  - rag_context: List[RAGResult] (知識庫結果)
  - counselor_notes: str (諮商師筆記，可選)
Output:
  - suggestions: List[Suggestion]
    - type: enum (question | resource | insight)
    - content: str (建議內容)
    - confidence: float (信心分數)
    - source: str (來源依據)
```

**驗收標準**:
- [ ] 建議生成延遲 < 3 秒
- [ ] 諮商師採用率 > 30%
- [ ] 無關建議率 < 10%

---

#### F4: 會談後報告自動生成

**使用者故事**:
> 作為諮商師，會談結束後我希望 AI 自動生成摘要報告，節省我的整理時間

**功能描述**:
- 基於完整逐字稿 + RAG 知識庫
- 生成結構化報告（主訴、議題、建議、資源）
- 支援 Markdown 格式編輯
- 與現有報告系統整合

**技術規格**:
```yaml
Input:
  - session_id: UUID
  - full_transcript: str (完整逐字稿)
  - keywords: List[str] (關鍵字分析結果)
Output:
  - report: Report
    - summary: str (會談摘要)
    - key_issues: List[str] (關鍵議題)
    - recommendations: List[str] (建議事項)
    - resources: List[RAGResult] (推薦資源)
```

**驗收標準**:
- [ ] 報告生成時間 < 30 秒
- [ ] 關鍵議題識別準確率 > 80%
- [ ] 諮商師滿意度 > 4/5

---

### 3.2 非功能需求

#### 性能
- API 回應時間 P95 < 3 秒
- WebSocket 支援 100+ 並發連線
- RAG 查詢支援 10 QPS/session

#### 可靠性
- 系統可用性 > 99.5%
- 音訊串流斷線自動重連
- 失敗重試機制（Exponential backoff）

#### 安全性
- 音訊串流加密（TLS 1.3）
- 逐字稿儲存加密（AES-256）
- 符合 GDPR 資料保護（30 天自動刪除）

#### 成本
- Scribe API 成本 < $1.5/會談
- GPT-4 成本 < $0.5/會談
- 總成本 < $2/會談

---

## 4. 技術架構

### 4.1 系統架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                         iOS App                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Audio Input  │→ │ WebSocket    │→ │ Transcript   │      │
│  │ (麥克風)      │  │ Connection   │  │ Display      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│           ↓                ↑                  ↑              │
└───────────│────────────────│──────────────────│──────────────┘
            │                │                  │
            │ Audio Stream   │ Transcript +     │ AI Suggestions
            ↓                │ Suggestions      │
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         WebSocket Manager (Real-time Service)          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ Scribe v2    │→ │ RAG Query    │→ │ LLM Suggest  │ │ │
│  │  │ Connector    │  │ Service      │  │ Service      │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│           │                  │                  │            │
│           ↓                  ↓                  ↓            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Session DB   │  │ RAG Vector   │  │ OpenAI GPT-4 │      │
│  │ (Postgres)   │  │ DB (pgvector)│  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
            │                  │
            ↓                  ↓
┌─────────────────────────────────────────────────────────────┐
│                  External Services                           │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │ Eleven Labs  │                    │ OpenAI API   │       │
│  │ Scribe v2    │                    │ (GPT-4)      │       │
│  └──────────────┘                    └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 資料流

**會談進行中**:
```
1. iOS → Backend: Audio stream (WebSocket)
2. Backend → Scribe v2: Audio forwarding
3. Scribe v2 → Backend: Transcript segments
4. Backend → RAG DB: Semantic query (if keywords detected)
5. Backend → GPT-4: Generate suggestions (with RAG context)
6. Backend → iOS: Transcript + Suggestions (WebSocket)
```

**會談結束後**:
```
1. iOS → Backend: POST /api/v1/sessions/{id}/finalize
2. Backend: Trigger report generation (Background Task)
3. Backend → RAG DB: Query full context
4. Backend → GPT-4: Generate structured report
5. Backend → DB: Save report (status: draft)
6. Backend → iOS: Report ready notification
```

### 4.3 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| **即時通訊** | FastAPI WebSocket | 音訊串流與轉錄傳輸 |
| **語音轉文字** | Eleven Labs Scribe v2 API | 即時 STT |
| **語意理解** | Vertex AI Embeddings | 文本向量化 |
| **知識檢索** | pgvector (Supabase) | 向量相似度搜尋 |
| **AI 生成** | GPT-4 Turbo | 建議與報告生成 |
| **任務佇列** | FastAPI BackgroundTasks | 異步報告生成 |
| **資料庫** | PostgreSQL 15 | Session、Transcript 儲存 |

---

## 5. API 設計

### 5.1 WebSocket API

#### `WS /api/v1/realtime/session/{session_id}`

**描述**: 即時會談 WebSocket 連線

**認證**: JWT Token (query param: `?token=xxx`)

**Client → Server 訊息格式**:
```json
{
  "type": "audio_chunk",
  "data": {
    "audio": "base64_encoded_pcm_data",
    "timestamp": 1234567890.123
  }
}
```

**Server → Client 訊息格式**:

1. **轉錄結果**:
```json
{
  "type": "transcript",
  "data": {
    "text": "我最近在考慮轉職...",
    "speaker": "client",
    "timestamp": 1234567890.123,
    "is_final": true
  }
}
```

2. **AI 建議**:
```json
{
  "type": "suggestion",
  "data": {
    "id": "sugg_123",
    "suggestion_type": "question",
    "content": "您可以進一步詢問案主：『轉職的主要動機是什麼？』",
    "confidence": 0.85,
    "rag_sources": [
      {
        "title": "如何規劃轉職策略",
        "url": "https://...",
        "snippet": "轉職前應先釐清..."
      }
    ]
  }
}
```

3. **系統事件**:
```json
{
  "type": "system",
  "event": "connection_ready" | "scribe_connected" | "error",
  "message": "連線成功，可以開始會談"
}
```

---

### 5.2 REST API

#### `POST /api/v1/realtime/sessions`

**描述**: 建立即時會談 Session

**Request**:
```json
{
  "case_id": "uuid",
  "name": "第 3 次會談",
  "enable_realtime": true,
  "language": "zh-TW"
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "websocket_url": "wss://api.example.com/api/v1/realtime/session/{id}",
  "token": "jwt_token_for_websocket",
  "expires_at": "2025-12-07T15:30:00Z"
}
```

---

#### `POST /api/v1/realtime/sessions/{id}/finalize`

**描述**: 結束會談並觸發報告生成

**Request**:
```json
{
  "counselor_notes": "案主主要關注轉職方向...",
  "generate_report": true
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "status": "completed",
  "transcript_url": "/api/v1/sessions/{id}/transcript",
  "report_generation_status": "processing",
  "estimated_completion": "2025-12-07T14:05:00Z"
}
```

---

#### `GET /api/v1/realtime/sessions/{id}/transcript`

**描述**: 取得完整逐字稿

**Response**:
```json
{
  "session_id": "uuid",
  "transcript": [
    {
      "speaker": "counselor",
      "text": "今天想聊什麼呢？",
      "timestamp": 0.0
    },
    {
      "speaker": "client",
      "text": "我最近在考慮轉職...",
      "timestamp": 3.5
    }
  ],
  "duration_seconds": 3600,
  "word_count": 5420
}
```

---

#### `GET /api/v1/realtime/sessions/{id}/suggestions`

**描述**: 取得會談中的 AI 建議歷史

**Response**:
```json
{
  "suggestions": [
    {
      "id": "sugg_123",
      "timestamp": 1234567890.123,
      "type": "question",
      "content": "...",
      "counselor_action": "accepted" | "rejected" | "ignored"
    }
  ],
  "total": 15,
  "acceptance_rate": 0.4
}
```

---

## 6. 資料模型

### 6.1 RealtimeSession (新增)

```python
class RealtimeSession(Base):
    __tablename__ = "realtime_sessions"

    id: UUID = Column(UUID, primary_key=True)
    session_id: UUID = Column(UUID, ForeignKey("sessions.id"))

    # Scribe v2 設定
    scribe_session_id: str = Column(String)
    language: str = Column(String, default="zh-TW")

    # 狀態
    status: str = Column(String)  # active | completed | failed
    started_at: datetime = Column(DateTime)
    ended_at: datetime = Column(DateTime, nullable=True)

    # 連線資訊
    websocket_url: str = Column(String)
    connection_token: str = Column(String)

    # 統計
    duration_seconds: int = Column(Integer, default=0)
    transcript_word_count: int = Column(Integer, default=0)
    suggestions_generated: int = Column(Integer, default=0)
```

### 6.2 TranscriptSegment (新增)

```python
class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: UUID = Column(UUID, primary_key=True)
    realtime_session_id: UUID = Column(UUID, ForeignKey("realtime_sessions.id"))

    # 轉錄內容
    text: str = Column(Text)
    speaker: str = Column(String)  # counselor | client
    timestamp: float = Column(Float)
    is_final: bool = Column(Boolean, default=False)

    # 語音資訊
    confidence: float = Column(Float, nullable=True)
    language: str = Column(String, nullable=True)

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

### 6.3 AISuggestion (新增)

```python
class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: UUID = Column(UUID, primary_key=True)
    realtime_session_id: UUID = Column(UUID, ForeignKey("realtime_sessions.id"))

    # 建議內容
    suggestion_type: str = Column(String)  # question | resource | insight
    content: str = Column(Text)
    confidence: float = Column(Float)

    # RAG 來源
    rag_sources: JSONB = Column(JSONB, default=[])

    # 諮商師反饋
    counselor_action: str = Column(String, nullable=True)  # accepted | rejected | ignored
    counselor_feedback: str = Column(Text, nullable=True)

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

### 6.4 Sessions 表更新

```python
# 新增欄位到現有 sessions 表
class Session(Base):
    # ... 現有欄位 ...

    # 新增即時會談支援
    has_realtime: bool = Column(Boolean, default=False)
    realtime_transcript: JSONB = Column(JSONB, nullable=True)  # 完整逐字稿
    ai_suggestions_count: int = Column(Integer, default=0)
```

---

## 7. 實作計劃

### 7.1 Phase 1: 基礎架構 (Week 1-2)

**目標**: 建立 WebSocket 連線 + Scribe v2 整合

**任務**:
- [ ] WebSocket Manager 實作（FastAPI）
- [ ] Eleven Labs Scribe v2 API 整合
- [ ] 音訊串流 Proxy（iOS → Backend → Scribe）
- [ ] 即時轉錄結果儲存
- [ ] 資料庫 Migration（新增 3 張表）

**驗收**:
- [ ] WebSocket 連線穩定（60 分鐘無斷線）
- [ ] 轉錄延遲 < 2 秒
- [ ] Integration tests: WebSocket + Scribe API

**TDD 流程**:
```bash
# 1. 寫測試
poetry run pytest tests/integration/test_realtime_websocket.py -v  # RED

# 2. 實作功能
# - app/services/realtime_service.py
# - app/api/v1/realtime.py

# 3. 測試通過
poetry run pytest tests/integration/test_realtime_websocket.py -v  # GREEN

# 4. Refactor
```

---

### 7.2 Phase 2: RAG 整合 (Week 3)

**目標**: 即時語意分析 + 知識庫查詢

**任務**:
- [ ] 關鍵字偵測服務（重用 KeywordAnalysisService）
- [ ] RAG Query Service 整合
- [ ] 語意觸發規則引擎（配置化）
- [ ] RAG 結果快取（Redis，可選）

**驗收**:
- [ ] 關鍵字偵測準確率 > 80%
- [ ] RAG 查詢延遲 < 1 秒
- [ ] Integration tests: Keyword detection + RAG query

**TDD 流程**:
```bash
poetry run pytest tests/integration/test_realtime_rag.py -v
```

---

### 7.3 Phase 3: AI 建議生成 (Week 4)

**目標**: GPT-4 生成即時建議

**任務**:
- [ ] SuggestionService 實作
- [ ] Prompt Engineering（建議生成）
- [ ] 建議評分與過濾機制
- [ ] WebSocket 推送 AI 建議

**驗收**:
- [ ] 建議生成延遲 < 3 秒
- [ ] 無關建議率 < 10%
- [ ] Integration tests: End-to-end suggestion flow

**TDD 流程**:
```bash
poetry run pytest tests/integration/test_ai_suggestions.py -v
```

---

### 7.4 Phase 4: 報告生成整合 (Week 5)

**目標**: 會談後自動報告

**任務**:
- [ ] 整合現有 ReportService
- [ ] 逐字稿格式化（speaker diarization）
- [ ] 報告模板優化（加入 RAG 來源引用）
- [ ] Background Task 優化

**驗收**:
- [ ] 報告生成時間 < 30 秒
- [ ] 報告品質評分 > 4/5（人工評估）
- [ ] Integration tests: Report generation from realtime session

---

### 7.5 Phase 5: iOS 整合 (Week 6)

**目標**: iOS App 介面整合

**任務**:
- [ ] iOS WebSocket Client 實作
- [ ] 音訊串流處理（AVAudioEngine）
- [ ] UI 設計（逐字稿顯示 + 建議卡片）
- [ ] 錯誤處理與重連機制

**驗收**:
- [ ] iOS App 穩定運行 60 分鐘會談
- [ ] UI 回應流暢（60 FPS）
- [ ] Beta 測試通過（5 位諮商師）

---

### 7.6 Phase 6: 優化與上線 (Week 7-8)

**目標**: 性能優化 + 正式上線

**任務**:
- [ ] 成本優化（API 調用策略）
- [ ] 監控與告警（Datadog / Sentry）
- [ ] 負載測試（100 並發）
- [ ] 文檔與培訓

**驗收**:
- [ ] 成本 < $2/會談
- [ ] P95 延遲 < 3 秒
- [ ] 可用性 > 99.5%

---

## 8. 風險與挑戰

### 8.1 技術風險

| 風險 | 影響 | 機率 | 緩解策略 |
|------|------|------|----------|
| **Scribe v2 中文準確率不足** | 高 | 中 | 1. 先用 Whisper 作 POC<br>2. 準備 Fallback 方案（Google STT） |
| **WebSocket 連線不穩定** | 高 | 中 | 1. 實作自動重連<br>2. 本地暫存音訊<br>3. 斷點續傳 |
| **RAG 查詢延遲過高** | 中 | 低 | 1. 向量索引優化（HNSW）<br>2. 快取熱門查詢<br>3. 異步查詢 |
| **GPT-4 成本超標** | 中 | 中 | 1. 使用 GPT-4-mini<br>2. 限制 Token 長度<br>3. 批次處理 |
| **並發連線數限制** | 低 | 低 | 1. Cloud Run 自動擴展<br>2. WebSocket 連線池 |

### 8.2 業務風險

| 風險 | 影響 | 機率 | 緩解策略 |
|------|------|------|----------|
| **諮商師不信任 AI 建議** | 高 | 中 | 1. 強調「輔助」非「取代」<br>2. 提供建議來源追溯<br>3. 使用者培訓 |
| **案主隱私疑慮** | 高 | 中 | 1. 明確告知資料使用<br>2. 30 天自動刪除<br>3. 符合 GDPR |
| **功能過於複雜** | 中 | 中 | 1. MVP 先做核心功能<br>2. 逐步迭代<br>3. 使用者研究 |

### 8.3 時程風險

| 風險 | 影響 | 機率 | 緩解策略 |
|------|------|------|----------|
| **8 週時程過於樂觀** | 中 | 高 | 1. 保留 2 週 Buffer<br>2. 每週 Review<br>3. 縮減 MVP 範圍 |
| **依賴第三方 API 延遲** | 中 | 中 | 1. 提早測試 API<br>2. 準備 Fallback |

---

## 9. 測試策略

### 9.1 TDD 原則

**所有關鍵功能必須先寫測試**:
- ✅ WebSocket 連線
- ✅ Scribe v2 整合
- ✅ RAG 查詢
- ✅ AI 建議生成
- ✅ 報告生成

### 9.2 測試類型

#### Unit Tests
```python
# tests/unit/test_realtime_service.py
def test_keyword_detection():
    service = RealtimeService()
    text = "我想轉職，但不知道履歷怎麼寫"
    keywords = service.detect_keywords(text)
    assert "轉職" in keywords
    assert "履歷" in keywords

def test_transcript_formatting():
    segments = [...]
    formatted = RealtimeService.format_transcript(segments)
    assert "諮商師:" in formatted
    assert "案主:" in formatted
```

#### Integration Tests
```python
# tests/integration/test_realtime_flow.py
async def test_end_to_end_realtime_session():
    # 1. 建立 Session
    response = client.post("/api/v1/realtime/sessions", json={...})

    # 2. WebSocket 連線
    async with websocket_connect(ws_url) as ws:
        # 3. 發送音訊
        await ws.send_json({"type": "audio_chunk", ...})

        # 4. 接收轉錄
        msg = await ws.receive_json()
        assert msg["type"] == "transcript"

        # 5. 接收 AI 建議
        msg = await ws.receive_json()
        assert msg["type"] == "suggestion"
```

#### Load Tests
```python
# tests/load/test_websocket_concurrency.py
async def test_100_concurrent_sessions():
    """模擬 100 個同時進行的會談"""
    tasks = [simulate_session() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    assert all(r.status == "success" for r in results)
```

### 9.3 測試覆蓋率目標

| 模組 | 目標覆蓋率 |
|------|-----------|
| WebSocket Manager | > 90% |
| Scribe Service | > 85% |
| RAG Service | > 90% |
| Suggestion Service | > 85% |
| API Endpoints | > 90% |

---

## 10. 成功標準

### 10.1 MVP 上線標準

**技術指標**:
- [ ] 轉錄準確率 > 90%
- [ ] 系統延遲 P95 < 3 秒
- [ ] 測試覆蓋率 > 85%
- [ ] 可用性 > 99%（1 週監控）

**業務指標**:
- [ ] 5 位諮商師完成 Beta 測試
- [ ] 每位完成 3+ 場會談
- [ ] 滿意度 > 4/5
- [ ] 無 P0/P1 Bug

### 10.2 正式上線後指標

**第 1 個月**:
- [ ] 30+ 場會談使用即時功能
- [ ] AI 建議採用率 > 20%
- [ ] 報告生成時間減少 > 70%

**第 3 個月**:
- [ ] 100+ 場會談
- [ ] AI 建議採用率 > 30%
- [ ] 諮商師每日接案量 +30%

---

## 附錄

### A. Eleven Labs Scribe v2 API 文件
- 官方文檔: https://elevenlabs.io/docs/api-reference/scribe
- WebSocket 端點: `wss://api.elevenlabs.io/v1/scribe`
- 支援語言: zh, en, ja, ko...
- 定價: $0.12/小時

### B. 相關文檔
- **現有 RAG 系統**: `PRD.md` - Section "RAG 系統"
- **會談管理**: `PRD.md` - Section "會談管理"
- **iOS API 指南**: `IOS_API_GUIDE.md`

### C. 參考專案
- OpenAI Realtime API: https://platform.openai.com/docs/guides/realtime
- LiveKit AI Assistant: https://github.com/livekit/agents

---

**核准簽名**:
- [ ] Product Manager: _______________
- [ ] Tech Lead: _______________
- [ ] QA Lead: _______________

**預計開始日期**: 2025-12-10
**預計 MVP 上線**: 2026-02-10 (8 週 + 2 週 Buffer)
