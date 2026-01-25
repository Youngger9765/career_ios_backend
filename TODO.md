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
- [x] 測試完整 Web 流程（已用 Chrome 完整測試：註冊 → 忘記密碼 → 重設密碼 → 新密碼登入，全部成功）

### 網域與信任感
- [ ] 評估並選擇合適的網域（使用既有網域子網域或另買網域如 GoDaddy）
  - 🔴 阻塞原因：需要商業決策（用既有網域或購買新網域）
  - 建議：先決定網域策略
- [ ] 設定可信賴的網域用於 Web 重設密碼/條款頁面
  - 🔴 依賴：網域選擇完成
- [ ] 設定 support 信箱（用於寄送密碼重設郵件）
  - 🔴 阻塞原因：需要建立或指定 support email
- [ ] 配置網域 DNS 設定
  - 🔴 依賴：網域購買/選擇完成
- [ ] 確保 SSL 憑證正確配置
  - 🔴 依賴：網域設定完成
- [ ] 更新 `APP_URL` 環境變數指向新網域
  - 🔴 依賴：網域設定完成

### Landing Page 建立
- [ ] 設計 Landing Page 內容與版型
  - 🔴 阻塞原因：需要設計/行銷決策（內容、風格、品牌形象）
  - 建議：可以先用 frontend-design-workflow 生成設計提案
- [ ] 建立 Landing Page 模板（HTML/CSS）
  - 🟡 半阻塞：設計完成後可立即執行
- [ ] 整合到後端路由（如 `/` 或 `/landing`）
  - 🟡 半阻塞：設計完成後可立即執行
- [ ] 確保響應式設計（支援手機/桌面）
  - 🟡 半阻塞：設計完成後可立即執行
- [ ] 加入 App 下載連結（App Store）
  - 🟡 半阻塞：需要 App Store 連結
- [ ] 測試 Landing Page 在不同裝置上的顯示
  - 🟡 半阻塞：實作完成後可立即執行
- [ ] 部署並測試網域連線
  - 🔴 依賴：網域設定完成

## 高優先級 - 郵件服務

### SMTP 郵件服務遷移
- [ ] 將 SMTP mail 服務換成官方使用的郵件服務
  - 🔴 阻塞原因：需要決策使用哪個郵件服務
- [ ] 評估並選擇合適的郵件服務提供商（如 SendGrid, AWS SES, Mailgun 等）
  - 🔴 阻塞原因：需要商業決策（成本、功能評估）
  - 建議：可以先調研各服務商的優缺點
- [ ] 更新 SMTP 配置和環境變數
  - 🟡 半阻塞：服務商選定後可立即執行
- [ ] 更新 email 發送相關程式碼
  - 🟡 半阻塞：服務商選定後可立即執行
- [ ] 測試郵件發送功能
  - 🟡 半阻塞：程式碼更新後可立即執行
- [ ] 更新相關文件
  - 🟡 半阻塞：實作完成後可立即執行

## 高優先級 - 資料庫基礎設施

### Production 資料庫獨立
- [ ] Production 的 DB 要獨立（與 staging/dev 環境分離）
  - 🔴 阻塞原因：需要基礎設施決策與資源配置
  - 建議：評估 Supabase 或其他 PostgreSQL 託管服務的成本
- [ ] 設定獨立的 production 資料庫連線配置
  - 🔴 依賴：資料庫建立完成
- [ ] 更新環境變數和配置管理
  - 🟡 半阻塞：資料庫建立後可立即執行
- [ ] 確保資料庫備份策略
  - 🟡 半阻塞：資料庫建立後可立即執行
- [ ] 更新部署文件
  - 🟡 半阻塞：實作完成後可立即執行

## ✅ 已完成（2026-01-26）

### Code Quality ✅
- [x] `keyword_analysis_service.py` 進一步模組化 (663 lines → 390 lines)
  - 完成日期：2026-01-26
  - 實際影響：
    - 代碼減少 41%（273 行）
    - 創建 4 個專門模組（prompts, validators, metadata, simplified_analyzer）
    - 單一職責原則（SRP）實踐
    - 7 個整合測試通過
  - 相關文件：`app/services/analysis/keyword_analysis/`

### AI Output Validation 改進 ✅
- [x] 抽取共用 validation helper function (`app/services/utils/ai_validation.py`)
  - 完成日期：2026-01-26
  - 實際影響：
    - 創建 3 個核心函數（validate_ai_output_length, validate_finish_reason, apply_fallback_if_invalid）
    - 23 個單元測試通過
    - 4 個服務重構（emotion, quick_feedback, keyword_analysis, parents_report）
    - 完整文件（README + Quick Reference）
  - 相關文件：`app/services/utils/ai_validation.py`, `tests/unit/test_ai_validation.py`

- [x] 加 `finish_reason` 檢查 (針對 max_tokens 較小的 services)
  - 完成日期：2026-01-26
  - 實際影響：
    - 支援 Gemini 和 OpenAI 兩種 provider
    - emotion_service max_tokens 50 → 500（防止截斷）
    - 自動檢測 AI 輸出是否被截斷
    - 詳細日誌記錄供監控
  - 測試覆蓋：finish_reason 驗證測試通過

### 測試結果 ✅
- **整合測試**: 366 passed, 77 skipped, 0 failed
- **單元測試**: 23 passed (ai_validation)
- **代碼品質**: Ruff clean, 100% type hints
- **無迴歸**: 所有既有功能正常運作

## ⚠️ 需外部資源/決策（暫時無法執行）

### AI Output Validation - Dashboard
- [ ] AI output 監控 dashboard (fallback 使用率、over-limit warnings)
  - 🔴 阻塞原因：需要設計 dashboard 需求
  - 建議：先完成基礎 validation，dashboard 可延後
