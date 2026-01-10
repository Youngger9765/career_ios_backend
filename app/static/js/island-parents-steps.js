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
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>POST /api/auth/login</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto;">Content-Type: application/json</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "tenant_id": "island_parents",  // 固定值
  "email": "string",
  "password": "string"
}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "access_token": "eyJhbG...",  // JWT token
  "token_type": "bearer",
  "expires_in": 7776000         // 90 天
}</pre>
                        <p style="margin: 8px 0; color: #ef4444;"><strong>⚠️ 重要：</strong> 後續 API 都需要帶 Authorization header</p>
                        <pre style="background: #fef2f2; padding: 8px; border-radius: 4px; font-size: 12px;">Authorization: Bearer {access_token}</pre>
                    </div>
                </details>
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

        'island-get-credits': {
            title: '💰 取得額度資訊',
            subtitle: 'GET /api/auth/me → available_credits',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>GET /api/auth/me</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 取得當前用戶資訊與可用額度</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {access_token}
X-Tenant-Id: island_parents</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "full_name": "用戶名稱",
  "role": "counselor",
  "tenant_id": "island_parents",
  "is_active": true,
  "available_credits": 1000.0,  // ⭐ 可用額度（分鐘）
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS 流程：</strong></p>
                        <ol style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>登入成功後調用此 API 取得額度</li>
                            <li>在模式選擇頁顯示「預計還可使用 N 分鐘」</li>
                            <li>每次結束對話後可重新調用更新額度</li>
                        </ol>
                    </div>
                </details>
                <div class="info-card" style="background: #ecfdf5; border-left: 4px solid #10b981;">
                    <p style="margin: 0; font-size: 13px; color: #065f46;">
                        💰 此 API 回傳用戶可用額度，用於顯示剩餘分鐘數
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandGetCredits()" style="margin-top: 16px;">取得額度</button>
            `,
            execute: async () => {
                const token = state.token || localStorage.getItem('token');
                const tenant_id = localStorage.getItem('tenant_id') || 'island_parents';

                const response = await fetch(`${BASE_URL}/api/auth/me`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'X-Tenant-Id': tenant_id
                    }
                });

                const data = await response.json();
                if (response.ok) {
                    // Store credits for display
                    window.islandTestData.availableCredits = data.available_credits;
                }
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>💰 用戶額度資訊</h3>
                    <div class="info-row">
                        <span class="info-label">用戶名稱</span>
                        <span class="info-value">${data.full_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Email</span>
                        <span class="info-value">${data.email}</span>
                    </div>
                    <div class="info-row" style="background: #ecfdf5;">
                        <span class="info-label">可用額度</span>
                        <span class="info-value" style="color: #059669; font-weight: bold; font-size: 18px;">${Math.floor(data.available_credits)} 分鐘</span>
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
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>GET /api/v1/clients</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 取得所有孩子列表</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "items": [
    {
      "id": "uuid",           // ⭐ client_id
      "name": "小明",         // 孩子姓名
      "client_code": "C0001"  // 客戶編號
    }
  ],
  "total": 10
}</pre>
                        <hr style="margin: 12px 0; border: none; border-top: 1px solid #e2e8f0;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>GET /api/v1/cases?client_id={client_id}</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 取得該孩子的所有案件</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "items": [
    {
      "id": "uuid",              // ⭐ case_id - 建立 Session 用
      "case_number": "CASE0001",
      "status": "active"
    }
  ],
  "total": 1
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS 流程：</strong></p>
                        <ol style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>先調用 GET /api/v1/clients 取得孩子列表</li>
                            <li>用戶選擇孩子後，調用 GET /api/v1/cases?client_id=xxx</li>
                            <li>用戶選擇案件，儲存 case_id 供建立 Session 使用</li>
                        </ol>
                    </div>
                </details>
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
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>POST /api/v1/ui/client-case</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Content-Type: application/json
Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "name": "小明",           // 必填：孩子姓名
  "birth_date": "2015-06-15",  // 必填：生日 (YYYY-MM-DD)
  "grade": "小學3年級",     // 選填：年級
  "relationship": "爸爸",   // 必填：家長關係
  "case_summary": "",       // 選填：案件摘要
  "case_goals": ""          // 選填：目標
}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (201 Created):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "client_id": "uuid",      // ⭐ 儲存這個！
  "client_code": "C0001",
  "client_name": "小明",
  "case_id": "uuid",        // ⭐ 儲存這個！
  "case_number": "CASE0001",
  "message": "客戶與個案建立成功"
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS 提示：</strong> 儲存 client_id 和 case_id，建立 Session 時需要 case_id</p>
                    </div>
                </details>
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

        'island-get-client': {
            title: '👁️ 查看孩子資料',
            subtitle: 'GET /api/v1/clients/{id}',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>GET /api/v1/clients/{client_id}</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 取得單一孩子的詳細資料</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "id": "uuid",
  "code": "C240115-001",
  "name": "小明",
  "email": null,
  "gender": "不透露",
  "birth_date": "2015-01-01",
  "phone": "0000000000",
  "identity_option": "孩子",
  "current_status": "年級: 小學3年級",
  "notes": "關係: 爸爸",
  "metadata": null
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS Edit Page 用法：</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>從 <code>current_status</code> 解析年級：<code>年級: 小學3年級</code></li>
                            <li>從 <code>notes</code> 解析關係：<code>關係: 爸爸</code></li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Client ID:</strong> ${islandTestData.clientId || '請先選擇或建立孩子'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>Client ID</label>
                    <input type="text" id="island-get-client-id" value="${islandTestData.clientId || ''}" placeholder="從 2a 選擇孩子後自動帶入" />
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandGetClient()" ${!islandTestData.clientId ? 'disabled' : ''}>查看孩子資料</button>
            `,
            execute: async () => {
                const inputId = document.getElementById('island-get-client-id').value.trim();
                const clientId = inputId || islandTestData.clientId;
                if (!clientId) {
                    throw new Error('請先選擇或建立孩子');
                }

                const response = await fetch(`${BASE_URL}/api/v1/clients/${clientId}`, {
                    headers: {
                        'Authorization': `Bearer ${state.token}`
                    }
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>👶 孩子資料</h3>
                    <div class="info-row">
                        <span class="info-label">ID</span>
                        <span class="info-value" style="font-size: 11px;">${data.id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">編號</span>
                        <span class="info-value">${data.code}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">名字</span>
                        <span class="info-value">${data.name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">年級</span>
                        <span class="info-value">${data.current_status || '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">關係</span>
                        <span class="info-value">${data.notes || '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">生日</span>
                        <span class="info-value">${data.birth_date || '-'}</span>
                    </div>
                </div>
            `
        },

        'island-update-client': {
            title: '✏️ 更新孩子資料',
            subtitle: 'PATCH /api/v1/clients/{id}',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>PATCH /api/v1/clients/{client_id}</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 更新孩子資料（部分更新）</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Content-Type: application/json
Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body (只傳需要更新的欄位):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "name": "小明",                    // 選填
  "current_status": "年級: 小學4年級", // 選填：年級
  "notes": "關係: 媽媽"               // 選填：關係
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS Edit Page 用法：</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>使用 PATCH（不是 PUT）</li>
                            <li>年級存在 <code>current_status</code>：格式 <code>年級: 小學3年級</code></li>
                            <li>關係存在 <code>notes</code>：格式 <code>關係: 爸爸</code></li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Client ID:</strong> ${islandTestData.clientId || '請先選擇或建立孩子'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>Client ID</label>
                    <input type="text" id="island-update-client-id" value="${islandTestData.clientId || ''}" placeholder="從 2a 選擇孩子後自動帶入" />
                </div>
                <div class="form-group">
                    <label>孩子名字</label>
                    <input type="text" id="island-update-client-name" placeholder="小明" />
                </div>
                <div class="form-group">
                    <label>年級</label>
                    <select id="island-update-client-grade">
                        <option value="">-- 不更新 --</option>
                        <option value="小學1年級">小學1年級</option>
                        <option value="小學2年級">小學2年級</option>
                        <option value="小學3年級">小學3年級</option>
                        <option value="小學4年級">小學4年級</option>
                        <option value="小學5年級">小學5年級</option>
                        <option value="小學6年級">小學6年級</option>
                        <option value="國中1年級">國中1年級</option>
                        <option value="國中2年級">國中2年級</option>
                        <option value="國中3年級">國中3年級</option>
                        <option value="高中1年級">高中1年級</option>
                        <option value="高中2年級">高中2年級</option>
                        <option value="高中3年級">高中3年級</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>關係（你是孩子的）</label>
                    <select id="island-update-client-relation">
                        <option value="">-- 不更新 --</option>
                        <option value="爸爸">爸爸</option>
                        <option value="媽媽">媽媽</option>
                        <option value="爺爺">爺爺</option>
                        <option value="奶奶">奶奶</option>
                        <option value="外公">外公</option>
                        <option value="外婆">外婆</option>
                        <option value="其他">其他</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandUpdateClient()" ${!islandTestData.clientId ? 'disabled' : ''}>更新孩子資料</button>
            `,
            execute: async () => {
                const inputId = document.getElementById('island-update-client-id').value.trim();
                const clientId = inputId || islandTestData.clientId;
                if (!clientId) {
                    throw new Error('請先選擇或建立孩子');
                }

                const name = document.getElementById('island-update-client-name').value.trim();
                const grade = document.getElementById('island-update-client-grade').value;
                const relationship = document.getElementById('island-update-client-relation').value;

                // Build update body with only non-empty fields
                const body = {};
                if (name) body.name = name;
                if (grade) body.current_status = `年級: ${grade}`;
                if (relationship) body.notes = `關係: ${relationship}`;

                if (Object.keys(body).length === 0) {
                    throw new Error('請至少填寫一個欄位');
                }

                const response = await fetch(`${BASE_URL}/api/v1/clients/${clientId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify(body)
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 孩子資料已更新</h3>
                    <div class="info-row">
                        <span class="info-label">ID</span>
                        <span class="info-value" style="font-size: 11px;">${data.id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">名字</span>
                        <span class="info-value">${data.name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">年級</span>
                        <span class="info-value">${data.current_status || '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">關係</span>
                        <span class="info-value">${data.notes || '-'}</span>
                    </div>
                </div>
            `
        },

        'island-create-session': {
            title: '📋 建立會談',
            subtitle: 'POST /api/v1/sessions',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>POST /api/v1/sessions</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Content-Type: application/json
Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "case_id": "uuid",           // 必填：從 Step 2b 取得
  "name": "諮詢 - 2024-01-01", // 選填：會談名稱
  "session_mode": "practice",   // 選填：practice(對話練習) / emergency(親子溝通)
  "scenario": "功課問題",       // 選填：情境標題
  "scenario_description": "..."  // 選填：情境描述
  // session_date, start_time 自動產生
}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (201 Created):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "id": "uuid",             // ⭐ session_id 儲存這個！
  "client_id": "uuid",
  "case_id": "uuid",
  "session_number": 1,
  "name": "諮詢 - 2024-01-01 15:09",
  "session_mode": "practice",  // ⭐ 用於 History Page 分類
  "session_date": "2024-01-01T15:09:04Z",
  "start_time": "2024-01-01T15:09:04Z"
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS History Page:</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li><code>GET /api/v1/sessions?client_id=xxx</code> - 取得孩子的所有 session</li>
                            <li><code>GET /api/v1/sessions?session_mode=practice</code> - 篩選對話練習</li>
                            <li><code>GET /api/v1/sessions?session_mode=emergency</code> - 篩選親子溝通</li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Case ID:</strong> ${islandTestData.caseId || '請先建立客戶+案件'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>模式</label>
                    <select id="island-session-mode">
                        <option value="">-- 不指定 --</option>
                        <option value="practice">🎯 對話練習 (practice)</option>
                        <option value="emergency">🔴 親子溝通 (emergency)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>會談名稱 <span style="color:#888;font-size:12px">(選填，留空自動產生)</span></label>
                    <input type="text" id="island-session-name" placeholder="諮詢 - 自動產生日期時間" />
                </div>
                <div class="info-card" style="margin-top: 12px; background: #f0fdf4; border-left: 4px solid #22c55e;">
                    <p style="margin: 0; font-size: 12px; color: #166534;">
                        💡 <strong>簡化版</strong>：只需 case_id + session_mode，其他欄位自動填入
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandCreateSession()" ${!islandTestData.caseId ? 'disabled' : ''} style="margin-top: 16px;">建立會談</button>
            `,
            execute: async () => {
                if (!islandTestData.caseId) {
                    throw new Error('請先建立客戶+案件');
                }

                const sessionName = document.getElementById('island-session-name').value.trim();
                const sessionMode = document.getElementById('island-session-mode').value;

                // Send case_id and optional fields - session_date, start_time auto-filled by backend
                const requestBody = { case_id: islandTestData.caseId };
                if (sessionName) {
                    requestBody.name = sessionName;
                }
                if (sessionMode) {
                    requestBody.session_mode = sessionMode;
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
                        <span class="info-label">Mode</span>
                        <span class="info-value">${data.session_mode ? (data.session_mode === 'practice' ? '🎯 對話練習' : '🔴 親子溝通') : '未指定'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Session Date</span>
                        <span class="info-value">${data.session_date}</span>
                    </div>
                </div>
            `
        },

        'island-get-session': {
            title: '📖 取得會談',
            subtitle: 'GET /api/v1/sessions/{id}',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>GET /api/v1/sessions/{session_id}</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 取得 Session 完整資料（確認狀態、查看逐字稿）</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "id": "uuid",
  "client_id": "uuid",
  "client_name": "小明",
  "client_code": "CHILD001",
  "case_id": "uuid",
  "session_number": 1,
  "session_mode": "practice",
  "scenario": "功課問題",
  "scenario_description": "孩子不願意寫功課",
  "transcript_text": "累積的逐字稿...",
  "has_report": false
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS 使用時機:</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>錄音頁面載入時確認 Session 狀態</li>
                            <li>確認 scenario 設定是否正確</li>
                            <li>查看累積的 transcript_text</li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先建立會談'}
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandGetSession()" ${!islandTestData.sessionId ? 'disabled' : ''}>
                    取得會談資料
                </button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談');
                }

                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${state.token}`,
                        'X-Tenant-Id': 'island_parents'
                    }
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 取得會談成功</h3>
                    <div class="info-row">
                        <span class="info-label">Session ID</span>
                        <span class="info-value">${data.id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Client Name</span>
                        <span class="info-value">${data.client_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Mode</span>
                        <span class="info-value">${data.session_mode ? (data.session_mode === 'practice' ? '🎯 對話練習' : '🔴 親子溝通') : '未指定'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Scenario</span>
                        <span class="info-value">${data.scenario || '未設定'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Has Report</span>
                        <span class="info-value">${data.has_report ? '✅ 有' : '❌ 無'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Transcript Length</span>
                        <span class="info-value">${data.transcript_text ? data.transcript_text.length : 0} 字</span>
                    </div>
                </div>
            `
        },

        'island-set-scenario': {
            title: '🎯 設定練習情境',
            subtitle: 'PATCH /api/v1/sessions/{id}',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>PATCH /api/v1/sessions/{session_id}</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 更新 Session 資訊（設定練習情境）</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Content-Type: application/json
Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>URL 參數:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; font-size: 12px;">session_id: Step 3 回傳的 id</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "scenario": "親子溝通",              // 選填: 練習情境
  "scenario_description": "寫作業衝突"  // 選填: 情境描述
}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "id": "uuid",
  "name": "諮詢 - 2024/01/01",
  "scenario": "親子溝通",
  "scenario_description": "寫作業衝突",
  "updated_at": "2024-01-01T15:00:00Z"
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS 提示：</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>開始錄音前設定練習情境</li>
                            <li>scenario 和 scenario_description 都是選填</li>
                            <li>可以多次 PATCH 更新</li>
                        </ul>
                    </div>
                </details>
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

        'island-elevenlabs-token': {
            title: '🎤 取得 ElevenLabs Token',
            subtitle: 'POST /api/v1/transcript/elevenlabs-token',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>POST /api/v1/transcript/elevenlabs-token</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 取得 ElevenLabs STT WebSocket 連線用的臨時 token</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Content-Type: application/json</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong> 無</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "token": "xxx..."  // ⭐ 用於 WebSocket 連線
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS 提示：</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>開始錄音前調用</li>
                            <li>Token 是一次性的（single-use）</li>
                            <li>用 token 連接 ElevenLabs WebSocket</li>
                            <li>WebSocket URL: wss://api.elevenlabs.io/v1/speech-to-text/realtime</li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        💡 此 API 不需要 Authorization，但需要後端有設定 ELEVEN_LABS_API_KEY
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandElevenlabsToken()" style="margin-top: 16px;">取得 Token</button>
            `,
            execute: async () => {
                const response = await fetch(`${BASE_URL}/api/v1/transcript/elevenlabs-token`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();

                // Store token for potential use
                if (response.ok && data.token) {
                    islandTestData.elevenlabsToken = data.token;
                }

                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ ElevenLabs Token 取得成功</h3>
                    <div class="info-row">
                        <span class="info-label">Token</span>
                        <span class="info-value" style="font-size: 11px; word-break: break-all;">${data.token ? data.token.substring(0, 50) + '...' : 'N/A'}</span>
                    </div>
                    <div class="alert alert-info" style="margin-top: 12px;">
                        💡 使用此 token 連接 ElevenLabs WebSocket 進行語音轉文字
                    </div>
                </div>
            `
        },

        'island-append-recording': {
            title: '🎙️ Append 錄音片段',
            subtitle: 'POST /api/v1/sessions/{id}/recordings/append',
            renderForm: () => {
                // Use window.islandTestData to avoid closure issues
                const data = window.islandTestData;
                const currentSegment = data.transcriptSegments[data.currentSegmentIndex] || {};
                const maxIndex = data.transcriptSegments.length - 1;
                return `
                    <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                        <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                        <div style="margin-top: 12px; font-size: 13px;">
                            <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                                <code>POST /api/v1/sessions/{session_id}/recordings/append</code>
                            </div>
                            <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                            <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Content-Type: application/json
Authorization: Bearer {access_token}</pre>
                            <p style="margin: 8px 0; color: #64748b;"><strong>URL 參數:</strong></p>
                            <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; font-size: 12px;">session_id: Step 3 回傳的 id</pre>
                            <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong></p>
                            <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "transcript_text": "家長：寫作業時間囉。\\n孩子：我不想寫。",  // 必填
  "start_time": "2024-01-01T15:10:00Z",   // 必填: ISO 8601
  "end_time": "2024-01-01T15:10:10Z"      // 必填: ISO 8601
  // duration_seconds 選填，後端會自動計算
}</pre>
                            <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                            <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "session_id": "uuid",
  "recording_added": {
    "segment_number": 1,
    "start_time": "2024-01-01T15:10:00Z",
    "end_time": "2024-01-01T15:10:10Z",
    "duration_seconds": 10,              // 後端計算
    "transcript_text": "..."
  },
  "total_recordings": 1,
  "transcript_text": "完整逐字稿..."     // 累積
}</pre>
                            <p style="margin: 8px 0; color: #22c55e;"><strong>💡 前端建議：</strong></p>
                            <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                                <li><strong>Console 測試</strong>：每 10 秒 append 一次</li>
                                <li><strong>iOS</strong>：間隔由 iOS 自己決定（建議 10-15 秒）</li>
                                <li>不用傳 duration_seconds，後端會從 start_time/end_time 計算</li>
                                <li>累積的 transcript_text 用於 Quick/Deep/Report 分析</li>
                            </ul>
                        </div>
                    </details>
                    <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                        <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                            <strong>Session ID:</strong> ${data.sessionId || '請先建立會談'}
                        </p>
                    </div>
                    <div class="form-group" style="margin-top: 16px;">
                        <label>片段編號 (${data.currentSegmentIndex + 1}/${data.transcriptSegments.length})</label>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn" onclick="window.islandTestData.currentSegmentIndex = Math.max(0, window.islandTestData.currentSegmentIndex - 1); window.selectStep('island-append-recording')" ${data.currentSegmentIndex === 0 ? 'disabled' : ''}>◀ 上一段</button>
                            <button class="btn" onclick="window.islandTestData.currentSegmentIndex = Math.min(${maxIndex}, window.islandTestData.currentSegmentIndex + 1); window.selectStep('island-append-recording')" ${data.currentSegmentIndex === maxIndex ? 'disabled' : ''}>下一段 ▶</button>
                        </div>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <div class="form-group" style="flex: 1;">
                            <label>Start Time (ISO 8601)</label>
                            <input type="text" id="island-start-time" value="${(() => {
                                const base = new Date();
                                const start = new Date(base.getTime() + data.currentSegmentIndex * 10 * 1000);
                                return start.toISOString();
                            })()}" />
                        </div>
                        <div class="form-group" style="flex: 1;">
                            <label>End Time (ISO 8601)</label>
                            <input type="text" id="island-end-time" value="${(() => {
                                const base = new Date();
                                const end = new Date(base.getTime() + (data.currentSegmentIndex + 1) * 10 * 1000);
                                return end.toISOString();
                            })()}" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label>逐字稿內容</label>
                        <textarea id="island-transcript" rows="5">${currentSegment.text || ''}</textarea>
                    </div>
                    <button class="btn btn-primary" onclick="window.executeIslandAppendRecording()" ${!data.sessionId ? 'disabled' : ''}>Append 錄音片段</button>
                `;
            },
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談');
                }

                const transcript = document.getElementById('island-transcript').value;
                const startTime = document.getElementById('island-start-time').value;
                const endTime = document.getElementById('island-end-time').value;

                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}/recordings/append`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify({
                        transcript_text: transcript,
                        start_time: startTime,
                        end_time: endTime
                        // duration_seconds 由後端自動計算
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
            subtitle: 'POST /api/v1/sessions/{id}/quick-feedback',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>POST /api/v1/sessions/{session_id}/quick-feedback</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 10秒內快速反饋（Toast 提示用）</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong> 無（從 session 自動讀取逐字稿）</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "message": "你沒急著反駁",  // ⭐ 15字以內
  "type": "ai_generated",
  "timestamp": "2024-01-01T15:10:00Z",
  "latency_ms": 7727                    // ~8秒
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 前端建議：</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li><strong>Console 測試</strong>：每 10 秒調用一次</li>
                            <li><strong>iOS</strong>：間隔自己決定（建議 10-15 秒）</li>
                            <li><strong>⏱️ 後端分析</strong>：自動取最近 15 秒的 segments</li>
                            <li>⚠️ message 強制 <strong>15 字以內</strong>，適合同心圓 UI</li>
                            <li>session_id 在 URL 路徑中，不需要 body</li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
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

                // New session-based API - no need to fetch transcript separately
                // Use session_mode from stored session data
                const sessionMode = islandTestData.sessionMode || 'practice';
                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}/quick-feedback?session_mode=${sessionMode}`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.token}`
                    }
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
            subtitle: 'POST /api/v1/sessions/{id}/deep-analyze',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>POST /api/v1/sessions/{session_id}/deep-analyze?session_mode=practice</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 深層分析（約15-20秒），返回安全等級 + 專家建議</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Query Parameters:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">session_mode=practice    // 選填: practice|emergency，預設 practice
use_rag=false    // 選填: 預設 false</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Request Body:</strong> 無（從 session 自動讀取逐字稿）</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "safety_level": "green",           // ⭐ 安全等級: green|yellow|red
  "summary": "對話分析摘要...",       // ⭐ 分析摘要
  "suggestions": ["建議1"],          // ⭐ 專家建議 (1條)
  "alerts": [],                      // 警告訊息
  "time_range": "0:00-2:00",
  "timestamp": "2024-01-01T15:10:00Z",
  "rag_sources": [],                 // RAG 知識來源
  "provider_metadata": {
    "provider": "gemini",
    "latency_ms": 17000,             // ~17秒
    "model": "gemini-3-flash-preview"
  }
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 前端建議：</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li><strong>iOS</strong>：用戶點擊「立即分析」時調用（或定時 60 秒）</li>
                            <li><strong>⏱️ 後端分析</strong>：自動取最近 60 秒的 segments</li>
                            <li>根據 safety_level 顯示對應顏色</li>
                            <li>suggestions 只有 1 條，直接顯示</li>
                            <li>session_id 在 URL 路徑中，mode 在 query string</li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先建立會談並添加錄音'}
                    </p>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <label>分析模式</label>
                    <select id="island-deep-mode">
                        <option value="practice">practice (練習模式)</option>
                        <option value="emergency">emergency (緊急模式)</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandDeepAnalysis()" ${!islandTestData.sessionId ? 'disabled' : ''}>執行 Deep Analysis</button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談並添加錄音');
                }

                const sessionMode = document.getElementById('island-deep-mode').value;

                // New session-based API - no need to fetch transcript separately
                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}/deep-analyze?session_mode=${sessionMode}&use_rag=false`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.token}`
                    }
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
            subtitle: '檢查 suggestions (1句)',
            renderForm: () => {
                const analysis = islandTestData.lastAnalysis || {};
                const suggestions = analysis.suggestions || analysis.quick_suggestions || [];

                return `
                    <div class="info-card" style="background: ${suggestions.length >= 1 ? '#f0fdf4' : '#fef2f2'}; border-left: 4px solid ${suggestions.length >= 1 ? '#10b981' : '#ef4444'};">
                        <h4 style="font-size: 14px; margin: 0 0 8px 0;">
                            ${suggestions.length >= 1 ? '✅' : '❌'} Suggestions: ${suggestions.length}/1
                        </h4>
                        <p style="font-size: 12px; color: #6b7280; margin: 0;">
                            ${suggestions.length >= 1 ? '符合預期！' : `預期 1 條建議，實際 ${suggestions.length} 條`}
                        </p>
                    </div>

                    ${suggestions.length > 0 ? `
                        <div style="margin-top: 16px; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <h4 style="font-size: 13px; margin: 0 0 8px 0; color: #374151;">💡 專家建議：</h4>
                            ${suggestions.map((s, i) => `
                                <div style="background: white; padding: 8px; margin-bottom: 6px; border-radius: 4px; font-size: 12px; border-left: 3px solid #10b981;">
                                    ${s}
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
                const analysis = islandTestData.lastAnalysis || {};
                const suggestions = analysis.suggestions || analysis.quick_suggestions || [];
                return {
                    response: { ok: true, status: 200 },
                    data: {
                        suggestions_count: suggestions.length,
                        passed: suggestions.length >= 1
                    }
                };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>${data.passed ? '✅ 驗證通過' : '⚠️ 驗證失敗'}</h3>
                    <div class="info-row">
                        <span class="info-label">Suggestions</span>
                        <span class="info-value">${data.suggestions_count} 條 ${data.suggestions_count >= 1 ? '✅' : '❌'}</span>
                    </div>
                </div>
            `
        },

        'island-generate-report': {
            title: '📄 生成親子對話報告',
            subtitle: 'POST /api/v1/sessions/{id}/report',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS 工程師必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>POST /api/v1/sessions/{session_id}/report</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 會談結束後生成親子對話報告</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Query Params:</strong> use_rag=true (預設啟用 RAG)</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "encouragement": "你正在接住孩子",  // 💪 鼓勵標題 (15字以內)
  "issue": "對話陷入無效重複，缺乏雙向互動。",                      // ❓ 待解決議題
  "analyze": "重複相同的指令容易讓孩子產生「聽而不聞」...",         // 📊 溝通分析
  "suggestion": "「我知道你還想玩，要停下來很難。你是想...」",      // 💡 建議說法
  "references": [                                                   // 📚 RAG 參考資料
    {
      "title": "正向教養：溫和而堅定的教養方式",
      "content": "當孩子不配合時，提供有限選擇讓孩子感受到自主權...",
      "source": "正向教養指南.pdf",
      "theory": "正向教養"
    }
  ],
  "timestamp": "2024-01-01T15:30:00Z"
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS 提示：</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>會談結束後調用，生成完整報告 + 結算 Billing</li>
                            <li>encouragement: 綠色卡片，正向鼓勵</li>
                            <li>issue: 橙色卡片，待改進議題</li>
                            <li>analyze: 藍色卡片，溝通分析</li>
                            <li>suggestion: 紫色卡片，建議說法</li>
                            <li>references: 灰色區塊，RAG 教養理論參考</li>
                        </ul>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先完成會談分析'}
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandGenerateReport()" ${!islandTestData.sessionId ? 'disabled' : ''} style="margin-top: 16px;">生成報告</button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先完成會談並分析');
                }

                // New session-based API - no need to fetch transcript separately
                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}/report`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.token}`
                    }
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 親子對話報告生成成功</h3>

                    <div style="margin-top: 16px; padding: 16px; background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%); border-radius: 8px; border-left: 4px solid #4caf50;">
                        <h4 style="font-size: 14px; color: #2e7d32; margin-bottom: 8px;">💪 鼓勵</h4>
                        <p style="margin: 0; color: #1b5e20; font-size: 15px;">${data.encouragement || '感謝你願意花時間與孩子溝通。'}</p>
                    </div>

                    <div style="margin-top: 12px; padding: 16px; background: #fff3e0; border-radius: 8px; border-left: 4px solid #ff9800;">
                        <h4 style="font-size: 14px; color: #e65100; margin-bottom: 8px;">❓ 待解決的議題</h4>
                        <p style="margin: 0; color: #bf360c; font-size: 14px;">${data.issue || '無'}</p>
                    </div>

                    <div style="margin-top: 12px; padding: 16px; background: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;">
                        <h4 style="font-size: 14px; color: #1565c0; margin-bottom: 8px;">📊 溝通內容分析</h4>
                        <p style="margin: 0; color: #0d47a1; font-size: 14px;">${data.analyze || '無'}</p>
                    </div>

                    <div style="margin-top: 12px; padding: 16px; background: #f3e5f5; border-radius: 8px; border-left: 4px solid #9c27b0;">
                        <h4 style="font-size: 14px; color: #7b1fa2; margin-bottom: 8px;">💡 建議下次可以這樣說</h4>
                        <p style="margin: 0; color: #4a148c; font-size: 14px;">${data.suggestion || '無'}</p>
                    </div>

                    ${data.references && data.references.length > 0 ? `
                        <div style="margin-top: 16px; padding: 16px; background: #fafafa; border-radius: 8px; border: 1px solid #e0e0e0;">
                            <h4 style="font-size: 14px; color: #616161; margin-bottom: 12px;">📚 參考資料 (${data.references.length} 筆)</h4>
                            ${data.references.map((ref, i) => `
                                <div style="margin-bottom: 12px; padding: 10px; background: white; border-radius: 6px; border-left: 3px solid #9e9e9e;">
                                    <div style="font-weight: 600; color: #424242; font-size: 13px;">${i + 1}. ${ref.title || ref.source}</div>
                                    <div style="color: #757575; font-size: 12px; margin-top: 4px;">${ref.content}</div>
                                    <div style="color: #9e9e9e; font-size: 11px; margin-top: 4px;">來源: ${ref.source} | ${ref.theory || '教養理論'}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <div style="margin-top: 12px; text-align: right; color: #9e9e9e; font-size: 11px;">
                        生成時間: ${data.timestamp || new Date().toISOString()}
                    </div>
                </div>
            `
        },

        'island-get-session-report': {
            title: '📄 取得會談報告 (History)',
            subtitle: 'GET /api/v1/sessions/{id}/report',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS History Page 必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>GET /api/v1/sessions/{session_id}/report</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 用 session_id 取得報告 (History Page 點擊會談時使用)</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "id": "report-uuid",
  "session_id": "session-uuid",
  "client_name": "小明",
  "session_number": 5,
  "content_json": {
    "encouragement": "你正在接住孩子",
    "issue": "對話陷入無效重複...",
    "analyze": "重複相同的指令...",
    "suggestion": "我知道你還想玩..."
  },
  "status": "completed"
}</pre>
                        <p style="margin: 8px 0; color: #ef4444;"><strong>⚠️ 注意：</strong> 如果該 session 沒有報告會回傳 404</p>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS History Page 流程:</strong></p>
                        <ol style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li>GET /api/v1/sessions → 列出會談 (含 has_report 欄位)</li>
                            <li>點擊 has_report=true 的會談</li>
                            <li>GET /api/v1/sessions/{id}/report → 取得報告內容</li>
                        </ol>
                    </div>
                </details>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Session ID:</strong> ${islandTestData.sessionId || '請先建立會談並生成報告'}
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandGetSessionReport()" ${!islandTestData.sessionId ? 'disabled' : ''} style="margin-top: 16px;">取得報告</button>
            `,
            execute: async () => {
                if (!islandTestData.sessionId) {
                    throw new Error('請先建立會談');
                }

                const response = await fetch(`${BASE_URL}/api/v1/sessions/${islandTestData.sessionId}/report`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${state.token}`,
                        'X-Tenant-Id': 'island_parents'
                    }
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>${data.detail ? '❌ ' + data.detail : '✅ 取得報告成功'}</h3>

                    ${!data.detail ? `
                        <div class="info-row">
                            <span class="info-label">Report ID</span>
                            <span class="info-value">${data.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Client</span>
                            <span class="info-value">${data.client_name} (第 ${data.session_number} 次會談)</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Status</span>
                            <span class="info-value">${data.status === 'completed' ? '✅ 已完成' : data.status}</span>
                        </div>

                        ${data.content_json ? `
                            <div style="margin-top: 16px; padding: 16px; background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%); border-radius: 8px; border-left: 4px solid #4caf50;">
                                <h4 style="font-size: 14px; color: #2e7d32; margin-bottom: 8px;">💪 鼓勵</h4>
                                <p style="margin: 0; color: #1b5e20; font-size: 14px;">${data.content_json.encouragement || '-'}</p>
                            </div>

                            <div style="margin-top: 12px; padding: 16px; background: #fff3e0; border-radius: 8px; border-left: 4px solid #ff9800;">
                                <h4 style="font-size: 14px; color: #e65100; margin-bottom: 8px;">❓ 待解決議題</h4>
                                <p style="margin: 0; color: #bf360c; font-size: 14px;">${data.content_json.issue || '-'}</p>
                            </div>

                            <div style="margin-top: 12px; padding: 16px; background: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;">
                                <h4 style="font-size: 14px; color: #1565c0; margin-bottom: 8px;">📊 分析</h4>
                                <p style="margin: 0; color: #0d47a1; font-size: 14px;">${data.content_json.analyze || '-'}</p>
                            </div>

                            <div style="margin-top: 12px; padding: 16px; background: #f3e5f5; border-radius: 8px; border-left: 4px solid #9c27b0;">
                                <h4 style="font-size: 14px; color: #6a1b9a; margin-bottom: 8px;">💡 建議</h4>
                                <p style="margin: 0; color: #4a148c; font-size: 14px;">${data.content_json.suggestion || '-'}</p>
                            </div>
                        ` : '<p style="color: #9ca3af; margin-top: 12px;">報告內容為空</p>'}
                    ` : ''}
                </div>
            `
        },

        'island-list-sessions': {
            title: '📋 列出所有會談 (History)',
            subtitle: 'GET /api/v1/sessions',
            renderForm: () => `
                <details class="api-docs" style="margin-bottom: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
                    <summary style="cursor: pointer; font-weight: 600; color: #475569;">📖 API 說明 (iOS History Page 必讀)</summary>
                    <div style="margin-top: 12px; font-size: 13px;">
                        <div style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <code>GET /api/v1/sessions</code>
                        </div>
                        <p style="margin: 8px 0; color: #64748b;"><strong>用途：</strong> 列出所有會談記錄 (History Page)</p>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Headers:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">Authorization: Bearer {access_token}</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Query Parameters:</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">client_id: UUID       // 依孩子篩選
session_mode: string  // practice / emergency
search: string        // 搜尋孩子名稱
skip: int             // 分頁偏移 (default: 0)
limit: int            // 每頁筆數 (default: 20)</pre>
                        <p style="margin: 8px 0; color: #64748b;"><strong>Response (200 OK):</strong></p>
                        <pre style="background: #f1f5f9; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{
  "total": 15,
  "items": [
    {
      "id": "session-uuid",
      "client_name": "小明",
      "session_mode": "practice",
      "scenario": "功課問題",
      "has_report": true,
      "created_at": "2025-01-05T10:00:00Z"
    }
  ]
}</pre>
                        <p style="margin: 8px 0; color: #22c55e;"><strong>💡 iOS History Page 用法:</strong></p>
                        <ul style="margin: 4px 0; padding-left: 20px; color: #64748b;">
                            <li><code>?client_id=xxx</code> - 取得某孩子的所有會談</li>
                            <li><code>?session_mode=practice</code> - 篩選對話練習</li>
                            <li><code>?session_mode=emergency</code> - 篩選親子溝通</li>
                        </ul>
                    </div>
                </details>
                <div class="form-group">
                    <label>篩選模式</label>
                    <select id="island-list-mode">
                        <option value="">全部</option>
                        <option value="practice">🎯 對話練習 (practice)</option>
                        <option value="emergency">🔴 親子溝通 (emergency)</option>
                    </select>
                </div>
                <div class="info-card" style="background: #f0f9ff; border-left: 4px solid #0ea5e9;">
                    <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                        <strong>Client ID:</strong> ${islandTestData.clientId || '將列出所有會談'}
                    </p>
                </div>
                <button class="btn btn-primary" onclick="window.executeIslandListSessions()" style="margin-top: 16px;">列出會談</button>
            `,
            execute: async () => {
                const mode = document.getElementById('island-list-mode').value;
                let url = `${BASE_URL}/api/v1/sessions`;
                const params = [];

                if (islandTestData.clientId) {
                    params.push(`client_id=${islandTestData.clientId}`);
                }
                if (mode) {
                    params.push(`session_mode=${mode}`);
                }
                if (params.length > 0) {
                    url += '?' + params.join('&');
                }

                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${state.token}`,
                        'X-Tenant-Id': 'island_parents'
                    }
                });

                const data = await response.json();
                return { response, data };
            },
            renderPreview: (data) => `
                <div class="info-card">
                    <h3>✅ 列出會談成功</h3>
                    <div class="info-row">
                        <span class="info-label">總數</span>
                        <span class="info-value">${data.total || 0} 筆</span>
                    </div>

                    ${data.items && data.items.length > 0 ? `
                        <div style="margin-top: 16px;">
                            <h4 style="font-size: 14px; color: #475569; margin-bottom: 8px;">會談列表</h4>
                            ${data.items.slice(0, 5).map((session, i) => `
                                <div style="margin-bottom: 8px; padding: 10px; background: #f8fafc; border-radius: 6px; border-left: 3px solid ${session.session_mode === 'practice' ? '#22c55e' : session.session_mode === 'emergency' ? '#ef4444' : '#9ca3af'};">
                                    <div style="font-weight: 600; color: #1e293b; font-size: 13px;">
                                        ${session.session_mode === 'practice' ? '🎯' : session.session_mode === 'emergency' ? '🔴' : '📋'} ${session.client_name || '未知'} - ${session.scenario || '無情境'}
                                    </div>
                                    <div style="color: #64748b; font-size: 12px; margin-top: 4px;">
                                        報告: ${session.has_report ? '✅' : '❌'} | ${session.created_at ? new Date(session.created_at).toLocaleDateString('zh-TW') : 'N/A'}
                                    </div>
                                </div>
                            `).join('')}
                            ${data.items.length > 5 ? `<p style="color: #9ca3af; font-size: 12px;">還有 ${data.items.length - 5} 筆...</p>` : ''}
                        </div>
                    ` : '<p style="color: #9ca3af; margin-top: 12px;">沒有會談記錄</p>'}
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
    window.executeIslandGetCredits = () => window.executeStep('island-get-credits');
    window.executeIslandSelectClient = () => window.executeStep('island-select-client');
    window.executeIslandCreateClientCase = () => window.executeStep('island-create-client-case');
    window.executeIslandGetClient = () => window.executeStep('island-get-client');
    window.executeIslandUpdateClient = () => window.executeStep('island-update-client');
    window.executeIslandCreateSession = () => window.executeStep('island-create-session');
    window.executeIslandGetSession = () => window.executeStep('island-get-session');
    window.executeIslandSetScenario = () => window.executeStep('island-set-scenario');
    window.executeIslandElevenlabsToken = () => window.executeStep('island-elevenlabs-token');
    window.executeIslandAppendRecording = () => window.executeStep('island-append-recording');
    window.executeIslandQuickFeedback = () => window.executeStep('island-quick-feedback');
    window.executeIslandDeepAnalysis = () => window.executeStep('island-deep-analysis');
    window.executeIslandVerifySuggestions = () => window.executeStep('island-verify-suggestions');
    window.executeIslandGenerateReport = () => window.executeStep('island-generate-report');
    window.executeIslandGetSessionReport = () => window.executeStep('island-get-session-report');
    window.executeIslandListSessions = () => window.executeStep('island-list-sessions');

    // Merge island steps into global steps object
    if (window.steps) {
        Object.assign(window.steps, islandSteps);
        console.log('✅ Island Parents testing steps loaded');
    } else {
        console.warn('⚠️ window.steps not found, storing island steps separately');
        window.islandSteps = islandSteps;
    }
})();
