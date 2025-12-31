/**
 * Integration Example for realtime_counseling.html
 * 展示如何整合 Session Workflow 到現有的即時諮詢頁面
 *
 * @version 1.0.0
 * @created 2025-01-01
 */

// ============================================================
// 使用方式：在 realtime_counseling.html 中加入以下代碼
// ============================================================

/*
<!-- Add before </body> in realtime_counseling.html -->
<script type="module">
    import { SessionWorkflow } from '/static/js/session-workflow.js';

    // Initialize workflow
    const sessionWorkflow = new SessionWorkflow();
    let isSessionInitialized = false;

    // ========== Step 1: 修改孩子資料設定表單 ==========
    document.getElementById('clientSetupForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const childNickname = document.getElementById('childNickname').value;
        const childGrade = document.getElementById('childGrade').value;
        const parentRelation = document.getElementById('parentRelation').value;

        try {
            // Show loading state
            document.getElementById('setupButton').disabled = true;
            document.getElementById('setupButton').textContent = '設定中...';

            // Use new workflow (creates client + case + session)
            await sessionWorkflow.initializeSession({
                name: childNickname,
                email: `${childNickname.toLowerCase().replace(/\s/g, '')}@example.com`,
                gender: '不透露',
                birth_date: '2015-01-01',
                phone: '0900000000',
                identity_option: '其他',
                current_status: '進行中',
                case_summary: `${childNickname} 的親子諮詢`,
                case_goals: '改善親子溝通',
                problem_description: `家長關係：${parentRelation}，孩子年級：${childGrade}`
            });

            isSessionInitialized = true;
            alert(`${childNickname} 設定完成！已創建會談 Session`);

            // Update UI to enable analysis
            document.getElementById('analyzeButton').disabled = false;

        } catch (error) {
            console.error('Setup error:', error);
            alert(`設定失敗: ${error.message}\n\n請確認您已登入並有權限操作。`);
        } finally {
            // Reset button state
            document.getElementById('setupButton').disabled = false;
            document.getElementById('setupButton').textContent = '完成設定';
        }
    });

    // ========== Step 2: 修改即時分析功能 ==========
    async function performRealtimeAnalysis() {
        if (!isSessionInitialized) {
            alert('請先完成孩子資料設定');
            return;
        }

        try {
            // Get transcript from existing UI
            const transcript = getCurrentTranscript(); // Your existing function
            const mode = getCurrentMode(); // Your existing function (practice/emergency)

            // Show loading state
            showAnalysisLoading(); // Your existing function

            // Use new workflow
            const analysis = await sessionWorkflow.performAnalysis(transcript, mode);

            // Display using existing UI function
            displayAnalysisCard(analysis); // Your existing function

            // Update session metadata in UI (optional)
            const metadata = sessionWorkflow.getSessionMetadata();
            console.log('[Session Metadata]', metadata);

        } catch (error) {
            console.error('Analysis error:', error);
            alert(`分析失敗: ${error.message}`);
            hideAnalysisLoading(); // Your existing function
        }
    }

    // Make function global for existing code
    window.performRealtimeAnalysis = performRealtimeAnalysis;

    // ========== Step 3: 結束會談時清理 Session ==========
    document.getElementById('endSessionButton')?.addEventListener('click', () => {
        if (confirm('確定要結束此次會談嗎？')) {
            sessionWorkflow.endSession();
            isSessionInitialized = false;
            alert('會談已結束');

            // Reset UI state
            document.getElementById('analyzeButton').disabled = true;
        }
    });
</script>
*/

// ============================================================
// 向後兼容的 Feature Flag 實現
// ============================================================

/*
如果需要保留舊的 Realtime API 作為 fallback：

<script type="module">
    import { SessionWorkflow } from '/static/js/session-workflow.js';

    // Feature flag (可從 localStorage 讀取)
    const USE_SESSION_WORKFLOW = localStorage.getItem('useSessionWorkflow') === 'true' || true;

    let sessionWorkflow = null;
    let isSessionInitialized = false;

    if (USE_SESSION_WORKFLOW) {
        sessionWorkflow = new SessionWorkflow();
    }

    async function performRealtimeAnalysis() {
        const transcript = getCurrentTranscript();
        const mode = getCurrentMode();

        if (USE_SESSION_WORKFLOW && isSessionInitialized) {
            // New workflow
            try {
                const analysis = await sessionWorkflow.performAnalysis(transcript, mode);
                displayAnalysisCard(analysis);
            } catch (error) {
                console.error('[Session Workflow] Failed, falling back to Realtime API', error);
                // Fallback to old API
                await performRealtimeAnalysisOld(transcript, mode);
            }
        } else {
            // Old workflow (直接調用 Realtime API)
            await performRealtimeAnalysisOld(transcript, mode);
        }
    }

    // Old implementation (kept for backward compatibility)
    async function performRealtimeAnalysisOld(transcript, mode) {
        const response = await fetch('/api/v1/island-parents/realtime-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('authToken')}`
            },
            body: JSON.stringify({ transcript, mode })
        });
        const analysis = await response.json();
        displayAnalysisCard(analysis);
    }

    window.performRealtimeAnalysis = performRealtimeAnalysis;
</script>
*/

// ============================================================
// 輔助函數範例
// ============================================================

/**
 * Example: Get current transcript from UI
 * 你需要根據實際的 UI 結構調整
 */
function getCurrentTranscript() {
    // Example: Get from textarea or contenteditable div
    const transcriptElement = document.getElementById('transcriptInput');
    return transcriptElement ? transcriptElement.value : '';
}

/**
 * Example: Get current analysis mode
 */
function getCurrentMode() {
    // Example: Get from radio buttons or select
    const modeSelect = document.getElementById('modeSelect');
    return modeSelect ? modeSelect.value : 'practice';
}

/**
 * Example: Display analysis result in UI
 * 這個函數應該已經存在於 realtime_counseling.html
 */
function displayAnalysisCard(analysis) {
    // Example implementation:
    const cardHTML = `
        <div class="analysis-card ${analysis.safety_level}">
            <h3>${analysis.safety_level === 'red' ? '⚠️ 注意' : analysis.safety_level === 'yellow' ? '⚡ 提醒' : '✅ 良好'}</h3>
            <p><strong>分析結果：</strong>${analysis.summary}</p>
            ${analysis.alerts.length > 0 ? `<p class="alert"><strong>建議：</strong>${analysis.alerts.join(', ')}</p>` : ''}
            ${analysis.suggestions.length > 0 ? `
                <div class="suggestions">
                    <strong>快速回應建議：</strong>
                    <ul>
                        ${analysis.suggestions.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            <p class="timestamp">時間：${new Date(analysis.timestamp).toLocaleString('zh-TW')}</p>
        </div>
    `;

    document.getElementById('analysisResults').innerHTML = cardHTML;
}

/**
 * Example: Show loading state
 */
function showAnalysisLoading() {
    document.getElementById('analyzeButton').disabled = true;
    document.getElementById('analyzeButton').textContent = '分析中...';
    document.getElementById('analysisResults').innerHTML = '<div class="loading">分析中，請稍候...</div>';
}

/**
 * Example: Hide loading state
 */
function hideAnalysisLoading() {
    document.getElementById('analyzeButton').disabled = false;
    document.getElementById('analyzeButton').textContent = '即時分析';
}

// Export for reference (not actually used in HTML)
export {
    getCurrentTranscript,
    getCurrentMode,
    displayAnalysisCard,
    showAnalysisLoading,
    hideAnalysisLoading
};
