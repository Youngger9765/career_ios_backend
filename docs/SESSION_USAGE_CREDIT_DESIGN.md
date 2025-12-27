# Session 資料結構調整 - DB Log 持久化 + Usage vs Credit 設計

## 🎯 核心問題

### 1. DB Log 持久化
**問題**:
- 當前 `analysis_logs` 存在 Session JSONB 欄位中
- 每次 partial 分析都會新增一筆 log
- JSONB 存取效能差，不適合頻繁寫入和查詢
- 無法建立索引，難以追蹤和分析

**解決方案**:
- ✅ **獨立 `session_analysis_logs` table**
- 每筆分析記錄獨立存儲
- 可建立索引：session_id, created_at, safety_level
- 支援分頁查詢和統計分析

### 2. Usage vs Credit 設計
**問題**:
- 如何追蹤每個 session 的使用量（時間、token、API calls）？
- 何時扣除點數？（實時 vs 結束時）
- 如何記錄扣點歷史？
- 如何處理點數不足？

**設計方案**:

#### Option A: Session 結束時統一扣點（推薦）✅
```
錄音開始 → 累積 usage → 錄音結束 → 計算總點數 → 一次性扣除
```

**優點**:
- 簡單明確
- 避免頻繁 DB 寫入
- 容易回滾（取消/失敗時不扣點）

**缺點**:
- 無法實時監控點數消耗
- 用戶可能超用（先用完再扣點）

#### Option B: 實時累積扣點
```
每次 partial 分析 → 立即扣除該分鐘的點數
```

**優點**:
- 實時監控，點數不足立即停止
- 防止超用

**缺點**:
- 頻繁 DB 寫入（性能問題）
- 複雜度高

---

## 📋 推薦設計（Option A）

### 1. 新增 `session_analysis_logs` Table（DB Log 持久化）

```python
class SessionAnalysisLog(Base, BaseModel):
    """Session 分析記錄（獨立 table）"""
    __tablename__ = "session_analysis_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # 關聯
    session_id = Column(GUID(), ForeignKey("sessions.id"), nullable=False, index=True)
    counselor_id = Column(GUID(), ForeignKey("counselors.id"), nullable=False, index=True)

    # 分析結果
    safety_level = Column(String(20), nullable=False, index=True)  # red, yellow, green
    severity = Column(Integer, nullable=False)  # 1-3
    display_text = Column(Text, nullable=True)
    action_suggestion = Column(Text, nullable=True)

    # RAG 資訊
    rag_documents = Column(JSON, nullable=True)  # 引用的文檔
    rag_sources = Column(JSON, nullable=True)    # 來源標籤

    # 技術指標
    transcript_length = Column(Integer, nullable=True)  # 逐字稿長度（字數）
    duration_seconds = Column(Integer, nullable=True)   # 分析的時間範圍（秒）
    model_used = Column(String(100), nullable=True)     # gemini-2.5-flash

    # Token 使用量
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cached_tokens = Column(Integer, nullable=True)

    # 成本估算
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)

    # 時間戳
    analyzed_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Multi-tenant
    tenant_id = Column(String, nullable=False, index=True)
```

**Migration**:
```sql
CREATE TABLE session_analysis_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    counselor_id UUID NOT NULL REFERENCES counselors(id),

    safety_level VARCHAR(20) NOT NULL,
    severity INTEGER NOT NULL,
    display_text TEXT,
    action_suggestion TEXT,

    rag_documents JSON,
    rag_sources JSON,

    transcript_length INTEGER,
    duration_seconds INTEGER,
    model_used VARCHAR(100),

    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cached_tokens INTEGER,

    estimated_cost_usd NUMERIC(10, 6),

    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    tenant_id VARCHAR(50) NOT NULL
);

CREATE INDEX idx_session_analysis_logs_session_id ON session_analysis_logs(session_id);
CREATE INDEX idx_session_analysis_logs_counselor_id ON session_analysis_logs(counselor_id);
CREATE INDEX idx_session_analysis_logs_safety_level ON session_analysis_logs(safety_level);
CREATE INDEX idx_session_analysis_logs_analyzed_at ON session_analysis_logs(analyzed_at);
CREATE INDEX idx_session_analysis_logs_tenant_id ON session_analysis_logs(tenant_id);
```

---

### 2. 新增 `session_usage` Table（Usage 追蹤）

```python
class SessionUsage(Base, BaseModel):
    """Session 使用量追蹤（一個 session 一筆記錄）"""
    __tablename__ = "session_usage"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # 關聯
    session_id = Column(GUID(), ForeignKey("sessions.id"), unique=True, nullable=False, index=True)
    counselor_id = Column(GUID(), ForeignKey("counselors.id"), nullable=False, index=True)

    # 時間使用量
    duration_seconds = Column(Integer, default=0)  # 錄音總時長
    analysis_count = Column(Integer, default=0)    # 分析次數

    # Token 使用量（累積）
    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cached_tokens = Column(Integer, default=0)

    # 成本估算（累積）
    estimated_cost_usd = Column(Numeric(10, 6), default=0)

    # 點數消耗
    credits_consumed = Column(Integer, default=0)  # 本次 session 消耗的點數
    credit_deducted = Column(Boolean, default=False)  # 是否已扣點
    credit_deducted_at = Column(DateTime(timezone=True), nullable=True)

    # 狀態
    status = Column(String(20), default="in_progress")  # in_progress, completed, failed

    # 時間戳
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Multi-tenant
    tenant_id = Column(String, nullable=False, index=True)
```

**Migration**:
```sql
CREATE TABLE session_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID UNIQUE NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    counselor_id UUID NOT NULL REFERENCES counselors(id),

    duration_seconds INTEGER DEFAULT 0,
    analysis_count INTEGER DEFAULT 0,

    total_prompt_tokens INTEGER DEFAULT 0,
    total_completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cached_tokens INTEGER DEFAULT 0,

    estimated_cost_usd NUMERIC(10, 6) DEFAULT 0,

    credits_consumed INTEGER DEFAULT 0,
    credit_deducted BOOLEAN DEFAULT FALSE,
    credit_deducted_at TIMESTAMP WITH TIME ZONE,

    status VARCHAR(20) DEFAULT 'in_progress',

    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    tenant_id VARCHAR(50) NOT NULL
);

CREATE INDEX idx_session_usage_session_id ON session_usage(session_id);
CREATE INDEX idx_session_usage_counselor_id ON session_usage(counselor_id);
CREATE INDEX idx_session_usage_status ON session_usage(status);
CREATE INDEX idx_session_usage_tenant_id ON session_usage(tenant_id);
```

---

### 3. API Workflow（Usage + Credit）

#### Step 1: Session 開始（Create）
```python
POST /api/v1/island/sessions
{
  "client_id": "uuid",
  "mode": "emergency",
  "started_at": "2025-12-20T10:00:00Z"
}

# Backend 行為:
# 1. 建立 Session
# 2. 建立 SessionUsage (status='in_progress', credits_consumed=0)
# 3. 回傳 session_id
```

#### Step 2: Partial 分析（每分鐘）
```python
POST /api/v1/island/sessions/{session_id}/analyze-partial
{
  "transcript_segment": "最近 60 秒的逐字稿",
  "duration_seconds": 60
}

# Backend 行為:
# 1. 執行即時分析（Gemini + RAG）
# 2. 建立 SessionAnalysisLog（獨立記錄）
# 3. 更新 SessionUsage:
#    - analysis_count += 1
#    - duration_seconds += 60
#    - total_tokens += usage_metadata.total_tokens
#    - estimated_cost_usd += calculated_cost
# 4. ⚠️ 不扣點（累積 usage only）
# 5. 回傳分析結果
```

#### Step 3: Session 結束（Complete）
```python
PATCH /api/v1/island/sessions/{session_id}/complete
{
  "full_transcript": "完整逐字稿",
  "ended_at": "2025-12-20T10:30:00Z"
}

# Backend 行為:
# 1. 更新 Session (status='completed', transcript=full_transcript)
# 2. 更新 SessionUsage (status='completed', completed_at=now)
# 3. 計算點數消耗:
#    - 取得 active credit_rate
#    - credits_consumed = calculate_credits(duration_seconds, rate)
# 4. 扣除點數（CreditBillingService）:
#    - counselor.credits_used += credits_consumed
#    - 建立 CreditLog (transaction_type='session_fee')
# 5. 更新 SessionUsage:
#    - credit_deducted = True
#    - credit_deducted_at = now
# 6. 回傳完成狀態
```

---

### 4. 點數不足處理

#### Option 1: Soft Warning（推薦）
```python
# Session 結束時檢查點數
if counselor.available_credits < credits_consumed:
    # 仍然扣點（可能變負數）
    counselor.credits_used += credits_consumed
    # 記錄 warning
    log_credit_warning(counselor_id, "負點數警告")
    # 通知 admin
    notify_admin_credit_shortage(counselor_id)
```

**優點**: 不中斷服務，後續人工處理

#### Option 2: Hard Block
```python
# 點數不足直接拒絕
if counselor.available_credits < estimated_credits:
    return 403 Forbidden("點數不足，請購買點數")
```

**缺點**: 用戶體驗差

---

## 📊 資料查詢範例

### 1. 查詢某個 Session 的所有分析記錄
```python
GET /api/v1/sessions/{session_id}/analysis-logs
# 從 session_analysis_logs table 查詢
```

### 2. 查詢諮詢師的使用量統計
```python
GET /api/v1/counselors/{counselor_id}/usage-stats?start_date=2025-12-01&end_date=2025-12-31

# Response:
{
  "total_sessions": 45,
  "total_duration_seconds": 135000,  # 37.5 小時
  "total_analysis_count": 2250,
  "total_tokens": 4500000,
  "total_cost_usd": 13.50,
  "total_credits_consumed": 1800
}
```

### 3. 查詢紅黃綠燈分佈
```python
GET /api/v1/sessions/{session_id}/safety-distribution

# Response:
{
  "red_count": 3,
  "yellow_count": 12,
  "green_count": 45,
  "red_percentage": 5.0,
  "yellow_percentage": 20.0,
  "green_percentage": 75.0
}
```

---

## 🎯 Implementation Plan

### Phase 1: DB Schema (Week 52)
- [ ] 建立 `session_analysis_logs` table
- [ ] 建立 `session_usage` table
- [ ] Migration script
- [ ] 5+ integration tests

### Phase 2: API Integration (Week 52)
- [ ] 更新 `POST /api/v1/island/sessions` (建立 SessionUsage)
- [ ] 更新 `POST /analyze-partial` (寫入 SessionAnalysisLog + 更新 SessionUsage)
- [ ] 更新 `PATCH /complete` (扣點邏輯)
- [ ] 15+ integration tests

### Phase 3: Queries & Dashboard (Week 53)
- [ ] GET `/sessions/{id}/analysis-logs` (分頁查詢)
- [ ] GET `/counselors/{id}/usage-stats` (統計查詢)
- [ ] GET `/sessions/{id}/safety-distribution`
- [ ] Admin dashboard UI
- [ ] 10+ integration tests

---

## 🔍 比較：JSONB vs 獨立 Table

| 特性 | JSONB (現況) | 獨立 Table (建議) |
|------|--------------|------------------|
| 寫入性能 | ⚠️ 慢（整個 JSONB 更新） | ✅ 快（INSERT 單筆） |
| 查詢性能 | ⚠️ 慢（無索引） | ✅ 快（可建索引） |
| 統計分析 | ❌ 困難 | ✅ 簡單（SQL aggregation） |
| 資料完整性 | ⚠️ 弱（JSONB 格式自由） | ✅ 強（Schema 驗證） |
| 可擴展性 | ❌ 差（JSONB 大小限制） | ✅ 好（無限記錄） |
| 維護成本 | ⚠️ 高（難以追蹤問題） | ✅ 低（結構化資料） |

**結論**: ✅ **強烈建議使用獨立 Table**

---

**設計完成時間**: 2025-12-26
**預計實作時間**: 2 週（Week 52-53）
**優先級**: 🔴 P0（與 iOS API 改版同步進行）
