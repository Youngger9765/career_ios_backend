# TODO - 開發任務清單

**最後更新**: 2025-12-27

---

## 任務一：Web 改版（Web Realtime Console）

### 1.1 紅綠燈卡片機制（視覺化風險等級）⚠️ Backend 完成 / Frontend 待整合
**優先級**: 🔴 P0
**預估時間**: 4-6 小時
**負責**: Backend API ✅ + Frontend UI ⏳

**需求說明**:
- **紅燈（嚴重錯誤）**：家長說了很不該說的話
  - 視覺：紅色卡片 + 大字凸顯
  - 觸發頻率：縮短為 **15 秒一張卡片**（緊急機制）
  - 範例：威脅、辱罵、情緒失控

- **黃燈（有點不合適）**：可以接受但需注意
  - 視覺：黃色卡片
  - 觸發頻率：**30 秒一張卡片**
  - 範例：語氣不當、急躁、施壓

- **綠燈（表現不錯）**：溝通良好
  - 視覺：綠色卡片 + 鼓勵訊息
  - 觸發頻率：**60 秒一張卡片**（正常）
  - 範例：溫和、同理、有效策略

**Backend ✅ 已完成** (2025-12-25):
- Response schema 包含 risk_level, severity, suggested_interval_seconds
- 動態分析間隔：Green 60s / Yellow 30s / Red 15s
- 15 integration tests 通過

**Frontend 需配合**:
- 根據 `suggested_interval_seconds` 動態調整 Timer
- Timer 不等 API 回來，以「送出時間」為基準
- 紅黃綠視覺化（顏色、大小、動畫）

---

## 任務三：iOS API 改版 - island_parents 租戶

**優先級**: 🔴 P0
**預估時間**: 10-12 小時
**負責**: Backend
**參考**: 會議紀錄 + 「浮島 App Pivot」文件

### 3.1 Multi-Tenant 架構擴充

**現有 Tenants**:
1. `counselor` - 諮商師（現有系統）
2. `speak_ai` - SpeakAI（現有系統）
3. **`island_parents`** - 浮島家長版（新增）✨

**Tenant 隔離策略**:
- [ ] 所有 table 都有 `tenant_id` 欄位
- [ ] API 自動注入 `tenant_id`（基於 JWT）
- [ ] Query 自動過濾 tenant（避免跨租戶資料洩漏）

---

### 3.2 Client 物件簡化（island_parents 專用）

**問題**:
- 現有 `clients` table 的 required 欄位太多：
  - email, phone, gender, birth_date, address, emergency_contact...
  - 不適合「家長建立孩子資料」的情境

**解決方案**:

**Option 1: 新增 tenant-specific schema（推薦）** ✅

- [ ] **island_parents 的 Client 只需兩個 required 欄位**:
  - `name` (String, required) - 孩子姓名或代號
  - `grade` (Integer, required) - 年級（1-12）
    - 1 = 小一, 6 = 小六, 7 = 國一, 10 = 高一, 12 = 高三
    - UI 負責顯示轉換（例如：10 → "高一"）

- [ ] **Optional 欄位**（App 動態顯示）:
  - `birth_date` (Date, optional)
  - `gender` (String, optional)
  - `notes` (Text, optional) - 家長備註（例如：「容易生氣、拒絕寫作業」）

- [ ] **DB Schema 調整**:
  ```python
  class Client(Base, BaseModel):
      # 現有欄位保持不變（counselor tenant）

      # 新增欄位（island_parents 專用）
      grade = Column(Integer, nullable=True)  # 1-12

      # 既有欄位改為 nullable（向後相容）
      email = Column(String, nullable=True)  # 改為 optional
      phone = Column(String, nullable=True)  # 改為 optional
      gender = Column(String, nullable=True)  # 改為 optional
      birth_date = Column(Date, nullable=True)  # 改為 optional
  ```

- [ ] **Schema Validation（Pydantic）**:
  ```python
  class ClientCreateIslandParents(BaseModel):
      """island_parents 租戶專用的簡化 schema"""
      name: str  # required
      grade: int  # required, 1-12
      birth_date: Optional[date] = None
      gender: Optional[str] = None
      notes: Optional[str] = None

      @validator('grade')
      def validate_grade(cls, v):
          if not 1 <= v <= 12:
              raise ValueError('年級必須在 1-12 之間')
          return v
  ```

- [ ] **API 路由分離**:
  ```python
  # 既有 API（counselor tenant）
  POST /api/v1/clients  # 需要完整欄位

  # 新增 API（island_parents tenant）
  POST /api/v1/island/clients  # 只需 name + grade
  ```

**Deliverable**:
- DB migration（新增 `grade` 欄位，既有欄位改 nullable）
- 新增 `ClientCreateIslandParents` schema
- 5+ integration tests

---

### 3.3 Session 資料結構調整

**新增欄位**:

- [ ] **scenario_topic** (String, optional)
  - 用途：事前練習時，使用者填寫「這次要練習什麼情境」
  - 範例：「孩子不寫作業」、「兄弟姊妹吵架」、「睡前拖延」
  - DB Migration：新增欄位到 `sessions` table

- [ ] **mode** (String, required)
  - `practice` - 事前練習模式
  - `emergency` - 事中實戰模式
  - 預設：`emergency`

- [ ] **partial_segments** (JSONB, default=[])
  - 儲存 partial 分析的逐字稿片段
  - 格式：
    ```json
    [
      {
        "timestamp": "2025-12-20T10:01:00Z",
        "text": "第一分鐘的逐字稿...",
        "duration_seconds": 60
      },
      {
        "timestamp": "2025-12-20T10:02:00Z",
        "text": "第二分鐘的逐字稿...",
        "duration_seconds": 60
      }
    ]
    ```

- [ ] **partial_last_updated_at** (DateTime, nullable)
  - 最後一次 partial 更新時間

**DB Migration**:
```sql
ALTER TABLE sessions
ADD COLUMN scenario_topic VARCHAR(255),
ADD COLUMN mode VARCHAR(20) DEFAULT 'emergency',
ADD COLUMN partial_segments JSONB DEFAULT '[]'::jsonb,
ADD COLUMN partial_last_updated_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_sessions_mode ON sessions(mode);
```

---

### 3.3.2 錄音同意流程（實戰模式）

**需求說明**:
- 實戰模式（emergency mode）須在開始錄音前獲得用戶同意
- 符合 GDPR 和個資法要求
- 記錄同意時間、版本、IP 地址

**開發**:

- [ ] **設計錄音同意文案與流程**
  - 與法務審核同意文案
  - 明確告知錄音用途、儲存方式、保留期限
  - 提供拒絕選項（無法使用實戰模式，僅能使用練習模式）

- [ ] **Backend API: 儲存同意記錄**
  - `POST /api/v1/island/sessions/{id}/consent`
  - 記錄欄位：
    - consent_timestamp (DateTime) - 同意時間
    - consent_version (String) - 同意條款版本
    - ip_address (String) - 用戶 IP
    - user_agent (String) - 設備資訊

- [ ] **RecordingConsent Model**
  ```python
  class RecordingConsent(Base):
      id = Column(GUID(), primary_key=True)
      session_id = Column(GUID(), ForeignKey("sessions.id"), nullable=False)
      counselor_id = Column(GUID(), ForeignKey("counselors.id"), nullable=False)
      consent_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
      consent_version = Column(String(20), nullable=False)  # "v1.0"
      ip_address = Column(String(50), nullable=True)
      user_agent = Column(Text, nullable=True)
      tenant_id = Column(String, nullable=False)
  ```

- [ ] **iOS: 實戰模式開始前顯示同意彈窗**
  - 練習模式不需同意（無錄音儲存）
  - 實戰模式必須同意後才能開始

- [ ] **隱私政策與合規審查**
  - 更新隱私政策文件
  - GDPR compliance check
  - 個資法 compliance check

**Deliverable**:
- RecordingConsent model + migration
- POST /api/v1/island/sessions/{id}/consent API
- 同意文案（經法務審核）
- 5+ integration tests
- 隱私政策更新

**預估時間**: 4-6 小時

---

### 3.3.3 使用記錄邊界情境處理

**需求說明**:
- 定義邊界情境（中途取消、離線、靜音）的計費規則
- 實作容錯機制確保使用記錄準確
- 提供爭議處理 SOP

**邊界情境規則**:

- [ ] **中途取消**
  - < 1分鐘：不扣點
  - >= 1分鐘：按實際分鐘數扣點（無條件捨去）
  - 範例：錄音 1 分 30 秒取消 → 扣 1 點

- [ ] **離線/崩潰**
  - 按最後成功寫入的 duration_seconds 計算
  - 使用 SessionUsage.duration_seconds (每 30 秒更新一次)
  - 若完全沒有 duration 記錄 → 0 點

- [ ] **長時間靜音**
  - 仍計費（ElevenLabs STT 特性：連線即計費）
  - 不因靜音而停止計時

**容錯機制**:

- [ ] **增量更新 SessionUsage**
  - 每 30 秒寫入一次 SessionUsage (incremental update)
  - 不等到 session 結束才寫入
  - 確保離線時有最新資料

- [ ] **Session 異常結束自動補完**
  ```python
  def auto_complete_abandoned_sessions():
      """每小時跑一次，自動完成超過 2 小時未更新的 session"""
      abandoned = Session.query.filter(
          Session.status == "in_progress",
          Session.partial_last_updated_at < datetime.utcnow() - timedelta(hours=2)
      ).all()

      for session in abandoned:
          # 使用最後 partial_last_updated_at 計算 duration
          duration = calculate_duration(session)
          complete_session(session, duration)
  ```

- [ ] **爭議處理 SOP**
  - Admin 可查看詳細使用記錄（SessionUsage + SessionAnalysisLog）
  - 手動調整扣點（需註記原因）
  - 記錄所有手動調整歷史

**Deliverable**:
- 邊界情境邏輯實作
- 增量更新機制（每 30 秒）
- 自動補完 abandoned sessions (cron job)
- Admin 爭議處理 API
- 8+ integration tests（各種邊界情境）

**預估時間**: 4-6 小時

---

### 3.3.4 前端使用時長與點數顯示

**需求說明**:
- iOS 錄音中即時顯示本次使用時長、預計扣點、剩餘點數
- 剩餘點數 < 100 時提醒用戶
- Web 同步實作

**iOS 顯示需求**:

- [ ] **錄音中即時顯示**
  - 本次時長：「15:32」(分:秒) - 每秒更新
  - 預計扣點：「16 點」- 無條件捨去 (15.5 分鐘 = 15 點)
  - 剩餘點數：「84 點」- 即時更新

- [ ] **低點數警告**
  - < 100 點：黃色提示「剩餘點數不多，建議加值」
  - < 20 點：紅色警告「點數即將用盡，請盡快加值」
  - < 5 點：阻擋新 session「點數不足，無法開始錄音」

- [ ] **API 支援**
  - GET /api/v1/island/credits/balance - 查詢剩餘點數
  - 回傳：
    ```json
    {
      "available_credits": 84,
      "total_credits": 100,
      "credits_used": 16,
      "low_balance_warning": false,  // < 100
      "critical_balance_warning": false  // < 20
    }
    ```

- [ ] **Web 同步實作**
  - console.html 即時顯示使用時長與點數
  - 與 iOS 相同的 UI 邏輯

**Deliverable**:
- iOS 即時顯示 UI（前端任務）
- GET /api/v1/island/credits/balance API
- 低點數警告邏輯
- Web 即時顯示（前端任務）
- 5+ integration tests (API)

**預估時間**: 3-4 小時（Backend API only，前端另計）

---

### 3.4 自動存檔功能（三段式 API）

**問題**:
- 現況：錄音結束後才 Create/Update Session
- 風險：API 失敗 → 後端沒有 session → **資料消失** 💀

**解法（三段式存檔）**:

#### Phase 1: 開始錄音 - Create 空 Session

- [ ] **POST /api/v1/island/sessions** - 建立空 Session
  ```json
  Request:
  {
    "client_id": "uuid",
    "case_id": "uuid",  // 可選（現階段只有一個 Case）
    "mode": "emergency" | "practice",
    "scenario_topic": "孩子不寫作業",  // practice mode 需填
    "started_at": "2025-12-20T10:00:00Z"
  }

  Response 201:
  {
    "session_id": "uuid",
    "client_id": "uuid",
    "mode": "emergency",
    "scenario_topic": "孩子不寫作業",
    "started_at": "2025-12-20T10:00:00Z",
    "status": "in_progress"
  }
  ```

- [ ] **行為**:
  - 建立空 session（只有 `started_at`）
  - `transcript` 為空
  - `status = "in_progress"`
  - 回傳 `session_id` 給 App

---

#### Phase 2: 錄音中 - Partial 分析 API

- [ ] **POST /api/v1/island/sessions/:session_id/analyze-partial** - Partial 分析
  ```json
  Request:
  {
    "transcript_segment": "最近這 60 秒的逐字稿",
    "timestamp": "2025-12-20T10:01:00Z",
    "duration_seconds": 60
  }

  Response 200:
  {
    "risk_level": "yellow",
    "severity": 2,
    "display_text": "家長語氣有點急躁",
    "action_suggestion": "深呼吸 3 次，放慢語速",
    "suggested_interval_seconds": 30,  // 建議改 30 秒
    "should_merge": false,
    "keywords": ["急躁", "作業"],
    "categories": ["情緒管理"]
  }
  ```

- [ ] **行為**:
  1. 儲存 partial segment 到 `partial_segments` JSONB 欄位
  2. 執行即時分析（紅黃綠燈判斷）
  3. 計算與前一張卡片的相似度
  4. 回傳分析結果（含 `should_merge`）
  5. 更新 `partial_last_updated_at`

- [ ] **Backup 機制**:
  - 每次 partial 都儲存到 DB
  - 若最後 Update 失敗，可用 partial_segments 重建完整逐字稿

---

#### Phase 3: 結束錄音 - Update 完整逐字稿

- [ ] **PATCH /api/v1/island/sessions/:session_id/complete** - 完成 Session
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
    "started_at": "2025-12-20T10:00:00Z",
    "ended_at": "2025-12-20T10:30:00Z",
    "duration_seconds": 1800,
    "transcript_length": 5432,
    "partial_segments_count": 30  // 備份了 30 個片段
  }
  ```

- [ ] **行為**:
  1. 更新 `transcript` 為完整逐字稿
  2. 更新 `ended_at` 和 `status = "completed"`
  3. 計算 `duration_seconds`
  4. 若 `full_transcript` 為空或失敗，使用 `partial_segments` 拼接（fallback）

- [ ] **Fallback 機制**:
  ```python
  def get_transcript_with_fallback(session):
      if session.transcript:
          return session.transcript
      else:
          # 拼接 partial_segments
          segments = session.partial_segments or []
          return "\n\n".join([seg["text"] for seg in segments])
  ```

---

#### 補充：結束時補齊最後一段

- [ ] **App 端行為**:
  - 使用者按「結束錄音」時
  - 立即觸發最後一個 `analyze-partial`（不等 timer）
  - 確保最後一段也被儲存

**Deliverable**:
- 3 個 API endpoints（Create / Partial / Complete）
- Session model 更新（新增 4 個欄位）
- Fallback 機制實作
- 20+ integration tests（正常流程 + 失敗 fallback）

---

### 3.4.2 報告展示層級與RAG術語可見性

**需求說明**:
- 定義親子溝通報告的展示層級（心法＋做法的呈現範圍）
- 決定是否顯示 RAG 理論標籤和專業術語
- 設計可視化方式（摺疊/展開、說明文字）

**產品決策（待確認）**:

- [ ] **RAG 理論標籤顯示規則**
  - Option 1: 完全隱藏 RAG 來源（用戶只看建議）
  - Option 2: 顯示但可 toggle（預設摺疊）
  - Option 3: 顯示且預設展開（專業模式）

- [ ] **專業術語處理**
  - Option 1: 白話翻譯（如「5比1」→「5次正向回應配1次負向」）
  - Option 2: 保留術語但加註解釋（tooltip 或註腳）
  - Option 3: 同時顯示術語和白話（「5比1 原則（5次正向回應配1次負向）」）

- [ ] **展示層級設計**
  - 心法：Icon + 簡短標題（如「正向對話比例」）
  - 做法：具體步驟列表（如「1. 先肯定孩子努力 2. 再提出建議」）
  - RAG 來源：可選顯示（「參考：正向教養理論」）
  - 預設摺疊 vs 全展開？

**實作需求**:

- [ ] **報告 Schema 調整**
  ```python
  class ParentingReportSection(BaseModel):
      """報告區段"""
      principle: str  # 心法（簡短標題）
      principle_description: str  # 心法說明（可選顯示）
      actionable_steps: List[str]  # 做法（具體步驟）
      rag_source: Optional[str] = None  # RAG 來源（可選顯示）
      rag_source_visible: bool = False  # 是否顯示 RAG 來源
      example_dialogue: Optional[str] = None  # 範例對話
  ```

- [ ] **可視化設計**
  - 心法：使用 Icon（如 💡 ✨ 🎯）
  - 做法：編號列表，每項可點擊展開詳細說明
  - RAG 來源：灰色小字，可 toggle 顯示/隱藏

- [ ] **A/B Testing（可選）**
  - 測試不同展示層級的用戶偏好
  - 指標：報告閱讀時間、行動採納率

**Deliverable**:
- 產品決策文件（展示層級規則）
- 報告 Schema 更新（支援可選顯示）
- iOS/Web UI 調整（摺疊/展開、tooltip）
- A/B Testing 實驗設計（可選）
- 3+ integration tests

**預估時間**: 3-4 小時（待產品定案後實作）
**優先級**: 🟡 P1（依賴產品決策）

---

### 3.5 即時分析 API 改版

**參考**: 任務一的 Web 改版（紅黃綠燈機制）

- [ ] 使用相同的 response schema
- [ ] island_parents 租戶專用的 Prompt 調整
- [ ] RAG 知識庫：使用親子教養相關知識（而非諮商專業）

---

### 3.6 Case 管理簡化

**現階段**:
- **Only One Case**（固定大目標）
- 每次談話：新的 Session（不同小主題）

**實作**:

- [ ] **預設 Case 自動建立**
  - 當 island_parents 租戶第一次建立 Client 時
  - 自動建立一個預設 Case：「親子溝通成長」
  - `case_id` 自動關聯到所有 Session

- [ ] **API 簡化**
  - App 不需要自己建立 Case
  - Create Session 時，若 `case_id` 為空，自動使用預設 Case

**Deliverable**:
- 預設 Case 自動建立邏輯
- 3+ integration tests

---

### 3.6.3 點數有效期與結算細則

**需求說明**:
- 定義點數有效期規則（每學期 vs 半年 vs 一年）
- 實作到期自動處理機制
- 提供到期前通知
- 設計點數滾存或歸零規則

**產品決策（待確認）**:

- [ ] **點數有效期長度**
  - Option 1: 每學期（4 個月）- 配合學期制
  - Option 2: 半年（6 個月）- 彈性較大
  - Option 3: 一年（12 個月）- 最長期限
  - 建議：根據目標用戶使用頻率決定

- [ ] **到期處理規則**
  - Option 1: 到期歸零（鼓勵持續使用）
  - Option 2: 自動滾存到下期（保留價值）
  - Option 3: 可延期一次（給予緩衝）

- [ ] **剩餘點數處理**
  - 未用完的點數如何處理？
  - 是否允許退款或轉讓？
  - 到期前多久通知用戶？

**實作需求**:

- [ ] **CreditPackage Model 更新**
  ```python
  class CreditPackage(Base):
      # 現有欄位...

      # 新增欄位
      expires_at = Column(DateTime(timezone=True), nullable=True)  # 到期時間
      expiry_notified = Column(Boolean, default=False)  # 是否已通知到期
      expiry_notification_sent_at = Column(DateTime(timezone=True), nullable=True)
      status = Column(String(20), default="active")  # active, expired, extended
  ```

- [ ] **到期自動處理 (Cron Job)**
  ```python
  @scheduler.scheduled_job('cron', hour=0, minute=0)  # 每日 00:00 執行
  def check_credit_expiry():
      """檢查並處理過期點數"""
      # 1. 到期前 7 天通知
      notify_expiring_credits(days_before=7)

      # 2. 到期當日處理
      expire_credits()

      # 3. 記錄到期日誌
      log_expiry_events()
  ```

- [ ] **Backend APIs**
  - GET /api/v1/island/credits/expiry - 查詢點數到期資訊
    ```json
    {
      "total_credits": 100,
      "available_credits": 84,
      "expiring_soon": 30,  // 7 天內到期
      "expires_at": "2025-07-01T00:00:00Z",
      "days_until_expiry": 5
    }
    ```

  - POST /api/v1/admin/credits/extend-expiry - Admin 手動延期
    ```json
    Request:
    {
      "counselor_id": "uuid",
      "extend_days": 30,
      "reason": "特殊情況延期"
    }
    ```

- [ ] **通知機制**
  - 到期前 7 天：Email + App 推播
  - 到期前 1 天：再次提醒
  - 到期當日：通知已歸零（若採用歸零規則）

**Deliverable**:
- 產品決策文件（有效期規則）
- CreditPackage model 更新 + migration
- Cron job（每日檢查到期）
- 2 個 API endpoints（查詢到期 + Admin 延期）
- Email 通知整合
- 8+ integration tests（正常到期 + 延期 + 通知）

**預估時間**: 4-5 小時（待產品定案後實作）
**優先級**: 🟡 P1（依賴產品決策）

---

## 任務四：密碼管理與通知系統

**優先級**: 🔴 P0
**預估時間**: 6-8 小時
**負責**: Backend
**影響範圍**: Web Admin + iOS App

### 4.1 帳號建立後自動發送密碼信件

**需求說明**:
- 當管理員在後台建立新會員帳號時，系統應自動發送包含密碼的歡迎信件給用戶
- 信件應包含：登入網址、帳號（Email）、初始密碼、首次登入提示

**開發**:

- [ ] **整合 Email 服務**
  - 選擇 Email 服務商（SendGrid / AWS SES / SMTP）
  - 設定 Email 模板
  - 環境變數配置（API Key、發件人地址）

- [ ] **信件模板設計**
  ```html
  主旨：歡迎加入浮島諮詢系統

  內容：
  - 歡迎訊息
  - 登入網址：https://your-domain.com/admin
  - 您的帳號：{email}
  - 初始密碼：{password}
  - 建議首次登入後立即修改密碼
  ```

- [ ] **修改會員建立 API**
  - 在 `POST /api/v1/admin/counselors` 成功建立後
  - 觸發異步任務發送 Email
  - 記錄發送狀態（成功/失敗）

- [ ] **Email 發送日誌**
  ```python
  class EmailLog(Base):
      id = Column(GUID(), primary_key=True)
      recipient_email = Column(String, nullable=False)
      email_type = Column(String)  # "welcome", "password_reset"
      status = Column(String)  # "sent", "failed", "pending"
      sent_at = Column(DateTime(timezone=True))
      error_message = Column(Text, nullable=True)
  ```

**Deliverable**:
- Email 服務整合
- 歡迎信件模板
- Email 日誌模型
- 5+ integration tests

---

### 4.2 密碼重設頁面（Web）

**需求說明**:
- 提供 Web 頁面讓用戶可以自行重設密碼
- 流程：輸入 Email → 收到重設連結 → 設定新密碼

**開發**:

- [ ] **密碼重設請求頁面**
  - URL: `/reset-password`
  - 輸入欄位：Email
  - 提交後顯示「已發送重設連結」訊息

- [ ] **密碼重設 Token 生成**
  ```python
  class PasswordResetToken(Base):
      id = Column(GUID(), primary_key=True)
      counselor_id = Column(GUID(), ForeignKey("counselors.id"))
      token = Column(String(64), unique=True, index=True)
      expires_at = Column(DateTime(timezone=True))  # 有效期 1 小時
      used = Column(Boolean, default=False)
      created_at = Column(DateTime(timezone=True))
  ```

- [ ] **密碼重設確認頁面**
  - URL: `/reset-password/confirm?token={token}`
  - 驗證 Token 有效性
  - 輸入欄位：新密碼、確認密碼
  - 提交後更新密碼並標記 Token 為已使用

- [ ] **發送密碼重設信件**
  ```html
  主旨：密碼重設請求

  內容：
  - 收到密碼重設請求
  - 重設連結：https://your-domain.com/reset-password/confirm?token={token}
  - 連結有效期：1 小時
  - 若非本人操作，請忽略此信件
  ```

**Deliverable**:
- 2 個 Web 頁面（請求 + 確認）
- PasswordResetToken 模型
- Email 通知整合
- 8+ integration tests

---

### 4.3 密碼重設 API（給 iOS 使用）

**需求說明**:
- iOS App 需要 API 來實現密碼重設功能
- 流程與 Web 相同，但使用 API 而非頁面

**API 設計**:

- [ ] **POST /api/v1/auth/password-reset/request** - 請求密碼重設
  ```json
  Request:
  {
    "email": "user@example.com"
  }

  Response 200:
  {
    "message": "密碼重設信件已發送，請檢查您的信箱",
    "expires_in_minutes": 60
  }

  Response 404:
  {
    "detail": "找不到此 Email 的帳號"
  }
  ```

- [ ] **POST /api/v1/auth/password-reset/verify** - 驗證 Token
  ```json
  Request:
  {
    "token": "abc123..."
  }

  Response 200:
  {
    "valid": true,
    "email": "user@example.com"
  }

  Response 400:
  {
    "valid": false,
    "reason": "Token 已過期或無效"
  }
  ```

- [ ] **POST /api/v1/auth/password-reset/confirm** - 確認重設密碼
  ```json
  Request:
  {
    "token": "abc123...",
    "new_password": "NewSecurePass123"
  }

  Response 200:
  {
    "message": "密碼已成功重設"
  }

  Response 400:
  {
    "detail": "Token 無效或已使用"
  }
  ```

**安全考量**:
- [ ] Token 應使用加密隨機字串（至少 32 字元）
- [ ] Token 有效期 1 小時
- [ ] Token 只能使用一次
- [ ] 密碼強度驗證（至少 6 字元）
- [ ] 限制請求頻率（同一 Email 5 分鐘內只能請求一次）

**Deliverable**:
- 3 個 API endpoints
- 請求頻率限制邏輯
- 10+ integration tests（正常流程 + 錯誤處理）
- API 文檔更新

---

### 4.5 登入失敗提示語統一（資安）

**需求說明**:
- 登入失敗時採用泛化訊息，不區分密碼錯誤或帳號不存在
- 防止帳號探測攻擊（Account Enumeration）
- 統一 Backend 錯誤訊息和前端 UI 提示

**資安考量**:
- ❌ 錯誤：「密碼錯誤」→ 洩漏帳號存在
- ❌ 錯誤：「此帳號不存在」→ 可用於探測有效帳號
- ✅ 正確：「登入資料有誤，請檢查後重試」→ 泛化訊息

**Backend 實作**:

- [ ] **統一 API 錯誤訊息**
  - 密碼錯誤 → `401 Unauthorized: "登入資料有誤，請檢查後重試"`
  - 帳號不存在 → `401 Unauthorized: "登入資料有誤，請檢查後重試"`
  - 帳號停權 → `403 Forbidden: "無權限訪問，請聯繫客服"`
  - 帳號鎖定 → `429 Too Many Requests: "登入失敗次數過多，請稍後再試"`

- [ ] **登入 API 更新**
  ```python
  @router.post("/api/v1/auth/login")
  def login(credentials: LoginRequest):
      counselor = get_counselor_by_email(credentials.email)

      # 統一錯誤訊息 - 不洩漏帳號是否存在
      if not counselor or not verify_password(credentials.password, counselor.hashed_password):
          # 記錄失敗次數
          log_failed_login_attempt(credentials.email)
          raise HTTPException(
              status_code=401,
              detail="登入資料有誤，請檢查後重試"
          )

      # 檢查帳號狀態
      if counselor.status == "suspended":
          raise HTTPException(
              status_code=403,
              detail="無權限訪問，請聯繫客服"
          )

      # 檢查是否鎖定
      if is_account_locked(counselor):
          raise HTTPException(
              status_code=429,
              detail="登入失敗次數過多，請 15 分鐘後再試"
          )

      # 登入成功，重置失敗次數
      reset_failed_login_attempts(counselor)
      return generate_jwt_token(counselor)
  ```

- [ ] **iOS/Web 前端統一錯誤提示 UI**
  - 401: 顯示「登入資料有誤，請檢查後重試」
  - 403: 顯示「無權限訪問，請聯繫客服」
  - 429: 顯示「登入失敗次數過多，請稍後再試」

**Deliverable**:
- Backend: 統一錯誤訊息邏輯
- iOS: 統一前端錯誤提示 UI（前端任務）
- Web: 統一前端錯誤提示 UI（前端任務）
- 文檔: 登入失敗訊息規範
- 5+ integration tests（各種失敗情境）

**預估時間**: 2-3 小時
**優先級**: 🔴 P0（資安必須）

---

### 4.6 Email 發信系統與錯誤處理

**需求說明**:
- 確認並建立官方發信 Email（可用 Gmail SMTP）
- 實作 Email 狀態追蹤（sent, delivered, bounced, failed）
- Admin 可查看 Email 發送記錄與狀態
- 提供重發機制

**Email 服務商選擇**:

- [ ] **Option 1: Gmail SMTP（簡單、快速）** ✅ 推薦 Prototype 階段
  - 優點：快速設定、免費（每日 500 封限額）
  - 缺點：功能較陽春、無詳細追蹤
  - 設定：環境變數 `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`

- [ ] **Option 2: SendGrid（專業、易用）**
  - 優點：免費額度（每日 100 封）、API 簡單、追蹤詳細
  - 缺點：需註冊、需驗證 domain
  - 適合：Production 環境

- [ ] **Option 3: AWS SES（可靠、便宜）**
  - 優點：便宜（$0.10/1000 封）、穩定、整合 AWS
  - 缺點：設定複雜、需 AWS 帳號
  - 適合：Production 大量發送

**實作需求**:

- [ ] **EmailLog Model**
  ```python
  class EmailLog(Base):
      id = Column(GUID(), primary_key=True)
      recipient_email = Column(String, nullable=False, index=True)
      email_type = Column(String, nullable=False)  # "welcome", "password_reset", "credit_expiry"
      subject = Column(String, nullable=False)
      body = Column(Text, nullable=False)

      # 狀態追蹤
      status = Column(String(20), default="pending")  # pending, sent, delivered, bounced, failed
      sent_at = Column(DateTime(timezone=True), nullable=True)
      delivered_at = Column(DateTime(timezone=True), nullable=True)
      bounced_at = Column(DateTime(timezone=True), nullable=True)

      # 錯誤處理
      error_message = Column(Text, nullable=True)
      retry_count = Column(Integer, default=0)
      last_retry_at = Column(DateTime(timezone=True), nullable=True)

      # 關聯
      counselor_id = Column(GUID(), ForeignKey("counselors.id"), nullable=True)
      tenant_id = Column(String, nullable=False)

      created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
  ```

- [ ] **Email Service 實作**
  ```python
  class EmailService:
      def send_email(self, to: str, subject: str, body: str, email_type: str):
          """發送 Email 並記錄狀態"""
          log = EmailLog(
              recipient_email=to,
              email_type=email_type,
              subject=subject,
              body=body,
              status="pending"
          )
          db.add(log)

          try:
              # 使用 SMTP 或 SendGrid 發送
              send_via_smtp(to, subject, body)
              log.status = "sent"
              log.sent_at = datetime.utcnow()
          except Exception as e:
              log.status = "failed"
              log.error_message = str(e)

          db.commit()
          return log

      def handle_bounce(self, email_log_id: str):
          """處理退信"""
          log = db.query(EmailLog).get(email_log_id)
          log.status = "bounced"
          log.bounced_at = datetime.utcnow()

          # 標記 Counselor 的 Email 無效
          counselor = log.counselor
          counselor.email_status = "bounced"

          # 通知 Admin
          notify_admin_email_bounce(counselor)
  ```

- [ ] **Admin Backend APIs**
  - GET /api/v1/admin/emails/logs - 查看 Email 發送記錄
    ```json
    {
      "logs": [
        {
          "id": "uuid",
          "recipient_email": "user@example.com",
          "email_type": "welcome",
          "status": "sent",
          "sent_at": "2025-12-20T10:00:00Z"
        }
      ],
      "total": 150,
      "page": 1
    }
    ```

  - POST /api/v1/admin/emails/resend - 重發 Email
    ```json
    Request:
    {
      "email_log_id": "uuid"
    }
    ```

- [ ] **重發機制（用戶端）**
  - 用戶可在登入頁面點擊「重新發送密碼重設信」
  - 5 分鐘內只能請求一次（防止濫用）

**Deliverable**:
- Email 服務商選擇與設定（Gmail SMTP 優先）
- EmailLog model + migration
- EmailService 實作（發送 + 錯誤處理）
- 2 個 Admin API endpoints
- 用戶端重發機制
- 8+ integration tests（發送 + 失敗 + 重發）

**預估時間**: 4-5 小時
**優先級**: 🔴 P0（密碼管理依賴）

---

### 4.7 密碼強度政策與安全策略

**需求說明**:
- 定義密碼規則（最低長度、複雜度要求）
- 實作弱密碼黑名單
- 實作登入失敗鎖定機制
- 前端即時密碼強度檢查

**密碼規則定義**:

- [ ] **最低要求**
  - 長度：至少 8 字元（建議 10+）
  - 組成：必須包含英文 + 數字
  - 可選：特殊字元（!@#$%^&*）

- [ ] **弱密碼黑名單**
  - 常見弱密碼：`123456`, `password`, `qwerty`, `abc123`, `12345678`
  - 連續字元：`111111`, `aaaaaa`
  - 鍵盤順序：`asdfgh`, `zxcvbn`

- [ ] **登入失敗鎖定機制**
  - 5 次失敗 → 鎖定 15 分鐘
  - 記錄欄位：`failed_login_attempts`, `locked_until`

**Backend 實作**:

- [ ] **Counselor Model 更新**
  ```python
  class Counselor(Base):
      # 現有欄位...

      # 新增欄位
      failed_login_attempts = Column(Integer, default=0)
      locked_until = Column(DateTime(timezone=True), nullable=True)
      last_failed_login_at = Column(DateTime(timezone=True), nullable=True)
  ```

- [ ] **密碼驗證邏輯**
  ```python
  def validate_password_strength(password: str) -> tuple[bool, str]:
      """驗證密碼強度"""
      # 長度檢查
      if len(password) < 8:
          return False, "密碼長度至少需要 8 個字元"

      # 複雜度檢查
      has_letter = any(c.isalpha() for c in password)
      has_number = any(c.isdigit() for c in password)
      if not (has_letter and has_number):
          return False, "密碼必須包含英文和數字"

      # 弱密碼黑名單
      weak_passwords = ["123456", "password", "qwerty", "abc123", "12345678"]
      if password.lower() in weak_passwords:
          return False, "此密碼過於簡單，請使用更複雜的密碼"

      return True, "密碼強度符合要求"

  def check_account_locked(counselor: Counselor) -> bool:
      """檢查帳號是否鎖定"""
      if counselor.locked_until and counselor.locked_until > datetime.utcnow():
          return True
      return False

  def record_failed_login(counselor: Counselor):
      """記錄登入失敗"""
      counselor.failed_login_attempts += 1
      counselor.last_failed_login_at = datetime.utcnow()

      # 5 次失敗 → 鎖定 15 分鐘
      if counselor.failed_login_attempts >= 5:
          counselor.locked_until = datetime.utcnow() + timedelta(minutes=15)

      db.commit()

  def reset_failed_login(counselor: Counselor):
      """登入成功後重置"""
      counselor.failed_login_attempts = 0
      counselor.locked_until = None
      db.commit()
  ```

- [ ] **密碼重設 API 整合**
  - 在 `POST /api/v1/auth/password-reset/confirm` 加入密碼強度驗證
  - 拒絕弱密碼

**Frontend 實作（iOS + Web）**:

- [ ] **即時密碼強度檢查**
  - 使用者輸入時即時檢查（debounce 500ms）
  - 視覺化顯示：
    - 弱（紅色）：< 8 字元或純數字
    - 中（黃色）：8+ 字元 + 英文數字
    - 強（綠色）：10+ 字元 + 英文數字 + 特殊字元
  - 提示訊息：即時顯示不符合的規則

**Deliverable**:
- 密碼規則文檔
- Counselor model 更新 + migration
- Backend 驗證邏輯（密碼強度 + 鎖定機制）
- Frontend 即時檢查 UI（iOS + Web，前端任務）
- 10+ integration tests（密碼驗證 + 鎖定機制）

**預估時間**: 3-4 小時
**優先級**: 🔴 P0（資安必須）

---

### 4.4 整合測試與文檔

- [ ] **完整流程測試**
  - 建立帳號 → 收到歡迎信
  - 請求密碼重設 → 收到重設信 → 成功重設密碼
  - Token 過期處理
  - Token 重複使用防護

- [ ] **API 文檔更新**
  - Swagger UI 更新
  - 在 `點數管理後台.md` 添加密碼重設說明

- [ ] **環境變數文檔**
  ```env
  # Email 服務配置
  EMAIL_PROVIDER=sendgrid  # sendgrid / ses / smtp
  EMAIL_API_KEY=your_api_key
  EMAIL_FROM_ADDRESS=noreply@your-domain.com
  EMAIL_FROM_NAME=浮島諮詢系統

  # 密碼重設配置
  PASSWORD_RESET_TOKEN_EXPIRY_HOURS=1
  PASSWORD_RESET_RATE_LIMIT_MINUTES=5
  ```

**Deliverable**:
- 完整流程測試（20+ tests）
- 用戶文檔更新
- 開發者文檔（環境變數、部署指南）

---

## ~~任務五：浮島 App iOS 完整功能交付~~ ✅ 已合併至任務三

**📌 重要通知**: 此任務已於 2025-12-27 合併至 **任務三：iOS API 改版 - island_parents 租戶**

**合併原因**:
- 任務三和任務五內容高度重疊（皆為 island_parents 租戶相關 API）
- 合併後可更好地追蹤完整的 iOS API 開發進度
- 避免重複任務造成混淆

**📋 詳細任務內容請參考**:
1. **任務三**（本文件上方）- 包含完整的 iOS API 開發任務
2. **docs/ISLAND_APP_TASKS_REORGANIZED.md** - 重新組織後的任務分解（WEB vs iOS API）

**原任務五內容已整合至任務三**:
- 5.1 手機號碼登入與 SMS 認證 → 任務三 3.1.1 SMS Authentication
- 5.2 孩子管理 API → 任務三 3.1.2 Children Management
- 5.3 四格情境選擇 → 任務三 3.2.1 Practice Scenarios
- 5.4 錄音與即時提醒 → 任務三 3.3.1 Three-phase Session API
- 5.5 報告生成 → 任務三 3.4.1 Reports
- 5.6 歷史記錄查詢 → 任務三 3.5.1 History
- 5.7 設置頁 API → 任務三 3.6.1 Settings
- 5.8 兌換碼與點數系統 → 任務三 3.6.2 Redeem Codes
- 5.9 Web Admin Console → 任務三 3.7 Web Admin APIs

**🚀 請直接查看任務三進行開發**

- 🎯 完成 5 大任務（Web 改版 + 付費版 + iOS API + 密碼管理 + 浮島 App）
- 🎯 110+ integration tests 新增
- 🎯 8+ DB migrations

### API 交付
- 🎯 Web 改版：2 APIs（即時分析改版 + 卡片合併）
- 🎯 付費版：5 APIs（白名單管理）
- 🎯 iOS 基礎 API：3 APIs（Create / Partial / Complete）
- 🎯 密碼管理：3 APIs（密碼重設請求/驗證/確認）
- 🎯 浮島 App iOS：11 APIs（SMS登入 + 孩子管理 + 情境 + 報告 + 歷史 + 兌換碼）

### 性能目標
- 🎯 即時分析 API：< 10 秒（含紅黃綠判斷）
- 🎯 Partial 分析 API：< 5 秒
- 🎯 卡片相似度計算：< 1 秒

### 品質目標
- 🎯 Test coverage：> 80%（新代碼）
- 🎯 Ruff check：0 errors
- 🎯 所有 integration tests：100% 通過

---

## 📚 參考文件

### 會議紀錄
- 2025-12-20 產品會議重點整理（1500 字）
- 浮島 App 付費機制規劃
- Web 改版需求

### 技術規格
- `docs/TECH_SPEC_PARENTING_REALTIME_V2.md`
- `docs/ARCHITECTURE_PARENTING_REALTIME_V2.md`

---

## 📝 Notes & Decisions

### 技術決策記錄
1. **API 路徑分離** (2025-12-13)
   - 決策：分離「即時分析」與「錄音歸檔」兩條 API 路徑
   - 理由：避免 segment 與 recording 的對應混亂，簡化資料模型
   - 影響：需要建立新的 RealtimeSession/RealtimeAnalysis models

2. **雙模式設計** (2025-12-13)
   - 決策：Emergency (急救) + Practice (練習) 雙模式
   - 理由：符合產品定位（事中急救 vs 事前練習）
   - 影響：需要不同的 prompt、UI、回應格式

3. **RAG Threshold 調整** (2025-12-13)
   - 決策：降低 similarity_threshold 從 0.7 至 0.5
   - 理由：實際相似度分數最高約 0.54-0.59，0.7 太嚴格
   - 影響：提高 RAG 召回率，但可能降低精確度

### 產品會議重點
- **使用者體驗**：手機端卡片要大、字要大、資訊密度要低
- **互動設計**：紅黃綠燈危機提示、卡片滑動/展開/歷史檢視
- **倫理考量**：錄音權限、家長向孩子說明使用目的
- **速度要求**：< 5 秒（Emergency）、< 10 秒（Practice）

### 待討論事項
- [ ] 卡片疊加/覆蓋規則（新卡片如何顯示？）
- [ ] 歷史卡片快速回看機制
- [ ] RAG cache 失效策略（多久過期？）
- [ ] 錄音片段如何對應歷史卡片？

---
