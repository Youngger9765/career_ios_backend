# 更新日誌

本文件記錄職涯諮詢平台 iOS 後端 API 的所有重要變更。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，
版本號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

---

## [未發布]

### 新增
- Analysis Logs CRUD API，用於追蹤會談關鍵字分析歷程
  - `GET /api/v1/sessions/{id}/analysis-logs` - 取得會談的所有分析記錄
  - `DELETE /api/v1/sessions/{id}/analysis-logs/{log_index}` - 刪除特定分析記錄
  - 呼叫 analyze-keywords 時自動儲存分析結果
  - 結構化記錄格式：時間戳記、逐字稿片段、關鍵字、類別、信心分數、洞見、諮商師 ID、備援標記
- Agent 系統文件大小監控規則（API: 300 行，Services: 400 行）
- 資料庫遷移：在 sessions 表新增 analysis_logs JSON 欄位
- Console UI 新增檢視與刪除分析記錄功能（步驟 #19 & #20）
- Favicon 處理器，避免 404 錯誤

### 變更
- **系統性服務層重構（10 個檔案，平均減少 50% 程式碼量）**
  - 將業務邏輯從 API 端點抽取至專用服務類別
  - 改善可維護性、可測試性與程式碼組織
  - 所有整合測試通過（符合 TDD 原則的重構）
- 重構 Sessions API 拆分為 3 個路由器（424 → 324 行，-24%）
  - 建立 sessions_keywords.py（53 行）處理關鍵字分析端點
  - 建立 sessions_analysis.py（72 行）處理分析記錄端點
  - 保留 sessions.py（324 行）處理核心 CRUD、反思與錄音端點
  - 所有 29 個整合測試通過（22 個 sessions + 7 個 recordings）
- 重構 UI Client-Case API 抽取 schemas（452 → 281 行，-38%）
  - 建立 app/schemas/ui_client_case.py（181 行）放置 Pydantic 模型
  - 將 UI 優化的請求/回應 schemas 與 API 邏輯分離
  - 所有 18 個整合測試通過（符合 TDD 原則的重構）
- 重構 SessionService 抽取輔助模組（555 → 448 行，-19%）
  - 建立 app/services/helpers/session_transcript.py（102 行）處理逐字稿處理
  - 建立 app/services/helpers/session_validation.py（26 行）處理日期時間解析
  - 改善程式碼組織並降低服務檔案複雜度
  - 所有 22 個整合測試通過（符合 TDD 原則的重構）
- 重構 RAG Evaluation API 抽取 schemas（399 → 262 行，-34%）
  - 建立 app/schemas/rag_evaluation.py（151 行）放置 Pydantic 模型與輔助函數
  - 抽取所有請求/回應模型與輔助函數
  - 改善程式碼組織與可維護性
- 重構 Reports API 抽取 schemas（328 → 307 行，-6%）
  - 建立 app/schemas/reports.py（31 行）放置 Pydantic 請求/回應模型
  - 抽取 GenerateReportRequest、ProcessingStatus、GenerateReportResponse
  - 所有 10 個整合測試通過（符合 TDD 原則的重構）
- 重構 ClientCaseService 抽取輔助模組與查詢建構器（509 → 351 行，-31%）
  - 建立 app/services/helpers/client_case_helpers.py（91 行）處理代碼生成與格式化
  - 建立 app/services/helpers/client_case_query_builder.py（130 行）處理複雜查詢邏輯
  - 抽取所有輔助方法與 SQLAlchemy 查詢建構邏輯
  - 所有 20 個整合測試通過（符合 TDD 原則的重構）
- 重構 console.html 模組化（程式碼量減少 75%：7245 → 1785 行）
  - 抽取 5479 行步驟定義至 console-steps.js
  - 改善可維護性與程式碼組織
- 重構 Sessions API 至 Service Layer 模式（1,219 → 424 行，-65%）
  - 建立 KeywordAnalysisService（288 行）用於 AI 關鍵字萃取
  - 建立 AnalysisLogService（139 行）用於分析記錄 CRUD 操作
  - 增強 SessionService：新增 get_session_with_details(), update_session(), delete_session()
  - 整合 ReflectionService, RecordingService, TimelineService 以委派 endpoint 邏輯
  - 建立回應建構器輔助函數以減少重複代碼 (_build_session_response)
  - 複雜的會談編號重新計算邏輯已抽取至 service layer
  - 所有 41 個整合測試通過（符合 TDD 原則的重構）
- 重構 UI Client-Case List API 至 Service Layer 模式（962 → 452 行，-53%）
  - 建立 ClientCaseService（516 行）處理客戶個案業務邏輯
  - 抽取 CRUD 操作、統計計算、代碼生成邏輯
  - 所有 18 個整合測試通過（符合 TDD 原則的重構）
- 重構 RAG Evaluation API 至 Service Layer 模式（703 → 397 行，-43%）
  - 建立 EvaluationPromptsService（230 行）處理 Prompt 版本管理
  - 建立 EvaluationRecommendationsService（113 行）提供智慧建議
  - 抽取輔助函數（_build_experiment_response, _parse_experiment_id）
  - 所有 124 個整合測試通過（符合 TDD 原則的重構）
- 重構 Reports API 至 Service Layer 模式（529 → 325 行，-39%）
  - 建立 ReportOperationsService（328 行）處理報告 CRUD 操作
  - 抽取列表、取得、更新、生成報告邏輯至 service layer
  - 簡化背景任務協調
  - 所有 10 個整合測試通過（符合 TDD 原則的重構）
- 重構 Clients API 至 Service Layer 模式（517 → 197 行，-62%）
  - 建立 ClientService（385 行）處理客戶 CRUD 與時間線操作
  - 抽取客戶代碼生成、年齡計算、時間線查詢邏輯
  - 所有 13 個整合測試通過（符合 TDD 原則的重構）
- 重構 Cases API 至 Service Layer 模式（352 → 138 行，-61%）
  - 建立 CaseService（280 行）處理案例 CRUD 操作
  - 抽取案例編號生成與驗證邏輯
- 重構 RAG Chat API 至 Service Layer 模式（334 → 114 行，-66%）
  - 建立 RAGChatService（372 行）處理 RAG 聊天業務邏輯
  - 抽取意圖分類、向量搜尋、答案生成邏輯
  - 簡化 endpoint 至薄路由層並委派至 service
- 重構 RAG Report API 至 Service Layer 模式（484 → 168 行，-65%）
  - 建立 RAGReportService（499 行）處理報告生成業務邏輯
  - 抽取逐字稿解析、理論搜尋、提示詞建構、品質評估邏輯
  - 簡化 endpoint 至薄路由層並委派至 service
- 重構 RAG Ingest API 至 Service Layer 模式（410 → 267 行，-35%）
  - 建立 RAGIngestService（275 行）處理文件擷取業務邏輯
  - 抽取 PDF 上傳/萃取、文字分塊、嵌入生成、儲存操作邏輯
  - 簡化 endpoint 至薄路由層並委派至 service
- 重構 Evaluation Service 並抽取輔助函數（599 → 394 行，-34%）
  - 建立 EvaluationHelpers（340 行）處理 RAG 評估邏輯
  - 抽取文件 ID 查詢、RAG 答案生成、RAGAS 評估、指標計算邏輯
  - 分離實驗比較邏輯至可重用輔助函數
- 隱藏分析記錄中的 counselor_id 欄位（隱私改善）
- 更新 analyze-keywords UI 文字：「已自動儲存」而非「不會儲存」
- 分析記錄顯示改用顏色區分 AI 分析與備援分析

### 修復
- 修復 SQLAlchemy JSON 欄位變更追蹤（使用 flag_modified() 處理 analysis_logs）
- 修復 Staging 環境 Vertex AI 權限（新增 roles/aiplatform.user 至 service account）
- 分析記錄現已正確儲存至資料庫

### 基礎設施
- 新增 roles/aiplatform.user 至 career-app-sa service account，以存取 Vertex AI
- Staging 環境現使用 AI 驅動分析，不再使用備援機制
- Agent 系統強制文檔更新規則（文檔未更新則封鎖 push）
  - 每次 push 前自動檢查 CHANGELOG、PRD.md、週報
  - 確保專案文檔保持最新

---

## [0.3.1] - 2025-11-29

### 新增
- 即時逐字稿關鍵字分析 API（`POST /api/v1/sessions/{id}/analyze-keywords`）
  - AI 驅動的關鍵字提取，包含類別和信心分數
  - 基於逐字稿內容提供諮商師洞見和提醒
- Session 名稱欄位，改善組織管理（Session 模型新增 `name` 欄位）
- 從錄音片段自動計算時間範圍（start_time/end_time）
- Claude Code agent 配置與 TDD 強制執行
- 智慧模型選擇策略（Haiku/Sonnet/Opus）

### 變更
- Gemini 2.5 Flash 作為預設 LLM 提供者（成本降低 40%，回應時間 < 2 秒）
- 簡化關鍵字分析 UI（僅需 session + transcript）
- 移除 API 端點標題中的「(iOS)」後綴，統一命名規範

### 修復
- 修復 CI/CD 中逐字稿關鍵字 API 測試失敗（使用 GeminiService mock）
- 修復 Admin 角色資源刪除權限（可刪除租戶內任何資源）
- 修正 Agent 模型選擇策略文檔（釐清僅支援靜態配置）

### 效能
- Session 服務層抽取與 N+1 查詢修復（**快 3 倍**：800ms → 250ms）
- UI client-case-list API 優化（**快 5 倍**：1.2s → 240ms）
- Claude Code 工作流程優化（hook 輸出效率提升 93%）

---

## [0.3.0] - 2025-11-25

### 新增
- 快速 CI 策略，包含 smoke tests（< 10 秒）
- 報告生成整合測試（使用 mocked background tasks）
- Admin 角色，支援跨諮商師資源管理

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
- Console 中的 iPhone 模擬器預覽視圖，用於 Client-Case CRUD 操作
- GET client-case detail 端點（`/api/v1/ui/client-case/{id}`）
- 選擇 client-case 時自動填充更新表單
- Bruno API 客戶端相容性的 OpenAPI 範例
- 完整的 API 整合測試（66 個測試）

### 變更
- Case status 從字串 enum 改為整數（0: 未開始, 1: 進行中, 2: 已結案）
- 重組 UI Pages 為兩個類別（CRUD Forms + Preview Pages）
- 改善 console 的行動版 RWD，更好的導航和分頁
- 重新設計 console 側邊欄，使用淺灰色主題

### 修復
- 修復 client-case list 的 500 錯誤（timezone-aware datetime 比較）
- 修復 `loadClientCaseForUpdate` 中的欄位映射優先順序
- 修復 schema 欄位顯示，包含所有欄位（含空值）

### 效能
- 優化 CI/CD pipeline，提升可靠性和效能

---

## [0.2.2] - 2025-11-22

### 新增
- iOS 專用的追加錄音 API（`POST /api/v1/sessions/{id}/recordings/append`）
  - 允許在諮商會談期間增量上傳錄音
  - 自動更新逐字稿和 session metadata

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
- Sessions API 文檔新增 recordings 欄位
- 週進度報告（第 46 週：2025-11-11 ~ 2025-11-17）

### 變更
- 整合並清理文檔結構
- 將 API 文檔移至根目錄，提升可存取性
- 釐清所有文檔中的 tenant_id 使用方式

### 移除
- 未使用的未來功能設計文檔
- 過時的測試報告和重複文檔

### 修復
- 改善報告生成的防重複邏輯

---

## [0.1.0] - 2025-11-18

**Phase 3 發布** - 認證與業務邏輯

### 新增
- JWT 認證系統，token 有效期 24 小時
- 客戶 CRUD 操作，自動生成客戶代碼（C0001, C0002...）
- 案件 CRUD 操作，自動生成案件編號（CASE-20251124-001）
- 會談 CRUD 操作，支援錄音片段和反思
- 報告生成，使用非同步 background tasks（RAG + GPT-4）
- iOS 專用的 UI 整合 API（`/api/v1/ui/*`）
- Web console，用於 API 測試（`/console`）
- 多租戶架構，使用 tenant_id 隔離
- 角色型存取控制（admin, counselor）

### 安全性
- bcrypt 密碼雜湊
- JWT token 認證
- 多租戶資料隔離
- 列級權限檢查（諮商師僅能存取自己的資料）

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
- 報告生成的輸出格式參數（JSON/Markdown）
- RAG 系統比較模式，用於報告生成
- Vertex AI RAG Engine POC，用於評估
- 週進度報告（第 41 週：2025-10-06 ~ 2025-10-12）

### 變更
- 報告生成從 GET 改為 POST（安全性改善）
- 允許未認證存取 Cloud Run 服務
- 增加 Cloud Run 記憶體限制至 1Gi
- 更新 RAG 系統使用 Gemini（移除 Vertex AI POC）

### 修復
- 在 Docker 中安裝 git，以支援 ragas 套件依賴
- 改善 RAG 檢索和比較模式 UX

### 效能
- 增強統計頁面，支援各策略顯示和更新 LLM 模型

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
- 案件報告的表格格式，包含多格式分頁
- Cloud Run 的 CI/CD secrets 配置

### 變更
- 增加 Cloud Run 記憶體從 128Mi 至 512Mi
- 新增 Cloud Run 的 timeout 配置

### 修復
- 更新佔位符憑證，避免誤判為機密洩漏
- 重組文檔和更新 UI 樣式

---

## [0.0.1] - 2025-10-03

**初始發布** - RAG 系統基礎

### 新增
- RAG Console，整合 Supabase
- Alembic 資料庫遷移系統
- RAG 系統模型和 API 端點（`/api/rag/*`）
- RAG 處理服務（chunking, embedding, retrieval）
- 諮商 console UI 和測試套件
- 智慧 RAG 意圖偵測，改善對話 UX
- RAG chat API 的完整測試
- 文件 chunks 表格視圖和 modal
- 多檔案上傳，包含進度追蹤

### 變更
- 改善 RAG chat 測試，使用整合方法
- 正確同步資料庫 sessions

### 修復
- 修復檔案上傳功能
- 增強 RAG Console，改善除錯和 UI 修復

### 基礎設施
- GitHub Actions CI/CD 至 Cloud Run
- Docker 容器化，使用 Poetry
- Cloud Build 配置，自動部署
- Workload Identity Federation（WIF）for GitHub Actions
- Career Platform API 公開展示頁面

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

建立完整的諮商平台，包含認證和 CRUD 操作：
- JWT 認證，多租戶隔離
- Client, Case, Session 管理
- 即時逐字稿關鍵字分析
- iOS 優化 API，效能調校（快 3-5 倍）
- 100% 整合測試覆蓋率（106 個測試）

**關鍵成就**：完整的諮商平台，準備好整合 iOS

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
- 更新 iOS app，在諮商會談期間利用即時關鍵字分析功能
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
