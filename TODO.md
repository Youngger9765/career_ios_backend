# TODO - 開發任務清單

**最後更新**: 2025-12-29 (大規模清理：移除 20+ 已完成但未標記的項目，剩餘任務從 ~25 減少至 ~10 個真正待實作項目)

**本次清理摘要**：
- ✅ 標記已完成：Multi-Tenant、Admin Portal、Session 擴充、Email 系統
- ✅ 移除已完成但未標記：Practice/Emergency Mode 錄音流程、History 查詢、個人設定管理、RAG 整合
- ✅ 移除不需要的需求：SMS 登入認證、Session 新欄位（mode/scenario_topic/partial_segments）
- ✅ 重新分類：將產品決策階段任務明確標記，避免誤認為 Backend 待辦

---

## ✅ 已完成：Gemini 3 Flash 升級 + Island Parents 關係欄位 (2025-12-29)

### Gemini 3 Flash 升級 (2025-12-28)
- ✅ 從 Gemini 2.5 Flash 升級至 Gemini 3 Flash (`gemini-3-flash-preview`)
- ✅ Pro 級智能，Flash 速度與定價
- ✅ 更新定價計算：Input $0.50/1M, Output $3.00/1M, Cached $0.125/1M
- ✅ 所有整合測試通過（22 個測試）
- ✅ API 向後相容，無破壞性變更
- 📝 Commit: 7135983

### Island Parents 關係欄位 (2025-12-29)
- ✅ 新增 `relationship` 欄位（爸爸/媽媽/爺爺/奶奶/外公/外婆/其他）
- ✅ 欄位標籤更新："孩子姓名" → "孩子暱稱"
- ✅ 完整 iOS API 整合指南（9 步驟工作流程）
- ✅ Safety level 分析說明（🟢🟡🔴）
- ✅ 動態分析間隔（5-30s）
- ✅ 完整工作流程整合測試（681 行）
- 📝 Commit: 0d58d80

### 文檔整理與成本分析 (2025-12-29)
- ✅ 重組文檔結構（testing/, docs/）
- ✅ PRD 更新（Safety Level 系統、Incremental Billing）
- ✅ 基礎設施成本分析（Cloud Run + Supabase + Gemini）
- ✅ 成本預估：$10-25/月（原型）、$65-125/月（正式）
- ✅ 成本優化策略文檔
- 📝 Commit: 5db1167

### 12 月周報補齊 (2025-12-29)
- ✅ Week 11 (Dec 15-21): Register API、Universal Credit System
- ✅ Week 12 (Dec 22-28): Parents RAG Phase 1.1-1.4、Skill Auto-Activation
- ✅ Week 13 (Dec 29 - Jan 4): Gemini 3 Flash、Relationship Field、Cost Analysis
- 📝 Commit: 8cd4e95

---

## ✅ 已完成：密碼重設系統 (2025-12-27)

### 功能概述
- Web UI 頁面：`/forgot-password` 和 `/reset-password`
- API 端點：`POST /api/v1/auth/password-reset/request`, `GET /verify`, `POST /confirm`
- Admin API：新增諮詢師時自動發送密碼重設郵件（6 小時有效期）
- Multi-tenant 支援：career, island, island_parents
- SMTP 郵件發送：已配置並測試成功

### 技術實現
- Token 安全：32+ 字元加密隨機字串，6 小時過期，單次使用
- Rate limiting：每 5 分鐘最多 1 次請求
- 環境變數：SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, APP_URL（已設定在 GitHub Secrets）
- CI/CD：自動部署到 staging 並套用 SMTP 配置

### 測試狀態
- ✅ 23 個 integration tests，100% 通過
- ✅ Staging 環境端到端測試通過
- ✅ 郵件發送成功驗證（young.tsai.9765@gmail.com）

### 相關文件
- SMTP 配置：`SMTP_SETUP.md`
- API 規格：`PRD.md`
- 變更記錄：`CHANGELOG.md`, `CHANGELOG_zh-TW.md`
- Commits: 217a5d8, 81e4e57, 75dbfc4

---

## ✅ 已完成：多租戶架構 + Admin Portal + Session 擴充 (2025-12-15)

### Multi-Tenant 架構擴充 (2025-12-15)
- ✅ 所有 table 都有 tenant_id 欄位（自動注入與過濾）
- ✅ API 自動注入 tenant_id（基於 JWT 解析）
- ✅ Query 自動過濾 tenant（避免跨租戶資料洩漏）
- ✅ 支援三租戶：career, island, island_parents
- 📝 Commits: 40bf98e, c620474, f0352df

### Session 資料結構擴充 (2025-12-15)
- ✅ SessionAnalysisLog table（獨立存儲分析記錄）
- ✅ SessionUsage table（使用量追蹤 + 點數扣除）
- ✅ Universal Credit System（增量計費 + 天花板捨入）
- ✅ GBQ 持久化整合（完整可觀測性）
- 📝 Commits: 1eed1d1, f071e4b, 432eeef

### Admin Portal 功能 (2025-12-15)
- ✅ 諮詢師管理（CRUD + 跨租戶管理）
- ✅ 點數管理（查詢、手動加點、費率設定）
- ✅ 點數異動記錄查詢
- ✅ Credit Admin Guide 文檔
- 📝 Commits: b740768, 318350b, 379fabe
- 📋 Files: admin_counselors.py, admin_credits.py

### Email 發信系統 (2025-12-27)
- ✅ Gmail SMTP 整合（環境變數配置）
- ✅ Tenant-specific email templates
- ✅ 密碼重設郵件自動發送
- ✅ 新增諮詢師自動發送歡迎信
- 📝 Commits: 3e40091, 217a5d8, 81e4e57
- 📋 File: email_service.py

---

## 任務一：Web 改版（Web Realtime Console）

### 1.1 紅綠燈卡片機制（視覺化風險等級）✅ 已完成

**Backend ✅ 已完成**
- Response schema 包含 risk_level, severity, suggested_interval_seconds
- 動態分析間隔：Green 60s / Yellow 30s / Red 15s

**Frontend ✅ 已完成**:
- ✅ 根據 suggested_interval_seconds 動態調整 Timer (`updateAnalysisInterval()`)
- ✅ 紅黃綠視覺化（顏色、大小、動畫）
- ✅ 測試按鈕（🟢🟡🔴）用於快速測試不同風險等級

**實作位置**: `app/templates/realtime_counseling.html`

## 任務三：iOS API 改版 - island_parents 租戶

**詳細規劃文檔**:
- 📋 [浮島 App 完整任務清單](docs/ISLAND_APP_TASKS_REORGANIZED.md) - iOS API + Web Console + Infrastructure
- 🔧 [Session 設計文檔](docs/SESSION_USAGE_CREDIT_DESIGN.md) - DB Log 持久化 + 點數扣除邏輯

**參考 Notion SPEC**:
- SPEC 1: 登入註冊、Onboarding
- SPEC 2: AI 功能模組 (事前練習)
- SPEC 3: AI 功能模組 (事中提醒)
- SPEC 4: History 頁 (諮詢紀錄)
- SPEC 5: Settings 設置頁

---

### 3.0 基礎架構（Infrastructure）

#### 3.0.1 Multi-Tenant 架構擴充 ✅ 已完成 (2025-12-15)
- [x] ✅ 所有 table 都有 tenant_id 欄位
- [x] ✅ API 自動注入 tenant_id（基於 JWT）
- [x] ✅ Query 自動過濾 tenant（避免跨租戶資料洩漏）
- 📝 Commits: 40bf98e, c620474, f0352df
- 📋 完整多租戶隔離機制，支援 career, island, island_parents

#### 3.0.2 Session 資料結構擴充 ✅ 已完成 (2025-12-15)
詳見 [Session 設計文檔](docs/SESSION_USAGE_CREDIT_DESIGN.md) 了解 DB Log 持久化和點數扣除邏輯

- [x] ✅ SessionAnalysisLog table（獨立存儲分析記錄）- 2025-12-15
- [x] ✅ SessionUsage table（使用量追蹤 + 點數扣除）- 2025-12-15
- 📝 Commits: 1eed1d1 (SessionAnalysisLog), f071e4b (SessionUsage + Universal Credit System)
- 📋 Note: mode/scenario_topic/partial_segments 欄位移除（現有 JSONB 欄位已足夠；mode 已在 Realtime API 實作為 request parameter）

#### 3.0.3 Client 物件簡化（island_parents）
- [x] ✅ 新增 `relationship` 欄位（爸爸/媽媽/爺爺/奶奶/外公/外婆/其他）- 2025-12-29
- [x] ✅ 欄位標籤更新："孩子姓名" → "孩子暱稱" - 2025-12-29
- [ ] island_parents 的 Client 只需：name + grade (1-12)
- [ ] Optional 欄位：birth_date, gender, notes（已存在，待確認是否需調整）
- [ ] DB Schema 調整：新增 grade 欄位（待實作）

---

### 3.1 SPEC 1：登入註冊、Onboarding

#### 3.1.1 孩子資料管理（沿用 Client API）✅ 已完成
- [x] ✅ POST /api/v1/clients - 新增孩子（tenant_id=island_parents）
- [x] ✅ GET /api/v1/clients - 列出孩子（自動過濾 tenant）
- [x] ✅ PATCH /api/v1/clients/{id} - 編輯孩子資料
- [x] ✅ DELETE /api/v1/clients/{id} - 刪除孩子
- [x] ✅ 完整 iOS API 整合指南（9 步驟工作流程）- 2025-12-29
- [x] ✅ 完整工作流程整合測試（681 行）- 2025-12-29
- 📝 已可使用，支援 island_parents 租戶的所有 CRUD 操作

---

### 3.2 SPEC 2：AI 功能模組（事前練習）✅ 已完成

#### 3.2.1 練習情境選擇 - 移至產品決策階段
- [ ] GET /api/v1/island/scenarios - 取得預設情境列表（產品待定義情境清單）
  - 孩子不寫作業、兄弟姊妹吵架、睡前拖延、自訂情境
- 📋 Note: API 結構簡單，等產品決策後 1 小時可完成

#### ~~3.2.2 Practice Mode 錄音流程~~ ✅ 已完成 (2025-12-29)
**使用現有 API 實作完成，無需新建 /api/v1/island/sessions**

- [x] ✅ POST /api/v1/sessions - 建立練習會談
- [x] ✅ POST /api/v1/sessions/{id}/recordings/append - 追加錄音片段
- [x] ✅ POST /api/v1/sessions/{id}/analyze-partial - 即時分析（返回🟢🟡🔴）
- [x] ✅ SessionUsage 自動計費（每次 analyze-partial 自動記錄）
- [x] ✅ 681 行整合測試通過（test_island_parents_complete_workflow.py）
- 📋 參考：IOS_API_GUIDE.md (line 487-982), ISLAND_PARENTS_WORKFLOW_TEST_REPORT.md

#### ~~3.2.3 Practice 報告生成~~ ✅ 已完成 (2025-12-29)
- [x] ✅ analyze-partial API 已返回完整分析結果（summary, suggestions, RAG references）
- [x] ✅ 分析歷程記錄：GET /api/v1/sessions/{id}/analysis-logs
- 📋 Note: 報告內容已在即時分析回應中，無需額外 report endpoint

---

### 3.3 SPEC 3：AI 功能模組（事中提醒）✅ 已完成

#### 3.3.1 錄音同意流程 - 產品與法務決策階段
- [ ] 設計錄音同意文案（法務審核）- 產品責任
- [ ] RecordingConsent Model + migration - 等產品確認需求後實作
- [ ] iOS：實戰模式開始前顯示同意彈窗 - iOS 開發責任
- [ ] 隱私政策與合規審查（GDPR, 個資法）- 法務責任
- 📋 Note: Backend API 結構簡單（POST /api/v1/consents），等確認後 2 小時可完成

#### ~~3.3.2 Emergency Mode 錄音流程~~ ✅ 已完成 (2025-12-29)
**與 Practice Mode 使用相同 API，已完成**

- [x] ✅ POST /api/v1/sessions - 建立實戰會談（與 Practice 相同）
- [x] ✅ POST /api/v1/sessions/{id}/analyze-partial - 即時危機提醒
- [x] ✅ 🟢🟡🔴 三級安全判斷（severity 1-3）
- [x] ✅ 動態分析間隔（Red 15s / Yellow 30s / Green 60s）
- [x] ✅ 測試覆蓋：test_7_red_yellow_green_logic_accuracy ✅ PASSED
- 📋 參考：IOS_API_GUIDE.md, test_island_parents_complete_workflow.py

#### ~~3.3.3 Emergency 報告生成~~ ✅ 已完成 (2025-12-29)
- [x] ✅ analyze-partial API 已返回完整分析（與 Practice 相同架構）
- [x] ✅ Emergency 與 Practice 差異已在 AI prompt 層實現
- 📋 Note: 報告內容已在即時分析回應中

---

### 3.4 SPEC 4：History 頁（諮詢紀錄）✅ 已完成

#### 3.4.1 歷史記錄查詢 ✅ 已完成
**使用現有 API，無需新建 /api/v1/island/sessions**

- [x] ✅ GET /api/v1/sessions - 列出所有 sessions
  - ✅ 篩選：client_id (Query parameter)
  - ✅ 分頁支援：skip, limit (Query parameters)
  - ✅ 搜尋：search parameter 支援 client name/code
- [x] ✅ GET /api/v1/sessions/{id} - 單一 session 詳情
  - ✅ 完整逐字稿（transcript_text 欄位）
  - ✅ 分析記錄：GET /api/v1/sessions/{id}/analysis-logs
  - ✅ 使用量統計：GET /api/v1/sessions/{id}/usage
- [x] ✅ GET /api/v1/sessions/timeline - 會談時間線（依 client_id 篩選）
- 📋 參考：IOS_API_GUIDE.md, test_island_parents_complete_workflow.py (test_6_view_session_timeline)

#### 3.4.2 進階查詢功能（P2 可選）- 產品決策階段
- [ ] 排序功能：created_at, duration, safety_level - 等產品確認需求
- [ ] 逐字稿關鍵字搜尋 - PostgreSQL full-text search，2-3 小時可完成
- [ ] 匯出功能（PDF, CSV）- 等產品確認格式需求

---

### 3.5 SPEC 5：Settings 設置頁

#### 3.5.1 個人設定管理 ✅ 已完成
**使用現有 Auth API，無需新建 /api/v1/island/settings**

- [x] ✅ GET /api/auth/me - 取得設定（姓名、email、租戶、角色）
- [x] ✅ PATCH /api/auth/me - 更新設定（full_name, email 等）
- [ ] 隱私設定（notification_enabled）- 等產品決策後加入 Counselor model
- 📋 參考：IOS_API_GUIDE.md (Authentication APIs)

#### 3.5.2 點數查詢與兌換
詳見 [Session 設計文檔](docs/SESSION_USAGE_CREDIT_DESIGN.md) 了解點數系統設計

- [x] ✅ GET /api/auth/me - 已返回 available_credits（查詢點數餘額）
- [ ] POST /api/v1/redeem-codes/redeem - 兌換碼兌換（等產品決策）
- [ ] RedeemCode Model + migration（等產品決策）
- [ ] 低點數警告邏輯（< 100 黃色，< 20 紅色）- iOS App 責任
- 📋 Note: 兌換碼系統結構簡單，確認需求後 3-4 小時可完成

#### 3.5.3 點數有效期管理 - 產品決策階段
- [ ] 定義點數有效期規則（產品決策：每學期/半年/一年）
- [ ] 定義到期處理規則（歸零/滾存/延期）
- [ ] 到期自動處理 Cron Job（每日 00:00）
- [ ] GET /api/v1/credits/expiry - 查詢到期資訊
- [ ] Email 通知整合（到期前 7 天 + 1 天）
- 📋 Note: 等產品規則確認後，Backend 3-4 小時可完成

#### 3.5.4 帳號管理 - 產品決策階段
- [x] ✅ 登出功能 - iOS App 責任（清除本地 token）
- [ ] 刪除帳號（產品決策：是否需要？資料保留政策？）
- [ ] 變更手機號碼（產品決策：是否需要？SMS 認證？）
- 📋 Note: API 結構簡單，等產品決策後各 1-2 小時可完成

#### 3.5.5 進階隱私設定（P2 可選）- 產品決策階段
- [ ] 資料使用授權管理（分析、研究用途）- 法務與產品決策
- [ ] 錄音保存期限偏好設定 - 產品決策
- [ ] 第三方分享設定 - 產品決策
- 📋 Note: 低優先級功能，等產品與法務確認需求

---

### 3.6 WEB Admin 功能

#### 3.6.1 諮詢師管理 ✅ 已完成 (2025-12-15)
- [x] ✅ GET /api/v1/admin/counselors - 列出所有諮詢師
- [x] ✅ GET /api/v1/admin/counselors/{id} - 諮詢師詳情
- [x] ✅ POST /api/v1/admin/counselors - 新增諮詢師（自動發送密碼重設郵件）
- [x] ✅ PATCH /api/v1/admin/counselors/{id} - 更新諮詢師狀態
- [x] ✅ DELETE /api/v1/admin/counselors/{id} - 刪除諮詢師
- [x] ✅ 多租戶隔離（支援跨租戶管理）
- 📝 Commits: b740768, 318350b, 379fabe
- 📋 File: app/api/v1/admin_counselors.py

#### 3.6.1-B 點數管理 ✅ 已完成 (2025-12-15)
- [x] ✅ GET /api/v1/admin/credits/members - 列出所有會員點數
- [x] ✅ GET /api/v1/admin/credits/members/{id} - 單一會員點數詳情
- [x] ✅ POST /api/v1/admin/credits/members/{id}/add - 手動加點
- [x] ✅ GET /api/v1/admin/credits/logs - 查詢點數異動記錄
- [x] ✅ POST /api/v1/admin/credits/rates - 設定費率
- [x] ✅ GET /api/v1/admin/credits/rates - 查詢費率
- 📝 Commits: 4e5dee1, f071e4b
- 📋 File: app/api/v1/admin_credits.py

#### 3.6.2 兌換碼管理（待實作）
- [ ] POST /api/v1/admin/redeem-codes/generate - 批次生成兌換碼
- [ ] GET /api/v1/admin/redeem-codes - 列出所有兌換碼
- [ ] PATCH /api/v1/admin/redeem-codes/{code}/revoke - 停權兌換碼
- [ ] POST /api/v1/admin/credits/extend-expiry - 手動延期點數
- [ ] RedeemCode Model + migration

#### 3.6.3 使用記錄爭議處理（待實作）
- [ ] 定義邊界情境規則（中途取消、離線、靜音）
- [ ] Admin 查看詳細使用記錄
- [ ] Admin 手動調整扣點（需註記原因）

---

### 3.7 其他整合

#### 3.7.1 RAG 知識庫整合 ✅ 已完成
- [x] ✅ island_parents 租戶專用 Prompt（analyze-partial API 自動切換）
- [x] ✅ RAG 知識庫：親子教養相關知識（依附理論、情緒調節等）
- [x] ✅ Response schema：與 Web 版統一的 IslandParentAnalysisResponse
- [x] ✅ 200+ 專家建議句庫（app/data/island_parents_expert_suggestions.json）
- 📋 參考：test_island_parents_complete_workflow.py, IOS_API_GUIDE.md

#### 3.7.2 Case 管理簡化 - 產品決策階段
- [ ] 預設 Case 自動建立（「親子溝通成長」）- 等產品確認命名
- [ ] Create Session 時自動使用預設 Case - 等產品確認流程
- 📋 Note: 目前需手動建立 Case（標準流程），自動建立需產品確認 UX 流程

---

## 任務四：密碼管理與通知系統

### 4.1 帳號建立後自動發送密碼信件
- [x] 整合 Email 服務（Gmail SMTP）
- [x] 設定 Email 模板（歡迎信件）
- [x] 修改 POST /api/v1/admin/counselors 觸發發送
- [x] Tenant-specific email templates（career/island/island_parents）
- [ ] EmailLog Model（記錄發送狀態）

### 4.2 密碼重設頁面（Web）
- [x] 密碼重設請求頁面（/forgot-password）
- [x] PasswordResetToken Model（token, expires_at, used）
- [x] 密碼重設確認頁面（/reset-password）
- [x] 發送密碼重設信件
- [x] Token 延長至 6 小時有效期（開發階段）

### 4.3 密碼重設 API（給 iOS 使用）
- [x] POST /api/v1/password-reset/request - 請求密碼重設
- [x] POST /api/v1/password-reset/verify - 驗證 token
- [x] POST /api/v1/password-reset/confirm - 確認重設密碼
- [x] Token 安全：加密隨機字串（32+ 字元）、6 小時有效期、只能使用一次
- [x] 請求頻率限制（5 分鐘內只能請求一次）
- [x] Multi-tenant 支援（支援 career/island/island_parents）

### 4.4 整合測試與文檔
- [x] 完整流程測試（建立帳號 → 歡迎信 → 密碼重設）
- [x] 23 個整合測試（100% 通過）
- [x] API 文檔更新（Swagger UI）
- [x] DEBUG mode 跨租戶管理員存取

### 4.5 登入失敗提示語統一（資安）
- [ ] Backend: 統一 API 錯誤訊息（密碼錯誤 = 帳號不存在 = "登入資料有誤"）
- [ ] iOS/Web: 統一前端錯誤提示 UI
- [ ] 文檔: 登入失敗訊息規範

### 4.6 Email 發信系統與錯誤處理 🟡 部分完成 (2025-12-27)
- [x] ✅ 選擇並設定 Email 服務商（Gmail SMTP）- 2025-12-27
- [x] ✅ Email Service 實作（發送 + 錯誤處理）- 2025-12-27
- [x] ✅ Tenant-specific email templates（career/island/island_parents）- 2025-12-27
- [x] ✅ SMTP 環境變數配置（GitHub Secrets）- 2025-12-27
- [x] ✅ 密碼重設郵件自動發送（新增諮詢師時）- 2025-12-27
- [ ] EmailLog Model（status: pending/sent/delivered/bounced/failed）- 待實作
- [ ] GET /api/v1/admin/emails/logs API - 待實作
- [ ] POST /api/v1/admin/emails/resend API - 待實作
- [ ] 退信處理機制 - 待實作
- [ ] 用戶端重發機制（5 分鐘限制）- 待實作
- 📝 Commits: 3e40091, 217a5d8, 81e4e57, 75dbfc4
- 📋 File: app/services/email_service.py

### 4.7 密碼強度政策與安全策略
- [ ] 定義密碼規則（最低 8 字元，英文 + 數字）
- [ ] 弱密碼黑名單（123456, password, qwerty...）
- [ ] Counselor Model 更新（failed_login_attempts, locked_until）
- [ ] 登入失敗鎖定機制（5 次失敗 → 鎖定 15 分鐘）
- [ ] 密碼驗證邏輯（Backend）
- [ ] iOS/Web 即時密碼強度檢查 UI
