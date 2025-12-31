# TODO - 開發任務清單

**最後更新**: 2025-12-31 (完成 Phase 1-2 與 P2，大規模清理已完成項目)

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

## 🎯 待辦事項 (未來可能需要)

### 1. Performance Optimization (如需要)
- [ ] Streaming API 支援（iOS/Web 明確需求時）
- [ ] 性能基準測試更新

### 2. Documentation Updates (如需要)
- [ ] API 使用範例更新
- [ ] 新功能文檔補充

### 3. Future Features (產品需求驅動)
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
- 清理後: ~150 行
- 縮減比例: 90%
- 清理原則: 已完成項目移至 CHANGELOG，保留真正待辦事項
