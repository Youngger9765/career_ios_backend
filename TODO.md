# TODO - 開發任務清單

**最後更新**: 2025-12-27

---

## 任務一：Web 改版（Web Realtime Console）

### 1.1 紅綠燈卡片機制（視覺化風險等級）

**Backend ✅ 已完成**
- Response schema 包含 risk_level, severity, suggested_interval_seconds
- 動態分析間隔：Green 60s / Yellow 30s / Red 15s

**Frontend 待完成**:
- [ ] 根據 suggested_interval_seconds 動態調整 Timer
- [ ] 紅黃綠視覺化（顏色、大小、動畫）

---

## 任務三：iOS API 改版 - island_parents 租戶

### 3.1 Multi-Tenant 架構擴充
- [ ] 所有 table 都有 tenant_id 欄位
- [ ] API 自動注入 tenant_id（基於 JWT）
- [ ] Query 自動過濾 tenant（避免跨租戶資料洩漏）

### 3.2 Client 物件簡化（island_parents 專用）
- [ ] island_parents 的 Client 只需兩個 required 欄位：name + grade (1-12)
- [ ] Optional 欄位：birth_date, gender, notes
- [ ] DB Schema 調整：新增 grade 欄位，既有欄位改 nullable
- [ ] Schema Validation：ClientCreateIslandParents
- [ ] API 路由分離：POST /api/v1/island/clients

### 3.3 Session 資料結構調整

**3.3.1 新增欄位**:
- [ ] scenario_topic (String, optional) - 練習情境
- [ ] mode (String, required) - practice / emergency
- [ ] partial_segments (JSONB) - 儲存 partial 分析片段
- [ ] partial_last_updated_at (DateTime)

**3.3.2 錄音同意流程（實戰模式）**:
- [ ] 設計錄音同意文案與流程（法務審核）
- [ ] POST /api/v1/island/sessions/{id}/consent API
- [ ] RecordingConsent Model + migration
- [ ] iOS：實戰模式開始前顯示同意彈窗
- [ ] 隱私政策與合規審查（GDPR, 個資法）

**3.3.3 使用記錄邊界情境處理**:
- [ ] 定義邊界情境規則（中途取消、離線、靜音）
- [ ] 增量更新 SessionUsage（每 30 秒）
- [ ] Session 異常結束自動補完（cron job）
- [ ] Admin 爭議處理 API

**3.3.4 前端使用時長與點數顯示**:
- [ ] GET /api/v1/island/credits/balance API
- [ ] 低點數警告邏輯（< 100 黃色，< 20 紅色）
- [ ] iOS/Web 即時顯示 UI

### 3.4 自動存檔功能（三段式 API）

**Phase 1: 開始錄音**:
- [ ] POST /api/v1/island/sessions - 建立空 Session
- [ ] 回傳 session_id 給 App

**Phase 2: 錄音中**:
- [ ] POST /api/v1/island/sessions/{id}/analyze-partial
- [ ] 儲存 partial segment 到 JSONB
- [ ] 執行即時分析（紅黃綠燈判斷）
- [ ] 計算與前一張卡片的相似度
- [ ] 回傳分析結果（含 should_merge）

**Phase 3: 結束錄音**:
- [ ] PATCH /api/v1/island/sessions/{id}/complete
- [ ] 更新完整逐字稿
- [ ] Fallback 機制：若 full_transcript 為空，使用 partial_segments 拼接

**3.4.2 報告展示層級與RAG術語可見性**:
- [ ] 定義 RAG 理論標籤顯示規則（產品決策）
- [ ] 定義專業術語處理方式（產品決策）
- [ ] 報告 Schema 調整（支援可選顯示）
- [ ] iOS/Web UI 調整（摺疊/展開、tooltip）

### 3.5 即時分析 API 改版
- [ ] 使用相同的 response schema（與 Web 版一致）
- [ ] island_parents 租戶專用的 Prompt 調整
- [ ] RAG 知識庫：使用親子教養相關知識

### 3.6 Case 管理簡化
- [ ] 預設 Case 自動建立（「親子溝通成長」）
- [ ] API 簡化：Create Session 時自動使用預設 Case

**3.6.3 點數有效期與結算細則**:
- [ ] 定義點數有效期規則（產品決策：每學期/半年/一年）
- [ ] 定義到期處理規則（歸零/滾存/延期）
- [ ] CreditPackage Model 更新（新增 expires_at 等欄位）
- [ ] 到期自動處理 Cron Job（每日 00:00）
- [ ] GET /api/v1/island/credits/expiry API
- [ ] POST /api/v1/admin/credits/extend-expiry API（Admin 手動延期）
- [ ] Email 通知整合（到期前 7 天 + 1 天）

---

## 任務四：密碼管理與通知系統

### 4.1 帳號建立後自動發送密碼信件
- [ ] 整合 Email 服務（SendGrid / AWS SES / SMTP）
- [ ] 設定 Email 模板（歡迎信件）
- [ ] 修改 POST /api/v1/admin/counselors 觸發發送
- [ ] EmailLog Model（記錄發送狀態）

### 4.2 密碼重設頁面（Web）
- [ ] 密碼重設請求頁面（/reset-password）
- [ ] PasswordResetToken Model（token, expires_at, used）
- [ ] 密碼重設確認頁面（/reset-password/confirm?token={token}）
- [ ] 發送密碼重設信件

### 4.3 密碼重設 API（給 iOS 使用）
- [ ] POST /api/v1/auth/password-reset/request
- [ ] POST /api/v1/auth/password-reset/verify
- [ ] POST /api/v1/auth/password-reset/confirm
- [ ] Token 安全：加密隨機字串（32+ 字元）、1 小時有效期、只能使用一次
- [ ] 請求頻率限制（5 分鐘內只能請求一次）

### 4.4 整合測試與文檔
- [ ] 完整流程測試（建立帳號 → 歡迎信 → 密碼重設）
- [ ] API 文檔更新（Swagger UI）
- [ ] 開發者文檔（環境變數、部署指南）

### 4.5 登入失敗提示語統一（資安）
- [ ] Backend: 統一 API 錯誤訊息（密碼錯誤 = 帳號不存在 = "登入資料有誤"）
- [ ] iOS/Web: 統一前端錯誤提示 UI
- [ ] 文檔: 登入失敗訊息規範

### 4.6 Email 發信系統與錯誤處理
- [ ] 選擇並設定 Email 服務商（Gmail SMTP / SendGrid / AWS SES）
- [ ] EmailLog Model（status: pending/sent/delivered/bounced/failed）
- [ ] Email Service 實作（發送 + 錯誤處理 + 退信處理）
- [ ] GET /api/v1/admin/emails/logs API
- [ ] POST /api/v1/admin/emails/resend API
- [ ] 用戶端重發機制（5 分鐘限制）

### 4.7 密碼強度政策與安全策略
- [ ] 定義密碼規則（最低 8 字元，英文 + 數字）
- [ ] 弱密碼黑名單（123456, password, qwerty...）
- [ ] Counselor Model 更新（failed_login_attempts, locked_until）
- [ ] 登入失敗鎖定機制（5 次失敗 → 鎖定 15 分鐘）
- [ ] 密碼驗證邏輯（Backend）
- [ ] iOS/Web 即時密碼強度檢查 UI
