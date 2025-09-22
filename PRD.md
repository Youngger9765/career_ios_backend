# 助人者 App 後端 PRD（單租戶 + FastAPI Mono 架構）

## 1. 產品背景與目標

* **情境**：諮商師與客戶在 iOS App 中對談，App 錄音並將檔案上傳後端。
* **後端責任**：處理錄音、生成逐字稿、產出報告、保存個案資料，並提供 API 給前端。
* **目標**：
  1. 一鍵完成錄音上傳到報告生成。
  2. 確保報告符合助人專業框架，可被審核與監管。
  3. 提供完整的個案管理閉環：個案 → 會談 → 報告 → 提醒。

---

## 2. 功能需求（大項）

### 2.1 帳號與權限
* 諮商師登入、管理員建立帳號
* 角色分級：諮商師 / 督導 / 管理員

### 2.2 客戶與個案
* 建立來訪者資料
* 個案（諮商師 + 來訪者的關係）

### 2.3 會談與錄音
* 每次會談包含：諮商師、客戶、房間資訊、日期時間
* 錄音檔上傳並保存

### 2.4 任務（Ingestion）
* 上傳音訊或文字 → 建立處理任務
* 任務有狀態（排隊 / 處理中 / 完成 / 失敗）

### 2.5 逐字稿與脫敏
* 音訊轉文字
* 保存原稿與脫敏稿（敏感資訊去除）

### 2.6 AI RAG 報告生成
* 使用逐字稿，檢索知識庫（框架、倫理規範）
* 產生結構化報告（摘要、階段分析、策略建議）
* 保存報告與檢索足跡

### 2.7 報告審核
* 督導或管理員可審核報告
* 狀態：草稿 / 通過 / 退回
* 留存歷史版本

### 2.8 提醒與追蹤
* 諮商師可建立提醒（回訪日期、追蹤事項）
* 提供提醒查詢與列表

### 2.9 隱私與安全
* 音訊與逐字稿加密保存
* 預設展示脫敏稿，原始檔需特權存取
* 保留政策：180 天（可調整）

### 2.10 部署與運維
* 使用 FastAPI + Docker + Cloud Run
* PostgreSQL 資料庫
* GCS 存放錄音與報告
* GitHub Actions 自動部署

---

## 3. 使用流程（User Flow）

1. 諮商師登入 iOS App，開始會談
2. 會談錄音完成 → 上傳音訊檔至後端
3. 後端建立任務，保存錄音
4. 後端處理任務 → 轉逐字稿 → 脫敏
5. 後端將逐字稿送入 AI RAG → 生成報告（草稿）
6. 諮商師 / 督導在後台查看並審核報告
7. 通過的報告存入個案紀錄，並可建立提醒
8. 後續回訪時可查詢歷史紀錄與提醒

---

## 4. 資料結構（主要物件）

* **使用者（User）**：id, 姓名, Email, 角色
* **客戶（Visitor）**：id, 姓名/代號, 標籤
* **個案（Case）**：id, 諮商師, 客戶, 狀態
* **會談（Session）**：id, 個案, 日期, 房間, 錄音檔位置, 逐字稿位置
* **任務（Job）**：id, 會談, 類型(audio/text), 狀態
* **報告（Report）**：id, 個案, 會談, 版本, 內容, 狀態
* **提醒（Reminder）**：id, 個案, 日期, 內容, 狀態

---

## 5. FastAPI Mono 架構規劃

### 單一後端服務（mono-repo）
所有 API、服務邏輯集中在一個專案

### 分層結構

* **API 層**：定義路由（使用者、個案、會談、任務、報告、提醒）
* **Service 層**：處理業務邏輯（STT、RAG、審核流程）
* **Repository 層**：負責資料存取（PostgreSQL、GCS）
* **Schema 層**：資料模型定義與驗證（例如 Pydantic 模型）
* **Infra 層**：雲端資源整合（DB 連線、GCS、認證）

### 好處
結構清晰、方便維護、後續可切分成微服務

---

## 6. 成功標準（MVP）

* 從錄音上傳 → 逐字稿 → 報告 → 審核 → 存檔 → 建立提醒，流程能完整跑通
* 管理員與諮商師能透過 API 查詢歷史個案與提醒
* 音訊與文字資料有隱私保護與審核流程

---

## 7. MVP 範圍劃分

### 必做（MVP）

#### 核心功能
* 使用者登入（簡單認證）
* 錄音檔上傳 API
* 音訊轉逐字稿（使用 OpenAI Whisper）
* AI 生成報告（使用 GPT-4）
* 報告查詢 API

#### 基礎資料管理
* 諮商師資料
* 客戶資料（來訪者）
* 個案關聯（諮商師 + 客戶）
* 會談紀錄

#### 最小化安全
* 基本認證（JWT）
* 檔案加密存儲
* 脫敏處理（移除身分證字號、電話）

### 進階功能（Phase 2）

#### 管理功能
* 角色權限管理（諮商師/督導/管理員）
* 報告審核流程
* 版本控制與歷史紀錄

#### 進階處理
* RAG 知識庫建置（專業框架、倫理規範）
* 多語言支援
* 批次處理任務佇列

#### 協作功能
* 提醒與追蹤系統
* 督導評論與批註
* 個案轉介功能

#### 分析與報表
* 個案統計儀表板
* 諮商趨勢分析
* 成效追蹤報告

---

## 8. 技術選型

### 後端框架
* FastAPI (Python 3.11+)
* SQLAlchemy ORM
* Alembic (資料庫遷移)

### 資料庫
* PostgreSQL 15
* Redis (快取與任務佇列)

### 雲端服務
* Google Cloud Run (部署)
* Cloud Storage (檔案儲存)
* Cloud SQL (PostgreSQL)
* Secret Manager (敏感資料)

### AI 服務
* OpenAI Whisper API (語音轉文字)
* GPT-4 API (報告生成)
* Embeddings API (未來 RAG 使用)

### 開發工具
* Poetry (依賴管理)
* Pytest (測試)
* Black + Ruff (程式碼品質)
* GitHub Actions (CI/CD)

---

## 9. API 端點規劃（MVP）

### 認證
* POST /auth/login
* POST /auth/refresh
* POST /auth/logout

### 使用者
* GET /users/me
* PUT /users/me

### 客戶管理
* GET /visitors
* POST /visitors
* GET /visitors/{id}
* PUT /visitors/{id}

### 個案管理
* GET /cases
* POST /cases
* GET /cases/{id}
* PUT /cases/{id}

### 會談與錄音
* POST /sessions
* GET /sessions/{id}
* POST /sessions/{id}/upload-audio
* GET /sessions/{id}/transcript

### 報告
* GET /reports
* GET /reports/{id}
* POST /reports/generate
* GET /reports/{id}/download

### 任務狀態
* GET /jobs/{id}
* GET /jobs

---

## 10. 開發時程（預估）

### Phase 1: MVP (8-10 週)
* Week 1-2: 專案架構、資料庫設計、環境設置
* Week 3-4: 認證系統、使用者管理
* Week 5-6: 客戶與個案管理
* Week 7-8: 錄音上傳、STT 整合
* Week 9-10: AI 報告生成、基礎 API 完成

### Phase 2: 進階功能 (6-8 週)
* Week 11-12: 報告審核流程
* Week 13-14: RAG 知識庫整合
* Week 15-16: 提醒系統
* Week 17-18: 測試、優化、部署

---

## 11. 風險與緩解

### 技術風險
* **AI API 成本**：設定使用上限、快取結果
* **音訊處理延遲**：非同步處理、進度回報
* **資料隱私**：端對端加密、定期稽核

### 業務風險
* **法規合規**：諮詢法務、建立合規檢核表
* **使用者採用**：漸進式推出、教育訓練
* **資料遺失**：定期備份、災難復原計畫

---

## 12. 成功指標

### 技術指標
* API 回應時間 < 200ms (95th percentile)
* 音訊轉文字準確率 > 95%
* 系統可用性 > 99.9%

### 業務指標
* 諮商師採用率 > 80%
* 報告生成時間 < 5 分鐘
* 使用者滿意度 > 4.5/5

---

## 附錄：參考資料

* [FastAPI 官方文件](https://fastapi.tiangolo.com/)
* [OpenAI API 文件](https://platform.openai.com/docs)
* [Google Cloud Run 最佳實踐](https://cloud.google.com/run/docs/bestpractices)
* [HIPAA 合規指南](https://www.hhs.gov/hipaa/for-professionals/security/index.html)