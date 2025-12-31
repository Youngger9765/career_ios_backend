# TODO - 開發任務清單

**最後更新**: 2025-12-31 (新增兩個 P1 需求：客製化 Prompt + 提醒頻率優化)

---

## 📊 當前狀態總覽

### ✅ 已完成 Phase (2025-12-31)
1. **P0-A: 修正 RAG Bug** ✅ 完成
   - 修復 RAG 執行順序問題（在 Gemini 之前執行）
   - RAG context 正確加入 AI prompts
   - 113/113 測試通過，新增 7 個 RAG 測試
   - Git commit: 82cd8d1

2. **P1-A: 配置管理重構** ✅ 完成
   - 建立 Single Source of Truth 架構
   - 移除所有 getattr() fallback defaults
   - 創建 docs/CONFIGURATION.md
   - 29/29 測試通過

3. **P0-B: Mode 支援** ✅ 完成
   - analyze-partial API 新增 mode 參數
   - 支援 emergency/practice 模式
   - 修復 realtime.py bug (分離 analysis_type 和 mode)
   - 4 個整合測試通過

4. **P0-C: API 統一 - Phase 1** ✅ 完成
   - Sliding Window prompt 註解整合
   - 所有租戶 prompt 品質對齊 realtime.py
   - 373 個整合測試全通過
   - **Phase 3/4 暫緩**（Web Console 遷移延後）

5. **P2: Prompt 升級 - 8 大流派** ✅ 完成
   - 整合 8 大親子教養理論
   - 新增 detailed_scripts 和 theoretical_frameworks 欄位
   - Practice/Emergency Mode 完整支援
   - 整合測試完成

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

#### 1. 客製化 Prompt - 8 大教養流派強化
**來源**: 逗點教室需求 (2025-12-31)
**目標**: 在練習模式中整合更詳細的教養理論角色設定

**背景**:
- 逗點教室提供了完整的 8 大教養流派 prompt（含回應架構）
- 希望 AI 能提供更具體的「話術」(Scripts)，類似 Dr. Becky Kennedy 風格
- 包含：阿德勒、薩提爾、ABA、Siegel、Gottman、Ross Greene、Dr. Becky、社會正義教養

**三階段實施策略**:
- **Step 1**: 直接採用新 prompt，讓逗點測試（最快驗證）
  - [ ] 整合 8 大流派 prompt 到 `app/services/prompt_service.py`
  - [ ] 修改 `analyze_partial`/`analyze_complete` 使用新 prompt（practice mode）
  - [ ] **注意**: Solomon 提醒 Dan Siegel "全腦教養"有偽科學爭議，降低權重/標註
  - [ ] 建立測試集（5-10 個真實逐字稿範例）
  - [ ] 請逗點實測並收集回饋
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

#### 2. 提醒頻率優化 - 10-15 秒間隔回饋
**來源**: KM 需求 (2025-12-31)
**目標**: 縮短【事前練習】【事中提醒】的回饋間隔至 10-15 秒

**當前問題**:
- RAG + prompt 響應時間較長（重度思考）
- 每兩個提醒間隔過久
- 用戶希望更頻繁的即時回饋

**解決方案**: 「雞湯文 + 重度思考」交替模式

```
Timeline:
0s ───→ 10s ───→ 20s ───→ 30s ───→ 40s ───→ 50s
  雞湯文1   雞湯文2   RAG分析1   雞湯文3   雞湯文4   RAG分析2
  (快速)    (快速)    (重度)     (快速)    (快速)    (重度)
```

**實施計畫**:

**方案 A: Rule-Based 雞湯文**（推薦先試）
- [ ] 建立 `app/services/encouragement_service.py`
- [ ] 定義中性鼓勵文句庫（20-30 句）
  - 例如：「做得很好，繼續保持」「維持正常語速」「注意孩子的感受」
- [ ] 定義危險關鍵字規則（打、罵、威脅等）
- [ ] 實作簡單規則引擎：
  - 檢測危險關鍵字 → 警告提示
  - 檢測提問 → 鼓勵引導
  - 預設 → 中性鼓勵
- [ ] 前端整合：每 10-15 秒輪詢顯示
- [ ] A/B 測試：有/無快速提示的用戶體驗差異

**方案 B: 輕量 Prompt 雞湯文**（若 A 不夠靈活）
- [ ] 設計輕量 prompt（< 50 tokens 輸出，一句話建議）
- [ ] 使用 Gemini Flash（最快模型）+ 不用 RAG
- [ ] 測試響應時間（目標 < 2 秒）
- [ ] 前端整合

**前端邏輯**（兩方案共用）:
- [ ] 設計 FeedbackManager
- [ ] 實作優先級邏輯：
  - 有深度分析 → 優先顯示
  - 無深度分析 → 顯示快速提示
- [ ] 用戶體驗測試：10-15 秒間隔是否過於頻繁

**技術說明**:
- RAG 和 Prompt 不可分離（RAG 像查字典找食材，Prompt 是調味，必須一起輸出）
- 目前系統已有判斷是否使用 RAG 的機制（AI 自行判斷）
- 雞湯文填補空白思考時間，為重度分析爭取時間

**風險提醒**:
- 10-15 秒可能太頻繁，造成用戶煩躁（需 A/B 測試）
- 雞湯文句庫太小會顯得機械化（需準備 30+ 句）

**預計時間**: 方案 A 約 2-3 天，方案 B 約 3-4 天

---

### 📋 P2 - 中優先級 (未來可能需要)

#### 3. Performance Optimization (如需要)
- [ ] Streaming API 支援（iOS/Web 明確需求時）
- [ ] 性能基準測試更新

#### 4. Documentation Updates (如需要)
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
