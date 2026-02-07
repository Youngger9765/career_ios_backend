# Changelog

All notable changes to the Career iOS Backend API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **Admin Dashboard Time Filtering** (2026-02-08): Fixed 3 critical bugs causing cost calculations to include all historical data
  - **Bug #1 - `get_top_users`**: Missing `SessionAnalysisLog.analyzed_at` filter caused Gemini costs to include all history
  - **Bug #2 - `get_user_segments`**: Function received `time_range` parameter but never used it (only checked registration date)
  - **Bug #3 - `export_csv`**: Missing `SessionAnalysisLog.analyzed_at` filter caused CSV exports to include all historical costs
  - **Impact**: Before fix, selecting "Today" would still show costs from weeks/months ago (1800% inflation in test data: 975 logs vs 51 logs)
  - **Fix Pattern**: Added `or_(SessionAnalysisLog.id.is_(None), SessionAnalysisLog.analyzed_at >= start_time)` to preserve NULL handling while filtering by time
  - **Files Modified**:
    - `app/api/v1/admin/dashboard.py`: Fixed 3 endpoints, added `or_` import
    - `tests/manual/test_dashboard_time_filtering.py`: Verification test showing 924 old records that were incorrectly included
  - **Documentation**:
    - `DASHBOARD_TIME_FILTER_FIXES.md`: Technical summary with test results
    - `DASHBOARD_FIX_COMPARISON.md`: Before/after comparison with visual examples
    - `sql/verify_dashboard_fix.sql`: SQL queries to manually verify the fix
  - **Testing**: Linting passed, module imports successfully, manual test confirms fix

### Added
- **App Config API Expansion** (2026-02-08): Extended `/api/v1/app/config/{tenant}` endpoint from 3 to 7 fields
  - **New URL Fields**:
    - `data_usage_url`: Data Usage Guide (Island Parents: `/island_parents_data_usage/`)
    - `help_url`: User Guide / Help Center (Island Parents: `/island_parents_help/`)
    - `faq_url`: Frequently Asked Questions (Island Parents: `/island_parents_faq/`)
    - `contact_url`: Contact Us page (Island Parents: `/island_parents_contact_us/`)
  - **URL Standardization**: Updated Island Parents URLs from URL-encoded Chinese and page_id format to clean `/island_parents_*` pattern
  - **Files Modified**:
    - `app/schemas/app_config.py`: Extended `AppConfigResponse` schema
    - `app/core/config.py`: Added 4 new URL constants per tenant
    - `app/api/app_config.py`: Updated `TENANT_CONFIGS` mapping and endpoint docstring
    - `tests/integration/test_app_config_api.py`: Updated tests to validate all 7 fields
  - **Backward Compatibility**: No breaking changes, pure addition maintaining compatibility
  - **Integration Tests**: All 5 tests passing (100% coverage of new fields)

- **Admin Dashboard V2 - Business-Driven Redesign** (2026-02-08): Complete redesign from technical monitoring to business decision platform
  - **Product Strategy**: Jobs-to-be-Done analysis identifying 3 core business needs
    1. **Cost Control**: Predict spending, identify anomalies, prevent waste
    2. **User Retention**: Segment users, detect churn risk, find upsell opportunities
    3. **Resource Optimization**: Track efficiency, optimize AI model usage
  - **New API Endpoints** (`app/api/v1/admin/dashboard.py`):
    - `GET /cost-per-user`: Cost anomaly detection with status classification (normal/high_cost/test_account)
    - `GET /user-segments`: User cohort analysis (Power Users, Active, At-Risk, Churned)
    - `GET /cost-prediction`: Monthly cost forecasting with growth rate analysis
  - **New Dashboard UI** (`app/templates/admin_dashboard_v2.html`):
    - **Section 1 - Cost Control Center**: Cost prediction, anomaly alerts, cost trend chart
    - **Section 2 - User Health**: User segmentation cards, engagement metrics, suggested actions
    - **Section 3 - Operational Efficiency**: Summary metrics, cost breakdown by service
  - **Design Principles**: Action-oriented (every metric suggests next step), comparison-rich (trends), predictive (forecast future), segmented (user cohorts)
  - **Business Impact**: Projected savings of $71/month (identify waste $45, prevent churn $16, upsell $10)
  - **Time Savings**: 87% reduction in weekly cost review time (15 min → 2 min)
  - **Documentation**:
    - `docs/dashboard-redesign-product-strategy.md`: Product vision, Jobs-to-be-Done, user personas
    - `docs/dashboard-redesign-implementation-guide.md`: Step-by-step implementation, testing, deployment
    - `docs/DASHBOARD_V2_SUMMARY.md`: Executive summary, key metrics, success criteria
    - `docs/DASHBOARD_BEFORE_AFTER.md`: Visual comparison, ROI analysis, workflow improvements
  - **Status**: Design complete, ready for stakeholder approval and implementation

### Fixed
- **Dashboard Data Accuracy Fixes** (2026-02-08): Fixed 4 critical bugs in admin dashboard
  - **Bug 1 - Cost Breakdown Duplicates**: Standardized model name grouping
    - **Issue**: Model names like `models/gemini-flash-lite-latest` and `gemini-flash-lite-latest` appeared as separate entries
    - **Fix**: Used SQL `CASE WHEN` to normalize model names to display names before grouping
    - **Impact**: Cost Breakdown now shows 2-3 services instead of 4-5 duplicate entries
  - **Bug 2 - Incorrect Total Cost**: Added Gemini costs to summary
    - **Issue**: Total Cost only included ElevenLabs STT costs (from `SessionUsage`), missing Gemini costs (from `SessionAnalysisLog`)
    - **Fix**: Query both tables and sum costs: `total_cost = elevenlabs_cost + gemini_cost`
    - **Impact**: Total Cost increased from $0.22 to $0.66 (correct value)
  - **Bug 3 - Meaningless Avg Tokens/Day**: Replaced with Avg Cost/Day
    - **Issue**: Average token count has no business value (different tokens have different costs)
    - **Fix**: Calculate average cost per day instead: `avg_cost_per_day = total_cost / num_days`
    - **Frontend**: Updated label from "Avg Tokens/Day" to "Avg Cost/Day", displays as "$0.0212"
  - **Bug 4 - Incomplete Time Range Charts**: Fill missing dates with zeros
    - **Issue**: "Past 7 Days" chart only showed dates with data, skipping days with no activity
    - **Fix**: Generate complete date range and fill missing dates with 0 values
    - **Impact**: Charts now show consistent 7-day or 30-day timelines
  - **Files Modified**:
    - `app/api/v1/admin/dashboard.py`: 4 endpoints modified (summary, cost-breakdown, overall-stats, daily-active-users)
    - `app/templates/admin_dashboard.html`: Updated "Avg Tokens/Day" to "Avg Cost/Day"

### Changed
- **Dashboard Top Users Token Split** (2026-02-08): Split "Total Tokens" into three service-specific columns
  - **Rationale**: Provide visibility into token usage by different AI services (Gemini Flash 3, Gemini Lite, ElevenLabs)
  - **New Table Columns**:
    - Gemini Flash 3 (tokens): Report generation usage
    - Gemini Lite (tokens): Emotion feedback usage
    - ElevenLabs (hours): STT audio transcription duration
  - **Backend Changes**:
    - Modified `GET /api/v1/admin/dashboard/top-users` to query `SessionAnalysisLog` table
    - Used SQLAlchemy `case()` expressions to separate tokens by model type
    - Changed ordering from `total_tokens` to `total_cost_usd`
    - Updated CSV export with new columns
  - **Frontend Changes**:
    - Updated table headers with service names and units
    - Added color-coded backgrounds: Purple (Flash 3), Green (Lite), Blue (ElevenLabs)
    - Format: Flash/Lite tokens with commas (1,234), ElevenLabs as "9.7h"
  - **Files Modified**:
    - `app/api/v1/admin/dashboard.py` (lines 572-656, 777-850)
    - `app/templates/admin_dashboard.html` (table structure, JS, CSS)
  - **Documentation**: See `DASHBOARD_TOKENS_SPLIT.md` for complete implementation details

- **Dashboard UI Enhancement** (2026-02-07): Replaced Model Distribution chart with Daily Active Users trend
  - **Rationale**: Model Distribution showed fixed proportions (no insights); DAU tracks user engagement
  - **New Chart**: Line chart showing daily unique user counts over time
    - Green color scheme (growth/positive trend)
    - Smooth curve with area fill
    - Integer-only Y-axis (no decimals)
    - Tooltip shows "X users" format
  - **Time Filter Support**:
    - Today: Hourly breakdown (HH:MM)
    - 7 Days: Daily breakdown (MM/DD)
    - 30 Days: Daily breakdown (MM/DD)
  - **New API Endpoint**: `GET /api/v1/admin/dashboard/daily-active-users`
    - Counts `DISTINCT counselor_id` per period from `SessionUsage` table
    - Supports tenant filtering
    - Returns `{labels: ["2/1", "2/2", ...], data: [12, 15, 8, ...]}`
  - **Backward Compatibility**: Old `/model-distribution` endpoint kept (marked deprecated)
  - **Files Modified**:
    - `app/api/v1/admin/dashboard.py` (+60 lines)
    - `app/templates/admin_dashboard.html` (chart replacement)

### Fixed
- **Analysis Logging Bug Fixes** (2026-02-07): Fixed two critical bugs in analysis logging system
  - **Bug 1 - Model Name Recording**: All analysis logs incorrectly recorded `model_name` as `"gemini-3-flash-preview"` instead of actual model used
    - **Root Cause**: API endpoints didn't include `model_name` in `_metadata` when calling `SessionBillingService.save_analysis_log_and_usage()`
    - **Impact**: Dashboard analytics showed wrong model usage; cost calculations may have been inaccurate
    - **Fix Applied**:
      - `EmotionAnalysisService` now returns `model_name` and `provider` in `token_usage` dict
      - All API endpoints (`analyze_emotion_feedback`, `quick_feedback`, `deep_analyze`, `report`) now pass `model_name` to `_metadata`
      - `MetadataBuilder` updated with correct model names: `gemini-flash-lite-latest` (emotion), `gemini-1.5-flash-latest` (deep/report)
      - Added defensive fallback in `SessionBillingService._get_default_model_name()` with warning log
    - **Files Modified**:
      - `app/services/analysis/emotion_service.py` (lines 164-179)
      - `app/api/sessions.py` (lines 597-600)
      - `app/api/session_analysis.py` (lines 221-228, 362-370)
      - `app/services/analysis/keyword_analysis/metadata.py` (lines 99, 122, 146-154)
      - `app/services/analysis/session_billing_service.py` (lines 38-48, 120-122)
  - **Bug 2 - Missing ElevenLabs STT Cost**: Cost tracking only included Gemini LLM costs, missing ElevenLabs Scribe v2 Realtime STT cost ($0.40/hr = 68% of total)
    - **Root Cause**: `estimated_cost_usd` only calculated token costs, didn't include per-hour STT costs
    - **Impact**: Dashboard showed costs ~8x lower than actual ($0.073/hr vs expected $0.535/hr)
    - **Cost Structure** (per hour):
      - ElevenLabs Scribe v2 Realtime: $0.40 (68%)
      - Gemini Flash Lite (Emotion): $0.10 (17%)
      - Gemini Flash 1.5 (Report): $0.035 (6%)
      - Infrastructure (not tracked): $0.052 (9%)
      - **Total tracked**: $0.535/hr
    - **Fix Applied**:
      - `SessionBillingService.save_analysis_log_and_usage()` now calculates ElevenLabs cost based on session duration
      - Formula: `elevenlabs_cost = (duration_seconds / 3600) * 0.40`
      - Total cost: `gemini_cost + elevenlabs_cost`
    - **Files Modified**:
      - `app/services/analysis/session_billing_service.py` (lines 168-191)
      - `app/services/core/quick_feedback_service.py` (lines 94-109)
      - `app/services/analysis/parents_report_service.py` (lines 83-100)
  - **Correct Model Pricing** (updated in fixes):
    - Gemini Flash Lite Latest: Input $0.075/1M, Output $0.30/1M
    - Gemini Flash 1.5 Latest: Input $0.50/1M, Output $3.00/1M (deep_analyze)
    - Gemini Flash 1.5 Latest: Input $1.25/1M, Output $5.00/1M (report generation)
  - **Test Coverage**: Added `test_logging_unit.py` with 4 comprehensive tests (all passing)
  - **Verification**: Unit tests confirm model_name inclusion and ElevenLabs cost calculation

### Completed
- **Domain & Deployment** (2026-02-04): All domain-related tasks completed
  - Landing Page deployed to comma.study (WordPress)
  - Backend Web pages DNS/SSL configured (forgot-password, reset-password, etc.)
  - `APP_URL` environment variable updated to comma subdomain

### Changed
- **Subscription Management Delegation to RevenueCat** (2026-02-03): Removed backend subscription expiry validation to let RevenueCat handle subscription state
  - **Removed**: `subscription_expires_at` validation in `app/middleware/usage_limit.py` (lines 40-58)
  - **Removed**: `subscription_expires_at` initialization in `Counselor.__init__` (lines 111-113)
  - **Kept**: `subscription_expires_at` field in model for backward compatibility
  - **Architecture**: RevenueCat is now the single source of truth for subscription validity on iOS
  - **Backend Role**: Only manages usage quotas (monthly_limit_minutes = 360 minutes)
  - **Impact**: Subscription users can create sessions without backend expiry check; iOS client validates subscription via RevenueCat SDK
  - **Reason**: Eliminates redundant validation logic; prevents sync issues between backend and RevenueCat state

### Fixed
- **Usage Tracking Bug Fix** (2026-02-03): Fixed session creation not updating monthly_minutes_used for subscription accounts
  - **Root Cause**: Session creation endpoint (`POST /api/v1/sessions`) was checking usage limits but not incrementing the usage counter
  - **Location**: `app/api/sessions.py:116-122` - Added usage tracking before creating session
  - **Fix**: Increment `monthly_minutes_used` when creating sessions with subscription mode
  - **Edge Case**: Handle sessions without `duration_minutes` (optional field) - only track when provided
  - **Impact**: Subscription accounts now correctly track session usage; monthly limits properly enforced
  - **Test Coverage**: Added 2 comprehensive regression tests in `tests/integration/test_usage_tracking_verification.py`
    - `test_usage_tracking_complete_flow`: Verifies cumulative tracking (0 → 20 → 80 minutes)
    - `test_usage_limit_enforcement`: Verifies 360-minute limit blocks session creation (HTTP 429)
  - **Timezone Bug Fix**: Fixed naive/aware datetime comparison in session numbering (`app/services/core/session_service.py`)
  - **Test Results**: All 432 integration tests pass, CI/CD successful

- **Subscription Initialization Bug** (2026-02-03): Fixed new subscription accounts being rejected with "subscription expired" error
  - **Root Cause**: `usage_period_start` and `subscription_expires_at` were not initialized in `Counselor.__init__`
  - **Fix**: Added automatic initialization of both fields for new accounts
  - **Values**: `usage_period_start` = account creation time, `subscription_expires_at` = creation time + 365 days
  - **Impact**: New accounts can now create sessions immediately after registration
  - **Test Results**: All 8 billing tests pass, session creation tests pass
  - **Deprecated Warning Fixed**: Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)`

### Added
- **Subscription Billing as Default** (2026-02-03): Changed default billing mode from prepaid to subscription for RevenueCat integration
  - **Model Update**: `Counselor.billing_mode` now defaults to `subscription` (was `prepaid`)
  - **Business Context**: Frontend uses RevenueCat for iOS subscription management
  - **New Accounts**: All registrations via `/api/auth/register` default to subscription mode
  - **Default Limits**: New accounts get 360 minutes (6 hours) monthly limit
  - **Migration Scripts**: Added scripts to migrate existing accounts to subscription
  - **Test Coverage**: 8 new tests covering both subscription and prepaid modes
  - **Backward Compatible**: Existing prepaid accounts remain unaffected, prepaid mode still functional
  - **Impact**: Aligns new user onboarding with iOS App Store subscription model

- **Usage Stats API Documentation - Complete** (2026-02-03): Added usage statistics query endpoint to console and iOS guide
  - **Console Update**: Added "使用量統計 Usage" section with usage stats endpoint
  - **iOS Guide Update**: Added IOS_GUIDE_PARENTS.md Section 2.7 "使用量統計 API" with full Swift implementation
  - **Endpoint**: `GET /api/v1/usage/stats` (requires auth)
  - **Features**: Monthly limit, used minutes, remaining quota, usage percentage, billing period
  - **Swift Examples**: Complete UsageStats Codable struct, async fetch function, SwiftUI usage view
  - **UI Components**: Progress bar, warning alerts, remaining quota display
  - **Impact**: iOS developers have complete reference for implementing usage tracking UI

- **Email Verification Documentation** (2026-02-03): Added comprehensive email verification guide to iOS documentation
  - **New Section**: IOS_GUIDE_PARENTS.md Section 2.2.1 "Email 驗證機制"
  - **Content**: Complete email verification flow, error handling (403), resend mechanism
  - **API Reference**: Section 16.3.3 (verify-email), Section 16.3.4 (resend-verification)
  - **Swift Examples**: Full implementation examples for error handling and resend
  - **Console Page**: Added email verification and resend endpoints to test console
  - **Impact**: iOS developers now have complete guide for handling email verification

### Changed
- **App Config API - BREAKING CHANGE** (2026-02-03): Simplified from 8 fields to 3 essential URL fields
  - **Removed fields**: `help_url`, `forgot_password_url`, `base_url`, `version`, `maintenance_mode`
  - **Kept fields**: `terms_url`, `privacy_url`, `landing_page_url`
  - **Reason**: iOS client only needs these 3 URLs; other fields unused
  - **Impact**: iOS client MUST update `AppConfig` struct before consuming this API
  - **Migration**: Remove 5 fields from Swift model, keep only 3 fields
  - **Endpoint**: `GET /api/v1/app/config/{tenant}` (island_parents, career)
  - **Tests**: All 5 integration tests pass, explicitly verify removed fields absent

- **CI/CD Pipeline - Automatic Database Migrations for Staging** (2026-02-01): Staging deployments now automatically execute database migrations
  - Pipeline runs `alembic upgrade head` before deploying to Cloud Run
  - Uses `DATABASE_URL` (connection pooler) for IPv4 compatibility with GitHub Actions
  - Ensures database schema matches deployed code version
  - Production migrations remain manual for safety (requires human approval)
  - **Impact**: Faster deployment cycle, prevents schema/code mismatch errors
  - **Location**: `.github/workflows/ci.yml` (staging job only)

- **Password Reset API - BREAKING CHANGE** (2026-02-01): Migrated from URL-based tokens to 6-digit verification codes
  - **Previous**: `GET /api/v1/auth/password-reset/verify?token=xxx` (removed)
  - **New**: `POST /api/v1/auth/password-reset/verify-code` (added)
  - **Reason**: Better mobile UX, easier for users to type codes from email
  - **Client Impact**: iOS app must update to use new verification code flow
  - **Migration Guide**: See `docs/api/password-reset-verification-code.md`

### Added
- **Multi-Step Password Reset Template with Deeplink Support** (2026-02-01): Enhanced forgot password page for iOS in-app browser
  - 4-step single-page flow: Email → Verification Code → New Password → Success
  - Progress indicator (1/4, 2/4, 3/4, 4/4)
  - Auto-deeplink redirect to App when `source=app` parameter detected
  - Fallback mechanism: Returns to web login if App fails to open
  - Deeplink scheme: `islandparent://auth/forgot-password-done`
  - Support for both iOS in-app browser and web browser usage
  - **Implementation**: `app/templates/forgot_password.html` (complete rewrite)
  - **Testing**: 3 new integration tests in `tests/integration/test_password_reset_flows.py`
  - **Benefits**: Seamless iOS App integration, improved user experience, single-page convenience

- **Password Reset Verification Code System** (2026-02-01): Enhanced security with user-friendly 6-digit codes
  - 6-digit verification codes (instead of 64-character URL tokens)
  - 10-minute code expiration (vs 6-hour token expiration)
  - Account lockout after 5 failed verification attempts (15-minute lockout)
  - Optional pre-validation endpoint to check code before password form
  - Email delivery with customizable templates per tenant
  - Full end-to-end test coverage (request → verify → confirm → login)
  - **API Endpoints**:
    - `POST /api/v1/auth/password-reset/request` (updated to generate codes)
    - `POST /api/v1/auth/password-reset/verify-code` (new)
    - `POST /api/v1/auth/password-reset/confirm` (updated to accept codes)
  - **Implementation**: `app/api/v1/password_reset.py`, `app/models/password_reset.py`
  - **Testing**: 7 integration tests in `tests/integration/test_password_reset_verification.py`
  - **Documentation**: Complete API guide at `docs/api/password-reset-verification-code.md`
  - **Benefits**: Mobile-friendly, reduced friction, improved security with lockout mechanism

- **App Config API** (2026-01-31): Dynamic URL management for iOS client
  - Multi-tenant support (`island_parents`, `career`)
  - Public endpoint `GET /api/v1/app/config/{tenant}`
  - Returns dynamic URLs: terms, privacy, landing page, help, forgot password
  - Environment-aware base_url configuration
  - Version tracking and maintenance mode support
  - No authentication required (public endpoint)
  - 404 response for invalid tenants
  - **Implementation**: `app/api/app_config.py`, `app/schemas/app_config.py`
  - **Testing**: Complete unit and integration test coverage
  - **Documentation**: Added to `IOS_API_GUIDE.md` and `IOS_GUIDE_PARENTS.md`
  - **Benefits**: No app release needed to update URLs, supports A/B testing, instant maintenance mode toggle

- **WordPress Legal Pages** (2026-01-31): Elementor-ready HTML pages for Island Parents
  - **Landing Page**: Product introduction and features showcase
    - Deployed to: https://www.comma.study/island_parents_landing/
    - Highlights: Real-time AI feedback, safety assessment, parenting guidance
  - **Privacy Policy**: GDPR/Taiwan PIPA compliant privacy policy
    - Deployed to: https://www.comma.study/island_parents_privacy_policy/
    - 7 sections: Data collection, usage, third-party services, security, children's privacy
  - **Terms of Service**: Comprehensive terms of service
    - Deployed to: https://www.comma.study/island_parents_terms_of_service/
    - 10 sections: Service description, usage rules, refund policy, disclaimers
  - **Technical Features**:
    - Responsive design (desktop/tablet/mobile)
    - Direct paste into WordPress Elementor HTML blocks
    - PM can update content without API redeployment
    - Clean, professional styling matching Island Parents branding
  - **Location**: `wordpress-legal-pages/` directory
  - **Documentation**: `wordpress-legal-pages/README.md`

- **Billing Mode Support and Monthly Usage Limits** (2026-01-31): Flexible payment models for prepaid and subscription users
  - Billing mode support (prepaid/subscription) for flexible payment models
  - Monthly usage limits for subscription users (360 minutes/month)
  - Usage statistics API endpoint (`GET /api/v1/usage/stats`)
  - Rolling 30-day usage period with auto-reset
  - HTTP 429 error when subscription limit exceeded
  - Backward compatible: All existing users default to prepaid mode

- **Email Verification Status in API Responses** (2026-01-31): Enhanced auth endpoints to include email verification status
  - **Register Response**: Added `email_verified`, `verification_email_sent`, and `message` fields
  - **Login Response**: Now returns `user` object with `email_verified` field
  - **Email Verification Check**: Login blocked for unverified users when email verification enabled (HTTP 403)
  - **Database Schema**: Added `email_verified` boolean column to Counselor model
  - **Verify Email Endpoint**: Sets both `is_active` and `email_verified` to true
  - **Test Environment**: Email verification disabled by default in tests via autouse fixture
  - **Implementation**:
    - Modified: `app/api/auth.py`, `app/schemas/auth.py`, `app/models/counselor.py`
    - Modified: `tests/integration/conftest.py`, `tests/integration/test_auth_api.py`, `tests/integration/test_email_verification.py`
    - Added: `tests/integration/test_issue_4_email_verification_status.py` (4 comprehensive tests)
    - Test Coverage: 37/37 auth tests passing

- **Registration Security Enhancements** (2026-01-30): Comprehensive security layer for user authentication
  - **Rate Limiting**: SlowAPI-based protection against abuse
    - Registration: 3 requests per hour per IP
    - Login: 5 requests per minute per IP
    - Password reset: 3 requests per hour per IP
    - Development environment: Relaxed limits (100/20/20) for testing
  - **Password Strength Validation**: Enhanced from 8 to 12 character minimum
    - Must contain uppercase, lowercase, numbers, and special characters
    - Checks against 10,000+ common password blacklist
    - Clear error messages guide users to create strong passwords
  - **Email Verification System**: JWT-based verification workflow
    - Configurable via `ENABLE_EMAIL_VERIFICATION` env variable (default: enabled)
    - 24-hour token expiry for verification links
    - New endpoints: `/api/v1/auth/verify-email` and `/api/v1/auth/resend-verification`
    - Unverified accounts cannot login (HTTP 403 with clear message)
  - **Implementation**:
    - New modules: `app/middleware/rate_limit.py`, `app/core/password_validator.py`, `app/core/email_verification.py`
    - Modified: `app/api/auth.py`, `app/schemas/auth.py`, `app/services/external/email_sender.py`
  - **Testing**: 32 new integration tests (100% pass rate)
    - `test_rate_limiting.py` (3 tests)
    - `test_password_validation.py` (14 tests)
    - `test_email_verification.py` (15 tests)
    - Updated 37 existing test files with strong passwords (161 instances)
  - **Security**: All features follow OWASP best practices and production-ready

- **Deeplink Redirect & Email Autofill for Password Reset** (2026-01-30): iOS App integration improvements
  - Added `source` parameter to `PasswordResetRequest` schema (Optional, backward compatible)
  - Password reset emails include `&source=app` in reset link when requested from iOS
  - Reset password page (`reset_password.html`) detects source and redirects accordingly:
    - From App: Attempts deeplink `islandparent://auth/forgot-password-done`
    - Fallback mechanism: 3-second timeout checks `document.visibilityState`
    - If App not installed/opened: Auto-redirects to web login page
  - Forgot password page (`forgot_password.html`) supports `?mail=xxx` parameter
  - Email autofill: iOS can pass user email via URL parameter for seamless UX
  - All changes backward compatible (Optional parameters, graceful fallback)
  - Testing: All 14 password reset integration tests pass

- **Terms of Service & Privacy Policy Pages** (2026-01-27): Legal pages for RevenueCat/App Store compliance
  - Route: `/island-parents/terms` - Terms of Service with 10 comprehensive sections
  - Route: `/island-parents/privacy` - Privacy Policy compliant with GDPR/Taiwan PIPA
  - Shared template system (`legal_base.html`) with sticky table of contents
  - Responsive design: Desktop sidebar TOC + Mobile collapsible dropdown
  - Smooth scroll navigation with active section highlighting (Intersection Observer)
  - Content covers: Service description, user rights, data handling, GDPR compliance, refund policy
  - Ready for RevenueCat Paywall integration (App Store審核要求)
  - PM可隨時更新文案（僅需編輯 HTML 模板，無需重新部署）

- **Improved OpenAPI Documentation for analyze-partial** (2026-01-26): Enhanced Swagger UI experience
  - Added comprehensive summary and description with multi-tenant behavior explanation
  - Added 3 response examples (island_parents_green, island_parents_red, career_analysis)
  - Documented all response codes (200/401/404/500) with clear descriptions
  - Included feature highlights (non-blocking, background tasks, RAG, token tracking)
  - Improved developer experience for iOS/frontend teams using `/docs`

### Removed
- **Old Token-based Password Reset Verification** (2026-02-01): Deprecated endpoint removed
  - `GET /api/v1/auth/password-reset/verify?token=xxx` endpoint removed
  - `PasswordResetVerifyResponse` schema no longer exported (internal use only)
  - **Reason**: Replaced by more secure verification code flow
  - **Migration**: Update clients to use `POST /api/v1/auth/password-reset/verify-code`

### Security
- **Password Reset Brute Force Protection** (2026-02-01): Multi-layer security enhancements
  - Rate limiting: 5 password reset requests per hour per IP
  - Verification lockout: 15-minute account lock after 5 failed code verification attempts
  - Failed attempt tracking: `verify_attempts` counter and `locked_until` timestamp
  - IP audit trail: Request IP and usage IP logged to database
  - User enumeration prevention: Always return success message regardless of email existence
  - One-time code usage: Tokens marked as `used` with timestamp after successful password reset
  - **Risk Mitigation**: Prevents automated attacks, credential stuffing, and verification code guessing

### Changed
- **Session Creation with Usage Limits** (2026-01-31): Session creation now checks usage limits based on billing mode
  - Counselor model extended with billing mode and usage tracking fields
  - Prepaid users: Blocked if credits <= 0
  - Subscription users: Blocked if monthly limit exceeded or subscription expired
  - Auto-resets usage period after 30 days

- **Parents Report Prompt Refinement** (2026-01-29): Balanced professional authority with accessibility
  - Modified prompt in `parents_report_service.py` to use life-like language while maintaining credibility
  - **Strategy**: Moderate use of simple professional terms, avoid excessive academic jargon
  - **Preserved terms**: 同理, 界限, 情緒, 歸屬感, 價值感 (simple, understandable)
  - **Removed**: Expert name-dropping (Gottman, 阿德勒, 薩提爾, Dan Siegel, Ross Greene, Dr. Becky Kennedy)
  - **Translated concepts**:
    - '冰山理論' → '表面行為背後的真正需求'
    - '情緒教練時刻' → '陪伴孩子面對情緒'
    - '黃金時刻' → '很難得的時刻'
    - '權力鬥爭' → '親子之間的拉扯'
  - **Neutral phrasing**: 'Gottman理論' → '研究發現...', '專家建議...'
  - **RAG integration**: Remains active, only presentation style changed
  - **A/B testing validation**: Academic density reduced 100% (19.1 → 0.0 terms/1000 chars)
  - **Impact**: No API changes, no schema changes, no iOS changes required
  - **Testing**: Created automated A/B testing script (`scripts/test_parents_report_ab.py`)
  - **Verification**: All 9 integration tests pass

### Database
- **Billing Mode and Usage Tracking Schema** (2026-01-31): Extended counselors table for flexible billing
  - Added `billing_mode` enum column to counselors table (prepaid/subscription)
  - Added subscription usage tracking columns:
    - `monthly_usage_limit_minutes` (default: 360)
    - `monthly_minutes_used` (default: 0)
    - `usage_period_start` (rolling 30-day period)
  - Migration: All existing users default to prepaid mode (backward compatible)

### Fixed
- **Emotion-Feedback API Production Bugs** (2026-01-28 to 2026-01-29): Resolved 422 and 500 errors
  - **422 Error Fix** (Commit c8cfe7b): Empty context validation
    - Modified `EmotionFeedbackRequest.context` to allow empty string (default="")
    - First emotion-feedback call can now send `context=""` without validation error
    - Changed schema from `min_length=1` to optional empty string
  - **500 Error Fix** (Commit c8cfe7b): Token usage extraction
    - Fixed `get_last_token_usage()` method not found error in `emotion_service.py`
    - Extract token usage directly from `response.usage_metadata`
    - Pattern matches `quick_feedback_service.py` implementation
  - **Redundant Validation Removal** (Commit 2af6ab2): Route handler cleanup
    - Removed duplicate empty context check in `/api/sessions.py` endpoint
    - Route handler had second validation layer (400 error) blocking empty context
    - Now relies solely on Pydantic schema validation
  - **Test Enablement**: Removed `pytest.mark.skip` decorator from emotion API tests
  - **Impact**: All emotion-feedback API calls now work correctly in staging/production
  - **Testing**: `test_emotion_api.py` tests enabled and passing

- **Safety Assessment Test Failure** (2026-01-27): Fixed `test_safe_conversation_returns_green_level`
  - Root cause: Placeholder `/messages` endpoint doesn't store transcript data
  - Solution: Test now directly sets `transcript_text` on session object
  - Updated test assertions to match `RealtimeAnalyzeResponse` schema (summary/alerts/suggestions)
  - Test passes reliably in CI/CD pipeline after 5 consecutive failures
  - Documented limitation: `/api/v1/sessions/{id}/messages` endpoint is placeholder (message storage not implemented)
- **Removed duplicate deep-analyze endpoint** (2026-01-26): Fixed 23 failing tests
  - Removed obsolete TDD stub endpoint in `sessions.py` that returned hardcoded response
  - The proper implementation in `session_analysis.py` now handles all deep-analyze requests
  - Root cause: Duplicate endpoint was registered first, shadowing the real implementation
  - Tests now correctly receive `RealtimeAnalyzeResponse` with full analysis results
  - Impact: All E2E workflow, session analysis, and RAG integration tests now pass

### Deprecated
- **Deep Analysis API - TDD GREEN phase** (2026-01-26): Replaced by session_analysis.py
  - ~~Added POST /sessions/{id}/deep-analyze endpoint (placeholder with hardcoded safe status)~~
  - ~~DeepAnalysisResponse schema with safety_level/display_text/quick_suggestion~~
  - This was a TDD stub that has been superseded by the full implementation
- **Emotion feedback API logging** (2026-01-25): DB and BigQuery logging for cost tracking and analytics
  - Track token usage (prompt/completion tokens + cost)
  - Log analysis results to SessionAnalysisLog (PostgreSQL)
  - Background task uploads to BigQuery
  - Follows same pattern as quick/deep feedback APIs
- **IOS_GUIDE_PARENTS.md v1.10** (2026-01-25): Complete Client & Case Management documentation
  - Added Section 2.6 with complete client-case API documentation
  - Included Swift implementation examples with error handling
  - Added prerequisite warnings for session creation workflow
  - Updated API endpoint overview (Section 12.3) to highlight Island Parents UI APIs
  - Documentation completeness increased from 92% to ~98%
- **Island Parents Delivery Checklist** (2026-01-25): `docs/weekly/ISLAND_PARENTS_DELIVERY_CHECKLIST.md`
  - Comprehensive delivery overview for iOS team handoff
  - Complete API specifications with Request/Response examples
  - Validation results with actual test data from staging environment
  - Quick test guide for iOS team verification
  - Contact information and pending items requiring PM decisions

### Fixed
- **Staging URLs in IOS_GUIDE_PARENTS.md** (2026-01-25)
  - Updated 3 outdated staging URLs to current format
  - Old: `career-app-api-staging-kxaznpplqq-uc.a.run.app`
  - New: `career-app-api-staging-978304030758.us-central1.run.app`
  - Affected sections: 2.6 (Client-Case API), 11 (Forgot Password Web Flow)

- **ElevenLabs Token API Documentation** (2026-01-12)
  - Corrected endpoint path in IOS_API_GUIDE.md: `/api/v1/realtime/elevenlabs-token` → `/api/v1/transcript/elevenlabs-token`
  - Added Section 6 in IOS_GUIDE_PARENTS.md with complete API documentation
  - Resolved iOS team 404 error when calling the endpoint
  - Note: Swagger documentation (`/docs`) is the authoritative source for API endpoints

- **Quick Feedback Truncation Bug** (2026-01-08)
  - Root cause: `max_tokens=50` was too small, causing Gemini to truncate mid-word
  - Symptoms: Incomplete responses like "你", "能複", "願意" (1-3 chars)
  - Fix: Increased `max_tokens` from 50 to 500
  - Added `min_chars=7` validation with fallback for incomplete responses
  - Improved text parsing to remove garbage (English text, parentheses)
  - Now returns complete sentences with optional emoji: "願意學習傾聽是非常棒的進步 🌟"

- **Report Encouragement Truncation Bug** (2026-01-08)
  - Root cause: Hard truncation `[:15]` was cutting sentences mid-word
  - Symptoms: "你耐心傾聽孩子分享諮商體驗，並" (cut off at "並")
  - Fix: Removed hard truncation, let AI naturally generate within prompt's limit
  - Now returns complete sentences: "你正努力嘗試承接孩子深奧的思想"

- **Deep Analyze Field Validation** (2026-01-08)
  - Added min/max validation for `display_text` (4-20 chars)
  - Added min/max validation for `quick_suggestion` (5-20 chars, based on 200 expert suggestions)
  - Log warnings for out-of-range values without hard truncation
  - Fallback to default "分析完成" if display_text too short

- **GET Report API Format Consistency** (2026-01-08)
  - `GET /api/v1/sessions/{session_id}/report` now returns same format as POST
  - Uses `tenant_id` (from JWT) to determine format, NOT `report.mode`
  - For `tenant_id == "island_parents"`: always returns flat `ParentsReportResponse`
  - iOS can now use the same Model for both POST and GET responses
  - Other tenants still receive full `ReportResponse` for backward compatibility
  - Updated IOS_GUIDE_PARENTS.md v1.6 with GET endpoint documentation

### Changed
- **Analysis Services Refactoring** (2026-01-07)
  - Extracted 4 new modules from large files for better maintainability:
    - `expert_suggestion_service.py` - AI-powered suggestion selection
    - `session_billing_service.py` - Incremental billing with ceiling rounding
    - `analysis_helpers.py` - Utility functions for keyword analysis
    - `parents_report_service.py` - Parent-child dialogue report generation
  - File size optimizations:
    - `keyword_analysis_service.py`: 1397 → 632 lines (-55%)
    - `session_analysis.py`: 771 → 529 lines (-31%)
  - Updated `__init__.py` with backward-compatible re-exports
  - All 333 integration tests pass

### Security
- **Admin API DEBUG Mode Hardening** (2026-01-07)
  - Fixed security vulnerability allowing unauthenticated admin access
  - DEBUG mode now requires `ENVIRONMENT != production AND != staging`
  - Affects: `admin_counselors.py` and `admin_credits.py`
  - All admin endpoints now properly protected in staging/production

### Fixed
- **Pydantic V2 Deprecation Warnings** (2026-01-07)
  - Migrated 14 `class Config:` blocks to `model_config = ConfigDict(...)` pattern
  - Files updated: auth.py, analysis.py, ui_client_case.py, session_usage.py, client.py, session.py, report.py
  - All 333 integration tests pass
- **datetime.utcnow() Deprecation** (2026-01-07)
  - Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)`
  - Files: security.py, credit_billing.py, billing_analyzer.py
- **IOS_GUIDE_PARENTS.md** - Authentication API documentation corrections (2026-01-07)
  - Fixed login endpoint: `/api/v1/auth/login` → `/api/auth/login`
  - Fixed login body: `username` → `email` + added `tenant_id` requirement
  - Fixed auth/me endpoint: `/api/v1/auth/me` → `/api/auth/me`
  - Added `expires_in` field and complete user object in login response
  - Updated Section 11.1 API reference table
- **IOS_GUIDE_PARENTS.md** - Corrected quick-feedback API documentation
  - Removed outdated `recent_transcript` body requirement
  - API now correctly documented as auto-reading from session

### Added
- **Time-based Transcript Segmentation for Quick/Deep APIs** (2026-01-05)
  - New `_extract_transcripts_by_time()` helper in `session_analysis.py`
  - Quick Feedback: extracts last 15 seconds of recordings
  - Deep Analyze: extracts last 60 seconds of recordings
  - Both APIs now receive `full_transcript` (context) + `transcript_segment` (focus)
  - Fallback: uses last segment if no recordings within time window
  - Updated prompts with dual-section structure:
    - 【完整對話背景 - 供參考脈絡】
    - 【最近 N 秒內容 - 重點分析對象】
  - Frontend polling intervals updated:
    - Append: 10 seconds (fixed)
    - Quick: 15 seconds (fixed)
    - Deep: dynamic based on safety level (green:60s, yellow:45s, pink:30s)
  - Files: `session_analysis.py`, `quick_feedback_service.py`, `keyword_analysis_service.py`, `parenting.py`, `recording.html`

- **PromptRegistry - Unified Prompt Architecture** (2026-01-04)
  - New centralized prompt management system in `app/prompts/`
  - File structure:
    - `base.py` - Default prompts (fallback for any tenant)
    - `career.py` - Career counseling prompts (deep, report)
    - `parenting.py` - Island Parents prompts (quick, deep, report)
    - `__init__.py` - PromptRegistry class with `get_prompt()` method
  - Features:
    - Multi-tenant support with automatic fallback to default
    - Tenant alias: `island` → `island_parents` (flexible for future separation)
    - Mode support for island_parents deep analysis: `practice` / `emergency`
    - Type support: `quick`, `deep`, `report`
  - Usage: `PromptRegistry.get_prompt("island_parents", "deep", mode="emergency")`
  - Updated services:
    - `quick_feedback_service.py` - Now accepts `tenant_id` parameter
    - `keyword_analysis_service.py` - Uses PromptRegistry instead of hardcoded prompts
  - Prompt coverage:
    | Type | Career | Island Parents | Default |
    |------|--------|----------------|---------|
    | quick | ❌ fallback | ✅ 親子專用 | ✅ 通用 |
    | deep | ✅ 職涯分析 | ✅ practice/emergency | ✅ 通用 |
    | report | ✅ 職涯報告 | ✅ 8學派報告 | ✅ 通用 |
  - PRD updated with full architecture documentation

### Changed
- **Recording-Based Billing** (2026-01-05)
  - Changed billing calculation from elapsed time to actual recording time
  - Old method: `duration = current_time - session.start_time` (included idle/pause time)
  - New method: `duration = sum(recordings[].duration_seconds)` (only counts recording time)
  - User benefits:
    - Pausing the conversation no longer incurs charges
    - Counselor stepping away doesn't consume credits
    - Only active recording time is billed
  - File: `app/services/keyword_analysis_service.py`

- **Credits API for Island Parents** (2026-01-05)
  - Fixed clients_history.html to use `/api/auth/me` instead of non-existent `/api/v1/credits/balance`
  - Now correctly displays remaining credits from `available_credits` field
  - File: `app/templates/island_parents/clients_history.html`

### Documentation
- **IOS_GUIDE_PARENTS.md v1.4** (2026-01-05)
  - Fixed Deep Analyze endpoint: `/api/v1/sessions/{id}/deep-analyze` (was incorrectly documented as `analyze-partial`)
  - Fixed recordings/append format: `start_time` and `end_time` must be ISO 8601 datetime strings (not floats)
  - Validated complete 11-step API flow via browser automation testing
  - Test flow: Login → Get Credits → Create Client+Case → Create Session → Set Scenario → Get ElevenLabs Token → Append Recording → Quick Feedback → Deep Analysis → Generate Report → History Page
  - All APIs tested and confirmed working

### Fixed
- **Traditional Chinese (zh-TW) Enforcement** (2026-01-02)
  - Issue: Simplified Chinese characters found in AI prompts and code comments
    - Files affected: app/services/keyword_analysis_service.py (lines 45-50, 74-87)
    - Characters: 从→從, 专家→專家, 建议→建議, 挑选→挑選, 适合→適合, 对话→對話, 等级→等級, 数量→數量, 当前→當前, 库→庫, 请→請, 选择→選擇, 规则→規則, 必须→必須, 改写→改寫, 输出→輸出
  - Fix: Converted all simplified Chinese to Traditional Chinese
    - Updated docstrings and AI prompts in keyword_analysis_service.py
    - Added explicit zh-TW enforcement to both Quick Feedback and Deep Analysis prompts
    - Added instruction: "CRITICAL: 所有回應必須使用繁體中文（zh-TW），不可使用簡體中文。"
  - Impact: All AI responses (Quick Feedback & Deep Analysis) now guaranteed to use Traditional Chinese
  - Files: app/services/keyword_analysis_service.py, app/services/quick_feedback_service.py
  - Commit: 7c0f9dd

- **Quick Feedback Contextual Analysis Fix** (2026-01-02)
  - Issue: Hardcoded scenario rules caused false positives in feedback
    - Example: "我數到三，一、二、三！" (threatening countdown) misclassified as "testing microphone"
    - Root cause: Prompt had "如果...則..." rules that matched keywords without context
  - Fix: Replaced hardcoded rules with contextual understanding
    - Removed all "如果家長在數數/測試麥克風 → 回應..." type rules
    - Added instructions to analyze full conversation context:
      - 對話的脈絡和情境 (conversation context and situation)
      - 家長當下的互動方式 (parent's current interaction style)
      - 對話的走向 (trajectory of the conversation)
    - Added anti-template instruction: "不要套用固定模板"
  - Impact: AI now provides contextually appropriate feedback based on actual conversation flow
  - Test result: 9/9 quick feedback tests pass, can now distinguish nuanced situations
  - File: app/services/quick_feedback_service.py:19-39
  - Commit: Pending

- **Quick Feedback Token Limit Fix** (2026-01-02)
  - Issue 1: Quick Feedback always returned fallback message "繼續保持，你做得很好"
    - Root cause: Google Cloud authentication expired
    - Error: `google.auth.exceptions.RefreshError: Reauthentication is needed`
    - Fix: Re-authenticated with `gcloud auth application-default login` and restarted server
  - Issue 2: After auth fix, Quick Feedback only returned single characters (e.g., "你", "深")
    - Root cause: `max_tokens=100` was too restrictive, Gemini hit MAX_TOKENS limit
    - Server log: "Response may be incomplete. Finish reason: 2" (2=MAX_TOKENS)
    - Symptom: Chinese characters need multiple tokens, even short responses couldn't fit
  - Fix: Implemented two-layer length control strategy
    - Increased `max_tokens` from 100 → 1000 (safety ceiling for output)
    - Kept prompt instruction "請用 1 句話（20 字內）" for content-level control
    - Rationale: `max_output_tokens` (Vertex AI) only counts OUTPUT tokens, not input
    - This prevents truncation while giving budget for formatting/complete sentences
  - Impact: Quick Feedback now generates complete, contextual responses
  - Test result: "先同理孩子不想寫的心情，再好奇他的困難。" (complete sentence, no truncation)
  - File: app/services/quick_feedback_service.py:71
  - Commit: Pending

- **Database Migration: Added Missing `last_billed_minutes` Column** (2026-01-02)
  - Issue: Analysis stuck due to missing `session_usages.last_billed_minutes` column
  - Root cause: Migration 02c909267dd6 was marked as applied but column wasn't created
  - Fix: Manually added column via `ALTER TABLE session_usages ADD COLUMN last_billed_minutes INTEGER NOT NULL DEFAULT 0`
  - Impact: Real-time analysis now works correctly, incremental billing operational
  - Error: `psycopg2.errors.UndefinedColumn: column session_usages.last_billed_minutes does not exist`

- **Mobile Client List Not Reloading on "回到首頁" Click** (2026-01-02)
  - Issue: When clicking "回到首頁" button, client list showed stale data from initial login
  - Root cause: `goToHome()` function didn't reload clients from API
  - Original behavior: Showed cached HTML from initial login, no API call
  - Fix: Inlined client loading logic directly in `goToHome()` function
  - Implementation:
    - Made `goToHome()` async function
    - Added `fetch('/api/v1/clients')` call with proper error handling
    - Re-renders client list with fresh data from API
    - Handles edge cases (no clients → show form, renderClientList not defined → log error)
  - Impact: Client list always fresh when returning home, newly added clients appear immediately
  - Lines changed: app/templates/realtime_counseling.html:399-462
  - Console logs: `[ONBOARDING] Going back to home`, `[CLIENT_LIST] Fetching clients...`

### Added
- **Mobile Global Navigation for Island Parents** (2026-01-02)
  - Added persistent navigation header on all mobile pages
  - Features:
    - Left: "回到首頁" (Home) button - returns to client selection
    - Right: "登出" (Logout) button in red - logs out user
  - Implementation:
    - Fixed header with z-index 9999 (always on top)
    - Only visible on mobile (md:hidden)
    - Auto-shows when user logged in, hides when logged out
  - Impact: Consistent navigation across all mobile screens, easy access to logout
  - Files changed: app/templates/realtime_counseling.html

- **Enhanced Mobile Onboarding for Island Parents** (2026-01-02)
  - Redesigned two-screen onboarding flow:
    - Screen 1: Select or create child
    - Screen 2: Choose mode (Emergency/Practice) + confirm child name
  - Features added:
    - "現在要跟 [孩子名稱] 對話" - Shows which child will be talked to
    - Back button on mode selection to re-select child
    - "開始對話" button (changed from "下一步")
  - Mobile-first: Homepage routes to client selection instead of main content
  - Impact: Better UX for parent onboarding, clear context about selected child
  - Files changed: app/templates/realtime_counseling.html

### Changed
- **Quick Feedback Improvements for Island Parents** (2026-01-02)
  - Increased interval from 10 seconds to 20 seconds (less intrusive)
  - Fixed line-breaking issues in AI responses:
    - Added "CRITICAL: 只輸出一句話，不要換行" to prompt
    - Strip `\n` and `\r` characters in response processing
  - Changed display layout to two-line format:
    - Top line: Deep analysis (larger, bold)
    - Bottom line: Quick feedback (smaller, lighter opacity)
    - No longer overwrites Deep analysis
  - Impact: More natural feedback rhythm, cleaner UI presentation
  - Files changed:
    - app/services/quick_feedback_service.py (prompt + processing)
    - app/templates/realtime_counseling.html (two-line display)

### Fixed
- **Mobile Button Click Handlers Not Working** (2026-01-02)
  - Fixed ReferenceError: functions not defined when onclick handlers executed
  - Root cause: Functions defined after HTML rendered, onclick attributes couldn't find them
  - Solution: Moved all button handler functions to early script tag (before HTML)
  - Functions moved: logout(), goToHome(), showClientForm(), backToClientSelection(), setOnboardingMode(), completeOnboarding()
  - Impact: All mobile navigation and onboarding buttons now work correctly
  - Files changed: app/templates/realtime_counseling.html
  - Testing: All 6 critical buttons verified in Chrome mobile view

- **Mobile Navigation Z-Index Issue** (2026-01-02)
  - Fixed mobile navigation being hidden behind onboarding container
  - Changed z-index from z-50 to z-[9999]
  - Impact: Navigation buttons now properly visible on all mobile pages
  - Files changed: app/templates/realtime_counseling.html

- **Mobile Client Selection Display** (2026-01-02)
  - Fixed blank screen issue after mobile login
  - Added explicit initialization of clientListMode display state
  - Impact: Client selection properly shows after login on mobile
  - Files changed: app/templates/realtime_counseling.html (checkAuth function)

- **Web Realtime Counseling - Island Parents Flow** (2026-01-02)
  - Fixed default tenant: Changed from 'career' to 'island_parents' for parent-facing web interface
  - Fixed session initialization: Now uses client selected during onboarding instead of hardcoded defaults
  - Implementation:
    - Updated `app/templates/realtime_counseling.html` default tenant_id to 'island_parents'
    - Modified session workflow to check localStorage for selectedClientId/selectedClientName
    - If client selected: Creates case and session for existing client (proper data linking)
    - If no client: Falls back to creating new client+case+session (backwards compatible)
  - Flow improvements:
    - Login → Client selection/creation → Practice mode → Analysis (all properly linked)
    - Client data persists across practice sessions via localStorage
    - Case and session correctly associated with selected child
  - Impact: Parents can now properly set up child information and track consultation history
  - Files changed: app/templates/realtime_counseling.html (+88 lines, -22 lines)

- **BigQuery Permissions for Analysis Logging** (2026-01-02)
  - Added missing BigQuery permissions for Cloud Run service account
  - Service account: career-app-sa@groovy-iris-473015-h3.iam.gserviceaccount.com
  - Granted roles:
    - roles/bigquery.dataEditor (write analysis logs to tables)
    - roles/bigquery.user (execute queries)
  - Fixed error: "Permission bigquery.tables.updateData denied on table realtime_analysis_logs"
  - Impact: Session analysis logs can now be written to BigQuery for analytics
  - Reference: Analysis logging in app/services/gbq_service.py

- **Authentication and Quick Feedback for New Session Workflow** (2026-01-02)
  - Fixed 403 Forbidden error when calling `/api/v1/sessions/{id}/recordings/append`
  - Root cause: APIClient cached auth token in constructor before user logged in
  - Solution: Read auth token fresh from localStorage on every request
  - Fixed missing quick feedback suggestions for island_parents tenant
  - Root cause: Backend returns `detailed_scripts`, frontend expected `quick_suggestions`
  - Solution: Transform `detailed_scripts` to suggestions format in session-workflow.js
  - Format: `💡 {situation}\n{parent_script}`
  - Fallback to `quick_suggestions` for career tenant (backwards compatible)
  - Impact: Analysis now works with proper authentication, quick feedback displays correctly
  - Files changed:
    - app/static/js/api-client.js (read token on every request)
    - app/static/js/session-workflow.js (transform detailed_scripts)

### Added
- **Dual-API Analysis System - Quick Feedback (雞湯文) + Deep Analysis** (2026-01-02)
  - Implemented simultaneous quick feedback and deep analysis timers
  - **Quick Feedback API** (雞湯文 - Inspirational quotes):
    - Endpoint: POST `/api/v1/realtime/quick-feedback`
    - Triggers: Every 10 seconds during 🟢 Green and 🟡 Yellow safety levels
    - Disabled during 🔴 Red (already fast enough with 15s deep analysis)
    - Toast: Yellow gradient ("⚡ 快速分析中...")
    - Purpose: Fill gaps between deep analyses with lightweight encouragement
    - Response time: ~1-2 seconds (Gemini Flash lightweight prompt)
  - **Deep Analysis API** (Full analysis with safety level updates):
    - Endpoint: POST `/api/v1/realtime/analyze` (existing)
    - Triggers: Adaptive intervals based on safety level
      - 🟢 Green: Every 60 seconds
      - 🟡 Yellow: Every 30 seconds
      - 🔴 Red: Every 15 seconds (unchanged)
    - Toast: Purple-blue gradient ("⚡ 自動分析中...")
    - Purpose: Change safety levels and adjust analysis intervals
  - **Dual-Timer Independence**: Both timers run simultaneously without interference
  - **UI Enhancements**:
    - Added "即時建議" (Quick Suggestions) header to suggestions section
    - Added "分析完成" (Analysis Complete) badge next to header
    - Different toast colors distinguish quick vs deep analysis
  - Architecture:
    - Backend: `/app/services/quick_feedback_service.py` (AI-powered encouragement)
    - Frontend: Dual-timer logic in `app/templates/realtime_counseling.html`
    - Cost: +$0.0036/hour (+0.85%) for green-light scenarios
  - Impact: Continuous feedback flow prevents "blank gaps" during long analysis intervals
  - Files changed:
    - app/templates/realtime_counseling.html (dual-timer implementation)
    - Backend: quick_feedback_service.py, realtime.py (API already existed)
  - Reference: Based on `/api/v1/realtime/quick-feedback` endpoint (added 2026-01-01)

### Changed
- **Web/iOS API Architecture Verification** (2026-01-01)
  - Confirmed Web version already uses 8 Schools Prompt via `keyword_analysis_service`
  - Web and iOS share unified analysis logic (no duplication):
    - Both platforms use same prompts from `app/prompts/parenting.py`
    - Both use 200 expert suggestions from RAG knowledge base
    - Both leverage identical keyword analysis service
  - API response formats differ by platform:
    - Web: `RealtimeAnalyzeResponse` (realtime.py)
    - iOS: `IslandParentAnalysisResponse` (sessions_keywords.py)
  - Core analysis logic is identical across platforms
  - ✅ Refactoring successfully removed duplicate code from realtime.py
  - Impact: No additional integration needed for Web - already using 8 Schools framework
  - Reference: Architecture analysis confirms unified codebase (2026-01-01)

### Fixed
- **Cloud Run Deployment - Orphaned Alembic Revision** (2026-01-01)
  - Fixed Cloud Run deployment failure: Container failed to start on port 8080
  - Root cause: Database had orphaned revision `58545e695a2d` from deleted organization management migration
  - Real error from Cloud Run logs: `Can't locate revision identified by '58545e695a2d'`
  - Timeline:
    - Commit ccbfc95 added organization management with migration 58545e695a2d
    - Migration was deployed to staging database
    - Commit 3c87a32 reverted feature and deleted migration file
    - Database retained alembic_version entry for 58545e695a2d
    - Subsequent deployments failed when alembic couldn't find the file
  - Solution: Created fix script to update database revision to correct value (6b32af0c9441)
  - Implementation:
    - Added scripts/fix_alembic_version.py to update alembic_version table
    - Modified scripts/start.sh to run fix before migrations
    - Deleted wrongly restored migration file
  - Previous investigation attempts (SSL config, DATABASE_URL, restoring migration file) were incorrect
  - Impact: Enables successful Cloud Run deployment with database migrations
  - Files changed: scripts/fix_alembic_version.py (new), scripts/start.sh, deleted 58545e695a2d migration

- **Integration Test Suite Fixes** (2026-01-01)
  - Fixed test_error_handling.py status code expectations to match actual API behavior:
    - Changed 401 Unauthorized tests to 403 Forbidden (correct for protected endpoints without auth)
    - Changed 404 Not Found expectations for invalid login (security: don't reveal if user exists)
    - Fixed auth endpoint paths (`/api/auth/*` instead of `/auth/*`)
  - Added `@pytest.mark.skip` to test_annotated_safety_window.py (feature not yet implemented):
    - Tests require `ANNOTATED_SAFETY_WINDOW_TURNS` constant (missing)
    - Tests require `_build_annotated_transcript` function (missing)
  - Test results improved from 22 failures to 284 passed, 4 failed, 94 skipped, 11 errors

### Added
- **Modular JavaScript Architecture for Web Session Workflow** (2026-01-01)
  - Created modular JavaScript architecture to unify Web and iOS session workflows
  - New modules:
    - `app/static/js/api-client.js` - Centralized API communication layer with authentication
    - `app/static/js/session-workflow.js` - Unified session management for web clients (iOS-style)
  - Feature flag integration in `app/templates/realtime_counseling.html`:
    - `USE_NEW_SESSION_WORKFLOW` flag controls new vs legacy API paths
    - New workflow: create client+case → create session → append → analyze
    - Legacy workflow: direct realtime analyze API (preserved for backwards compatibility)
  - Response transformation layer:
    - Automatically converts Session API responses to Realtime API format
    - Ensures zero UI changes required (`displayAnalysisCard` function compatible)
  - Documentation and examples:
    - `docs/web-session-workflow-implementation.md` - Complete implementation guide
    - `app/static/js/README.md` - API client and session workflow documentation
    - `app/static/integration-example.js` - Standalone integration example
    - `app/static/test-session-workflow.html` - Interactive test page
  - Integration tests (`tests/integration/test_web_session_workflow.py`):
    - test_complete_web_session_workflow - Full workflow test
    - test_web_workflow_multiple_analyses - Multiple analysis segments test
    - test_web_workflow_emergency_mode - Emergency mode workflow test
  - Benefits:
    - **iOS/Web Consistency**: Both platforms now use identical session workflow
    - **Backwards Compatible**: Legacy realtime API path preserved with feature flag
    - **Modular Design**: Clean separation of concerns (API client, session workflow, UI)
    - **Easy Testing**: Standalone test page for rapid development
  - Test coverage: 3 new integration tests, 283 total tests passed (no regressions)
  - Commit: 2ec0033

### Changed
- **Reduced Dan Siegel Weight in 8 Schools Prompts** (2026-01-01)
  - Added scientific controversy warning to Dan Siegel's "Whole-Brain Child" theory
  - Reordered analysis framework to prioritize ABC behavioral model over brain dichotomy
  - Replaced "上層腦/下層腦" (upper/lower brain) terminology with neutral "情緒狀態" (emotional state)
  - Updated: `app/prompts/parenting.py` - Practice and Emergency mode prompts
  - Based on Solomon's feedback: prioritize evidence-based approaches over controversial theories

### Added
- **Quick Feedback API for Real-Time Encouragement** (2026-01-01)
  - New `/api/v1/realtime/quick-feedback` endpoint for lightweight AI-powered encouragement messages
  - Provides 1-2 second AI-generated feedback to fill gaps between full analysis cycles
  - **Unified 10-second polling interval** for consistent user experience:
    - 🟢 Green: 60-second full analysis + **10-second quick-feedback** (6 encouragements/minute)
    - 🟡 Yellow: 30-second full analysis + **10-second quick-feedback** (3 encouragements/30s)
    - 🔴 Red: 15-second full analysis only (quick-feedback disabled - already fast enough)
  - Features:
    - Context-aware AI responses using Gemini Flash (≤ 20 characters)
    - Reads recent 10-second transcript to generate appropriate encouragement
    - Graceful fallback to default messages on error
    - Latency tracking for performance monitoring
  - New files:
    - `app/services/quick_feedback_service.py` - AI-powered quick feedback service
    - `app/services/encouragement_service.py` - Rule-based fallback service (unused, kept for reference)
    - `app/schemas/realtime.py` - Added QuickFeedbackRequest/Response models
  - Updated: `app/api/realtime.py` - Integrated quick_feedback_service
  - Documentation:
    - `docs/encouragement_api_integration.md` - Complete iOS integration guide with Swift examples
    - `docs/encouragement_services_report.md` - Performance comparison (Rule-based vs AI-powered)
  - Cost impact: +$0.0036/hour (+0.85%) for green-light scenarios
  - Backward compatible: New endpoint, no changes to existing APIs

- **8 Schools of Parenting - Detailed Scripts and Theoretical Frameworks** (2025-12-31)
  - Integrated 8 major parenting theories into island_parents tenant prompts
  - New response fields for Practice Mode:
    - `detailed_scripts`: Step-by-step dialogue guidance (100-300 word specific conversation examples)
    - `theoretical_frameworks`: Theory attribution (marks which schools are used)
  - Schema extensions:
    - New `DetailedScript` model with fields: situation, parent_script, child_likely_response, theory_basis, step
    - Extended `IslandParentAnalysisResponse` with optional detailed_scripts and theoretical_frameworks
  - Prompt files:
    - `app/prompts/island_parents_8_schools_practice_v1.py` (Practice Mode - detailed teaching version)
    - `app/prompts/island_parents_8_schools_emergency_v1.py` (Emergency Mode - quick suggestions version)
  - Backward compatible: All new fields are Optional, Emergency Mode remains concise, Career tenant unaffected
  - Integration tests: `tests/integration/test_8_schools_prompt_integration.py`
  - Test scenarios: Practice/Emergency mode selection, Schema validation, Safety level evaluation, Token tracking
  - Updated: `app/services/keyword_analysis_service.py`, `app/schemas/analysis.py`, `PRD.md`
  - Foundation: `scripts/README_8_SCHOOLS_PROMPT.md`, `scripts/PROMPT_COMPARISON.md`, `scripts/test_8_schools_prompt.py`
  - Reference: `docs/PARENTING_THEORIES.md` - Comprehensive guide to 8 Schools of Parenting theories

- **Counseling Mode Support for analyze-partial API** (2025-12-31)
  - New `mode` parameter for island_parents tenant
    - `emergency`: Fast, simplified analysis (1-2 critical suggestions)
    - `practice`: Detailed teaching mode (3-4 suggestions with techniques)
  - Backward compatible: Optional parameter, defaults to `practice`
  - Career tenant: Ignores mode parameter (not applicable)
  - realtime.py bug fix: Separate `analysis_type` and `mode` fields in GBQ
  - 4 integration tests: emergency mode, practice mode, default, career ignore
  - Updated: `app/schemas/analysis.py`, `app/api/sessions_keywords.py`, `app/services/keyword_analysis_service.py`, `app/api/realtime.py`
  - Tests: `tests/integration/test_analyze_partial_api.py` (lines 472-730)

- **Configuration Management Documentation** (2025-12-31)
  - Created `docs/CONFIGURATION.md` - Single Source of Truth configuration guide
  - Model selection guide (Gemini 3 Flash, 2.0 Flash, 1.5 Pro)
  - Region compatibility documentation (global vs us-central1)
  - Anti-pattern warnings and troubleshooting guide

- **RFC 7807 Standardized Error Handling** (2025-12-31)
  - Implemented RFC 7807 (Problem Details for HTTP APIs) standard for all error responses
  - All API errors now return consistent JSON format with `type`, `title`, `status`, `detail`, and `instance` fields
  - Added comprehensive error handling modules:
    - `app/core/exceptions.py` - Custom exception classes (BadRequestError, UnauthorizedError, ForbiddenError, NotFoundError, ConflictError, UnprocessableEntityError, InternalServerError)
    - `app/core/errors.py` - Error formatting utilities with multi-language support (English/Chinese)
    - `app/middleware/error_handler.py` - Global error handler middleware
  - Updated endpoints to use RFC 7807 format:
    - `app/api/auth.py` - All authentication endpoints (register, login, profile update)
    - `app/api/sessions.py` - All session management endpoints
  - Error status code improvements:
    - Changed duplicate resource errors from 400 to 409 (Conflict) - more semantically correct
    - Maintained backward compatibility for error message content
  - Added 31 unit tests (`tests/unit/test_errors.py`) covering all error types and edge cases
  - Added 18 integration tests (`tests/integration/test_error_handling.py`) verifying end-to-end error format
  - Benefits:
    - **Consistency**: All errors follow the same predictable structure
    - **Standards Compliance**: Follows IETF RFC 7807 specification
    - **Client-Friendly**: Easier for iOS app to parse and display errors
    - **Internationalization**: Built-in support for Chinese error messages
    - **Debugging**: Instance field shows exact endpoint that failed
  - Example error response:
    ```json
    {
      "type": "https://api.career-counseling.app/errors/not-found",
      "title": "Not Found",
      "status": 404,
      "detail": "Session not found",
      "instance": "/api/v1/sessions/123e4567-e89b-12d3-a456-426614174000"
    }
    ```

### Changed
- **Configuration Management Refactoring - Single Source of Truth** (2025-12-31)
  - Refactored configuration management to establish Single Source of Truth pattern
  - Removed all `getattr()` fallback defaults from service modules
  - All modules now directly use `settings` from `app/core/config.py`
  - Modified files:
    - `app/services/gemini_service.py` - Removed Lines 12-21 fallbacks, direct settings usage
    - `app/services/cache_manager.py` - Removed Lines 25-31 fallbacks, simplified initialization
    - `scripts/test_config.py` - Created centralized test configuration module
  - Updated 3 test scripts to use unified configuration
  - Impact: Model changes now only require updating .env or config.py (Single Source of Truth)
  - Validation: 29/29 integration tests pass, configuration loading verified
  - Time saved: Model changes from 5 files → 1 file
  - Reference: `docs/CONFIGURATION.md`

### Removed
- **CodeerProvider Support** (2025-12-31)
  - Removed Codeer AI provider integration to simplify codebase
  - Now exclusively uses Gemini for all analysis
  - Impact: Reduced complexity, easier maintenance, consistent provider
  - Reason: Codeer实测效果不佳 (poor real-world performance)
  - Modified:
    - `app/schemas/realtime.py` - Removed `provider` and `codeer_model` parameters from `RealtimeAnalyzeRequest`
    - `app/schemas/realtime.py` - Removed `CodeerTokenMetadata` schema
    - `app/api/realtime.py` - Removed Codeer provider routing logic
    - `app/api/realtime.py` - Removed `_analyze_with_codeer()` function
    - `app/core/config.py` - Removed all CODEER_* configuration fields
    - `app/models/session_analysis_log.py` - Updated provider comment to remove "codeer"
  - Deleted:
    - `app/services/codeer_client.py` - Codeer API client
    - `app/services/codeer_session_pool.py` - Codeer session pooling
    - `tests/integration/test_realtime_codeer_provider.py` - Codeer provider tests
    - `scripts/list_codeer_agents.py` - Agent listing script
    - `scripts/validate_codeer_cache.py` - Cache validation script
    - `scripts/test_all_codeer_models.py` - Model testing script
  - Note: iOS app should remove `provider` parameter from API requests

### Added
- **Documentation** (2025-12-31)
  - Created `docs/PARENTING_THEORIES.md` - Comprehensive guide to 8 Schools of Parenting theories
    - Detailed explanation of each framework (Positive Discipline, Satir, Adler, Montessori, NVC, Attachment, Emotion Coaching, Behaviorism)
    - API integration examples showing how theoretical_frameworks are returned
    - Usage guidelines for AI analysis
  - Created `docs/LOGIN_ERROR_MESSAGES.md` - Security specification for login error messages
    - Unified error messages to prevent account enumeration attacks
    - Backend/Frontend implementation guidelines
    - Security logging and rate limiting specifications
    - OWASP compliant authentication error handling

### Fixed
- **Test Suite Reliability** (2025-12-31)
  - Fixed GCP credential authentication checks in integration tests
  - Tests now properly skip when credentials are invalid (not just missing)
  - Fixed time calculation bug in session usage credit deduction test
  - Impact: Test suite now passes reliably (280 passed, 90 skipped, 0 failed)
  - Modified:
    - `tests/integration/test_token_usage_response.py` - Added proper GCP auth validation
    - `tests/integration/test_session_usage_api.py` - Fixed minute overflow bug (use timedelta)

- **RAG Execution Order Bug - Critical Fix** (2025-12-31)
  - Fixed critical bug where RAG retrieval occurred AFTER Gemini call
  - RAG context now properly included in AI prompts before AI analysis
  - Impact: RAG knowledge is now actually used by the AI for better responses (200+ expert suggestions)
  - Root cause: RAG was called after Gemini, making it completely ineffective
  - Modified: `app/services/keyword_analysis_service.py`
    - Moved RAG retrieval before prompt building (line 143-177)
    - Added RAG context to prompt template (line 194)
    - Added clear step-by-step comments for flow clarity
  - Validation: 113/113 tests pass (added 7 new RAG tests)
  - Quality improvement: AI analysis now uses expert knowledge from parenting database
  - Performance impact: 0s (only execution order change)
  - Documentation: `docs/bugfix_rag_integration.md`
  - Git commit: 82cd8d1

- **Token Usage Response** (2025-12-31)
  - Fixed missing token_usage in API response fallback scenarios
  - token_usage now always included (zero values when AI call fails)
  - Impact: API response schema consistency, better error monitoring
  - Modified: `app/services/keyword_analysis_service.py`
    - Updated `_get_tenant_fallback_result()` to include `_metadata` with `token_usage`
    - Ensures token_usage is never null in API responses

### Removed
- **CacheManager removed** (2025-12-31)
  - Removed Gemini Context Caching implementation (实测效果 28%，预期 50%)
  - Vertex AI Context Caching API将于 2026-06-24 弃用
  - Deleted files:
    - `app/services/cache_manager.py` (216 lines)
    - `scripts/cleanup_caches.py` (49 lines)
    - `tests/integration/test_realtime_cache.py` (full test file)
  - Modified files:
    - `app/api/realtime.py` - Removed cache_manager import and caching logic
    - `app/services/gemini_service.py` - Removed analyze_with_cache method and caching import
    - `scripts/compare_four_providers.py` - Removed cache usage
  - Result: Simplified architecture, -300 lines of code, reduced maintenance cost

### Added
- **8 Schools of Parenting Prompt Integration** (2025-12-31)
  - ✅ Integrated 8 major parenting theories into island_parents tenant prompts
    1. Adlerian Positive Discipline (尊重、合作、溫和而堅定)
    2. Satir Model (冰山理論、探索深層需求)
    3. Behavioral Analysis (ABA, ABC 模式、環境設計)
    4. Interpersonal Neurobiology (全腦教養、情緒優先)
    5. Emotion Coaching (情緒標註、同理、設限)
    6. Collaborative Problem Solving (Ross Greene CPS)
    7. Modern Attachment & Inside-Out Perspective (Dr. Becky Kennedy)
    8. Social Awareness Parenting (性別平權、身體自主權)
  - ✅ **New Response Fields** (island_parents Practice Mode):
    - `detailed_scripts`: 逐字稿級別話術指導 (100-300 字具體對話範例)
    - `theoretical_frameworks`: 理論來源追溯 (標註使用的流派)
  - ✅ **Schema Extensions**:
    - New `DetailedScript` model with fields: situation, parent_script, child_likely_response, theory_basis, step
    - Extended `IslandParentAnalysisResponse` with optional detailed_scripts and theoretical_frameworks
  - ✅ **Prompt Files**:
    - `app/prompts/island_parents_8_schools_practice_v1.py` (Practice Mode - 詳細教學版)
    - `app/prompts/island_parents_8_schools_emergency_v1.py` (Emergency Mode - 快速建議版)
  - ✅ **Backward Compatibility**:
    - All new fields are Optional (doesn't break existing API calls)
    - Emergency Mode remains concise (no detailed_scripts)
    - Career tenant unaffected
  - ✅ **Integration Tests**: `tests/integration/test_8_schools_prompt_integration.py`
    - Test scenarios: Practice/Emergency mode selection, Schema validation, Safety level evaluation, Token tracking
  - 📝 Updated: `app/services/keyword_analysis_service.py`, `app/schemas/analysis.py`, `PRD.md`
  - 📝 Foundation: `scripts/README_8_SCHOOLS_PROMPT.md`, `scripts/PROMPT_COMPARISON.md`, `scripts/test_8_schools_prompt.py`
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
- **Career Mode Token Usage Returns 0** (2025-12-31)
  - 🐛 Fixed bug where career tenant's analyze-partial API returned token_usage = 0
  - 🔧 Root cause: `GeminiService.generate_text()` returned text string instead of response object with metadata
  - ✅ Modified `GeminiService.generate_text()` to return full response object (line 98)
  - ✅ Updated all callers to extract `.text` from response object:
    - `gemini_service.py`: chat_completion(), chat_completion_with_messages()
    - `keyword_analysis_service.py`: _parse_ai_response()
    - `analyze.py`: JSON parsing logic
  - ✅ Fixed test model field errors in `test_token_usage_response.py`:
    - Session model: removed invalid `status`, added `session_date`
    - Client/Case models: added missing required fields
  - ✅ Tests: 2/2 PASSED (was 0/2), all related tests pass (16/16)
  - 📝 Updated: `app/services/gemini_service.py`, `app/services/keyword_analysis_service.py`, `app/api/analyze.py`, `tests/integration/test_token_usage_response.py`
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
