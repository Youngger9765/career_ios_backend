# 更新日誌

本文件記錄職涯諮詢平台 iOS 後端 API 的所有重要變更。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，
版本號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

---

## [未發布]

### 新增
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
- GCP Billing Monitor（AI 分析與 Email 報告，3 個新 API）
- BigQuery 整合實現即時成本追蹤
- Gemini AI 自動化帳單報告生成
- Gemini 回應診斷詳細日誌
- **即時 STT 諮詢系統**（Phase 2 前端完成）：AI 驅動的即時諮詢分析
  - TDD 方法論，11 個整合測試（後端 API 完成）
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
