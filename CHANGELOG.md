# Changelog

All notable changes to the Career iOS Backend API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Counseling Mode Support for analyze-partial API** (2025-12-31)
  - ✅ New `mode` parameter for island_parents tenant
    - `emergency`: Fast, simplified analysis (1-2 critical suggestions)
    - `practice`: Detailed teaching mode (3-4 suggestions with techniques)
  - ✅ Backward compatible: Optional parameter, defaults to `practice`
  - ✅ Career tenant: Ignores mode parameter (not applicable)
  - ✅ realtime.py bug fix: Separate `analysis_type` and `mode` fields in GBQ
  - ✅ 4 integration tests: emergency mode, practice mode, default, career ignore
  - 📝 Updated: `app/schemas/analysis.py`, `app/api/sessions_keywords.py`, `app/services/keyword_analysis_service.py`, `app/api/realtime.py`
  - 📝 Tests: `tests/integration/test_analyze_partial_api.py` (lines 472-730)
- **Performance Analysis and Testing Infrastructure** (2025-12-31)
  - ✅ Performance analysis documentation:
    - `docs/LIGHT_VS_HEAVY_ANALYSIS.md` - Speed comparison report (rule-based vs Gemini Light vs Gemini Heavy)
    - `docs/OPTIMIZATION_OPPORTUNITIES.md` - Optimization opportunities analysis with priority rankings
  - ✅ Performance testing scripts (7 scripts):
    - `scripts/test_vertex_ai_caching.py` - Vertex AI Context Caching performance test
    - `scripts/test_gemini_context_caching.py` - Gemini Context Caching test
    - `scripts/test_light_vs_heavy_analysis.py` - Light vs Heavy analysis comparison
    - `scripts/test_timing_average.py` - Average timing test (5 iterations)
    - `scripts/test_detailed_timing.py` - Detailed timing breakdown
    - `scripts/test_real_api_e2e.py` - Real API end-to-end test
    - `scripts/test_real_gemini_speed.py` - Gemini API speed test
  - ✅ Utility scripts:
    - `scripts/check_test_account.py` - Test account verification
    - `scripts/verify_password.py` - Password verification utility
  - 📊 Key findings:
    - Gemini 3 Flash: 5.61s average (45% faster than Gemini 2.5 Flash)
    - Context Caching: 28.4% improvement (not 50% as claimed, API deprecated 2026-06)
    - Main bottleneck: Gemini API (4.64s, 83%) + RAG retrieval (0.97s, 17%)
    - Recommendation: Focus on Streaming for perceived latency improvement (5.61s → 1-2s)
  - 📝 Related to TODO.md P0-A (RAG Bug Fix) and P1-2 (Performance Optimization)

### Changed
- **Gemini 3 Flash Upgrade** (2025-12-28)
  - ✅ Upgraded from Gemini 2.5 Flash to Gemini 3 Flash (`gemini-3-flash-preview`)
  - ✅ Pro-level intelligence at Flash speed and pricing
  - ✅ Updated pricing calculations:
    - Input: $0.50/1M tokens (was $0.075/1M)
    - Output: $3.00/1M tokens (was $0.30/1M)
    - Cached input: $0.125/1M tokens (was $0.01875/1M)
  - ✅ Updated all service files, API endpoints, and tests
  - ✅ All integration tests passing (22 tests: billing, analysis, GBQ integrity)
  - ✅ No breaking changes - backward compatible API
  - 📝 Updated: `app/core/config.py`, `app/services/gemini_service.py`, `app/services/keyword_analysis_service.py`, `app/api/realtime.py`, pricing calculations
  - 📝 Source: [Gemini 3 Flash Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash)

### Added
- **Island Parents Relationship Field** (2025-12-29)
  - ✅ New `relationship` field for island_parents Client form
    - Options: 爸爸 (father), 媽媽 (mother), 爺爺 (grandfather), 奶奶 (grandmother), 外公 (maternal grandfather), 外婆 (maternal grandmother), 其他 (other)
    - Required field for island_parents tenant
    - Field order optimized for better UX (order=3)
  - ✅ Updated Client field labels:
    - "孩子姓名" → "孩子暱稱" (Child Name → Child Nickname)
  - ✅ Comprehensive iOS API integration guide
    - 9-step complete workflow documentation
    - Safety level analysis explanation (🟢🟡🔴)
    - Dynamic analysis intervals (5-30s based on safety level)
    - Swift code examples for iOS implementation
    - FAQ section and related resources
  - ✅ Complete workflow integration tests (681 lines)
  - 📝 Updated: `app/config/field_configs.py`, `IOS_API_GUIDE.md`
  - 📝 New test: `tests/integration/test_island_parents_complete_workflow.py`
  - 📝 Test report: `docs/testing/ISLAND_PARENTS_WORKFLOW_TEST_REPORT.md`

- **Documentation Organization and Infrastructure Cost Analysis** (2025-12-29)
  - ✅ Reorganized documentation structure:
    - Moved test reports to `docs/testing/`
    - Centralized technical docs in `docs/`
    - Improved file organization by functional areas
  - ✅ PRD Updates:
    - Added island_parents Safety Level system details
    - Marked Incremental Billing (Phase 2) as complete
    - Updated field configurations and descriptions
  - ✅ Infrastructure cost analysis added to PRD:
    - Cloud Run cost estimates (low/medium/high traffic)
    - Supabase pricing tiers and recommendations
    - Gemini 3 Flash AI model cost calculations
    - Total monthly cost projections: $10-25 (prototype), $65-125 (production)
    - Cost optimization strategies (caching, rate limiting, monitoring)
  - 📝 Updated: `PRD.md` with cost analysis and feature status
  - 📝 Source: [Gemini 3 Flash Pricing](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash)

- **Password Reset System** (2025-12-27)
  - ✅ Web UI pages: `/forgot-password` (request) and `/reset-password` (confirmation)
  - ✅ API endpoints for iOS integration:
    - `POST /api/v1/password-reset/request` - Request password reset
    - `POST /api/v1/password-reset/verify` - Verify reset token
    - `POST /api/v1/password-reset/confirm` - Confirm new password
  - ✅ Auto-send welcome email when creating new counselors via Admin API
  - ✅ Multi-tenant support (career/island/island_parents) with tenant-specific email templates
  - ✅ Token security: 32+ character encrypted random string, 6-hour expiration, single-use
  - ✅ Rate limiting: Maximum one request per 5 minutes
  - ✅ DEBUG mode: Cross-tenant admin access for development
  - ✅ Database migration: `20251227_1049_f9b8a56ce021_add_password_reset_tokens_table.py`
  - ✅ 23 integration tests with 100% pass rate
  - ✅ Email service enhancements:
    - SMTP delivery via Gmail
    - Tenant-specific templates (career/island/island_parents)
    - Error handling and retry logic

### Fixed
- **SMTP Configuration for Staging Deployment** (2025-12-27)
  - 🔧 Added SMTP environment variables to CI/CD pipeline
  - 🔧 Required GitHub Secrets: SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, APP_URL
  - 🔧 Fixed silent email sending failure in staging environment
  - 🔧 Created SMTP_SETUP.md documentation for configuration steps
  - 📝 See: `.github/workflows/ci.yml`, `SMTP_SETUP.md`

### Added
- **Parents RAG Refinement - Complete Observability** (2025-12-26)
  - ✅ Expanded GBQ schema coverage from 23% to 67%+ (29/43 fields)
  - ✅ Complete metadata tracking for parents_report API:
    - Token usage: prompt_tokens, completion_tokens, total_tokens, cached_tokens
    - Cost calculation: Gemini 2.5 Flash pricing ($0.000075/1K input, $0.0003/1K output)
    - Timing breakdown: RAG search time, LLM call time, total duration
    - Full prompts: system_prompt, user_prompt, prompt_template
    - LLM response: raw response, structured analysis result
    - RAG tracking: query, documents, sources, timing
    - Model info: provider, model_name, model_version
  - ✅ Modified `gemini_service.chat_completion()` to optionally return usage_metadata
  - ✅ JSON serialization for BigQuery JSON fields (analysis_result, speakers, rag_documents)
  - ✅ Session ID capture from request (Web localStorage-based)
  - ✅ Fixed field name mismatches (response_time_ms → api_response_time_ms, transcript_segment → transcript)
  - ✅ Model corrected to gemini-2.5-flash (from 2.0-flash-exp)
- **Parents RAG Refinement - Phase 1.4 & 2.1** (2025-12-25)
  - ✅ Phase 1.4 - Frontend Adjustments:
    - Removed two-line format detection, unified single-line suggestion display
    - Updated frontend descriptions (Mobile & Desktop) to reflect 200 expert suggestions
    - Emergency mode: 1-2 expert suggestions (from 200 pool)
    - Practice mode: 3-4 expert suggestions (from 200 pool)
  - ✅ Phase 2.1 - Backend Optimizations:
    - Expanded analysis scope from 1 min to 3-5 min (SAFETY_WINDOW_SPEAKER_TURNS: 10 → 40)
    - Enhanced RAG retrieval: top_k 3→7, similarity_threshold 0.5→0.35
    - Removed 200-character truncation from RAG content
  - ✅ Dynamic Analysis Intervals (Commit: 2b10eb0):
    - Implemented adaptive monitoring based on safety_level
    - Green (safe): 60 seconds
    - Yellow (warning): 30 seconds
    - Red (critical): 15 seconds
    - Visual notifications and console logging
    - `updateAnalysisInterval()` function dynamically adjusts timer
  - ✅ Card Color Consistency:
    - Fixed card colors to use `safety_level` instead of `risk_level`
    - Updated labels: "危險：立即修正", "警示：需要調整", "安全：溝通良好"
  - ✅ Testing Enhancements:
    - Added preset transcript shortcuts (🟢🟡🔴)
    - Added "⚡ 立即分析" button for instant testing
    - Phase 1.5: 8/9 integration tests pass, 106 total tests pass
- **Parents Report API & Unified Session Management** (2025-12-26)
  - ✅ New endpoint: `POST /api/v1/realtime/parents-report`
    - Generates comprehensive parenting communication reports
    - Analyzes parent-child conversation transcripts
    - Provides structured feedback in 4 sections:
      1. Summary/theme (neutral stance)
      2. Communication highlights (what went well)
      3. Areas for improvement with specific suggestions
      4. RAG references from parenting knowledge base
    - Integrates with existing RAG infrastructure (similarity_threshold=0.5)
    - Uses Gemini 2.5 Flash for analysis (temperature=0.7)
  - ✅ Unified Session ID Management
    - Generated once at session start: `session-{timestamp}-{random}`
    - Persisted in localStorage for cross-request tracking
    - Used consistently across all realtime APIs:
      - `/api/v1/realtime/analyze` (now includes session_id + use_cache)
      - `/api/v1/realtime/parents-report`
      - Future GBQ data persistence
    - Enables Gemini context caching for cost optimization
  - ✅ Frontend Integration
    - Report screen UI with highlight cards and improvement suggestions
    - Click "查看報告" triggers API call and displays structured feedback
    - Mobile-responsive design with completion screen
    - Session ID tracking across recording lifecycle
  - ✅ New Schemas: `ParentsReportRequest`, `ParentsReportResponse`, `ImprovementSuggestion`
  - ✅ Testing: Backend API tested via curl (successful response with RAG integration)
- **Universal Credit/Payment System - Admin Backend (Phase 1)** (2025-12-20)
  - ✅ Database schema extensions:
    - Extended `counselors` table with credit fields (phone, total_credits, credits_used, subscription_expires_at)
    - New `credit_rates` table for configurable billing rules with versioning support
    - New `credit_logs` table for transaction audit trail with raw data preservation
  - ✅ Service layer implementation:
    - `CreditBillingService` with flexible credit calculation (per_second, per_minute, tiered pricing)
    - `get_active_rate()`, `calculate_credits()`, `add_credits()`, `get_counselor_balance()` methods
    - Raw seconds storage for future recalculation flexibility
  - ✅ Admin API endpoints (`/api/v1/admin/credits/*`):
    - `GET /members` - List all counselors with credit info (supports tenant filtering)
    - `POST /members/{id}/add` - Add/remove credits (purchase, admin_adjustment, refund)
    - `GET /logs` - View transaction history (filterable by counselor, type, with pagination)
    - `POST /rates` - Create/update billing rates (automatic versioning)
    - `GET /rates` - List all billing rates (filterable by rule name, active status)
  - ✅ Multi-tenant support:
    - Universal credit mechanism for ALL tenants (career, island, island_parents)
    - island_parents dynamic form configurations added (child-focused client form, case form)
  - ✅ Security & access control:
    - Admin-only endpoints with role-based access control
    - Complete audit trail for all transactions
  - ✅ Testing:
    - 21 integration tests covering all admin endpoints, RBAC, cross-tenant functionality
    - TDD approach (tests written first, implementation follows)
  - ✅ Database migration: `20251220_1829_5ae92c306158` applied successfully
  - ⚠️ Phase 2 pending: Automatic credit deduction on session end
- **User Registration API** (2025-12-15)
  - ✅ New endpoint: `POST /api/auth/register` for counselor account registration
  - ✅ Auto-login after registration (returns JWT token immediately)
  - ✅ Multi-tenant support (email + tenant_id uniqueness check)
  - ✅ Username uniqueness validation across all tenants
  - ✅ Password validation (minimum 8 characters)
  - ✅ Default role assignment (counselor if not specified)
  - ✅ Registration form added to `/console` page
  - ✅ Complete TDD test coverage (6 test cases, all passing)
  - ✅ Updated iOS API documentation with Swift examples

### Changed
- **Documentation Reorganization** (2025-12-26)
  - Moved safety transition testing docs to `docs/testing/` directory:
    - `SAFETY_TRANSITIONS_SUMMARY.md` - Test plan overview and design decisions
    - `SAFETY_TRANSITIONS_MANUAL_TEST_GUIDE.md` - Step-by-step testing procedures
    - `SAFETY_TRANSITIONS_TEST_FINDINGS.md` - Sticky behavior analysis and trade-offs
    - `SAFETY_TRANSITIONS_TEST_RESULTS_TABLE.md` - Expected results and keyword detection
    - `SLIDING_WINDOW_SAFETY_ASSESSMENT.md` - Algorithm details and cost savings
  - Updated PRD.md with references to testing documentation
  - Cleaned up 7 experiment JSON files (data already documented in PRD.md):
    - Removed cache_strategy_comparison.json, experiment_results*.json, strategy_*.json
  - Reason: Better organization, separate concerns (PRD vs testing docs)
  - Impact: Cleaner root directory, easier navigation, preserved test documentation
- **Extended JWT Token Expiration** (2025-12-13)
  - Access Token: 24 hours → 90 days (3 months)
  - Refresh Token: 7 days → 90 days (3 months)
  - Reason: Improve developer experience, reduce re-login frequency for prototype phase
  - Impact: Both tokens now have consistent 90-day expiration

### Fixed
- **RAG Similarity Threshold Too Strict** (2025-12-13)
  - Fixed: RAG knowledge retrieval now working for parenting queries
  - Root cause: similarity_threshold=0.7 was too high; real-world scores max at ~0.54-0.59
  - Solution: Lowered threshold from 0.7 to 0.5 based on production data analysis
  - Impact: RAG now retrieves relevant parenting knowledge instead of returning empty results
  - Files updated: `app/api/realtime.py`, `tests/integration/test_realtime_rag_integration.py`
- **Codeer Agent Mismatch Error** (2025-12-11)
  - Fixed: Claude Sonnet 4.5 and Gemini 2.5 Flash models now fully operational
  - Root cause: Incorrect agent_id parameter passing in realtime.py
  - Solution: Updated to use correct agent ID from codeer_model parameter
  - Impact: All three Codeer models (Claude, Gemini, GPT-5) now working in production

### Changed
- **Codeer Model Recommendations** (2025-12-11)
  - **Default model changed**: GPT-5 Mini → Gemini 2.5 Flash (best speed/quality balance)
  - **Model reordering**: Prioritized by performance (Gemini > Claude > GPT-5 Mini)
  - **Frontend UI updates**: Added performance hints (~10.3s, ~10.6s, ~22.6s) and status badges
  - **Documentation updates**: Removed "experimental" status, added verified performance benchmarks
  - **Performance data** (from real testing):
    - Claude Sonnet 4.5: 10.3s latency (highest quality)
    - Gemini 2.5 Flash: 10.6s latency (⭐ recommended: best balance)
    - GPT-5 Mini: 22.6s latency (stable, specialized knowledge)

### Added
- **Codeer Multi-Model Support for Realtime Counseling** (2025-12-11)
  - ✅ 3 Codeer models available: GPT-5 Mini (default), Claude Sonnet 4.5, Gemini 2.5 Flash
  - ✅ Session pooling optimization for Codeer provider (50% latency improvement)
  - ✅ Frontend model selector UI with responsive design (mobile + desktop)
  - ✅ Model metadata display in analysis results (shows which model was used)
  - ✅ API parameter `codeer_model` for model selection
  - ✅ Model comparison benchmark script (`scripts/test_all_codeer_models.py`)
  - ✅ Documentation updates with security best practices
- **Codeer AI API Client Integration** (2025-12-11)
  - ✅ Complete async CodeerClient service with httpx
  - ✅ SSE (Server-Sent Events) streaming support for real-time chat
  - ✅ Comprehensive API coverage: Chat, Stream, RAG, STT, TTS, Web Search
  - ✅ 27 integration tests covering all endpoints and scenarios
  - ✅ Configuration management: API key, base URL, default agent
  - ✅ Automatic error handling and retry mechanisms
  - ✅ Full TDD implementation (RED-GREEN-REFACTOR workflow)
- **Gemini Explicit Context Caching Production Implementation** (2025-12-10)
  - ✅ Cache Manager service with Strategy A (always update with accumulated transcript)
  - ✅ Multi-layer cleanup mechanism (manual delete + TTL + cleanup script)
  - ✅ Automatic fallback for short content (<1024 tokens)
  - ✅ Integration with `/api/v1/realtime/analyze` endpoint
  - ✅ Cache metadata tracking in API responses
  - ✅ 8 integration tests covering all scenarios
- **Cache Strategy Comparison Experiments** (2025-12-10)
  - Strategy A: Full cumulative (10/10 success, 100% stability, complete context)
  - Strategy B: Incremental only (9/10 success, 90% stability, missing context)
  - Experimental data saved in `CACHE_STRATEGY_ANALYSIS.md`
- **Cost-benefit analysis** for Explicit Context Caching in realtime counseling (PRD.md)
  - Complete cost breakdown: STT + Gemini with/without caching
  - ROI analysis: 15.2% cost savings per session, NT$10,439/year savings (10 sessions/day)
  - Recommendation: Implement Explicit Caching for production

### Fixed
- **Critical Cache Update Bug** (2025-12-10)
  - Fixed: Cache content was frozen after first creation, never updated
  - Root cause: `get_or_create_cache()` returned existing cache without checking new content
  - Solution: Implemented Strategy A - always delete old cache and create new one with latest transcript
  - Impact: AI analysis now correctly includes all conversation history

### Changed
- **Realtime API Enhancement** - Updated chat creation to use UUID for uniqueness
  - Added microsecond precision + UUID to prevent duplicate chat names
  - Improved error handling for Codeer API interactions
- GCP Billing Monitor with AI analysis and email reports (3 new APIs)
- BigQuery integration for real-time cost tracking
- Automated billing report generation with Gemini AI
- Detailed logging for Gemini response diagnosis
- **Realtime STT Counseling** (Phase 2 Frontend Complete): AI-powered realtime counseling analysis
  - TDD approach with 11 integration tests (Backend API complete)

### Notes
  - ElevenLabs Scribe v2 Realtime API integration (Chinese support)
  - Manual speaker toggle (counselor/client) for demo simplicity
  - Click-to-analyze with progressive minute-by-minute simulation
  - Commercial-grade mobile-first UI with RWD (breakpoints: 640px, 1024px)
  - Chat-style transcript with WhatsApp-like message bubbles
  - Severity-based alert badges (Critical/Warning/Info)
  - Floating Action Button (FAB) and fixed bottom bar for mobile
  - Loading skeletons and empty state designs
  - Analysis cards: summary, alerts, suggestions with animated gradients
  - Demo mode with 5-scenario progressive conversation simulation
  - localStorage-based session history management
- **Performance Benchmark Testing Suite** for realtime analysis
  - Comprehensive benchmark script testing 1/10/30/60 minute transcripts
  - Performance test reports and client-friendly documentation
  - 100% success rate across all transcript lengths (11-12 second response times)
- **Gemini Cache Performance Tracking**
  - Usage metadata logging (cached_content_token_count, prompt_token_count, candidates_token_count)
  - Cache performance test script for cumulative transcripts (1-10 minutes)
  - Validates Gemini Implicit Caching effectiveness (75% cost savings on cached tokens)

### Changed
- Gemini max_tokens increased from 4000 to 8000 (prevents JSON truncation)
- Documentation consolidation (42 → 31 files, single source of truth in PRD.md)
- Code quality improvements (11 files refactored, 100% file size compliance)
- **Realtime AI Prompt Enhancement**: Improved counseling supervision prompt based on professional counselor feedback
  - Empathy-first approach: AI now validates parent emotions before offering guidance
  - Concrete, actionable suggestions: All recommendations include specific steps and dialogue examples
  - Gentle, non-judgmental tone: Replaced direct/critical language with supportive guidance
  - Structured output: Summary, empathy section, concerns, and action steps with examples
  - **Focus Scope Optimization**: Added 【分析範圍】section to ensure AI focuses on latest minute instead of summarizing entire conversation
    - Main focus: Latest 1-minute dialogue (real-time supervision context)
    - Background context: Earlier conversation for understanding continuity
    - Prevents generic summaries, ensures actionable real-time guidance

### Fixed
- Gemini report grading JSON truncation (success rate: 85% → 100%)
- BigQuery lazy-load to prevent CI authentication errors
- Incorrect await syntax in sync database calls
- Broken documentation references after consolidation

### Infrastructure
- Billing monitoring with AI cost analysis
- Email notification system (Gmail SMTP)
- Enhanced error handling with robust JSON parsing

---

## [0.3.1] - 2025-11-29

### Added
- Real-time transcript keyword analysis API with AI-powered extraction
- Session name field for better organization
- Auto-calculated time range from recording segments
- Claude Code agent configuration with TDD enforcement

### Changed
- Gemini 2.5 Flash as default LLM provider (40% cost reduction, < 2s response time)
- Simplified keyword analysis UI (only requires session + transcript)
- Removed "(iOS)" suffix from API endpoint titles for consistency

### Fixed
- CI/CD test failures with GeminiService mocking
- Admin role resource deletion permissions

### Performance
- Session service layer extraction with N+1 query fixes (**3x faster**: 800ms → 250ms)
- UI client-case-list API optimization (**5x faster**: 1.2s → 240ms)
- Claude Code workflow optimization (93% efficiency gains in hook output)

---

## [0.3.0] - 2025-11-25

### Added
- Fast CI strategy with smoke tests (< 10 seconds)
- Report generation integration tests with mocked background tasks
- Admin role with cross-counselor resource management

### Changed
- Skip expensive background task tests in staging CI for faster deployment

### Fixed
- N+1 query issues in Sessions API using SQLAlchemy `joinedload`
- N+1 query issues in UI client-case-list API (TDD approach)
- Integration test compatibility for CI environment

### Removed
- Playwright frontend tests (focus on backend API testing)

---

## [0.2.5] - 2025-11-24

### Added
- Pre-commit hooks with comprehensive checks (ruff, security, file size)
- Pre-push hooks with 4 core API smoke tests
- 100% integration test pass rate (106 tests)

### Changed
- Reduced smoke tests to 4 core API tests for faster feedback
- Updated API response status codes (POST: 201, DELETE: 204)
- Optimized pre-push hook to run only critical tests

### Fixed
- All remaining integration test failures (100% pass rate achieved)
- Report API tests field name assertions (`edited_content_markdown`)
- Client API tests with required fields and correct status codes
- Session creation tests to expect 201 Created status

### Security
- Explicitly forbid `--no-verify` in git operations (documented in CLAUDE.md)
- Added security checks for API keys, secrets, and private keys in pre-commit hooks

---

## [0.2.4] - 2025-11-24

### Added
- Mypy type checking for improved code quality
- SSL requirement for Supabase Pooler connections

### Changed
- Suppress var-annotated mypy errors for SQLAlchemy columns (compatibility fix)
- Separate unit and integration tests in CI pipeline

### Fixed
- SSL connection issues with Supabase Pooler (`sslmode=require`)
- Import order in model files
- Integration test database setup and auth tests
- None-safety checks for OpenAI API responses

---

## [0.2.3] - 2025-11-23

### Added
- iPhone simulator preview views in console
- GET client-case detail endpoint
- Auto-populate update form when selecting client-case
- Comprehensive API integration tests (66 tests)

### Changed
- Case status from string enum to integer (0: 未開始, 1: 進行中, 2: 已結案)
- Reorganized UI Pages into two categories (CRUD Forms + Preview Pages)
- Improved mobile RWD for console with better navigation and tabs
- Redesigned console sidebar with light gray theme

### Fixed
- Client-case list 500 error with timezone-aware datetime
- Field mapping priority in update form
- Schema field display for empty values

### Performance
- Optimized CI/CD pipeline for better reliability and performance

---

## [0.2.2] - 2025-11-22

### Added
- Append recording API for iOS incremental upload

### Changed
- Reverted Cloud Run memory to 1Gi to fix container startup timeout

### Performance
- Optimized Cloud Run resources for cost efficiency (1 CPU, 1Gi memory)

---

## [0.2.1] - 2025-11-21

### Added
- Test credentials display in console for easy development access

### Changed
- Fixed tenant dropdown in console login form

---

## [0.2.0] - 2025-11-19

### Added
- Comprehensive multi-tenancy documentation for iOS developers
- RecordingSegment schema for OpenAPI/Swagger
- Weekly progress reports (Week 46)

### Changed
- Consolidated and cleaned up documentation structure
- Moved API documentation to root directory for better accessibility
- Clarified tenant_id usage in all documentation

### Removed
- Unused future feature design documents

### Fixed
- Report generation anti-duplicate logic improvements

---

## [0.1.0] - 2025-11-18

**Phase 3 Release** - Authentication & Business Logic

### Added
- JWT authentication system (24h expiration)
- Client, Case, Session CRUD with auto-generated codes
- Report generation with async background tasks
- UI integration APIs for iOS (`/api/v1/ui/*`)
- Web console for API testing
- Multi-tenant architecture with RBAC

### Security
- bcrypt password hashing, JWT authentication
- Multi-tenant data isolation with row-level permissions

---

## [0.0.5] - 2025-10-17

### Added
- Improved RAG chat intent classification with lower similarity threshold

### Changed
- Replace SSE streaming with direct JSON response for report generation
- Improve upload error handling and form field name

### Fixed
- Remove NUL characters from PDF text before storing in PostgreSQL
- Improve error visibility in report generation UI

### Removed
- Outdated PDF report for RAG

---

## [0.0.4] - 2025-10-12

### Added
- Output format parameter for report generation
- RAG system comparison mode
- Weekly progress reports (W41)

### Changed
- Report generation from GET to POST
- Cloud Run memory limit to 1Gi
- RAG system to use Gemini

### Fixed
- Docker git installation for ragas dependency
- RAG retrieval and comparison mode UX

### Performance
- Enhanced stats page with per-strategy display

---

## [0.0.3] - 2025-10-05

### Added
- Chunk strategies API with matrix visualization
- RAG evaluation system with matrix view and batch evaluation
- Enhanced evaluation matrix with chunk strategies integration

### Performance
- Organized sidebar navigation for better UX

---

## [0.0.2] - 2025-10-04

### Added
- Multi-environment deployment (staging/production)
- Table format for case reports

### Changed
- Cloud Run memory from 128Mi to 512Mi

### Fixed
- Placeholder credentials for secret detection
- Documentation organization

---

## [0.0.1] - 2025-10-03

**Initial Release** - RAG System Foundation

### Added
- RAG Console with Supabase integration
- RAG system models and API endpoints
- RAG processing services (chunking, embedding, retrieval)
- Counseling console UI with document upload

### Changed
- RAG chat tests to integration approach

### Fixed
- File upload functionality
- RAG Console debugging and UI

### Infrastructure
- GitHub Actions CI/CD to Cloud Run
- Docker containerization with Poetry
- Workload Identity Federation for deployment

---

## Development Timeline

### 📅 Phase 1: RAG Foundation (Oct 2025)
**Duration**: 2 weeks | **Versions**: 0.0.1 - 0.0.3

Established the core RAG (Retrieval-Augmented Generation) system infrastructure:
- Document processing pipeline (chunking, embedding, retrieval)
- RAG evaluation system with matrix visualization
- Cloud Run deployment with CI/CD automation
- Supabase integration for vector storage (pgvector)

**Key Achievement**: Fully functional RAG engine for knowledge retrieval

---

### 📅 Phase 2: RAG Optimization (Oct 2025)
**Duration**: 1 week | **Versions**: 0.0.4 - 0.0.5

Enhanced RAG capabilities and report generation:
- Multi-format report output (JSON, Markdown, Table)
- Vertex AI RAG comparison and evaluation
- Gemini 2.5 integration for improved performance
- Intent classification for intelligent chat routing

**Key Achievement**: Production-ready RAG system with 40% cost reduction

---

### 📅 Phase 3: Business Logic (Nov 2025)
**Duration**: 2 weeks | **Versions**: 0.1.0 - 0.3.1

Built complete counseling platform with authentication and CRUD operations:
- JWT authentication with multi-tenant isolation
- Client, Case, Session management
- Real-time transcript keyword analysis
- iOS-optimized APIs with performance tuning (3-5x faster)
- 100% integration test coverage (106 tests)

**Key Achievement**: Full-stack counseling platform ready for iOS integration

---

## Version History Summary

| Version | Date | Phase | Key Features |
|---------|------|-------|--------------|
| **0.3.1** | 2025-11-29 | **Phase 3** | Real-time keyword analysis, Session naming, Gemini 2.5 Flash |
| 0.3.0 | 2025-11-25 | Phase 3 | N+1 query fixes, Fast CI, Admin role |
| 0.2.5 | 2025-11-24 | Phase 3 | Pre-commit hooks, 100% test coverage |
| 0.2.4 | 2025-11-24 | Phase 3 | Mypy type checking, SSL fixes |
| 0.2.3 | 2025-11-23 | Phase 3 | iPhone simulator views, Case status integers |
| 0.2.2 | 2025-11-22 | Phase 3 | Append recording API for iOS |
| 0.2.1 | 2025-11-21 | Phase 3 | Console improvements |
| 0.2.0 | 2025-11-19 | Phase 3 | Multi-tenancy docs, API consolidation |
| **0.1.0** | 2025-11-18 | **Phase 3** | **Authentication & Business Logic** |
| 0.0.5 | 2025-10-17 | Phase 2 | RAG chat improvements, Report generation fixes |
| 0.0.4 | 2025-10-12 | Phase 2 | Report formats, RAG comparison, Vertex AI POC |
| 0.0.3 | 2025-10-05 | Phase 1 | Chunk strategies, Evaluation matrix |
| 0.0.2 | 2025-10-04 | Phase 1 | Multi-env deployment, Report tables |
| **0.0.1** | 2025-10-03 | **Phase 1** | **RAG System Foundation** |

**Total Development Time**: ~8 weeks (Oct 3 - Nov 29, 2025)
**Total Versions**: 14 releases
**Total Commits**: 227

---

## Upgrade Notes

### From 0.3.0 to 0.3.1

**New Features Available:**
- Use `POST /api/v1/sessions/{id}/analyze-keywords` for real-time keyword analysis
- Add optional `name` field when creating sessions

**Breaking Changes:**
- None

**Recommended Actions:**
- Update iOS app to utilize real-time keyword analysis during counseling sessions
- Consider adding session naming feature to improve UX

### From 0.2.x to 0.3.0

**API Changes:**
- No breaking changes, all updates are backward compatible

**Performance Improvements:**
- Sessions API is now 3x faster (response time: 800ms → 250ms)
- UI client-case-list API is now 5x faster (response time: 1.2s → 240ms)

**Recommended Actions:**
- No code changes required, enjoy the performance boost!

---

## [Keep a Changelog] Categories

This project uses the following change categories:

- **Added** - New features or endpoints
- **Changed** - Changes to existing functionality
- **Deprecated** - Features that will be removed in future versions
- **Removed** - Features that have been removed
- **Fixed** - Bug fixes
- **Security** - Security vulnerability fixes
- **Performance** - Performance improvements and optimizations

---

**For full commit history**: See [GitHub repository](https://github.com/Youngger9765/career_ios_backend)
**For API documentation**: Visit `/docs` (Swagger UI) or `/redoc` (ReDoc)
**For iOS integration guide**: See [IOS_API_GUIDE.md](./IOS_API_GUIDE.md)
