# TODO

## 🚨 緊急 - Bug 修復上線驗證

### Emotion-Feedback API Bug 修復確認 ✅ 已完成 (2026-01-29)
- [x] 修復 422 錯誤：允許空 context 欄位 (commit: c8cfe7b)
  - **問題**: Pydantic schema `min_length=1` 限制
  - **修復**: 改為 `default=""` 無 min_length
  - **檔案**: `app/schemas/session.py:604`

- [x] 修復 400 錯誤：移除 route handler 多餘的 empty context 檢查 (commit: 2af6ab2)
  - **問題**: `app/api/sessions.py:554` 有第二層 `if not request.context` 檢查
  - **修復**: 移除該檢查，允許首次呼叫 context 為空
  - **檔案**: `app/api/sessions.py`

- [x] 修復 500 錯誤：Token usage 提取失敗 (commit: c8cfe7b)
  - **問題**: `get_last_token_usage()` 方法不存在導致內部錯誤
  - **修復**: 直接從 `response.usage_metadata` 提取 token 使用量
  - **檔案**: `app/services/analysis/emotion_service.py`

- [x] CI/CD 通過：Staging 環境已部署 (2026-01-29 02:26)
- [x] **Staging 實測驗證通過** (2026-01-29) — 8/8 API 呼叫全部 200
  - 空 context + 中文 target → 200
  - 空 context + 溫和 target → 200
  - 有 context + 攻擊語句 → 200
  - 有 context + 同理心語句 → 200
  - 長 context + 質疑語句 → 200
  - 舊 URL（kxaznpplqq）也全部正常
  - Level 判斷合理（溫和=1, 中性=2, 攻擊=3）

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

### 忘記密碼流程優化（AllenLee 需求 2026-01-29）

#### Deeplink Redirect（App 來源區分）
- [ ] 密碼重設完成頁面區分 App vs Web 來源
  - 方案：URL 加 `?source=app` 參數區分
  - App 來的：重設完成後按鈕 redirect 到 `islandparent://auth/forgot-password-done`
  - Web 來的：維持現有行為（顯示返回登入連結）
- [ ] 修改 email 中的重設連結，App 發起的請求帶上 `source=app` 參數
  - 例：`/island-parents/reset-password?token=xxx&source=app`
- [ ] 修改 `reset_password.html` 重設成功後的按鈕行為
  - 讀取 `source` 參數，若為 `app` → `window.location.href = 'islandparent://auth/forgot-password-done'`
  - 否則 → 維持現有返回登入頁面連結
- [ ] 修改 forgot-password 請求 API / email 發送邏輯，傳遞 `source` 參數

#### Email 自動帶入
- [ ] forgot-password 頁面支援 `?mail=` query parameter 預填 email
  - 例：`/island-parents/forgot-password?mail=allen@gmail.com`
  - 修改 `forgot_password.html`，讀取 URL `mail` 參數自動填入 email 欄位
- [ ] App 端開啟 forgot-password 頁面時帶上使用者 email

### Base URL 統一（AllenLee 回報 2026-01-29）
- [ ] iOS 端 base URL 需更新（Allen 負責）
  - 舊：`https://career-app-api-staging-kxaznpplqq-uc.a.run.app`
  - 新：`https://career-app-api-staging-978304030758.us-central1.run.app`
  - Production 也要確認：`career-app-api-prod-kxaznpplqq-uc.a.run.app` → 待確認新 URL
- [ ] 後端文件 base URL 更新（IOS_GUIDE_PARENTS.md 等）
  - `IOS_GUIDE_PARENTS.md` 中多處引用需確認一致
  - 舊 weekly reports 仍引用舊 URL（已過期，不需改）
- [ ] 確認兩個 URL 是否都還能用（Cloud Run 可能兩個都有效）

### Terms & Privacy 網頁 ✅ 已完成 (2026-01-27)
- [x] 建立 Terms of Service 頁面 (`/island-parents/terms`)
- [x] 建立 Privacy Policy 頁面 (`/island-parents/privacy`)
- [x] 實作響應式設計（桌面 + 手機）
- [x] 實作 Sticky TOC 導航（Intersection Observer）
- [x] 符合 GDPR 與台灣個資法規範
- [x] 提供 RevenueCat Paywall 配置用 URL
- [x] 撰寫完整測試覆蓋（11 個整合測試）
- [x] 更新文檔（IOS_GUIDE_PARENTS.md, PRD.md, CHANGELOG.md, BACKEND_DELIVERY.md）
- [x] Chrome 驗證測試通過
- [x] CI/CD 部署至 Staging 環境

**URL (Staging)**:
- Terms: https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/terms
- Privacy: https://career-app-api-staging-978304030758.us-central1.run.app/island-parents/privacy

### 網域與信任感
- [x] ~~評估並選擇合適的網域~~ → **決定掛在逗點教室網域下**（KM 確認 2026-01-29）
  - 明天 Young 與逗點一起確認具體子網域
- [ ] **將 WEB 放在逗點網域** 🔴 待 Young 協助
  - 後端 Web 頁面（forgot-password, reset-password, terms, privacy 等）部署到逗點網域
  - 需與逗點網域管理員協調
- [ ] 設定可信賴的網域用於 Web 重設密碼/條款頁面
  - 🟡 半阻塞：等逗點確認子網域後可執行
- [x] ~~設定 support 信箱~~ → **`CC_BDS@careercreator.tw`**（KM 確認 2026-01-29）
- [ ] 設定 Gmail SMTP 應用程式密碼（KM 負責）
  - 步驟：登入 CC_BDS@careercreator.tw → 開啟兩步驟驗證 → 產生應用程式密碼
  - 🔴 阻塞：等 KM 完成後提供 16 碼密碼
- [ ] 後端更新 SMTP 環境變數（拿到密碼後）
  - `SMTP_USER=CC_BDS@careercreator.tw`
  - `FROM_EMAIL=CC_BDS@careercreator.tw`
  - `SMTP_PASSWORD=<KM 提供的 16 碼>`
  - 🔴 依賴：KM 產生應用程式密碼
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

## 高優先級 - 內容品質優化

### 報告內容調整
- [x] **調整報告中太過學理的內容** ✅ 已完成 (2026-01-29)
  - 修改 Prompt：平衡專業權威與生活化語言
  - 策略：適度保留簡單術語（同理、界限、情緒、歸屬感、價值感），避免過度學術化
  - 理論轉譯：「冰山理論」→「表面行為背後的真正需求」、「情緒教練時刻」→「陪伴孩子面對情緒」
  - 移除專家名稱引用（Gottman、阿德勒、薩提爾），改用「研究發現...」等中性表述
  - A/B Testing：學術密度降低 100%（19.1 → 0.0 terms/1000 chars）
  - 無需 iOS 改動，無需 Schema 變更
  - 相關 commits: 0399132, 2ee975b, 14b80f5

---

## 高優先級 - 郵件服務

### SMTP 郵件服務遷移
- [x] **將 SMTP mail 服務換成官方使用的郵件服務** ✅ 已完成 (2026-01-29)
  - 選定方案：使用 Gmail SMTP 與官方帳號 `CC_BDS@careercreator.tw`
  - ✅ 已更新 GitHub Secrets：`SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL`
  - ✅ 已更新 `.env.example` 文檔
  - ✅ 已更新本地 `.env` 配置
  - Gmail 應用程式密碼：已由 KM 提供並設置完成
  - 無需更新程式碼：現有 email_sender.py 已支援
  - 測試：部署後需驗證郵件發送功能（忘記密碼、計費報告等）

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
