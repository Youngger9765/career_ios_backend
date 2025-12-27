## 任務三：浮島 App 完整交付（WEB + iOS API）

**優先級**: 🔴 P0（最高優先）
**預估時間**: 3-4 週
**負責**: Backend + Frontend
**參考**: 浮島 App SPEC 1-5 + SESSION_USAGE_CREDIT_DESIGN.md

**架構調整**:
- ✅ 新增 `island_parents` tenant (第三個租戶)
- ✅ Multi-tenant isolation 完整實作
- ⚠️ Client 簡化（name + grade only for island_parents）
- ⚠️ Session DB log 持久化（獨立 table）
- ⚠️ Usage tracking + Credit deduction

---

### 📱 分類一：iOS API（給 App 使用）

#### 3.1 Authentication & Onboarding

##### 3.1.1 SMS 登入認證系統
**優先級**: 🔴 P0
**預估時間**: 6-8 小時

**API Endpoints**:
- [ ] `POST /api/v1/auth/sms/send-code` - 發送 SMS 驗證碼
  ```json
  Request:
  {
    "phone": "+886912345678",
    "tenant_id": "island_parents"
  }

  Response 200:
  {
    "verification_id": "uuid",
    "expires_in": 300,  // 5 分鐘
    "message": "驗證碼已發送"
  }
  ```

- [ ] `POST /api/v1/auth/sms/verify-code` - 驗證並登入
  ```json
  Request:
  {
    "phone": "+886912345678",
    "code": "123456",
    "verification_id": "uuid"
  }

  Response 200:
  {
    "access_token": "jwt_token",
    "counselor_id": "uuid",
    "is_new_user": false,
    "expires_in": 7776000  // 90 days
  }
  ```

**Data Models**:
- [ ] `SMSVerification` model
  ```python
  class SMSVerification(Base):
      id: UUID
      phone: str (index)
      code: str (6 digits)
      verification_id: UUID (unique)
      expires_at: datetime
      verified: bool (default=False)
      attempts: int (default=0, max=3)
      tenant_id: str
  ```

**Deliverables**:
- 2 API endpoints
- SMSVerification model + migration
- SMS provider integration (Twilio / AWS SNS)
- 10+ integration tests
- Rate limiting (防止濫用)

---

##### 3.1.2 孩子資料管理（Onboarding）
**優先級**: 🔴 P0
**預估時間**: 4-6 小時

**API Endpoints**:
- [ ] `POST /api/v1/island/children` - 新增孩子資料
  ```json
  Request:
  {
    "name": "小明",
    "grade": 3,  // 1-12 (小一到高三)
    "birth_date": "2018-05-15",  // optional
    "gender": "male",  // optional
    "notes": "容易生氣、拒絕寫作業"  // optional
  }

  Response 201:
  {
    "client_id": "uuid",
    "name": "小明",
    "grade": 3,
    "created_at": "2025-12-26T10:00:00Z"
  }
  ```

- [ ] `GET /api/v1/island/children` - 列出所有孩子
  ```json
  Response 200:
  {
    "children": [
      {
        "client_id": "uuid",
        "name": "小明",
        "grade": 3,
        "age": 7,
        "created_at": "..."
      }
    ],
    "total": 2
  }
  ```

**Data Models**:
- [ ] 擴充 `Client` model
  ```python
  # 新增欄位（island_parents 專用）
  grade: int (nullable, 1-12)

  # 既有欄位改為 nullable（向後相容）
  email: str (nullable)
  phone: str (nullable)
  gender: str (nullable)
  birth_date: date (nullable)
  ```

**Deliverables**:
- 2 API endpoints
- Client model migration (grade 欄位 + nullable)
- ClientCreateIslandParents schema
- 8+ integration tests

---

#### 3.2 Practice Scenarios（事前練習）

##### 3.2.1 練習情境管理
**優先級**: 🔴 P0
**預估時間**: 4-5 小時

**API Endpoints**:
- [ ] `GET /api/v1/island/scenarios` - 取得預設情境列表
  ```json
  Response 200:
  {
    "scenarios": [
      {
        "id": "scenario_1",
        "title": "孩子不寫作業",
        "description": "練習如何引導孩子完成作業",
        "category": "學習行為",
        "difficulty": "medium"
      },
      {
        "id": "scenario_2",
        "title": "兄弟姊妹吵架",
        "description": "學習調解手足衝突",
        "category": "人際關係",
        "difficulty": "hard"
      },
      {
        "id": "scenario_3",
        "title": "睡前拖延",
        "description": "協助建立良好睡眠習慣",
        "category": "生活習慣",
        "difficulty": "easy"
      },
      {
        "id": "custom",
        "title": "自訂情境",
        "description": "輸入您想練習的情境",
        "category": "其他",
        "difficulty": null
      }
    ],
    "total": 4
  }
  ```

**Backend Implementation**:
- [ ] 4 個預設情境（hardcoded in backend）
- [ ] 1 個 custom 選項（用戶自填）

**Deliverables**:
- 1 API endpoint
- Scenario data structure
- 5+ integration tests

---

#### 3.3 Realtime Analysis（即時分析）

##### 3.3.1 三段式存檔 API
**優先級**: 🔴 P0
**預估時間**: 8-10 小時
**參考**: SESSION_USAGE_CREDIT_DESIGN.md

**Phase 1: 開始錄音**
- [ ] `POST /api/v1/island/sessions` - 建立空 Session + SessionUsage
  ```json
  Request:
  {
    "client_id": "uuid",
    "mode": "emergency" | "practice",
    "scenario_topic": "孩子不寫作業",  // practice mode 必填
    "started_at": "2025-12-20T10:00:00Z"
  }

  Response 201:
  {
    "session_id": "uuid",
    "client_id": "uuid",
    "mode": "practice",
    "scenario_topic": "孩子不寫作業",
    "started_at": "2025-12-20T10:00:00Z",
    "status": "in_progress"
  }
  ```

**Phase 2: 錄音中 - Partial 分析**
- [ ] `POST /api/v1/island/sessions/{session_id}/analyze-partial` - 每分鐘分析
  ```json
  Request:
  {
    "transcript_segment": "最近 60 秒的逐字稿",
    "timestamp": "2025-12-20T10:01:00Z",
    "duration_seconds": 60
  }

  Response 200:
  {
    "safety_level": "yellow",  // red, yellow, green
    "severity": 2,  // 1-3
    "display_text": "家長語氣有點急躁",
    "action_suggestion": "深呼吸 3 次，放慢語速",
    "suggested_interval_seconds": 30,  // 建議下次間隔
    "keywords": ["急躁", "作業"],
    "categories": ["情緒管理"],
    "rag_sources": [
      {
        "theory": "正向教養",
        "reference": "..."
      }
    ]
  }
  ```

**Phase 3: 結束錄音 - Complete + 扣點**
- [ ] `PATCH /api/v1/island/sessions/{session_id}/complete` - 完成 + 扣點
  ```json
  Request:
  {
    "full_transcript": "完整逐字稿（App 端整合好的）",
    "ended_at": "2025-12-20T10:30:00Z"
  }

  Response 200:
  {
    "session_id": "uuid",
    "status": "completed",
    "duration_seconds": 1800,  // 30 分鐘
    "analysis_count": 30,
    "credits_consumed": 60,  // 本次消耗點數
    "remaining_credits": 1940,  // 剩餘點數
    "usage_summary": {
      "total_tokens": 45000,
      "estimated_cost_usd": 0.135,
      "red_count": 2,
      "yellow_count": 8,
      "green_count": 20
    }
  }
  ```

**Data Models**:
- [ ] 擴充 `Session` model
  ```python
  # 新增欄位
  mode: str (emergency | practice)
  scenario_topic: str (nullable)
  partial_segments: JSONB (default=[])
  partial_last_updated_at: datetime (nullable)
  ```

- [ ] 新增 `SessionAnalysisLog` model (獨立 table)
  ```python
  id: UUID
  session_id: UUID (FK, index)
  counselor_id: UUID (FK, index)
  safety_level: str (index)
  severity: int
  display_text: text
  action_suggestion: text
  rag_documents: JSON
  rag_sources: JSON
  transcript_length: int
  duration_seconds: int
  model_used: str
  prompt_tokens: int
  completion_tokens: int
  total_tokens: int
  cached_tokens: int
  estimated_cost_usd: Decimal
  analyzed_at: datetime (index)
  tenant_id: str (index)
  ```

- [ ] 新增 `SessionUsage` model (獨立 table)
  ```python
  id: UUID
  session_id: UUID (unique, FK, index)
  counselor_id: UUID (FK, index)
  duration_seconds: int (default=0)
  analysis_count: int (default=0)
  total_prompt_tokens: int (default=0)
  total_completion_tokens: int (default=0)
  total_tokens: int (default=0)
  total_cached_tokens: int (default=0)
  estimated_cost_usd: Decimal (default=0)
  credits_consumed: int (default=0)
  credit_deducted: bool (default=False)
  credit_deducted_at: datetime (nullable)
  status: str (in_progress | completed | failed)
  started_at: datetime
  completed_at: datetime (nullable)
  tenant_id: str (index)
  ```

**Backend Implementation**:
- [ ] Session 開始時建立 SessionUsage
- [ ] Partial 分析時：
  - 建立 SessionAnalysisLog (INSERT)
  - 更新 SessionUsage (累積 usage)
  - **不扣點**
- [ ] Session 完成時：
  - 計算 credits_consumed
  - 呼叫 CreditBillingService.add_credits() 扣點
  - 建立 CreditLog (transaction_type='session_fee')
  - 更新 SessionUsage (credit_deducted=True)

**Deliverables**:
- 3 API endpoints (Create / Partial / Complete)
- 3 DB migrations (Session 擴充 + SessionAnalysisLog + SessionUsage)
- 20+ integration tests
- Usage tracking 邏輯
- Credit deduction 整合

---

#### 3.4 Reports（報告生成）

##### 3.4.1 Practice vs Emergency 報告差異
**優先級**: 🔴 P0
**預估時間**: 3-4 小時

**API Endpoints**:
- [ ] `GET /api/v1/island/sessions/{session_id}/report` - 取得報告
  ```json
  Response 200:
  {
    "session_id": "uuid",
    "mode": "practice",
    "scenario_topic": "孩子不寫作業",
    "report": {
      "summary": "本次練習重點...",
      "highlights": [
        "成功使用同理心回應孩子感受",
        "語氣溫和，沒有指責"
      ],
      "improvements": [
        {
          "issue": "當孩子拒絕時，語氣變得急躁",
          "suggestion": "可以先深呼吸，用「我注意到...」開頭",
          "example": "我注意到你現在不想寫作業，是因為覺得太難嗎？"
        }
      ],
      "rag_references": [
        {
          "theory": "正向教養",
          "quote": "...",
          "source": "..."
        }
      ],
      "practice_tips": [  // 僅 practice mode
        "下次可以提早 5 分鐘提醒",
        "準備一個計時器讓孩子自己掌控時間"
      ]
    },
    "usage_summary": {
      "duration_minutes": 15,
      "credits_consumed": 30,
      "safety_distribution": {
        "red": 1,
        "yellow": 5,
        "green": 9
      }
    }
  }
  ```

**報告差異**:
| 欄位 | Practice Mode | Emergency Mode |
|------|---------------|----------------|
| `scenario_topic` | ✅ 顯示 | ❌ 無 |
| `practice_tips` | ✅ 包含 | ❌ 無 |
| `summary` | "本次練習..." | "本次對話..." |
| `improvements` | 3-4 條建議 | 1-2 條建議 |

**Backend Implementation**:
- [ ] 從 SessionAnalysisLog 查詢所有分析記錄
- [ ] 統計 safety_distribution
- [ ] 根據 mode 調整報告內容
- [ ] 整合 SessionUsage 資料

**Deliverables**:
- 1 API endpoint
- Report generation service
- 8+ integration tests

---

#### 3.5 History（歷史記錄）

##### 3.5.1 歷史記錄查詢
**優先級**: 🟡 P1
**預估時間**: 3-4 小時

**API Endpoints**:
- [ ] `GET /api/v1/island/sessions` - 列出所有 sessions
  ```json
  Query Parameters:
  - client_id: uuid (optional, 篩選特定孩子)
  - mode: emergency | practice (optional)
  - start_date: 2025-12-01 (optional)
  - end_date: 2025-12-31 (optional)
  - limit: 20 (default)
  - offset: 0 (default)

  Response 200:
  {
    "sessions": [
      {
        "session_id": "uuid",
        "client_name": "小明",
        "mode": "practice",
        "scenario_topic": "孩子不寫作業",
        "duration_minutes": 15,
        "safety_level_overall": "yellow",  // 主要等級
        "created_at": "2025-12-26T10:00:00Z",
        "credits_consumed": 30
      }
    ],
    "total": 45,
    "page": 1,
    "pages": 3
  }
  ```

- [ ] `GET /api/v1/island/sessions/{session_id}` - 單一 session 詳情
  ```json
  Response 200:
  {
    "session_id": "uuid",
    "client_name": "小明",
    "mode": "practice",
    "scenario_topic": "孩子不寫作業",
    "transcript": "完整逐字稿...",
    "duration_seconds": 900,
    "analysis_logs": [  // 最多顯示 50 筆
      {
        "analyzed_at": "2025-12-26T10:01:00Z",
        "safety_level": "green",
        "display_text": "溝通良好",
        "action_suggestion": "繼續保持"
      }
    ],
    "usage_summary": {
      "analysis_count": 15,
      "total_tokens": 22500,
      "credits_consumed": 30,
      "estimated_cost_usd": 0.0675
    }
  }
  ```

**Deliverables**:
- 2 API endpoints
- Pagination support
- 10+ integration tests

---

#### 3.6 Settings & Redeem Code（設定與兌換碼）

##### 3.6.1 個人設定
**優先級**: 🟢 P2
**預估時間**: 2-3 小時

**API Endpoints**:
- [ ] `GET /api/v1/island/settings` - 取得設定
  ```json
  Response 200:
  {
    "counselor_id": "uuid",
    "phone": "+886912345678",
    "name": "王小明",
    "email": "user@example.com",  // optional
    "notification_enabled": true,
    "language": "zh-TW",
    "created_at": "2025-12-01T00:00:00Z"
  }
  ```

- [ ] `PATCH /api/v1/island/settings` - 更新設定
  ```json
  Request:
  {
    "name": "王大明",
    "email": "new@example.com",
    "notification_enabled": false
  }

  Response 200:
  {
    "message": "設定已更新",
    "updated_fields": ["name", "email", "notification_enabled"]
  }
  ```

**Deliverables**:
- 2 API endpoints
- 5+ integration tests

---

##### 3.6.2 兌換碼兌換
**優先級**: 🟡 P1
**預估時間**: 4-5 小時

**API Endpoints**:
- [ ] `POST /api/v1/island/redeem` - 兌換點數
  ```json
  Request:
  {
    "code": "XXXX-XXXX-XXXX"
  }

  Response 200:
  {
    "message": "兌換成功",
    "credits_added": 60,
    "new_balance": 2000,
    "code_info": {
      "hours_quota": 60,
      "expires_at": "2026-12-31T23:59:59Z"
    }
  }

  Response 400 (已使用 / 過期 / 無效):
  {
    "error": "此兌換碼已使用",
    "code": "ALREADY_REDEEMED"
  }
  ```

- [ ] `GET /api/v1/island/credits` - 查詢點數餘額
  ```json
  Response 200:
  {
    "counselor_id": "uuid",
    "total_credits": 2000,
    "credits_used": 60,
    "available_credits": 1940,
    "subscription_expires_at": "2026-06-30T23:59:59Z"
  }
  ```

**Data Models**:
- [ ] `RedeemCode` model
  ```python
  id: UUID
  code: str (unique, index, 16 chars)
  hours_quota: int (default=60)
  hours_used: int (default=0)
  status: str (active | revoked | expired | depleted)
  created_at: datetime
  expires_at: datetime (nullable)
  redeemed_at: datetime (nullable)
  created_by: str (admin email)
  redeemed_by: UUID (FK counselor, nullable)
  tenant_id: str (index)
  ```

**Deliverables**:
- 2 API endpoints
- RedeemCode model + migration
- Redeem service logic
- 10+ integration tests

---

### 🌐 分類二：WEB（給 Admin 使用）

#### 3.7 Admin Console 擴充

##### 3.7.1 浮島家長版管理
**優先級**: 🟡 P1
**預估時間**: 6-8 小時

**API Endpoints**:
- [ ] `GET /api/v1/admin/island/users` - 列出所有浮島用戶
  ```json
  Query Parameters:
  - status: active | inactive (optional)
  - limit: 20 (default)
  - offset: 0 (default)

  Response 200:
  {
    "users": [
      {
        "counselor_id": "uuid",
        "phone": "+886912345678",
        "name": "王小明",
        "status": "active",
        "total_credits": 2000,
        "available_credits": 1940,
        "total_sessions": 15,
        "children_count": 2,
        "created_at": "2025-12-01T00:00:00Z",
        "last_active_at": "2025-12-26T10:00:00Z"
      }
    ],
    "total": 156
  }
  ```

- [ ] `GET /api/v1/admin/island/users/{counselor_id}` - 用戶詳情
  ```json
  Response 200:
  {
    "counselor_id": "uuid",
    "phone": "+886912345678",
    "name": "王小明",
    "email": "user@example.com",
    "status": "active",
    "credits": {
      "total": 2000,
      "used": 60,
      "available": 1940,
      "subscription_expires_at": "2026-06-30T23:59:59Z"
    },
    "usage_stats": {
      "total_sessions": 15,
      "total_duration_hours": 7.5,
      "total_credits_consumed": 60,
      "avg_session_duration_minutes": 30
    },
    "children": [
      {
        "client_id": "uuid",
        "name": "小明",
        "grade": 3,
        "created_at": "..."
      }
    ]
  }
  ```

- [ ] `PATCH /api/v1/admin/island/users/{counselor_id}` - 更新用戶狀態
  ```json
  Request:
  {
    "status": "inactive",  // active | inactive
    "notes": "停權原因..."
  }

  Response 200:
  {
    "message": "用戶狀態已更新",
    "counselor_id": "uuid",
    "status": "inactive"
  }
  ```

**Frontend (Admin Console)**:
- [ ] 浮島用戶列表頁面
- [ ] 用戶詳情 Modal
- [ ] 狀態切換按鈕
- [ ] 搜尋功能（phone, name）

**Deliverables**:
- 3 API endpoints
- Admin UI pages
- 10+ integration tests

---

##### 3.7.2 兌換碼管理
**優先級**: 🟡 P1
**預估時間**: 4-5 小時

**API Endpoints**:
- [ ] `POST /api/v1/admin/redeem-codes/generate` - 批次生成兌換碼
  ```json
  Request:
  {
    "count": 100,  // 生成數量
    "hours_quota": 60,  // 每張 60 小時
    "expires_at": "2026-12-31T23:59:59Z",  // 到期時間
    "prefix": "ISLAND"  // optional, 兌換碼前綴
  }

  Response 201:
  {
    "generated_count": 100,
    "codes": [
      "ISLAND-A1B2-C3D4-E5F6",
      "ISLAND-G7H8-I9J0-K1L2",
      ...
    ],
    "download_url": "/api/v1/admin/redeem-codes/export/batch-123"
  }
  ```

- [ ] `GET /api/v1/admin/redeem-codes` - 列出所有兌換碼
  ```json
  Query Parameters:
  - status: active | redeemed | expired | revoked
  - limit: 50 (default)
  - offset: 0

  Response 200:
  {
    "codes": [
      {
        "code": "ISLAND-A1B2-C3D4-E5F6",
        "status": "active",
        "hours_quota": 60,
        "hours_used": 0,
        "created_at": "2025-12-26T10:00:00Z",
        "expires_at": "2026-12-31T23:59:59Z",
        "redeemed_by": null
      }
    ],
    "total": 500
  }
  ```

- [ ] `PATCH /api/v1/admin/redeem-codes/{code}/revoke` - 停權兌換碼
  ```json
  Request:
  {
    "reason": "重複生成"
  }

  Response 200:
  {
    "code": "ISLAND-A1B2-C3D4-E5F6",
    "status": "revoked",
    "message": "兌換碼已停權"
  }
  ```

**Frontend (Admin Console)**:
- [ ] 批次生成頁面
- [ ] 兌換碼列表
- [ ] 篩選與搜尋
- [ ] CSV 匯出功能

**Deliverables**:
- 3 API endpoints
- Code generation service
- Admin UI pages
- 10+ integration tests

---

### 📋 完整 Deliverables Summary

#### Database
- [ ] 3 新 models: SMSVerification, SessionAnalysisLog, SessionUsage
- [ ] 1 新 model: RedeemCode
- [ ] 3 model 擴充: Client (grade), Session (mode, scenario_topic, partial_segments), Counselor (phone)
- [ ] 7+ DB migrations

#### API Endpoints
**iOS API** (給 App):
- [ ] 2 endpoints - SMS 認證 (send-code, verify-code)
- [ ] 2 endpoints - 孩子管理 (create, list)
- [ ] 1 endpoint - 練習情境 (list scenarios)
- [ ] 3 endpoints - Session 三段式 (create, partial, complete)
- [ ] 1 endpoint - 報告生成 (get report)
- [ ] 2 endpoints - 歷史記錄 (list, detail)
- [ ] 2 endpoints - 設定 (get, update)
- [ ] 2 endpoints - 兌換碼 (redeem, check balance)
- **小計: 15 endpoints**

**Web API** (給 Admin):
- [ ] 3 endpoints - 用戶管理 (list, detail, update status)
- [ ] 3 endpoints - 兌換碼管理 (generate, list, revoke)
- **小計: 6 endpoints**

**總計: 21 新 API endpoints**

#### Testing
- [ ] 80+ integration tests (iOS API)
- [ ] 20+ integration tests (Web Admin)
- **總計: 100+ integration tests**

#### Documentation
- [ ] SESSION_USAGE_CREDIT_DESIGN.md ✅ (已完成)
- [ ] API 文檔更新（Swagger）
- [ ] iOS API 對接文檔

---

### 🗓️ Implementation Timeline

#### Week 52 (2025-12-27 ~ 2026-01-02)
**Focus: Core Infrastructure**
- [ ] DB Schema (7 migrations)
- [ ] SMS 認證系統 (2 endpoints)
- [ ] 孩子管理 (2 endpoints)
- [ ] Session 三段式存檔 (3 endpoints)
- [ ] SessionAnalysisLog + SessionUsage integration

**Deliverable**: Core backend ready (7 endpoints + DB)

---

#### Week 53 (2026-01-03 ~ 2026-01-09)
**Focus: Reports & History**
- [ ] 練習情境 (1 endpoint)
- [ ] 報告生成 (1 endpoint)
- [ ] 歷史記錄 (2 endpoints)
- [ ] 設定管理 (2 endpoints)
- [ ] Usage tracking 邏輯完善

**Deliverable**: iOS API 基本完成 (13 endpoints)

---

#### Week 54 (2026-01-10 ~ 2026-01-16)
**Focus: Credits & Admin**
- [ ] 兌換碼兌換 (2 endpoints)
- [ ] Admin 用戶管理 (3 endpoints)
- [ ] Admin 兌換碼管理 (3 endpoints)
- [ ] Admin Console UI
- [ ] Credit deduction 整合測試

**Deliverable**: 完整系統交付 (21 endpoints + Admin UI)

---

### ⚠️ Critical Dependencies

1. **Universal Credit System** ✅ (已完成)
   - CreditBillingService
   - Credit rates configuration
   - Credit logs table

2. **SMS Provider Integration** ⏳ (待選擇)
   - Option 1: Twilio
   - Option 2: AWS SNS
   - Option 3: 台灣本地 SMS gateway

3. **Frontend Integration** ⏳ (iOS App 開發)
   - 需要 iOS team 配合測試
   - API 文檔必須完整

---

### 🎯 Success Criteria

#### Technical
- [ ] 100+ integration tests 全部通過
- [ ] API response time < 500ms (p95)
- [ ] DB query optimization (索引完善)
- [ ] Credit deduction 準確率 100%

#### Business
- [ ] iOS App 可成功對接所有 API
- [ ] Admin 可管理用戶和兌換碼
- [ ] 點數扣除機制運作正常
- [ ] 分析記錄持久化完整

#### Documentation
- [ ] Swagger API 文檔完整
- [ ] iOS 對接文檔 (含範例)
- [ ] SESSION_USAGE_CREDIT_DESIGN.md
- [ ] Migration guide
