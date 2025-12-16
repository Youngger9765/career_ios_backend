        const steps = {
            register: {
                title: '註冊帳號',
                subtitle: 'POST /auth/register',
                renderForm: () => `
                    <div class="form-group">
                        <label>Tenant ID</label>
                        <select id="register_tenant_id">
                            <option value="career">career</option>
                            <option value="island">island</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Email *</label>
                        <input type="email" id="register_email" placeholder="user@example.com" />
                    </div>
                    <div class="form-group">
                        <label>Username *</label>
                        <input type="text" id="register_username" placeholder="username" />
                    </div>
                    <div class="form-group">
                        <label>Full Name *</label>
                        <input type="text" id="register_full_name" placeholder="Full Name" />
                    </div>
                    <div class="form-group">
                        <label>Password * (至少 8 個字元)</label>
                        <input type="password" id="register_password" placeholder="password" />
                    </div>
                    <div class="form-group">
                        <label>Role</label>
                        <select id="register_role">
                            <option value="counselor">Counselor</option>
                            <option value="supervisor">Supervisor</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <button class="btn btn-primary" onclick="executeRegister()">註冊</button>
                `,
                execute: async () => {
                    const tenant_id = document.getElementById('register_tenant_id').value;
                    const email = document.getElementById('register_email').value;
                    const username = document.getElementById('register_username').value;
                    const full_name = document.getElementById('register_full_name').value;
                    const password = document.getElementById('register_password').value;
                    const role = document.getElementById('register_role').value;

                    if (!email || !username || !full_name || !password) {
                        return {
                            response: { ok: false, status: 400 },
                            data: { detail: '請填寫所有必填欄位' }
                        };
                    }

                    if (password.length < 8) {
                        return {
                            response: { ok: false, status: 400 },
                            data: { detail: '密碼長度至少需要 8 個字元' }
                        };
                    }

                    const response = await fetch(`${BASE_URL}/api/auth/register`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tenant_id, email, username, full_name, password, role })
                    });

                    const data = await response.json();
                    if (response.ok) {
                        state.token = data.access_token;
                        localStorage.setItem('token', state.token);

                        // 自動獲取當前用戶資訊
                        try {
                            const meResponse = await fetch(`${BASE_URL}/api/auth/me`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (meResponse.ok) {
                                const userData = await meResponse.json();
                                state.currentUser = userData;
                            }
                        } catch (error) {
                            console.error('Failed to fetch user info:', error);
                        }

                        // 自動載入 field schemas
                        await loadFieldSchemas();
                    }
                    return { response, data };
                },
                renderPreview: (data) => {
                    if (!data || data.detail) {
                        return `
                            <div class="info-card" style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444;">
                                <h3>❌ 註冊失敗</h3>
                                <p style="color: #ef4444;">${data?.detail || '未知錯誤'}</p>
                            </div>
                        `;
                    }
                    return `
                        <div class="info-card">
                            <h3>✅ 註冊成功</h3>
                            <div class="info-row">
                                <span class="info-label">Token Type</span>
                                <span class="info-value">${data.token_type}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Expires In</span>
                                <span class="info-value">${data.expires_in}s</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Access Token</span>
                                <span class="info-value" style="font-size: 11px; word-break: break-all;">${data.access_token.substring(0, 40)}...</span>
                            </div>
                            <div class="info-row" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.1);">
                                <span class="info-label">提示</span>
                                <span class="info-value" style="color: #0ea5e9;">已自動登入，Token 已儲存</span>
                            </div>
                        </div>
                    `;
                }
            },
            login: {
                title: '登入驗證',
                subtitle: 'POST /auth/login',
                renderForm: () => `
                    <div class="form-group">
                        <label>Tenant ID</label>
                        <select id="tenant_id" onchange="document.getElementById('email').value = this.value === 'career' ? 'admin@career.com' : 'admin@island.com'">
                            <option value="career">career</option>
                            <option value="island">island</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" id="email" value="admin@career.com" />
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" id="password" value="password123" />
                    </div>
                    <button class="btn btn-primary" onclick="executeLogin()">登入</button>
                `,
                execute: async () => {
                    const tenant_id = document.getElementById('tenant_id').value;
                    const email = document.getElementById('email').value;
                    const password = document.getElementById('password').value;

                    const response = await fetch(`${BASE_URL}/api/auth/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tenant_id, email, password })
                    });

                    const data = await response.json();
                    if (response.ok) {
                        state.token = data.access_token;
                        localStorage.setItem('token', state.token);

                        // 自動獲取當前用戶資訊
                        try {
                            const meResponse = await fetch(`${BASE_URL}/api/auth/me`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (meResponse.ok) {
                                const userData = await meResponse.json();
                                state.currentUser = userData;
                            }
                        } catch (error) {
                            console.error('Failed to fetch user info:', error);
                        }

                        // 自動載入 field schemas
                        await loadFieldSchemas();
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>🔐 登入成功</h3>
                        <div class="info-row">
                            <span class="info-label">Token Type</span>
                            <span class="info-value">${data.token_type}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Expires In</span>
                            <span class="info-value">${data.expires_in}s</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Access Token</span>
                            <span class="info-value" style="font-size: 11px; word-break: break-all;">${data.access_token.substring(0, 40)}...</span>
                        </div>
                    </div>
                `
            },
            me: {
                title: '取得當前用戶',
                subtitle: 'GET /auth/me',
                renderForm: () => `
                    <div class="info-card">
                        <p style="font-size: 13px; color: #6b7280;">需要先登入取得 Token</p>
                    </div>
                    <button class="btn btn-primary" onclick="executeMe()" ${!state.token ? 'disabled' : ''}>取得用戶資訊</button>
                `,
                execute: async () => {
                    const response = await fetch(`${BASE_URL}/api/auth/me`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.currentUser = data;
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>👤 用戶資訊</h3>
                        <div class="info-row">
                            <span class="info-label">姓名</span>
                            <span class="info-value">${data.full_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Email</span>
                            <span class="info-value">${data.email}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">角色</span>
                            <span class="info-value">${data.role}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">租戶</span>
                            <span class="info-value">${data.tenant_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">狀態</span>
                            <span class="info-value">${data.is_active ? '✅ 啟用' : '❌ 停用'}</span>
                        </div>
                    </div>
                `
            },
            'get-client-field-schema': {
                title: '取得 Client 欄位配置',
                subtitle: 'GET /api/v1/ui/field-schemas/client',
                renderForm: () => `
                    ${renderTenantBanner()}
                    <p>取得當前租戶的 Client 表單欄位配置，用於動態生成表單</p>
                    <button class="btn btn-primary" onclick="executeGetClientFieldSchema()" ${!state.token ? 'disabled' : ''}>取得配置</button>
                `,
                execute: async () => {
                    const response = await fetch(`${BASE_URL}/api/v1/ui/field-schemas/client`, {
                        headers: {
                            'Authorization': `Bearer ${state.token}`
                        }
                    });

                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="response-card">
                        <h4>📋 ${data.tenant_id.toUpperCase()} - ${data.form_type.toUpperCase()} 表單配置</h4>
                        ${data.sections.map(section => `
                            <div style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #3b82f6;">
                                <h5 style="margin: 0 0 10px 0; color: #1e40af;">📌 ${section.title}</h5>
                                ${section.description ? `<p style="color: #6b7280; margin: 0 0 15px 0;">${section.description}</p>` : ''}
                                <div style="display: grid; gap: 12px;">
                                    ${section.fields.map(field => `
                                        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
                                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                                                <div>
                                                    <strong style="color: #111827;">${field.label}</strong>
                                                    ${field.required ? '<span style="color: #ef4444; margin-left: 4px;">*</span>' : ''}
                                                </div>
                                                <span style="background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${field.type}</span>
                                            </div>
                                            <div style="font-size: 13px; color: #6b7280;">
                                                <div><strong>Key:</strong> ${field.key}</div>
                                                ${field.placeholder ? `<div><strong>Placeholder:</strong> ${field.placeholder}</div>` : ''}
                                                ${field.help_text ? `<div><strong>說明:</strong> ${field.help_text}</div>` : ''}
                                                ${field.options ? `<div><strong>選項:</strong> ${field.options.join(', ')}</div>` : ''}
                                                ${field.default_value ? `<div><strong>預設值:</strong> ${field.default_value}</div>` : ''}
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `,
                renderResponse: (data) => `
                    <div class="response-card">
                        <h4>📋 ${data.tenant_id.toUpperCase()} - ${data.form_type.toUpperCase()} 表單配置</h4>
                        ${data.sections.map(section => `
                            <div style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #3b82f6;">
                                <h5 style="margin: 0 0 10px 0; color: #1e40af;">📌 ${section.title}</h5>
                                ${section.description ? `<p style="color: #6b7280; margin: 0 0 15px 0;">${section.description}</p>` : ''}
                                <div style="display: grid; gap: 12px;">
                                    ${section.fields.map(field => `
                                        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
                                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                                                <div>
                                                    <strong style="color: #111827;">${field.label}</strong>
                                                    ${field.required ? '<span style="color: #ef4444; margin-left: 4px;">*</span>' : ''}
                                                </div>
                                                <span style="background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${field.type}</span>
                                            </div>
                                            <div style="font-size: 13px; color: #6b7280;">
                                                <div><strong>Key:</strong> ${field.key}</div>
                                                ${field.placeholder ? `<div><strong>Placeholder:</strong> ${field.placeholder}</div>` : ''}
                                                ${field.help_text ? `<div><strong>說明:</strong> ${field.help_text}</div>` : ''}
                                                ${field.options ? `<div><strong>選項:</strong> ${field.options.join(', ')}</div>` : ''}
                                                ${field.default_value ? `<div><strong>預設值:</strong> ${field.default_value}</div>` : ''}
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `
            },
            'get-case-field-schema': {
                title: '取得 Case 欄位配置',
                subtitle: 'GET /api/v1/ui/field-schemas/case',
                renderForm: () => `
                    ${renderTenantBanner()}
                    <p>取得當前租戶的個案 (Case) 表單欄位配置，用於動態生成表單</p>
                    <button class="btn btn-primary" onclick="executeGetCaseFieldSchema()" ${!state.token ? 'disabled' : ''}>取得配置</button>
                `,
                execute: async () => {
                    const response = await fetch(`${BASE_URL}/api/v1/ui/field-schemas/case`, {
                        headers: {
                            'Authorization': `Bearer ${state.token}`
                        }
                    });

                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="response-card">
                        <h4>📋 ${data.tenant_id.toUpperCase()} - ${data.form_type.toUpperCase()} 表單配置</h4>
                        ${data.sections.map(section => `
                            <div style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #10b981;">
                                <h5 style="margin: 0 0 10px 0; color: #059669;">📌 ${section.title}</h5>
                                ${section.description ? `<p style="color: #6b7280; margin: 0 0 15px 0;">${section.description}</p>` : ''}
                                <div style="display: grid; gap: 12px;">
                                    ${section.fields.map(field => `
                                        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
                                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                                                <div>
                                                    <strong style="color: #111827;">${field.label}</strong>
                                                    ${field.required ? '<span style="color: #ef4444; margin-left: 4px;">*</span>' : ''}
                                                </div>
                                                <span style="background: #d1fae5; color: #059669; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${field.type}</span>
                                            </div>
                                            <div style="font-size: 13px; color: #6b7280;">
                                                <div><strong>Key:</strong> ${field.key}</div>
                                                ${field.placeholder ? `<div><strong>Placeholder:</strong> ${field.placeholder}</div>` : ''}
                                                ${field.help_text ? `<div><strong>說明:</strong> ${field.help_text}</div>` : ''}
                                                ${field.options ? `<div><strong>選項:</strong> ${field.options.join(', ')}</div>` : ''}
                                                ${field.default_value ? `<div><strong>預設值:</strong> ${field.default_value}</div>` : ''}
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `,
                renderResponse: (data) => `
                    <div class="response-card">
                        <h4>📋 ${data.tenant_id.toUpperCase()} - ${data.form_type.toUpperCase()} 表單配置</h4>
                        ${data.sections.map(section => `
                            <div style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #10b981;">
                                <h5 style="margin: 0 0 10px 0; color: #059669;">📌 ${section.title}</h5>
                                ${section.description ? `<p style="color: #6b7280; margin: 0 0 15px 0;">${section.description}</p>` : ''}
                                <div style="display: grid; gap: 12px;">
                                    ${section.fields.map(field => `
                                        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
                                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                                                <div>
                                                    <strong style="color: #111827;">${field.label}</strong>
                                                    ${field.required ? '<span style="color: #ef4444; margin-left: 4px;">*</span>' : ''}
                                                </div>
                                                <span style="background: #d1fae5; color: #059669; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${field.type}</span>
                                            </div>
                                            <div style="font-size: 13px; color: #6b7280;">
                                                <div><strong>Key:</strong> ${field.key}</div>
                                                ${field.placeholder ? `<div><strong>Placeholder:</strong> ${field.placeholder}</div>` : ''}
                                                ${field.help_text ? `<div><strong>說明:</strong> ${field.help_text}</div>` : ''}
                                                ${field.options ? `<div><strong>選項:</strong> ${field.options.join(', ')}</div>` : ''}
                                                ${field.default_value ? `<div><strong>預設值:</strong> ${field.default_value}</div>` : ''}
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `
            },
            'list-clients': {
                title: '列出個案',
                subtitle: 'GET /api/v1/clients',
                renderForm: () => `
                    ${renderTenantBanner()}
                    <div class="form-group">
                        <label>Search (optional)</label>
                        <input type="text" id="search" placeholder="搜尋姓名、代碼..." />
                    </div>
                    <button class="btn btn-primary" onclick="executeListClients()" ${!state.token ? 'disabled' : ''}>查詢個案</button>
                `,
                execute: async () => {
                    const search = document.getElementById('search').value;
                    const params = new URLSearchParams();
                    if (search) params.append('search', search);

                    const response = await fetch(`${BASE_URL}/api/v1/clients?${params}`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.clients = data.items;
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <h3>📋 個案列表 (共 ${data.total} 筆)</h3>
                    ${data.items.map(client => `
                        <div class="info-card">
                            <div class="info-row">
                                <span class="info-label">姓名</span>
                                <span class="info-value">${client.name}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">代碼</span>
                                <span class="info-value">${client.code}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">年齡</span>
                                <span class="info-value">${client.age || 'N/A'}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">建立時間</span>
                                <span class="info-value">${new Date(client.created_at).toLocaleString('zh-TW')}</span>
                            </div>
                        </div>
                    `).join('')}
                `
            },
            'create-client': {
                title: '建立客戶',
                subtitle: 'POST /api/v1/clients',
                init: async function() {
                    // Fetch client field schema
                    if (!state.clientFieldSchema) {
                        try {
                            const clientRes = await fetch(`${BASE_URL}/api/v1/ui/field-schemas/client`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });

                            if (clientRes.ok) {
                                state.clientFieldSchema = await clientRes.json();
                            }
                        } catch (error) {
                            console.error('Failed to fetch client schema:', error);
                        }
                    }
                },
                renderForm: () => {
                    if (!state.clientFieldSchema) {
                        return `<p>載入欄位配置中...</p>`;
                    }

                    let formHtml = renderTenantBanner();

                    // Render Client fields dynamically
                    const clientSchema = state.clientFieldSchema;

                    clientSchema.sections.forEach(section => {
                        formHtml += `<h4 style="margin: 20px 0 10px 0; color: #1e40af; border-bottom: 1px solid #dbeafe; padding-bottom: 6px;">${section.title}</h4>`;
                        if (section.description) {
                            formHtml += `<p style="color: #6b7280; font-size: 13px; margin-bottom: 15px;">${section.description}</p>`;
                        }

                        section.fields.forEach(field => {
                            const required = field.required ? ' *' : '';
                            const inputId = `client-${field.key}`;

                            formHtml += `<div class="form-group">`;
                            formHtml += `<label>${field.label}${required}</label>`;

                            if (field.type === 'textarea') {
                                formHtml += `<textarea id="${inputId}" placeholder="${field.placeholder || ''}" ${field.required ? 'required' : ''}></textarea>`;
                            } else if (field.type === 'single_select') {
                                formHtml += `<select id="${inputId}" ${field.required ? 'required' : ''}>`;
                                formHtml += `<option value="">請選擇</option>`;
                                field.options.forEach(opt => {
                                    formHtml += `<option value="${opt}">${opt}</option>`;
                                });
                                formHtml += `</select>`;
                            } else if (field.type === 'date') {
                                formHtml += `<input type="date" id="${inputId}" ${field.required ? 'required' : ''} />`;
                            } else if (field.type === 'email') {
                                formHtml += `<input type="email" id="${inputId}" placeholder="${field.placeholder || ''}" ${field.required ? 'required' : ''} />`;
                            } else if (field.type === 'phone') {
                                formHtml += `<input type="tel" id="${inputId}" placeholder="${field.placeholder || ''}" ${field.required ? 'required' : ''} />`;
                            } else {
                                formHtml += `<input type="text" id="${inputId}" placeholder="${field.placeholder || ''}" ${field.required ? 'required' : ''} />`;
                            }

                            if (field.help_text) {
                                formHtml += `<small style="color: #6b7280; font-size: 12px;">${field.help_text}</small>`;
                            }
                            formHtml += `</div>`;
                        });
                    });

                    formHtml += `<div style="display: flex; gap: 10px; margin-top: 24px;">`;
                    formHtml += `<button class="btn btn-primary" onclick="executeCreateClient()" ${!state.token ? 'disabled' : ''}>建立客戶</button>`;
                    formHtml += `<button class="btn btn-secondary" onclick="quickFillClient()" ${!state.token ? 'disabled' : ''} style="background: #6366f1;">🎲 快速填入測試資料</button>`;
                    formHtml += `</div>`;

                    return formHtml;
                },
                renderForm_old: () => `
                    <div class="form-group">
                        <label>姓名 *</label>
                        <input type="text" id="client-name" placeholder="請輸入姓名" required />
                    </div>
                    <div class="form-group">
                        <label>暱稱</label>
                        <input type="text" id="client-nickname" placeholder="請輸入暱稱" />
                    </div>
                    <div class="form-group">
                        <label>出生日期 (必填，用於自動計算年齡)</label>
                        <input type="date" id="client-birth-date" required />
                    </div>
                    <div class="form-group">
                        <label>性別</label>
                        <select id="client-gender">
                            <option value="">請選擇</option>
                            <option value="male">男性</option>
                            <option value="female">女性</option>
                            <option value="other">其他</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>職業</label>
                        <input type="text" id="client-occupation" placeholder="請輸入職業" />
                    </div>
                    <div class="form-group">
                        <label>學歷</label>
                        <input type="text" id="client-education" placeholder="例如：國立OO大學" />
                    </div>
                    <div class="form-group">
                        <label>現居地</label>
                        <input type="text" id="client-location" placeholder="例如：台北市" />
                    </div>
                    <div class="form-group">
                        <label>經濟狀況</label>
                        <input type="text" id="client-economic-status" placeholder="例如：可負擔日常及進修" />
                    </div>
                    <div class="form-group">
                        <label>家庭關係</label>
                        <textarea id="client-family-relations" rows="2" placeholder="例如：父母支持升學；與哥哥同住"></textarea>
                    </div>
                    <div class="form-group">
                        <label>其他重要資訊</label>
                        <textarea id="client-other-info" rows="2" placeholder="例如：近半年考慮轉職；對職涯方向感到迷惘"></textarea>
                    </div>
                    <div class="form-group">
                        <label>備註 (私人)</label>
                        <textarea id="client-notes" rows="2" placeholder="諮詢師私人備註"></textarea>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-primary" onclick="executeCreateClient()" ${!state.token ? 'disabled' : ''}>建立個案</button>
                        <button class="btn btn-secondary" onclick="quickFillRandomClient()" ${!state.token ? 'disabled' : ''} style="background: #6366f1;">🎲 快速填入測試資料</button>
                    </div>
                `,
                execute: async () => {
                    if (!state.clientFieldSchema) {
                        throw new Error('Client schema not loaded');
                    }

                    // Collect Client data from form
                    const clientData = {};
                    state.clientFieldSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const inputId = `client-${field.key}`;
                            const element = document.getElementById(inputId);
                            if (element && element.value) {
                                clientData[field.key] = element.value;
                            }
                        });
                    });

                    // Remove empty values
                    Object.keys(clientData).forEach(key => {
                        if (clientData[key] === '' || clientData[key] === undefined) {
                            delete clientData[key];
                        }
                    });

                    // Create Client
                    const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(clientData)
                    });
                    const data = await response.json();

                    if (response.ok) {
                        state.currentClient = data;
                        // Add to clients list
                        state.clients = state.clients || [];
                        state.clients.push(data);
                    }

                    return { response, data };
                },
                renderPreview: (data) => {
                    return `
                    <div class="info-card">
                        <h3>✅ 客戶建立成功</h3>
                        <div class="info-row">
                            <span class="info-label">客戶 ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">姓名</span>
                            <span class="info-value">${data.name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">代碼</span>
                            <span class="info-value">${data.code}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Email</span>
                            <span class="info-value">${data.email || 'N/A'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">電話</span>
                            <span class="info-value">${data.phone || 'N/A'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">建立時間</span>
                            <span class="info-value">${new Date(data.created_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                `;
                }
            },
            'view-client': {
                title: '查看個案',
                subtitle: 'GET /api/v1/clients/{id}',
                init: async () => {
                    // Load field schemas if not already loaded
                    if (!state.clientFieldSchema || !state.caseFieldSchema) {
                        const [clientRes, caseRes] = await Promise.all([
                            fetch(`${BASE_URL}/api/v1/ui/field-schemas/client`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            }),
                            fetch(`${BASE_URL}/api/v1/ui/field-schemas/case`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            })
                        ]);
                        if (clientRes.ok) state.clientFieldSchema = await clientRes.json();
                        if (caseRes.ok) state.caseFieldSchema = await caseRes.json();
                    }

                    // Refresh client list before showing view form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.clients = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['view-client'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh client list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const clientOptions = state.clients.map(c =>
                        `<option value="${c.id}">${c.name} (${c.code})</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="form-group">
                            <label>選擇個案 *</label>
                            <select id="view-client-id">
                                ${state.currentClient ? `<option value="${state.currentClient.id}" selected>${state.currentClient.name} (${state.currentClient.code})</option>` : ''}
                                ${clientOptions}
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeViewClient()" ${!state.token || state.clients.length === 0 ? 'disabled' : ''}>查看個案</button>
                    `;
                },
                execute: async () => {
                    const clientId = document.getElementById('view-client-id').value;

                    // Fetch client data and their cases in parallel
                    const [clientResponse, casesResponse] = await Promise.all([
                        fetch(`${BASE_URL}/api/v1/clients/${clientId}`, {
                            method: 'GET',
                            headers: { 'Authorization': `Bearer ${state.token}` }
                        }),
                        fetch(`${BASE_URL}/api/v1/cases?client_id=${clientId}`, {
                            method: 'GET',
                            headers: { 'Authorization': `Bearer ${state.token}` }
                        })
                    ]);

                    const clientData = await clientResponse.json();
                    let casesData = null;

                    if (casesResponse.ok) {
                        casesData = await casesResponse.json();
                    }

                    if (clientResponse.ok) {
                        state.currentClient = clientData;
                    }

                    return {
                        response: clientResponse,
                        data: {
                            client: clientData,
                            cases: casesData
                        }
                    };
                },
                renderPreview: (data) => {
                    if (!state.clientFieldSchema || !state.caseFieldSchema) {
                        return '<div class="info-card"><p>載入欄位配置中...</p></div>';
                    }

                    const client = data.client;
                    const cases = data.cases;

                    let html = '<div class="info-card">';

                    // Render client sections dynamically
                    state.clientFieldSchema.sections.forEach(section => {
                        html += `
                            <h3 style="color: #3b82f6; margin-top: ${section.order > 1 ? '20px' : '0'}; margin-bottom: 12px;">
                                👤 ${section.title}
                            </h3>
                        `;

                        section.fields.forEach(field => {
                            let value = client[field.key];

                            // Format value based on type
                            if (value === null || value === undefined || value === '') {
                                value = 'N/A';
                            } else if (field.type === 'date' && value) {
                                value = new Date(value).toLocaleDateString('zh-TW');
                            } else if (Array.isArray(value)) {
                                value = value.join(', ');
                            } else if (typeof value === 'object') {
                                value = JSON.stringify(value);
                            }

                            html += `
                                <div class="info-row">
                                    <span class="info-label">${field.label}</span>
                                    <span class="info-value">${value}</span>
                                </div>
                            `;
                        });
                    });

                    // Show metadata
                    html += `
                        <h3 style="color: #6b7280; margin-top: 20px; margin-bottom: 12px;">ℹ️ 系統資訊</h3>
                        <div class="info-row">
                            <span class="info-label">客戶 ID</span>
                            <span class="info-value" style="font-size: 11px;">${client.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">代碼</span>
                            <span class="info-value">${client.code}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">建立時間</span>
                            <span class="info-value">${new Date(client.created_at).toLocaleString('zh-TW')}</span>
                        </div>
                    `;

                    html += '</div>';

                    // Render cases if available
                    if (cases && cases.items && cases.items.length > 0) {
                        cases.items.forEach((caseItem, index) => {
                            html += '<div class="info-card" style="margin-top: 16px;">';

                            state.caseFieldSchema.sections.forEach(section => {
                                html += `
                                    <h3 style="color: #10b981; margin-top: ${section.order > 1 ? '20px' : '0'}; margin-bottom: 12px;">
                                        📋 ${section.title} ${cases.items.length > 1 ? `#${index + 1}` : ''}
                                    </h3>
                                `;

                                section.fields.forEach(field => {
                                    let value = caseItem[field.key];

                                    // Format value based on type
                                    if (value === null || value === undefined || value === '') {
                                        value = 'N/A';
                                    } else if (field.type === 'date' && value) {
                                        value = new Date(value).toLocaleDateString('zh-TW');
                                    } else if (Array.isArray(value)) {
                                        value = value.join(', ');
                                    } else if (typeof value === 'object') {
                                        value = JSON.stringify(value);
                                    }

                                    html += `
                                        <div class="info-row">
                                            <span class="info-label">${field.label}</span>
                                            <span class="info-value">${value}</span>
                                        </div>
                                    `;
                                });
                            });

                            // Case metadata
                            html += `
                                <h3 style="color: #6b7280; margin-top: 20px; margin-bottom: 12px;">ℹ️ Case 系統資訊</h3>
                                <div class="info-row">
                                    <span class="info-label">Case ID</span>
                                    <span class="info-value" style="font-size: 11px;">${caseItem.id}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">建立時間</span>
                                    <span class="info-value">${new Date(caseItem.created_at).toLocaleString('zh-TW')}</span>
                                </div>
                            `;

                            html += '</div>';
                        });
                    } else {
                        html += `
                            <div class="info-card" style="margin-top: 16px;">
                                <h3 style="color: #6b7280;">📋 關聯的 Cases</h3>
                                <p style="color: #6b7280; font-size: 14px; margin-top: 12px;">此客戶尚無 Case 記錄</p>
                            </div>
                        `;
                    }

                    return html;
                }
            },
            'client-timeline': {
                title: '查看個案歷程',
                subtitle: 'GET /api/v1/sessions/timeline',
                init: async () => {
                    // Refresh client list before showing timeline form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.clients = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['client-timeline'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh client list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const clientOptions = state.clients.map(c =>
                        `<option value="${c.id}">${c.name} (${c.code})</option>`
                    ).join('');

                    return `
                        <div class="form-group">
                            <label>選擇個案 *</label>
                            <select id="timeline-client-id">
                                ${state.currentClient ? `<option value="${state.currentClient.id}" selected>${state.currentClient.name} (${state.currentClient.code})</option>` : ''}
                                ${clientOptions}
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeClientTimeline()" ${!state.token || state.clients.length === 0 ? 'disabled' : ''}>查看歷程</button>
                    `;
                },
                execute: async () => {
                    const clientId = document.getElementById('timeline-client-id').value;

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/timeline?client_id=${clientId}`, {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${state.token}`
                        }
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => {
                    if (!data.sessions || data.sessions.length === 0) {
                        return `
                            <div class="info-card">
                                <h3>📅 個案歷程</h3>
                                <p style="color: #6b7280; font-size: 14px; margin-top: 12px;">此個案尚無諮詢記錄</p>
                            </div>
                        `;
                    }

                    return `
                        <div class="info-card">
                            <h3>📅 個案歷程 - ${data.client_name} (${data.client_code})</h3>
                            <div style="margin-top: 16px;">
                                <p style="color: #374151; font-size: 14px; margin-bottom: 12px;">共 ${data.total_sessions} 次諮詢</p>
                                ${data.sessions.map(session => {
                                    // Remove surrounding quotes from summary if present
                                    let cleanSummary = session.summary;
                                    if (cleanSummary && cleanSummary.startsWith('"') && cleanSummary.endsWith('"')) {
                                        cleanSummary = cleanSummary.slice(1, -1);
                                    }
                                    // Also handle escaped quotes
                                    if (cleanSummary) {
                                        cleanSummary = cleanSummary.replace(/\\"/g, '"');
                                    }

                                    return `
                                    <div style="border-left: 3px solid #3b82f6; padding-left: 12px; margin-bottom: 20px;">
                                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                                            <div style="font-weight: 600; color: #1f2937; font-size: 15px;">
                                                ● 第${session.session_number}次 | ${session.date} ${session.time_range || ''}
                                            </div>
                                            ${session.has_report ? `
                                                <span style="background: #10b981; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; white-space: nowrap;">
                                                    已出報告
                                                </span>
                                            ` : `
                                                <span style="background: #9ca3af; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; white-space: nowrap;">
                                                    未出報告
                                                </span>
                                            `}
                                        </div>
                                        ${cleanSummary ? `
                                            <div style="font-size: 14px; color: #374151; line-height: 1.6;">
                                                ${cleanSummary}
                                            </div>
                                        ` : ''}
                                    </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    `;
                }
            },
            'get-reflection': {
                title: '查看反思',
                subtitle: 'GET /api/v1/sessions/{id}/reflection',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                                document.getElementById('action-form').innerHTML = steps['get-reflection'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh session list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || '未知'} - 第 ${s.session_number} 次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="form-group">
                            <label>選擇會談記錄 *</label>
                            <select id="reflection-session-id">
                                ${sessionOptions}
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeGetReflection()" ${!state.token || !state.sessions?.length ? 'disabled' : ''}>查看反思</button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('reflection-session-id').value;
                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/reflection`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>💭 諮詢師反思</h3>
                        <div class="info-row">
                            <span class="info-label">Session ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.session_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                    ${data.reflection && Object.keys(data.reflection).length > 0 ? `
                        <div class="info-card">
                            <h4>反思內容</h4>
                            ${data.reflection.working_with_client ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">我和這個人工作的感受是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.working_with_client}</p>
                                </div>
                            ` : ''}
                            ${data.reflection.feeling_source ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">這個感受的原因是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.feeling_source}</p>
                                </div>
                            ` : ''}
                            ${data.reflection.current_challenges ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">目前的困難／想更深入的地方是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.current_challenges}</p>
                                </div>
                            ` : ''}
                            ${data.reflection.supervision_topics ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">我會想找督導討論的問題是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.supervision_topics}</p>
                                </div>
                            ` : ''}
                        </div>
                    ` : '<div class="info-card"><p style="color: #6b7280;">此會談尚無反思記錄</p></div>'}
                `
            },
            'update-reflection': {
                title: '更新反思',
                subtitle: 'PUT /api/v1/sessions/{id}/reflection',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                                document.getElementById('action-form').innerHTML = steps['update-reflection'].renderForm();
                                setTimeout(() => loadReflectionForUpdate(), 100);
                            }
                        } catch (error) {
                            console.error('Failed to refresh session list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || '未知'} - 第 ${s.session_number} 次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="form-group">
                            <label>選擇會談記錄 *</label>
                            <select id="update-reflection-session-id" onchange="loadReflectionForUpdate()">
                                ${sessionOptions}
                            </select>
                        </div>
                        <div class="info-card" style="background: #eff6ff; border-color: #3b82f6;">
                            <h4 style="color: #1e40af; margin-bottom: 12px;">諮詢師反思</h4>
                            <div class="form-group">
                                <label>我和這個人工作的感受是？</label>
                                <textarea id="put-reflection-working" placeholder="例如：整體過程流暢輕鬆，逐漸贏得信任..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>這個感受的原因是？</label>
                                <textarea id="put-reflection-source" placeholder="例如：個案從緊張到逐步放鬆，願意開放心態分享更多..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>目前的困難／想更深入的地方是？</label>
                                <textarea id="put-reflection-challenges" placeholder="例如：當肯定個案時，仍會有自我懷疑反應..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>我會想找督導討論的問題是？</label>
                                <textarea id="put-reflection-supervision" placeholder="例如：如何在支持與挑戰間拿捏節奏..." rows="2"></textarea>
                            </div>
                        </div>
                        <button class="btn btn-primary" onclick="executeUpdateReflection()" ${!state.token || !state.sessions?.length ? 'disabled' : ''}>更新反思</button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('update-reflection-session-id').value;
                    const requestBody = {};

                    const working = document.getElementById('put-reflection-working').value;
                    const source = document.getElementById('put-reflection-source').value;
                    const challenges = document.getElementById('put-reflection-challenges').value;
                    const supervision = document.getElementById('put-reflection-supervision').value;

                    if (working) requestBody.working_with_client = working;
                    if (source) requestBody.feeling_source = source;
                    if (challenges) requestBody.current_challenges = challenges;
                    if (supervision) requestBody.supervision_topics = supervision;

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/reflection`, {
                        method: 'PUT',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestBody)
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="border-color: #10b981;">
                        <h3 style="color: #10b981;">✅ 反思更新成功</h3>
                        <div class="info-row">
                            <span class="info-label">Session ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.session_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                `
            },
            'append-recording': {
                title: '🎙️ Append 錄音片段',
                subtitle: 'POST /api/v1/sessions/{id}/recordings/append',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                                document.getElementById('action-form').innerHTML = steps['append-recording'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh session list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || '未知'} - 第 ${s.session_number} 次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="info-card" style="background: #fef3c7; border-color: #f59e0b;">
                            <h4 style="color: #92400e; margin: 0 0 8px 0;">📱 iOS 友善 API</h4>
                            <p style="font-size: 13px; color: #92400e; line-height: 1.5;">
                                此 API 為 iOS 設計，簡化錄音片段添加流程：<br>
                                • 自動計算 segment_number<br>
                                • 自動聚合所有片段的 transcript_text<br>
                                • 支持會談中斷後繼續錄音
                            </p>
                        </div>
                        <div class="form-group">
                            <label>選擇會談記錄 *</label>
                            <select id="append-session-id">
                                ${sessionOptions}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>開始時間 *</label>
                            <input type="text" id="append-start-time" placeholder="2025-01-15 10:00 或 2025-01-15T10:00:00" />
                            <small style="color: #6b7280; font-size: 12px;">格式：YYYY-MM-DD HH:MM 或 ISO format</small>
                        </div>
                        <div class="form-group">
                            <label>結束時間 *</label>
                            <input type="text" id="append-end-time" placeholder="2025-01-15 10:30 或 2025-01-15T10:30:00" />
                            <small style="color: #6b7280; font-size: 12px;">格式：YYYY-MM-DD HH:MM 或 ISO format</small>
                        </div>
                        <div class="form-group">
                            <label>錄音時長（秒） *</label>
                            <input type="number" id="append-duration" placeholder="1800" />
                            <small style="color: #6b7280; font-size: 12px;">例如：30分鐘 = 1800秒</small>
                        </div>
                        <div class="form-group">
                            <label>逐字稿內容 *</label>
                            <textarea id="append-transcript" placeholder="此片段的逐字稿內容..." rows="8"></textarea>
                        </div>
                        <div class="form-group">
                            <label>脫敏逐字稿（選填）</label>
                            <textarea id="append-transcript-sanitized" placeholder="如不填，系統將使用原始逐字稿..." rows="5"></textarea>
                            <small style="color: #6b7280; font-size: 12px;">💡 若需隱藏個人資訊，請提供脫敏版本</small>
                        </div>
                        <button class="btn btn-primary" onclick="executeAppendRecording()" ${!state.token || !state.sessions?.length ? 'disabled' : ''}>
                            🎙️ Append 錄音片段
                        </button>
                        <button class="btn btn-secondary" onclick="quickFillAppendRecording()" ${!state.token || !state.sessions?.length ? 'disabled' : ''} style="background: #6366f1; margin-top: 8px;">
                            🎲 快速填入測試資料
                        </button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('append-session-id').value;
                    const requestBody = {
                        start_time: document.getElementById('append-start-time').value,
                        end_time: document.getElementById('append-end-time').value,
                        duration_seconds: parseInt(document.getElementById('append-duration').value),
                        transcript_text: document.getElementById('append-transcript').value
                    };

                    const sanitized = document.getElementById('append-transcript-sanitized').value;
                    if (sanitized) {
                        requestBody.transcript_sanitized = sanitized;
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/recordings/append`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestBody)
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="border-color: #10b981;">
                        <h3 style="color: #10b981;">✅ 錄音片段已成功 Append</h3>
                        <div class="info-row">
                            <span class="info-label">Session ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.session_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Segment Number</span>
                            <span class="info-value" style="color: #10b981; font-weight: 600;">#${data.recording_added.segment_number}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">總片段數</span>
                            <span class="info-value">${data.total_recordings} 個</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">錄音時長</span>
                            <span class="info-value">${data.recording_added.duration_seconds} 秒 (${Math.round(data.recording_added.duration_seconds / 60)} 分鐘)</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                    <div class="info-card">
                        <h4>📝 新增片段內容</h4>
                        <div style="background: #f3f4f6; padding: 12px; border-radius: 6px; margin-top: 8px;">
                            <p style="font-size: 13px; line-height: 1.6; white-space: pre-wrap;">${data.recording_added.transcript_text}</p>
                        </div>
                    </div>
                    <div class="info-card">
                        <h4>📄 完整逐字稿（已自動聚合）</h4>
                        <small style="color: #6b7280; font-size: 12px;">包含所有 ${data.total_recordings} 個片段</small>
                        <div style="background: #f3f4f6; padding: 12px; border-radius: 6px; margin-top: 8px; max-height: 300px; overflow-y: auto;">
                            <p style="font-size: 13px; line-height: 1.6; white-space: pre-wrap;">${data.transcript_text}</p>
                        </div>
                    </div>
                `
            },
            'analyze-keywords': {
                title: '🔍 即時關鍵字分析',
                subtitle: 'POST /api/v1/sessions/{session_id}/analyze-keywords',
                init: async () => {
                    if (state.token) {
                        try {
                            // Fetch sessions for selection
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });

                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                            }

                            document.getElementById('action-form').innerHTML = steps['analyze-keywords'].renderForm();
                        } catch (error) {
                            console.error('Failed to load sessions:', error);
                        }
                    }
                },
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || '未知'} - 第 ${s.session_number} 次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="info-card" style="background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%); border-color: #667eea;">
                            <h4 style="color: #5145cd; margin: 0 0 8px 0;">🔍 即時關鍵字分析 (RESTful)</h4>
                            <p style="color: #6366f1; font-size: 13px; margin: 0;">
                                從逐字稿片段即時提取關鍵字，不儲存任何資料<br/>
                                自動從會談載入案主背景、案例目標和會談資訊作為 AI 分析脈絡<br/>
                                <strong>包含諮詢師洞見</strong>：AI 會根據背景提供關注重點建議
                            </p>
                        </div>

                        <div class="form-group">
                            <label>選擇會談 *</label>
                            <select id="analyze-session-id">
                                ${sessionOptions}
                            </select>
                        </div>

                        <div class="form-group">
                            <label>逐字稿片段 *</label>
                            <textarea id="analyze-transcript" placeholder="輸入或貼上要分析的逐字稿片段..." rows="8"></textarea>
                            <small style="color: #6b7280; font-size: 12px;">💡 可即時傳送部分錄音的逐字稿進行分析</small>
                        </div>

                        <button class="btn btn-primary" onclick="executeAnalyzeKeywords()" ${!state.token || !state.sessions?.length ? 'disabled' : ''}>
                            🔍 分析關鍵字
                        </button>
                        <button class="btn btn-secondary" onclick="quickFillAnalyzeKeywords()" ${!state.token ? 'disabled' : ''} style="background: #6366f1; margin-top: 8px;">
                            🎲 快速填入測試資料
                        </button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('analyze-session-id').value;
                    const transcript = document.getElementById('analyze-transcript').value;

                    const requestBody = {
                        transcript_segment: transcript
                    };

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/analyze-keywords`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestBody)
                    });

                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%); border-color: #667eea;">
                        <h3 style="color: #5145cd;">🔍 關鍵字分析結果</h3>

                        <div class="info-row">
                            <span class="info-label">信心分數</span>
                            <span class="info-value">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 8px;">
                                        <div style="width: ${data.confidence * 100}%; background: linear-gradient(90deg, #667eea, #764ba2); height: 100%; border-radius: 4px;"></div>
                                    </div>
                                    <span style="font-weight: 600; color: #5145cd;">${(data.confidence * 100).toFixed(0)}%</span>
                                </div>
                            </span>
                        </div>

                        <div style="margin-top: 16px;">
                            <h4 style="color: #374151; margin-bottom: 8px;">🏷️ 提取的關鍵字</h4>
                            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                                ${data.keywords.map(keyword => `
                                    <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 4px 12px; border-radius: 16px; font-size: 13px;">
                                        ${keyword}
                                    </span>
                                `).join('')}
                            </div>
                        </div>

                        ${data.categories && data.categories.length > 0 ? `
                            <div style="margin-top: 16px;">
                                <h4 style="color: #374151; margin-bottom: 8px;">📂 分類</h4>
                                <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                                    ${data.categories.map(category => `
                                        <span style="background: #f0f4ff; color: #5145cd; padding: 4px 12px; border-radius: 8px; font-size: 13px; border: 1px solid #c7d2fe;">
                                            ${category}
                                        </span>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${data.counselor_insights ? `
                            <div style="margin-top: 16px;">
                                <h4 style="color: #374151; margin-bottom: 8px;">💡 諮詢師洞見</h4>
                                <div class="info-card" style="background: #fef3c7; border-color: #fbbf24;">
                                    <p style="color: #92400e; font-size: 13px; margin: 0; line-height: 1.6;">
                                        ${data.counselor_insights}
                                    </p>
                                </div>
                            </div>
                        ` : ''}

                        <div class="info-card" style="background: #d1f4e0; border-color: #10b981; margin-top: 16px;">
                            <p style="color: #065f46; font-size: 12px; margin: 0;">
                                ✅ 此分析結果已自動儲存到資料庫，可使用「📋 查看分析記錄」功能查看歷史記錄
                            </p>
                        </div>
                    </div>
                `
            },
            'update-client': {
                title: '更新個案',
                subtitle: 'PATCH /api/v1/clients/{id} + PATCH /api/v1/cases/{id}',
                init: async () => {
                    // Load field schemas if not already loaded
                    if (!state.clientFieldSchema || !state.caseFieldSchema) {
                        const [clientRes, caseRes] = await Promise.all([
                            fetch(`${BASE_URL}/api/v1/ui/field-schemas/client`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            }),
                            fetch(`${BASE_URL}/api/v1/ui/field-schemas/case`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            })
                        ]);
                        if (clientRes.ok) state.clientFieldSchema = await clientRes.json();
                        if (caseRes.ok) state.caseFieldSchema = await caseRes.json();
                    }

                    // Refresh client list before showing update form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.clients = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['update-client'].renderForm();
                                // Load data for first/current client
                                setTimeout(() => loadClientDataForUpdate(), 100);
                            }
                        } catch (error) {
                            console.error('Failed to refresh client list:', error);
                        }
                    }
                },
                renderForm: () => {
                    if (!state.clientFieldSchema) {
                        return `${renderTenantBanner()}<p>載入欄位配置中...</p>`;
                    }

                    // Filter out currentClient from the list to avoid duplicates
                    const filteredClients = state.currentClient
                        ? state.clients.filter(c => c.id !== state.currentClient.id)
                        : state.clients;

                    const clientOptions = filteredClients.map(c =>
                        `<option value="${c.id}">${c.name} (${c.code})</option>`
                    ).join('');

                    let formHtml = `
                        ${renderTenantBanner()}
                        <div class="form-group">
                            <label>選擇個案 *</label>
                            <select id="update-client-id" onchange="loadClientDataForUpdate()">
                                ${state.currentClient ? `<option value="${state.currentClient.id}" selected>${state.currentClient.name} (${state.currentClient.code})</option>` : ''}
                                ${clientOptions}
                            </select>
                        </div>
                    `;

                    // Render dynamic fields from schema
                    state.clientFieldSchema.sections.forEach(section => {
                        formHtml += `<h4 style="margin: 20px 0 10px 0; color: #1e40af; border-bottom: 1px solid #dbeafe; padding-bottom: 6px;">${section.title}</h4>`;

                        section.fields.forEach(field => {
                            const inputId = `update-client-${field.key}`;
                            formHtml += `<div class="form-group">`;
                            formHtml += `<label>${field.label}</label>`;

                            if (field.type === 'textarea') {
                                formHtml += `<textarea id="${inputId}" placeholder="${field.placeholder || ''}"></textarea>`;
                            } else if (field.type === 'single_select') {
                                formHtml += `<select id="${inputId}">`;
                                formHtml += `<option value="">請選擇</option>`;
                                field.options.forEach(opt => {
                                    formHtml += `<option value="${opt}">${opt}</option>`;
                                });
                                formHtml += `</select>`;
                            } else if (field.type === 'date') {
                                formHtml += `<input type="date" id="${inputId}" />`;
                            } else if (field.type === 'email') {
                                formHtml += `<input type="email" id="${inputId}" placeholder="${field.placeholder || ''}" />`;
                            } else if (field.type === 'phone') {
                                formHtml += `<input type="tel" id="${inputId}" placeholder="${field.placeholder || ''}" />`;
                            } else {
                                formHtml += `<input type="text" id="${inputId}" placeholder="${field.placeholder || ''}" />`;
                            }

                            if (field.help_text) {
                                formHtml += `<small style="color: #6b7280; font-size: 12px;">${field.help_text}</small>`;
                            }
                            formHtml += `</div>`;
                        });
                    });

                    formHtml += `<button class="btn btn-primary" onclick="executeUpdateClient()" ${!state.token || (!state.currentClient && state.clients.length === 0) ? 'disabled' : ''}>更新個案</button>`;

                    return formHtml;
                },
                execute: async () => {
                    if (!state.clientFieldSchema) {
                        throw new Error('Client schema not loaded');
                    }

                    const clientId = document.getElementById('update-client-id').value;
                    const updateData = {};

                    // Collect data from dynamic fields
                    state.clientFieldSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const inputId = `update-client-${field.key}`;
                            const element = document.getElementById(inputId);
                            if (element && element.value) {
                                updateData[field.key] = element.value;
                            }
                        });
                    });

                    // Remove empty values
                    Object.keys(updateData).forEach(key => {
                        if (updateData[key] === '' || updateData[key] === undefined) {
                            delete updateData[key];
                        }
                    });

                    const response = await fetch(`${BASE_URL}/api/v1/clients/${clientId}`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(updateData)
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.currentClient = data;
                    }
                    return { response, data };
                },
                renderPreview: (data) => {
                    if (!state.clientFieldSchema) {
                        return `<div class="info-card"><h3>✅ 個案更新成功</h3></div>`;
                    }

                    let html = `<div class="info-card"><h3>✅ 個案更新成功</h3>`;

                    // Display basic info
                    html += `
                        <div class="info-row">
                            <span class="info-label">ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">代碼</span>
                            <span class="info-value">${data.code}</span>
                        </div>
                    `;

                    // Dynamically display fields from schema
                    state.clientFieldSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const value = data[field.key];
                            if (value !== undefined && value !== null && value !== '') {
                                const displayValue = Array.isArray(value) ? value.join(', ') : value;
                                html += `
                                    <div class="info-row">
                                        <span class="info-label">${field.label}</span>
                                        <span class="info-value">${displayValue}</span>
                                    </div>
                                `;
                            }
                        });
                    });

                    html += `
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                    `;

                    html += `</div>`;
                    return html;
                }
            },
            'delete-client': {
                title: '刪除個案',
                subtitle: 'DELETE /api/v1/clients/{id}',
                init: async () => {
                    // Refresh client list before showing delete form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.clients = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['delete-client'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh client list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const clientOptions = state.clients.map(c =>
                        `<option value="${c.id}">${c.name} (${c.code})</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="form-group">
                            <label>選擇要刪除的個案 *</label>
                            <select id="delete-client-id">
                                ${clientOptions}
                            </select>
                        </div>
                        <div class="info-card" style="background: #fee2e2; border-color: #ef4444;">
                            <p style="color: #991b1b; font-size: 13px;">⚠️ 警告：刪除個案後無法復原!</p>
                        </div>
                        <button class="btn btn-primary" onclick="executeDeleteClient()" ${!state.token || state.clients.length === 0 ? 'disabled' : ''} style="background: #ef4444;">刪除個案</button>
                    `;
                },
                execute: async () => {
                    const clientId = document.getElementById('delete-client-id').value;

                    const response = await fetch(`${BASE_URL}/api/v1/clients/${clientId}`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${state.token}`
                        }
                    });

                    // DELETE returns 204 No Content, no JSON to parse
                    const data = response.status === 204 ? { success: true, message: '個案已刪除' } : await response.json();

                    // Remove deleted client from state
                    if (response.status === 204) {
                        state.clients = state.clients.filter(c => c.id !== clientId);
                        if (state.currentClient?.id === clientId) {
                            state.currentClient = null;
                        }
                        // Refresh the dropdown list
                        document.getElementById('action-form').innerHTML = steps['delete-client'].renderForm();
                    }

                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="border-color: #10b981;">
                        <h3 style="color: #10b981;">✅ 個案刪除成功</h3>
                        <p style="color: #065f46; font-size: 14px; margin-top: 12px;">該個案已從系統中移除</p>
                    </div>
                `
            },
            'list-cases': {
                title: '列出個案',
                subtitle: 'GET /api/v1/cases',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/cases`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.cases = data.items;
                            }
                        } catch (error) {
                            console.error('Failed to fetch cases:', error);
                        }
                    }
                },
                renderForm: () => `
                    ${renderTenantBanner()}
                    <div class="form-group">
                        <label>篩選個案 ID（選填）</label>
                        <select id="list-cases-client-id">
                            <option value="">全部個案</option>
                            ${state.clients.map(c => `<option value="${c.id}">${c.name} (${c.code})</option>`).join('')}
                        </select>
                    </div>
                    <button class="btn btn-primary" onclick="executeStep('list-cases')" ${!state.token ? 'disabled' : ''}>查詢個案列表</button>
                `,
                execute: async () => {
                    const clientId = document.getElementById('list-cases-client-id').value;
                    const url = clientId
                        ? `${BASE_URL}/api/v1/cases?client_id=${clientId}`
                        : `${BASE_URL}/api/v1/cases`;

                    const response = await fetch(url, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.cases = data.items;
                    }
                    return { response, data };
                },
                renderPreview: (data) => {
                    let html = `<div class="info-card"><h3>📋 共 ${data.total} 個個案</h3>`;
                    data.items.forEach(caseItem => {
                        html += `
                            <div class="info-row">
                                <span class="info-label">個案編號</span>
                                <span class="info-value">${caseItem.case_number}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">狀態</span>
                                <span class="info-value">${caseItem.status}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">摘要</span>
                                <span class="info-value">${caseItem.summary || '無'}</span>
                            </div>
                            <hr style="margin: 12px 0; border: none; border-top: 1px solid #e5e7eb;">
                        `;
                    });
                    html += `</div>`;
                    return html;
                }
            },
            'create-case': {
                title: '建立個案',
                subtitle: 'POST /api/v1/cases',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.clients = data.items;
                            }
                        } catch (error) {
                            console.error('Failed to fetch clients:', error);
                        }
                    }
                },
                renderForm: () => `
                    ${renderTenantBanner()}
                    <div class="form-group">
                        <label>選擇客戶 *</label>
                        <select id="create-case-client-id">
                            ${state.clients.map(c => `<option value="${c.id}">${c.name} (${c.code})</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>狀態</label>
                        <select id="create-case-status">
                            <option value="active">Active</option>
                            <option value="completed">Completed</option>
                            <option value="suspended">Suspended</option>
                            <option value="referred">Referred</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>摘要</label>
                        <textarea id="create-case-summary" rows="3" placeholder="個案摘要"></textarea>
                    </div>
                    <div class="form-group">
                        <label>目標</label>
                        <textarea id="create-case-goals" rows="3" placeholder="諮詢目標"></textarea>
                    </div>
                    <div class="form-group">
                        <label>問題描述</label>
                        <textarea id="create-case-problem" rows="3" placeholder="諮詢目的或問題敘述"></textarea>
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 24px;">
                        <button class="btn btn-primary" onclick="executeStep('create-case')" ${!state.token || state.clients.length === 0 ? 'disabled' : ''}>建立個案</button>
                        <button class="btn btn-secondary" onclick="quickFillCase()" ${!state.token || state.clients.length === 0 ? 'disabled' : ''} style="background: #6366f1;">🎲 快速填入測試資料</button>
                    </div>
                `,
                execute: async () => {
                    const caseData = {
                        client_id: document.getElementById('create-case-client-id').value,
                        status: document.getElementById('create-case-status').value,
                        summary: document.getElementById('create-case-summary').value || null,
                        goals: document.getElementById('create-case-goals').value || null,
                        problem_description: document.getElementById('create-case-problem').value || null
                    };

                    const response = await fetch(`${BASE_URL}/api/v1/cases`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(caseData)
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>✅ 個案建立成功</h3>
                        <div class="info-row">
                            <span class="info-label">個案編號</span>
                            <span class="info-value">${data.case_number}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">狀態</span>
                            <span class="info-value">${data.status}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">摘要</span>
                            <span class="info-value">${data.summary || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">目標</span>
                            <span class="info-value">${data.goals || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">問題描述</span>
                            <span class="info-value">${data.problem_description || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">建立時間</span>
                            <span class="info-value">${new Date(data.created_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                `
            },
            'view-case': {
                title: '查看個案',
                subtitle: 'GET /api/v1/cases/{id}',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/cases`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.cases = data.items;
                            }
                        } catch (error) {
                            console.error('Failed to fetch cases:', error);
                        }
                    }
                },
                renderForm: () => `
                    ${renderTenantBanner()}
                    <div class="form-group">
                        <label>選擇個案 *</label>
                        <select id="view-case-id">
                            ${state.cases.map(c => `<option value="${c.id}">${c.case_number} - ${c.status}</option>`).join('')}
                        </select>
                    </div>
                    <button class="btn btn-primary" onclick="executeStep('view-case')" ${!state.token || state.cases.length === 0 ? 'disabled' : ''}>查看個案</button>
                `,
                execute: async () => {
                    const caseId = document.getElementById('view-case-id').value;
                    const response = await fetch(`${BASE_URL}/api/v1/cases/${caseId}`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>📋 個案詳情</h3>
                        <div class="info-row">
                            <span class="info-label">個案編號</span>
                            <span class="info-value">${data.case_number}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">狀態</span>
                            <span class="info-value">${data.status}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">客戶 ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.client_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">諮詢師 ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.counselor_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">摘要</span>
                            <span class="info-value">${data.summary || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">目標</span>
                            <span class="info-value">${data.goals || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">問題描述</span>
                            <span class="info-value">${data.problem_description || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">建立時間</span>
                            <span class="info-value">${new Date(data.created_at).toLocaleString('zh-TW')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                `
            },
            'update-case': {
                title: '更新個案',
                subtitle: 'PATCH /api/v1/cases/{id}',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/cases`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.cases = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['update-case'].renderForm();
                                // Load data for first case
                                setTimeout(() => loadCaseDataForUpdate(), 100);
                            }
                        } catch (error) {
                            console.error('Failed to fetch cases:', error);
                        }
                    }
                },
                renderForm: () => `
                    ${renderTenantBanner()}
                    <div class="form-group">
                        <label>選擇個案 *</label>
                        <select id="update-case-id" onchange="loadCaseDataForUpdate()">
                            ${state.cases.map(c => `<option value="${c.id}">${c.case_number} - ${c.status}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>狀態</label>
                        <select id="update-case-status">
                            <option value="">請選擇</option>
                            <option value="active">Active</option>
                            <option value="completed">Completed</option>
                            <option value="suspended">Suspended</option>
                            <option value="referred">Referred</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>摘要</label>
                        <textarea id="update-case-summary" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label>目標</label>
                        <textarea id="update-case-goals" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label>問題描述</label>
                        <textarea id="update-case-problem" rows="3"></textarea>
                    </div>
                    <button class="btn btn-primary" onclick="executeUpdateCase()" ${!state.token || state.cases.length === 0 ? 'disabled' : ''}>更新個案</button>
                `,
                execute: async () => {
                    const caseId = document.getElementById('update-case-id').value;
                    const updateData = {};

                    const status = document.getElementById('update-case-status').value;
                    const summary = document.getElementById('update-case-summary').value;
                    const goals = document.getElementById('update-case-goals').value;
                    const problem = document.getElementById('update-case-problem').value;

                    if (status) updateData.status = status;
                    if (summary) updateData.summary = summary;
                    if (goals) updateData.goals = goals;
                    if (problem) updateData.problem_description = problem;

                    const response = await fetch(`${BASE_URL}/api/v1/cases/${caseId}`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(updateData)
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>✅ 個案更新成功</h3>
                        <div class="info-row">
                            <span class="info-label">個案編號</span>
                            <span class="info-value">${data.case_number}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">狀態</span>
                            <span class="info-value">${data.status}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">摘要</span>
                            <span class="info-value">${data.summary || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">目標</span>
                            <span class="info-value">${data.goals || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">問題描述</span>
                            <span class="info-value">${data.problem_description || '無'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                `
            },
            'delete-case': {
                title: '刪除個案',
                subtitle: 'DELETE /api/v1/cases/{id}',
                init: async () => {
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/cases`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.cases = data.items;
                            }
                        } catch (error) {
                            console.error('Failed to fetch cases:', error);
                        }
                    }
                },
                renderForm: () => `
                    ${renderTenantBanner()}
                    <div class="form-group">
                        <label>選擇要刪除的個案 *</label>
                        <select id="delete-case-id">
                            ${state.cases.map(c => `<option value="${c.id}">${c.case_number} - ${c.status}</option>`).join('')}
                        </select>
                    </div>
                    <div class="info-card" style="background: #fee2e2; border-color: #ef4444;">
                        <p style="color: #991b1b; font-size: 13px;">⚠️ 警告：刪除個案為軟刪除（設置 deleted_at），不影響資料完整性</p>
                    </div>
                    <button class="btn btn-primary" onclick="executeStep('delete-case')" ${!state.token || state.cases.length === 0 ? 'disabled' : ''} style="background: #ef4444;">刪除個案</button>
                `,
                execute: async () => {
                    const caseId = document.getElementById('delete-case-id').value;
                    const response = await fetch(`${BASE_URL}/api/v1/cases/${caseId}`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${state.token}`
                        }
                    });

                    const data = response.status === 204 ? { success: true, message: '個案已刪除' } : await response.json();

                    if (response.status === 204) {
                        state.cases = state.cases.filter(c => c.id !== caseId);
                    }

                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="border-color: #10b981;">
                        <h3 style="color: #10b981;">✅ 個案刪除成功</h3>
                        <p style="color: #065f46; font-size: 14px; margin-top: 12px;">該個案已軟刪除（設置 deleted_at 時間戳）</p>
                    </div>
                `
            },
            'create-session': {
                title: '建立會談記錄',
                subtitle: 'POST /api/v1/sessions',
                init: async () => {
                    if (state.token) {
                        try {
                            // Fetch both clients and cases
                            const [clientsRes, casesRes] = await Promise.all([
                                fetch(`${BASE_URL}/api/v1/clients`, {
                                    headers: { 'Authorization': `Bearer ${state.token}` }
                                }),
                                fetch(`${BASE_URL}/api/v1/cases`, {
                                    headers: { 'Authorization': `Bearer ${state.token}` }
                                })
                            ]);
                            if (clientsRes.ok) {
                                const clientsData = await clientsRes.json();
                                state.clients = clientsData.items;
                            }
                            if (casesRes.ok) {
                                const casesData = await casesRes.json();
                                state.cases = casesData.items;
                            }
                        } catch (error) {
                            console.error('Failed to fetch data:', error);
                        }
                    }
                },
                renderForm: () => {
                    // Create a map of client info by ID for quick lookup
                    const clientMap = {};
                    state.clients.forEach(c => {
                        clientMap[c.id] = c;
                    });

                    // Build case options with client name + case number
                    const caseOptions = state.cases.map(caseItem => {
                        const client = clientMap[caseItem.client_id];
                        const clientName = client ? `${client.name} (${client.code})` : 'Unknown Client';
                        return `<option value="${caseItem.id}">${clientName} + ${caseItem.case_number}</option>`;
                    }).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="form-group">
                            <label>選擇個案 *</label>
                            <select id="session-case-id">
                                ${caseOptions}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>會談日期 *</label>
                            <input type="date" id="session-date" value="${new Date().toISOString().split('T')[0]}" />
                        </div>
                        <div class="form-group">
                            <label>會談名稱/主題（選填）</label>
                            <input type="text" id="session-name" placeholder="例如：生涯探索、工作適應、轉職規劃..." />
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div class="form-group">
                                <label>開始時間</label>
                                <input type="time" id="session-start-time" />
                            </div>
                            <div class="form-group">
                                <label>結束時間</label>
                                <input type="time" id="session-end-time" />
                            </div>
                        </div>

                        <div class="info-card" style="background: #f0fdf4; border-color: #10b981; margin-top: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                <h4 style="color: #047857; margin: 0;">🎙️ 錄音片段 Recordings（支援會談中斷後繼續）</h4>
                                <button type="button" class="btn btn-secondary" onclick="addRecordingSegment()" style="background: #10b981; padding: 6px 12px; font-size: 13px;">+ 新增片段</button>
                            </div>
                            <div id="recordings-container"></div>
                        </div>

                        <div class="form-group">
                            <label>逐字稿內容（完整，自動從 recordings 匯聚）</label>
                            <textarea id="session-transcript" placeholder="輸入會談逐字稿..." rows="10"></textarea>
                            <small style="color: #6b7280; font-size: 12px;">💡 若有使用 Recordings，此欄位會自動匯聚所有片段的逐字稿</small>
                        </div>
                        <div class="form-group">
                            <label>備註</label>
                            <textarea id="session-notes" placeholder="選填" rows="3"></textarea>
                        </div>
                        <div class="info-card" style="background: #eff6ff; border-color: #3b82f6;">
                            <h4 style="color: #1e40af; margin-bottom: 12px;">諮詢師反思（選填）</h4>
                            <div class="form-group">
                                <label>我和這個人工作的感受是？</label>
                                <textarea id="reflection-working" placeholder="例如：整體過程流暢輕鬆，逐漸贏得信任..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>這個感受的原因是？</label>
                                <textarea id="reflection-source" placeholder="例如：個案從緊張到逐步放鬆，願意開放心態分享更多..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>目前的困難／想更深入的地方是？</label>
                                <textarea id="reflection-challenges" placeholder="例如：當肯定個案時，仍會有自我懷疑反應..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>我會想找督導討論的問題是？</label>
                                <textarea id="reflection-supervision" placeholder="例如：如何在支持與挑戰間拿捏節奏..." rows="2"></textarea>
                            </div>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <button class="btn btn-primary" onclick="executeCreateSession()" ${!state.token || state.cases.length === 0 ? 'disabled' : ''}>建立會談記錄</button>
                            <button class="btn btn-secondary" onclick="quickFillSessionData()" ${!state.token ? 'disabled' : ''} style="background: #6366f1;">🎲 快速填入測試資料</button>
                        </div>
                    `;
                },
                execute: async () => {
                    const sessionDate = document.getElementById('session-date').value;
                    const startTime = document.getElementById('session-start-time').value;
                    const endTime = document.getElementById('session-end-time').value;

                    // Validate session_date is not empty
                    if (!sessionDate) {
                        throw new Error('會談日期為必填欄位');
                    }

                    const requestBody = {
                        case_id: document.getElementById('session-case-id').value,
                        session_date: sessionDate,  // Should be in YYYY-MM-DD format from input[type=date]
                        name: document.getElementById('session-name').value || null,
                        transcript: document.getElementById('session-transcript').value,
                        notes: document.getElementById('session-notes').value || null
                    };

                    // Add start_time and end_time if provided (non-empty)
                    if (startTime && startTime.trim()) {
                        requestBody.start_time = `${sessionDate} ${startTime}`;
                    }
                    if (endTime && endTime.trim()) {
                        requestBody.end_time = `${sessionDate} ${endTime}`;
                    }

                    // Add reflection if any field is filled
                    const reflectionWorking = document.getElementById('reflection-working').value;
                    const reflectionSource = document.getElementById('reflection-source').value;
                    const reflectionChallenges = document.getElementById('reflection-challenges').value;
                    const reflectionSupervision = document.getElementById('reflection-supervision').value;

                    if (reflectionWorking || reflectionSource || reflectionChallenges || reflectionSupervision) {
                        requestBody.reflection = {};
                        if (reflectionWorking) requestBody.reflection.working_with_client = reflectionWorking;
                        if (reflectionSource) requestBody.reflection.feeling_source = reflectionSource;
                        if (reflectionChallenges) requestBody.reflection.current_challenges = reflectionChallenges;
                        if (reflectionSupervision) requestBody.reflection.supervision_topics = reflectionSupervision;
                    }

                    // Add recordings if any segments exist
                    const recordings = collectRecordings();
                    if (recordings.length > 0) {
                        requestBody.recordings = recordings;
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestBody)
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.sessions = state.sessions || [];
                        state.sessions.push(data);
                        state.currentSession = data;
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>📝 逐字稿已儲存</h3>
                        <div class="info-row">
                            <span class="info-label">Session ID</span>
                            <span class="info-value">${data.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">會談編號</span>
                            <span class="info-value">第 ${data.session_number} 次</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">會談日期</span>
                            <span class="info-value">${new Date(data.session_date).toLocaleDateString('zh-TW')}</span>
                        </div>
                        ${data.name ? `
                        <div class="info-row">
                            <span class="info-label">會談主題</span>
                            <span class="info-value">${data.name}</span>
                        </div>
                        ` : ''}
                        <div class="info-row">
                            <span class="info-label">已生成報告</span>
                            <span class="info-value">${data.has_report ? '是' : '否'}</span>
                        </div>
                    </div>
                `
            },
            'list-sessions': {
                title: '列出會談記錄',
                subtitle: 'GET /api/v1/sessions',
                init: async () => {
                    // Refresh client list before showing form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/clients`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.clients = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['list-sessions'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh client list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const clientOptions = state.clients.map(c =>
                        `<option value="${c.id}">${c.name} (${c.code})</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="form-group">
                            <label>篩選個案 (可選)</label>
                            <select id="filter-session-client-id">
                                <option value="">全部</option>
                                ${clientOptions}
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeListSessions()" ${!state.token ? 'disabled' : ''}>列出逐字稿</button>
                    `;
                },
                execute: async () => {
                    const clientId = document.getElementById('filter-session-client-id').value;
                    const url = clientId
                        ? `${BASE_URL}/api/v1/sessions?client_id=${clientId}`
                        : `${BASE_URL}/api/v1/sessions`;

                    const response = await fetch(url, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.sessions = data.items;
                    }
                    return { response, data };
                },
                renderPreview: (data) => {
                    if (data.total === 0) {
                        return `<div class="empty-state"><p>尚無逐字稿記錄</p></div>`;
                    }
                    return `
                        <div class="info-card">
                            <h3>📝 逐字稿列表 (${data.total})</h3>
                        </div>
                        ${data.items.map(s => `
                            <div class="info-card" style="cursor: pointer;" onclick="state.currentSession = ${JSON.stringify(s).replace(/"/g, '&quot;')}; showStep('view-session');">
                                <div class="info-row">
                                    <span class="info-label">個案姓名</span>
                                    <span class="info-value">${s.client_name || 'N/A'}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">會談日期</span>
                                    <span class="info-value">${new Date(s.session_date).toLocaleDateString('zh-TW')}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">會談編號</span>
                                    <span class="info-value">第 ${s.session_number} 次</span>
                                </div>
                                ${s.name ? `
                                <div class="info-row">
                                    <span class="info-label">會談主題</span>
                                    <span class="info-value">${s.name}</span>
                                </div>
                                ` : ''}
                                <div class="info-row">
                                    <span class="info-label">已生成報告</span>
                                    <span class="info-value">${s.has_report ? '✅ 是' : '❌ 否'}</span>
                                </div>
                            </div>
                        `).join('')}
                    `;
                }
            },
            'view-session': {
                title: '查看會談詳情',
                subtitle: 'GET /api/v1/sessions/{id}',
                init: async () => {
                    // Refresh session list before showing view form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['view-session'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh session list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || '未知'} - 第 ${s.session_number} 次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="form-group">
                            <label>選擇會談記錄 *</label>
                            <select id="view-session-id">
                                ${sessionOptions}
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeViewSession()" ${!state.token || !state.sessions?.length ? 'disabled' : ''}>查看會談詳情</button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('view-session-id').value;

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.currentSession = data;
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>📝 會談詳情</h3>
                        <div class="info-row">
                            <span class="info-label">個案姓名</span>
                            <span class="info-value">${data.client_name || 'N/A'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">會談日期</span>
                            <span class="info-value">${new Date(data.session_date).toLocaleDateString('zh-TW')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">會談編號</span>
                            <span class="info-value">第 ${data.session_number} 次</span>
                        </div>
                        ${data.name ? `
                        <div class="info-row">
                            <span class="info-label">會談主題</span>
                            <span class="info-value">${data.name}</span>
                        </div>
                        ` : ''}
                        ${data.start_time ? `
                        <div class="info-row">
                            <span class="info-label">開始時間</span>
                            <span class="info-value">${new Date(data.start_time).toLocaleTimeString('zh-TW', {hour: '2-digit', minute: '2-digit'})}</span>
                        </div>
                        ` : ''}
                        ${data.end_time ? `
                        <div class="info-row">
                            <span class="info-label">結束時間</span>
                            <span class="info-value">${new Date(data.end_time).toLocaleTimeString('zh-TW', {hour: '2-digit', minute: '2-digit'})}</span>
                        </div>
                        ` : ''}
                        <div class="info-row">
                            <span class="info-label">已生成報告</span>
                            <span class="info-value">${data.has_report ? '✅ 是' : '❌ 否'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">建立時間</span>
                            <span class="info-value">${new Date(data.created_at).toLocaleString('zh-TW')}</span>
                        </div>
                        ${data.updated_at ? `
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="info-card">
                        <h4>逐字稿內容</h4>
                        <p style="white-space: pre-wrap; font-size: 13px; line-height: 1.6;">${data.transcript_text}</p>
                    </div>
                    ${data.summary ? `
                        <div class="info-card">
                            <h4>會談摘要（AI 生成）</h4>
                            <p style="font-size: 13px; line-height: 1.6;">${data.summary}</p>
                        </div>
                    ` : ''}
                    ${data.notes ? `
                        <div class="info-card">
                            <h4>備註（人類撰寫）</h4>
                            <p style="font-size: 13px;">${data.notes}</p>
                        </div>
                    ` : ''}
                    ${data.reflection && Object.keys(data.reflection).length > 0 ? `
                        <div class="info-card">
                            <h4>諮詢師反思（人類撰寫）</h4>
                            ${data.reflection.working_with_client ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">我和這個人工作的感受是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.working_with_client}</p>
                                </div>
                            ` : ''}
                            ${data.reflection.feeling_source ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">這個感受的原因是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.feeling_source}</p>
                                </div>
                            ` : ''}
                            ${data.reflection.current_challenges ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">目前的困難／想更深入的地方是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.current_challenges}</p>
                                </div>
                            ` : ''}
                            ${data.reflection.supervision_topics ? `
                                <div style="margin-bottom: 12px;">
                                    <strong style="color: #2563eb;">我會想找督導討論的問題是？</strong>
                                    <p style="font-size: 13px; margin-top: 4px; line-height: 1.6;">${data.reflection.supervision_topics}</p>
                                </div>
                            ` : ''}
                            ${!data.reflection.working_with_client && !data.reflection.feeling_source && !data.reflection.current_challenges && !data.reflection.supervision_topics ? `
                                <p style="font-size: 13px; color: #6b7280;">（自訂格式反思資料）</p>
                                <pre style="font-size: 12px; background: #f3f4f6; padding: 12px; border-radius: 4px; overflow-x: auto;">${JSON.stringify(data.reflection, null, 2)}</pre>
                            ` : ''}
                        </div>
                    ` : ''}
                `
            },
            'update-session': {
                title: '更新會談記錄',
                subtitle: 'PATCH /api/v1/sessions/{id}',
                init: async () => {
                    // Refresh session list before showing update form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['update-session'].renderForm();
                                // Load data for first session
                                setTimeout(() => loadSessionForUpdate(), 100);
                            }
                        } catch (error) {
                            console.error('Failed to refresh session list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || '未知'} - 第 ${s.session_number} 次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="form-group">
                            <label>選擇會談記錄 *</label>
                            <select id="update-session-id" onchange="loadSessionForUpdate()">
                                ${sessionOptions}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>會談日期</label>
                            <input type="date" id="update-session-date" />
                        </div>
                        <div class="form-group">
                            <label>會談名稱/主題</label>
                            <input type="text" id="update-session-name" placeholder="例如：生涯探索、工作適應、轉職規劃..." />
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div class="form-group">
                                <label>開始時間</label>
                                <input type="time" id="update-session-start-time" />
                            </div>
                            <div class="form-group">
                                <label>結束時間</label>
                                <input type="time" id="update-session-end-time" />
                            </div>
                        </div>
                        <div class="form-group">
                            <label>逐字稿內容</label>
                            <textarea id="update-session-transcript" placeholder="更新逐字稿..." rows="10"></textarea>
                        </div>
                        <div class="form-group">
                            <label>備註</label>
                            <textarea id="update-session-notes" placeholder="更新備註" rows="3"></textarea>
                        </div>
                        <div class="info-card" style="background: #eff6ff; border-color: #3b82f6;">
                            <h4 style="color: #1e40af; margin-bottom: 12px;">諮詢師反思（選填）</h4>
                            <div class="form-group">
                                <label>我和這個人工作的感受是？</label>
                                <textarea id="update-reflection-working" placeholder="例如：整體過程流暢輕鬆，逐漸贏得信任..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>這個感受的原因是？</label>
                                <textarea id="update-reflection-source" placeholder="例如：個案從緊張到逐步放鬆，願意開放心態分享更多..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>目前的困難／想更深入的地方是？</label>
                                <textarea id="update-reflection-challenges" placeholder="例如：當肯定個案時，仍會有自我懷疑反應..." rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <label>我會想找督導討論的問題是？</label>
                                <textarea id="update-reflection-supervision" placeholder="例如：如何在支持與挑戰間拿捏節奏..." rows="2"></textarea>
                            </div>
                        </div>
                        <button class="btn btn-primary" onclick="executeUpdateSession()" ${!state.token || !state.sessions?.length ? 'disabled' : ''}>更新會談記錄</button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('update-session-id').value;
                    const updateData = {};

                    const sessionDate = document.getElementById('update-session-date').value;
                    const sessionName = document.getElementById('update-session-name').value;
                    const startTime = document.getElementById('update-session-start-time').value;
                    const endTime = document.getElementById('update-session-end-time').value;
                    const transcript = document.getElementById('update-session-transcript').value;
                    const notes = document.getElementById('update-session-notes').value;

                    if (sessionDate) updateData.session_date = sessionDate;
                    if (sessionName) updateData.name = sessionName;
                    if (startTime && sessionDate) updateData.start_time = `${sessionDate} ${startTime}`;
                    if (endTime && sessionDate) updateData.end_time = `${sessionDate} ${endTime}`;
                    if (transcript) updateData.transcript = transcript;
                    if (notes) updateData.notes = notes;

                    // Add reflection if any field is filled
                    const reflectionWorking = document.getElementById('update-reflection-working').value;
                    const reflectionSource = document.getElementById('update-reflection-source').value;
                    const reflectionChallenges = document.getElementById('update-reflection-challenges').value;
                    const reflectionSupervision = document.getElementById('update-reflection-supervision').value;

                    if (reflectionWorking || reflectionSource || reflectionChallenges || reflectionSupervision) {
                        updateData.reflection = {};
                        if (reflectionWorking) updateData.reflection.working_with_client = reflectionWorking;
                        if (reflectionSource) updateData.reflection.feeling_source = reflectionSource;
                        if (reflectionChallenges) updateData.reflection.current_challenges = reflectionChallenges;
                        if (reflectionSupervision) updateData.reflection.supervision_topics = reflectionSupervision;
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(updateData)
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.currentSession = data;
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="border-color: #10b981;">
                        <h3 style="color: #10b981;">✅ 會談記錄更新成功</h3>
                        <div class="info-row">
                            <span class="info-label">會談日期</span>
                            <span class="info-value">${new Date(data.session_date).toLocaleDateString('zh-TW')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">更新時間</span>
                            <span class="info-value">${new Date(data.updated_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                `
            },
            'delete-session': {
                title: '刪除會談記錄',
                subtitle: 'DELETE /api/v1/sessions/{id}',
                init: async () => {
                    // Refresh session list before showing delete form
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['delete-session'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh session list:', error);
                        }
                    }
                },
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || '未知'} - 第 ${s.session_number} 次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="form-group">
                            <label>選擇會談記錄 *</label>
                            <select id="delete-session-id">
                                ${sessionOptions}
                            </select>
                        </div>
                        <div class="info-card" style="background: #fee2e2; border-color: #ef4444;">
                            <p style="color: #991b1b; font-size: 13px;">⚠️ 警告：無法刪除已生成報告的會談記錄!</p>
                        </div>
                        <button class="btn btn-primary" onclick="executeDeleteSession()" ${!state.token || !state.sessions?.length ? 'disabled' : ''} style="background: #ef4444;">刪除會談記錄</button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('delete-session-id').value;

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });

                    const data = response.status === 204 ? { success: true, message: '逐字稿已刪除' } : await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="border-color: #10b981;">
                        <h3 style="color: #10b981;">✅ 逐字稿刪除成功</h3>
                        <p style="color: #065f46; font-size: 14px; margin-top: 12px;">該逐字稿已從系統中移除</p>
                    </div>
                `
            },
            'update-counselor': {
                title: '更新諮詢師資訊',
                subtitle: 'PATCH /api/auth/me',
                renderForm: () => `
                    <div class="info-card">
                        <p style="font-size: 13px; color: #6b7280;">當前用戶: ${state.currentUser?.full_name || 'N/A'}</p>
                    </div>
                    <div class="form-group">
                        <label>全名</label>
                        <input type="text" id="update-counselor-fullname" placeholder="更新全名" value="${state.currentUser?.full_name || ''}" />
                    </div>
                    <div class="form-group">
                        <label>用戶名</label>
                        <input type="text" id="update-counselor-username" placeholder="更新用戶名" value="${state.currentUser?.username || ''}" />
                    </div>
                    <button class="btn btn-primary" onclick="executeUpdateCounselor()" ${!state.token || !state.currentUser ? 'disabled' : ''}>更新資訊</button>
                `,
                execute: async () => {
                    const updateData = {};

                    const fullName = document.getElementById('update-counselor-fullname').value;
                    const username = document.getElementById('update-counselor-username').value;

                    if (fullName) updateData.full_name = fullName;
                    if (username) updateData.username = username;

                    const response = await fetch(`${BASE_URL}/api/auth/me`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(updateData)
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.currentUser = data;
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>✅ 諮詢師資訊更新成功</h3>
                        <div class="info-row">
                            <span class="info-label">全名</span>
                            <span class="info-value">${data.full_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">用戶名</span>
                            <span class="info-value">${data.username}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Email</span>
                            <span class="info-value">${data.email}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">角色</span>
                            <span class="info-value">${data.role}</span>
                        </div>
                    </div>
                `
            },
            'generate-report': {
                title: '生成報告',
                subtitle: 'POST /api/v1/reports/generate',
                init: async () => {
                    // Refresh sessions list to get latest data with has_report status
                    if (state.token) {
                        try {
                            const response = await fetch(`${BASE_URL}/api/v1/sessions`, {
                                headers: { 'Authorization': `Bearer ${state.token}` }
                            });
                            if (response.ok) {
                                const data = await response.json();
                                state.sessions = data.items;
                                // Re-render form with updated list
                                document.getElementById('action-form').innerHTML = steps['generate-report'].renderForm();
                            }
                        } catch (error) {
                            console.error('Failed to refresh session list:', error);
                        }
                    }
                },
                renderForm: () => {
                    // Filter sessions that don't have reports yet
                    const sessionsWithoutReports = (state.sessions || []).filter(s => !s.has_report);

                    if (sessionsWithoutReports.length === 0) {
                        return `
                            ${renderTenantBanner()}
                            <div class="info-card" style="background: #fef3c7; border-color: #f59e0b;">
                                <p style="color: #92400e;">⚠️ 沒有未生成報告的逐字稿。請先儲存逐字稿。</p>
                            </div>
                        `;
                    }

                    const sessionOptions = sessionsWithoutReports.map(s =>
                        `<option value="${s.id}">${s.client_name} - 第${s.session_number}次 (${new Date(s.session_date).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="form-group">
                            <label>選擇會談記錄 * (僅顯示未生成報告的記錄)</label>
                            <select id="report-session-id">
                                ${sessionOptions}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>報告類型</label>
                            <select id="report-type">
                                <option value="enhanced">Enhanced (10段式)</option>
                                <option value="legacy">Legacy (5段式)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>RAG 系統</label>
                            <select id="report-rag">
                                <option value="openai">OpenAI (GPT-4.1 Mini)</option>
                                <option value="gemini">Gemini 2.5 Flash</option>
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeGenerateReport()" ${!state.token ? 'disabled' : ''}>生成報告</button>
                    `;
                },
                execute: async () => {
                    const reportData = {
                        session_id: document.getElementById('report-session-id').value,
                        report_type: document.getElementById('report-type').value,
                        rag_system: document.getElementById('report-rag').value
                    };

                    const response = await fetch(`${BASE_URL}/api/v1/reports/generate`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(reportData)
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.currentReport = data;
                    }
                    return { response, data };
                },
                renderPreview: (data) => {
                    // 檢查是否是 processing 狀態
                    if (data.report?.status === 'processing') {
                        // 開始輪詢
                        setTimeout(() => pollReportStatus(data.report_id), 3000);

                        return `
                            <div class="info-card" style="background: #fef3c7; border-color: #f59e0b;">
                                <h3>⏳ 報告生成中...</h3>
                                <p style="color: #92400e; margin-top: 12px;">逐字稿已保存，報告正在背景生成中，請稍候</p>
                                <div class="info-row">
                                    <span class="info-label">Report ID</span>
                                    <span class="info-value" style="font-size: 11px;">${data.report_id}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Session ID</span>
                                    <span class="info-value" style="font-size: 11px;">${data.session_id}</span>
                                </div>
                                <div id="polling-status" style="margin-top: 16px; padding: 12px; background: white; border-radius: 6px;">
                                    <p style="font-size: 13px; color: #6b7280;">正在查詢狀態...</p>
                                </div>
                            </div>
                        `;
                    }

                    const report = data.report?.report || {};
                    const quality = data.quality_summary || {};

                    return `
                        ${quality.grade ? `
                            <div class="quality-summary">
                                <div class="quality-grade">${quality.grade}</div>
                                <div class="quality-score">評分：${quality.overall_score} / 100</div>
                            </div>
                        ` : ''}

                        <div class="info-card">
                            <h3>📊 報告基本資訊</h3>
                            <div class="info-row">
                                <span class="info-label">Report ID</span>
                                <span class="info-value" style="font-size: 11px;">${data.report_id}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Session ID</span>
                                <span class="info-value" style="font-size: 11px;">${data.session_id}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">模式</span>
                                <span class="info-value">${data.report?.mode || 'N/A'}</span>
                            </div>
                        </div>

                        ${report.client_info ? `
                            <div class="report-section">
                                <h3>👤 案主資料</h3>
                                <div class="info-card">
                                    <div class="info-row">
                                        <span class="info-label">姓名</span>
                                        <span class="info-value">${report.client_info.name || 'N/A'}</span>
                                    </div>
                                    <div class="info-row">
                                        <span class="info-label">性別</span>
                                        <span class="info-value">${report.client_info.gender || 'N/A'}</span>
                                    </div>
                                    <div class="info-row">
                                        <span class="info-label">年齡</span>
                                        <span class="info-value">${report.client_info.age || 'N/A'}</span>
                                    </div>
                                    <div class="info-row">
                                        <span class="info-label">職業</span>
                                        <span class="info-value">${report.client_info.occupation || 'N/A'}</span>
                                    </div>
                                </div>
                            </div>
                        ` : ''}

                        ${report.main_concerns?.length ? `
                            <div class="report-section">
                                <h3>🎯 主要議題</h3>
                                <ul>
                                    ${report.main_concerns.map(c => `<li>${c}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}

                        ${report.conceptualization ? `
                            <div class="report-section">
                                <h3>💡 個案概念化</h3>
                                <p>${report.conceptualization}</p>
                            </div>
                        ` : ''}

                        ${report.theories?.length ? `
                            <div class="report-section">
                                <h3>📚 理論引用</h3>
                                ${report.theories.slice(0, 3).map(t => `
                                    <div class="theory-item">
                                        <p>${t.text}</p>
                                        <div class="theory-meta">
                                            相似度: ${(t.score * 100).toFixed(1)}% | 來源: ${t.document}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    `;
                }
            },
            'list-reports': {
                title: '列出報告',
                subtitle: 'GET /api/v1/reports',
                renderForm: () => {
                    const hasClients = state.clients.length > 0;
                    const clientOptions = state.clients.map(c =>
                        `<option value="${c.id}">${c.name} (${c.code})</option>`
                    ).join('');
                    return `
                        ${renderTenantBanner()}
                        ${!hasClients ? '<div class="alert alert-warning" style="background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 6px; margin-bottom: 16px; color: #856404;"><strong>⚠️ 提示：</strong> 請先執行「列出個案」步驟以載入個案清單，才能使用篩選功能</div>' : ''}
                        <div class="form-group">
                            <label>篩選個案 (選填)</label>
                            <select id="filter-client-id" ${!hasClients ? 'disabled' : ''}>
                                <option value="">全部個案</option>
                                ${clientOptions}
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeListReports()" ${!state.token ? 'disabled' : ''}>查詢報告</button>
                    `;
                },
                execute: async () => {
                    const clientId = document.getElementById('filter-client-id')?.value;
                    const url = clientId
                        ? `${BASE_URL}/api/v1/reports?client_id=${clientId}`
                        : `${BASE_URL}/api/v1/reports`;

                    const response = await fetch(url, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    if (response.ok) {
                        state.reports = data.items;
                    }
                    return { response, data };
                },
                renderPreview: (data) => `
                    <h3>📋 報告列表 (共 ${data.total} 筆)</h3>
                    ${data.items.map(report => `
                        <div class="info-card">
                            <div class="info-row">
                                <span class="info-label">個案/次數</span>
                                <span class="info-value">${report.client_name || 'N/A'} - 第 ${report.session_number || '?'} 次</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">ID</span>
                                <span class="info-value" style="font-size: 11px;">${report.id}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">模式</span>
                                <span class="info-value">${report.mode}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">狀態</span>
                                <span class="info-value">${report.status}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">評分</span>
                                <span class="info-value">${report.quality_grade || 'N/A'}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">建立時間</span>
                                <span class="info-value">${new Date(report.created_at).toLocaleString('zh-TW')}</span>
                            </div>
                        </div>
                    `).join('')}
                `
            },
            'view-report': {
                title: '查看報告',
                subtitle: 'GET /api/v1/reports/{id}',
                renderForm: () => {
                    const reportOptions = state.reports.map(r =>
                        `<option value="${r.id}">${r.client_name || 'Client'} - 第${r.session_number || '?'}次 (${new Date(r.created_at).toLocaleDateString('zh-TW')})</option>`
                    ).join('');

                    return `
                        <div class="info-card" style="background: #e0f2fe; border-color: #3b82f6; margin-bottom: 16px;">
                            <p style="color: #1e40af; font-size: 12px;">
                                💡 支援多種輸出格式：不傳參數返回完整 metadata，或使用 format 參數輸出 Markdown/HTML
                            </p>
                        </div>
                        <div class="form-group">
                            <label>選擇報告</label>
                            <select id="view-report-id">
                                ${state.currentReport ? `<option value="${state.currentReport.report_id}" selected>Current Report</option>` : ''}
                                ${reportOptions}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>輸出格式</label>
                            <select id="view-report-format">
                                <option value="">JSON metadata (預設)</option>
                                <option value="markdown">Markdown</option>
                                <option value="html">HTML</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>版本選擇</label>
                            <select id="view-report-use-edited">
                                <option value="true">編輯版 (優先)</option>
                                <option value="false">AI 原始版</option>
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="executeViewReport()" ${!state.token || (!state.currentReport && state.reports.length === 0) ? 'disabled' : ''}>查看報告</button>
                    `;
                },
                execute: async () => {
                    const reportId = document.getElementById('view-report-id').value;
                    const format = document.getElementById('view-report-format').value;
                    const useEdited = document.getElementById('view-report-use-edited').value;

                    let url = `${BASE_URL}/api/v1/reports/${reportId}`;
                    const params = new URLSearchParams();
                    if (format) params.append('format', format);
                    params.append('use_edited', useEdited);

                    if (params.toString()) {
                        url += `?${params.toString()}`;
                    }

                    const response = await fetch(url, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    return { response, data, format: format || 'json' };
                },
                renderPreview: (result) => {
                    // Handle error response
                    if (!result || !result.data) {
                        return '<div class="info-card" style="background: #fee2e2; border-color: #ef4444;"><p style="color: #991b1b;">無法載入報告</p></div>';
                    }

                    const { data, format } = result;

                    if (format === 'json') {
                        const content = data.content_json?.report || data.content_json || {};
                        return `
                            <div class="info-card">
                                <h3>📄 報告詳情 (JSON)</h3>
                                <div class="info-row">
                                    <span class="info-label">ID</span>
                                    <span class="info-value" style="font-size: 11px;">${data.id}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">狀態</span>
                                    <span class="info-value">${data.status}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">評分</span>
                                    <span class="info-value">${data.quality_grade || 'N/A'} (${data.quality_score || 'N/A'})</span>
                                </div>
                            </div>
                            <div style="background: #1e293b; border-radius: 8px; padding: 20px; max-height: 600px; overflow-y: auto;">
                                <pre style="margin: 0; color: #e2e8f0; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(content, null, 2)}</pre>
                            </div>
                        `;
                    }

                    // Markdown or HTML format - Render nicely
                    const isEdited = (data.is_edited === true) ? '✏️ 編輯版' : '🤖 AI 原始版';
                    const formattedContent = data.formatted_content || '';

                    if (format === 'markdown') {
                        // Use marked.js to render Markdown to HTML
                        const htmlContent = marked.parse(formattedContent);

                        return `
                            <div class="info-card">
                                <h3>📄 報告內容 (${isEdited})</h3>
                                <div class="info-row">
                                    <span class="info-label">格式</span>
                                    <span class="info-value">Markdown (渲染)</span>
                                </div>
                                ${data.edited_at ? `
                                <div class="info-row">
                                    <span class="info-label">最後編輯</span>
                                    <span class="info-value">${new Date(data.edited_at).toLocaleString('zh-TW')}</span>
                                </div>
                                ` : ''}
                            </div>
                            <div class="markdown-content" style="max-height: 600px; overflow-y: auto; padding: 24px; background: white; border: 1px solid #e5e7eb; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1f2937;">
                                ${htmlContent}
                            </div>
                            <style>
                                .markdown-content h1 { color: #1e40af; margin: 28px 0 14px; font-size: 28px; }
                                .markdown-content h2 { color: #1e40af; margin: 24px 0 12px; font-size: 24px; }
                                .markdown-content h3 { color: #1e40af; margin: 20px 0 10px; font-size: 20px; }
                                .markdown-content p { margin: 12px 0; line-height: 1.8; }
                                .markdown-content ul, .markdown-content ol { margin: 12px 0; padding-left: 24px; }
                                .markdown-content li { margin: 4px 0; }
                                .markdown-content strong { font-weight: 600; }
                                .markdown-content code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: 'Courier New', monospace; }
                                .markdown-content pre { background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; overflow-x: auto; }
                                .markdown-content blockquote { border-left: 4px solid #3b82f6; padding-left: 16px; color: #6b7280; margin: 12px 0; }
                            </style>
                        `;
                    } else if (format === 'html') {
                        // HTML format - render as HTML
                        return `
                            <div class="info-card">
                                <h3>📄 報告內容 (${isEdited})</h3>
                                <div class="info-row">
                                    <span class="info-label">格式</span>
                                    <span class="info-value">HTML</span>
                                </div>
                                ${data.edited_at ? `
                                <div class="info-row">
                                    <span class="info-label">最後編輯</span>
                                    <span class="info-value">${new Date(data.edited_at).toLocaleString('zh-TW')}</span>
                                </div>
                                ` : ''}
                            </div>
                            <div style="max-height: 600px; overflow-y: auto; padding: 24px; background: white; border: 1px solid #e5e7eb; border-radius: 8px;">
                                ${formattedContent}
                            </div>
                        `;
                    } else {
                        // Unknown format
                        return `
                            <div class="info-card">
                                <h3>📄 報告內容 (${isEdited})</h3>
                            </div>
                            <div style="background: #1e293b; border-radius: 8px; padding: 20px; max-height: 600px; overflow-y: auto;">
                                <pre style="margin: 0; color: #e2e8f0; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word;">${formattedContent}</pre>
                            </div>
                        `;
                    }
                }
            },
            'update-report': {
                title: '更新報告',
                subtitle: 'PATCH /api/v1/reports/{id} (僅供 iOS 使用)',
                renderForm: () => {
                    return `
                        <div class="info-card" style="background: #fef3c7; border-color: #f59e0b;">
                            <p style="color: #92400e; font-size: 12px;">
                                ⚠️ 此 API 僅供 iOS App 使用，用於提交諮詢師編輯後的報告內容。<br>
                                Web Console 不提供編輯功能。
                            </p>
                        </div>
                        <button class="btn btn-secondary" disabled>此功能僅供 iOS 使用</button>
                    `;
                },
                execute: async () => {
                    const reportId = document.getElementById('update-report-id').value;
                    const contentText = document.getElementById('update-report-content').value;

                    let editedContent;
                    try {
                        editedContent = JSON.parse(contentText);
                    } catch (e) {
                        throw new Error('Invalid JSON format');
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/reports/${reportId}`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ edited_content_json: editedContent })
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card">
                        <h3>✅ 報告更新成功</h3>
                        <div class="info-row">
                            <span class="info-label">Report ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">編輯時間</span>
                            <span class="info-value">${new Date(data.edited_at).toLocaleString('zh-TW')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">編輯次數</span>
                            <span class="info-value">${data.edit_count}</span>
                        </div>
                    </div>
                    <div class="report-section">
                        <h3>📝 格式化 Markdown</h3>
                        <div class="response-content" style="max-height: 400px; white-space: pre-wrap;">${data.formatted_markdown}</div>
                    </div>
                `
            },

            // ================== UI-0: Mobile Login ==================
            'ui-mobile-login': {
                title: '📱 登入頁面 (手機模擬)',
                subtitle: 'POST /api/auth/login',
                renderForm: () => {
                    // Immediately show initial preview (don't wait for API call)
                    setTimeout(() => {
                        const previewEl = document.getElementById('preview-content');
                        if (previewEl) {
                            previewEl.innerHTML = steps['ui-mobile-login'].renderPreview({
                                preview: true,
                                email: 'counselor@career.com',
                                password: 'password123',
                                tenant_id: 'career'
                            });
                        }

                        // Add input listeners for live preview sync
                        const syncPreview = () => {
                            const previewEl = document.getElementById('preview-content');
                            if (!previewEl) return;

                            const email = document.getElementById('ui-login-email')?.value || '';
                            const password = document.getElementById('ui-login-password')?.value || '';
                            const tenant = document.getElementById('ui-login-tenant')?.value || '';

                            // Update preview with current form values
                            const previewHtml = steps['ui-mobile-login'].renderPreview({
                                preview: true,
                                email: email,
                                password: password,
                                tenant_id: tenant
                            });
                            previewEl.innerHTML = previewHtml;
                        };

                        const emailInput = document.getElementById('ui-login-email');
                        const passwordInput = document.getElementById('ui-login-password');
                        const tenantInput = document.getElementById('ui-login-tenant');

                        emailInput?.addEventListener('input', syncPreview);
                        passwordInput?.addEventListener('input', syncPreview);
                        tenantInput?.addEventListener('input', syncPreview);
                    }, 100);

                    return `
                        <div class="info-card">
                            <p>📱 手機風格的登入頁面</p>
                            <p style="color: #86868b; font-size: 14px; margin-top: 8px;">• 左右欄位即時同步</p>
                            <p style="color: #86868b; font-size: 14px;">• 修改左邊表單，右邊預覽即時更新</p>
                        </div>
                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" id="ui-login-email" value="counselor@career.com" />
                        </div>
                        <div class="form-group">
                            <label>密碼</label>
                            <input type="password" id="ui-login-password" value="password123" />
                        </div>
                        <div class="form-group">
                            <label>Tenant ID</label>
                            <input type="text" id="ui-login-tenant" value="career" />
                        </div>
                        <button class="btn btn-primary" onclick="executeStep('ui-mobile-login')">測試登入</button>
                    `;
                },
                execute: async () => {
                    const email = document.getElementById('ui-login-email').value;
                    const password = document.getElementById('ui-login-password').value;
                    const tenant_id = document.getElementById('ui-login-tenant').value;

                    const response = await fetch(`${BASE_URL}/api/auth/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password, tenant_id })
                    });
                    const data = await response.json();

                    // Store token if login successful
                    if (response.ok && data.access_token) {
                        state.token = data.access_token;
                    }

                    return { response, data };
                },
                renderPreview: (data) => {
                    // Always show login form preview (never replace with success screen)
                    // Success message will be shown in Response section below

                    // Get current form values (for live sync)
                    const email = data.email || 'counselor@career.com';
                    const password = data.password || 'password123';
                    const tenant = data.tenant_id || 'career';

                    // Show login form preview
                    return `
                        <div class="iphone-preview">
                            <!-- Status Bar -->
                            <div style="padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 500;">
                                <span>9:41</span>
                                <div style="display: flex; gap: 6px; align-items: center;">
                                    <span>📶</span>
                                    <span>📡</span>
                                    <span>🔋</span>
                                </div>
                            </div>

                            <!-- Login Form -->
                            <div style="flex: 1; display: flex; flex-direction: column; padding: 40px 32px; background: #f5f5f7;">
                                <div style="flex: 1;">
                                    <h1 style="font-size: 48px; font-weight: 700; margin: 0; color: #1d1d1f;">登入</h1>

                                    <div style="margin-top: 60px;">
                                        <!-- Email Input -->
                                        <div style="background: #e8e8ed; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;">
                                            <input type="email"
                                                   value="${email}"
                                                   readonly
                                                   style="width: 100%; border: none; background: transparent; font-size: 16px; color: #1d1d1f; outline: none;" />
                                        </div>

                                        <!-- Password Input -->
                                        <div style="background: #e8e8ed; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;">
                                            <input type="password"
                                                   value="${password}"
                                                   readonly
                                                   style="width: 100%; border: none; background: transparent; font-size: 16px; color: #1d1d1f; outline: none;" />
                                        </div>

                                        <!-- Tenant ID (hidden field, shown as label) -->
                                        <div style="font-size: 12px; color: #86868b; margin-top: 8px;">
                                            Tenant: ${tenant}
                                        </div>
                                    </div>
                                </div>

                                <!-- Login Button -->
                                <div>
                                    <button style="
                                        width: 100%;
                                        background: ${email && password ? '#007aff' : '#8e8e93'};
                                        color: white;
                                        border: none;
                                        border-radius: 12px;
                                        padding: 18px;
                                        font-size: 18px;
                                        font-weight: 600;
                                        margin-bottom: 20px;
                                        cursor: ${email && password ? 'pointer' : 'not-allowed'};
                                    ">登入</button>

                                    <div style="text-align: center;">
                                        <a href="#" style="color: #8e8e93; font-size: 14px; text-decoration: none;">忘記密碼</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
            },

            'ui-client-case-list': {
                title: '📱 客戶個案列表 (手機模擬)',
                subtitle: 'GET /api/v1/ui/client-case-list (嵌入式)',
                renderForm: () => {
                    return `
                        <div class="info-card">
                            <p>📱 手機風格的客戶個案列表頁面</p>
                            <p style="color: #86868b; font-size: 14px; margin-top: 8px;">• 自動載入真實數據</p>
                            <p style="color: #86868b; font-size: 14px;">• 點擊右側預覽查看</p>
                        </div>
                        <button class="btn btn-primary" onclick="executeStep('ui-client-case-list')">載入預覽</button>
                    `;
                },
                execute: async () => {
                    // Fetch real data from API
                    const response = await fetch(`${BASE_URL}/api/v1/ui/client-case-list?skip=0&limit=100`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => {
                    const items = data.items || [];

                    const caseCardsHtml = items.length === 0 ? `
                        <div class="empty-state">
                            <svg fill="currentColor" viewBox="0 0 24 24" style="width: 80px; height: 80px; margin-bottom: 16px; opacity: 0.3;">
                                <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/>
                            </svg>
                            <div>尚無個案</div>
                            <div style="font-size: 12px; margin-top: 8px;">點擊右上角 + 新增個案</div>
                        </div>
                    ` : items.map(item => {
                        // Map integer status to CSS class (0=NOT_STARTED, 1=IN_PROGRESS, 2=COMPLETED)
                        const statusClass = item.case_status === 2 ? 'completed' :
                                          item.case_status === 1 ? 'in-progress' : 'not-started';
                        return `
                            <div class="case-card" style="background: #fff; border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                    <div>
                                        <div style="font-size: 18px; font-weight: 600; color: #1d1d1f;">${item.client_name}</div>
                                        <p style="margin: 4px 0; font-size: 12px; color: #6e6e73;">${item.client_email}</p>
                                    </div>
                                    <div style="color: #86868b; font-size: 20px; cursor: pointer;">⋯</div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; color: #6e6e73;">
                                    <svg fill="currentColor" viewBox="0 0 24 24" style="width: 16px; height: 16px;">
                                        <path d="M20,6C20.58,6 21.05,6.2 21.42,6.59C21.8,7 22,7.45 22,8V19C22,19.55 21.8,20 21.42,20.41C21.05,20.8 20.58,21 20,21H4C3.42,21 2.95,20.8 2.58,20.41C2.2,20 2,19.55 2,19V8C2,7.45 2.2,7 2.58,6.59C2.95,6.2 3.42,6 4,6H8V4C8,3.42 8.2,2.95 8.58,2.58C8.95,2.2 9.42,2 10,2H14C14.58,2 15.05,2.2 15.42,2.58C15.8,2.95 16,3.42 16,4V6H20M4,8V19H20V8H4M10,4V6H14V4H10Z"/>
                                    </svg>
                                    <span>${item.identity_option}</span>
                                </div>
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; color: #6e6e73;">
                                    <svg fill="currentColor" viewBox="0 0 24 24" style="width: 16px; height: 16px;">
                                        <path d="M9,10H7V12H9V10M13,10H11V12H13V10M17,10H15V12H17V10M19,3H18V1H16V3H8V1H6V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M19,19H5V8H19V19Z"/>
                                    </svg>
                                    <span>最後諮詢：${item.last_session_date_display || '未開始'}</span>
                                </div>
                                <span style="display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; margin-top: 8px; background: ${
                                    statusClass === 'completed' ? '#d1f4e0' :
                                    statusClass === 'in-progress' ? '#fff4e6' : '#e0f0ff'
                                }; color: ${
                                    statusClass === 'completed' ? '#0d894f' :
                                    statusClass === 'in-progress' ? '#f5a623' : '#0071e3'
                                };">${item.case_status_label}</span>
                            </div>
                        `;
                    }).join('');

                    return `
                        <style>
                            .iphone-preview {
                                width: 390px;
                                height: 844px;
                                background: #000;
                                border-radius: 50px;
                                padding: 12px;
                                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                                position: relative;
                                margin: 0 auto;
                            }
                            .iphone-preview .notch {
                                position: absolute;
                                top: 0;
                                left: 50%;
                                transform: translateX(-50%);
                                width: 120px;
                                height: 30px;
                                background: #000;
                                border-radius: 0 0 20px 20px;
                                z-index: 10;
                            }
                            .iphone-preview .screen {
                                width: 100%;
                                height: 100%;
                                background: #fff;
                                border-radius: 40px;
                                overflow: hidden;
                            }
                            .iphone-preview .status-bar {
                                display: flex;
                                justify-content: space-between;
                                padding: 0 20px;
                                height: 44px;
                                align-items: center;
                                font-size: 15px;
                                font-weight: 600;
                            }
                            .iphone-preview .status-bar .time {
                                margin-left: 60px;
                            }
                            .iphone-preview .nav-bar {
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                padding: 16px 20px;
                                border-bottom: 1px solid #e5e5e7;
                            }
                            .iphone-preview .nav-bar .title {
                                font-size: 17px;
                                font-weight: 600;
                                flex: 1;
                                text-align: center;
                            }
                            .iphone-preview .nav-bar .add-btn {
                                width: 36px;
                                height: 36px;
                                background: #5ac8fa;
                                border-radius: 50%;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                color: #fff;
                                font-size: 24px;
                            }
                            .iphone-preview .content {
                                height: calc(100% - 44px - 60px - 50px);
                                overflow-y: auto;
                                padding: 12px 16px;
                                background: #f9f9f9;
                            }
                        </style>
                        <div class="iphone-preview">
                            <div class="notch"></div>
                            <div class="screen">
                                <div class="status-bar">
                                    <span class="time">9:41</span>
                                    <div>⚡️ 📶 🔋</div>
                                </div>
                                <div class="nav-bar">
                                    <div>‹</div>
                                    <div class="title">個案列表</div>
                                    <div class="add-btn">+</div>
                                </div>
                                <div class="content">
                                    ${caseCardsHtml}
                                </div>
                            </div>
                        </div>
                    `;
                }
            },
            'ui-create-client-case': {
                title: '📝 獲取表單 Schema',
                subtitle: 'GET /api/v1/ui/field-schemas/client-case',
                renderForm: () => {
                    return `
                        ${renderTenantBanner()}
                        <div class="info-card">
                            <p>📱 iOS 建立個案流程 - Step 1: 獲取表單配置</p>
                            <p style="color: #86868b; font-size: 14px; margin-top: 8px;">
                                • 一次性獲取 Client 和 Case 兩個表單的 Schema<br>
                                • 減少網絡請求次數<br>
                                • 根據 tenant_id 動態決定欄位
                            </p>
                        </div>
                        <button class="btn btn-primary" onclick="executeStep('ui-create-client-case')">獲取表單 Schema</button>
                    `;
                },
                execute: async () => {
                    // Fetch both schemas in one call
                    const response = await fetch(`${BASE_URL}/api/v1/ui/field-schemas/client-case`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();

                    return {
                        response,
                        data: {
                            client_schema: data.client,
                            case_schema: data.case,
                            tenant_id: data.tenant_id
                        }
                    };
                },
                renderPreview: (data) => {
                    const clientFields = data.client_schema?.sections?.[0]?.fields?.slice(0, 5) || [];
                    const caseFields = data.case_schema?.sections?.[0]?.fields?.slice(0, 3) || [];

                    return `
                        <div class="info-card">
                            <h3>✅ Schema 獲取成功</h3>
                            <p style="color: #86868b; margin-top: 8px;">租戶: <strong>${data.tenant_id}</strong></p>
                        </div>

                        <div class="info-card" style="margin-top: 16px;">
                            <h4>📝 Client Schema (前 5 個欄位)</h4>
                            ${clientFields.map(f => `
                                <div style="padding: 8px 0; border-bottom: 1px solid #f0f0f0;">
                                    <div style="font-weight: 600;">${f.label}${f.required ? ' *' : ''}</div>
                                    <div style="color: #86868b; font-size: 12px;">
                                        key: ${f.key} | type: ${f.type}
                                        ${f.options ? `| options: ${f.options.join(', ')}` : ''}
                                    </div>
                                </div>
                            `).join('')}
                            <p style="color: #86868b; font-size: 12px; margin-top: 8px;">
                                總共 ${data.client_schema?.sections?.[0]?.fields?.length || 0} 個欄位
                            </p>
                        </div>

                        <div class="info-card" style="margin-top: 16px;">
                            <h4>📋 Case Schema (前 3 個欄位)</h4>
                            ${caseFields.map(f => `
                                <div style="padding: 8px 0; border-bottom: 1px solid #f0f0f0;">
                                    <div style="font-weight: 600;">${f.label}${f.required ? ' *' : ''}</div>
                                    <div style="color: #86868b; font-size: 12px;">
                                        key: ${f.key} | type: ${f.type}
                                        ${f.options ? `| options: ${f.options.join(', ')}` : ''}
                                    </div>
                                </div>
                            `).join('')}
                            <p style="color: #86868b; font-size: 12px; margin-top: 8px;">
                                總共 ${data.case_schema?.sections?.[0]?.fields?.length || 0} 個欄位
                            </p>
                        </div>

                        <div class="info-card" style="margin-top: 16px; background: #f0f9ff; border-color: #0ea5e9;">
                            <p style="color: #0369a1; font-size: 13px;">
                                💡 <strong>iOS 使用方式：</strong><br>
                                1. 解析 client_schema 和 case_schema<br>
                                2. 根據 field type 動態生成 UI 元件<br>
                                3. 用戶填寫後，POST 到 /api/v1/ui/client-case
                            </p>
                        </div>
                    `;
                }
            },

            // ================== 客戶個案管理 CRUD ==================
            'list-client-cases': {
                title: '列出客戶個案',
                subtitle: 'GET /api/v1/ui/client-case-list',
                renderForm: () => `
                    ${renderTenantBanner()}
                    <div class="info-card">
                        <p>📊 查詢所有客戶個案 (Client + Case + Session)</p>
                        <p style="color: #86868b; font-size: 14px; margin-top: 8px;">• 一次取得 Client 基本資料、第一個 Case、最後諮詢日期</p>
                    </div>
                    <div class="form-group">
                        <label>Skip (跳過筆數)</label>
                        <input type="number" id="cc-list-skip" value="0" min="0" />
                    </div>
                    <div class="form-group">
                        <label>Limit (每頁筆數)</label>
                        <input type="number" id="cc-list-limit" value="20" min="1" max="100" />
                    </div>
                    <button class="btn btn-primary" onclick="executeListClientCases()">查詢</button>
                `,
                execute: async () => {
                    const skip = document.getElementById('cc-list-skip').value || 0;
                    const limit = document.getElementById('cc-list-limit').value || 20;

                    const response = await fetch(`${BASE_URL}/api/v1/ui/client-case-list?skip=${skip}&limit=${limit}`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();

                    // Store for later use
                    state.clientCases = data.items || [];

                    return { response, data };
                },
                                renderPreview: (data) => {
                    if (!data.items || data.items.length === 0) {
                        return `
                            <div class="info-card">
                                <h3>📊 查詢結果</h3>
                                <p>尚無客戶個案資料</p>
                            </div>
                        `;
                    }

                    // iPhone 模擬器視圖 - 列表卡片
                    const caseCardsHtml = data.items.map(item => `
                        <div style="background: white; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                                <div style="flex: 1;">
                                    <h4 style="margin: 0; font-size: 16px; font-weight: 600; color: #1d1d1f;">${item.client_name}</h4>
                                    <p style="margin: 4px 0 0 0; font-size: 13px; color: #6e6e73;">${item.client_email}</p>
                                </div>
                                <span style="padding: 4px 12px; border-radius: 12px; font-size: 11px; white-space: nowrap; margin-left: 8px; background: ${
                                    item.case_status === 1 ? '#fff4e6' :
                                    item.case_status === 2 ? '#d1f4e0' :
                                    '#e0f0ff'
                                }; color: ${
                                    item.case_status === 1 ? '#f5a623' :
                                    item.case_status === 2 ? '#0d894f' :
                                    '#0071e3'
                                };">${item.case_status_label}</span>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px;">
                                <div>
                                    <div style="color: #86868b; font-size: 11px;">身份</div>
                                    <div style="color: #1d1d1f; font-weight: 500;">${item.identity_option}</div>
                                </div>
                                <div>
                                    <div style="color: #86868b; font-size: 11px;">會談次數</div>
                                    <div style="color: #1d1d1f; font-weight: 500;">${item.total_sessions}</div>
                                </div>
                                <div style="grid-column: 1 / -1;">
                                    <div style="color: #86868b; font-size: 11px;">最後諮詢</div>
                                    <div style="color: #1d1d1f; font-weight: 500;">${item.last_session_date_display || '未開始'}</div>
                                </div>
                            </div>
                        </div>
                    `).join('');

                    return `
                        <style>
                            .iphone-preview {
                                width: 390px;
                                height: 844px;
                                background: #000;
                                border-radius: 50px;
                                padding: 12px;
                                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                                position: relative;
                                margin: 0 auto;
                            }
                            .iphone-preview .notch {
                                position: absolute;
                                top: 0;
                                left: 50%;
                                transform: translateX(-50%);
                                width: 120px;
                                height: 30px;
                                background: #000;
                                border-radius: 0 0 20px 20px;
                                z-index: 10;
                            }
                            .iphone-preview .screen {
                                width: 100%;
                                height: 100%;
                                background: #fff;
                                border-radius: 40px;
                                overflow: hidden;
                            }
                            .iphone-preview .status-bar {
                                display: flex;
                                justify-content: space-between;
                                padding: 0 20px;
                                height: 44px;
                                align-items: center;
                                font-size: 15px;
                                font-weight: 600;
                            }
                            .iphone-preview .status-bar .time {
                                margin-left: 60px;
                            }
                            .iphone-preview .nav-bar {
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                padding: 16px 20px;
                                border-bottom: 1px solid #e5e5e7;
                            }
                            .iphone-preview .nav-bar .title {
                                font-size: 17px;
                                font-weight: 600;
                                flex: 1;
                                text-align: center;
                            }
                            .iphone-preview .nav-bar .add-btn {
                                width: 36px;
                                height: 36px;
                                background: #5ac8fa;
                                border-radius: 50%;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                color: #fff;
                                font-size: 24px;
                            }
                            .iphone-preview .content {
                                height: calc(100% - 44px - 60px - 50px);
                                overflow-y: auto;
                                padding: 12px 16px;
                                background: #f9f9f9;
                            }
                        </style>
                        <div class="iphone-preview">
                            <div class="notch"></div>
                            <div class="screen">
                                <div class="status-bar">
                                    <span class="time">9:41</span>
                                    <div>⚡️ 📶 🔋</div>
                                </div>
                                <div class="nav-bar">
                                    <div>‹</div>
                                    <div class="title">個案列表</div>
                                    <div class="add-btn">+</div>
                                </div>
                                <div class="content">
                                    ${caseCardsHtml}
                                </div>
                            </div>
                        </div>
                    `;
                }

            },

            'create-client-case': {
                title: '建立客戶個案',
                subtitle: 'POST /api/v1/ui/client-case',
                init: async () => {
                    // Ensure schemas are loaded
                    if (!state.clientSchema || !state.caseSchema) {
                        await loadFieldSchemas();
                    }
                },
                renderForm: () => {
                    // Check if schemas are loaded
                    if (!state.clientSchema || !state.caseSchema) {
                        return `
                            ${renderTenantBanner()}
                            <div class="info-card" style="background: #fff3cd; border-color: #ffc107;">
                                <p>⏳ 正在載入 Schema...</p>
                            </div>
                        `;
                    }

                    let html = `
                        ${renderTenantBanner()}
                        <div class="info-card">
                            <p>➕ 同時建立 Client + Case</p>
                            <p style="color: #86868b; font-size: 14px; margin-top: 8px;">• Client Code 和 Case Number 自動生成</p>
                            <p style="color: #86868b; font-size: 14px;">• 表單完全基於 Schema 動態生成</p>
                        </div>

                        <button class="btn" onclick="generateRandomClientData()" style="background: #10b981; color: white; margin-bottom: 16px; width: 100%;">
                            🎲 隨機生成測試資料
                        </button>
                    `;

                    // 动态生成 Client 字段
                    if (state.clientSchema?.sections) {
                        const requiredFields = [];
                        const optionalFields = [];

                        state.clientSchema.sections.forEach(section => {
                            section.fields.forEach(field => {
                                if (field.required) {
                                    requiredFields.push(field);
                                } else {
                                    optionalFields.push(field);
                                }
                            });
                        });

                        // 必填字段
                        if (requiredFields.length > 0) {
                            html += '<h4 style="margin: 20px 0 12px;">📝 Client 必填欄位</h4>';
                            requiredFields.forEach(field => {
                                html += window.renderFormField(field, 'cc-client');
                            });
                        }

                        // 选填字段
                        if (optionalFields.length > 0) {
                            html += '<h4 style="margin: 20px 0 12px;">📋 Client 選填欄位</h4>';
                            optionalFields.forEach(field => {
                                html += window.renderFormField(field, 'cc-client');
                            });
                        }
                    }

                    // 动态生成 Case 字段
                    if (state.caseSchema?.sections) {
                        html += '<h4 style="margin: 20px 0 12px;">📋 Case 選填欄位</h4>';
                        state.caseSchema.sections.forEach(section => {
                            section.fields.forEach(field => {
                                // Skip case_number and status (auto-generated)
                                if (field.key !== 'case_number' && field.key !== 'status') {
                                    html += window.renderFormField(field, 'cc-case');
                                }
                            });
                        });
                    }

                    html += '<button class="btn btn-primary" onclick="executeCreateClientCase()">建立</button>';
                    return html;
                },
                execute: async () => {
                    const requestBody = {};

                    // 动态收集 Client 字段数据
                    if (state.clientSchema?.sections) {
                        state.clientSchema.sections.forEach(section => {
                            section.fields.forEach(field => {
                                const fieldId = 'cc-client-' + field.key;
                                const element = document.getElementById(fieldId);
                                if (element) {
                                    const value = element.value;
                                    if (value || field.required) {
                                        requestBody[field.key] = value || undefined;
                                    }
                                }
                            });
                        });
                    }

                    // 动态收集 Case 字段数据
                    if (state.caseSchema?.sections) {
                        state.caseSchema.sections.forEach(section => {
                            section.fields.forEach(field => {
                                // Skip auto-generated fields
                                if (field.key === 'case_number' || field.key === 'status') return;

                                const fieldId = 'cc-case-' + field.key;
                                const element = document.getElementById(fieldId);
                                if (element) {
                                    const value = element.value;
                                    if (value) {
                                        // Case fields use 'case_' prefix
                                        requestBody['case_' + field.key] = value;
                                    }
                                }
                            });
                        });
                    }

                    console.log('📤 Request Body:', requestBody);

                    const response = await fetch(`${BASE_URL}/api/v1/ui/client-case`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestBody)
                    });
                    const data = await response.json();

                    // Refresh the list after successful creation
                    if (response.ok) {
                        const listResponse = await fetch(`${BASE_URL}/api/v1/ui/client-case-list?skip=0&limit=100`, {
                            headers: { 'Authorization': `Bearer ${state.token}` }
                        });
                        if (listResponse.ok) {
                            const listData = await listResponse.json();
                            state.clientCases = listData.items;
                            console.log('✅ Client-case list refreshed after creation');
                        }
                    }

                    return { response, data };
                },
                                renderPreview: (data) => `
                    <style>
                        .iphone-preview {
                            width: 390px;
                            height: 844px;
                            background: #000;
                            border-radius: 50px;
                            padding: 12px;
                            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                            position: relative;
                            margin: 0 auto;
                        }
                        .iphone-preview .notch {
                            position: absolute;
                            top: 0;
                            left: 50%;
                            transform: translateX(-50%);
                            width: 120px;
                            height: 30px;
                            background: #000;
                            border-radius: 0 0 20px 20px;
                            z-index: 10;
                        }
                        .iphone-preview .screen {
                            width: 100%;
                            height: 100%;
                            background: #fff;
                            border-radius: 40px;
                            overflow: hidden;
                        }
                        .iphone-preview .status-bar {
                            display: flex;
                            justify-content: space-between;
                            padding: 0 20px;
                            height: 44px;
                            align-items: center;
                            font-size: 15px;
                            font-weight: 600;
                        }
                        .iphone-preview .status-bar .time {
                            margin-left: 60px;
                        }
                        .iphone-preview .nav-bar {
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 16px 20px;
                            border-bottom: 1px solid #e5e5e7;
                        }
                        .iphone-preview .nav-bar .title {
                            font-size: 17px;
                            font-weight: 600;
                            flex: 1;
                            text-align: center;
                        }
                        .iphone-preview .content {
                            height: calc(100% - 44px - 60px);
                            overflow-y: auto;
                            padding: 20px 16px;
                            background: #f9f9f9;
                        }
                        .iphone-preview .success-icon {
                            width: 80px;
                            height: 80px;
                            background: #34c759;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            margin: 40px auto 24px;
                            font-size: 48px;
                        }
                        .iphone-preview .detail-card {
                            background: white;
                            border-radius: 12px;
                            padding: 16px;
                            margin-bottom: 12px;
                            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                        }
                        .iphone-preview .detail-row {
                            display: flex;
                            justify-content: space-between;
                            padding: 10px 0;
                            border-bottom: 1px solid #f0f0f0;
                        }
                        .iphone-preview .detail-row:last-child {
                            border-bottom: none;
                        }
                        .iphone-preview .detail-label {
                            font-size: 13px;
                            color: #86868b;
                        }
                        .iphone-preview .detail-value {
                            font-size: 14px;
                            color: #1d1d1f;
                            font-weight: 500;
                            text-align: right;
                            max-width: 200px;
                            word-wrap: break-word;
                        }
                    </style>
                    <div class="iphone-preview">
                        <div class="notch"></div>
                        <div class="screen">
                            <div class="status-bar">
                                <span class="time">9:41</span>
                                <div>⚡️ 📶 🔋</div>
                            </div>
                            <div class="nav-bar">
                                <div>‹</div>
                                <div class="title">建立成功</div>
                                <div style="width: 24px;"></div>
                            </div>
                            <div class="content">
                                <div class="success-icon">✓</div>
                                <h2 style="text-align: center; font-size: 20px; margin-bottom: 8px;">個案建立成功！</h2>
                                <p style="text-align: center; color: #86868b; font-size: 14px; margin-bottom: 32px;">Client 和 Case 已同時建立</p>

                                <div class="detail-card">
                                    <h3 style="font-size: 15px; margin-bottom: 12px; color: #1d1d1f;">👤 Client 資訊</h3>
                                    <div class="detail-row">
                                        <span class="detail-label">姓名</span>
                                        <span class="detail-value">${data.client_name}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Client Code</span>
                                        <span class="detail-value" style="color: #007aff; font-weight: 600;">${data.client_code}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Email</span>
                                        <span class="detail-value">${data.client_email}</span>
                                    </div>
                                </div>

                                <div class="detail-card">
                                    <h3 style="font-size: 15px; margin-bottom: 12px; color: #1d1d1f;">📋 Case 資訊</h3>
                                    <div class="detail-row">
                                        <span class="detail-label">Case Number</span>
                                        <span class="detail-value" style="color: #34c759; font-weight: 600;">${data.case_number}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">狀態</span>
                                        <span class="detail-value">${data.case_status}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">建立時間</span>
                                        <span class="detail-value">${new Date(data.created_at).toLocaleString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `

            },

            'get-client-case-detail': {
                title: '🔍 獲取個案詳情',
                subtitle: 'GET /api/v1/ui/client-case/{id}',
                init: async () => {
                    // Ensure schemas are loaded for preview rendering
                    if (!state.clientSchema || !state.caseSchema) {
                        await loadFieldSchemas();
                    }
                },
                renderForm: () => {
                    const caseOptions = (state.clientCases || []).map(c =>
                        `<option value="${c.case_id}">${c.client_name} - ${c.case_number}</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="info-card">
                            <p>🔍 獲取單一個案的完整資訊（動態欄位）</p>
                            <p style="color: #86868b; font-size: 14px; margin-top: 8px;">
                                • 用於 iOS 更新表單載入現有資料<br>
                                • 返回所有 Client 和 Case 欄位（基於 Schema）
                            </p>
                        </div>

                        <div class="form-group">
                            <label>選擇個案 *</label>
                            <select id="detail-case-id">
                                <option value="">-- 請先執行「列出客戶個案」--</option>
                                ${caseOptions}
                            </select>
                        </div>

                        <button class="btn btn-primary" onclick="executeGetClientCaseDetail()">獲取詳情</button>
                    `;
                },
                execute: async () => {
                    const caseId = document.getElementById('detail-case-id').value;
                    if (!caseId) {
                        throw new Error('Please select a case');
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/ui/client-case/${caseId}`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();
                    return { response, data };
                },
                                                renderPreview: (data) => {
                    // Check if schemas are loaded
                    if (!state.clientSchema || !state.caseSchema) {
                        return `
                            <div class="info-card" style="background: #fff3cd; border-color: #ffc107;">
                                <p style="color: #856404;">⚠️ Schema 未載入，無法顯示詳情</p>
                                <p style="color: #856404; font-size: 13px; margin-top: 8px;">請重新整理頁面或重新登入</p>
                            </div>
                        `;
                    }

                    // Generate Client fields dynamically from schema
                    let clientFieldsHTML = '';
                    state.clientSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const value = data[field.key] || data['client_' + field.key] || '';
                            // Format value based on type
                            let displayValue = value || '-';
                            if (field.type === 'date' && value) {
                                displayValue = value.split('T')[0];
                            }

                            clientFieldsHTML += '<div class="detail-row">' +
                                '<span class="detail-label">' + field.label + '</span>' +
                                '<span class="detail-value">' + displayValue + '</span>' +
                            '</div>';
                        });
                    });

                    // Generate Case fields dynamically from schema
                    let caseFieldsHTML = '';
                    state.caseSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const value = data[field.key] || data['case_' + field.key] || '';
                            let displayValue = value || '-';
                                    // Handle case_status specially to show label
                                    if (field.key === 'status' && data.case_status_label) {
                                        displayValue = data.case_status_label;
                                    }

                                    caseFieldsHTML += '<div class="detail-row">' +
                                        '<span class="detail-label">' + field.label + '</span>' +
                                        '<span class="detail-value">' + displayValue + '</span>' +
                                    '</div>';
                            });
                        });

                    return '<style>' +
                        '.iphone-preview { width: 390px; height: 844px; background: #000; border-radius: 50px; padding: 12px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); position: relative; margin: 0 auto; }' +
                        '.iphone-preview .notch { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 120px; height: 30px; background: #000; border-radius: 0 0 20px 20px; z-index: 10; }' +
                        '.iphone-preview .screen { width: 100%; height: 100%; background: #fff; border-radius: 40px; overflow: hidden; }' +
                        '.iphone-preview .status-bar { display: flex; justify-content: space-between; padding: 0 20px; height: 44px; align-items: center; font-size: 15px; font-weight: 600; }' +
                        '.iphone-preview .status-bar .time { margin-left: 60px; }' +
                        '.iphone-preview .nav-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e5e5e7; background: white; }' +
                        '.iphone-preview .nav-bar .title { font-size: 17px; font-weight: 600; flex: 1; text-align: center; }' +
                        '.iphone-preview .content { height: calc(100% - 44px - 60px); overflow-y: auto; padding: 0; background: #f9f9f9; }' +
                        '.iphone-preview .hero-section { background: white; padding: 24px 20px; border-bottom: 1px solid #e5e5e7; }' +
                        '.iphone-preview .hero-name { font-size: 24px; font-weight: 700; color: #1d1d1f; margin-bottom: 4px; }' +
                        '.iphone-preview .hero-email { font-size: 14px; color: #6e6e73; }' +
                        '.iphone-preview .section { background: white; margin-top: 12px; padding: 16px 20px; }' +
                        '.iphone-preview .section-title { font-size: 13px; font-weight: 600; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }' +
                        '.iphone-preview .detail-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }' +
                        '.iphone-preview .detail-row:last-child { border-bottom: none; }' +
                        '.iphone-preview .detail-label { font-size: 14px; color: #1d1d1f; }' +
                        '.iphone-preview .detail-value { font-size: 14px; color: #86868b; text-align: right; max-width: 200px; word-wrap: break-word; }' +
                        '.iphone-preview .case-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; background: #e0f0ff; color: #0071e3; font-weight: 500; }' +
                    '</style>' +
                    '<div class="iphone-preview">' +
                        '<div class="notch"></div>' +
                        '<div class="screen">' +
                            '<div class="status-bar">' +
                                '<span class="time">9:41</span>' +
                                '<div>⚡️ 📶 🔋</div>' +
                            '</div>' +
                            '<div class="nav-bar">' +
                                '<div>‹</div>' +
                                '<div class="title">個案詳情</div>' +
                                '<div>編輯</div>' +
                            '</div>' +
                            '<div class="content">' +
                                '<div class="hero-section">' +
                                    '<div class="hero-name">' + data.client_name + '</div>' +
                                    '<div class="hero-email">' + (data.client_email || data.email) + '</div>' +
                                    '<div style="margin-top: 12px;">' +
                                        '<span class="case-badge">' + data.identity_option + '</span>' +
                                    '</div>' +
                                '</div>' +
                                '<div class="section">' +
                                    '<div class="section-title">Client 資訊</div>' +
                                    clientFieldsHTML +
                                '</div>' +
                                '<div class="section">' +
                                    '<div class="section-title">個案資訊</div>' +
                                    caseFieldsHTML +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
                }


            },

            'update-client-case': {
                title: '更新客戶個案',
                subtitle: 'PATCH /api/v1/ui/client-case/{id}',
                renderForm: () => {
                    // Check if schemas are loaded, if not, load them automatically
                    if ((!state.clientSchema || !state.caseSchema) && state.token) {
                        // Trigger async load and re-render
                        setTimeout(async () => {
                            await loadFieldSchemas();
                            selectStep('update-client-case'); // Re-render this step
                        }, 100);

                        return `
                            ${renderTenantBanner()}
                            <div class="info-card" style="background: #fff3cd; border-color: #ffc107;">
                                <p style="color: #856404;">
                                    ⏳ 正在載入表單 Schema...
                                </p>
                            </div>
                        `;
                    }

                    // Generate dropdown from state.clientCases
                    const caseOptions = (state.clientCases || []).map(c =>
                        `<option value="${c.case_id}">${c.client_name} - ${c.case_number}</option>`
                    ).join('');

                    // Generate dynamic form from schemas
                    const clientFormHTML = generateFormFromSchema(state.clientSchema, 'cc-update-client-');
                    const caseFormHTML = generateFormFromSchema(state.caseSchema, 'cc-update-case-');

                    return `
                        ${renderTenantBanner()}
                        <div class="info-card">
                            <p>✏️ 更新客戶與個案資料（動態欄位 by Tenant）</p>
                            <p style="color: #86868b; font-size: 14px; margin-top: 8px;">
                                • 所有欄位都是選填，只更新提供的欄位<br>
                                • 欄位根據租戶 (${state.currentUser?.tenant_id || 'unknown'}) 動態生成
                            </p>
                        </div>

                        <div class="form-group">
                            <label>選擇個案 *</label>
                            <select id="cc-update-id" onchange="loadClientCaseForUpdate(this.value)">
                                <option value="">-- 請先執行「列出客戶個案」--</option>
                                ${caseOptions}
                            </select>
                        </div>

                        <h4 style="margin: 20px 0 12px;">📝 Client 欄位 (選填)</h4>
                        ${clientFormHTML}

                        <h4 style="margin: 20px 0 12px;">📋 Case 欄位 (選填)</h4>
                        ${caseFormHTML}

                        <button class="btn btn-primary" onclick="executeUpdateClientCase()">更新</button>
                    `;
                },
                execute: async () => {
                    const caseId = document.getElementById('cc-update-id').value;
                    if (!caseId) {
                        throw new Error('Please select a case to update');
                    }

                    // Collect values dynamically from schemas
                    const clientValues = collectFormValues(state.clientSchema, 'cc-update-client-');
                    const caseValues = collectFormValues(state.caseSchema, 'cc-update-case-');

                    // Merge client and case values
                    const requestBody = { ...clientValues };

                    // Map case fields to API request format (add case_ prefix dynamically)
                    Object.keys(caseValues).forEach(key => {
                        if (caseValues[key] !== undefined && caseValues[key] !== null && caseValues[key] !== '') {
                            requestBody['case_' + key] = caseValues[key];
                        }
                    });

                    console.log('📤 Update request body:', requestBody);

                    const response = await fetch(`${BASE_URL}/api/v1/ui/client-case/${caseId}`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${state.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestBody)
                    });
                    const data = await response.json();

                    // Refresh the list after successful update
                    if (response.ok) {
                        const listResponse = await fetch(`${BASE_URL}/api/v1/ui/client-case-list?skip=0&limit=100`, {
                            headers: { 'Authorization': `Bearer ${state.token}` }
                        });
                        if (listResponse.ok) {
                            const listData = await listResponse.json();
                            state.clientCases = listData.items;
                            console.log('✅ Client-case list refreshed after update');
                        }
                    }

                    return { response, data };
                },
                                renderPreview: (data) => `
                    <style>
                        .iphone-preview {
                            width: 390px;
                            height: 844px;
                            background: #000;
                            border-radius: 50px;
                            padding: 12px;
                            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                            position: relative;
                            margin: 0 auto;
                        }
                        .iphone-preview .notch {
                            position: absolute;
                            top: 0;
                            left: 50%;
                            transform: translateX(-50%);
                            width: 120px;
                            height: 30px;
                            background: #000;
                            border-radius: 0 0 20px 20px;
                            z-index: 10;
                        }
                        .iphone-preview .screen {
                            width: 100%;
                            height: 100%;
                            background: #fff;
                            border-radius: 40px;
                            overflow: hidden;
                        }
                        .iphone-preview .status-bar {
                            display: flex;
                            justify-content: space-between;
                            padding: 0 20px;
                            height: 44px;
                            align-items: center;
                            font-size: 15px;
                            font-weight: 600;
                        }
                        .iphone-preview .status-bar .time {
                            margin-left: 60px;
                        }
                        .iphone-preview .nav-bar {
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 16px 20px;
                            border-bottom: 1px solid #e5e5e7;
                        }
                        .iphone-preview .nav-bar .title {
                            font-size: 17px;
                            font-weight: 600;
                            flex: 1;
                            text-align: center;
                        }
                        .iphone-preview .content {
                            height: calc(100% - 44px - 60px);
                            overflow-y: auto;
                            padding: 20px 16px;
                            background: #f9f9f9;
                        }
                        .iphone-preview .success-icon {
                            width: 64px;
                            height: 64px;
                            background: #34c759;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            margin: 32px auto 20px;
                            font-size: 40px;
                        }
                        .iphone-preview .update-card {
                            background: white;
                            border-radius: 12px;
                            padding: 20px;
                            margin-top: 16px;
                            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                        }
                        .iphone-preview .update-row {
                            display: flex;
                            justify-content: space-between;
                            padding: 12px 0;
                            border-bottom: 1px solid #f0f0f0;
                        }
                        .iphone-preview .update-row:last-child {
                            border-bottom: none;
                        }
                        .iphone-preview .update-label {
                            font-size: 14px;
                            color: #86868b;
                        }
                        .iphone-preview .update-value {
                            font-size: 15px;
                            color: #1d1d1f;
                            font-weight: 600;
                            text-align: right;
                            max-width: 180px;
                        }
                    </style>
                    <div class="iphone-preview">
                        <div class="notch"></div>
                        <div class="screen">
                            <div class="status-bar">
                                <span class="time">9:41</span>
                                <div>⚡️ 📶 🔋</div>
                            </div>
                            <div class="nav-bar">
                                <div>‹</div>
                                <div class="title">更新成功</div>
                                <div style="width: 24px;"></div>
                            </div>
                            <div class="content">
                                <div class="success-icon">✓</div>
                                <h2 style="text-align: center; font-size: 20px; margin-bottom: 8px;">更新成功</h2>
                                <p style="text-align: center; color: #86868b; font-size: 14px; margin-bottom: 24px;">個案資料已更新</p>

                                <div class="update-card">
                                    <div class="update-row">
                                        <span class="update-label">Client 姓名</span>
                                        <span class="update-value">${data.client_name}</span>
                                    </div>
                                    <div class="update-row">
                                        <span class="update-label">Client Code</span>
                                        <span class="update-value" style="color: #007aff;">${data.client_code}</span>
                                    </div>
                                    <div class="update-row">
                                        <span class="update-label">Case Number</span>
                                        <span class="update-value" style="color: #34c759;">${data.case_number}</span>
                                    </div>
                                    <div class="update-row">
                                        <span class="update-label">Case Status</span>
                                        <span class="update-value">${data.case_status}</span>
                                    </div>
                                </div>

                                <div style="background: #e8f5e9; border-radius: 12px; padding: 16px; margin-top: 16px; text-align: center;">
                                    <p style="color: #2e7d32; font-size: 13px; margin: 0;">
                                        ✅ ${data.message || '更新成功'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                `

            },

            'delete-client-case': {
                title: '刪除客戶個案',
                subtitle: 'DELETE /api/v1/ui/client-case/{id}',
                renderForm: () => {
                    const caseOptions = (state.clientCases || []).map(c =>
                        `<option value="${c.case_id}">${c.client_name} - ${c.case_number}</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="info-card" style="background: #fef2f2; border-color: #ef4444;">
                            <p style="color: #991b1b;">⚠️ 刪除個案（軟刪除）</p>
                            <p style="color: #991b1b; font-size: 14px; margin-top: 8px;">
                                • 只刪除 Case，不刪除 Client<br>
                                • 軟刪除，資料不會真正消失
                            </p>
                        </div>

                        <div class="form-group">
                            <label>選擇要刪除的個案 *</label>
                            <select id="cc-delete-id">
                                <option value="">-- 請先執行「列出客戶個案」--</option>
                                ${caseOptions}
                            </select>
                        </div>

                        <button class="btn btn-danger" onclick="executeDeleteClientCase()"
                                style="background: #ef4444;">刪除</button>
                    `;
                },
                execute: async () => {
                    const caseId = document.getElementById('cc-delete-id').value;
                    if (!caseId) {
                        throw new Error('Please select a case to delete');
                    }

                    if (!confirm('確定要刪除此個案嗎？此操作無法復原。')) {
                        throw new Error('Operation cancelled');
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/ui/client-case/${caseId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();

                    // Refresh the list after successful deletion
                    if (response.ok) {
                        const listResponse = await fetch(`${BASE_URL}/api/v1/ui/client-case-list?skip=0&limit=100`, {
                            headers: { 'Authorization': `Bearer ${state.token}` }
                        });
                        if (listResponse.ok) {
                            const listData = await listResponse.json();
                            state.clientCases = listData.items;
                            console.log('✅ Client-case list refreshed after deletion');
                        }
                    }

                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="background: #d1f4e0; border-color: #0d894f;">
                        <h3 style="color: #0d894f;">✅ ${data.message}</h3>
                        <div class="info-row">
                            <span class="info-label">Case Number</span>
                            <span class="info-value">${data.case_number}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">刪除時間</span>
                            <span class="info-value">${new Date(data.deleted_at).toLocaleString('zh-TW')}</span>
                        </div>
                    </div>
                `
            },
            'get-analysis-logs': {
                title: '📋 查看分析記錄',
                subtitle: 'GET /api/v1/sessions/{session_id}/analysis-logs',
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || 'Unknown'} - Session ${s.session_number}</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="info-card">
                            <p style="font-size: 13px; color: #6b7280;">查看會談的所有關鍵字分析記錄</p>
                        </div>

                        <div class="form-group">
                            <label>選擇會談 *</label>
                            <select id="log-session-id">
                                <option value="">-- 請先執行「列出會談」--</option>
                                ${sessionOptions}
                            </select>
                        </div>

                        <button class="btn btn-primary" onclick="executeGetAnalysisLogs()">查看記錄</button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('log-session-id').value;
                    if (!sessionId) {
                        throw new Error('Please select a session');
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/analysis-logs`, {
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });
                    const data = await response.json();

                    if (response.ok) {
                        state.currentAnalysisLogs = data.logs;
                        state.currentLogSessionId = sessionId;
                    }

                    return { response, data };
                },
                renderPreview: (data) => {
                    if (data.total_logs === 0) {
                        return `
                            <div class="info-card">
                                <h3>📋 分析記錄（無記錄）</h3>
                                <p style="color: #6b7280; font-size: 13px;">此會談尚無關鍵字分析記錄</p>
                            </div>
                        `;
                    }

                    const logsHtml = data.logs.map(log => `
                        <div class="info-card" style="margin-bottom: 12px; background: ${log.fallback ? '#fef3c7' : '#f0fdf4'}; border-color: ${log.fallback ? '#f59e0b' : '#10b981'};">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <h4 style="margin: 0; color: ${log.fallback ? '#92400e' : '#065f46'};">
                                    #${log.log_index} ${log.fallback ? '⚠️ 備援分析' : '✅ AI 分析'}
                                </h4>
                                <span style="font-size: 11px; color: #6b7280;">${new Date(log.analyzed_at).toLocaleString('zh-TW')}</span>
                            </div>
                            <div class="info-row" style="margin-top: 8px;">
                                <span class="info-label">逐字稿片段</span>
                                <span class="info-value" style="font-size: 12px;">${log.transcript_segment}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">關鍵字</span>
                                <span class="info-value">${log.keywords.join(', ')}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">分類</span>
                                <span class="info-value">${log.categories.join(', ')}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">信心分數</span>
                                <span class="info-value">${(log.confidence * 100).toFixed(0)}%</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">諮詢師洞見</span>
                                <span class="info-value" style="font-size: 12px;">${log.counselor_insights}</span>
                            </div>
                        </div>
                    `).join('');

                    return `
                        <div class="info-card">
                            <h3>📋 分析記錄</h3>
                            <div class="info-row">
                                <span class="info-label">Session ID</span>
                                <span class="info-value" style="font-size: 11px;">${data.session_id}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">總記錄數</span>
                                <span class="info-value">${data.total_logs}</span>
                            </div>
                        </div>
                        ${logsHtml}
                    `;
                }
            },
            'delete-analysis-log': {
                title: '🗑️ 刪除分析記錄',
                subtitle: 'DELETE /api/v1/sessions/{session_id}/analysis-logs/{log_index}',
                renderForm: () => {
                    const sessionOptions = (state.sessions || []).map(s =>
                        `<option value="${s.id}">${s.client_name || 'Unknown'} - Session ${s.session_number}</option>`
                    ).join('');

                    const logOptions = (state.currentAnalysisLogs || []).map(log =>
                        `<option value="${log.log_index}">#${log.log_index} - ${log.transcript_segment.substring(0, 50)}...</option>`
                    ).join('');

                    return `
                        ${renderTenantBanner()}
                        <div class="info-card" style="background: #fef2f2; border-color: #ef4444;">
                            <p style="color: #991b1b;">⚠️ 刪除分析記錄</p>
                            <p style="color: #991b1b; font-size: 14px; margin-top: 8px;">
                                刪除後無法復原，索引會自動重新計算
                            </p>
                        </div>

                        <div class="form-group">
                            <label>選擇會談 *</label>
                            <select id="delete-log-session-id" onchange="loadLogsForDeletion()">
                                <option value="">-- 請先執行「列出會談」--</option>
                                ${sessionOptions}
                            </select>
                        </div>

                        <div class="form-group">
                            <label>選擇要刪除的記錄 *</label>
                            <select id="delete-log-index">
                                <option value="">-- 請先選擇會談並執行「查看分析記錄」--</option>
                                ${logOptions}
                            </select>
                        </div>

                        <button class="btn btn-danger" onclick="executeDeleteAnalysisLog()"
                                style="background: #ef4444;">刪除</button>
                    `;
                },
                execute: async () => {
                    const sessionId = document.getElementById('delete-log-session-id').value;
                    const logIndex = document.getElementById('delete-log-index').value;

                    if (!sessionId || logIndex === '') {
                        throw new Error('Please select both session and log entry');
                    }

                    if (!confirm(`確定要刪除此分析記錄 #${logIndex} 嗎？此操作無法復原。`)) {
                        throw new Error('Operation cancelled');
                    }

                    const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/analysis-logs/${logIndex}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${state.token}` }
                    });

                    // 204 No Content - success
                    if (response.status === 204) {
                        // Refresh logs after deletion
                        const refreshResponse = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/analysis-logs`, {
                            headers: { 'Authorization': `Bearer ${state.token}` }
                        });
                        if (refreshResponse.ok) {
                            const refreshData = await refreshResponse.json();
                            state.currentAnalysisLogs = refreshData.logs;
                        }

                        return {
                            response,
                            data: {
                                message: `分析記錄 #${logIndex} 已刪除`,
                                session_id: sessionId,
                                deleted_index: logIndex
                            }
                        };
                    }

                    const data = await response.json();
                    return { response, data };
                },
                renderPreview: (data) => `
                    <div class="info-card" style="background: #d1f4e0; border-color: #0d894f;">
                        <h3 style="color: #0d894f;">✅ ${data.message}</h3>
                        <div class="info-row">
                            <span class="info-label">Session ID</span>
                            <span class="info-value" style="font-size: 11px;">${data.session_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">已刪除索引</span>
                            <span class="info-value">#${data.deleted_index}</span>
                        </div>
                        <p style="font-size: 12px; color: #065f46; margin-top: 8px;">剩餘記錄的索引已自動重新計算</p>
                    </div>
                `
            }
        };

        // Event handlers
        document.querySelectorAll('.flow-step').forEach(step => {
            step.addEventListener('click', () => {
                const stepKey = step.dataset.step;
                selectStep(stepKey);
            });
        });

        async function selectStep(stepKey) {
            // Update active state
            document.querySelectorAll('.flow-step').forEach(s => s.classList.remove('active'));
            document.querySelector(`[data-step="${stepKey}"]`).classList.add('active');

            // Update UI
            const stepConfig = steps[stepKey];
            document.getElementById('action-title').textContent = stepConfig.title;
            document.getElementById('action-subtitle').textContent = stepConfig.subtitle;

            // Call init function if exists (await if async)
            if (stepConfig.init) {
                await stepConfig.init();
            }

            // Render form after init completes
            document.getElementById('action-form').innerHTML = stepConfig.renderForm();

            document.getElementById('preview-title').textContent = stepConfig.title;
            document.getElementById('preview-subtitle').textContent = stepConfig.subtitle;

            // Clear preview content when switching steps
            document.getElementById('preview-content').innerHTML = `
                <div class="empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p>填寫參數並執行 API</p>
                </div>
            `;

            // Hide response initially
            document.getElementById('response-section').style.display = 'none';
        }

        async function executeStep(stepKey) {
            const stepConfig = steps[stepKey];
            const stepElement = document.querySelector(`[data-step="${stepKey}"]`);

            // Find the button in the action form and disable it with loading state
            const button = document.querySelector('#action-form .btn-primary');
            const originalText = button?.textContent;

            try {
                stepElement.classList.remove('completed', 'error');

                // Set loading state
                if (button) {
                    button.disabled = true;
                    button.textContent = '處理中...';
                }

                const result = await stepConfig.execute();
                const { response, data } = result;

                // Show response
                const responseSection = document.getElementById('response-section');
                const responseStatus = document.getElementById('response-status');
                const responseContent = document.getElementById('response-content');

                responseSection.style.display = 'block';
                responseStatus.innerHTML = `<span class="status-badge status-${response.ok ? 'success' : 'error'}">${response.status} ${response.statusText}</span>`;
                responseContent.textContent = JSON.stringify(data, null, 2);

                if (response.ok) {
                    stepElement.classList.add('completed');
                    // Update preview
                    if (stepConfig.renderPreview) {
                        // Pass the entire result object for steps that need it (like view-report)
                        // Otherwise just pass data for backwards compatibility
                        const previewArg = (stepKey === 'view-report') ? result : data;
                        document.getElementById('preview-content').innerHTML = stepConfig.renderPreview(previewArg);
                    }
                } else {
                    stepElement.classList.add('error');
                    document.getElementById('preview-content').innerHTML = `
                        <div class="info-card" style="border-color: #ef4444;">
                            <h3 style="color: #ef4444;">❌ 錯誤</h3>
                            <p style="color: #991b1b;">${data.detail || '請求失敗'}</p>
                        </div>
                    `;
                }
            } catch (error) {
                stepElement.classList.add('error');
                document.getElementById('response-section').style.display = 'block';
                document.getElementById('response-status').innerHTML = `<span class="status-badge status-error">Error</span>`;
                document.getElementById('response-content').textContent = error.message;
            } finally {
                // Restore button state
                if (button) {
                    button.disabled = false;
                    button.textContent = originalText;
                }
            }
        }

        // 輪詢報告狀態
        async function pollReportStatus(reportId) {
            try {
                const response = await fetch(`${BASE_URL}/api/v1/reports/${reportId}`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });
                const data = await response.json();

                const pollingDiv = document.getElementById('polling-status');
                if (!pollingDiv) return;

                if (data.status === 'processing') {
                    pollingDiv.innerHTML = `<p style="font-size: 13px; color: #f59e0b;">⏳ 處理中... (${new Date().toLocaleTimeString('zh-TW')})</p>`;
                    setTimeout(() => pollReportStatus(reportId), 3000);
                } else if (data.status === 'draft') {
                    pollingDiv.innerHTML = `<p style="font-size: 13px; color: #10b981;">✅ 報告生成完成!</p>`;
                    // 自動重新載入查看報告
                    setTimeout(() => {
                        document.getElementById('preview-content').innerHTML = steps['generate-report'].renderPreview({
                            report_id: data.id,
                            session_id: data.session_id,
                            report: { report: data.content_json.report || data.content_json },
                            quality_summary: {
                                grade: data.quality_grade,
                                overall_score: data.quality_score,
                                strengths: data.quality_strengths,
                                improvements_needed: data.quality_weaknesses
                            }
                        });
                    }, 1000);
                } else if (data.status === 'failed') {
                    pollingDiv.innerHTML = `
                        <p style="font-size: 13px; color: #ef4444;">❌ 生成失敗</p>
                        <p style="font-size: 12px; color: #991b1b; margin-top: 8px;">${data.error_message || '未知錯誤'}</p>
                    `;
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }

        // Helper: Load session data when selecting for update
        window.loadSessionForUpdate = function() {
            const sessionId = document.getElementById('update-session-id').value;
            const session = state.sessions.find(s => s.id === sessionId);
            if (session) {
                // Set date
                const sessionDate = new Date(session.session_date);
                document.getElementById('update-session-date').value = sessionDate.toISOString().split('T')[0];

                // Set name
                document.getElementById('update-session-name').value = session.name || '';

                // Set times
                if (session.start_time) {
                    const startTime = new Date(session.start_time);
                    document.getElementById('update-session-start-time').value =
                        `${String(startTime.getHours()).padStart(2, '0')}:${String(startTime.getMinutes()).padStart(2, '0')}`;
                }
                if (session.end_time) {
                    const endTime = new Date(session.end_time);
                    document.getElementById('update-session-end-time').value =
                        `${String(endTime.getHours()).padStart(2, '0')}:${String(endTime.getMinutes()).padStart(2, '0')}`;
                }

                document.getElementById('update-session-transcript').value = session.transcript_text || '';
                document.getElementById('update-session-notes').value = session.notes || '';

                // Load reflection data if exists
                if (session.reflection) {
                    document.getElementById('update-reflection-working').value = session.reflection.working_with_client || '';
                    document.getElementById('update-reflection-source').value = session.reflection.feeling_source || '';
                    document.getElementById('update-reflection-challenges').value = session.reflection.current_challenges || '';
                    document.getElementById('update-reflection-supervision').value = session.reflection.supervision_topics || '';
                } else {
                    document.getElementById('update-reflection-working').value = '';
                    document.getElementById('update-reflection-source').value = '';
                    document.getElementById('update-reflection-challenges').value = '';
                    document.getElementById('update-reflection-supervision').value = '';
                }
            }
        };

        // Load reflection data for update form
        window.loadReflectionForUpdate = function() {
            const sessionId = document.getElementById('update-reflection-session-id').value;
            const session = state.sessions.find(s => s.id === sessionId);
            if (session && session.reflection) {
                document.getElementById('put-reflection-working').value = session.reflection.working_with_client || '';
                document.getElementById('put-reflection-source').value = session.reflection.feeling_source || '';
                document.getElementById('put-reflection-challenges').value = session.reflection.current_challenges || '';
                document.getElementById('put-reflection-supervision').value = session.reflection.supervision_topics || '';
            } else {
                document.getElementById('put-reflection-working').value = '';
                document.getElementById('put-reflection-source').value = '';
                document.getElementById('put-reflection-challenges').value = '';
                document.getElementById('put-reflection-supervision').value = '';
            }
        };

        // Load client data for update form
        window.loadClientDataForUpdate = async () => {
            const clientId = document.getElementById('update-client-id')?.value;
            if (!clientId || !state.clientFieldSchema) return;

            try {
                const response = await fetch(`${BASE_URL}/api/v1/clients/${clientId}`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });

                if (response.ok) {
                    const client = await response.json();

                    // Dynamically populate fields based on schema
                    state.clientFieldSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const inputId = `update-client-${field.key}`;
                            const element = document.getElementById(inputId);
                            if (element && client[field.key] !== undefined) {
                                element.value = client[field.key] || '';
                            }
                        });
                    });
                }
            } catch (error) {
                console.error('Failed to load client data:', error);
            }
        };

        // Load case data for update form
        window.loadCaseDataForUpdate = async () => {
            const caseId = document.getElementById('update-case-id')?.value;
            if (!caseId) return;

            try {
                const response = await fetch(`${BASE_URL}/api/v1/cases/${caseId}`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });

                if (response.ok) {
                    const caseData = await response.json();

                    // Populate fields
                    const statusEl = document.getElementById('update-case-status');
                    const summaryEl = document.getElementById('update-case-summary');
                    const goalsEl = document.getElementById('update-case-goals');
                    const problemEl = document.getElementById('update-case-problem');

                    if (statusEl) statusEl.value = caseData.status || '';
                    if (summaryEl) summaryEl.value = caseData.summary || '';
                    if (goalsEl) goalsEl.value = caseData.goals || '';
                    if (problemEl) problemEl.value = caseData.problem_description || '';
                }
            } catch (error) {
                console.error('Failed to load case data:', error);
            }
        };

        // Load client-case data for update form (UI-5)
        window.loadClientCaseForUpdate = async function(caseId) {
            if (!caseId) {
                console.warn('No case selected');
                return;
            }

            console.log('📋 Fetching full case details for update:', caseId);

            try {
                // Fetch full case details from API
                const response = await fetch(`${BASE_URL}/api/v1/ui/client-case/${caseId}`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    console.error('❌ Failed to fetch case details:', errorData);
                    alert(`Failed to load case details: ${errorData.detail || 'Unknown error'}`);
                    return;
                }

                const caseDetail = await response.json();
                console.log('✅ Fetched case details:', caseDetail);

                // Populate Client fields dynamically from schema
                if (state.clientSchema?.sections) {
                    state.clientSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const fieldId = 'cc-update-client-' + field.key;
                            const element = document.getElementById(fieldId);
                            if (element) {
                                // Try direct field name first, then with client_ prefix
                                let value = caseDetail[field.key] || caseDetail['client_' + field.key] || '';

                                // Handle date fields - format as YYYY-MM-DD for input[type=date]
                                if (field.type === 'date' && value) {
                                    value = value.split('T')[0];
                                }

                                element.value = value;
                                console.log('Set ' + fieldId + ' = ' + value);
                            }
                        });
                    });
                }

                // Populate Case fields dynamically from schema
                if (state.caseSchema?.sections) {
                    state.caseSchema.sections.forEach(section => {
                        section.fields.forEach(field => {
                            const fieldId = 'cc-update-case-' + field.key;
                            const element = document.getElementById(fieldId);
                            if (element) {
                                // Try direct field name first, then with case_ prefix
                                let value = caseDetail[field.key] || caseDetail['case_' + field.key] || '';

                                element.value = value;
                                console.log('Set ' + fieldId + ' = ' + value);
                            }
                        });
                    });
                }

                console.log('✅ Form populated with current values from API');

            } catch (error) {
                console.error('❌ Error loading case for update:', error);
                alert('Failed to load case details. Please try again.');
            }
        };


        // Recording segments management
        let recordingSegmentCounter = 0;

        window.addRecordingSegment = () => {
            recordingSegmentCounter++;
            const segmentNumber = recordingSegmentCounter;
            const container = document.getElementById('recordings-container');

            const segmentHtml = `
                <div class="recording-segment" id="recording-segment-${segmentNumber}" style="background: white; border: 1px solid #d1d5db; border-radius: 6px; padding: 16px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h5 style="color: #047857; margin: 0;">📝 片段 ${segmentNumber}</h5>
                        <button type="button" onclick="removeRecordingSegment(${segmentNumber})" style="background: #ef4444; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">🗑️ 刪除</button>
                    </div>
                    <input type="hidden" id="recording-${segmentNumber}-segment-number" value="${segmentNumber}" />
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                        <div class="form-group" style="margin: 0;">
                            <label style="font-size: 13px;">開始時間</label>
                            <input type="time" id="recording-${segmentNumber}-start" style="font-size: 13px; padding: 6px;" />
                        </div>
                        <div class="form-group" style="margin: 0;">
                            <label style="font-size: 13px;">結束時間</label>
                            <input type="time" id="recording-${segmentNumber}-end" style="font-size: 13px; padding: 6px;" />
                        </div>
                        <div class="form-group" style="margin: 0;">
                            <label style="font-size: 13px;">時長（秒）</label>
                            <input type="number" id="recording-${segmentNumber}-duration" placeholder="自動計算或手動填" style="font-size: 13px; padding: 6px;" />
                        </div>
                    </div>
                    <div class="form-group" style="margin: 0;">
                        <label style="font-size: 13px;">逐字稿內容</label>
                        <textarea id="recording-${segmentNumber}-transcript" rows="4" placeholder="此片段的逐字稿..." style="font-size: 13px;"></textarea>
                    </div>
                </div>
            `;

            container.insertAdjacentHTML('beforeend', segmentHtml);
        };

        window.removeRecordingSegment = (segmentNumber) => {
            const segment = document.getElementById(`recording-segment-${segmentNumber}`);
            if (segment) {
                segment.remove();
            }
        };

        window.collectRecordings = () => {
            const recordings = [];
            const segments = document.querySelectorAll('.recording-segment');

            segments.forEach((segment) => {
                const segmentId = segment.id.replace('recording-segment-', '');
                const segmentNumber = document.getElementById(`recording-${segmentId}-segment-number`)?.value;
                const startTime = document.getElementById(`recording-${segmentId}-start`)?.value;
                const endTime = document.getElementById(`recording-${segmentId}-end`)?.value;
                const duration = document.getElementById(`recording-${segmentId}-duration`)?.value;
                const transcript = document.getElementById(`recording-${segmentId}-transcript`)?.value;

                if (transcript) {  // Only include if transcript is provided
                    const sessionDate = document.getElementById('session-date')?.value;
                    const recording = {
                        segment_number: parseInt(segmentNumber),
                        transcript_text: transcript
                    };

                    if (startTime) recording.start_time = `${sessionDate} ${startTime}`;
                    if (endTime) recording.end_time = `${sessionDate} ${endTime}`;
                    if (duration) recording.duration_seconds = parseInt(duration);

                    recordings.push(recording);
                }
            });

            return recordings;
        };

        // Quick fill session test data
        window.quickFillSessionData = () => {
            const sampleTranscripts = [
                `Co: 你好，今天想聊些什麼呢？
Cl: 最近工作壓力很大，覺得快要撐不下去了。
Co: 可以多說一些嗎？是什麼樣的壓力？
Cl: 主管總是對我的工作不滿意，不管我怎麼做都覺得不夠好。
Co: 聽起來你感到很挫折，可以分享一個具體的例子嗎？
Cl: 上週我做了一份企劃案，花了很多心力，但主管只看了一眼就說這不是他要的。`,
                `Co: 上次提到的職涯方向，有新的想法嗎？
Cl: 我一直在思考，但還是很迷茫。
Co: 迷茫的感覺是什麼？
Cl: 不知道自己適合做什麼，也不確定現在的工作是不是對的選擇。
Co: 讓我們先從你的興趣開始聊起吧。`,
                `Co: 今天看起來心情不錯？
Cl: 對啊，這週工作順利很多，主管也稱讚了我。
Co: 很高興聽到這個消息！是什麼改變了？
Cl: 我開始用你上次建議的方法，先確認主管的需求再開始做。
Co: 聽起來這個策略很有效，繼續保持！`
            ];

            const sampleReflections = [
                {
                    working: '整體過程流暢輕鬆，逐漸贏得信任。首次面對職場PUA案例，獲得新的輔導經驗。',
                    source: '個案從緊張到逐步放鬆，願意開放心態分享更多。能夠建立良好的治療同盟。',
                    challenges: '當肯定個案時，仍會有自我懷疑反應；但已逐漸能接受讚賞。需要更多時間探索其內在認知模式。',
                    supervision: '如何在支持與挑戰間拿捏節奏，以及量表與質化紀錄整合方式。特別是如何處理職場創傷。'
                },
                {
                    working: '個案展現出強烈的改變動機，工作配合度高，讓會談進展順利。',
                    source: '個案對自己的困境有清楚的認知，也願意嘗試新的方法，這讓諮詢過程更有效率。',
                    challenges: '個案有時會過度理性化自己的情緒，需要引導其更深入地覺察感受。',
                    supervision: '如何幫助個案在理性思考與情緒覺察間取得平衡？是否需要引入更多情緒焦點技術？'
                },
                {
                    working: '今天的會談充滿正向能量，看到個案的進步感到很欣慰。',
                    source: '個案能夠主動分享成功經驗，展現出更多的自信和自我效能感。',
                    challenges: '需要協助個案將這次的成功經驗內化，避免未來遇到挫折時回到原點。',
                    supervision: '如何強化個案的成功經驗，建立長期的因應策略？下一步的介入重點應該放在哪裡？'
                }
            ];

            const randomIndex = Math.floor(Math.random() * sampleTranscripts.length);
            const randomTranscript = sampleTranscripts[randomIndex];
            const randomReflection = sampleReflections[randomIndex];
            const today = new Date();
            const startHour = 14 + Math.floor(Math.random() * 3); // 14-16點
            const endHour = startHour + 1;

            document.getElementById('session-date').value = today.toISOString().split('T')[0];
            document.getElementById('session-start-time').value = `${startHour}:00`;
            document.getElementById('session-end-time').value = `${endHour}:00`;
            // transcript 將從 recordings 自動聚合，暫不填充
            document.getElementById('session-transcript').value = '';
            document.getElementById('session-notes').value = '測試會談記錄';

            // Fill reflection fields
            document.getElementById('reflection-working').value = randomReflection.working;
            document.getElementById('reflection-source').value = randomReflection.source;
            document.getElementById('reflection-challenges').value = randomReflection.challenges;
            document.getElementById('reflection-supervision').value = randomReflection.supervision;

            // Clear existing recordings and add 3 sample segments
            document.getElementById('recordings-container').innerHTML = '';
            recordingSegmentCounter = 0;

            const sampleRecordingTranscripts = [
                // 片段 1: 開場與建立關係
                `Co: 你好，歡迎你來。今天想聊些什麼呢？
Cl: 嗯...最近工作壓力很大，覺得快要撐不下去了。
Co: 聽起來很辛苦。可以多說一些嗎？是什麼樣的壓力？
Cl: 主管總是對我的工作不滿意，不管我怎麼做都覺得不夠好。
Co: 聽起來你感到很挫折，可以分享一個具體的例子嗎？
Cl: 上週我做了一份企劃案，花了很多心力，但主管只看了一眼就說這不是他要的。`,
                // 片段 2: 深入探索
                `Co: 剛才提到主管的反應，你當時的感受是什麼？
Cl: 我覺得很困惑，也很受傷。我明明很努力了...
Co: 這種困惑和受傷的感覺，能再具體描述嗎？
Cl: 就像...不管我怎麼努力都得不到認可，開始懷疑自己是不是真的不適合這份工作。
Co: 你開始懷疑自己的能力了？
Cl: 對，我開始想，也許我真的做不好這個職位。`,
                // 片段 3: 總結與下次方向
                `Co: 那我們來總結一下今天談到的重點。
Cl: 好的，我覺得今天收穫很多。
Co: 你提到了工作上的挫折感，以及對自己能力的懷疑。下次我們可以更深入探討這些自我懷疑的來源。
Cl: 好的，謝謝你。我會試著記錄這週的情緒變化。
Co: 很好！那我們下次見。記得要好好照顧自己。
Cl: 謝謝，我會的。`
            ];

            // Add exactly 3 recording segments
            const numSegments = 3;

            // Create all segments first, then fill them
            for (let i = 0; i < numSegments; i++) {
                addRecordingSegment();
            }

            // Wait a bit for DOM to be ready, then fill all segments
            setTimeout(() => {
                for (let i = 0; i < numSegments; i++) {
                    const segmentId = i + 1; // segment IDs are 1, 2, 3
                    const segmentStartMinute = i * 20; // Each segment is ~20 minutes apart
                    const segmentDuration = 15 + Math.floor(Math.random() * 5); // 15-19 minutes duration
                    const segmentEndMinute = segmentStartMinute + segmentDuration;
                    const startHourSegment = startHour + Math.floor(segmentStartMinute / 60);
                    const startMinuteSegment = segmentStartMinute % 60;
                    const endHourSegment = startHour + Math.floor(segmentEndMinute / 60);
                    const endMinuteSegment = segmentEndMinute % 60;
                    const durationSeconds = segmentDuration * 60;

                    const startEl = document.getElementById(`recording-${segmentId}-start`);
                    const endEl = document.getElementById(`recording-${segmentId}-end`);
                    const durationEl = document.getElementById(`recording-${segmentId}-duration`);
                    const transcriptEl = document.getElementById(`recording-${segmentId}-transcript`);

                    if (startEl) startEl.value = `${String(startHourSegment).padStart(2, '0')}:${String(startMinuteSegment).padStart(2, '0')}`;
                    if (endEl) endEl.value = `${String(endHourSegment).padStart(2, '0')}:${String(endMinuteSegment).padStart(2, '0')}`;
                    if (durationEl) durationEl.value = durationSeconds;
                    if (transcriptEl) transcriptEl.value = sampleRecordingTranscripts[i];
                }

                // 自動聚合所有 recordings 的 transcript_text 到完整逐字稿
                const aggregatedTranscript = sampleRecordingTranscripts.join('\n\n');
                document.getElementById('session-transcript').value = aggregatedTranscript;
            }, 150); // Wait 150ms for all segments to be created
        };

        // Quick fill random client data
        window.quickFillRandomClient = () => {
            const names = ['王小明', '李小華', '陳大同', '張美玲', '林志強', '黃淑芬', '劉建國', '吳佳穎'];
            const nicknames = ['小明', '小華', '大同', '美玲', '阿強', '芬芬', '建國', '佳佳'];
            const occupations = ['工程師', '設計師', '教師', '醫生', '護理師', '會計師', '業務', '行政'];
            const genders = ['male', 'female'];
            const educations = ['高中畢業', '國立台灣大學', '私立東吳大學', '國立政治大學', '私立輔仁大學', '國立成功大學'];
            const locations = ['台北市', '新北市', '台中市', '台南市', '高雄市', '桃園市'];
            const economicStatuses = ['可負擔日常及進修', '經濟穩定', '需家人支持', '獨立自主', '收入穩定'];
            const familyRelations = [
                '父母支持；與哥哥同住',
                '單親家庭；母親為主要支持',
                '已婚；配偶關係良好',
                '與父母同住；關係融洽',
                '獨居；與家人保持聯繫',
                '與伴侶同居；家人知情'
            ];
            const notes = [
                '初次諮詢，對職涯發展有疑問',
                '曾有轉職經驗，希望確認方向',
                '對未來感到焦慮，需要引導',
                '積極主動，目標明確',
                '需要建立信任關係'
            ];
            const otherInfos = [
                '近半年考慮轉職；對職涯方向感到迷惘',
                '曾在科技業工作三年；希望轉換跑道',
                '對目前工作感到倦怠；想探索新可能',
                '準備出國進修；需要釐清職涯規劃',
                '剛畢業一年；對未來感到不確定'
            ];

            const randomIndex = Math.floor(Math.random() * names.length);

            // Generate random birth date (20-50 years old)
            const today = new Date();
            const age = Math.floor(Math.random() * 30) + 20;
            const birthYear = today.getFullYear() - age;
            const birthMonth = String(Math.floor(Math.random() * 12) + 1).padStart(2, '0');
            const birthDay = String(Math.floor(Math.random() * 28) + 1).padStart(2, '0');
            const birthDate = `${birthYear}-${birthMonth}-${birthDay}`;

            try {
                const fields = [
                    { id: 'client-name', value: names[randomIndex] },
                    { id: 'client-nickname', value: nicknames[randomIndex] },
                    { id: 'client-birth-date', value: birthDate },
                    { id: 'client-gender', value: genders[Math.floor(Math.random() * genders.length)] },
                    { id: 'client-occupation', value: occupations[Math.floor(Math.random() * occupations.length)] },
                    { id: 'client-education', value: educations[Math.floor(Math.random() * educations.length)] },
                    { id: 'client-location', value: locations[Math.floor(Math.random() * locations.length)] },
                    { id: 'client-economic-status', value: economicStatuses[Math.floor(Math.random() * economicStatuses.length)] },
                    { id: 'client-family-relations', value: familyRelations[Math.floor(Math.random() * familyRelations.length)] },
                    { id: 'client-other-info', value: otherInfos[Math.floor(Math.random() * otherInfos.length)] },
                    { id: 'client-notes', value: notes[Math.floor(Math.random() * notes.length)] }
                ];

                fields.forEach(field => {
                    const element = document.getElementById(field.id);
                    if (element) {
                        element.value = field.value;
                    } else {
                        console.warn(`Element not found: ${field.id}`);
                    }
                });
            } catch (error) {
                console.error('Error filling form:', error);
                alert('填入資料時發生錯誤，請確認已在「建立個案」頁面');
            }
        };

        // Quick fill function for dynamic client form
        window.quickFillClient = () => {
            if (!state.clientFieldSchema) {
                alert('欄位配置未載入');
                return;
            }

            const randomNames = ['王大明', '李小華', '張美麗', '陳建國', '林雅婷', '吳志偉'];
            const randomEmails = ['test1@example.com', 'test2@example.com', 'user@test.com'];
            const randomPhones = ['0912345678', '0987654321', '0923456789'];

            // Fill Client fields
            state.clientFieldSchema.sections.forEach(section => {
                section.fields.forEach(field => {
                    const inputId = `client-${field.key}`;
                    const element = document.getElementById(inputId);
                    if (!element) return;

                    switch (field.type) {
                        case 'text':
                            if (field.key === 'name') {
                                element.value = randomNames[Math.floor(Math.random() * randomNames.length)];
                            } else if (field.key === 'location') {
                                element.value = ['台北市', '新北市', '台中市', '高雄市'][Math.floor(Math.random() * 4)];
                            } else if (field.key === 'current_job') {
                                element.value = '軟體工程師 / 3年';
                            } else if (field.key === 'current_status') {
                                element.value = '探索中';
                            } else {
                                element.value = '測試資料';
                            }
                            break;
                        case 'email':
                            element.value = randomEmails[Math.floor(Math.random() * randomEmails.length)];
                            break;
                        case 'phone':
                            element.value = randomPhones[Math.floor(Math.random() * randomPhones.length)];
                            break;
                        case 'date':
                            element.value = '1990-01-15';
                            break;
                        case 'single_select':
                            if (field.options && field.options.length > 0) {
                                const randomIndex = Math.floor(Math.random() * field.options.length);
                                element.value = field.options[randomIndex];
                            }
                            break;
                        case 'textarea':
                            element.value = '這是測試資料';
                            break;
                    }
                });
            });

            // Fill Case fields
            state.caseFieldSchema.sections.forEach(section => {
                section.fields.forEach(field => {
                    if (field.key === 'case_number') return; // Skip auto-generated
                    const inputId = `case-${field.key}`;
                    const element = document.getElementById(inputId);
                    if (!element) return;

                    switch (field.type) {
                        case 'single_select':
                            if (field.options && field.options.length > 0) {
                                // Use default value if available, otherwise random
                                element.value = field.default_value || field.options[0];
                            }
                            break;
                        case 'textarea':
                            if (field.key === 'problem_description') {
                                element.value = '希望釐清職涯方向，探索適合的發展路徑';
                            } else if (field.key === 'goals') {
                                element.value = '協助個案探索職涯方向、準備面試技巧';
                            } else if (field.key === 'summary') {
                                element.value = '個案對未來感到迷惘，希望透過諮詢找到方向';
                            } else {
                                element.value = '測試資料';
                            }
                            break;
                    }
                });
            });
        };

        // Execute analyze keywords function
        window.executeAnalyzeKeywords = () => executeStep('analyze-keywords');

        // Quick fill function for analyze keywords
        window.quickFillAnalyzeKeywords = () => {
            const sampleTranscripts = [
                '我最近在工作上遇到很多壓力，常常感到焦慮和無助。主管對我的要求越來越高，我不知道該如何應對。',
                '最近家人關係變得很緊張，我覺得很難在家裡找到平靜的空間。每次回家都感到壓抑。',
                '我對未來感到迷茫，不知道自己的人生方向在哪裡。看到朋友們都很有成就，我感到很自卑。',
                '失眠問題困擾我很久了，晚上總是翻來覆去睡不著，白天又沒精神工作。'
            ];

            document.getElementById('analyze-transcript').value =
                sampleTranscripts[Math.floor(Math.random() * sampleTranscripts.length)];
        };

        // Quick fill function for append recording
        window.quickFillAppendRecording = () => {
            const now = new Date();
            const startTime = new Date(now.getTime() - 30 * 60000); // 30 minutes ago
            const endTime = new Date(now.getTime() - 10 * 60000); // 10 minutes ago

            const sampleTranscripts = [
                `Co: 今天想聊些什麼呢？
Cl: 最近工作壓力很大，覺得快要撐不下去了。
Co: 可以多說一些嗎？是什麼樣的壓力？
Cl: 主管總是對我的工作不滿意，不管我怎麼做都覺得不夠好。`,
                `Co: 上次提到的職涯方向，有新的想法嗎？
Cl: 我一直在思考，但還是很迷茫。
Co: 迷茫的感覺是什麼？
Cl: 不知道自己適合做什麼，也不確定現在的工作是不是對的選擇。`,
                `Co: 今天看起來心情不錯？
Cl: 對啊，這週工作順利很多，主管也稱讚了我。
Co: 很高興聽到這個消息！是什麼改變了？
Cl: 我開始用你上次建議的方法，先確認主管的需求再開始做。`
            ];

            const randomTranscript = sampleTranscripts[Math.floor(Math.random() * sampleTranscripts.length)];
            const durationSeconds = 1200; // 20 minutes

            // Format times as "YYYY-MM-DD HH:MM"
            const formatTime = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                return `${year}-${month}-${day} ${hours}:${minutes}`;
            };

            document.getElementById('append-start-time').value = formatTime(startTime);
            document.getElementById('append-end-time').value = formatTime(endTime);
            document.getElementById('append-duration').value = durationSeconds;
            document.getElementById('append-transcript').value = randomTranscript;
            document.getElementById('append-transcript-sanitized').value = ''; // Leave empty for auto-fill
        };

        // Quick fill function for case creation
        window.quickFillCase = () => {
            const summaryEl = document.getElementById('create-case-summary');
            const goalsEl = document.getElementById('create-case-goals');
            const problemEl = document.getElementById('create-case-problem');
            const statusEl = document.getElementById('create-case-status');

            const sampleData = [
                {
                    summary: '個案對未來感到迷惘，希望透過諮詢找到方向',
                    goals: '協助個案探索職涯方向、準備面試技巧',
                    problem: '希望釐清職涯方向，探索適合的發展路徑'
                },
                {
                    summary: '職場適應困難，與主管關係緊張',
                    goals: '改善職場人際關係、提升溝通技巧',
                    problem: '在工作中感到壓力大，與主管溝通不良'
                },
                {
                    summary: '轉職準備階段，需要履歷與面試指導',
                    goals: '優化履歷、提升面試表現、建立求職信心',
                    problem: '想轉換職涯跑道，但不知如何準備'
                }
            ];

            const randomData = sampleData[Math.floor(Math.random() * sampleData.length)];

            if (summaryEl) summaryEl.value = randomData.summary;
            if (goalsEl) goalsEl.value = randomData.goals;
            if (problemEl) problemEl.value = randomData.problem;
            if (statusEl) statusEl.value = 'active';
        };

        // Helper: Load logs for deletion dropdown
        window.loadLogsForDeletion = async function() {
            const sessionId = document.getElementById('delete-log-session-id').value;
            if (!sessionId) {
                return;
            }

            try {
                const response = await fetch(`${BASE_URL}/api/v1/sessions/${sessionId}/analysis-logs`, {
                    headers: { 'Authorization': `Bearer ${state.token}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    state.currentAnalysisLogs = data.logs;

                    // Update the dropdown
                    const logSelect = document.getElementById('delete-log-index');
                    if (data.logs.length === 0) {
                        logSelect.innerHTML = '<option value="">此會談無分析記錄</option>';
                    } else {
                        const options = data.logs.map(log =>
                            `<option value="${log.log_index}">#${log.log_index} - ${log.transcript_segment.substring(0, 50)}...</option>`
                        ).join('');
                        logSelect.innerHTML = '<option value="">請選擇要刪除的記錄</option>' + options;
                    }
                }
            } catch (error) {
                console.error('Failed to load analysis logs:', error);
            }
        };

        // Step execution functions
        window.executeRegister = () => executeStep('register');
        window.executeLogin = () => executeStep('login');
        window.executeMe = () => executeStep('me');
        window.executeGetClientFieldSchema = () => executeStep('get-client-field-schema');
        window.executeGetCaseFieldSchema = () => executeStep('get-case-field-schema');
        window.executeListClients = () => executeStep('list-clients');
        window.executeCreateClient = () => executeStep('create-client');
        window.executeViewClient = () => executeStep('view-client');
        window.executeClientTimeline = () => executeStep('client-timeline');
        window.executeUpdateClient = () => executeStep('update-client');
        window.executeDeleteClient = () => executeStep('delete-client');
        window.executeListCases = () => executeStep('list-cases');
        window.executeCreateCase = () => executeStep('create-case');
        window.executeViewCase = () => executeStep('view-case');
        window.executeUpdateCase = () => executeStep('update-case');
        window.executeDeleteCase = () => executeStep('delete-case');
        window.executeCreateSession = () => executeStep('create-session');
        window.executeListSessions = () => executeStep('list-sessions');
        window.executeViewSession = () => executeStep('view-session');
        window.executeUpdateSession = () => executeStep('update-session');
        window.executeDeleteSession = () => executeStep('delete-session');
        window.executeGetReflection = () => executeStep('get-reflection');
        window.executeUpdateReflection = () => executeStep('update-reflection');
        window.executeAppendRecording = () => executeStep('append-recording');
        window.executeUpdateCounselor = () => executeStep('update-counselor');
        window.executeGenerateReport = () => executeStep('generate-report');
        window.executeListReports = () => executeStep('list-reports');
        window.executeViewReport = () => executeStep('view-report');
        window.executeUpdateReport = () => executeStep('update-report');
        window.executeGetAnalysisLogs = () => executeStep('get-analysis-logs');
        window.executeDeleteAnalysisLog = () => executeStep('delete-analysis-log');

        // Dynamic form field renderer
        window.renderFormField = (field, prefix) => {
            const fieldId = prefix + '-' + field.key;
            const requiredMark = field.required ? ' *' : '';
            let fieldHTML = '<div class="form-group">';
            fieldHTML += '<label>' + field.label + requiredMark + '</label>';

            if (field.type === 'text' || field.type === 'email' || field.type === 'phone') {
                const inputType = field.type === 'email' ? 'email' : field.type === 'phone' ? 'tel' : 'text';
                fieldHTML += '<input type="' + inputType + '" id="' + fieldId + '" ';
                if (field.placeholder) fieldHTML += 'placeholder="' + field.placeholder + '" ';
                if (field.required) fieldHTML += 'required ';
                fieldHTML += '/>';
            } else if (field.type === 'date') {
                fieldHTML += '<input type="date" id="' + fieldId + '" ';
                if (field.required) fieldHTML += 'required ';
                fieldHTML += '/>';
            } else if (field.type === 'textarea') {
                fieldHTML += '<textarea id="' + fieldId + '" rows="3" ';
                if (field.placeholder) fieldHTML += 'placeholder="' + field.placeholder + '" ';
                if (field.required) fieldHTML += 'required ';
                fieldHTML += '></textarea>';
            } else if (field.type === 'single_select') {
                fieldHTML += '<select id="' + fieldId + '" ';
                if (field.required) fieldHTML += 'required ';
                fieldHTML += '>';
                if (!field.required) fieldHTML += '<option value="">請選擇</option>';
                if (field.options) {
                    field.options.forEach(opt => {
                        fieldHTML += '<option value="' + opt + '">' + opt + '</option>';
                    });
                }
                fieldHTML += '</select>';
            }

            if (field.help_text) {
                fieldHTML += '<small style="color: #86868b; font-size: 12px; display: block; margin-top: 4px;">' + field.help_text + '</small>';
            }
            fieldHTML += '</div>';
            return fieldHTML;
        };

        // Client-Case CRUD functions
        window.executeListClientCases = () => executeStep('list-client-cases');
        window.executeCreateClientCase = () => executeStep('create-client-case');
        window.executeGetClientCaseDetail = () => executeStep('get-client-case-detail');
        window.executeUpdateClientCase = () => executeStep('update-client-case');
        window.executeDeleteClientCase = () => executeStep('delete-client-case');

        // Generate random test data for create-client-case form (dynamic)
        window.generateRandomClientData = () => {
            const timestamp = Date.now();
            const randomData = {
                names: { surnames: ['王', '李', '張', '劉', '陳', '楊', '黃', '吳', '趙', '周'], givenNames: ['小明', '小華', '小芳', '建國', '志偉', '淑芬', '雅婷', '冠宇', '怡君', '佳玲'] },
                phones: () => `09${Math.floor(Math.random() * 100000000).toString().padStart(8, '0')}`,
                dates: () => {
                    const year = 1970 + Math.floor(Math.random() * 35);
                    const month = String(1 + Math.floor(Math.random() * 12)).padStart(2, '0');
                    const day = String(1 + Math.floor(Math.random() * 28)).padStart(2, '0');
                    return `${year}-${month}-${day}`;
                },
                locations: ['台北市', '新北市', '台中市', '台南市', '高雄市', '桃園市'],
                currentStatus: ['求職中', '在學中', '考慮轉職', '探索新方向', '穩定就業', '準備面試'],
                currentJobs: ['軟體工程師 / 3年', 'UI設計師 / 2年', '產品經理 / 5年', '行銷專員 / 1年', '資料分析師 / 4年', '專案經理 / 6年'],
                consultationHistory: ['否', '是，曾接受過生涯諮詢', '是，參加過職涯工作坊'],
                mentalHealthHistory: ['否', '否，無相關紀錄'],
                problems: ['不確定職涯方向', '想轉換跑道但不知如何開始', '面試屢次失敗需要協助', '工作不快樂想尋求改變'],
                goals: ['找到適合的職涯方向', '成功轉職到理想產業', '提升面試技巧', '釐清職涯規劃'],
                summaries: ['職涯諮詢', '轉職諮詢', '面試輔導', '職涯探索']
            };

            const fullName = randomData.names.surnames[Math.floor(Math.random() * 10)] +
                           randomData.names.givenNames[Math.floor(Math.random() * 10)];

            // 动态填充 Client 字段
            if (state.clientSchema?.sections) {
                state.clientSchema.sections.forEach(section => {
                    section.fields.forEach(field => {
                        const fieldId = 'cc-client-' + field.key;
                        const element = document.getElementById(fieldId);
                        if (!element) return;

                        // 特定欄位的隨機資料
                        if (field.key === 'name') {
                            element.value = fullName;
                        } else if (field.key === 'email') {
                            element.value = `test${timestamp}@example.com`;
                        } else if (field.key === 'phone') {
                            element.value = randomData.phones();
                        } else if (field.key === 'birth_date') {
                            element.value = randomData.dates();
                        } else if (field.key === 'location') {
                            element.value = randomData.locations[Math.floor(Math.random() * randomData.locations.length)];
                        } else if (field.key === 'current_status') {
                            element.value = randomData.currentStatus[Math.floor(Math.random() * randomData.currentStatus.length)];
                        } else if (field.key === 'current_job') {
                            element.value = randomData.currentJobs[Math.floor(Math.random() * randomData.currentJobs.length)];
                        } else if (field.key === 'has_consultation_history') {
                            element.value = randomData.consultationHistory[Math.floor(Math.random() * randomData.consultationHistory.length)];
                        } else if (field.key === 'has_mental_health_history') {
                            element.value = randomData.mentalHealthHistory[Math.floor(Math.random() * randomData.mentalHealthHistory.length)];
                        } else if (field.key === 'notes') {
                            element.value = ''; // 備註留空
                        } else if (field.type === 'single_select' && field.options && field.options.length > 0) {
                            // 其他 select 欄位隨機選擇
                            element.value = field.options[Math.floor(Math.random() * field.options.length)];
                        } else if (field.type === 'text' && !element.value) {
                            // 其他 text 欄位如果沒有特別處理，使用 placeholder 或留空
                            element.value = '';
                        } else if (field.type === 'textarea' && !element.value) {
                            // 其他 textarea 欄位留空
                            element.value = '';
                        }
                    });
                });
            }

            // 动态填充 Case 字段
            if (state.caseSchema?.sections) {
                state.caseSchema.sections.forEach(section => {
                    section.fields.forEach(field => {
                        if (field.key === 'case_number' || field.key === 'status') return;
                        const fieldId = 'cc-case-' + field.key;
                        const element = document.getElementById(fieldId);
                        if (!element) return;

                        if (field.key === 'summary') {
                            element.value = randomData.summaries[Math.floor(Math.random() * randomData.summaries.length)];
                        } else if (field.key === 'problem_description') {
                            element.value = randomData.problems[Math.floor(Math.random() * randomData.problems.length)];
                        } else if (field.key === 'goals') {
                            element.value = randomData.goals[Math.floor(Math.random() * randomData.goals.length)];
                        } else if (field.type === 'single_select' && field.options && field.options.length > 0) {
                            element.value = field.options[Math.floor(Math.random() * field.options.length)];
                        } else {
                            element.value = '';
                        }
                    });
                });
            }

            console.log('✅ 隨機測試資料已生成 (動態):', fullName, `test${timestamp}@example.com`);
        };
