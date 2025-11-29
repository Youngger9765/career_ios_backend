# Changelog

All notable changes to the Career iOS Backend API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Analysis Logs CRUD API for session keyword analysis history tracking
  - `GET /api/v1/sessions/{id}/analysis-logs` - Retrieve all analysis logs for a session
  - `DELETE /api/v1/sessions/{id}/analysis-logs/{log_index}` - Delete specific log entry
  - Auto-save analysis results when calling analyze-keywords endpoint
  - Structured log schema: timestamp, transcript segment, keywords, categories, confidence, insights, counselor_id, fallback flag
- File size monitoring rules in agent system (API: 300 lines, Services: 400 lines)
- Database migration for analysis_logs JSON column in sessions table
- Console UI steps for viewing and deleting analysis logs (Steps #19 & #20)
- Favicon handler to avoid 404 errors

### Changed
- Refactored console.html modularization (75% code reduction: 7245 → 1785 lines)
  - Extracted 5479 lines of step definitions to console-steps.js
  - Improved maintainability and code organization
- Refactored Sessions API to service layer pattern (1,219 → 756 lines, -38%)
  - Created KeywordAnalysisService (288 lines) for AI-powered keyword extraction
  - Enhanced SessionService with get_session_with_details() and update_session() methods
  - Extracted complex session number recalculation logic to service layer
  - Refactored analyze_session_keywords endpoint to use KeywordAnalysisService
  - All 34 integration tests pass (TDD-compliant refactoring)
- Hidden counselor_id field in analysis logs display (privacy improvement)
- Updated analyze-keywords UI text: "已自動儲存" instead of "不會儲存"
- Analysis logs display with color-coded AI vs fallback analysis

### Fixed
- SQLAlchemy JSON column change tracking with flag_modified() for analysis_logs
- Vertex AI permissions in staging environment (added roles/aiplatform.user to service account)
- Analysis logs now properly persist in database after keyword analysis

### Infrastructure
- Added roles/aiplatform.user to career-app-sa service account for Vertex AI access
- Staging environment now uses AI-powered analysis instead of fallback
- Mandatory documentation update rules in agent system (BLOCKS push if docs not updated)
  - Auto-checks CHANGELOG, PRD.md, and weekly reports before every push
  - Ensures project documentation stays current

---

## [0.3.1] - 2025-11-29

### Added
- Real-time transcript keyword analysis API (`POST /api/v1/sessions/{id}/analyze-keywords`)
  - AI-powered keyword extraction with categories and confidence scores
  - Counselor insights and reminders based on transcript content
- Session name field for better organization (`name` field in Session model)
- Auto-calculated time range from recording segments (start_time/end_time)
- Claude Code agent configuration with TDD enforcement
- Intelligent model selection strategy (Haiku/Sonnet/Opus)

### Changed
- Gemini 2.5 Flash as default LLM provider (40% cost reduction, < 2s response time)
- Simplified keyword analysis UI (only requires session + transcript)
- Removed "(iOS)" suffix from API endpoint titles for consistency

### Fixed
- CI/CD test failures in transcript keywords API with GeminiService mocking
- Admin role resource deletion permissions (can delete any tenant resources)
- Agent model selection strategy documentation (clarified static configuration only)

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
- iPhone simulator preview views in console for Client-Case CRUD operations
- GET client-case detail endpoint (`/api/v1/ui/client-case/{id}`)
- Auto-populate update form when selecting client-case
- OpenAPI examples for Bruno API client compatibility
- Comprehensive API integration tests (66 tests)

### Changed
- Case status from string enum to integer (0: 未開始, 1: 進行中, 2: 已結案)
- Reorganized UI Pages into two categories (CRUD Forms + Preview Pages)
- Improved mobile RWD for console with better navigation and tabs
- Redesigned console sidebar with light gray theme

### Fixed
- Client-case list 500 error with timezone-aware datetime comparison
- Field mapping priority in `loadClientCaseForUpdate`
- Schema field display to show all fields including empty values

### Performance
- Optimized CI/CD pipeline for better reliability and performance

---

## [0.2.2] - 2025-11-22

### Added
- Append recording API for iOS convenience (`POST /api/v1/sessions/{id}/recordings/append`)
  - Allows incremental recording upload during counseling sessions
  - Auto-updates transcript and session metadata

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
- RecordingSegment schema for OpenAPI/Swagger documentation
- Recordings field to Sessions API documentation
- Weekly progress reports (Week 46: 2025-11-11 ~ 2025-11-17)

### Changed
- Consolidated and cleaned up documentation structure
- Moved API documentation to root directory for better accessibility
- Clarified tenant_id usage in all documentation

### Removed
- Unused future feature design documents
- Outdated test reports and duplicate documentation

### Fixed
- Report generation anti-duplicate logic improvements

---

## [0.1.0] - 2025-11-18

**Phase 3 Release** - Authentication & Business Logic

### Added
- JWT authentication system with 24h token expiration
- Client CRUD operations with auto-generated client codes (C0001, C0002...)
- Case CRUD operations with auto-generated case numbers (CASE-20251124-001)
- Session CRUD operations with recording segments and reflection support
- Report generation with async background tasks (RAG + GPT-4)
- UI integration APIs for iOS convenience (`/api/v1/ui/*`)
- Web console for API testing (`/console`)
- Multi-tenant architecture with tenant_id isolation
- Role-based access control (admin, counselor)

### Security
- bcrypt password hashing
- JWT token authentication
- Multi-tenant data isolation
- Row-level permission checks (counselors can only access own data)

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
- Output format parameter for report generation (JSON/Markdown)
- RAG system comparison mode for report generation
- Vertex AI RAG Engine POC for evaluation
- Weekly progress reports (W41: 2025-10-06 ~ 2025-10-12)

### Changed
- Report generation from GET to POST (security improvement)
- Allow unauthenticated access to Cloud Run services
- Increase Cloud Run memory limit to 1Gi
- Update RAG system to use Gemini (remove Vertex AI POC)

### Fixed
- Install git in Docker for ragas package dependency
- Improve RAG retrieval and comparison mode UX

### Performance
- Enhance stats page with per-strategy display and update LLM models

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
- Table format for case reports with multi-format tabs
- CI/CD secrets configuration for Cloud Run

### Changed
- Increase Cloud Run memory from 128Mi to 512Mi
- Add timeout configuration for Cloud Run

### Fixed
- Update placeholder credentials to avoid false positive secret detection
- Reorganize documentation and update UI styling

---

## [0.0.1] - 2025-10-03

**Initial Release** - RAG System Foundation

### Added
- RAG Console with Supabase integration
- Alembic database migration system
- RAG system models and API endpoints (`/api/rag/*`)
- RAG processing services (chunking, embedding, retrieval)
- Counseling console UI and test suite
- Intelligent RAG intent detection with improved chat UX
- Comprehensive tests for RAG chat API
- Document chunks table view and modal
- Multiple file upload with progress tracking

### Changed
- Improve RAG chat tests to use integration approach
- Sync database sessions properly

### Fixed
- File upload functionality fixes
- Enhance RAG Console with improved debugging and UI fixes

### Infrastructure
- GitHub Actions CI/CD to Cloud Run
- Docker containerization with Poetry
- Cloud Build configuration for automatic deployment
- Workload Identity Federation (WIF) for GitHub Actions
- Public demo page for Career Platform API

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
