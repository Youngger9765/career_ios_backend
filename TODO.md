# TODO

**Last Updated**: 2026-02-03

---

## 👤 Young 負責項目（2026-01-31）

### App 配置 API（動態連結管理）
- [ ] **建立 App Config API，回傳動態連結給 iOS** 🔴 Young
  - **目的**：iOS 端不需硬編碼 URL，從後端動態獲取
  - **端點**：`GET /api/v1/app/config`
  - **Response 包含**：
    ```json
    {
      "terms_url": "https://duodian.com/career/terms",
      "privacy_url": "https://duodian.com/career/privacy",
      "landing_page_url": "https://duodian.com/career",
      "help_url": "https://duodian.com/career/help",
      "forgot_password_url": "https://duodian.com/career/forgot-password",
      "base_url": "https://career-app-api-prod-xxx.run.app",
      "version": "1.0.0",
      "maintenance_mode": false
    }
    ```
  - **優點**：
    - iOS 不需每次更新 URL 都發版
    - 支援 A/B testing（不同環境不同 URL）
    - 支援維護模式切換
  - **實作**：
    - Schema: `AppConfigResponse`
    - Router: `app/api/app_config.py`
    - Config: 從環境變數讀取 URL（`.env`）

### 註冊/登入 API 修改
- [ ] **註冊/登入 API Response 調整** 🔴 Young
  - **需求**：加入郵件驗證狀態欄位
  - **Response 包含**：
    - 註冊：`email_verified: false`, `verification_email_sent: true`
    - 登入成功：`user.email_verified: true`
    - 登入失敗（未驗證）：HTTP 403 + `EMAIL_NOT_VERIFIED` error code
  - **錯誤訊息設計**：
    - 未驗證：`"Please verify your email before logging in"`
    - Rate limit：`"Too many attempts. Try again in 60 seconds"`
  - 參考上方詳細設計（Line 10-13 above）
  - 相關：目前「註冊安全性增強」已在進行中（郵件驗證、Rate Limiting、密碼強度）

### 忘記密碼調整
- [x] **Deeplink Redirect** ✅ 已完成 (2026-01-30)
  - App vs Web 來源區分
  - Deeplink + Fallback 機制
  - Email 自動帶入功能
  - 參考：Line 27-51

### 網域與部署
- [ ] **Landing page, Terms & Privacy 頁面部署到逗點網域** 🔴 Young 協助
  - [ ] KM 先準備文案內容
  - [ ] 設計 Landing Page（可用 frontend-design-workflow）
  - [ ] 建立 Terms & Privacy 頁面
  - [ ] 部署到逗點子網域
  - [ ] 請 Allen 更新 iOS App 中的連結
  - 參考：Line 118-146 (網域與信任感 + Landing Page 建立)

### 使用量限制
- [x] **每個月使用量隱藏上限設定** ✅ 已完成 (2026-01-31)
  - [x] 上限設定：6 小時/月 (360 分鐘)
  - [x] 計費模式：prepaid / subscription
  - [x] 重置週期：Rolling 30 天
  - [x] 超限行為：HTTP 429 + 詳細訊息
  - [x] API 端點：GET /api/v1/usage/stats
  - 實作：Middleware + UsageTracker service
  - 完成時間：2026-01-31
  - 對應 Issue：#8

### 基礎設施
- [ ] **Production DB、GCP 持久化建立** 🔴 待決策與資源配置
  - [ ] 評估 PostgreSQL 託管服務（Supabase 或其他）
  - [ ] 建立獨立 Production 資料庫
  - [ ] 設定備份策略
  - [ ] 更新環境變數配置
  - [ ] **調整 PROD DB 參數** 🔴 Young
    - 檢查當前 DB 配置（連線池、timeout、max_connections）
    - 根據實際負載調整參數優化效能
    - 更新環境變數（DATABASE_URL, DB_POOL_SIZE 等）
  - 參考：Line 150-161 (Production 資料庫獨立)

### iOS 整合
- [x] **Deeplink to iOS** ✅ 已完成 (2026-01-30)
  - 忘記密碼完成後 deeplink 回 App
  - Fallback 機制（3 秒後檢測）
  - 參考：Line 29-44

- [ ] **iOS 團隊確認 Deeplink 整合** 🔴 待 iOS 團隊測試
  - [ ] 在 Info.plist 註冊 `islandparent://` URL scheme
  - [ ] 實作 AppDelegate deeplink handler (`islandparent://auth/forgot-password-done`)
  - [ ] 使用 SFSafariViewController 開啟忘記密碼頁面
  - [ ] 傳入 email 參數：`?source=app&mail={email}`
  - [ ] 測試完整流程：App → 忘記密碼網頁 → 重設密碼 → Deeplink 返回 App
  - **後端已完成**：deeplink URL、網頁邏輯、文件更新
  - **參考文件**：`IOS_GUIDE_PARENTS.md` (已更新 313 行)

---

## 🚨 緊急 - Production 上線驗證

### Emotion-Feedback API Production 驗證
- [ ] **Production 上線前驗證** 🔴 待 Allen 測試確認
  - [ ] Allen 使用 App 實測 emotion-feedback
  - [ ] 確認空 context 首次呼叫成功
  - [ ] 確認第二次呼叫（有 context）成功
  - [ ] 驗證完成後才可推送至 Production

**測試帳號** (已 seed):
- Island Parents: `counselor@island.com` / `password123`
- Career: `counselor@career.com` / `password123`

**測試步驟**:
1. 登入 console.html 或 App
2. 建立新 session
3. 呼叫 `/api/v1/sessions/{session_id}/emotion-feedback`
4. 第一次呼叫使用 `context=""` (空字串) - 應成功 (不應 422)
5. 檢查 response 包含 `level`, `hint`, `token_usage` - 應成功 (不應 500)

---

## 高優先級 - 訂閱註冊與付費流程 (Paywall / IAP)

### 忘記密碼流程優化（AllenLee 需求 2026-01-29）

#### Deeplink Redirect（App 來源區分）✅ 完成 (2026-01-30)
- [x] 密碼重設完成頁面區分 App vs Web 來源
  - 方案：URL 加 `?source=app` 參數區分
  - App 來的：重設完成後 redirect 到 `islandparent://auth/forgot-password-done`
  - Web 來的：維持現有行為（顯示返回登入連結）
  - **Fallback 機制**：3 秒後檢測 `document.visibilityState`，App 未開啟則自動跳轉網頁
- [x] 修改 email 中的重設連結，App 發起的請求帶上 `source=app` 參數
  - 例：`/island-parents/reset-password?token=xxx&source=app`
  - 實作於 `email_sender.py:send_password_reset_email`
- [x] 修改 `reset_password.html` 重設成功後的 redirect 行為
  - 新增 `handleSuccessRedirect()` 函數處理 deeplink + fallback
  - 讀取 `source` 參數，若為 `app` → 嘗試 deeplink，3 秒後檢查失敗則跳轉網頁
  - 否則 → 直接返回登入頁面
- [x] 修改 forgot-password 請求 API / email 發送邏輯，傳遞 `source` 參數
  - Schema: `PasswordResetRequest.source` (Optional, backward compatible)
  - API: `password_reset.py` 傳遞 source 給 email sender

#### Email 自動帶入 ✅ 完成 (2026-01-30)
- [x] forgot-password 頁面支援 `?mail=` query parameter 預填 email
  - 例：`/island-parents/forgot-password?mail=allen@gmail.com`
  - 修改 `forgot_password.html`，讀取 URL `mail` 參數自動填入 email 欄位
  - 自動 focus 到提交按鈕提升 UX
- [x] App 端開啟 forgot-password 頁面時帶上使用者 email（iOS 端實作）

### 註冊安全性增強（2026-01-30）🔄 實作中

**背景**：
- 目前註冊流程無郵件驗證、無 Rate Limiting
- 存在高風險：假帳號氾濫、自動化攻擊、資源濫用

**需求**：
- [ ] **郵件驗證功能**（可開關設計）✅ 確認實作，預設啟用
  - 環境變數：`ENABLE_EMAIL_VERIFICATION=true/false`（預設 true）
  - 註冊流程：註冊 → 發送驗證信 → 點擊連結 → 啟用帳號
  - 未驗證帳號：`is_active=False`，無法登入
  - 驗證連結：24 小時有效期
  - 重發驗證信：API endpoint `/api/v1/auth/resend-verification`

- [ ] **Rate Limiting**（永久啟用）🔄 實作中（agent-manager 執行中）
  - **設計決策**：不提供開關，作為安全基線永久啟用
  - 註冊限制：同 IP 每小時最多 3 次
  - 登入限制：同 IP 每分鐘最多 5 次
  - 忘記密碼限制：同 IP 每小時最多 3 次
  - 使用 slowapi memory-based 實作
  - 開發環境：寬鬆限制（100/20/20）
  - Production：嚴格限制（3/5/3）

- [ ] **密碼強度驗證增強**（永久啟用）🔄 實作中（agent-manager 執行中）
  - **設計決策**：作為安全基線，不提供開關
  - 至少 12 字元（目前 8 字元）
  - 必須包含大小寫 + 數字 + 特殊字元
  - 檢查常見密碼清單

**實作原則**：
- **Rate Limiting & 密碼強度**：永久啟用（安全基線）
- **郵件驗證**：可透過環境變數開關，**預設 enabled**
- 所有功能都要實作並啟用（「通通 enable」）
- 完整測試覆蓋

**影響範圍**：
- Files: `app/api/auth.py`, `app/core/config.py`, `app/services/external/email_sender.py`, `app/middleware/rate_limit.py`
- Tests: 18-20 integration tests
- Complexity: High (3 days)

---

### Base URL 統一（AllenLee 回報 2026-01-29）
- [ ] iOS 端 base URL 需更新（Allen 負責）
  - 舊：`https://career-app-api-staging-kxaznpplqq-uc.a.run.app`
  - 新：`https://career-app-api-staging-978304030758.us-central1.run.app`
  - Production 也要確認：`career-app-api-prod-kxaznpplqq-uc.a.run.app` → 待確認新 URL
- [ ] 後端文件 base URL 更新（IOS_GUIDE_PARENTS.md 等）
  - `IOS_GUIDE_PARENTS.md` 中多處引用需確認一致
  - 舊 weekly reports 仍引用舊 URL（已過期，不需改）
- [ ] 確認兩個 URL 是否都還能用（Cloud Run 可能兩個都有效）

### 使用量軟性上限（防濫用機制）
- [ ] **設定每月使用量 Soft Cap** 🔴 待規格確認
  - 對外：「一個月無限使用」（行銷話術）
  - 實際：後端設定隱藏上限，超過後禁止使用
  - 目的：防止惡意濫用、保護系統資源
  - 需確認：
    - 上限數值（例：每月 1000 次 API 呼叫？）
    - 計數範圍（所有 API？僅 AI 相關？）
    - 超限行為（HTTP 429？友善提示？）
    - 重置週期（每月 1 號？註冊日起算？）
  - 實作位置：Middleware / User model
  - 🔴 阻塞原因：需要產品/商業決策（上限數值、計費策略）

### 網域與信任感
- [ ] **將 WEB 放在逗點網域** 🔴 待 Young 協助
  - 後端 Web 頁面（forgot-password, reset-password, terms, privacy 等）部署到逗點網域
  - 需與逗點網域管理員協調
- [ ] 設定可信賴的網域用於 Web 重設密碼/條款頁面
  - 🟡 半阻塞：等逗點確認子網域後可執行
- [ ] 配置網域 DNS 設定
  - 🟡 半阻塞：等逗點確認後可執行
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

## ⚠️ 需外部資源/決策（暫時無法執行）

### AI Output Validation - Dashboard
- [ ] AI output 監控 dashboard (fallback 使用率、over-limit warnings)
  - 🔴 阻塞原因：需要設計 dashboard 需求
  - 建議：先完成基礎 validation，dashboard 可延後
