# 全站功能審查報告

**審查日期**: 2025-10-03
**基準文件**: PRD.md (v2.0 雙業務線架構)

---

## 一、諮商應用線（業務層）功能檢查

### 1.1 帳號與權限

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| 使用者登入 | `POST /api/v1/auth/login` | ✅ User | ❌ | ⚠️ API存在但需檢查 |
| Token刷新 | `POST /api/v1/auth/refresh` | ✅ User | ❌ | ⚠️ API存在但需檢查 |
| 角色分級 | - | ✅ User.role | ❌ | ⚠️ Model有role欄位 |
| 取得使用者資料 | `GET /api/v1/users/me` | ✅ User | ❌ | ⚠️ API存在但需檢查 |

**缺失**:
- ❌ 登入前台頁面 `/console/login`
- ❌ 使用者管理前台 `/console/users`

---

### 1.2 個案管理

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| 來訪者CRUD | `GET/POST /api/v1/visitors` | ✅ Visitor | ❌ | ⚠️ API存在 |
| 個案CRUD | `GET/POST /api/v1/cases` | ✅ Case | ❌ | ⚠️ API存在 |
| 會談紀錄 | `GET/POST /api/v1/sessions` | ✅ Session | ❌ | ⚠️ API存在 |

**缺失**:
- ❌ 個案管理前台 `/console/cases`
- ❌ 來訪者列表前台 `/console/visitors`
- ❌ 會談紀錄前台 `/console/sessions`

---

### 1.3 雙輸入模式

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| 音訊上傳（模式1） | `POST /api/v1/sessions/{id}/upload-audio` | ✅ Session | ❌ | ⚠️ 需檢查 |
| 逐字稿直傳（模式2） | `POST /api/v1/sessions/{id}/upload-transcript` | ✅ Session | ❌ | ⚠️ 需檢查 |
| 異步任務追蹤 | `GET /api/v1/jobs/{id}` | ✅ Job | ❌ | ⚠️ API存在 |
| STT處理 | - | - | - | ❌ 未實現 |
| 脫敏處理 | - | - | - | ❌ 未實現 |

**Session Model 檢查需求**:
- ⚠️ 需確認有 `audio_path` 欄位
- ⚠️ 需確認有 `transcript_text` 欄位
- ⚠️ 需確認有 `transcript_sanitized` 欄位
- ⚠️ 需確認有 `source_type` 欄位

**缺失**:
- ❌ STT Service (OpenAI Whisper整合)
- ❌ 脫敏Service
- ❌ 音訊上傳前台

---

### 1.4 AI 報告生成

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| 報告生成 | `POST /api/v1/reports/generate` | ✅ Report | ❌ | ⚠️ 需檢查 |
| 調用RAG Agent | 內部調用 `/api/rag/chat` | - | - | ✅ RAG API存在 |
| 取得報告 | `GET /api/v1/reports/{id}` | ✅ Report | ❌ | ⚠️ 需檢查 |
| 報告審核 | `PATCH /api/v1/reports/{id}/review` | ✅ Report | ❌ | ⚠️ 需檢查 |

**Report Model 檢查需求**:
- ⚠️ 需確認有 `content_json` 欄位
- ⚠️ 需確認有 `citations_json` 欄位
- ⚠️ 需確認有 `agent_id` 欄位
- ⚠️ 需確認有 `version` 欄位
- ⚠️ 需確認有 `status` 欄位

**缺失**:
- ❌ 報告生成Service（整合RAG + GPT-4）
- ❌ 報告列表前台 `/console/reports`
- ❌ 報告詳情前台 `/console/reports/{id}`
- ❌ 報告審核前台

---

### 1.5 提醒與追蹤

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| 提醒CRUD | `GET/POST /api/v1/reminders` | ✅ Reminder | ❌ | ⚠️ API存在 |

**缺失**:
- ❌ 提醒列表前台 `/console/reminders`
- ❌ 提醒通知機制

---

## 二、RAG Ops 生產線（管理層）功能檢查

### 2.1 Agent 管理

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| Agent列表 | `GET /api/rag/agents` | ✅ Agent | ⚠️ 部分 | ✅ API存在 |
| Agent建立 | `POST /api/rag/agents` | ✅ Agent | ❌ | ✅ API存在 |
| Agent版本管理 | `/api/rag/agents/{id}/versions` | ✅ AgentVersion | ❌ | ✅ API存在 |
| 版本發布 | `POST /api/rag/agents/{id}/versions/{vid}/publish` | ✅ AgentVersion | ❌ | ✅ API存在 |

**前台狀態**:
- ✅ RAG Console 主頁 `/rag`
- ⚠️ Agent列表頁面 `/rag/agents` (路由存在但無模板)
- ❌ Agent建立頁面
- ❌ Agent編輯頁面

---

### 2.2 文件管理

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| PDF上傳 | `POST /api/rag/ingest/files` | ✅ Document | ✅ | ✅ 完整 |
| URL上傳 | `POST /api/rag/ingest/url` | ✅ Datasource | ❌ | ✅ API存在 |
| 文件列表 | `GET /api/rag/documents` | ✅ Document | ❌ | ⚠️ 需檢查 |
| 文件刪除 | `DELETE /api/rag/documents/{id}` | ✅ Document | ❌ | ⚠️ 需檢查 |
| 重新嵌入 | `POST /api/rag/documents/{id}/reembed` | - | ❌ | ⚠️ 需檢查 |

**前台狀態**:
- ✅ 上傳頁面 `/rag/upload`
- ⚠️ 文件列表頁面 `/rag/documents` (路由存在但無模板)

---

### 2.3 向量檢索與測試

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| 向量搜尋 | `POST /api/rag/search` | ✅ Embedding | ❌ | ✅ API存在 |
| RAG聊天 | `POST /api/rag/chat` | ✅ ChatLog | ❌ | ✅ API存在 |
| 統計資料 | `GET /api/rag/stats` | - | ❌ | ✅ API存在 |

**前台狀態**:
- ⚠️ 測試台頁面 `/rag/test` (路由存在但無模板)

---

### 2.4 Pipeline 與集合

| 功能 | API | Model | 前台 | 狀態 |
|------|-----|-------|------|------|
| Pipeline追蹤 | `GET /api/rag/pipelines/runs` | ✅ PipelineRun | ❌ | ⚠️ 需檢查 |
| Pipeline重試 | `POST /api/rag/pipelines/runs/{id}/retry` | ✅ PipelineRun | ❌ | ⚠️ 需檢查 |
| 集合CRUD | `/api/rag/collections` | ✅ Collection | ❌ | ⚠️ 需檢查 |

**缺失**:
- ❌ Pipeline可視化前台
- ❌ 集合管理前台

---

## 三、資料模型完整性檢查

### 3.1 諮商系統 Models (已存在)

✅ **User** - `app/models/user.py`
✅ **Visitor** - `app/models/visitor.py`
✅ **Case** - `app/models/case.py`
✅ **Session** - `app/models/session.py`
✅ **Job** - `app/models/job.py`
✅ **Report** - `app/models/report.py`
✅ **Reminder** - `app/models/reminder.py`

### 3.2 RAG系統 Models (已存在)

✅ **Agent** - `app/models/agent.py`
✅ **AgentVersion** - `app/models/agent.py`
✅ **Datasource** - `app/models/document.py`
✅ **Document** - `app/models/document.py`
✅ **Chunk** - `app/models/document.py`
✅ **Embedding** - `app/models/document.py`
✅ **Collection** - `app/models/collection.py`
✅ **CollectionItem** - `app/models/collection.py`
✅ **PipelineRun** - `app/models/pipeline.py`
✅ **ChatLog** - `app/models/chat.py`

### 3.3 Model 欄位驗證需求

**需檢查 Session Model**:
```python
# PRD要求欄位:
audio_path           # 音訊檔路徑
transcript_text      # 逐字稿內容
transcript_sanitized # 脫敏後逐字稿
source_type          # [audio|text] 輸入來源
```

**需檢查 Report Model**:
```python
# PRD要求欄位:
content_json    # 結構化報告內容
citations_json  # RAG檢索的理論引用
agent_id        # 使用的Agent ID
version         # 報告版本
status          # 報告狀態
```

---

## 四、關鍵缺失功能清單

### 🔴 高優先級（MVP必要）

#### 諮商應用線:
1. **STT Service** - OpenAI Whisper整合
2. **報告生成Service** - RAG + GPT-4整合
3. **Session Model欄位補齊** - audio_path, transcript_text等
4. **Report Model欄位補齊** - content_json, citations_json等
5. **諮商前台基礎頁面**:
   - `/console/login` - 登入頁
   - `/console/cases` - 個案管理
   - `/console/reports` - 報告列表
   - `/console/reports/{id}` - 報告詳情

#### RAG Ops生產線:
6. **RAG前台補齊**:
   - `/rag/agents` - Agent列表 (模板缺失)
   - `/rag/documents` - 文件列表 (模板缺失)
   - `/rag/test` - 測試台 (模板缺失)

### 🟡 中優先級（Phase 2）

7. **脫敏Service**
8. **報告審核前台**
9. **Pipeline可視化前台**
10. **集合管理前台**
11. **提醒通知機制**

### 🟢 低優先級（Phase 3+）

12. **使用者管理前台**
13. **權限管理UI**
14. **統計分析儀表板**

---

## 五、下一步行動建議

### 立即執行（本週）:

1. **檢查並修復 Model 欄位**
   ```bash
   # 檢查 Session Model
   # 檢查 Report Model
   ```

2. **補齊 RAG Console 模板**
   ```bash
   # 建立 app/templates/rag/agents.html
   # 建立 app/templates/rag/documents.html
   # 建立 app/templates/rag/test.html
   ```

3. **實作核心Service**
   ```bash
   # app/services/stt_service.py
   # app/services/report_service.py (整合RAG)
   ```

4. **建立諮商前台基礎**
   ```bash
   # app/templates/console/ 目錄
   # 登入、個案、報告頁面
   ```

### Phase 2（下週）:

5. 實作脫敏Service
6. 實作報告審核流程
7. Pipeline可視化

### Phase 3（後續）:

8. 進階功能與優化
9. 安全加固
10. 性能調優

---

**審查結論**:
- ✅ 資料模型：95% 完整（需驗證欄位）
- ⚠️ API層：70% 完整（存在但需驗證實作）
- ❌ Service層：30% 完整（缺STT、Report生成）
- ❌ 前台：20% 完整（RAG部分有，諮商前台缺失）

**建議優先順序**: Model驗證 → Service實作 → 前台補齊
