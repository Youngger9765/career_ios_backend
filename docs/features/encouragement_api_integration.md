# Quick Feedback API 整合指南（方案 B: AI-Powered）

**版本**: v2.0
**最後更新**: 2026-01-01
**狀態**: ✅ 已整合到 `/api/v1/realtime/quick-feedback`

---

## 📋 設計原則

### 核心理念

**Quick Feedback 是「補充」而非「取代」**：
- 主要分析：`/api/v1/realtime/analyze`（完整 AI 分析，8 大派 + 200 句專家建議）
- 快速鼓勵：`/api/v1/realtime/quick-feedback`（輕量 AI 雞湯文，填補空檔）

### 動態協調策略

**Quick-feedback 統一 10 秒輪詢，不隨燈號改變**：

| 燈號 | realtime/analyze | quick-feedback | 策略 |
|------|------------------|----------------|------|
| 🟢 綠燈 | 60 秒 | 10 秒 | ✅ 每分鐘 6 次快速鼓勵 |
| 🟡 黃燈 | 30 秒 | 10 秒 | ✅ 每 30 秒 3 次快速鼓勵 |
| 🔴 紅燈 | 15 秒 | **停用** | ❌ 不要 quick-feedback（已經夠快）|

**重要**：Quick-feedback 固定每 10 秒觸發，提供即時鼓勵。紅燈時停用，因為 15 秒分析已經足夠快。

---

## 🚀 API 規格

### Endpoint

```
POST /api/v1/realtime/quick-feedback
```

### Request

```json
{
  "recent_transcript": "家長：你再這樣我就生氣了！\n孩子：我不是故意的..."
}
```

### Response

```json
{
  "message": "深呼吸，保持冷靜",
  "type": "ai_generated",
  "timestamp": "2026-01-01T10:00:00Z",
  "latency_ms": 1200
}
```

### Response Fields

- `message` (string): AI 生成的鼓勵訊息（≤ 20 字）
- `type` (string): 訊息類型
  - `ai_generated` - AI 成功生成
  - `fallback` - AI 失敗，使用預設訊息
  - `fallback_error` - 發生錯誤，使用預設訊息
- `timestamp` (string): 生成時間（ISO 8601）
- `latency_ms` (int): 延遲時間（毫秒）

---

## 📱 iOS 客戶端整合

### Swift 實作範例

```swift
class ParentingPracticeViewController: UIViewController {

    // MARK: - Properties
    private var quickFeedbackTimer: Timer?
    private var realtimeAnalyzeTimer: Timer?
    private var currentSafetyLevel: SafetyLevel = .green

    enum SafetyLevel: String {
        case green = "green"   // 綠燈：安全
        case yellow = "yellow" // 黃燈：警示
        case red = "red"       // 紅燈：高風險
    }

    // MARK: - Lifecycle
    override func viewDidLoad() {
        super.viewDidLoad()
        startDynamicPolling()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        stopAllPolling()
    }

    // MARK: - Dynamic Polling Control

    /// 根據燈號啟動動態輪詢
    private func startDynamicPolling() {
        // 初始假設為綠燈
        updatePollingIntervals(safetyLevel: .green)
    }

    /// 更新輪詢間隔（當燈號改變時）
    private func updatePollingIntervals(safetyLevel: SafetyLevel) {
        // 停止舊的 timer
        stopAllPolling()

        // 記錄當前燈號
        currentSafetyLevel = safetyLevel

        // 根據燈號設定新的間隔
        switch safetyLevel {
        case .green:
            // 🟢 綠燈：analyze 60秒 + quick-feedback 10秒
            startRealtimeAnalyze(interval: 60.0)
            startQuickFeedback(interval: 10.0)

        case .yellow:
            // 🟡 黃燈：analyze 30秒 + quick-feedback 10秒
            startRealtimeAnalyze(interval: 30.0)
            startQuickFeedback(interval: 10.0)

        case .red:
            // 🔴 紅燈：只用 analyze 15秒，停用 quick-feedback
            startRealtimeAnalyze(interval: 15.0)
            // 不啟動 quick-feedback
        }

        print("⏱️ Polling updated: safety=\(safetyLevel.rawValue), analyze=\(getAnalyzeInterval())s, quick=\(getQuickFeedbackInterval())s")
    }

    private func startRealtimeAnalyze(interval: TimeInterval) {
        realtimeAnalyzeTimer = Timer.scheduledTimer(
            withTimeInterval: interval,
            repeats: true
        ) { [weak self] _ in
            self?.callRealtimeAnalyze()
        }

        // 立即執行一次
        callRealtimeAnalyze()
    }

    private func startQuickFeedback(interval: TimeInterval) {
        quickFeedbackTimer = Timer.scheduledTimer(
            withTimeInterval: interval,
            repeats: true
        ) { [weak self] _ in
            self?.callQuickFeedback()
        }
    }

    private func stopAllPolling() {
        realtimeAnalyzeTimer?.invalidate()
        realtimeAnalyzeTimer = nil

        quickFeedbackTimer?.invalidate()
        quickFeedbackTimer = nil
    }

    // MARK: - API Calls

    private func callRealtimeAnalyze() {
        let transcript = getFullTranscript() // 完整 60 秒逐字稿

        APIClient.shared.realtimeAnalyze(transcript: transcript) { [weak self] result in
            switch result {
            case .success(let analysis):
                // 1. 更新燈號（可能觸發 polling 間隔變化）
                if analysis.safetyLevel != self?.currentSafetyLevel.rawValue {
                    let newLevel = SafetyLevel(rawValue: analysis.safetyLevel) ?? .green
                    self?.updatePollingIntervals(safetyLevel: newLevel)
                }

                // 2. 顯示完整分析
                self?.displayFullAnalysis(analysis)

            case .failure(let error):
                print("❌ Realtime analyze error: \(error)")
            }
        }
    }

    private func callQuickFeedback() {
        // 只在非紅燈時呼叫（紅燈已停用 timer）
        guard currentSafetyLevel != .red else { return }

        let recentTranscript = getRecentTranscript(seconds: 10) // 最近 10 秒

        APIClient.shared.quickFeedback(recentTranscript: recentTranscript) { [weak self] result in
            switch result {
            case .success(let feedback):
                self?.displayQuickFeedback(feedback)

            case .failure(let error):
                print("❌ Quick feedback error: \(error)")
            }
        }
    }

    // MARK: - Display

    private func displayFullAnalysis(_ analysis: RealtimeAnalysis) {
        // 完整分析：大卡片，停留較久
        let card = AnalysisCardView()
        card.configure(
            safetyLevel: analysis.safetyLevel,
            summary: analysis.summary,
            suggestions: analysis.suggestions,
            displayDuration: 8.0 // 停留 8 秒
        )
        card.show(in: self.view)
    }

    private func displayQuickFeedback(_ feedback: QuickFeedback) {
        // 快速鼓勵：小浮動提示，停留較短
        let toast = ToastView()
        toast.configure(
            message: feedback.message,
            displayDuration: 3.0 // 停留 3 秒
        )
        toast.show(in: self.view)
    }

    // MARK: - Helpers

    private func getAnalyzeInterval() -> TimeInterval {
        switch currentSafetyLevel {
        case .green: return 60.0
        case .yellow: return 30.0
        case .red: return 15.0
        }
    }

    private func getQuickFeedbackInterval() -> TimeInterval? {
        switch currentSafetyLevel {
        case .green: return 10.0
        case .yellow: return 10.0
        case .red: return nil // 停用
        }
    }
}

// MARK: - API Client Extension

extension APIClient {
    func quickFeedback(
        recentTranscript: String,
        completion: @escaping (Result<QuickFeedback, Error>) -> Void
    ) {
        let endpoint = "/api/v1/realtime/quick-feedback"
        let body: [String: Any] = ["recent_transcript": recentTranscript]

        request(endpoint: endpoint, method: .post, body: body) { result in
            switch result {
            case .success(let data):
                do {
                    let feedback = try JSONDecoder().decode(QuickFeedback.self, from: data)
                    completion(.success(feedback))
                } catch {
                    completion(.failure(error))
                }
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}

// MARK: - Models

struct QuickFeedback: Codable {
    let message: String
    let type: String
    let timestamp: String
    let latencyMs: Int

    enum CodingKeys: String, CodingKey {
        case message, type, timestamp
        case latencyMs = "latency_ms"
    }
}
```

---

## 🎨 UI/UX 建議

### 視覺層次

```
完整 AI 分析（優先，高視覺權重）
├─ 卡片形式，佔螢幕 30-40%
├─ 大字體（18-20pt）
├─ 根據燈號變色（綠/黃/紅）
├─ 顯示完整建議（200 句專家建議）
└─ 停留 6-8 秒

快速鼓勵（次要，低視覺權重）
├─ Toast/浮動提示
├─ 中字體（14-16pt）
├─ 柔和顏色
├─ 一句話（≤ 20 字）
└─ 停留 3 秒後淡出
```

### 位置建議

| 元素 | 位置 | 原因 |
|------|------|------|
| 完整分析卡片 | 螢幕上半部 | 重要資訊，需要注意 |
| 快速鼓勵 Toast | 螢幕底部 | 輕量提示，不干擾主要內容 |
| 燈號指示器 | 右上角 | 持續可見，快速判斷狀態 |

---

## ⚠️ 重要注意事項

### 1. 紅燈時停用 Quick Feedback

```swift
// ❌ 錯誤：紅燈還繼續輪詢
if currentSafetyLevel == .red {
    startQuickFeedback(interval: 10.0) // 不要這樣做！
}

// ✅ 正確：紅燈時停用
if currentSafetyLevel == .red {
    // 只用 realtime/analyze (15秒)，不需要 quick-feedback
    quickFeedbackTimer?.invalidate()
}
```

### 2. 燈號變化時即時調整

```swift
// API 返回新的 safety_level 時
if newSafetyLevel != currentSafetyLevel {
    print("🚦 Safety level changed: \(currentSafetyLevel) → \(newSafetyLevel)")
    updatePollingIntervals(safetyLevel: newSafetyLevel)
}
```

### 3. 錯開時間避免衝突

```swift
// ✅ 好的做法：quick-feedback 在 analyze 中間
// 綠燈範例：
// 0s  → realtime/analyze
// 30s → quick-feedback
// 60s → realtime/analyze
// 90s → quick-feedback

// ❌ 壞的做法：兩個 API 同時觸發
// 0s → realtime/analyze + quick-feedback（用戶困惑）
```

---

## 📊 效能指標

### 預期延遲

| API | 預期延遲 | 備註 |
|-----|---------|------|
| quick-feedback | 1-2 秒 | Gemini Flash，輕量 prompt |
| realtime/analyze | 5-10 秒 | 完整分析 + RAG 檢索 |

### 監控項目

1. **quick-feedback 延遲** - 應 < 2 秒
2. **API 成功率** - 應 > 98%
3. **紅燈時 quick-feedback 呼叫次數** - 應為 0（已停用）
4. **用戶滿意度** - 透過 feedback button 收集

---

## 🧪 測試檢查清單

### Backend 測試
- [ ] `/api/v1/realtime/quick-feedback` 正常運作
- [ ] 延遲 < 2 秒
- [ ] 錯誤時返回 fallback 訊息
- [ ] 訊息長度 ≤ 20 字

### iOS 測試
- [ ] 綠燈：analyze 60秒 + quick 10秒
- [ ] 黃燈：analyze 30秒 + quick 10秒
- [ ] 紅燈：只有 analyze 15秒，quick 停用
- [ ] Quick-feedback 固定 10 秒間隔（不隨燈號改變）
- [ ] 離開頁面時停止所有 polling

### 整合測試
- [ ] 紅燈時不會看到 quick-feedback
- [ ] 兩個 API 不會同時觸發
- [ ] UI 層次清晰（分析 > 鼓勵）
- [ ] 網路失敗時優雅降級

---

## 🔮 未來優化

### 短期（2 週內）
- [ ] 收集用戶回饋（「這個建議有幫助嗎？」）
- [ ] A/B 測試：有 vs 無 quick-feedback 的用戶滿意度
- [ ] 優化 prompt 提升訊息品質

### 中期（1 個月）
- [ ] 根據用戶偏好個人化訊息
- [ ] 分析哪些情境最需要 quick-feedback
- [ ] 探索更輕量的 AI 模型（降低延遲）

### 長期（3 個月）
- [ ] 機器學習：預測何時最需要鼓勵
- [ ] 多語言支援
- [ ] 與 Apple Watch 整合（haptic feedback）

---

**文件版本**: v2.0（AI-Powered with Dynamic Intervals）
**最後更新**: 2026-01-01
**對應 API**: `/api/v1/realtime/quick-feedback`
