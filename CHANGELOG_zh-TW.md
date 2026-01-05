# 更新日誌

本文件記錄職涯諮詢平台 iOS 後端 API 的所有重要變更。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，
版本號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

---

## [未發布]

### 新增
- **PromptRegistry - 統一 Prompt 架構** (2026-01-04)
  - 新增集中式 prompt 管理系統於 `app/prompts/`
  - 檔案結構：
    - `base.py` - 預設 prompts（任何租戶的 fallback）
    - `career.py` - 職涯諮詢 prompts（deep、report）
    - `parenting.py` - 浮島家長版 prompts（quick、deep、report）
    - `__init__.py` - PromptRegistry 類別與 `get_prompt()` 方法
  - 功能特點：
    - 多租戶支援，自動 fallback 到預設值
    - 租戶別名：`island` → `island_parents`（保留日後拆分彈性）
    - island_parents 深度分析模式支援：`practice` / `emergency`
    - 類型支援：`quick`、`deep`、`report`
  - 使用方式：`PromptRegistry.get_prompt("island_parents", "deep", mode="emergency")`
  - 更新的服務：
    - `quick_feedback_service.py` - 現接受 `tenant_id` 參數
    - `keyword_analysis_service.py` - 使用 PromptRegistry 取代硬編碼 prompts
  - Prompt 覆蓋範圍：
    | 類型 | Career | Island Parents | Default |
    |------|--------|----------------|---------|
    | quick | ❌ fallback | ✅ 親子專用 | ✅ 通用 |
    | deep | ✅ 職涯分析 | ✅ practice/emergency | ✅ 通用 |
    | report | ✅ 職涯報告 | ✅ 8學派報告 | ✅ 通用 |
  - PRD 已更新完整架構文件

### 修復
- **繁體中文（zh-TW）強制執行** (2026-01-02)
  - 問題：AI prompt 和程式碼註解中發現簡體中文字元
    - 受影響檔案：app/services/keyword_analysis_service.py（第 45-50, 74-87 行）
    - 字元：从→從、专家→專家、建议→建議、挑选→挑選、适合→適合、对话→對話、等级→等級、数量→數量、当前→當前、库→庫、请→請、选择→選擇、规则→規則、必须→必須、改写→改寫、输出→輸出
  - 修復：將所有簡體中文轉換為繁體中文
    - 更新 keyword_analysis_service.py 的 docstring 和 AI prompts
    - 在快速回饋和深度分析 prompt 中加入明確的 zh-TW 強制指令
    - 新增指示：「CRITICAL: 所有回應必須使用繁體中文（zh-TW），不可使用簡體中文。」
  - 影響：所有 AI 回應（快速回饋與深度分析）現在保證使用繁體中文
  - 檔案：app/services/keyword_analysis_service.py、app/services/quick_feedback_service.py
  - Commit：7c0f9dd

- **快速回饋情境分析修復** (2026-01-02)
  - 問題：硬編碼情境規則導致回饋誤判
    - 範例：「我數到三，一、二、三！」（威脅倒數）被誤判為「測試麥克風」
    - 根本原因：Prompt 中的「如果...則...」規則僅匹配關鍵字，忽略上下文
  - 修復：以情境理解取代硬編碼規則
    - 移除所有「如果家長在數數/測試麥克風 → 回應...」類型的規則
    - 新增指示要求 AI 分析完整對話情境：
      - 對話的脈絡和情境
      - 家長當下的互動方式
      - 對話的走向
    - 新增反模板指示：「不要套用固定模板」
  - 影響：AI 現在根據實際對話流程提供符合情境的回饋
  - 測試結果：9/9 快速回饋測試通過，現可區分細微情境差異
  - 檔案：app/services/quick_feedback_service.py:19-39
  - Commit：待提交

- **快速回饋 Token 限制修復** (2026-01-02)
  - 問題 1：快速回饋永遠回傳預設訊息「繼續保持，你做得很好」
    - 根本原因：Google Cloud 認證過期
    - 錯誤訊息：`google.auth.exceptions.RefreshError: Reauthentication is needed`
    - 修復：重新執行 `gcloud auth application-default login` 並重啟伺服器
  - 問題 2：認證修復後，快速回饋只回傳單一字元（如「你」、「深」）
    - 根本原因：`max_tokens=100` 太嚴格，Gemini 觸及 MAX_TOKENS 上限
    - 伺服器日誌：「Response may be incomplete. Finish reason: 2」（2=MAX_TOKENS）
    - 症狀：中文字元需要多個 token，即使短回應也無法完整輸出
  - 修復：實作雙層長度控制策略
    - 將 `max_tokens` 從 100 提高到 1000（輸出安全上限）
    - 保留 prompt 指示「請用 1 句話（20 字內）」作為內容層級控制
    - 理由：`max_output_tokens`（Vertex AI）只計算輸出 token，不含輸入
    - 這樣可防止截斷，同時給予足夠的 token 預算來生成完整句子和格式
  - 影響：快速回饋現在可生成完整、符合情境的回應
  - 測試結果：「先同理孩子不想寫的心情，再好奇他的困難。」（完整句子，無截斷）
  - 檔案：app/services/quick_feedback_service.py:71
  - Commit：待提交

- **資料庫遷移：補上遺失的 `last_billed_minutes` 欄位** (2026-01-02)
  - 問題：即時分析卡住，因為 `session_usages.last_billed_minutes` 欄位不存在
  - 根本原因：遷移腳本 02c909267dd6 標記為已執行，但欄位實際未建立
  - 修復：手動新增欄位 `ALTER TABLE session_usages ADD COLUMN last_billed_minutes INTEGER NOT NULL DEFAULT 0`
  - 影響：即時分析現在正常運作，增量計費功能可用
  - 錯誤訊息：`psycopg2.errors.UndefinedColumn: column session_usages.last_billed_minutes does not exist`

- **手機版點擊「回到首頁」時客戶清單未重新載入** (2026-01-02)
  - 問題：點擊「回到首頁」按鈕時，客戶清單顯示初次登入時的舊資料
  - 根本原因：`goToHome()` 函數未從 API 重新載入客戶清單
  - 原始行為：顯示初次登入時快取的 HTML，沒有呼叫 API
  - 修復：直接在 `goToHome()` 函數中內嵌客戶載入邏輯
  - 實作細節：
    - 將 `goToHome()` 改為非同步函數
    - 新增 `fetch('/api/v1/clients')` API 呼叫，包含錯誤處理
    - 使用 API 最新資料重新渲染客戶清單
    - 處理邊界情況（無客戶 → 顯示表單，renderClientList 未定義 → 記錄錯誤）
  - 影響：返回首頁時客戶清單永遠是最新的，新增的客戶立即顯示
  - 檔案變更：app/templates/realtime_counseling.html:399-462
  - Console 日誌：`[ONBOARDING] Going back to home`, `[CLIENT_LIST] Fetching clients...`

### 新增
- **Island Parents 手機版全域導航** (2026-01-02)
  - 在所有手機頁面新增持久化導航列
  - 功能：
    - 左上角：「回到首頁」按鈕 - 返回客戶選擇頁面
    - 右上角：「登出」按鈕（紅色）- 登出使用者
  - 實作細節：
    - 固定於頂部的 header，z-index 9999（永遠在最上層）
    - 僅在手機顯示（md:hidden）
    - 登入時自動顯示，登出時隱藏
  - 影響：所有手機頁面導航一致，方便登出
  - 檔案變更：app/templates/realtime_counseling.html

- **Island Parents 手機版引導流程強化** (2026-01-02)
  - 重新設計兩階段引導流程：
    - 第一頁：選擇或建立孩子
    - 第二頁：選擇模式（對談/練習）+ 確認孩子名稱
  - 新增功能：
    - 顯示「現在要跟 [孩子名稱] 對話」- 明確告知將與哪個孩子對話
    - 模式選擇頁新增「返回」按鈕，可重新選擇孩子
    - 按鈕文字改為「開始對話」（原為「下一步」）
  - 手機優先：登入後首頁導向客戶選擇，而非主內容
  - 影響：家長引導體驗更佳，清楚知道當前選擇的孩子
  - 檔案變更：app/templates/realtime_counseling.html

### 變更
- **Island Parents 快速回饋改進** (2026-01-02)
  - 間隔時間從 10 秒增加到 20 秒（降低干擾）
  - 修正 AI 回應的斷行問題：
    - 在 prompt 新增「CRITICAL: 只輸出一句話，不要換行」
    - 在回應處理中移除 `\n` 和 `\r` 字元
  - 改為兩行顯示：
    - 上方：深度分析（較大、粗體）
    - 下方：快速回饋（較小、較淡）
    - 不再覆蓋深度分析結果
  - 影響：回饋節奏更自然，UI 呈現更清晰
  - 檔案變更：
    - app/services/quick_feedback_service.py（prompt + 處理邏輯）
    - app/templates/realtime_counseling.html（兩行顯示）

### 修復
- **手機版按鈕點擊無反應** (2026-01-02)
  - 修正 ReferenceError: 函數未定義導致 onclick 處理器無法執行
  - 根本原因：函數定義在 HTML 渲染之後，onclick 屬性無法找到函數
  - 解決方案：將所有按鈕處理函數移到早期 script 標籤（HTML 之前）
  - 移動的函數：logout(), goToHome(), showClientForm(), backToClientSelection(), setOnboardingMode(), completeOnboarding()
  - 影響：所有手機導航和引導流程按鈕現在正常運作
  - 檔案變更：app/templates/realtime_counseling.html
  - 測試：Chrome 手機版驗證所有 6 個關鍵按鈕

- **手機導航 Z-Index 問題** (2026-01-02)
  - 修正手機導航被 onboarding 容器遮蓋的問題
  - 將 z-index 從 z-50 改為 z-[9999]
  - 影響：所有手機頁面的導航按鈕現在正確顯示
  - 檔案變更：app/templates/realtime_counseling.html

- **手機版客戶選擇畫面顯示** (2026-01-02)
  - 修正手機登入後空白畫面的問題
  - 在 checkAuth 函數中明確初始化 clientListMode 顯示狀態
  - 影響：手機登入後正確顯示客戶選擇畫面
  - 檔案變更：app/templates/realtime_counseling.html（checkAuth 函數）

- **Web 即時諮詢 - Island Parents 流程** (2026-01-02)
  - 修正預設租戶：從 'career' 改為 'island_parents'（家長使用的網頁介面）
  - 修正 session 初始化：現在使用 onboarding 階段選擇的客戶，而非硬編碼預設值
  - 實作細節：
    - 更新 `app/templates/realtime_counseling.html` 預設 tenant_id 為 'island_parents'
    - 修改 session workflow，從 localStorage 讀取 selectedClientId/selectedClientName
    - 若有選擇客戶：為現有客戶創建 case 和 session（資料正確關聯）
    - 若無客戶：fallback 創建新 client+case+session（向後相容）
  - 流程改進：
    - 登入 → 客戶選擇/建立 → 練習模式 → 分析（全部正確關聯）
    - 客戶資料透過 localStorage 在練習階段持久化
    - Case 和 session 正確關聯到選擇的孩子
  - 影響：家長現在可以正確設定孩子資訊並追蹤諮詢歷史
  - 檔案變更：app/templates/realtime_counseling.html (+88 行, -22 行)

- **BigQuery 分析日誌權限** (2026-01-02)
  - 為 Cloud Run service account 新增缺失的 BigQuery 權限
  - Service account: career-app-sa@groovy-iris-473015-h3.iam.gserviceaccount.com
  - 授予角色：
    - roles/bigquery.dataEditor（寫入分析日誌到表格）
    - roles/bigquery.user（執行查詢）
  - 修正錯誤："Permission bigquery.tables.updateData denied on table realtime_analysis_logs"
  - 影響：Session 分析日誌現在可以寫入 BigQuery 供分析使用
  - 參考：分析日誌功能在 app/services/gbq_service.py

- **新 Session Workflow 的驗證與快速回饋修復** (2026-01-02)
  - 修正呼叫 `/api/v1/sessions/{id}/recordings/append` 時的 403 Forbidden 錯誤
  - 根本原因：APIClient 在 constructor 快取 auth token，但當時用戶尚未登入
  - 解決方案：每次請求時從 localStorage 重新讀取最新的 auth token
  - 修正 island_parents 租戶缺少快速回饋建議的問題
  - 根本原因：後端回傳 `detailed_scripts`，前端期待 `quick_suggestions`
  - 解決方案：在 session-workflow.js 將 `detailed_scripts` 轉換為建議格式
  - 格式：`💡 {situation}\n{parent_script}`
  - 對 career 租戶 fallback 使用 `quick_suggestions`（向後相容）
  - 影響：分析現在可以正確驗證，快速回饋正確顯示
  - 檔案變更：
    - app/static/js/api-client.js（每次請求讀取 token）
    - app/static/js/session-workflow.js（轉換 detailed_scripts）

### 新增
- **雙 API 分析系統 - 快速回饋（雞湯文）+ 深度分析** (2026-01-02)
  - 實作同時運行的快速回饋與深度分析計時器
  - **快速回饋 API**（雞湯文 - 即時鼓勵訊息）：
    - 端點：POST `/api/v1/realtime/quick-feedback`
    - 觸發時機：在 🟢 綠燈和 🟡 黃燈安全等級下，每 10 秒觸發一次
    - 🔴 紅燈時停用（15 秒深度分析已經夠快）
    - Toast 提示：黃色漸層（「⚡ 快速分析中...」）
    - 目的：填補深度分析之間的空白，提供輕量級鼓勵
    - 回應時間：約 1-2 秒（Gemini Flash 輕量 prompt）
  - **深度分析 API**（完整分析含安全等級更新）：
    - 端點：POST `/api/v1/realtime/analyze`（既有端點）
    - 觸發時機：基於安全等級的自適應間隔
      - 🟢 綠燈：每 60 秒
      - 🟡 黃燈：每 30 秒
      - 🔴 紅燈：每 15 秒（維持不變）
    - Toast 提示：紫藍漸層（「⚡ 自動分析中...」）
    - 目的：變更安全等級並調整分析間隔
  - **雙計時器獨立運作**：兩個計時器同時運行，互不干擾
  - **UI 增強**：
    - 新增「即時建議」標題到建議區塊
    - 新增「分析完成」標籤在標題旁
    - 不同 toast 顏色區分快速 vs 深度分析
  - 架構：
    - 後端：`/app/services/quick_feedback_service.py`（AI 驅動的鼓勵訊息）
    - 前端：雙計時器邏輯在 `app/templates/realtime_counseling.html`
    - 成本：綠燈情境下增加 $0.0036/小時（+0.85%）
  - 影響：持續的回饋流程，避免長分析間隔時的「空白感」
  - 檔案變更：
    - app/templates/realtime_counseling.html（雙計時器實作）
    - 後端：quick_feedback_service.py、realtime.py（API 已存在）
  - 參考：基於 `/api/v1/realtime/quick-feedback` 端點（2026-01-01 新增）

### 變更
- **Web/iOS API 架構驗證** (2026-01-01)
  - 確認 Web 版本已透過 `keyword_analysis_service` 使用 8 大流派 Prompt
  - Web 與 iOS 共用統一的分析邏輯（無重複代碼）：
    - 兩個平台使用相同的 prompts（來自 `app/prompts/parenting.py`）
    - 兩個平台使用相同的 200 句專家建議（RAG 知識庫）
    - 兩個平台使用相同的 keyword analysis service
  - API 回應格式依平台不同：
    - Web: `RealtimeAnalyzeResponse` (realtime.py)
    - iOS: `IslandParentAnalysisResponse` (sessions_keywords.py)
  - 核心分析邏輯在兩個平台完全相同
  - ✅ 重構已成功從 realtime.py 移除重複代碼
  - 影響：Web 無需額外整合 - 已經在使用 8 大流派框架
  - 參考：架構分析確認統一程式碼基礎 (2026-01-01)

### 新增
- **Web Session Workflow 模組化 JavaScript 架構** (2026-01-01)
  - 建立模組化 JavaScript 架構，統一 Web 與 iOS 的 session workflows
  - 新增模組：
    - `app/static/js/api-client.js` - 集中式 API 通訊層，含認證功能
    - `app/static/js/session-workflow.js` - 統一的 session 管理（iOS 風格）
  - 在 `app/templates/realtime_counseling.html` 整合 Feature Flag：
    - `USE_NEW_SESSION_WORKFLOW` 旗標控制新舊 API 路徑
    - 新 workflow：建立 client+case → 建立 session → 附加錄音 → 分析
    - 舊 workflow：直接呼叫 realtime analyze API（保留向後相容性）
  - Response 轉換層：
    - 自動將 Session API 回應轉換為 Realtime API 格式
    - 確保零 UI 變更需求（`displayAnalysisCard` 函數完全相容）
  - 文檔與範例：
    - `docs/web-session-workflow-implementation.md` - 完整實作指南
    - `app/static/js/README.md` - API client 與 session workflow 文檔
    - `app/static/integration-example.js` - 獨立整合範例
    - `app/static/test-session-workflow.html` - 互動式測試頁面
  - 整合測試 (`tests/integration/test_web_session_workflow.py`)：
    - test_complete_web_session_workflow - 完整 workflow 測試
    - test_web_workflow_multiple_analyses - 多段分析測試
    - test_web_workflow_emergency_mode - Emergency 模式 workflow 測試
  - 優勢：
    - **iOS/Web 一致性**：兩個平台現在使用相同的 session workflow
    - **向後相容**：透過 feature flag 保留舊 realtime API 路徑
    - **模組化設計**：關注點清晰分離（API client、session workflow、UI）
    - **易於測試**：獨立測試頁面供快速開發使用
  - 測試覆蓋：3 個新整合測試，283 個測試全部通過（無迴歸）
  - Commit: 2ec0033

### 變更
- **降低 8 大流派 Prompt 中 Dan Siegel 的權重** (2026-01-01)
  - 為 Dan Siegel 的「全腦教養」理論添加科學爭議警告
  - 重新排序分析架構，優先使用 ABC 行為模型，而非腦部二分法
  - 將「上層腦/下層腦」術語替換為中性的「情緒狀態」
  - 更新：`app/prompts/parenting.py` - Practice 和 Emergency 模式 prompts
  - 基於 Solomon 的反饋：優先使用實證基礎的方法，而非有爭議的理論

### 新增
- **即時鼓勵快速回饋 API** (2026-01-01)
  - 新增 `/api/v1/realtime/quick-feedback` 端點，提供輕量級 AI 驅動的鼓勵訊息
  - 提供 1-2 秒 AI 生成回饋，填補完整分析週期之間的空檔
  - 根據燈號動態協調頻率，避免與 realtime/analyze 衝突：
    - 🟢 綠燈：30 秒間隔（補充 60 秒完整分析）
    - 🟡 黃燈：15 秒間隔（補充 30 秒完整分析）
    - 🔴 紅燈：停用（15 秒完整分析已足夠快速）
  - 功能特性：
    - 使用 Gemini Flash 的情境感知 AI 回應（≤ 20 字）
    - 讀取最近 10 秒逐字稿產生適當鼓勵
    - 錯誤時優雅降級至預設訊息
    - 追蹤延遲以進行效能監控
  - 新增檔案：
    - `app/services/quick_feedback_service.py` - AI 驅動的快速回饋服務
    - `app/services/encouragement_service.py` - 規則型備用服務（未使用，保留供參考）
    - `app/schemas/realtime.py` - 新增 QuickFeedbackRequest/Response 模型
  - 更新：`app/api/realtime.py` - 整合 quick_feedback_service
  - 文檔：
    - `docs/encouragement_api_integration.md` - 完整 iOS 整合指南（含 Swift 範例）
    - `docs/encouragement_services_report.md` - 效能比較（規則型 vs AI 驅動）
  - 成本影響：綠燈情境每小時 +$0.0036（+0.85%）
  - 向後相容：新端點，現有 API 無變更
  - 測試：`tests/integration/test_quick_feedback_api.py`（9 個測試：3 個通過，6 個需要 GCP 認證）

- **8 大教養流派 - 詳細話術與理論框架** (2025-12-31)
  - 整合 8 大親子教養理論至 island_parents 租戶 prompts
  - Practice Mode 新增回應欄位：
    - `detailed_scripts`: 逐步對話指導（100-300 字具體對話範例）
    - `theoretical_frameworks`: 理論歸因（標註使用的流派）
  - Schema 擴充：
    - 新增 `DetailedScript` 模型，包含欄位：situation, parent_script, child_likely_response, theory_basis, step
    - 擴充 `IslandParentAnalysisResponse`，新增選填欄位 detailed_scripts 與 theoretical_frameworks
  - Prompt 檔案：
    - `app/prompts/island_parents_8_schools_practice_v1.py`（Practice Mode - 詳細教學版）
    - `app/prompts/island_parents_8_schools_emergency_v1.py`（Emergency Mode - 快速建議版）
  - 向後相容：所有新欄位皆為 Optional，Emergency Mode 保持簡潔，Career 租戶不受影響
  - 整合測試：`tests/integration/test_8_schools_prompt_integration.py`
  - 測試場景：Practice/Emergency 模式選擇、Schema 驗證、安全等級評估、Token 追蹤
  - 更新：`app/services/keyword_analysis_service.py`、`app/schemas/analysis.py`、`PRD.md`
  - 基礎檔案：`scripts/README_8_SCHOOLS_PROMPT.md`、`scripts/PROMPT_COMPARISON.md`、`scripts/test_8_schools_prompt.py`
  - 參考：`docs/PARENTING_THEORIES.md` - 8 大教養流派理論完整指南

- **analyze-partial API 諮詢模式支援** (2025-12-31)
  - island_parents 租戶新增 `mode` 參數
    - `emergency`: 快速、簡化分析（1-2 個關鍵建議）
    - `practice`: 詳細教學模式（3-4 個建議含技巧說明）
  - 向後相容：選填參數，預設為 `practice`
  - Career 租戶：忽略 mode 參數（不適用）
  - realtime.py bug 修復：GBQ 中分離 `analysis_type` 與 `mode` 欄位
  - 4 個整合測試：emergency 模式、practice 模式、預設值、career 忽略
  - 更新：`app/schemas/analysis.py`、`app/api/sessions_keywords.py`、`app/services/keyword_analysis_service.py`、`app/api/realtime.py`
  - 測試：`tests/integration/test_analyze_partial_api.py`（第 472-730 行）

- **配置管理文檔** (2025-12-31)
  - 建立 `docs/CONFIGURATION.md` - Single Source of Truth 配置指南
  - 模型選擇指南（Gemini 3 Flash、2.0 Flash、1.5 Pro）
  - 區域相容性文檔（global vs us-central1）
  - 反模式警告與疑難排解指南

- **RFC 7807 標準化錯誤處理** (2025-12-31)
  - 實作 RFC 7807（HTTP API 問題詳情）標準，統一所有錯誤回應格式
  - 所有 API 錯誤現在返回一致的 JSON 格式，包含 `type`、`title`、`status`、`detail` 和 `instance` 欄位
  - 新增完整的錯誤處理模組：
    - `app/core/exceptions.py` - 自定義例外類別（BadRequestError、UnauthorizedError、ForbiddenError、NotFoundError、ConflictError、UnprocessableEntityError、InternalServerError）
    - `app/core/errors.py` - 錯誤格式化工具，支援多語言（英文/中文）
    - `app/middleware/error_handler.py` - 全域錯誤處理中介軟體
  - 更新端點以使用 RFC 7807 格式：
    - `app/api/auth.py` - 所有認證端點（註冊、登入、個人資料更新）
    - `app/api/sessions.py` - 所有會談管理端點
  - 錯誤狀態碼改進：
    - 將重複資源錯誤從 400 改為 409（Conflict）- 語意更正確
    - 維持錯誤訊息內容的向後相容性
  - 新增 31 個單元測試（`tests/unit/test_errors.py`）涵蓋所有錯誤類型和邊界情況
  - 新增 18 個整合測試（`tests/integration/test_error_handling.py`）驗證端對端錯誤格式
  - 優點：
    - **一致性**：所有錯誤遵循相同可預測的結構
    - **符合標準**：遵循 IETF RFC 7807 規範
    - **前端友善**：iOS app 更容易解析和顯示錯誤
    - **國際化**：內建中文錯誤訊息支援
    - **除錯**：instance 欄位顯示失敗的確切端點
  - 錯誤回應範例：
    ```json
    {
      "type": "https://api.career-counseling.app/errors/not-found",
      "title": "Not Found",
      "status": 404,
      "detail": "Session not found",
      "instance": "/api/v1/sessions/123e4567-e89b-12d3-a456-426614174000"
    }
    ```

### 變更
- **配置管理重構 - Single Source of Truth** (2025-12-31)
  - 重構配置管理以建立 Single Source of Truth 模式
  - 從 service 模組移除所有 `getattr()` fallback defaults
  - 所有模組現在直接使用 `app/core/config.py` 的 `settings`
  - 修改檔案：
    - `app/services/gemini_service.py` - 移除第 12-21 行 fallbacks，直接使用 settings
    - `app/services/cache_manager.py` - 移除第 25-31 行 fallbacks，簡化初始化
    - `scripts/test_config.py` - 建立集中式測試配置模組
  - 更新 3 個測試腳本以使用統一配置
  - 影響：模型變更現在只需更新 .env 或 config.py（Single Source of Truth）
  - 驗證：29/29 整合測試通過，配置加載已驗證
  - 節省時間：模型變更從 5 個檔案 → 1 個檔案
  - 參考：`docs/CONFIGURATION.md`

### 移除
- **CodeerProvider 支援** (2025-12-31)
  - 移除 Codeer AI provider 整合以簡化程式碼
  - 現在統一使用 Gemini 進行所有分析
  - 影響：降低複雜度、更易維護、提供者一致
  - 原因：Codeer 實測效果不佳
  - 修改檔案：
    - `app/schemas/realtime.py` - 從 `RealtimeAnalyzeRequest` 移除 `provider` 和 `codeer_model` 參數
    - `app/schemas/realtime.py` - 移除 `CodeerTokenMetadata` schema
    - `app/api/realtime.py` - 移除 Codeer provider 路由邏輯
    - `app/api/realtime.py` - 移除 `_analyze_with_codeer()` 函數
    - `app/core/config.py` - 移除所有 CODEER_* 設定欄位
    - `app/models/session_analysis_log.py` - 更新 provider 註解移除 "codeer"
  - 刪除檔案：
    - `app/services/codeer_client.py` - Codeer API 客戶端
    - `app/services/codeer_session_pool.py` - Codeer session pooling
    - `tests/integration/test_realtime_codeer_provider.py` - Codeer provider 測試
    - `scripts/list_codeer_agents.py` - Agent 列表腳本
    - `scripts/validate_codeer_cache.py` - Cache 驗證腳本
    - `scripts/test_all_codeer_models.py` - 模型測試腳本
  - 注意：iOS app 應移除 API 請求中的 `provider` 參數

### 新增
- **文檔** (2025-12-31)
  - 建立 `docs/PARENTING_THEORIES.md` - 8 大教養流派理論完整指南
    - 詳細說明各流派框架（正向教養、薩提爾、阿德勒、蒙特梭利、非暴力溝通、依附理論、情緒教養、行為主義）
    - API 整合範例展示 theoretical_frameworks 如何返回
    - AI 分析使用準則
  - 建立 `docs/LOGIN_ERROR_MESSAGES.md` - 登入錯誤訊息安全規範
    - 統一錯誤訊息防止帳號列舉攻擊
    - Backend/Frontend 實作指南
    - 安全日誌記錄與速率限制規範
    - 符合 OWASP 標準的認證錯誤處理

### 修復
- **Cloud Run 部署 - 孤立的 Alembic Revision** (2026-01-01)
  - 修復 Cloud Run 部署失敗：容器無法在 port 8080 啟動
  - 根本原因：資料庫有孤立的 revision `58545e695a2d` (已刪除的 organization management migration)
  - Cloud Run logs 真正錯誤：`Can't locate revision identified by '58545e695a2d'`
  - 時間軸：
    - Commit ccbfc95 新增 organization management 功能與 migration 58545e695a2d
    - Migration 已部署至 staging 資料庫
    - Commit 3c87a32 revert 功能並刪除 migration 檔案
    - 資料庫保留 alembic_version 中的 58545e695a2d 紀錄
    - 後續部署失敗，因為 alembic 找不到該檔案
  - 解決方案：建立修復 script 更新資料庫 revision 至正確值 (6b32af0c9441)
  - 實作細節：
    - 新增 scripts/fix_alembic_version.py 更新 alembic_version 表
    - 修改 scripts/start.sh 在 migrations 前執行修復
    - 刪除錯誤恢復的 migration 檔案
  - 先前的調查嘗試 (SSL 配置、DATABASE_URL、恢復 migration 檔案) 都不正確
  - 影響：成功啟用 Cloud Run 部署與資料庫 migration
  - 修改檔案：scripts/fix_alembic_version.py (新增)、scripts/start.sh、刪除 58545e695a2d migration

- **測試套件可靠性** (2025-12-31)
  - 修復整合測試中的 GCP 憑證驗證檢查
  - 測試現在會在憑證無效時正確跳過（不僅是缺少憑證）
  - 修復 session usage credit deduction 測試中的時間計算錯誤
  - 影響：測試套件現在可靠地通過（280 通過、90 跳過、0 失敗）
  - 修改檔案：
    - `tests/integration/test_token_usage_response.py` - 新增正確的 GCP 認證驗證
    - `tests/integration/test_session_usage_api.py` - 修復分鐘溢位問題（使用 timedelta）

- **RAG 執行順序 Bug - 關鍵修復** (2025-12-31)
  - 修復重大 bug：RAG 檢索在 Gemini 調用之後執行
  - RAG 上下文現在在 AI 分析前正確包含在 AI prompts 中
  - 影響：RAG 知識現在實際被 AI 使用，回應品質更好（200+ 專家建議）
  - 根本原因：RAG 在 Gemini 之後調用，導致完全失效
  - 修改檔案：`app/services/keyword_analysis_service.py`
    - 將 RAG 檢索移到 prompt 建構之前（第 143-177 行）
    - 將 RAG 上下文加入 prompt 模板（第 194 行）
    - 新增清晰的步驟註解以提高可讀性
  - 驗證：113/113 測試通過（新增 7 個 RAG 測試）
  - 品質提升：AI 分析現在使用親子教養資料庫的專家知識
  - 性能影響：0 秒（僅執行順序變更）
  - 文檔：`docs/bugfix_rag_integration.md`
  - Git commit: 82cd8d1

- **Token Usage 回應** (2025-12-31)
  - 修復 API 回應 fallback 場景中缺少 token_usage 的問題
  - token_usage 現在永遠包含（AI 調用失敗時為零值）
  - 影響：API 回應 schema 一致性、更好的錯誤監控
  - 修改檔案：`app/services/keyword_analysis_service.py`
    - 更新 `_get_tenant_fallback_result()` 以包含 `_metadata` 與 `token_usage`
    - 確保 token_usage 在 API 回應中永不為 null

### 移除
- **移除 CacheManager** (2025-12-31)
  - 移除 Gemini Context Caching 實作（實測效果 28%，預期 50%）
  - Vertex AI Context Caching API 將於 2026-06-24 棄用
  - 刪除檔案：
    - `app/services/cache_manager.py` (216 行)
    - `scripts/cleanup_caches.py` (49 行)
    - `tests/integration/test_realtime_cache.py` (完整測試檔案)
  - 修改檔案：
    - `app/api/realtime.py` - 移除 cache_manager import 和快取邏輯
    - `app/services/gemini_service.py` - 移除 analyze_with_cache 方法和快取 import
    - `scripts/compare_four_providers.py` - 移除快取使用
  - 成果：簡化架構、減少 300 行代碼、降低維護成本

### 新增
- **8 大流派親子教養 Prompt 整合** (2025-12-31)
  - ✅ 整合 8 大親子教養理論至 island_parents 租戶 prompts
    1. 阿德勒正向教養（尊重、合作、溫和而堅定）
    2. 薩提爾模式（冰山理論、探索深層需求）
    3. 行為分析學派（ABA、ABC 模式、環境設計）
    4. 人際神經生物學（全腦教養、情緒優先）
    5. 情緒輔導（情緒標註、同理、設限）
    6. 協作解決問題（Ross Greene CPS）
    7. 現代依附與內在觀點（Dr. Becky Kennedy）
    8. 社會意識教養（性別平權、身體自主權）
  - ✅ **新增回應欄位**（island_parents Practice Mode）：
    - `detailed_scripts`: 逐字稿級別話術指導（100-300 字具體對話範例）
    - `theoretical_frameworks`: 理論來源追溯（標註使用的流派）
  - ✅ **Schema 擴充**：
    - 新增 `DetailedScript` 模型，包含欄位：situation, parent_script, child_likely_response, theory_basis, step
    - 擴充 `IslandParentAnalysisResponse`，新增選填欄位 detailed_scripts 與 theoretical_frameworks
  - ✅ **Prompt 檔案**：
    - `app/prompts/island_parents_8_schools_practice_v1.py`（Practice Mode - 詳細教學版）
    - `app/prompts/island_parents_8_schools_emergency_v1.py`（Emergency Mode - 快速建議版）
  - ✅ **向後相容**：
    - 所有新欄位皆為 Optional（不影響現有 API 調用）
    - Emergency Mode 保持簡潔（不提供 detailed_scripts）
    - Career 租戶不受影響
  - ✅ **整合測試**: `tests/integration/test_8_schools_prompt_integration.py`
    - 測試場景：Practice/Emergency 模式選擇、Schema 驗證、安全等級評估、Token 追蹤
  - 📝 更新：`app/services/keyword_analysis_service.py`、`app/schemas/analysis.py`、`PRD.md`
  - 📝 基礎檔案：`scripts/README_8_SCHOOLS_PROMPT.md`、`scripts/PROMPT_COMPARISON.md`、`scripts/test_8_schools_prompt.py`
- **analyze-partial API 諮詢模式支援** (2025-12-31)
  - ✅ island_parents 租戶新增 `mode` 參數
    - `emergency`: 快速、簡化分析（1-2 個關鍵建議）
    - `practice`: 詳細教學模式（3-4 個建議含技巧說明）
  - ✅ 向後相容：選填參數，預設為 `practice`
  - ✅ Career 租戶：忽略 mode 參數（不適用）
  - ✅ realtime.py bug 修復：GBQ 中分離 `analysis_type` 與 `mode` 欄位
  - ✅ 4 個整合測試：emergency 模式、practice 模式、預設值、career 忽略
  - 📝 更新：`app/schemas/analysis.py`、`app/api/sessions_keywords.py`、`app/services/keyword_analysis_service.py`、`app/api/realtime.py`
  - 📝 測試：`tests/integration/test_analyze_partial_api.py`（第 472-730 行）
- **性能分析與測試基礎設施** (2025-12-31)
  - ✅ 性能分析文檔：
    - `docs/LIGHT_VS_HEAVY_ANALYSIS.md` - 速度對比報告（規則式 vs Gemini 輕量 vs Gemini 重量）
    - `docs/OPTIMIZATION_OPPORTUNITIES.md` - 優化機會分析與優先級排序
  - ✅ 性能測試腳本（7 個）：
    - `scripts/test_vertex_ai_caching.py` - Vertex AI Context Caching 性能測試
    - `scripts/test_gemini_context_caching.py` - Gemini Context Caching 測試
    - `scripts/test_light_vs_heavy_analysis.py` - 輕量 vs 重量分析對比
    - `scripts/test_timing_average.py` - 平均時間測試（5 次迭代）
    - `scripts/test_detailed_timing.py` - 詳細計時分解
    - `scripts/test_real_api_e2e.py` - 真實 API 端到端測試
    - `scripts/test_real_gemini_speed.py` - Gemini API 速度測試
  - ✅ 工具腳本：
    - `scripts/check_test_account.py` - 測試帳號驗證
    - `scripts/verify_password.py` - 密碼驗證工具
  - 📊 關鍵發現：
    - Gemini 3 Flash：平均 5.61 秒（比 Gemini 2.5 Flash 快 45%）
    - Context Caching：28.4% 改善（非宣稱的 50%，API 將於 2026-06 棄用）
    - 主要瓶頸：Gemini API（4.64 秒，83%）+ RAG 檢索（0.97 秒，17%）
    - 建議：專注於 Streaming 改善感知延遲（5.61 秒 → 1-2 秒）
  - 📝 相關於 TODO.md P0-A（RAG Bug 修復）和 P1-2（性能優化）

### 變更
- **Gemini 3 Flash 升級** (2025-12-28)
  - ✅ 從 Gemini 2.5 Flash 升級至 Gemini 3 Flash (`gemini-3-flash-preview`)
  - ✅ Pro 級智能，Flash 速度與定價
  - ✅ 更新定價計算：
    - 輸入：$0.50/1M tokens（原 $0.075/1M）
    - 輸出：$3.00/1M tokens（原 $0.30/1M）
    - 快取輸入：$0.125/1M tokens（原 $0.01875/1M）
  - ✅ 更新所有 service 檔案、API endpoints 與測試
  - ✅ 所有整合測試通過（22 個測試：計費、分析、GBQ 完整性）
  - ✅ 無破壞性變更 - API 向後相容
  - 📝 更新：`app/core/config.py`、`app/services/gemini_service.py`、`app/services/keyword_analysis_service.py`、`app/api/realtime.py`、定價計算
  - 📝 來源：[Gemini 3 Flash 文件](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash)

### 新增
- **Island Parents 關係欄位** (2025-12-29)
  - ✅ 新增 island_parents Client 表單的 `relationship` 欄位
    - 選項：爸爸、媽媽、爺爺、奶奶、外公、外婆、其他
    - island_parents 租戶必填欄位
    - 欄位順序優化以提升 UX（order=3）
  - ✅ 更新 Client 欄位標籤：
    - "孩子姓名" → "孩子暱稱"
  - ✅ 完整的 iOS API 整合指南
    - 9 步驟完整工作流程文件
    - 安全等級分析說明（🟢🟡🔴）
    - 動態分析間隔（5-30 秒，依安全等級調整）
    - iOS 實作的 Swift 程式碼範例
    - FAQ 章節與相關資源
  - ✅ 完整工作流程整合測試（681 行）
  - 📝 更新：`app/config/field_configs.py`、`IOS_API_GUIDE.md`
  - 📝 新增測試：`tests/integration/test_island_parents_complete_workflow.py`
  - 📝 測試報告：`docs/testing/ISLAND_PARENTS_WORKFLOW_TEST_REPORT.md`

- **文件整理與基礎設施成本分析** (2025-12-29)
  - ✅ 重組文件結構：
    - 測試報告移至 `docs/testing/`
    - 技術文件集中於 `docs/`
    - 依功能領域改善檔案組織
  - ✅ PRD 更新：
    - 新增 island_parents 安全等級系統細節
    - 標記增量計費（Phase 2）為已完成
    - 更新欄位配置與說明
  - ✅ 基礎設施成本分析加入 PRD：
    - Cloud Run 成本估算（低/中/高流量）
    - Supabase 定價方案與建議
    - Gemini 3 Flash AI 模型成本計算
    - 每月總成本預估：$10-25（原型階段）、$65-125（正式環境）
    - 成本優化策略（快取、頻率限制、監控）
  - 📝 更新：`PRD.md` 包含成本分析與功能狀態
  - 📝 來源：[Gemini 3 Flash 定價](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash)

- **密碼重設系統** (2025-12-27)
  - ✅ Web UI 頁面：`/forgot-password`（請求）與 `/reset-password`（確認）
  - ✅ iOS 整合 API 端點：
    - `POST /api/v1/password-reset/request` - 請求密碼重設
    - `POST /api/v1/password-reset/verify` - 驗證重設 token
    - `POST /api/v1/password-reset/confirm` - 確認新密碼
  - ✅ 透過 Admin API 建立新諮詢師時自動發送歡迎信
  - ✅ Multi-tenant 支援（career/island/island_parents），包含各租戶專屬 email 模板
  - ✅ Token 安全：32+ 字元加密隨機字串、6 小時有效期、單次使用
  - ✅ 頻率限制：每 5 分鐘最多請求一次
  - ✅ DEBUG 模式：開發階段跨租戶管理員存取
  - ✅ 資料庫遷移：`20251227_1049_f9b8a56ce021_add_password_reset_tokens_table.py`
  - ✅ 23 個整合測試，100% 通過率
  - ✅ Email 服務增強：
    - 透過 Gmail SMTP 發送
    - 各租戶專屬模板（career/island/island_parents）
    - 錯誤處理與重試邏輯

### 修復
- **Career 模式 Token 用量回傳 0 的問題** (2025-12-31)
  - 🐛 修復 career 租戶的 analyze-partial API 回傳 token_usage = 0 的 bug
  - 🔧 根本原因：`GeminiService.generate_text()` 回傳文字字串而非包含 metadata 的 response 物件
  - ✅ 修改 `GeminiService.generate_text()` 回傳完整 response 物件（第 98 行）
  - ✅ 更新所有呼叫者從 response 物件提取 `.text`：
    - `gemini_service.py`：chat_completion()、chat_completion_with_messages()
    - `keyword_analysis_service.py`：_parse_ai_response()
    - `analyze.py`：JSON 解析邏輯
  - ✅ 修正 `test_token_usage_response.py` 測試模型欄位錯誤：
    - Session 模型：移除無效的 `status`，新增 `session_date`
    - Client/Case 模型：新增缺少的必填欄位
  - ✅ 測試：2/2 通過（原本 0/2），所有相關測試通過（16/16）
  - 📝 更新：`app/services/gemini_service.py`、`app/services/keyword_analysis_service.py`、`app/api/analyze.py`、`tests/integration/test_token_usage_response.py`
- **Staging 部署的 SMTP 配置** (2025-12-27)
  - 🔧 在 CI/CD pipeline 中新增 SMTP 環境變數
  - 🔧 必要的 GitHub Secrets：SMTP_USER、SMTP_PASSWORD、FROM_EMAIL、APP_URL
  - 🔧 修復 staging 環境郵件靜默發送失敗問題
  - 🔧 建立 SMTP_SETUP.md 配置步驟文件
  - 📝 參見：`.github/workflows/ci.yml`、`SMTP_SETUP.md`

### 新增
- **Parents RAG 優化 - 完整可觀測性** (2025-12-26)
  - ✅ GBQ schema 覆蓋率從 23% 提升至 67%+（29/43 欄位）
  - ✅ parents_report API 完整 metadata 追蹤：
    - Token 用量：prompt_tokens、completion_tokens、total_tokens、cached_tokens
    - 成本計算：Gemini 2.5 Flash 定價（$0.000075/1K 輸入、$0.0003/1K 輸出）
    - 時間分解：RAG 搜尋時間、LLM 呼叫時間、總時長
    - 完整 prompts：system_prompt、user_prompt、prompt_template
    - LLM 回應：原始回應、結構化分析結果
    - RAG 追蹤：查詢、文件、來源、時間
    - 模型資訊：provider、model_name、model_version
  - ✅ 修改 `gemini_service.chat_completion()` 可選返回 usage_metadata
  - ✅ BigQuery JSON 欄位序列化（analysis_result、speakers、rag_documents）
  - ✅ 從請求擷取 Session ID（Web localStorage-based）
  - ✅ 修正欄位名稱不匹配（response_time_ms → api_response_time_ms、transcript_segment → transcript）
  - ✅ 模型修正為 gemini-2.5-flash（從 2.0-flash-exp）
- **Parents RAG 優化 - Phase 1.4 & 2.1** (2025-12-25)
  - ✅ Phase 1.4 - 前端調整：
    - 移除兩行格式判斷，統一單行建議顯示
    - 更新前端說明（行動版 & 桌面版）反映 200 句專家建議
    - Emergency 模式：1-2 句專家建議（從 200 句中選）
    - Practice 模式：3-4 句專家建議（從 200 句中選）
  - ✅ Phase 2.1 - 後端優化：
    - 擴大分析範圍從 1 分鐘至 3-5 分鐘（SAFETY_WINDOW_SPEAKER_TURNS：10 → 40）
    - 增強 RAG 檢索：top_k 3→7、similarity_threshold 0.5→0.35
    - 移除 RAG 內容的 200 字截斷
  - ✅ 動態分析間隔（Commit: 2b10eb0）：
    - 實作基於 safety_level 的自適應監控
    - 綠燈（安全）：60 秒
    - 黃燈（警示）：30 秒
    - 紅燈（高風險）：15 秒
    - 視覺通知與 console 日誌
    - `updateAnalysisInterval()` 函數動態調整計時器
  - ✅ 卡片顏色一致性：
    - 修正卡片顏色使用 `safety_level` 而非 `risk_level`
    - 更新標籤：「危險：立即修正」、「警示：需要調整」、「安全：溝通良好」
  - ✅ 測試增強：
    - 新增預設逐字稿快捷鍵（🟢🟡🔴）
    - 新增「⚡ 立即分析」按鈕用於即時測試
    - Phase 1.5：8/9 integration tests 通過，106 個總測試通過
- **家長報告 API 與統一 Session 管理** (2025-12-26)
  - ✅ 新增端點：`POST /api/v1/realtime/parents-report`
    - 生成完整的親子溝通報告
    - 分析家長與孩子的對話逐字稿
    - 提供 4 個結構化回饋區塊：
      1. 對話主題摘要（中性立場）
      2. 溝通亮點（表現良好的部分）
      3. 改進建議（具體建議或換句話說）
      4. RAG 知識庫參考（相關親子教養文獻）
    - 整合現有 RAG 基礎設施（similarity_threshold=0.5）
    - 使用 Gemini 2.5 Flash 進行分析（temperature=0.7）
  - ✅ 統一 Session ID 管理
    - 在 session 開始時生成一次：`session-{timestamp}-{random}`
    - 持久化於 localStorage 以跨請求追蹤
    - 所有即時分析 API 統一使用：
      - `/api/v1/realtime/analyze`（現包含 session_id + use_cache）
      - `/api/v1/realtime/parents-report`
      - 未來的 GBQ 資料持久化
    - 啟用 Gemini context caching 優化成本
  - ✅ 前端整合
    - 報告畫面 UI，包含亮點卡片與改進建議
    - 點擊「查看報告」觸發 API 並顯示結構化回饋
    - 手機版響應式設計，包含完成畫面
    - Session ID 貫穿整個錄音生命週期
  - ✅ 新增 Schemas：`ParentsReportRequest`、`ParentsReportResponse`、`ImprovementSuggestion`
  - ✅ 測試：後端 API 透過 curl 測試（成功回應，含 RAG 整合）
- **用戶註冊 API** (2025-12-15)
  - ✅ 新增端點：`POST /api/auth/register` 用於諮詢師帳號註冊
  - ✅ 註冊後自動登入（立即返回 JWT token）
  - ✅ 多租戶支援（email + tenant_id 唯一性檢查）
  - ✅ 用戶名全系統唯一性驗證
  - ✅ 密碼驗證（至少 8 個字元）
  - ✅ 預設角色分配（未指定時預設為 counselor）
  - ✅ 在 `/console` 頁面新增註冊表單
  - ✅ 完整的 TDD 測試覆蓋（6 個測試案例，全部通過）
  - ✅ 更新 iOS API 文檔，包含 Swift 範例

### 變更
- **文檔重組** (2025-12-26)
  - 將安全等級轉換測試文檔移至 `docs/testing/` 目錄：
    - `SAFETY_TRANSITIONS_SUMMARY.md` - 測試計劃總覽與設計決策
    - `SAFETY_TRANSITIONS_MANUAL_TEST_GUIDE.md` - 逐步測試程序
    - `SAFETY_TRANSITIONS_TEST_FINDINGS.md` - Sticky 行為分析與權衡
    - `SAFETY_TRANSITIONS_TEST_RESULTS_TABLE.md` - 預期結果與關鍵字檢測
    - `SLIDING_WINDOW_SAFETY_ASSESSMENT.md` - 演算法細節與成本節省
  - 更新 PRD.md 新增測試文檔參考連結
  - 清理 7 個實驗 JSON 檔案（資料已整理進 PRD.md）：
    - 移除 cache_strategy_comparison.json、experiment_results*.json、strategy_*.json
  - 原因：更好的組織結構，分離關注點（PRD vs 測試文檔）
  - 影響：根目錄更整潔、更易導航、保留測試文檔
- **延長 JWT Token 有效期限** (2025-12-13)
  - Access Token：24 小時 → 90 天（3 個月）
  - Refresh Token：7 天 → 90 天（3 個月）
  - 原因：改善開發者體驗，減少原型階段重新登入頻率
  - 影響：兩種 token 現在都具有一致的 90 天有效期

### 修復
- **RAG 相似度門檻過高** (2025-12-13)
  - 修復：RAG 知識檢索現已能正確運作於親子教養查詢
  - 根本原因：similarity_threshold=0.7 設定過高；實際相似度分數最高約 0.54-0.59
  - 解決方案：基於生產資料分析，將門檻從 0.7 降至 0.5
  - 影響：RAG 現在能檢索到相關的親子教養知識，不再回傳空結果
  - 更新檔案：`app/api/realtime.py`、`tests/integration/test_realtime_rag_integration.py`
- **Codeer Agent 不匹配錯誤** (2025-12-11)
  - 修復：Claude Sonnet 4.5 與 Gemini 2.5 Flash 模型現已完全運作
  - 根本原因：realtime.py 中 agent_id 參數傳遞錯誤
  - 解決方案：更新為從 codeer_model 參數使用正確的 agent ID
  - 影響：所有三個 Codeer 模型（Claude、Gemini、GPT-5）現已在生產環境正常運作

### 變更
- **Codeer 模型推薦更新** (2025-12-11)
  - **預設模型變更**：GPT-5 Mini → Gemini 2.5 Flash（最佳速度/品質平衡）
  - **模型重新排序**：依效能排序（Gemini > Claude > GPT-5 Mini）
  - **前端 UI 更新**：新增效能提示（~10.3s、~10.6s、~22.6s）與狀態標籤
  - **文件更新**：移除「實驗性」狀態，新增已驗證的效能基準
  - **效能數據**（實測結果）：
    - Claude Sonnet 4.5：10.3s 延遲（最高品質）
    - Gemini 2.5 Flash：10.6s 延遲（⭐ 推薦：最佳平衡）
    - GPT-5 Mini：22.6s 延遲（穩定、專業知識）

### 新增
- **Codeer 多模型支援 - 即時諮詢系統** (2025-12-11)
  - ✅ 3 種 Codeer 模型可選：GPT-5 Mini（預設）、Claude Sonnet 4.5、Gemini 2.5 Flash
  - ✅ Session pooling 優化（延遲降低 50%）
  - ✅ 前端模型選擇器 UI（響應式設計，支援行動與桌面）
  - ✅ 分析結果顯示使用的模型資訊
  - ✅ API 參數 `codeer_model` 支援模型選擇
  - ✅ 模型比較基準測試腳本（`scripts/test_all_codeer_models.py`）
  - ✅ 文件更新包含資安最佳實踐
- **Codeer AI API Client 整合** (2025-12-11)
  - ✅ 完整的異步 CodeerClient 服務（使用 httpx）
  - ✅ SSE (Server-Sent Events) 串流支援，實現即時聊天
  - ✅ 全面的 API 覆蓋：聊天、串流、RAG、STT、TTS、網頁搜尋
  - ✅ 27 個整合測試，涵蓋所有端點與情境
  - ✅ 配置管理：API key、base URL、預設 agent
  - ✅ 自動錯誤處理與重試機制
  - ✅ 完整 TDD 實作（RED-GREEN-REFACTOR 流程）
- **Gemini Explicit Context Caching Production 實作** (2025-12-10)
  - ✅ Cache Manager 服務採用 Strategy A（總是更新累積對話）
  - ✅ 多層清理機制（手動刪除 + TTL + 清理腳本）
  - ✅ 短內容自動降級（< 1024 tokens）
  - ✅ 整合到 `/api/v1/realtime/analyze` endpoint
  - ✅ API 回應包含 cache metadata
  - ✅ 8 個整合測試覆蓋所有場景
- **Cache 策略對比實驗** (2025-12-10)
  - 策略 A：完整累積（10/10 成功，100% 穩定，完整上下文）
  - 策略 B：僅當前增量（9/10 成功，90% 穩定，缺少上下文）
  - 實驗數據儲存於 `CACHE_STRATEGY_ANALYSIS.md`
- **即時諮詢成本效益分析**（PRD.md）
  - 完整成本拆解：STT + Gemini 有/無 Cache 方案對比
  - ROI 分析：每場諮詢省 15.2%，每年省 NT$10,439（每日 10 場）
  - 建議：Production 環境應實作 Explicit Context Caching

### 修復
- **Critical Cache 更新 Bug** (2025-12-10)
  - 修復：首次創建後 Cache 內容凍結，不再更新
  - 根本原因：`get_or_create_cache()` 返回舊 cache 不檢查新內容
  - 解決方案：實作 Strategy A - 總是刪除舊 cache，用最新 transcript 創建新的
  - 影響：AI 分析現在正確包含所有對話歷史

### 變更
- **即時 API 增強** - 更新聊天創建使用 UUID 確保唯一性
  - 新增微秒精度 + UUID 防止重複聊天名稱
  - 改善 Codeer API 互動的錯誤處理
- GCP Billing Monitor（AI 分析與 Email 報告，3 個新 API）
- BigQuery 整合實現即時成本追蹤
- Gemini AI 自動化帳單報告生成
- Gemini 回應診斷詳細日誌
- **即時 STT 諮詢系統**（Phase 2 前端完成）：AI 驅動的即時諮詢分析
  - TDD 方法論，11 個整合測試（後端 API 完成）

### 註記
  - ElevenLabs Scribe v2 Realtime API 整合（支援中文）
  - 手動說話者切換（諮詢師/案主）適用 Demo 場景
  - 點擊即時分析，提供逐分鐘漸進式模擬
  - 商用級行動優先 UI 與 RWD（斷點：640px, 1024px）
  - 聊天風格逐字稿，仿 WhatsApp 訊息氣泡
  - 嚴重性分級警示徽章（高/中/低風險）
  - 浮動操作按鈕（FAB）與固定底部控制列（行動版）
  - 載入骨架與空白狀態設計
  - 分析卡片：摘要、警示、建議（含漸變動畫）
  - Demo 模式提供 5 情境漸進式對話模擬
  - 基於 localStorage 的會話歷史管理
- **效能基準測試套件** 用於即時分析
  - 完整基準測試腳本，涵蓋 1/10/30/60 分鐘逐字稿
  - 效能測試報告與客戶友善文件
  - 所有逐字稿長度 100% 成功率（11-12 秒響應時間）
- **Gemini Cache 效能追蹤**
  - 使用量元資料記錄（cached_content_token_count, prompt_token_count, candidates_token_count）
  - 累積性逐字稿 Cache 效能測試腳本（1-10 分鐘）
  - 驗證 Gemini Implicit Caching 效能（快取 tokens 節省 75% 成本）

### 變更
- Gemini max_tokens 從 4000 提升至 8000（防止 JSON 截斷）
- 文檔整合（42 → 31 檔案，PRD.md 為單一真相來源）
- 程式碼品質改善（11 檔案重構，100% 檔案大小符合）
- **即時諮詢 AI 提示強化**：根據專業諮詢師回饋改善督導提示
  - 同理優先方法：AI 先理解父母情緒再提供引導
  - 具體可執行建議：所有建議包含明確步驟與對話範例
  - 溫和非批判語氣：以支持性引導取代直接批判語言
  - 結構化輸出：摘要、同理區段、關注事項、行動步驟含範例
  - **分析範圍優化**：新增【分析範圍】區段，確保 AI 聚焦最新一分鐘而非總結全部對話
    - 主要焦點：最新一分鐘對話（即時督導情境）
    - 背景脈絡：前面對話用於理解連續性
    - 避免泛泛總結，確保可執行的即時引導

### 修復
- Gemini 報告評分 JSON 截斷（成功率：85% → 100%）
- BigQuery lazy-load 避免 CI 認證錯誤
- 同步資料庫呼叫的錯誤 await 語法
- 文檔整合後的失效連結

### 基礎設施
- 帳單監控與 AI 成本分析
- Email 通知系統（Gmail SMTP）
- 強化錯誤處理與 robust JSON 解析

---

## [0.3.1] - 2025-11-29

### 新增
- 即時逐字稿關鍵字分析 API，包含 AI 驅動提取
- Session 名稱欄位，改善組織管理
- 從錄音片段自動計算時間範圍
- Claude Code agent 配置與 TDD 強制執行

### 變更
- Gemini 2.5 Flash 作為預設 LLM 提供者（成本降低 40%，回應時間 < 2 秒）
- 簡化關鍵字分析 UI（僅需 session + transcript）
- 移除 API 端點標題中的「(iOS)」後綴，統一命名規範

### 修復
- 修復 CI/CD 中 GeminiService mock 測試失敗
- 修復 Admin 角色資源刪除權限

### 效能
- Session 服務層抽取與 N+1 查詢修復（**快 3 倍**：800ms → 250ms）
- UI client-case-list API 優化（**快 5 倍**：1.2s → 240ms）
- Claude Code 工作流程優化（hook 輸出效率提升 93%）

---

## [0.3.0] - 2025-11-25

### 新增
- 快速 CI 策略，包含 smoke tests（< 10 秒）
- 報告生成整合測試（使用 mocked background tasks）
- Admin 角色，支援跨諮詢師資源管理

### 變更
- Staging CI 跳過耗時的 background task 測試，加快部署速度

### 修復
- 修復 Sessions API 的 N+1 查詢問題（使用 SQLAlchemy `joinedload`）
- 修復 UI client-case-list API 的 N+1 查詢問題（TDD 方法）
- 修復整合測試在 CI 環境的相容性問題

### 移除
- 移除 Playwright 前端測試（專注於後端 API 測試）

---

## [0.2.5] - 2025-11-24

### 新增
- Pre-commit hooks，包含完整檢查（ruff、資安、檔案大小）
- Pre-push hooks，包含 4 個核心 API smoke tests
- 100% 整合測試通過率（106 個測試）

### 變更
- 減少 smoke tests 至 4 個核心 API 測試，加快反饋速度
- 更新 API 回應狀態碼（POST: 201, DELETE: 204）
- 優化 pre-push hook，僅執行關鍵測試

### 修復
- 修復所有剩餘的整合測試失敗（達成 100% 通過率）
- 修復 Report API 測試欄位名稱斷言（`edited_content_markdown`）
- 修復 Client API 測試必填欄位和正確狀態碼
- 修復 Session 創建測試，預期回傳 201 Created

### 安全性
- 明確禁止 git 操作中使用 `--no-verify`（記錄於 CLAUDE.md）
- 在 pre-commit hooks 中新增 API keys、secrets、private keys 檢查

---

## [0.2.4] - 2025-11-24

### 新增
- Mypy 型別檢查，改善程式碼品質
- Supabase Pooler 連線需要 SSL

### 變更
- 抑制 SQLAlchemy columns 的 var-annotated mypy 錯誤（相容性修復）
- 在 CI pipeline 中分離 unit 和 integration 測試

### 修復
- 修復 Supabase Pooler 的 SSL 連線問題（`sslmode=require`）
- 修復 model 檔案中的 import 順序
- 修復整合測試資料庫設定和認證測試
- 新增 OpenAI API 回應的 None-safety 檢查

---

## [0.2.3] - 2025-11-23

### 新增
- Console 中的 iPhone 模擬器預覽視圖
- GET client-case detail 端點
- 選擇 client-case 時自動填充更新表單
- 完整的 API 整合測試（66 個測試）

### 變更
- Case status 從字串 enum 改為整數（0: 未開始, 1: 進行中, 2: 已結案）
- 重組 UI Pages 為兩個類別（CRUD Forms + Preview Pages）
- 改善 console 的行動版 RWD，更好的導航和分頁
- 重新設計 console 側邊欄，使用淺灰色主題

### 修復
- 修復 client-case list 的 500 錯誤（timezone-aware datetime）
- 修復更新表單中的欄位映射優先順序
- 修復 schema 空值欄位顯示

### 效能
- 優化 CI/CD pipeline，提升可靠性和效能

---

## [0.2.2] - 2025-11-22

### 新增
- iOS 專用的追加錄音 API，支援增量上傳

### 變更
- 將 Cloud Run 記憶體恢復為 1Gi，修復容器啟動超時問題

### 效能
- 優化 Cloud Run 資源成本效益（1 CPU, 1Gi 記憶體）

---

## [0.2.1] - 2025-11-21

### 新增
- Console 中顯示測試帳號，方便開發存取

### 變更
- 修復 console 登入表單中的租戶下拉選單

---

## [0.2.0] - 2025-11-19

### 新增
- 為 iOS 開發者提供完整的多租戶文檔
- OpenAPI/Swagger 文檔的 RecordingSegment schema
- 週進度報告（第 46 週）

### 變更
- 整合並清理文檔結構
- 將 API 文檔移至根目錄，提升可存取性
- 釐清所有文檔中的 tenant_id 使用方式

### 移除
- 未使用的未來功能設計文檔

### 修復
- 改善報告生成的防重複邏輯

---

## [0.1.0] - 2025-11-18

**Phase 3 發布** - 認證與業務邏輯

### 新增
- JWT 認證系統（24 小時有效期）
- Client、Case、Session CRUD，自動生成代碼
- 報告生成，使用非同步 background tasks
- iOS 專用 UI 整合 API（`/api/v1/ui/*`）
- Web console，用於 API 測試
- 多租戶架構與 RBAC

### 安全性
- bcrypt 密碼雜湊、JWT 認證
- 多租戶資料隔離與列級權限

---

## [0.0.5] - 2025-10-17

### 新增
- 改善 RAG 對話意圖分類，降低相似度門檻

### 變更
- 報告生成從 SSE streaming 改為直接 JSON 回應
- 改善上傳錯誤處理和表單欄位名稱

### 修復
- 移除 PDF 文字中的 NUL 字元再存入 PostgreSQL
- 改善報告生成 UI 的錯誤可見度

### 移除
- 移除過時的 RAG PDF 報告

---

## [0.0.4] - 2025-10-12

### 新增
- 報告生成的輸出格式參數
- RAG 系統比較模式
- 週進度報告（第 41 週）

### 變更
- 報告生成從 GET 改為 POST
- Cloud Run 記憶體限制至 1Gi
- RAG 系統改用 Gemini

### 修復
- Docker 中安裝 git 以支援 ragas 依賴
- RAG 檢索和比較模式 UX

### 效能
- 增強統計頁面，支援各策略顯示

---

## [0.0.3] - 2025-10-05

### 新增
- Chunk 策略 API，包含矩陣視覺化
- RAG 評估系統，包含矩陣視圖和批次評估
- 增強評估矩陣，整合 chunk 策略

### 效能
- 組織側邊欄導航，改善 UX

---

## [0.0.2] - 2025-10-04

### 新增
- 多環境部署（staging/production）
- 案件報告的表格格式

### 變更
- Cloud Run 記憶體從 128Mi 至 512Mi

### 修復
- 佔位符憑證，避免機密洩漏誤判
- 文檔重組

---

## [0.0.1] - 2025-10-03

**初始發布** - RAG 系統基礎

### 新增
- RAG Console，整合 Supabase
- RAG 系統模型和 API 端點
- RAG 處理服務（chunking, embedding, retrieval）
- 諮詢 console UI，支援文件上傳

### 變更
- RAG chat 測試改用整合方法

### 修復
- 檔案上傳功能
- RAG Console 除錯和 UI

### 基礎設施
- GitHub Actions CI/CD 至 Cloud Run
- Docker 容器化，使用 Poetry
- Workload Identity Federation 用於部署

---

## 開發時間軸

### 📅 第一階段：RAG 基礎建設（2025 年 10 月）
**期間**：2 週 | **版本**：0.0.1 - 0.0.3

建立核心 RAG（檢索增強生成）系統基礎設施：
- 文件處理流程（chunking, embedding, retrieval）
- RAG 評估系統，包含矩陣視覺化
- Cloud Run 部署，包含 CI/CD 自動化
- Supabase 整合，用於向量儲存（pgvector）

**關鍵成就**：完整功能的 RAG 引擎，用於知識檢索

---

### 📅 第二階段：RAG 優化（2025 年 10 月）
**期間**：1 週 | **版本**：0.0.4 - 0.0.5

增強 RAG 能力和報告生成：
- 多格式報告輸出（JSON, Markdown, Table）
- Vertex AI RAG 比較和評估
- Gemini 2.5 整合，改善效能
- 智慧對話路由的意圖分類

**關鍵成就**：生產就緒的 RAG 系統，成本降低 40%

---

### 📅 第三階段：業務邏輯（2025 年 11 月）
**期間**：2 週 | **版本**：0.1.0 - 0.3.1

建立完整的諮詢平台，包含認證和 CRUD 操作：
- JWT 認證，多租戶隔離
- Client, Case, Session 管理
- 即時逐字稿關鍵字分析
- iOS 優化 API，效能調校（快 3-5 倍）
- 100% 整合測試覆蓋率（106 個測試）

**關鍵成就**：完整的諮詢平台，準備好整合 iOS

---

## 版本歷史總覽

| 版本 | 日期 | 階段 | 主要功能 |
|------|------|------|----------|
| **0.3.1** | 2025-11-29 | **第三階段** | 即時關鍵字分析、Session 命名、Gemini 2.5 Flash |
| 0.3.0 | 2025-11-25 | 第三階段 | N+1 查詢修復、快速 CI、Admin 角色 |
| 0.2.5 | 2025-11-24 | 第三階段 | Pre-commit hooks、100% 測試覆蓋 |
| 0.2.4 | 2025-11-24 | 第三階段 | Mypy 型別檢查、SSL 修復 |
| 0.2.3 | 2025-11-23 | 第三階段 | iPhone 模擬器視圖、Case status 整數 |
| 0.2.2 | 2025-11-22 | 第三階段 | iOS 追加錄音 API |
| 0.2.1 | 2025-11-21 | 第三階段 | Console 改善 |
| 0.2.0 | 2025-11-19 | 第三階段 | 多租戶文檔、API 整合 |
| **0.1.0** | 2025-11-18 | **第三階段** | **認證與業務邏輯** |
| 0.0.5 | 2025-10-17 | 第二階段 | RAG 對話改善、報告生成修復 |
| 0.0.4 | 2025-10-12 | 第二階段 | 報告格式、RAG 比較、Vertex AI POC |
| 0.0.3 | 2025-10-05 | 第一階段 | Chunk 策略、評估矩陣 |
| 0.0.2 | 2025-10-04 | 第一階段 | 多環境部署、報告表格 |
| **0.0.1** | 2025-10-03 | **第一階段** | **RAG 系統基礎** |

**總開發時間**：約 8 週（2025-10-03 ~ 2025-11-29）
**總版本數**：14 個發布版本
**總提交數**：227

---

## 升級指南

### 從 0.3.0 升級到 0.3.1

**新功能可用**：
- 使用 `POST /api/v1/sessions/{id}/analyze-keywords` 進行即時關鍵字分析
- 創建 sessions 時可新增選填的 `name` 欄位

**重大變更**：
- 無

**建議行動**：
- 更新 iOS app，在諮詢會談期間利用即時關鍵字分析功能
- 考慮新增 session 命名功能以改善 UX

### 從 0.2.x 升級到 0.3.0

**API 變更**：
- 無重大變更，所有更新都向後相容

**效能改善**：
- Sessions API 現在快 3 倍（回應時間：800ms → 250ms）
- UI client-case-list API 現在快 5 倍（回應時間：1.2s → 240ms）

**建議行動**：
- 無需修改程式碼，直接享受效能提升！

---

## [Keep a Changelog] 分類說明

本專案使用以下變更分類：

- **新增（Added）** - 新功能或端點
- **變更（Changed）** - 現有功能的變更
- **棄用（Deprecated）** - 將在未來版本移除的功能
- **移除（Removed）** - 已移除的功能
- **修復（Fixed）** - Bug 修復
- **安全性（Security）** - 安全性漏洞修復
- **效能（Performance）** - 效能改善和優化

---

**完整提交歷史**：見 [GitHub 儲存庫](https://github.com/Youngger9765/career_ios_backend)
**API 文檔**：造訪 `/docs`（Swagger UI）或 `/redoc`（ReDoc）
**iOS 整合指南**：見 [IOS_API_GUIDE.md](./IOS_API_GUIDE.md)
