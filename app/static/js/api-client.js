/**
 * API Client Module
 * 統一管理所有 API 調用，處理認證和錯誤
 *
 * @module api-client
 * @version 1.0.0
 * @created 2025-01-01
 */

export class APIClient {
    /**
     * Initialize API Client
     * Reads auth token and tenant ID from localStorage
     */
    constructor() {
        this.baseURL = '';  // Same origin
        this.authToken = localStorage.getItem('authToken');
        this.tenantId = localStorage.getItem('tenantId');
    }

    /**
     * Generic fetch wrapper with authentication
     *
     * @param {string} endpoint - API endpoint (e.g., '/api/v1/sessions')
     * @param {Object} options - Fetch options (method, body, headers)
     * @returns {Promise<Object>} - JSON response
     * @throws {Error} - If HTTP status is not OK
     */
    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Read auth token fresh from localStorage on every request
        // (Fixes issue where token is saved after APIClient constructor runs)
        const authToken = localStorage.getItem('authToken');
        const tenantId = localStorage.getItem('tenantId');

        // Add authentication header if token exists
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }

        // Note: X-Tenant-ID header removed - tenant_id is extracted from JWT token on backend

        const response = await fetch(this.baseURL + endpoint, {
            ...options,
            headers
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API Error (${response.status}): ${error}`);
        }

        return await response.json();
    }

    /**
     * Create client and case atomically
     *
     * @param {Object} clientData - Client information
     * @param {string} clientData.name - Child's name
     * @param {string} clientData.email - Email address
     * @param {string} clientData.gender - Gender (男/女/不透露/其他)
     * @param {string} clientData.birth_date - Birth date (YYYY-MM-DD)
     * @param {string} clientData.phone - Phone number
     * @param {string} clientData.identity_option - Identity (學生/家長/其他)
     * @param {string} clientData.current_status - Current status
     * @param {string} [clientData.case_summary] - Case summary
     * @param {string} [clientData.case_goals] - Case goals
     * @returns {Promise<{client_id: string, case_id: string}>}
     */
    async createClientAndCase(clientData) {
        return await this.request('/api/v1/ui/client-case', {
            method: 'POST',
            body: JSON.stringify(clientData)
        });
    }

    /**
     * Create session
     *
     * @param {string} caseId - Case UUID
     * @param {string} [sessionName] - Session name (auto-generated if not provided)
     * @returns {Promise<{id: string}>}
     */
    async createSession(caseId, sessionName = null) {
        const now = new Date();
        const defaultName = `Web 即時諮詢 ${now.toLocaleString('zh-TW')}`;

        return await this.request('/api/v1/sessions', {
            method: 'POST',
            body: JSON.stringify({
                case_id: caseId,
                session_date: now.toISOString().split('T')[0],  // YYYY-MM-DD
                name: sessionName || defaultName
            })
        });
    }

    /**
     * Append recording to session
     *
     * @param {string} sessionId - Session UUID
     * @param {string} transcript - Transcript text
     * @param {number} [durationSeconds=60] - Recording duration in seconds
     * @returns {Promise<Object>}
     */
    async appendRecording(sessionId, transcript, durationSeconds = 60) {
        const now = new Date();
        const endTime = new Date(now.getTime() + durationSeconds * 1000);

        return await this.request(`/api/v1/sessions/${sessionId}/recordings/append`, {
            method: 'POST',
            body: JSON.stringify({
                start_time: now.toISOString().replace('T', ' ').substring(0, 16),  // 'YYYY-MM-DD HH:MM'
                end_time: endTime.toISOString().replace('T', ' ').substring(0, 16),
                duration_seconds: durationSeconds,
                transcript_text: transcript
            })
        });
    }

    /**
     * Analyze partial transcript (legacy - uses analyze-partial endpoint)
     *
     * @param {string} sessionId - Session UUID
     * @param {string} segment - Transcript segment to analyze
     * @param {string} [mode='practice'] - Analysis mode ('practice' or 'emergency')
     * @returns {Promise<Object>} - Analysis result
     */
    async analyzePartial(sessionId, segment, mode = 'practice') {
        return await this.request(`/api/v1/sessions/${sessionId}/analyze-partial`, {
            method: 'POST',
            body: JSON.stringify({
                transcript_segment: segment,
                mode: mode
            })
        });
    }

    /**
     * Quick feedback (session-based)
     * Reads transcript from session automatically
     *
     * @param {string} sessionId - Session UUID
     * @returns {Promise<Object>} - { message, type, timestamp, latency_ms }
     */
    async quickFeedback(sessionId) {
        return await this.request(`/api/v1/sessions/${sessionId}/quick-feedback`, {
            method: 'POST'
        });
    }

    /**
     * Deep analyze (session-based)
     * Reads transcript from session automatically
     *
     * @param {string} sessionId - Session UUID
     * @param {string} [mode='practice'] - Analysis mode ('practice' or 'emergency')
     * @param {boolean} [useRag=false] - Whether to use RAG
     * @returns {Promise<Object>} - { safety_level, summary, suggestions, ... }
     */
    async deepAnalyze(sessionId, mode = 'practice', useRag = false) {
        return await this.request(`/api/v1/sessions/${sessionId}/deep-analyze?mode=${mode}&use_rag=${useRag}`, {
            method: 'POST'
        });
    }

    /**
     * Generate report (session-based)
     * Reads transcript from session automatically
     *
     * @param {string} sessionId - Session UUID
     * @returns {Promise<Object>} - { summary, highlights, improvements, ... }
     */
    async generateReport(sessionId) {
        return await this.request(`/api/v1/sessions/${sessionId}/report`, {
            method: 'POST'
        });
    }

    /**
     * Refresh authentication credentials from localStorage
     * Call this after user login
     */
    refreshAuth() {
        this.authToken = localStorage.getItem('authToken');
        this.tenantId = localStorage.getItem('tenantId');
    }

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated() {
        return !!this.authToken && !!this.tenantId;
    }
}
