# TODO - 開發任務清單

**最後更新**: 2025-12-31 (重新編排優先順序 - 依技術依賴關係)

---

## 📊 執行優先序總覽

### Phase 1: 🔴 修復關鍵 Bug & 架構清理 (本週，3-5h)
1. **P0-A: 修正 RAG Bug** (2-3h) ← ✅ **已完成** (2025-12-31)
2. **P1-A: 配置管理重構** (1-1.5h) ← ✅ **已完成** (2025-12-31)

### Phase 2: 🟡 API 架構統一 (下週，18-26h)
3. **P0-B: Mode 支援** (6-8h) ← API 統一的前置需求
4. **P0-C: API 統一** (12-18h) ← 淘汰 realtime.py，Web + iOS 共用 API

### Phase 3: 🟢 體驗優化 (第 3 週，6-8h)
5. **P1-B: Streaming 支援** (6-8h) ← 感知延遲從 5.61s → 1-2s

### Phase 4: 🔵 產品增強 (第 4 週+，10-12h)
6. **P2: Prompt 升級 - 8 大流派** (10-12h) ← 產品功能擴充

**關鍵決策邏輯**:
- ✅ 先修 Bug (RAG 失效) → 再清架構 (配置) → 再統一 API → 再優化體驗
- ✅ API 統一依賴 Mode 支援 (先加 mode → 再統一)
- ✅ 架構穩定後再做產品增強 (8 大流派)

---

## ✅ P0-A: 修正 RAG Bug - 執行順序與 Context (已完成 2025-12-31)

### 問題描述 (已解決)
- **Bug 位置**: app/services/keyword_analysis_service.py:184-209
- **問題 1**: RAG 在 Gemini **之後**執行 (應該在之前)
- **問題 2**: RAG context **沒有**被加入 Prompt (功能完全失效)
- **影響**: AI 無法使用 200+ 專家建議句庫，分析品質大幅下降

### 修復任務 ✅ 全部完成
- [x] **Step 1**: 將 RAG 檢索移到 Gemini 調用之前 ✅
- [x] **Step 2**: 格式化 RAG 結果為 Prompt 文本 ✅
- [x] **Step 3**: 將 RAG context 加入 Prompt template ✅
- [x] **Step 4**: 測試驗證 AI 回應中包含 RAG 知識引用 ✅

### 達成成果 ✅
- ✅ RAG 功能恢復正常
- ✅ AI 分析品質提升 (使用專家知識)
- ✅ 0s 性能影響 (只是修正執行順序)
- ✅ 113/113 測試通過 (新增 7 個 RAG 測試)
- ✅ 文檔完整 (docs/bugfix_rag_integration.md)

**優先級**: 🔴 P0 (功能失效，必須立即修復)
**實際時間**: 2 小時 (符合預估)
**Git Commit**: 82cd8d1 (fix: RAG integration bug)

---

## ✅ P1-A: 配置管理重構 - Single Source of Truth (已完成 2025-12-31)

### 問題描述 (已解決)
- **當前問題**: Gemini 配置散落在 5 個地方（.env, config.py, gemini_service.py, cache_manager.py, scripts/）
- **影響**: 每次更換模型/location 需要修改多個檔案，容易遺漏
- **最近案例**: 升級 Gemini 3 Flash 時，需同步更新 5 個檔案的 `LOCATION` 和 `CHAT_MODEL`

### 架構目標：Single Source of Truth ✅ 達成

```
.env (環境變數 - 可覆蓋)
  ↓
app/core/config.py (Settings class - 唯一的配置來源)
  ↓
所有其他模組 (直接從 settings import，無 fallback defaults)
```

### 重構任務清單 ✅ 全部完成

#### Task 1: 清理 gemini_service.py ✅ 完成
- [x] **移除**: Lines 12-21 的所有 `getattr()` 和 fallback defaults ✅
- [x] **修改**: 直接使用 `settings.GEMINI_PROJECT_ID` 等 ✅
- [x] **移除**: `try/except ImportError` 區塊 ✅
- [x] **簡化**: `__init__` 方法直接使用 settings ✅

#### Task 2: 清理 cache_manager.py ✅ 完成
- [x] **移除**: Lines 25-31 的 `getattr()` fallback defaults ✅
- [x] **修改**: 直接使用 `settings.GEMINI_*` ✅
- [x] **簡化**: 初始化邏輯 ✅

#### Task 3: 統一測試腳本配置 ✅ 完成
- [x] **建立**: `scripts/test_config.py` - 測試腳本專用配置模組 ✅
- [x] **更新**: 3 個測試腳本改用 `from test_config import API_BASE_URL` ✅
  - test_cache_cumulative.py ✅
  - test_cache_strategy_a_api.py ✅
  - test_cache_strategy_b_api.py ✅

#### Task 4: 更新文檔 ✅ 完成
- [x] **建立**: `docs/CONFIGURATION.md` - 配置管理指南 ✅
  - 包含 Single Source of Truth 說明
  - 包含模型選擇指南 (Gemini 3 Flash, 2.0 Flash, 1.5 Pro)
  - 包含區域相容性說明 (global vs us-central1)
  - 包含反模式提醒
  - 包含疑難排解指南

#### Task 5: 驗證測試 ✅ 完成
- [x] **整合測試**: 29/29 tests PASS ✅
- [x] **配置加載**: 驗證 settings 正確讀取 ✅
- [x] **Linting**: ruff check 通過 ✅

### 預期成果

**重構前**（當前）:
```
修改模型需要:
1. 修改 .env
2. 修改 app/core/config.py
3. 修改 app/services/gemini_service.py (2 處)
4. 修改 app/services/cache_manager.py
5. 修改 scripts/*.py (多個檔案)

風險: 容易遺漏，不一致
```

**重構後**:
```
修改模型只需:
1. 修改 .env (或)
2. 修改 app/core/config.py 的 default

風險: 零，所有模組自動同步
```

### 影響範圍

**修改檔案** (4 個):
- `app/services/gemini_service.py`
- `app/services/cache_manager.py`
- `scripts/test_config.py` (新建)
- `docs/CONFIGURATION.md` (新建)

**需更新檔案** (3 個):
- `scripts/test_*.py` (3 個測試腳本)

### 達成成果 ✅
- ✅ Single Source of Truth 架構建立
- ✅ 所有 service 模組移除 fallback defaults
- ✅ 測試腳本統一使用 test_config.py
- ✅ 完整配置管理文檔 (docs/CONFIGURATION.md)
- ✅ 29/29 整合測試通過
- ✅ 配置變更測試驗證成功

**優先級**: 🟡 P1 (架構改善，快速見效)
**實際時間**: 55 分鐘 (符合預估 1-1.5h)
**Git Commit**: 待提交

---

## 🔴 P0-B: analyze-partial API mode 支援 (6-8h)

### 背景
- **問題發現**: realtime.py 存在 bug - 將 mode 值存入 analysis_type 欄位
- **架構釐清**: analysis_type (分析方法) vs mode (詳細程度) 是兩個不同維度
- **目標**: 為 analyze-partial API 新增 mode 支援，並修復 realtime.py bug
- **重要性**: API 統一的前置需求 (P0-C 依賴此任務)

### 任務清單

#### 1. 修復 realtime.py 的 bug (app/api/realtime.py:1130)
- [ ] **Bug**: `gbq_data["analysis_type"] = request.mode.value` 錯誤地儲存 mode
- [ ] **修復**: 改為 `analysis_type: "realtime_analysis"`, `mode: request.mode.value`
- [ ] **影響**: 歷史資料可能包含 "emergency"/"practice" 在 analysis_type 欄位
- [ ] **測試**: 驗證修復後 GBQ 資料正確性

#### 2. analyze-partial API 新增 mode 支援
- [ ] **Schema 層** (app/schemas/analysis.py):
  - 新增 `mode: Optional[CounselingMode] = CounselingMode.practice` 到 AnalyzePartialRequest
  - 引用 `from app.schemas.realtime import CounselingMode`
- [ ] **API 層** (app/api/sessions_keywords.py):
  - 傳遞 `mode=request.mode` 到 service layer
- [ ] **Service 層** (app/services/keyword_analysis_service.py):
  - 新增 `mode: CounselingMode = CounselingMode.practice` 參數
  - 根據 tenant_id + mode 選擇 prompt:
    - island_parents + emergency → ISLAND_PARENTS_EMERGENCY_PROMPT
    - island_parents + practice → ISLAND_PARENTS_PRACTICE_PROMPT
    - career → CAREER_PROMPT (不使用 mode)
  - 儲存時 `gbq_data["mode"] = mode.value`

#### 3. Prompt Templates 設計
- [ ] **ISLAND_PARENTS_EMERGENCY_PROMPT** (簡化版 ~400 tokens):
  - 選擇 1-2 句最關鍵建議
  - 聚焦當前最需要處理的問題
  - 快速判斷、快速回應
- [ ] **ISLAND_PARENTS_PRACTICE_PROMPT** (完整版 ~600 tokens):
  - 選擇 3-4 句建議
  - 包含 Bridge 技巧說明
  - 詳細指導與教學
- [ ] **注意**: 不使用 Context Caching（與 realtime.py 不同）

#### 4. 測試
- [ ] Integration tests for analyze-partial with mode parameter
- [ ] Verify emergency mode returns 1-2 suggestions
- [ ] Verify practice mode returns 3-4 suggestions
- [ ] Verify career tenant ignores mode parameter
- [ ] Verify GBQ data structure (analysis_type + mode)

#### 5. 文檔更新
- [ ] PRD.md - 更新 analyze-partial API 文檔
- [ ] CHANGELOG.md - 記錄此變更
- [ ] IOS_API_GUIDE.md - 更新 API 使用範例

### 技術細節
- **無需 migration**: mode 欄位已存在（2025-12-27 創建）
- **向後相容**: mode 參數為 Optional，預設 practice
- **適用範圍**: 僅 island_parents 租戶使用 mode，career 租戶忽略
- **Token 成本**: Emergency ~400 tokens, Practice ~600 tokens (vs Realtime ~1500 tokens)

**優先級**: 🔴 P0 (API 統一的前置需求)
**執行時間**: 6-8 小時
**風險**: 低

---

## 🔴 P0-C: API 統一 - 淘汰 realtime.py 分析邏輯 (12-18h)

### 背景與問題
- **當前問題**: 維護兩套分析邏輯
  - `realtime.py` (1493 行) - 第一版，太 heavy，只給 Web Console 用
  - `analyze-partial` API (922 行 service) - 新版，給 iOS 用
- **影響**: 重複維護、品質不一致、升級困難
- **案例**: 剛升級 Gemini 3 Flash，兩邊都要改
- **浪費**: 改進 prompt/RAG 要做兩次

### 架構目標：統一 API

```
當前 (重複維護):
Web Console → realtime.py /analyze → 舊分析邏輯
iOS App     → analyze-partial API  → 新分析邏輯

目標 (統一):
Web Console → analyze-partial API → 統一分析邏輯
iOS App     → analyze-partial API → 統一分析邏輯
```

---

### Phase 1: 拆解分析 (1-2h)

#### 1.1 realtime.py 的優點 ✅ (可取之處)
- [x] **Sliding Window 機制** (app/api/realtime.py:44-52)
  - `SAFETY_WINDOW_SPEAKER_TURNS = 10` (最近 10 個對話輪次)
  - `ANNOTATED_SAFETY_WINDOW_TURNS = 5` (標註最近 5 輪給 AI)
  - **價值**: 聚焦最近對話，避免歷史干擾

- [x] **Cache Management** (app/services/cache_manager.py)
  - Vertex AI Context Caching 整合
  - System instruction 緩存
  - **價值**: 降低 token 成本（但實測效果 28%，已決定不用）

- [x] **多 Provider 支援** (Gemini + Codeer)
  - `provider_metadata` 追蹤使用的 provider
  - **價值**: 靈活切換 LLM

- [x] **詳細 Prompt Engineering** (CACHE_SYSTEM_INSTRUCTION)
  - 角色定義明確 (counselor vs client)
  - 安全等級評估規則清楚
  - 溫和語氣指導
  - **價值**: Prompt 品質高

- [x] **GBQ Logging** (完整記錄)
  - analysis_type, mode, provider 等 metadata
  - **價值**: 數據分析完整

#### 1.2 analyze-partial 的優點 ✅ (已有優勢)
- [x] **Multi-Tenant 架構** (app/services/keyword_analysis_service.py)
  - `TENANT_PROMPTS` 字典 (career, island_parents)
  - `TENANT_RAG_CATEGORIES` 映射
  - **價值**: 乾淨的租戶隔離

- [x] **RAG 整合** (雖然目前有 bug)
  - RAG 知識檢索
  - 200+ 專家建議句庫
  - **價值**: 知識增強

- [x] **Service Layer 架構** (更乾淨)
  - `KeywordAnalysisService` 封裝分析邏輯
  - API 層只處理 request/response
  - **價值**: 職責分離清楚

- [x] **已升級 Gemini 3 Flash**
  - 性能提升 45% (10.24s → 5.61s)
  - **價值**: 最新最快

#### 1.3 比較表

| 功能 | realtime.py | analyze-partial | 建議 |
|------|-------------|----------------|------|
| **Sliding Window** | ✅ 有 (10 turns) | ❌ 無 | 從 realtime 移植 |
| **Cache Management** | ✅ 有 | ❌ 無 | 不需要 (實測效果差) |
| **Multi-Tenant** | ❌ 無 | ✅ 有 | 保留 analyze-partial |
| **RAG 整合** | ❌ 無 | ✅ 有 (有 bug) | 保留並修復 |
| **Mode 支援** | ✅ 有 (emergency/practice) | 🟡 規劃中 | 從 realtime 移植 |
| **Prompt 品質** | ✅ 高 (詳細) | 🟡 中等 | 合併最佳實踐 |
| **Service 架構** | ❌ 混在 API 層 | ✅ 分離 | 保留 analyze-partial |
| **GBQ Logging** | ✅ 完整 | ✅ 有 | 保留並統一 |
| **代碼量** | ❌ 1493 行 (太重) | ✅ 922 行 | analyze-partial 更輕 |

---

### Phase 2: 設計新模組 (3-4h)

#### 2.1 新模組名稱與職責

**模組**: `app/services/unified_analysis_service.py` (新建)

**職責**:
- 統一的親子對話分析邏輯
- 支援 Multi-Tenant (career, island_parents)
- 支援 Mode (emergency, practice)
- 整合 RAG + Sliding Window
- 乾淨的 Service Layer 架構

#### 2.2 核心設計

```python
# app/services/unified_analysis_service.py

class UnifiedAnalysisService:
    """統一分析服務 - Web + iOS 共用"""

    # 從 realtime.py 移植
    SAFETY_WINDOW_TURNS = 10
    ANNOTATED_WINDOW_TURNS = 5

    # 從 keyword_analysis_service.py 移植並改進
    TENANT_PROMPTS = {
        "career": "...",
        "island_parents": {
            "emergency": "...",  # 簡短快速
            "practice": "...",   # 詳細教學
        }
    }

    async def analyze(
        self,
        transcript: str,           # 完整對話
        recent_segment: str,       # 最近片段 (sliding window)
        tenant_id: str,
        mode: CounselingMode,
        session: Session,
        client: Client,
        case: Case,
    ) -> Dict:
        """統一分析方法"""

        # 1. 應用 Sliding Window (從 realtime 移植)
        windowed_transcript = self._apply_sliding_window(
            transcript,
            window_turns=self.SAFETY_WINDOW_TURNS
        )

        # 2. RAG 檢索 (從 analyze-partial 移植，並修正順序)
        rag_results = await self._retrieve_rag(
            query=recent_segment,
            tenant_id=tenant_id
        )

        # 3. 組裝 Prompt (合併兩邊最佳實踐)
        prompt = self._build_prompt(
            tenant_id=tenant_id,
            mode=mode,
            windowed_transcript=windowed_transcript,
            recent_segment=recent_segment,
            rag_context=rag_results,
            session=session,
            client=client,
            case=case,
        )

        # 4. 調用 Gemini (統一用 Gemini 3 Flash)
        ai_response = await self.gemini_service.generate_text(
            prompt,
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # 5. 解析結果
        return self._parse_response(ai_response, rag_results)
```

#### 2.3 Prompt 合併策略

**合併 realtime.py 和 analyze-partial 的最佳實踐**:

```python
ISLAND_PARENTS_EMERGENCY_PROMPT = """
{從 realtime CACHE_SYSTEM_INSTRUCTION 提取}
【角色定義】CRITICAL:
- counselor = 諮詢師, client = 案主/家長
- 分析焦點：案主的狀況、需求、風險

【分析範圍】CRITICAL:
🎯 主要焦點：最新一分鐘對話 (Sliding Window)
   前面對話僅作背景參考

【安全等級評估】CRITICAL:
⚠️ 僅根據【最近對話】區塊判斷

{從 analyze-partial 加入 RAG}
【專家知識庫】以下是相關教養知識:
{rag_context}

{從 analyze-partial 加入 Multi-Tenant}
完整對話逐字稿 (供參考):
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】(Sliding Window: 最近 {window_turns} 輪)
{recent_windowed_transcript}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

請分析並返回 JSON...
"""
```

---

### Phase 3: 實作任務清單 (8-12h)

#### Task 1: 建立統一服務 (3-4h)
- [ ] **新建**: `app/services/unified_analysis_service.py`
- [ ] **移植**: Sliding Window 邏輯 (from realtime.py)
- [ ] **移植**: Multi-Tenant Prompts (from keyword_analysis_service.py)
- [ ] **移植**: RAG 整合 (from keyword_analysis_service.py)
- [ ] **修復**: RAG 執行順序 bug (在 Gemini 之前)
- [ ] **合併**: Prompt 最佳實踐 (兩邊優點)
- [ ] **統一**: Response Schema (IslandParentAnalysisResponse)

#### Task 2: 更新 analyze-partial API (1-2h)
- [ ] **修改**: `app/api/sessions_keywords.py`
- [ ] **改用**: `UnifiedAnalysisService` 而非 `KeywordAnalysisService`
- [ ] **保持**: API 接口不變 (向後相容)
- [ ] **測試**: 681 行整合測試仍然通過

#### Task 3: Web Console 遷移 (2-3h)
- [ ] **修改**: `app/templates/realtime_counseling.html`
- [ ] **前端**: 改呼叫 `/api/v1/sessions/{id}/analyze-partial`
- [ ] **移除**: 對 `/api/v1/realtime/analyze` 的調用
- [ ] **測試**: Web Console 功能完整

#### Task 4: 淘汰 realtime.py (1-2h)
- [ ] **標記**: `/api/v1/realtime/analyze` 為 Deprecated
- [ ] **保留**: `/api/v1/realtime/stt` (STT 功能仍需要)
- [ ] **保留**: `/api/v1/realtime/report` (報告生成仍需要)
- [ ] **移除**: `analyze_transcript()` 函數 (~400 行)
- [ ] **移除**: `CACHE_SYSTEM_INSTRUCTION` (已移至統一服務)
- [ ] **文檔**: 更新 CHANGELOG 說明棄用

#### Task 5: 測試與驗證 (2-3h)
- [ ] **Web Console 測試**:
  - 錄音 → STT → 分析 → 顯示🟢🟡🔴
  - 動態分析間隔 (15s/30s/60s)
  - 建議顯示
- [ ] **iOS API 測試**:
  - 681 行整合測試通過
  - Practice Mode 功能正常
  - Emergency Mode 功能正常
- [ ] **性能測試**:
  - 確認 Gemini 3 Flash 仍然快速 (~5.61s)
  - Sliding Window 不影響性能
- [ ] **回歸測試**:
  - 所有 integration tests 通過
  - GBQ logging 正確

---

### Phase 4: 後續改進 (可選)

#### 4.1 移除不需要的功能
- [ ] **移除**: CacheManager (實測效果 28%，不值得)
- [ ] **簡化**: Provider 切換邏輯 (只用 Gemini)

#### 4.2 新增改進
- [ ] **新增**: Streaming 支援 (P1 優化)
- [ ] **新增**: Mode 支援 (emergency/practice)
- [ ] **新增**: 8 大流派整合 (P2 產品需求)

---

### 預期成果

**Before (當前)**:
```
維護成本:
- realtime.py (1493 行) - Web 專用
- keyword_analysis_service.py (922 行) - iOS 專用
- 總計: 2415 行，兩套邏輯

改進困難:
- Prompt 改進要做兩次
- RAG 整合要做兩次
- Bug 修復要做兩次
```

**After (統一)**:
```
維護成本:
- unified_analysis_service.py (~800 行) - Web + iOS 共用
- 總計: 800 行，一套邏輯

改進容易:
- Prompt 改進一次
- RAG 整合一次
- Bug 修復一次
```

**節省**: ~60% 代碼量，50% 維護成本

---

### 風險評估

**風險**: 中
**理由**: 影響 Web Console (正在使用中)

**緩解措施**:
1. ✅ 分階段遷移 (先實作 → 測試 → 再切換)
2. ✅ 保留 realtime.py 作為 fallback (標記 deprecated)
3. ✅ 完整回歸測試
4. ✅ Staging 環境先驗證

---

### 執行時間

- **Phase 1-2**: 規劃與設計 (4-6h)
- **Phase 3**: 實作 (8-12h)
- **Phase 4**: 改進 (可選)
- **總計**: 12-18 小時

---

### 相關任務

- **依賴**: P0 修正 RAG Bug (必須先完成)
- **連結**: P2 Mode 支援 (可同時完成)
- **連結**: P2 Prompt 升級 (可同時完成)

---

## 🟡 優先任務 -1：配置管理重構 - Single Source of Truth (2025-12-31)

### 背景與問題
- **當前問題**: Gemini 配置散落在 5 個地方（.env, config.py, gemini_service.py, cache_manager.py, scripts/）
- **影響**: 每次更換模型/location 需要修改多個檔案，容易遺漏
- **最近案例**: 升級 Gemini 3 Flash 時，需同步更新 5 個檔案的 `LOCATION` 和 `CHAT_MODEL`

### 架構目標：Single Source of Truth

```
.env (環境變數 - 可覆蓋)
  ↓
app/core/config.py (Settings class - 唯一的配置來源)
  ↓
所有其他模組 (直接從 settings import，無 fallback defaults)
```

### 重構任務清單

#### Task 1: 清理 gemini_service.py (15 分鐘)
- [ ] **移除**: Lines 12-21 的所有 `getattr()` 和 fallback defaults
- [ ] **修改**: 直接使用 `settings.GEMINI_PROJECT_ID` 等
- [ ] **修改前**:
  ```python
  PROJECT_ID = getattr(settings, "GEMINI_PROJECT_ID", "groovy-iris-473015-h3")
  LOCATION = getattr(settings, "GEMINI_LOCATION", "global")
  CHAT_MODEL = getattr(settings, "GEMINI_CHAT_MODEL", "gemini-3-flash-preview")
  ```
- [ ] **修改後**:
  ```python
  from app.core.config import settings

  # 直接使用 settings，不需要 fallback
  PROJECT_ID = settings.GEMINI_PROJECT_ID
  LOCATION = settings.GEMINI_LOCATION
  CHAT_MODEL = settings.GEMINI_CHAT_MODEL
  ```
- [ ] **移除**: `try/except ImportError` 區塊（不再需要）
- [ ] **簡化**: `__init__` 方法直接使用 settings

#### Task 2: 清理 cache_manager.py (10 分鐘)
- [ ] **移除**: Lines 25-31 的 `getattr()` fallback defaults
- [ ] **修改**: 直接使用 `settings.GEMINI_*`
- [ ] **簡化**: 初始化邏輯

#### Task 3: 統一測試腳本配置 (15 分鐘)
- [ ] **建立**: `scripts/test_config.py` - 測試腳本專用配置模組
  ```python
  # scripts/test_config.py
  import sys
  import os
  sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

  from app.core.config import settings

  # Re-export for test scripts
  PROJECT_ID = settings.GEMINI_PROJECT_ID
  LOCATION = settings.GEMINI_LOCATION
  CHAT_MODEL = settings.GEMINI_CHAT_MODEL
  ```
- [ ] **更新**: 所有 `scripts/test_*.py` 改用 `from test_config import *`
- [ ] **檔案清單**:
  - `test_vertex_ai_caching.py`
  - `test_gemini_context_caching.py`
  - `test_explicit_cache.py`
  - `test_timing_average.py`
  - `test_detailed_timing.py`
  - `test_real_api_e2e.py`

#### Task 4: 更新文檔 (10 分鐘)
- [ ] **建立**: `docs/CONFIGURATION.md` - 配置管理指南
  ```markdown
  # 配置管理指南

  ## 修改 Gemini 模型/Region

  1. 修改 `.env`:
     ```
     GEMINI_LOCATION=global
     GEMINI_CHAT_MODEL=gemini-3-flash-preview
     ```

  2. (可選) 修改 `app/core/config.py` 的 defaults

  3. 完成！所有模組自動使用新配置

  ## ❌ 不要做的事
  - ❌ 不要在其他檔案加 fallback defaults
  - ❌ 不要使用 `getattr(settings, "KEY", "fallback")`
  - ❌ 不要在測試腳本直接寫死配置
  ```
- [ ] **更新**: README.md 加入配置管理說明連結

#### Task 5: 驗證測試 (15 分鐘)
- [ ] **單元測試**: 驗證所有模組正確讀取 settings
- [ ] **整合測試**: 運行 `poetry run pytest tests/integration/` 確保沒有破壞
- [ ] **腳本測試**: 運行所有 `scripts/test_*.py` 確保配置正確
- [ ] **環境變數測試**: 修改 `.env` 後驗證生效

### 預期成果

**重構前**（當前）:
```
修改模型需要:
1. 修改 .env
2. 修改 app/core/config.py
3. 修改 app/services/gemini_service.py (2 處)
4. 修改 app/services/cache_manager.py
5. 修改 scripts/*.py (多個檔案)

風險: 容易遺漏，不一致
```

**重構後**:
```
修改模型只需:
1. 修改 .env (或)
2. 修改 app/core/config.py 的 default

風險: 零，所有模組自動同步
```

### 影響範圍

**修改檔案** (4 個):
- `app/services/gemini_service.py`
- `app/services/cache_manager.py`
- `scripts/test_config.py` (新建)
- `docs/CONFIGURATION.md` (新建)

**需更新檔案** (6+ 個):
- `scripts/test_*.py` (所有測試腳本)

### 執行時間

- **總計**: ~1-1.5 小時
- **風險**: 極低（純粹重構，不改邏輯）
- **優先級**: 中（架構改善，非緊急）

---

## 🔴 優先任務 0：性能優化 - analyze-partial API (2025-12-31)

### 背景
- **✅ 已完成**: 升級 Gemini 3 Flash - 性能提升 **45%**！
  - 升級前 (Gemini 2.5 Flash): 10.24s 平均
  - 升級後 (Gemini 3 Flash): **5.61s 平均** ← 當前性能
- **主要瓶頸**: Gemini API (4.64s, 83%) + RAG 檢索 (0.97s, 17%)
- **關鍵問題**: RAG 在 Gemini 之後執行，且沒有真正用在 Prompt 裡（功能失效）
- **優化目標**: 修復 RAG bug（品質提升）+ Streaming（感知速度提升）

### 詳細分析文檔
- 📊 [性能測試報告](docs/LIGHT_VS_HEAVY_ANALYSIS.md) - 真實測試數據（5 次平均）
- 🚀 [優化機會分析](docs/OPTIMIZATION_OPPORTUNITIES.md) - 6 個優化方向詳細評估

### 任務清單

#### Phase 1: 快速見效（本週，4-6h）

**🔴 P0-1: 修正 RAG 執行順序（必做）**
- [ ] **問題**: RAG 在 Gemini 之後執行（app/services/keyword_analysis_service.py:184-209）
- [ ] **問題**: RAG context 沒有被加入 Prompt（功能失效）
- [ ] **修復**:
  1. 將 RAG 檢索移到 Gemini 調用之前（line 175 之前）
  2. 格式化 RAG 結果為 Prompt 文本
  3. 將 RAG context 加入 Prompt template（新增 `{rag_knowledge}` 變數）
- [ ] **影響**: 品質大幅提升（AI 真正能用到 RAG 知識）
- [ ] **測試**: 驗證 AI 回應中包含 RAG 知識的引用
- 📝 預期: 0s 性能改善，但功能修復（這是 bug）
- ⏱️ 成本: 2-3 小時

**🟢 P2-1: 並行化 RAG + DB 查詢**
- [ ] 使用 `asyncio.gather()` 並行執行 context building 和 RAG 檢索
- [ ] 修改 `_build_context()` 為 async 方法
- [ ] 測試: 驗證並行執行正確性
- 📝 預期: 節省 0.2s
- ⏱️ 成本: 2-3 小時

#### Phase 2: 核心優化（下週，3-4h）

**❌ P1-1: Gemini Context Caching（已測試，不實作）**
- [x] **測試結果** (2025-12-31):
  - 基準線: 2.98s
  - 使用緩存: 2.13s
  - 節省比例: **28.4%** (不是宣稱的 50%)
  - ⚠️ **API 將在 2026-06-24 棄用**
- [x] **決策**: **不實作**
  - 理由 1: 效果不如預期（28% vs 50%）
  - 理由 2: API 明年中旬將被棄用
  - 理由 3: 增加複雜度但收益有限
  - 理由 4: 第一次建立緩存反而更慢 (4.14s vs 2.98s)
- 📝 詳見測試報告: `scripts/test_vertex_ai_caching.py`

**🟢 P2-2: RAG 結果緩存**
- [ ] 使用 `functools.lru_cache` 或 Redis 緩存 RAG 查詢結果
- [ ] 緩存 key: MD5(query[:100])
- [ ] 緩存 TTL: 1 小時
- [ ] 測試: 驗證緩存命中率（預期 10-20%）
- 📝 預期: 平均節省 0.2-0.3s
- ⏱️ 成本: 3-4 小時

#### Phase 3: 體驗優化（第 3 週，8-10h）

**🟡 P1-2: Gemini Streaming（體驗提升）**
- [ ] **原理**: 使用 `generate_content_stream()` 逐 Token 返回
- [ ] **Backend**:
  1. 新增 `/api/v1/sessions/{id}/analyze-partial-stream` endpoint
  2. 使用 SSE (Server-Sent Events) 或 WebSocket
  3. 逐步發送 chunk 給前端
- [ ] **Frontend**:
  1. 處理 streaming 連線
  2. 即時更新 UI（逐字顯示）
- [ ] **測試**:
  - 實際時間: 8.5s（不變）
  - 感知時間: 1-2s（用戶看到第一個字）
- 📝 預期: 感知延遲從 8.5s → **1-2s**
- ⏱️ 成本: 6-8 小時

#### Phase 4: 可選優化（第 4 週，8-10h）

**🟣 P3-1: 測試 Gemini Flash-8B（需驗證品質）**
- [ ] **目標**: 使用更快的模型（Gemini 1.5 Flash-8B）
- [ ] **測試方案**:
  1. 準備 50 個真實對話案例
  2. 分別用 Flash vs Flash-8B 分析
  3. 比較 safety_level 準確率、建議品質、速度
- [ ] **A/B 測試**: 真實用戶數據驗證
- [ ] **決策點**: 品質損失是否可接受？
- 📝 預期: 省 **3-5s (60%)**，但品質可能下降
- ⚠️ 風險: 中（需確認品質）
- ⏱️ 成本: 6-8 小時

### 預期成果（更新於 2025-12-31）

**✅ 已完成: 升級 Gemini 3 Flash**:
```
升級前: 10.24s 平均 (Gemini 2.5 Flash)
升級後: 5.61s 平均 (Gemini 3 Flash)
改善: 45% ✅
```

**短期（Phase 1-2，1-2 週）**:
```
當前: 5.61s 平均 (Gemini 3 Flash)
優化後: 5.3-5.5s 平均（P0 修正 RAG + P2 並行化 + RAG 緩存）
改善: ~5-10%
成本: 7-10 小時
風險: 極低

重點: 主要收益在修正 RAG bug（品質大幅提升）
```

**中期（+ Phase 3，3 週）**:
```
當前: 5.61s 平均
優化後: 5.3s 平均（實際）+ 1-2s（感知）
改善: 感知延遲從 5.61s → 1-2s（用戶體驗巨大改善！）
成本: 14-18 小時
風險: 低

重點: Streaming 是最有效的用戶體驗優化
      用戶 1-2 秒後就開始看到建議內容
```

**長期（可選）**:
```
當前: 5.61s 平均
優化後: N/A

註: Gemini 3 Flash 已經是最快的模型
    不再需要測試 Flash-8B (該項目已移除)
```

### 執行優先級建議（更新於 2025-12-31）

1. **立即執行（本週）**: P0-1 修正 RAG 順序 ← 這是 bug，必須修
2. **體驗優化（第 2 週）**: P1-2 Streaming ← **最有效的用戶體驗提升**
3. **性能微調（隨時）**: P2-1 並行化, P2-2 RAG 緩存 ← 小改善但成本低
4. **可選（評估後）**: P3-1 測試 Flash-8B ← 最大性能提升但需嚴格驗證品質

**關鍵結論**:
- ❌ Context Caching: 已測試，不實作（效果 28% < 50%，且 2026 棄用）
- ✅ Streaming: **最優先**（感知延遲從 10s → 1-2s）
- ✅ Flash-8B: **最大潛力**（可省 60%），但需嚴格品質測試

---

## 🔴 優先任務 1：analyze-partial API mode 支援 (2025-12-31)

### 背景
- **問題發現**: realtime.py 存在 bug - 將 mode 值存入 analysis_type 欄位
- **架構釐清**: analysis_type (分析方法) vs mode (詳細程度) 是兩個不同維度
- **目標**: 為 analyze-partial API 新增 mode 支援，並修復 realtime.py bug

---

## 🟡 優先任務 2：Prompt 升級 - 整合客戶需求（8 大流派 + 具體話術）(2025-12-31)

### 背景
- **客戶需求**：逗點教室希望參考 GPT 設定方式，加入"具體話術"（逐字稿級別）
- **客戶提供**：8 大教養流派整合架構 + 5 步驟思考邏輯
- **當前狀態**：我們的 prompt 較簡短，建議句為 1-2 句，缺少詳細對話範例
- **目標**：在保留現有 JSON 架構下，提供更詳細的話術指導

### 相容性分析

#### ✅ 高度相容（80%）
- **理論基礎重疊**: 客戶的 8 大流派 vs 我們的 7 種理論標籤
  - 共同：阿德勒正向教養、薩提爾、Gottman、依附理論、神經科學
  - 客戶獨有：ABA、Ross Greene (CPS)、社會意識教養
- **核心價值一致**: 同理心、溫和引導、具體行動
- **現有 RAG 已支援**: 7 種理論標籤（依附、正向教養、發展心理、家庭系統、認知行為、情緒教練、綜合）

#### ⚠️ 需要調整
| 維度 | 客戶期望 | 當前系統 | 差距 |
|------|---------|---------|------|
| **話術詳細度** | 逐字稿級別（Dr. Becky 風格） | 1-2 句簡短建議 | 🔴 大 |
| **思考架構** | 明確 5 步驟 | 隱含在 prompt | 🟡 中 |
| **理論顯性化** | 明確標註流派來源 | RAG 標籤（已有） | 🟢 小 |
| **輸出格式** | 自由文本 | 結構化 JSON | 🟡 中 |

### 整合方案：方案 B（推薦）

#### 核心策略
1. ✅ **保留現有架構**（JSON response, safety_level, suggestions）
2. ➕ **新增 `detailed_scripts` 欄位**（逐字稿級別話術，可選）
3. 🔄 **升級 Prompt**（整合 8 大流派 5 步驟思考）
4. 📚 **擴充建議句庫**（200 → 300+ 句，加入對話範例）

### 任務清單

#### 1. Response Schema 擴充
- [ ] **新增 DetailedScript Model** (app/schemas/analysis.py):
  ```python
  class DetailedScript(BaseModel):
      situation: str  # "當孩子拒絕寫作業時"
      parent_script: str  # 逐字稿話術（150-300 字）
      child_likely_response: str  # 孩子可能的回應
      theory_basis: str  # "薩提爾模式 + Dr. Becky"
      step: str  # "同理連結" | "解決策略"
  ```
- [ ] **擴充 IslandParentAnalysisResponse**:
  ```python
  class IslandParentAnalysisResponse(BaseModel):
      # 現有欄位（保留）
      safety_level: str
      severity: int
      display_text: str
      action_suggestion: str
      suggested_interval_seconds: int

      # 新增欄位
      detailed_scripts: Optional[List[DetailedScript]] = None  # 新增！
      theoretical_frameworks: Optional[List[str]] = None  # 使用的流派
      thinking_steps: Optional[Dict[str, str]] = None  # 5 步驟思考過程（可選，debug 用）
  ```

#### 2. Prompt Template 升級

**2.1 Practice Mode Prompt 整合 8 大流派**
- [ ] 在 ISLAND_PARENTS_PRACTICE_PROMPT 中新增：
  - **角色定義**: "你是專業親子教養顧問，精通 8 大流派"
  - **8 大流派明確列出**:
    1. 阿德勒正向教養
    2. 薩提爾模式（冰山理論）
    3. 行為分析學派 (ABA, ABC 模式)
    4. 人際神經生物學 (Dan Siegel, 全腦教養)
    5. 情緒輔導 (John Gottman, 情緒教練)
    6. 協作解決問題 (Ross Greene, CPS)
    7. 現代依附與內在觀點 (Dr. Becky Kennedy)
    8. 社會意識與價值觀教養（性別平權、身體自主權）
  - **5 步驟思考架構**:
    ```
    【分析步驟】(內化於建議中，不需全部輸出):
    1. 分析狀態 (Siegel/ABA): 上層腦 vs 下層腦？環境前因？依附焦慮？
    2. 意識檢核 (Feminism): 是否受性別框架影響？
    3. 同理連結 (薩提爾/Gottman): 冰山探索、情緒標註
    4. 解決策略 (阿德勒/Ross Greene): 習慣養成 or 協商技巧
    5. 具體話術 (Dr. Becky): 提供逐字稿級別對話範例
    ```

**2.2 新增 detailed_scripts 輸出指令**
- [ ] Prompt 中新增：
  ```
  【輸出格式】JSON:
  {
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "簡短提示（1 句話）",
    "action_suggestion": "核心建議（1-2 句）",
    "suggested_interval_seconds": 15-60,

    // 新增：詳細話術（Practice Mode 必填）
    "detailed_scripts": [
      {
        "situation": "當孩子拒絕寫作業時",
        "parent_script": "（蹲下與孩子平視）我看到你現在不想寫作業，身體好像很累的樣子。我猜你可能是因為今天在學校已經很努力了，現在需要休息一下，對嗎？（停頓，等待回應）\n\n如果你現在真的很累，我們可以一起想想看：是要先休息 10 分鐘再開始，還是我們一起做，我在旁邊陪你？你覺得哪一個對你來說比較容易開始？",
        "child_likely_response": "可能回應：「我就是不想寫！」或「我想先玩」",
        "theory_basis": "薩提爾模式（冰山探索）+ Dr. Becky（具體話術）+ 阿德勒（尊重選擇）",
        "step": "同理連結 → 解決策略"
      }
    ],

    // 新增：理論來源標註
    "theoretical_frameworks": ["薩提爾模式", "Dr. Becky Kennedy", "阿德勒正向教養"]
  }
  ```

**2.3 Emergency Mode Prompt 調整**
- [ ] Emergency Mode 不提供 detailed_scripts（保持簡短快速）
- [ ] 但仍整合 8 大流派思考（內化，不輸出）

#### 3. 建議句庫擴充

**3.1 擴充專家建議句** (app/data/island_parents_expert_suggestions.json)
- [ ] 當前：200 句（綠 100 / 黃 70 / 紅 30）
- [ ] 目標：300+ 句
- [ ] 新增類型：
  - **對話範例句**（50 句）: "可以這樣說：「我看到...我猜...你覺得...」"
  - **薩提爾冰山句**（30 句）: "探索感受：「你心裡現在是什麼感覺？」"
  - **Dr. Becky 風格句**（30 句）: "我知道這對你來說很難。我會陪著你。"
  - **ABA 環境設計句**（20 句）: "我們可以調整環境：先把玩具收起來，只留..."
  - **Ross Greene 協商句**（20 句）: "我們一起想辦法：你的擔心是...我的擔心是..."

**3.2 建議句分級**
- [ ] 每句標註理論來源（metadata）
- [ ] 每句標註步驟（分析/同理/策略/話術）

#### 4. Service Layer 實作

**4.1 keyword_analysis_service.py 調整**
- [ ] `analyze_partial()` 方法新增 `include_detailed_scripts: bool = False` 參數
- [ ] Practice Mode 預設 `include_detailed_scripts=True`
- [ ] Emergency Mode 預設 `include_detailed_scripts=False`
- [ ] AI Response 解析：新增 detailed_scripts 欄位提取

**4.2 Prompt 動態組裝**
- [ ] Practice Mode: 完整 prompt（8 流派 + 5 步驟 + detailed_scripts 要求）
- [ ] Emergency Mode: 簡化 prompt（8 流派思考 + 簡短建議）

#### 5. API 層調整

**5.1 Request Schema** (app/schemas/analysis.py)
- [ ] AnalyzePartialRequest 新增可選參數：
  ```python
  class AnalyzePartialRequest(BaseModel):
      transcript_segment: str
      mode: Optional[CounselingMode] = CounselingMode.practice
      include_detailed_scripts: Optional[bool] = None  # 新增，預設根據 mode 決定
  ```

**5.2 sessions_keywords.py**
- [ ] 根據 mode 自動設定 `include_detailed_scripts`:
  - practice → True
  - emergency → False

#### 6. 測試

**6.1 Integration Tests**
- [ ] test_practice_mode_detailed_scripts.py:
  - 驗證 Practice Mode 返回 detailed_scripts（1-3 個範例）
  - 驗證話術長度（150-300 字）
  - 驗證包含理論來源標註
- [ ] test_emergency_mode_no_scripts.py:
  - 驗證 Emergency Mode 不返回 detailed_scripts
- [ ] test_theoretical_frameworks_tracking.py:
  - 驗證 theoretical_frameworks 欄位正確標註

**6.2 Prompt 品質測試**
- [ ] 手動測試 10 個真實對話場景
- [ ] 驗證 AI 是否真正整合 8 大流派思考
- [ ] 驗證話術是否達到"逐字稿級別"

#### 7. 文檔更新

- [ ] PRD.md - 新增 "8 大流派整合" 章節
- [ ] IOS_API_GUIDE.md - 更新 Response 範例（含 detailed_scripts）
- [ ] CHANGELOG.md - 記錄此重大升級
- [ ] 新增 `docs/PARENTING_THEORIES.md` - 8 大流派理論說明文檔

### 技術細節

**Token 成本估算**:
- **Practice Mode Prompt**: ~800 tokens（8 流派 + 5 步驟 + 建議句庫）
- **AI Response**: ~500-800 tokens（含 detailed_scripts）
- **總計**: ~1300-1600 tokens/次（vs 當前 ~600 tokens）
- **成本影響**: +117% token 用量，但 Practice Mode 本就是"詳細版"

**向後相容**:
- ✅ 現有 API 調用不受影響（detailed_scripts 為 Optional）
- ✅ Emergency Mode 保持簡短（不受影響）
- ✅ career 租戶不受影響

**實作優先級**:
1. 🔴 **P0**: Response Schema 擴充 + Practice Prompt 升級（核心功能）
2. 🟡 **P1**: 建議句庫擴充（提升品質）
3. 🟢 **P2**: theoretical_frameworks 追蹤（錦上添花）

### 決策點（需與客戶確認）

- [ ] **話術詳細度**: 150-300 字是否足夠？還是需要更長？
- [ ] **輸出數量**: 每次返回幾個 detailed_scripts？（建議 1-2 個）
- [ ] **理論顯性化**: 是否需要在前端顯示理論來源？
- [ ] **成本接受度**: Token 用量增加 117%，成本 +$0.15/次，是否可接受？

### 參考資料
- 客戶提供 GPT Prompt（本次討論）
- 現有 Prompt: `app/api/realtime.py` (CACHE_SYSTEM_INSTRUCTION)
- 建議句庫: `app/data/island_parents_expert_suggestions.json`

---

### 任務清單

#### 1. 修復 realtime.py 的 bug (app/api/realtime.py:1130)
- [ ] **Bug**: `gbq_data["analysis_type"] = request.mode.value` 錯誤地儲存 mode
- [ ] **修復**: 改為 `analysis_type: "realtime_analysis"`, `mode: request.mode.value`
- [ ] **影響**: 歷史資料可能包含 "emergency"/"practice" 在 analysis_type 欄位
- [ ] **測試**: 驗證修復後 GBQ 資料正確性

#### 2. analyze-partial API 新增 mode 支援
- [ ] **Schema 層** (app/schemas/analysis.py):
  - 新增 `mode: Optional[CounselingMode] = CounselingMode.practice` 到 AnalyzePartialRequest
  - 引用 `from app.schemas.realtime import CounselingMode`
- [ ] **API 層** (app/api/sessions_keywords.py):
  - 傳遞 `mode=request.mode` 到 service layer
- [ ] **Service 層** (app/services/keyword_analysis_service.py):
  - 新增 `mode: CounselingMode = CounselingMode.practice` 參數
  - 根據 tenant_id + mode 選擇 prompt:
    - island_parents + emergency → ISLAND_PARENTS_EMERGENCY_PROMPT
    - island_parents + practice → ISLAND_PARENTS_PRACTICE_PROMPT
    - career → CAREER_PROMPT (不使用 mode)
  - 儲存時 `gbq_data["mode"] = mode.value`

#### 3. Prompt Templates 設計
- [ ] **ISLAND_PARENTS_EMERGENCY_PROMPT** (簡化版 ~400 tokens):
  - 選擇 1-2 句最關鍵建議
  - 聚焦當前最需要處理的問題
  - 快速判斷、快速回應
- [ ] **ISLAND_PARENTS_PRACTICE_PROMPT** (完整版 ~600 tokens):
  - 選擇 3-4 句建議
  - 包含 Bridge 技巧說明
  - 詳細指導與教學
- [ ] **注意**: 不使用 Context Caching（與 realtime.py 不同）

#### 4. 測試
- [ ] Integration tests for analyze-partial with mode parameter
- [ ] Verify emergency mode returns 1-2 suggestions
- [ ] Verify practice mode returns 3-4 suggestions
- [ ] Verify career tenant ignores mode parameter
- [ ] Verify GBQ data structure (analysis_type + mode)

#### 5. 文檔更新
- [ ] PRD.md - 更新 analyze-partial API 文檔
- [ ] CHANGELOG.md - 記錄此變更
- [ ] IOS_API_GUIDE.md - 更新 API 使用範例

### 技術細節
- **無需 migration**: mode 欄位已存在（2025-12-27 創建）
- **向後相容**: mode 參數為 Optional，預設 practice
- **適用範圍**: 僅 island_parents 租戶使用 mode，career 租戶忽略
- **Token 成本**: Emergency ~400 tokens, Practice ~600 tokens (vs Realtime ~1500 tokens)

### 參考文件
- `/tmp/correct_architecture.md` - 架構說明
- `/tmp/mode_support_analysis.md` - 影響範圍分析
- `/tmp/decision_code.py` - 決策代碼範例
- `/tmp/prompt_selection_flow.md` - Prompt 選擇流程

### ⚡ 執行計劃（建議）

**Phase 1（本週）：任務 1 - mode 支援** ⏱️ 6-8h
1. 修復 realtime.py bug（1h）
2. Schema/API/Service 層實作（3h）
3. 簡化版 prompt templates（2h）
4. Integration tests（2h）

**Phase 2（本週末）：任務 2 快速驗證** ⏱️ 2-3h
1. 寫測試版 8 大流派 prompt（1h）
2. 手動測試 5 個真實場景（1h）
3. 記錄成本 + 品質數據
4. **決策點**：給客戶確認是否符合期望

**Phase 3（下週）：任務 2 全面實作**（若 Phase 2 通過）⏱️ 10-12h
1. Response Schema 擴充（2h）
2. 完整 Prompt 升級（4h）
3. 建議句庫擴充（3h）
4. Integration tests（3h）

**理由**：
- ✅ 技術基礎優先（mode 是 Prompt 升級的基礎）
- ✅ Bug 修復優先（避免資料持續錯誤）
- ✅ 降低風險（prototype 驗證後再全面投入）
- ✅ 客戶導向（拿真實結果確認期望）

---

**最後更新**: 2025-12-29 (大規模清理：移除 20+ 已完成但未標記的項目，剩餘任務從 ~25 減少至 ~10 個真正待實作項目)

**本次清理摘要**：
- ✅ 標記已完成：Multi-Tenant、Admin Portal、Session 擴充、Email 系統
- ✅ 移除已完成但未標記：Practice/Emergency Mode 錄音流程、History 查詢、個人設定管理、RAG 整合
- ✅ 移除不需要的需求：SMS 登入認證、Session 新欄位（mode/scenario_topic/partial_segments）
- ✅ 重新分類：將產品決策階段任務明確標記，避免誤認為 Backend 待辦

---

## 任務一：Web 改版（Web Realtime Console）

### 1.1 紅綠燈卡片機制（視覺化風險等級）✅ 已完成

**Backend ✅ 已完成**
- Response schema 包含 risk_level, severity, suggested_interval_seconds
- 動態分析間隔：Green 60s / Yellow 30s / Red 15s

**Frontend ✅ 已完成**:
- ✅ 根據 suggested_interval_seconds 動態調整 Timer (`updateAnalysisInterval()`)
- ✅ 紅黃綠視覺化（顏色、大小、動畫）
- ✅ 測試按鈕（🟢🟡🔴）用於快速測試不同風險等級

**實作位置**: `app/templates/realtime_counseling.html`

## 任務三：iOS API 改版 - island_parents 租戶

**詳細規劃文檔**:
- 📋 [浮島 App 完整任務清單](docs/ISLAND_APP_TASKS_REORGANIZED.md) - iOS API + Web Console + Infrastructure
- 🔧 [Session 設計文檔](docs/SESSION_USAGE_CREDIT_DESIGN.md) - DB Log 持久化 + 點數扣除邏輯

**參考 Notion SPEC**:
- SPEC 1: 登入註冊、Onboarding
- SPEC 2: AI 功能模組 (事前練習)
- SPEC 3: AI 功能模組 (事中提醒)
- SPEC 4: History 頁 (諮詢紀錄)
- SPEC 5: Settings 設置頁

---

### 3.0 基礎架構（Infrastructure）

#### 3.0.1 Multi-Tenant 架構擴充 ✅ 已完成 (2025-12-15)
- [x] ✅ 所有 table 都有 tenant_id 欄位
- [x] ✅ API 自動注入 tenant_id（基於 JWT）
- [x] ✅ Query 自動過濾 tenant（避免跨租戶資料洩漏）
- 📝 Commits: 40bf98e, c620474, f0352df
- 📋 完整多租戶隔離機制，支援 career, island, island_parents

#### 3.0.2 Session 資料結構擴充 ✅ 已完成 (2025-12-15)
詳見 [Session 設計文檔](docs/SESSION_USAGE_CREDIT_DESIGN.md) 了解 DB Log 持久化和點數扣除邏輯

- [x] ✅ SessionAnalysisLog table（獨立存儲分析記錄）- 2025-12-15
- [x] ✅ SessionUsage table（使用量追蹤 + 點數扣除）- 2025-12-15
- 📝 Commits: 1eed1d1 (SessionAnalysisLog), f071e4b (SessionUsage + Universal Credit System)
- 📋 Note: mode/scenario_topic/partial_segments 欄位移除（現有 JSONB 欄位已足夠；mode 已在 Realtime API 實作為 request parameter）

#### 3.0.3 Client 物件簡化（island_parents）
- [x] ✅ 新增 `relationship` 欄位（爸爸/媽媽/爺爺/奶奶/外公/外婆/其他）- 2025-12-29
- [x] ✅ 欄位標籤更新："孩子姓名" → "孩子暱稱" - 2025-12-29
- [ ] island_parents 的 Client 只需：name + grade (1-12)
- [ ] Optional 欄位：birth_date, gender, notes（已存在，待確認是否需調整）
- [ ] DB Schema 調整：新增 grade 欄位（待實作）

---

### 3.1 SPEC 1：登入註冊、Onboarding

#### 3.1.1 孩子資料管理（沿用 Client API）✅ 已完成
- [x] ✅ POST /api/v1/clients - 新增孩子（tenant_id=island_parents）
- [x] ✅ GET /api/v1/clients - 列出孩子（自動過濾 tenant）
- [x] ✅ PATCH /api/v1/clients/{id} - 編輯孩子資料
- [x] ✅ DELETE /api/v1/clients/{id} - 刪除孩子
- [x] ✅ 完整 iOS API 整合指南（9 步驟工作流程）- 2025-12-29
- [x] ✅ 完整工作流程整合測試（681 行）- 2025-12-29
- 📝 已可使用，支援 island_parents 租戶的所有 CRUD 操作

---

### 3.2 SPEC 2：AI 功能模組（事前練習）✅ 已完成

#### 3.2.1 練習情境選擇 - 移至產品決策階段
- [ ] GET /api/v1/island/scenarios - 取得預設情境列表（產品待定義情境清單）
  - 孩子不寫作業、兄弟姊妹吵架、睡前拖延、自訂情境
- 📋 Note: API 結構簡單，等產品決策後 1 小時可完成

#### ~~3.2.2 Practice Mode 錄音流程~~ ✅ 已完成 (2025-12-29)
**使用現有 API 實作完成，無需新建 /api/v1/island/sessions**

- [x] ✅ POST /api/v1/sessions - 建立練習會談
- [x] ✅ POST /api/v1/sessions/{id}/recordings/append - 追加錄音片段
- [x] ✅ POST /api/v1/sessions/{id}/analyze-partial - 即時分析（返回🟢🟡🔴）
- [x] ✅ SessionUsage 自動計費（每次 analyze-partial 自動記錄）
- [x] ✅ 681 行整合測試通過（test_island_parents_complete_workflow.py）
- 📋 參考：IOS_API_GUIDE.md (line 487-982), ISLAND_PARENTS_WORKFLOW_TEST_REPORT.md

#### ~~3.2.3 Practice 報告生成~~ ✅ 已完成 (2025-12-29)
- [x] ✅ analyze-partial API 已返回完整分析結果（summary, suggestions, RAG references）
- [x] ✅ 分析歷程記錄：GET /api/v1/sessions/{id}/analysis-logs
- 📋 Note: 報告內容已在即時分析回應中，無需額外 report endpoint

---

### 3.3 SPEC 3：AI 功能模組（事中提醒）✅ 已完成

#### 3.3.1 錄音同意流程 - 產品與法務決策階段
- [ ] 設計錄音同意文案（法務審核）- 產品責任
- [ ] RecordingConsent Model + migration - 等產品確認需求後實作
- [ ] iOS：實戰模式開始前顯示同意彈窗 - iOS 開發責任
- [ ] 隱私政策與合規審查（GDPR, 個資法）- 法務責任
- 📋 Note: Backend API 結構簡單（POST /api/v1/consents），等確認後 2 小時可完成

#### ~~3.3.2 Emergency Mode 錄音流程~~ ✅ 已完成 (2025-12-29)
**與 Practice Mode 使用相同 API，已完成**

- [x] ✅ POST /api/v1/sessions - 建立實戰會談（與 Practice 相同）
- [x] ✅ POST /api/v1/sessions/{id}/analyze-partial - 即時危機提醒
- [x] ✅ 🟢🟡🔴 三級安全判斷（severity 1-3）
- [x] ✅ 動態分析間隔（Red 15s / Yellow 30s / Green 60s）
- [x] ✅ 測試覆蓋：test_7_red_yellow_green_logic_accuracy ✅ PASSED
- 📋 參考：IOS_API_GUIDE.md, test_island_parents_complete_workflow.py

#### ~~3.3.3 Emergency 報告生成~~ ✅ 已完成 (2025-12-29)
- [x] ✅ analyze-partial API 已返回完整分析（與 Practice 相同架構）
- [x] ✅ Emergency 與 Practice 差異已在 AI prompt 層實現
- 📋 Note: 報告內容已在即時分析回應中

---

### 3.4 SPEC 4：History 頁（諮詢紀錄）✅ 已完成

#### 3.4.1 歷史記錄查詢 ✅ 已完成
**使用現有 API，無需新建 /api/v1/island/sessions**

- [x] ✅ GET /api/v1/sessions - 列出所有 sessions
  - ✅ 篩選：client_id (Query parameter)
  - ✅ 分頁支援：skip, limit (Query parameters)
  - ✅ 搜尋：search parameter 支援 client name/code
- [x] ✅ GET /api/v1/sessions/{id} - 單一 session 詳情
  - ✅ 完整逐字稿（transcript_text 欄位）
  - ✅ 分析記錄：GET /api/v1/sessions/{id}/analysis-logs
  - ✅ 使用量統計：GET /api/v1/sessions/{id}/usage
- [x] ✅ GET /api/v1/sessions/timeline - 會談時間線（依 client_id 篩選）
- 📋 參考：IOS_API_GUIDE.md, test_island_parents_complete_workflow.py (test_6_view_session_timeline)

#### 3.4.2 進階查詢功能（P2 可選）- 產品決策階段
- [ ] 排序功能：created_at, duration, safety_level - 等產品確認需求
- [ ] 逐字稿關鍵字搜尋 - PostgreSQL full-text search，2-3 小時可完成
- [ ] 匯出功能（PDF, CSV）- 等產品確認格式需求

---

### 3.5 SPEC 5：Settings 設置頁

#### 3.5.1 個人設定管理 ✅ 已完成
**使用現有 Auth API，無需新建 /api/v1/island/settings**

- [x] ✅ GET /api/auth/me - 取得設定（姓名、email、租戶、角色）
- [x] ✅ PATCH /api/auth/me - 更新設定（full_name, email 等）
- [ ] 隱私設定（notification_enabled）- 等產品決策後加入 Counselor model
- 📋 參考：IOS_API_GUIDE.md (Authentication APIs)

#### 3.5.2 點數查詢與兌換
詳見 [Session 設計文檔](docs/SESSION_USAGE_CREDIT_DESIGN.md) 了解點數系統設計

- [x] ✅ GET /api/auth/me - 已返回 available_credits（查詢點數餘額）
- [ ] POST /api/v1/redeem-codes/redeem - 兌換碼兌換（等產品決策）
- [ ] RedeemCode Model + migration（等產品決策）
- [ ] 低點數警告邏輯（< 100 黃色，< 20 紅色）- iOS App 責任
- 📋 Note: 兌換碼系統結構簡單，確認需求後 3-4 小時可完成

#### 3.5.3 點數有效期管理 - 產品決策階段
- [ ] 定義點數有效期規則（產品決策：每學期/半年/一年）
- [ ] 定義到期處理規則（歸零/滾存/延期）
- [ ] 到期自動處理 Cron Job（每日 00:00）
- [ ] GET /api/v1/credits/expiry - 查詢到期資訊
- [ ] Email 通知整合（到期前 7 天 + 1 天）
- 📋 Note: 等產品規則確認後，Backend 3-4 小時可完成

#### 3.5.4 帳號管理 - 產品決策階段
- [x] ✅ 登出功能 - iOS App 責任（清除本地 token）
- [ ] 刪除帳號（產品決策：是否需要？資料保留政策？）
- [ ] 變更手機號碼（產品決策：是否需要？SMS 認證？）
- 📋 Note: API 結構簡單，等產品決策後各 1-2 小時可完成

#### 3.5.5 進階隱私設定（P2 可選）- 產品決策階段
- [ ] 資料使用授權管理（分析、研究用途）- 法務與產品決策
- [ ] 錄音保存期限偏好設定 - 產品決策
- [ ] 第三方分享設定 - 產品決策
- 📋 Note: 低優先級功能，等產品與法務確認需求

---

### 3.6 WEB Admin 功能

#### 3.6.1 諮詢師管理 ✅ 已完成 (2025-12-15)
- [x] ✅ GET /api/v1/admin/counselors - 列出所有諮詢師
- [x] ✅ GET /api/v1/admin/counselors/{id} - 諮詢師詳情
- [x] ✅ POST /api/v1/admin/counselors - 新增諮詢師（自動發送密碼重設郵件）
- [x] ✅ PATCH /api/v1/admin/counselors/{id} - 更新諮詢師狀態
- [x] ✅ DELETE /api/v1/admin/counselors/{id} - 刪除諮詢師
- [x] ✅ 多租戶隔離（支援跨租戶管理）
- 📝 Commits: b740768, 318350b, 379fabe
- 📋 File: app/api/v1/admin_counselors.py

#### 3.6.1-B 點數管理 ✅ 已完成 (2025-12-15)
- [x] ✅ GET /api/v1/admin/credits/members - 列出所有會員點數
- [x] ✅ GET /api/v1/admin/credits/members/{id} - 單一會員點數詳情
- [x] ✅ POST /api/v1/admin/credits/members/{id}/add - 手動加點
- [x] ✅ GET /api/v1/admin/credits/logs - 查詢點數異動記錄
- [x] ✅ POST /api/v1/admin/credits/rates - 設定費率
- [x] ✅ GET /api/v1/admin/credits/rates - 查詢費率
- 📝 Commits: 4e5dee1, f071e4b
- 📋 File: app/api/v1/admin_credits.py

#### 3.6.2 兌換碼管理（待實作）
- [ ] POST /api/v1/admin/redeem-codes/generate - 批次生成兌換碼
- [ ] GET /api/v1/admin/redeem-codes - 列出所有兌換碼
- [ ] PATCH /api/v1/admin/redeem-codes/{code}/revoke - 停權兌換碼
- [ ] POST /api/v1/admin/credits/extend-expiry - 手動延期點數
- [ ] RedeemCode Model + migration

#### 3.6.3 使用記錄爭議處理（待實作）
- [ ] 定義邊界情境規則（中途取消、離線、靜音）
- [ ] Admin 查看詳細使用記錄
- [ ] Admin 手動調整扣點（需註記原因）

---

### 3.7 其他整合

#### 3.7.1 RAG 知識庫整合 ✅ 已完成
- [x] ✅ island_parents 租戶專用 Prompt（analyze-partial API 自動切換）
- [x] ✅ RAG 知識庫：親子教養相關知識（依附理論、情緒調節等）
- [x] ✅ Response schema：與 Web 版統一的 IslandParentAnalysisResponse
- [x] ✅ 200+ 專家建議句庫（app/data/island_parents_expert_suggestions.json）
- 📋 參考：test_island_parents_complete_workflow.py, IOS_API_GUIDE.md

#### 3.7.2 Case 管理簡化 - 產品決策階段
- [ ] 預設 Case 自動建立（「親子溝通成長」）- 等產品確認命名
- [ ] Create Session 時自動使用預設 Case - 等產品確認流程
- 📋 Note: 目前需手動建立 Case（標準流程），自動建立需產品確認 UX 流程

---

## 任務四：密碼管理與通知系統

### 4.1 帳號建立後自動發送密碼信件
- [x] 整合 Email 服務（Gmail SMTP）
- [x] 設定 Email 模板（歡迎信件）
- [x] 修改 POST /api/v1/admin/counselors 觸發發送
- [x] Tenant-specific email templates（career/island/island_parents）
- [ ] EmailLog Model（記錄發送狀態）

### 4.2 密碼重設頁面（Web）
- [x] 密碼重設請求頁面（/forgot-password）
- [x] PasswordResetToken Model（token, expires_at, used）
- [x] 密碼重設確認頁面（/reset-password）
- [x] 發送密碼重設信件
- [x] Token 延長至 6 小時有效期（開發階段）

### 4.3 密碼重設 API（給 iOS 使用）
- [x] POST /api/v1/password-reset/request - 請求密碼重設
- [x] POST /api/v1/password-reset/verify - 驗證 token
- [x] POST /api/v1/password-reset/confirm - 確認重設密碼
- [x] Token 安全：加密隨機字串（32+ 字元）、6 小時有效期、只能使用一次
- [x] 請求頻率限制（5 分鐘內只能請求一次）
- [x] Multi-tenant 支援（支援 career/island/island_parents）

### 4.4 整合測試與文檔
- [x] 完整流程測試（建立帳號 → 歡迎信 → 密碼重設）
- [x] 23 個整合測試（100% 通過）
- [x] API 文檔更新（Swagger UI）
- [x] DEBUG mode 跨租戶管理員存取

### 4.5 登入失敗提示語統一（資安）
- [ ] Backend: 統一 API 錯誤訊息（密碼錯誤 = 帳號不存在 = "登入資料有誤"）
- [ ] iOS/Web: 統一前端錯誤提示 UI
- [ ] 文檔: 登入失敗訊息規範

### 4.6 Email 發信系統與錯誤處理 🟡 部分完成 (2025-12-27)
- [x] ✅ 選擇並設定 Email 服務商（Gmail SMTP）- 2025-12-27
- [x] ✅ Email Service 實作（發送 + 錯誤處理）- 2025-12-27
- [x] ✅ Tenant-specific email templates（career/island/island_parents）- 2025-12-27
- [x] ✅ SMTP 環境變數配置（GitHub Secrets）- 2025-12-27
- [x] ✅ 密碼重設郵件自動發送（新增諮詢師時）- 2025-12-27
- [ ] EmailLog Model（status: pending/sent/delivered/bounced/failed）- 待實作
- [ ] GET /api/v1/admin/emails/logs API - 待實作
- [ ] POST /api/v1/admin/emails/resend API - 待實作
- [ ] 退信處理機制 - 待實作
- [ ] 用戶端重發機制（5 分鐘限制）- 待實作
- 📝 Commits: 3e40091, 217a5d8, 81e4e57, 75dbfc4
- 📋 File: app/services/email_service.py

### 4.7 密碼強度政策與安全策略
- [ ] 定義密碼規則（最低 8 字元，英文 + 數字）
- [ ] 弱密碼黑名單（123456, password, qwerty...）
- [ ] Counselor Model 更新（failed_login_attempts, locked_until）
- [ ] 登入失敗鎖定機制（5 次失敗 → 鎖定 15 分鐘）
- [ ] 密碼驗證邏輯（Backend）
- [ ] iOS/Web 即時密碼強度檢查 UI
