/**
 * Island Parents Testing Steps
 * 親子版測試流程 JavaScript handlers
 *
 * @version 1.0.0
 * @created 2026-01-03
 */

// Add Island Parents testing steps to existing steps object
(() => {
    // Get reference to BASE_URL and state from console-steps.js
    const BASE_URL = window.BASE_URL || 'http://localhost:8000';
    let state = window.consoleState || {};

    // Island Parents test data
    const islandTestData = {
        // Stored from previous steps
        sessionId: null,
        caseId: null,
        clientId: null,

        // Sample transcript segments for testing
        transcriptSegments: [
            { time: "0-10秒", text: "現在是寫作業的時間囉。\n我不想寫，我還想玩。" },
            { time: "10-20秒", text: "我就是不要寫！為什麼一定要現在寫？\n因為晚一點就沒時間了，你明天要早起上學。" },
            { time: "20-30秒", text: "你怎麼這麼不聽話！我說幾次了？\n我就是不想寫！你都不聽我說話！" },
            { time: "30-40秒", text: "你哭什麼哭！哭也沒用！作業還是要寫！\n你都不愛我了！你只會兇我！" }
        ],

        currentSegmentIndex: 0
    };

    // Make test data accessible globally
    window.islandTestData = islandTestData;

    // Define Island Parents testing steps
    const islandSteps = {
        'island-login': {
            title: '🔑 登入 Island Parents',
            subtitle: 'POST /api/auth/login',
            renderForm: () => `
                <div class="form-group">
                    <label>Tenant ID</label>
                    <input type="text" id="island-tenant" value="island_parents" readonly />
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="island-email" value="counselor@island-parents.com" />
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="island-password" value="12345678" />
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandLogin()">登入</button>
            `,
            execute: async () => {
                const tenant_id = document.getElementById('island-tenant').value;
                const email = document.getElementById('island-email').value;
                const password = document.getElementById('island-password').value;

                const response = await fetch(`${BASE_URL}/api/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tenant_id, email, password })
                });

                const data = await response.json();
                if (response.ok) {
                    state.token = data.access_token;
                    localStorage.setItem('token', state.token);
                    localStorage.setItem('tenant_id', tenant_id);
                }
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>🔐 Island Parents 登入成功</h3>
                    <div class="info-row">
                        <span class="info-label">Token</span>
                        <span class="info-value" style="font-size: 11px; word-break: break-all;">${data.access_token.substring(0, 60)}...</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Expires In</span>
                        <span class="info-value">${data.expires_in}秒</span>
                    </div>
                </div>
            `
        },

        'island-select-client': {
            title: '👶 選擇既有孩子',
            subtitle: 'GET /api/v1/clients → GET /api/v1/cases',
            renderForm: () => {
                // Auto-load clients when form renders
                setTimeout(() => window.loadIslandClients(), 100);
                return `
                <div class="info-card" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                    <p style="margin: 0; font-size: 13px; color: #78350f;">
                        💡 選擇已建立的孩子，不需要每次都新增
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>選擇孩子</label>
                    <select id="island-existing-client" onchange="window.loadClientCases(this.value)">
                        <option value="">載入中...</option>
                    </select>
                </div>
                <div class="form-group" style="margin-top: 12px;">
                    <label>選擇案件</label>
                    <select id="island-existing-case">
                        <option value="">-- 請先選擇孩子 --</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandSelectClient()" style="margin-top: 16px;" id="island-select-btn" disabled>選擇此孩子</button>
            `;
            },
            execute: async () => {
                const clientSelect = document.getElementById('island-existing-client');
                const caseSelect = document.getElementById('island-existing-case');

                const clientId = clientSelect.value;
                const caseId = caseSelect.value;

                if (!clientId || !caseId) {
                    throw new Error('請先選擇孩子和案件');
                }

                // Store selected client and case
                islandTestData.clientId = clientId;
                islandTestData.caseId = caseId;

                // Get selected names for display
                const clientName = clientSelect.options[clientSelect.selectedIndex].text;
                const caseName = caseSelect.options[caseSelect.selectedIndex].text;

                return {
                    response: { ok: true, status: 200 },
                    data: {
                        client_id: clientId,
                        case_id: caseId,
                        client_name: clientName,
                        case_name: caseName
                    }
                };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 已選擇孩子</h3>
                    <div class="info-row">
                        <span class="info-label">孩子</span>
                        <span class="info-value">${data.client_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">案件</span>
                        <span class="info-value">${data.case_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Client ID</span>
                        <span class="info-value" style="font-size: 11px;">${data.client_id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Case ID</span>
                        <span class="info-value" style="font-size: 11px;">${data.case_id}</span>
                    </div>
                </div>
            `
        },

        'island-create-client-case': {
            title: '📝 建立親子客戶+案件',
            subtitle: 'POST /api/v1/ui/client-case',
            renderForm: () => `
                <div class="form-group">
                    <label>孩子姓名</label>
                    <input type="text" id="island-child-name" value="小明" />
                </div>
                <div class="form-group">
                    <label>孩子年級</label>
                    <select id="island-child-grade">
                        <option value="幼兒園">幼兒園</option>
                        <option value="小學1年級">小學1年級</option>
                        <option value="小學2年級">小學2年級</option>
                        <option value="小學3年級" selected>小學3年級</option>
                        <option value="小學4年級">小學4年級</option>
                        <option value="小學5年級">小學5年級</option>
                        <option value="小學6年級">小學6年級</option>
                        <option value="國中1年級">國中1年級</option>
                        <option value="國中2年級">國中2年級</option>
                        <option value="國中3年級">國中3年級</option>
                        <option value="高中1年級">高中1年級</option>
                        <option value="高中2年級">高中2年級</option>
                        <option value="高中3年級">高中3年級</option>
                        <option value="其他">其他</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>關係（你是孩子的）</label>
                    <select id="island-parent-relation">
                        <option value="爸爸" selected>爸爸</option>
                        <option value="媽媽">媽媽</option>
                        <option value="爺爺">爺爺</option>
                        <option value="奶奶">奶奶</option>
                        <option value="外公">外公</option>
                        <option value="外婆">外婆</option>
                        <option value="其他">其他</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>案件摘要 <span style="color:#888;font-size:12px">(選填)</span></label>
                    <textarea id="island-case-summary" rows="2" placeholder="可留空，系統會自動產生"></textarea>
                </div>
                <div class="form-group">
                    <label>案件目標 <span style="color:#888;font-size:12px">(選填)</span></label>
                    <input type="text" id="island-case-goals" placeholder="可留空" />
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandCreateClientCase()">建立客戶+案件</button>
            `,
            execute: async () => {
                const name = document.getElementById('island-child-name').value;
                const grade = document.getElementById('island-child-grade').value;
                const relationship = document.getElementById('island-parent-relation').value;
                const summary = document.getElementById('island-case-summary').value;
                const goals = document.getElementById('island-case-goals').value;

                // Estimate age from grade for birth_date calculation
                const gradeToAge = {
                    '幼兒園': 5,
                    '小學1年級': 7,
                    '小學2年級': 8,
                    '小學3年級': 9,
                    '小學4年級': 10,
                    '小學5年級': 11,
                    '小學6年級': 12,
                    '國中1年級': 13,
                    '國中2年級': 14,
                    '國中3年級': 15,
                    '高中1年級': 16,
                    '高中2年級': 17,
                    '高中3年級': 18,
                    '其他': 10
                };
                const estimatedAge = gradeToAge[grade] || 10;

                const response = await fetch(`${BASE_URL}/api/v1/ui/client-case`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify({
                        name: name,
                        // email 選填，親子版不需要
                        gender: '不透露',
                        birth_date: `${new Date().getFullYear() - estimatedAge}-01-01`,
                        phone: '0000000000',
                        identity_option: '孩子',
                        current_status: `年級: ${grade}`,
                        notes: `關係: ${relationship}`,
                        case_summary: summary || `親子溝通練習 - ${new Date().toLocaleString('zh-TW')}`,
                        case_goals: goals || '改善親子關係',
                        problem_description: '親子溝通練習'
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    islandTestData.clientId = data.client_id;
                    islandTestData.caseId = data.case_id;
                }
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 客戶+案件建立成功</h3>
                    <div class="info-row">
                        <span class="info-label">Client ID</span>
                        <span class="info-value">${data.client_id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Case ID</span>
                        <span class="info-value">${data.case_id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Client Name</span>
                        <span class="info-value">${data.client_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Case Summary</span>
                        <span class="info-value">${data.case_summary}</span>
                    </div>
                </div>
            `
        },

        'island-create-session': {
            title: '📋 建立會談',
            subtitle: 'POST /api/v1/sessions',
            renderForm: () => `
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Case ID:</strong> ${islandTestData.caseId || '請先建立客戶+案件'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>會談名稱 <span style="color:#888;font-size:12px">(選填，留空自動產生)</span></label>
                    <input type="text" id="island-session-name" placeholder="諮詢 - 自動產生日期時間" />
                </div>
                <div class="info-card" style="margin-top: 12px; background: #f0fdf4; border-left: 4px solid #22c55e;">
                    <p style="margin: 0; font-size: 12px; color: #166534;">
                        💡 <strong>簡化版</strong>：只需 case_id，其他欄位自動填入
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandCreateSession()" ${!islandTestData.caseId ? 'disabled' : ''} style="margin-top: 16px;">建立會談</button>
            `,
            execute: async () => {
                if (!islandTestData.caseId) {
                    throw new Error('請先建立客戶+案件');
                }

                const sessionName = document.getElementById('island-session-name').value.trim();

                // Send case_id and optional name - session_date, start_time auto-filled by backend
                const requestBody = { case_id: islandTestData.caseId };
                if (sessionName) {
                    requestBody.name = sessionName;
                }

                const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify(requestBody)
                });

                const data = await response.json();
                if (response.ok) {
                    islandTestData.sessionId = data.id;
                }
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 會談建立成功</h3>
                    <div class="info-row">
                        <span class="info-label">Session ID</span>
                        <span class="info-value">${data.id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Session Name</span>
                        <span class="info-value">${data.name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Session Date</span>
                        <span class="info-value">${data.session_date}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Status</span>
                        <span class="info-value">${data.status}</span>
                    </div>
                </div>
            `
        },

        'island-set-scenario': {
            title: '🎯 設定練習情境',
            subtitle: 'PATCH /api/v1/sessions/{id}',
            renderForm: () => `
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先建立會談'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>練習情境</label>
                    <select id="island-practice-scenario">
                        <option value="親子溝通">親子溝通</option>
                        <option value="情緒管理">情緒管理</option>
                        <option value="學業討論">學業討論</option>
                        <option value="行為規範">行為規範</option>
                        <option value="手足關係">手足關係</option>
                        <option value="其他">其他</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>補充說明（選填）</label>
                    <textarea id="island-scenario-notes" rows="2" placeholder="可補充練習情境的細節..."></textarea>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandSetScenario()" ${!islandTestData.sessionId ? 'disabled' : ''}>設定情境</button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談');
                }

                const scenario = document.getElementById('island-practice-scenario').value;
                const notes = document.getElementById('island-scenario-notes').value;

                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify({
                        scenario: scenario,
                        scenario_description: notes || null
                    })
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 練習情境已設定</h3>
                    <div class="info-row">
                        <span class="info-label">練習情境</span>
                        <span class="info-value">${data.scenario || '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">情境描述</span>
                        <span class="info-value">${data.scenario_description || '無'}</span>
                    </div>
                </div>
            `
        },

        'island-append-recording': {
            title: '🎙️ Append 錄音片段',
            subtitle: 'POST /api/v1/sessions/{id}/recordings/append',
            renderForm: () => {
                const currentSegment = islandTestData.transcriptSegments[islandTestData.currentSegmentIndex] || {};
                return `
                    <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                        <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                            <strong>Session ID:</strong> ${islandTestData.sessionId || '請先建立會談'}
                        </p>
                    </div>
                    <div class="form-group" style="margin-top: 16px;">
                        <label>片段編號 (${islandTestData.currentSegmentIndex + 1}/${islandTestData.transcriptSegments.length})</label>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn" onclick="window.islandTestData.currentSegmentIndex = Math.max(0, window.islandTestData.currentSegmentIndex - 1); window.executeStep('island-append-recording')" ${islandTestData.currentSegmentIndex === 0 ? 'disabled' : ''}>◀ 上一段</button>
                            <button class="btn" onclick="window.islandTestData.currentSegmentIndex = Math.min(${islandTestData.transcriptSegments.length - 1}, window.islandTestData.currentSegmentIndex + 1); window.executeStep('island-append-recording')" ${islandTestData.currentSegmentIndex === islandTestData.transcriptSegments.length - 1 ? 'disabled' : ''}>下一段 ▶</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>時間範圍</label>
                        <input type="text" id="island-time-range" value="${currentSegment.time || ''}" readonly />
                    </div>
                    <div class="form-group">
                        <label>逐字稿內容</label>
                        <textarea id="island-transcript" rows="5">${currentSegment.text || ''}</textarea>
                    </div>
                    <button class="btn btn-primary" onclick="window.executeIslandAppendRecording()" ${!islandTestData.sessionId ? 'disabled' : ''}>Append 錄音片段</button>
                `;
            },
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談');
                }

                const transcript = document.getElementById('island-transcript').value;
                const timeRange = document.getElementById('island-time-range').value;

                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}/recordings/append`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify({
                        transcript_text: transcript,
                        start_time: timeRange.split('-')[0] || '0秒',
                        end_time: timeRange.split('-')[1] || '10秒',
                        speaker_labels: []
                    })
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 錄音片段已添加</h3>
                    <div class="info-row">
                        <span class="info-label">Segment Number</span>
                        <span class="info-value">${data.segment_number}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Total Segments</span>
                        <span class="info-value">${data.total_segments}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Transcript Length</span>
                        <span class="info-value">${data.transcript_text?.length || 0} 字元</span>
                    </div>
                    <div class="alert alert-info" style="margin-top: 12px;">
                        💡 可以繼續添加下一段，或進行即時分析
                    </div>
                </div>
            `
        },

        'island-quick-feedback': {
            title: '💡 Quick Feedback',
            subtitle: 'POST /api/v1/realtime/quick-feedback',
            renderForm: () => `
                <div class="info-card" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                    <p style="margin: 0; font-size: 13px; color: #78350f;">
                        <strong>💡 Quick Feedback</strong>: 輕量級快速反饋（~8秒），使用最近的逐字稿
                    </p>
                </div>
                <div class="info-card" style="margin-top: 12px; background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先建立會談並添加錄音'}
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandQuickFeedback()" ${!islandTestData.sessionId ? 'disabled' : ''} style="margin-top: 16px;">執行 Quick Feedback</button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談並添加錄音');
                }

                // Get recent transcript from session
                const sessionResponse = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });
                const sessionData = await sessionResponse.json();
                const recentTranscript = sessionData.transcript_text || '';

                const response = await fetch(`${BASE_URL}/api/v1/realtime/quick-feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        recent_transcript: recentTranscript
                    })
                });

                const data = await response.json();

                // Store analysis result for verification step
                islandTestData.lastAnalysis = data;
                islandTestData.lastAnalysisType = 'quick';

                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 💡 Quick Feedback 完成</h3>
                    <div class="info-row">
                        <span class="info-label">分析類型</span>
                        <span class="info-value">Quick Feedback (快速反饋)</span>
                    </div>
                    ${data.message ? `
                        <div class="info-row">
                            <span class="info-label">Message</span>
                            <span class="info-value">${data.message}</span>
                        </div>
                    ` : ''}
                    ${data.type ? `
                        <div class="info-row">
                            <span class="info-label">Type</span>
                            <span class="info-value">${data.type}</span>
                        </div>
                    ` : ''}
                    ${data.latency_ms ? `
                        <div class="info-row">
                            <span class="info-label">Latency</span>
                            <span class="info-value">${data.latency_ms}ms</span>
                        </div>
                    ` : ''}
                    ${data.message ? `
                        <div style="margin-top: 16px; padding: 12px; background: #fef3c7; border-radius: 6px; border-left: 3px solid #f59e0b;">
                            <h4 style="font-size: 13px; margin: 0 0 8px 0; color: #78350f;">💡 快速反饋：</h4>
                            <p style="margin: 0; font-size: 12px; color: #78350f;">${data.message}</p>
                        </div>
                    ` : ''}
                </div>
            `
        },

        'island-deep-analysis': {
            title: '🔬 Deep Analysis',
            subtitle: 'POST /api/v1/realtime/analyze',
            renderForm: () => `
                <div class="info-card" style="background: #f0fdf4; border-left: 4px solid #10b981;">
                    <p style="margin: 0; font-size: 13px; color: #065f46;">
                        <strong>🔬 Deep Analysis</strong>: 完整深層分析（~26秒），使用全文+RAG知識庫
                    </p>
                </div>
                <div class="info-card" style="margin-top: 12px; background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先建立會談並添加錄音'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>分析模式</label>
                    <select id="island-deep-mode">
                        <option value="practice">practice (練習模式 - 4條建議)</option>
                        <option value="emergency">emergency (緊急模式 - 2條建議)</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandDeepAnalysis()" ${!islandTestData.sessionId ? 'disabled' : ''}>執行 Deep Analysis</button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談並添加錄音');
                }

                const mode = document.getElementById('island-deep-mode').value;

                // Get full transcript and prepare speakers
                const sessionResponse = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });
                const sessionData = await sessionResponse.json();
                const fullTranscript = sessionData.transcript_text || '';

                // Parse transcript into speaker segments (alternate parent/child)
                const lines = fullTranscript.split('\n').filter(l => l.trim() && !l.includes('秒]'));
                const speakers = lines.map((line, i) => ({
                    speaker: i % 2 === 0 ? 'counselor' : 'client',
                    text: line
                }));

                const response = await fetch(`${BASE_URL}/api/v1/realtime/analyze`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        mode: mode,
                        transcript: fullTranscript,
                        speakers: speakers,
                        time_range: '0:00-2:00',
                        session_id: islandTestData.sessionId,
                        use_cache: true
                    })
                });

                const data = await response.json();

                // Store analysis result for verification step
                islandTestData.lastAnalysis = data;
                islandTestData.lastAnalysisType = 'deep';

                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 🔬 Deep Analysis 完成</h3>
                    <div class="info-row">
                        <span class="info-label">分析類型</span>
                        <span class="info-value">Deep Analysis (深層分析)</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Safety Level</span>
                        <span class="info-value" style="color: ${data.safety_level === 'green' ? '#10b981' : data.safety_level === 'yellow' ? '#f59e0b' : '#ef4444'}">
                            ${data.safety_level === 'green' ? '🟢' : data.safety_level === 'yellow' ? '🟡' : '🔴'} ${data.safety_level || 'N/A'}
                        </span>
                    </div>
                    ${data.summary ? `
                        <div class="info-row">
                            <span class="info-label">Summary</span>
                            <span class="info-value">${data.summary}</span>
                        </div>
                    ` : ''}
                    <div class="info-row">
                        <span class="info-label">Quick Suggestions</span>
                        <span class="info-value">${data.quick_suggestions?.length || data.suggestions?.length || 0} 條</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Detailed Scripts</span>
                        <span class="info-value">${data.detailed_scripts?.length || 0} 個學派腳本</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">RAG Documents</span>
                        <span class="info-value">${data.rag_documents?.length || data.rag_sources?.length || 0} 筆知識庫</span>
                    </div>
                    ${(data.quick_suggestions || data.suggestions) && (data.quick_suggestions?.length > 0 || data.suggestions?.length > 0) ? `
                        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(0,0,0,0.1);">
                            <h4 style="font-size: 14px; margin-bottom: 8px;">💡 專家建議：</h4>
                            ${(data.quick_suggestions || data.suggestions || []).slice(0, 4).map((s, i) => `
                                <div style="background: #f0fdf4; padding: 8px; margin-bottom: 6px; border-radius: 6px; font-size: 12px; border-left: 3px solid #10b981;">
                                    ${i + 1}. ${s}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    ${data.detailed_scripts && data.detailed_scripts.length > 0 ? `
                        <div style="margin-top: 16px; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <h4 style="font-size: 13px; margin: 0 0 8px 0; color: #374151;">🎓 Detailed Scripts (8學派)：</h4>
                            ${data.detailed_scripts.slice(0, 8).map((s, i) => `
                                <div style="background: white; padding: 8px; margin-bottom: 6px; border-radius: 4px; font-size: 11px;">
                                    <strong>${i + 1}. ${s.school}</strong>: ${s.situation}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `
        },

        'island-verify-suggestions': {
            title: '✅ 驗證專家建議',
            subtitle: '檢查 quick_suggestions (4句) + detailed_scripts (8學派)',
            renderForm: () => {
                const analysis = islandTestData.lastAnalysis || {};
                const quickSuggestions = analysis.quick_suggestions || [];
                const detailedScripts = analysis.detailed_scripts || [];

                return `
                    <div class="info-card" style="background: ${quickSuggestions.length === 4 ? '#f0fdf4' : '#fef2f2'}; border-left: 4px solid ${quickSuggestions.length === 4 ? '#10b981' : '#ef4444'};">
                        <h4 style="font-size: 14px; margin: 0 0 8px 0;">
                            ${quickSuggestions.length === 4 ? '✅' : '❌'} Quick Suggestions: ${quickSuggestions.length}/4
                        </h4>
                        <p style="font-size: 12px; color: #6b7280; margin: 0;">
                            ${quickSuggestions.length === 4 ? '符合預期！' : `預期 4 條建議，實際 ${quickSuggestions.length} 條`}
                        </p>
                    </div>

                    <div class="info-card" style="margin-top: 12px; background: ${detailedScripts.length === 8 ? '#f0fdf4' : '#fef2f2'}; border-left: 4px solid ${detailedScripts.length === 8 ? '#10b981' : '#ef4444'};">
                        <h4 style="font-size: 14px; margin: 0 0 8px 0;">
                            ${detailedScripts.length === 8 ? '✅' : '❌'} Detailed Scripts: ${detailedScripts.length}/8
                        </h4>
                        <p style="font-size: 12px; color: #6b7280; margin: 0;">
                            ${detailedScripts.length === 8 ? '符合預期！' : `預期 8 個學派腳本，實際 ${detailedScripts.length} 個`}
                        </p>
                    </div>

                    ${quickSuggestions.length > 0 ? `
                        <div style="margin-top: 16px; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <h4 style="font-size: 13px; margin: 0 0 8px 0; color: #374151;">Quick Suggestions 詳細內容：</h4>
                            ${quickSuggestions.map((s, i) => `
                                <div style="background: white; padding: 8px; margin-bottom: 6px; border-radius: 4px; font-size: 11px; border-left: 2px solid #6366f1;">
                                    <strong>${i + 1}.</strong> ${s}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    ${detailedScripts.length > 0 ? `
                        <div style="margin-top: 16px; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <h4 style="font-size: 13px; margin: 0 0 8px 0; color: #374151;">Detailed Scripts 學派：</h4>
                            ${detailedScripts.map((s, i) => `
                                <div style="background: white; padding: 8px; margin-bottom: 6px; border-radius: 4px; font-size: 11px;">
                                    <strong>${i + 1}. ${s.school}</strong>: ${s.situation}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <button class="btn btn-success" onclick="window.executeIslandVerifySuggestions()" style="margin-top: 16px;">
                        重新檢查
                    </button>
                `;
            },
            execute: async () => {
                // This step just displays the verification results
                // No API call needed
                const analysis = islandTestData.lastAnalysis || {};
                return {
                    response: { ok: true, status: 200 },
                    data: {
                        quick_suggestions_count: analysis.quick_suggestions?.length || 0,
                        detailed_scripts_count: analysis.detailed_scripts?.length || 0,
                        passed: (analysis.quick_suggestions?.length === 4 || analysis.quick_suggestions?.length === 2) &&
                                analysis.detailed_scripts?.length === 8
                    }
                };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>${data.passed ? '✅ 驗證通過' : '⚠️ 驗證失敗'}</h3>
                    <div class="info-row">
                        <span class="info-label">Quick Suggestions</span>
                        <span class="info-value">${data.quick_suggestions_count} 條 ${data.quick_suggestions_count === 4 || data.quick_suggestions_count === 2 ? '✅' : '❌'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Detailed Scripts</span>
                        <span class="info-value">${data.detailed_scripts_count} 個學派 ${data.detailed_scripts_count === 8 ? '✅' : '❌'}</span>
                    </div>
                </div>
            `
        },

        'island-generate-report': {
            title: '📄 生成親子對話報告',
            subtitle: 'POST /api/v1/realtime/parents-report',
            renderForm: () => `
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先完成會談分析'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>報告類型</label>
                    <select id="island-report-type">
                        <option value="full">完整報告</option>
                        <option value="summary">摘要報告</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>包含 RAG 知識</label>
                    <select id="island-report-rag">
                        <option value="true">是</option>
                        <option value="false">否</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandGenerateReport()" ${!islandTestData.sessionId ? 'disabled' : ''}>生成報告</button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先完成會談並分析');
                }

                // Get full transcript from session
                const sessionResponse = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });
                const sessionData = await sessionResponse.json();
                const fullTranscript = sessionData.transcript_text || '';

                const response = await fetch(`${BASE_URL}/api/v1/realtime/parents-report`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify({
                        transcript: fullTranscript,
                        time_range: '0:00-1:00',
                        include_rag: document.getElementById('island-report-rag').value === 'true'
                    })
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 親子對話報告生成成功</h3>
                    <div class="info-row">
                        <span class="info-label">Summary</span>
                        <span class="info-value">${data.summary || '無'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Key Points</span>
                        <span class="info-value">${data.key_points?.length || 0} 個重點</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Suggestions</span>
                        <span class="info-value">${data.suggestions?.length || 0} 條建議</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">RAG Sources</span>
                        <span class="info-value">${data.rag_sources?.length || 0} 筆知識庫</span>
                    </div>
                    ${data.report_content ? `
                        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(0,0,0,0.1);">
                            <h4 style="font-size: 14px; margin-bottom: 8px;">📄 報告內容：</h4>
                            <div style="background: #f9fafb; padding: 12px; border-radius: 6px; font-size: 12px; max-height: 300px; overflow-y: auto; white-space: pre-wrap;">
${data.report_content}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `
        }
    };

    // Helper functions for selecting existing clients
    window.loadIslandClients = async () => {
        try {
            const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                headers: { 'Authorization': `Bearer ${state.token}` }
            });
            const data = await response.json();

            const select = document.getElementById('island-existing-client');
            select.innerHTML = '<option value="">-- 選擇孩子 --</option>';

            if (data.items && data.items.length > 0) {
                data.items.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.id;
                    option.textContent = `${client.name} (${client.code || 'N/A'})`;
                    select.appendChild(option);
                });
                console.log(`✅ 載入 ${data.items.length} 個孩子`);
            } else {
                select.innerHTML = '<option value="">-- 沒有找到任何孩子 --</option>';
            }
        } catch (error) {
            console.error('載入孩子列表失敗:', error);
            alert('載入失敗: ' + error.message);
        }
    };

    window.loadClientCases = async (clientId) => {
        const caseSelect = document.getElementById('island-existing-case');
        const selectBtn = document.getElementById('island-select-btn');

        if (!clientId) {
            caseSelect.innerHTML = '<option value="">-- 請先選擇孩子 --</option>';
            selectBtn.disabled = true;
            return;
        }

        try {
            const response = await fetch(`${BASE_URL}/api/v1/cases?client_id=${clientId}`, {
                headers: { 'Authorization': `Bearer ${state.token}` }
            });
            const data = await response.json();

            caseSelect.innerHTML = '<option value="">-- 選擇案件 --</option>';

            if (data.items && data.items.length > 0) {
                data.items.forEach(caseItem => {
                    const option = document.createElement('option');
                    option.value = caseItem.id;
                    option.textContent = caseItem.summary || `案件 ${caseItem.id.substring(0, 8)}`;
                    caseSelect.appendChild(option);
                });

                // Auto-select first case if only one
                if (data.items.length === 1) {
                    caseSelect.value = data.items[0].id;
                    selectBtn.disabled = false;
                }

                // Enable button when case is selected
                caseSelect.onchange = () => {
                    selectBtn.disabled = !caseSelect.value;
                };

                console.log(`✅ 載入 ${data.items.length} 個案件`);
            } else {
                caseSelect.innerHTML = '<option value="">-- 此孩子沒有案件 --</option>';
                selectBtn.disabled = true;
            }
        } catch (error) {
            console.error('載入案件列表失敗:', error);
            caseSelect.innerHTML = '<option value="">-- 載入失敗 --</option>';
            selectBtn.disabled = true;
        }
    };

    // Register global execute functions
    window.executeIslandLogin = () => window.executeStep('island-login');
    window.executeIslandSelectClient = () => window.executeStep('island-select-client');
    window.executeIslandCreateClientCase = () => window.executeStep('island-create-client-case');
    window.executeIslandCreateSession = () => window.executeStep('island-create-session');
    window.executeIslandSetScenario = () => window.executeStep('island-set-scenario');
    window.executeIslandAppendRecording = () => window.executeStep('island-append-recording');
    window.executeIslandQuickFeedback = () => window.executeStep('island-quick-feedback');
    window.executeIslandDeepAnalysis = () => window.executeStep('island-deep-analysis');
    window.executeIslandVerifySuggestions = () => window.executeStep('island-verify-suggestions');
    window.executeIslandGenerateReport = () => window.executeStep('island-generate-report');

    // Merge island steps into global steps object
    if (window.steps) {
        Object.assign(window.steps, islandSteps);
        console.log('✅ Island Parents testing steps loaded');
    } else {
        console.warn('⚠️ window.steps not found, storing island steps separately');
        window.islandSteps = islandSteps;
    }
})();
