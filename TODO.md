# TODO - 開發任務清單

**最後更新**: 2026-01-07 (新增重構優化項目)

---

## 📊 當前狀態總覽

### ⏸️ 暫緩項目
- **P0-C: Phase 3/4** (Web Console 遷移 + 棄用 realtime.py)
  - 理由：analyze-partial 已功能完整，維護成本可接受
  - 重啟條件：realtime.py 出現 bug 或邏輯分歧時

- **P1-B: Streaming 支援**
  - 理由：iOS 不需要，Web 暫不做
  - 重啟條件：產品明確需求時

---

## 🎯 待辦事項

### 🔥 P1 - 高優先級 (本週/下週)

#### 1. 客製化 Prompt - 8 大教養流派強化 ✅ **已完成 Step 1**
**來源**: 逗點教室需求 (2025-12-31)
**完成日期**: 2026-01-01
**狀態**: Step 1 技術實作完成，待逗點實測

**背景**:
- 逗點教室提供了完整的 8 大教養流派 prompt（含回應架構）
- 希望 AI 能提供更具體的「話術」(Scripts)，類似 Dr. Becky Kennedy 風格
- 包含：阿德勒、薩提爾、ABA、Siegel、Gottman、Ross Greene、Dr. Becky、社會正義教養

**架構說明** (2026-01-01 架構驗證):
- ✅ **Web 版本已整合 8 大流派 Prompt**
  - Web 透過 `keyword_analysis_service` 自動使用 8 大流派分析
  - 與 iOS 共用相同分析邏輯（無重複代碼）
  - 回應格式不同（Web: RealtimeAnalyzeResponse, iOS: IslandParentAnalysisResponse）
  - 核心邏輯完全相同（prompts, expert suggestions, RAG knowledge base）
- ✅ **無需額外整合**：Web 和 iOS 使用相同 Prompt 源（`parenting.py`）

**三階段實施策略**:
- **Step 1**: 直接採用新 prompt，讓逗點測試 ✅ **已完成**
  - [x] 整合 8 大流派 prompt 到 `app/prompts/parenting.py`
  - [x] 修改 analyze 使用新 prompt（通過 keyword_analysis_service）
  - [x] Dan Siegel "全腦教養"降低權重並添加科學爭議警告
  - [x] 架構驗證：Web/iOS 已共用相同 8 大流派 Prompt
  - [ ] 建立測試集（5-10 個真實逐字稿範例）← 待逗點提供
  - [ ] 請逗點實測並收集回饋（Web 和 iOS 使用相同 Prompt）← 下一步
  - [ ] 記錄測試結果：是否產生期待的「具體話術」

- **Step 2**: 若不滿意，用 GPTs 校準（實測反推）
  - [ ] 建立 GPTs 測試環境（逗點或我方）
  - [ ] 用真實案例調整 prompt
  - [ ] 反推最佳 prompt 配置

- **Step 3**: 後台客製化（進階選項，非必須）
  - [ ] 設計 prompt 管理介面
  - [ ] 實作 prompt 版本控制
  - [ ] 讓客戶可自行維護 prompt

**風險提醒**:
- Prompt 過長可能超過 context window（需監控 token 使用）
- 8 大流派可能有理論衝突（如 ABA 行為主義 vs 薩提爾內在探索）
- LLM 輸出是質性的，需要測試集驗證 spec match
- 客戶期待 ≠ 實際結果，需管理期待

**預計時間**: Step 1 約 1-2 天

---

#### 2. 提醒頻率優化 - 10秒間隔快速回饋 ✅ **已完成**
**來源**: KM 需求 (2025-12-31)
**完成日期**: 2026-01-01
**狀態**: 方案 B 已上線，待 iOS 整合

**當前問題**:
- RAG + prompt 響應時間較長（重度思考）
- 每兩個提醒間隔過久
- 用戶希望更頻繁的即時回饋

**解決方案**: ✅ 採用「方案 B: 輕量 AI 雞湯文」

**已完成實施**:
- [x] 新增 `/api/v1/realtime/quick-feedback` endpoint
- [x] 設計輕量 AI prompt（情緒控制、表達引導）
- [x] 使用 Gemini Flash（最快模型）+ 不使用 RAG
- [x] 測試響應時間：1-2 秒延遲
- [x] **統一 10 秒輪詢**（不隨燈號改變）
- [x] 動態協調策略：
  - 🟢 綠燈：analyze 60秒 + quick-feedback 10秒
  - 🟡 黃燈：analyze 30秒 + quick-feedback 10秒
  - 🔴 紅燈：analyze 15秒（停用 quick-feedback）
- [x] 完整 iOS 整合文檔（Swift 範例）
- [x] Integration tests（9 tests, 3 passed, 6 require GCP）
- [x] 成本影響分析：+$0.0036/hour (+0.85%)

**待 iOS 整合**:
- [ ] iOS 客戶端實作 10 秒輪詢
- [ ] UI/UX 設計（Toast/浮動提示）
- [ ] 用戶體驗測試

**參考文檔**:
- API 規格：`docs/encouragement_api_integration.md`
- 服務比較：`docs/encouragement_services_report.md`
- CHANGELOG: 2026-01-01 entries

---

### 🔧 P1.5 - 重構優化 (2026-01-07 專案審查)

#### 3. 安全性修復 ✅ **已完成**
- [x] **admin_credits.py DEBUG 模式漏洞** - 已加入環境檢查

#### 4. 代碼品質 ✅ **已完成**
- [x] **Pydantic V2 Deprecation Warnings** - 14 處 class Config 改為 ConfigDict
- [x] **datetime.utcnow() Deprecation** - 3 處改用 `datetime.now(timezone.utc)`

#### 5. 文件同步機制 🟢 (可選)
- [ ] 建立 API 文件驗證腳本 `scripts/validate_api_docs.py`
- [ ] 加入 pre-commit hook（防止文件與 API 不同步）

---

### 📋 P2 - 中優先級 (未來可能需要)

#### 6. Performance Optimization (如需要)
- [ ] Streaming API 支援（iOS/Web 明確需求時）
- [ ] 性能基準測試更新

#### 7. Documentation Updates (如需要)
- [ ] API 使用範例更新
- [ ] 新功能文檔補充

#### 5. Future Features (產品需求驅動)
- [ ] 待產品規劃

---

## 📝 已歸檔項目 (詳見 CHANGELOG.md)

### 2025-12-31 歸檔
**架構改善**:
- ✅ RAG Bug 修復
- ✅ 配置管理重構
- ✅ Mode 支援
- ✅ API 統一 Phase 1

**產品功能**:
- ✅ 8 大教養流派整合
- ✅ Multi-Tenant 架構
- ✅ Admin Portal
- ✅ Session 擴充
- ✅ Practice/Emergency Mode
- ✅ History 查詢
- ✅ 個人設定管理
- ✅ RAG 整合
- ✅ 紅綠燈卡片機制
- ✅ Gemini 3 Flash 升級

**技術債清理**:
- ✅ 移除 CacheManager
- ✅ 移除 CodeerProvider

---

## 🔗 參考文件

- **CHANGELOG.md** - 完整變更歷史（已更新 2025-12-31）
- **CHANGELOG_zh-TW.md** - 中文版變更歷史（已同步）
- **PRD.md** - 產品需求文檔
- **docs/CONFIGURATION.md** - 配置管理指南
- **docs/PARENTING_THEORIES.md** - 8 大教養流派指南
- **docs/bugfix_rag_integration.md** - RAG 修復文檔
- **TODO_backup_20251231.md** - 完整歷史備份（1491 行）

---

**清理統計**:
- 原始行數: 1491 行
- 清理後: 109 行 (2025-12-31)
- 新增需求後: 209 行 (2025-12-31 晚)
- 縮減比例: 86% (相比原始)
- 清理原則: 已完成項目移至 CHANGELOG，保留真正待辦事項
