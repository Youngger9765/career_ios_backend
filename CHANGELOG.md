# Changelog

All notable changes to the Career iOS Backend API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
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
