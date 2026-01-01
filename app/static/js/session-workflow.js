/**
 * Session Workflow Module
 * 管理 Web 即時諮詢的 Session 生命週期
 *
 * @module session-workflow
 * @version 1.0.0
 * @created 2025-01-01
 */

import { APIClient } from './api-client.js';

export class SessionWorkflow {
    /**
     * Initialize Session Workflow
     * Creates APIClient instance and initializes state
     */
    constructor() {
        this.apiClient = new APIClient();
        this.currentSessionId = null;
        this.currentCaseId = null;
        this.currentClientId = null;
    }

    /**
     * Initialize session (create client+case+session)
     *
     * This method performs the full initialization sequence:
     * 1. Create client + case atomically
     * 2. Create session for the case
     *
     * @param {Object} clientData - Client information
     * @param {string} clientData.name - Child's name
     * @param {string} clientData.email - Email address
     * @param {string} clientData.gender - Gender
     * @param {string} clientData.birth_date - Birth date (YYYY-MM-DD)
     * @param {string} clientData.phone - Phone number
     * @param {string} clientData.identity_option - Identity option
     * @param {string} clientData.current_status - Current status
     * @param {string} [clientData.case_summary] - Case summary
     * @param {string} [clientData.case_goals] - Case goals
     * @param {string} [clientData.problem_description] - Problem description
     * @returns {Promise<string>} session_id
     * @throws {Error} If initialization fails
     */
    async initializeSession(clientData) {
        try {
            // Step 1: Create client + case
            console.log('[Session] Creating client + case...');
            const { client_id, case_id } = await this.apiClient.createClientAndCase(clientData);
            console.log('[Session] Created:', { client_id, case_id });

            this.currentClientId = client_id;
            this.currentCaseId = case_id;

            // Step 2: Create session
            console.log('[Session] Creating session for case:', case_id);
            const sessionData = await this.apiClient.createSession(case_id);
            this.currentSessionId = sessionData.id;
            console.log('[Session] Session created:', this.currentSessionId);

            return this.currentSessionId;

        } catch (error) {
            console.error('[Session] Initialization failed:', error);
            throw new Error(`Session 初始化失敗: ${error.message}`);
        }
    }

    /**
     * Perform analysis (append + analyze)
     *
     * This method performs:
     * 1. Append recording to session
     * 2. Analyze the transcript segment
     * 3. Transform response to Realtime API format
     *
     * @param {string} transcript - Transcript text
     * @param {string} [mode='practice'] - Analysis mode ('practice' or 'emergency')
     * @returns {Promise<Object>} analysis result in Realtime API format
     * @throws {Error} If session not initialized or analysis fails
     */
    async performAnalysis(transcript, mode = 'practice') {
        if (!this.currentSessionId) {
            throw new Error('Session 未初始化，請先創建 session');
        }

        try {
            // Step 1: Append recording
            console.log('[Analysis] Appending recording to session:', this.currentSessionId);
            await this.apiClient.appendRecording(this.currentSessionId, transcript);

            // Step 2: Analyze
            console.log('[Analysis] Analyzing transcript...');
            const analysis = await this.apiClient.analyzePartial(
                this.currentSessionId,
                transcript,
                mode
            );

            console.log('[Analysis] Analysis complete:', analysis);
            return this.transformToRealtimeFormat(analysis);

        } catch (error) {
            console.error('[Analysis] Failed:', error);
            throw new Error(`分析失敗: ${error.message}`);
        }
    }

    /**
     * Transform Session API response to Realtime API format
     * (For backward compatibility with existing UI)
     *
     * @param {Object} sessionResponse - Response from Session API
     * @returns {Object} Realtime API format response
     */
    transformToRealtimeFormat(sessionResponse) {
        // Map detailed_scripts to suggestions (for island_parents tenant)
        // Fallback to quick_suggestions for career tenant
        let suggestions = [];

        if (sessionResponse.detailed_scripts && Array.isArray(sessionResponse.detailed_scripts)) {
            // Transform detailed scripts to simple suggestion format
            suggestions = sessionResponse.detailed_scripts.map(script =>
                `💡 ${script.situation}\n${script.parent_script}`
            );
        } else if (sessionResponse.quick_suggestions) {
            suggestions = Array.isArray(sessionResponse.quick_suggestions)
                ? sessionResponse.quick_suggestions
                : [];
        }

        return {
            // Core fields (Realtime API format)
            safety_level: sessionResponse.safety_level || 'green',
            summary: sessionResponse.display_text || '分析完成',
            alerts: sessionResponse.action_suggestion
                ? [sessionResponse.action_suggestion]
                : [],
            suggestions: suggestions,
            time_range: '',
            timestamp: new Date().toISOString(),
            rag_sources: sessionResponse.rag_documents || [],

            // Provider metadata
            provider_metadata: {
                provider: 'gemini',
                latency_ms: 0,
                model: 'gemini-2.0-flash-exp'
            },

            // Session-specific metadata (for advanced usage)
            _session_metadata: {
                session_id: this.currentSessionId,
                case_id: this.currentCaseId,
                client_id: this.currentClientId,
                severity: sessionResponse.severity,
                suggested_interval_seconds: sessionResponse.suggested_interval_seconds,
                keywords: sessionResponse.keywords || [],
                categories: sessionResponse.categories || []
            }
        };
    }

    /**
     * End current session and reset state
     */
    endSession() {
        console.log('[Session] Ending session:', this.currentSessionId);
        this.currentSessionId = null;
        this.currentCaseId = null;
        this.currentClientId = null;
    }

    /**
     * Get current session ID
     * @returns {string|null} session_id or null if not initialized
     */
    getCurrentSessionId() {
        return this.currentSessionId;
    }

    /**
     * Get current case ID
     * @returns {string|null} case_id or null if not initialized
     */
    getCurrentCaseId() {
        return this.currentCaseId;
    }

    /**
     * Get current client ID
     * @returns {string|null} client_id or null if not initialized
     */
    getCurrentClientId() {
        return this.currentClientId;
    }

    /**
     * Check if session is initialized
     * @returns {boolean}
     */
    isSessionActive() {
        return !!this.currentSessionId;
    }

    /**
     * Get session metadata
     * @returns {Object} Session metadata
     */
    getSessionMetadata() {
        return {
            session_id: this.currentSessionId,
            case_id: this.currentCaseId,
            client_id: this.currentClientId,
            is_active: this.isSessionActive()
        };
    }
}
