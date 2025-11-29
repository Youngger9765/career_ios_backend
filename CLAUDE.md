# CLAUDE.md - Prototype 開發策略

---

## 🎯 核心原則：速度優先（Prototype Phase）

**我們在做什麼？**
- ✅ Prototype 後端 API（未上線）
- ✅ 快速驗證功能可行性
- ✅ AI 輔助開發，人工驗證

**不是什麼？**
- ❌ 生產環境系統
- ❌ 需要 100% 測試覆蓋
- ❌ 過度工程化

---

## ⚡ 開發流程（簡化版）

```
1. 寫功能代碼（AI 輔助）
   ↓
2. 手動測試 API（Swagger UI 或 Console）
   ↓
3. 寫 Integration Test（驗證 API 可用）
   ↓
4. ruff check --fix（自動修復格式）
   ↓
5. Commit（無需 pre-commit hooks）
   ↓
6. Push → CI 跑 Integration Tests
```

**預期時間**：
- 開發功能：70% 時間
- 寫測試：20% 時間
- 修復/重構：10% 時間

---

## 🔧 工具鏈（極簡）

### 必要工具
- **pytest**: Integration tests only
- **ruff**: 格式化 + Linting（自動修復）
- **httpx**: API 測試
- **pre-commit**: Git hooks（自動檢查）

---

## 🧪 測試策略（TDD for Critical Features）

### TDD 核心原則（保留）

**Red-Green-Refactor Cycle**:
```
1. ❌ RED: 先寫測試（必定失敗）
2. ✅ GREEN: 寫最小代碼讓測試通過
3. ♻️ REFACTOR: 重構代碼（測試保持通過）
```

**何時必須用 TDD？**
- ✅ **關鍵功能**：所有 `console.html` 使用的 API（35+ endpoints）
- ✅ **核心業務邏輯**：認證、案主管理、諮商記錄、報告生成
- ✅ **RAG 功能**：文件上傳、嵌入、搜尋、評估

**何時可以跳過 TDD？**
- ⚠️ 實驗性功能（快速驗證 idea）
- ⚠️ 一次性腳本或工具

---

### ✅ 必須做

1. **Integration Tests**（API 端到端測試）
   - **所有 console.html 的 API 都必須有測試**
   - 驗證 API 能正常工作
   - 測試關鍵業務流程
   - 每個 endpoint 至少 1 個 happy path test

2. **TDD 流程（關鍵功能）**
   ```
   1. 定義 API 行為（人類設計）
   2. 寫 Integration Test（先寫測試）
   3. 跑測試 → RED（失敗）
   4. AI 生成實作代碼
   5. 跑測試 → GREEN（通過）
   6. Review + Refactor（人類主導）
   7. Commit
   ```

### ⚠️ 可選做
- Unit Tests（只在邏輯複雜時寫）
- Edge case tests（上線前補）

### ❌ 不做
- 100% 測試覆蓋率
- 過度的 mock
- 過度的類型檢查

**測試命令**：
```bash
# 日常開發：只跑 integration tests
poetry run pytest tests/integration/ -v

# 完整測試（可選）
poetry run pytest tests/ -v

# 檢查特定 API 測試
poetry run pytest tests/integration/test_auth_api.py -v
```

---

## 📦 Git Workflow

### Git Hooks 設置

**首次安裝**:
```bash
# 安裝 pre-commit 和 pre-push hooks
poetry run pre-commit install
poetry run pre-commit install --hook-type pre-push
```

**Commit 時自動檢查**（快速）:
1. ✅ 檢查分支（禁止 commit 到 main/master）
2. ✅ Ruff linting and formatting
3. ✅ 基本文件檢查（trailing whitespace, YAML/TOML）
4. ✅ **資安檢查**（防止 API keys, secrets, private keys 洩露）

**Push 時自動檢查**（關鍵冒煙測試，~10 秒）:
1. ✅ 運行關鍵 Console API 冒煙測試
   - 登入、案主、案例、會談的核心功能
   - 完整測試在 CI 跑（106+ tests）

### Commit 原則
1. **功能可用** → 就可以 commit
2. **代碼格式** → Commit 時自動用 ruff 修復
3. **測試通過** → Push 時自動跑 integration tests

### Commit & Push 流程
```bash
# 1. 檢查分支
git branch --show-current

# 2. Commit（快速檢查）
git add .
git commit -m "feat: add XXX API"
# ↓ Commit 時自動執行（~5 秒）：
#   ✅ 檢查分支
#   ✅ Ruff linting/formatting
#   ✅ 資安檢查
#   ✅ 文件檢查

# 3. Push（冒煙測試）
git push
# ↓ Push 時自動執行（~10 秒）：
#   ✅ 關鍵 Console API 冒煙測試
#   ✅ 確保核心功能正常（完整測試在 CI 跑）
```

### 手動運行 Hooks（可選）
```bash
# 手動運行 commit 檢查
poetry run pre-commit run --all-files

# 手動運行 push 冒煙測試
poetry run pre-commit run --hook-stage push

# 手動運行完整測試（106+ tests）
poetry run pytest tests/integration/ -v

# ❌ 絕對禁止跳過檢查！
# git push --no-verify  # 禁止使用！
```

### Commit Message 格式
- ✅ `feat: add user login API`
- ✅ `fix: correct client code generation`
- ✅ `docs: update API guide`
- ❌ 不要加 Claude 署名

---

## 🚀 CI/CD（簡化版）

### CI Pipeline
1. **Linting**: `ruff check app/`
2. **Integration Tests**: `pytest tests/integration/`
3. **Deploy**: 推到 Cloud Run（staging）

### 成功標準
- ✅ Ruff check 通過
- ✅ Integration tests 通過
- ✅ 部署成功，健康檢查通過

**CI 時間目標**: < 2 分鐘

---

## 📊 品質保證（最小化）

### 必須檢查
1. **API 能 work**（Integration tests）
2. **代碼格式統一**（Ruff）
3. **無明顯 bug**（手動測試 + 自動化測試）

### 不強制
- 類型提示完整性
- 測試覆蓋率百分比
- 代碼複雜度指標

---

## 💡 AI 協作原則（TDD + AI）

### 人類負責
- 需求理解
- API 設計
- **測試先行（TDD）**：人類寫測試，定義預期行為
- Code Review
- 重構決策

### AI 負責
- **生成實作代碼**（通過人類寫的測試）
- 格式修復
- 文檔生成
- 建議重構方案

### TDD + AI 協作流程
```
1. 人：定義需求 + API 設計
2. 人：先寫測試（RED）→ 定義預期行為
3. AI：生成實作讓測試通過（GREEN）
4. 人：Review + 重構（測試保持 GREEN）
```

⚠️ **注意**：AI 不能修改測試，測試是合約

---

## 🤖 Agent-Manager 強制使用規則

**CRITICAL: 所有開發任務必須透過 agent-manager**

```yaml
規則：
  1. 收到任何 coding task → 立即使用 Task(subagent_type="agent-manager", ...)
  2. Agent-manager 會自動路由到適當的 subagent
  3. 詳細規則請參考：.claude/agents/agent-manager.md

例外（可跳過 agent-manager）：
  - 單純讀檔案
  - 回答概念問題
  - 解釋現有程式碼
```

**可用的 Slash Commands：**
- `/tdd` - 完整 TDD 開發流程
- `/test-api` - 快速測試 API
- `/review-pr` - PR 審查
- `/deploy-check` - 部署前檢查

**Agent Model 智慧切換：**
- **Haiku** → test-runner (3x 快，10x 便宜，固定)
- **Sonnet** (預設) → 其他所有 agents
- **Opus** → agent-manager **自動偵測**並切換（複雜任務）

✅ **自動切換機制**：agent-manager 會偵測任務複雜度，自動執行 `/model opus` 升級
觸發條件：critical、production、security、5+ 檔案、架構重構

詳細說明請參考 `.claude/MODEL_STRATEGY.md` 和 `.claude/commands/` 目錄。

---

## 📈 何時升級品質標準？

### Prototype → Production 轉換點
當準備上線時，才需要：
- [ ] 補充 Unit Tests（關鍵邏輯）
- [ ] 啟用 Mypy（類型檢查）
- [ ] 設定 Pre-commit Hooks
- [ ] 提高測試覆蓋率（目標 80%+）
- [ ] 安全掃描（OWASP）
- [ ] 性能測試

**目前階段：Prototype（不需要以上項目）**

---

## 🔒 不可妥協的規則

**CRITICAL: These rules are ABSOLUTE and CANNOT be violated**

1. **❌ YOU MUST NOT commit 到 main/master**
   - IMPORTANT: 永遠在 staging/feature branch 開發
   - VIOLATION CONSEQUENCE: 破壞 production 環境

2. **❌ ABSOLUTELY FORBIDDEN: `--no-verify`**
   - ❌ `git commit --no-verify` - **禁止使用**
   - ❌ `git push --no-verify` - **禁止使用**
   - CRITICAL: 如果 hooks 失敗，修復問題，不要跳過檢查
   - NEVER bypass security checks

3. **✅ MANDATORY: Integration tests 必須通過**
   - IMPORTANT: API 不能壞掉
   - **YOU MUST ensure 所有 console.html 使用的 API 都有測試**
   - ZERO tolerance for broken APIs

4. **✅ REQUIRED: 代碼要能跑**
   - MINIMUM: 至少手動測試過
   - NEVER commit non-functional code

5. **❌ YOU MUST NOT 繞過 CI**
   - CRITICAL: 雖然簡化，但 CI 必須跑
   - CI failures MUST be fixed, not ignored

6. **✅ MANDATORY: TDD 用於關鍵功能**
   - IMPORTANT: 關鍵 API 必須先寫測試
   - **測試定義行為，AI 實作代碼**
   - NEVER implement without tests first

7. **🤖 Agent-Manager 強制使用**
   - 所有開發任務必須透過 agent-manager
   - 保護主要 context 不被消耗
   - 確保 TDD 流程一致性

---

## 🎯 Console API 測試檢查清單

**驗證所有 console.html 的 API 都有測試**:

```bash
# 檢查測試覆蓋率
poetry run pytest tests/integration/ -v | grep -E "(test_.*_api\.py|PASSED|FAILED)"

# 當前狀態（2025-11-24）
# ✅ 106 integration tests 覆蓋 35+ endpoints
# ✅ 所有主要功能都有測試：
#    - 認證 API (test_auth_api.py)
#    - 案主管理 (test_clients_api.py)
#    - 諮商記錄 (test_sessions_api.py)
#    - 案例管理 (test_cases_api.py)
#    - 報告生成 (test_reports_api.py)
#    - RAG 功能 (test_rag_*.py)
```

**新增 API 時的 TDD 流程**:
1. 在 console.html 添加新功能前
2. 先在 `tests/integration/` 寫測試
3. 跑測試確認 RED（失敗）
4. 實作 API endpoint
5. 跑測試確認 GREEN（通過）
6. 更新 console.html 使用新 API

---

## 參考資料

- **2025 AI Development**: "Dream up an idea one day, functional prototype the next"
- **Speed-Quality Trade-off**: Prototypes live in "buggy region" - speed優先
- **70-20-10 Rule**: 70% 開發, 20% QA, 10% 重構

---

**Remember: Prototype 求快不求完美。功能驗證完才追求品質。**

**版本**: v2.0 (Prototype-First)
**最後更新**: 2025-11-24
