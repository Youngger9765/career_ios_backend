# TODO

## 高優先級 - 訂閱註冊與付費流程 (Paywall / IAP)

### 註冊 API 簡化 ✅ 已完成
- [x] 修改 `RegisterRequest` schema (`app/schemas/auth.py`)：只保留 `email` 和 `password` 為必填
- [x] 修改資料庫模型：將 `username` 和 `full_name` 改為 `nullable=True`
- [x] 建立 Alembic migration (`20260124_1156_047d37606423_make_username_and_full_name_nullable_.py`)
- [x] 修改註冊 API (`app/api/auth.py`)：允許 `username` 和 `full_name` 為 `None`
- [x] 修改相關 Response schemas：`CounselorInfo`, `CounselorDetailResponse`, `CounselorListItem`, `CounselorCreditInfo` 的 `username` 和 `full_name` 改為 `Optional[str]`
- [x] 處理密碼重設 email 中 `full_name` 為 `None` 的情況
- [x] 處理 admin API 中 `full_name` 為 `None` 的情況
- [x] 修正搜尋邏輯：處理 `username` 和 `full_name` 為 `NULL` 時的搜尋
- [x] 更新相關測試 (`tests/integration/test_auth_api.py`)
- [x] 更新 API 文件 (`IOS_API_GUIDE.md`)
- [x] 更新 console-steps.js：簡化註冊表單，正確處理 nullable 欄位
- [x] 更新後端更新 API：允許清空欄位（空字串轉換為 `None`）

### 忘記密碼 Web 流程確認 ✅ 已完成
- [x] Web 頁面已存在：`/forgot-password` 和 `/reset-password`
- [x] API 端點已存在：`/api/v1/auth/password-reset/request`, `/verify`, `/confirm`
- [x] 確認 Web 流程實作方式符合需求：
  - App 點「忘記密碼」→ 開啟 Web 頁面 (`/forgot-password`)
  - 使用者輸入 Email → 發送重設信
  - 點信中連結 → 導向 Web 設定新密碼頁面 (`/reset-password?token=...`)
  - 設定新密碼後 → 回 App 用新密碼登入
- [x] 確認重設密碼 email 中的連結格式正確指向 Web 頁面：`{app_url}/reset-password?token={reset_token}`
- [ ] 測試完整 Web 流程（需要實際測試，非程式碼問題）

## 高優先級 - 郵件服務

### SMTP 郵件服務遷移
- [ ] 將 SMTP mail 服務換成官方使用的郵件服務
- [ ] 評估並選擇合適的郵件服務提供商（如 SendGrid, AWS SES, Mailgun 等）
- [ ] 更新 SMTP 配置和環境變數
- [ ] 更新 email 發送相關程式碼
- [ ] 測試郵件發送功能
- [ ] 更新相關文件

## Nice-to-Have (Low Priority)

### AI Output Validation 改進
- [ ] 抽取共用 validation helper function (`app/services/utils/ai_validation.py`)
- [ ] 加 `finish_reason` 檢查 (針對 max_tokens 較小的 services)
- [ ] AI output 監控 dashboard (fallback 使用率、over-limit warnings)

### Code Quality
- [ ] `keyword_analysis_service.py` 進一步模組化 (663 lines, 超過 400 limit)
