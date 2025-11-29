# Refactor TODO

## Overview

This document tracks remaining files that exceed the established size limits and need refactoring.

**Status**: 7 files remaining (as of 2025-11-30)

---

## File Size Limits

- **API Routes**: Max 300 lines
- **Services**: Max 400 lines
- **Models**: Max 200 lines
- **Schemas**: Max 250 lines
- **Tests**: Max 500 lines

---

## API Files (300 Line Limit)

### 1. app/api/ui_client_case_list.py
- **Current**: 452 lines
- **Over by**: +152 lines (51% over limit)
- **Priority**: HIGH
- **Suggested Approach**:
  - Extract complex query building to `ClientCaseQueryBuilder` service
  - Move timeline aggregation logic to helper functions
  - Consider splitting into `ui_client_list.py` and `ui_case_list.py`
- **Related Service**: `app/services/client_case_service.py` (509 lines, also needs refactoring)

### 2. app/api/sessions.py
- **Current**: 424 lines
- **Over by**: +124 lines (41% over limit)
- **Priority**: HIGH
- **Suggested Approach**:
  - Extract keyword analysis endpoints to `sessions_keywords.py`
  - Move analysis log endpoints to `sessions_analysis.py`
  - Keep core CRUD operations in `sessions.py`
- **Related Services**:
  - `app/services/session_service.py` (555 lines, needs refactoring)
  - `app/services/keyword_analysis_service.py` (already created)

### 3. app/api/rag_evaluation.py
- **Current**: 399 lines
- **Over by**: +99 lines (33% over limit)
- **Priority**: MEDIUM
- **Suggested Approach**:
  - Extract experiment comparison logic to helper functions
  - Move prompt management to dedicated router
  - Consider splitting recommendations to separate endpoint file
- **Related Services**:
  - `app/services/evaluation_prompts_service.py` (already created)
  - `app/services/evaluation_recommendations_service.py` (already created)

### 4. app/api/reports.py
- **Current**: 328 lines
- **Over by**: +28 lines (9% over limit)
- **Priority**: LOW
- **Suggested Approach**:
  - Extract background task logic to helper functions
  - Move report generation validation to service layer
- **Related Service**: `app/services/report_operations_service.py` (already created)

---

## Service Files (400 Line Limit)

### 5. app/services/session_service.py
- **Current**: 555 lines
- **Over by**: +155 lines (39% over limit)
- **Priority**: HIGH
- **Suggested Approach**:
  - Extract session creation logic to `SessionCreationService`
  - Move query building to `SessionQueryBuilder`
  - Create `SessionValidationHelper` for validation logic
  - Keep core CRUD operations in `SessionService`
- **Impact**: Used by `app/api/sessions.py`

### 6. app/services/client_case_service.py
- **Current**: 509 lines
- **Over by**: +109 lines (27% over limit)
- **Priority**: MEDIUM
- **Suggested Approach**:
  - Extract timeline aggregation to `TimelineAggregationService`
  - Move query building to `ClientCaseQueryBuilder`
  - Create helper functions for response formatting
- **Impact**: Used by `app/api/ui_client_case_list.py`

### 7. app/services/rag_report_service.py
- **Current**: 495 lines
- **Over by**: +95 lines (24% over limit)
- **Priority**: MEDIUM
- **Suggested Approach**:
  - Extract transcript parsing to `TranscriptParserHelper`
  - Move report formatting to `ReportFormatterService`
  - Create `ReportValidationHelper` for validation logic
- **Impact**: Used by `app/api/rag_report.py`

---

## Refactoring Strategy

### Phase 1: High Priority (API Files)
1. `sessions.py` (424 lines) - Split into multiple routers
2. `ui_client_case_list.py` (452 lines) - Extract query building

### Phase 2: High Priority (Services)
3. `session_service.py` (555 lines) - Extract creation and validation

### Phase 3: Medium Priority
4. `rag_evaluation.py` (399 lines)
5. `client_case_service.py` (509 lines)
6. `rag_report_service.py` (495 lines)

### Phase 4: Low Priority
7. `reports.py` (328 lines) - Minor cleanup

---

## Refactoring Principles (TDD)

1. **Test First**: All integration tests must pass before and after refactoring
2. **One at a Time**: Refactor files individually, commit after each
3. **Service Layer Pattern**: Extract business logic to dedicated services
4. **Helper Functions**: Create reusable functions for common operations
5. **Documentation**: Update CHANGELOG.md after each completion

---

## Progress Tracking

### Completed Refactorings (10 files, avg -50% reduction)
- ✅ sessions.py: 1,219 → 424 lines (-65%)
- ✅ ui_client_case_list.py: 962 → 452 lines (-53%)
- ✅ rag_evaluation.py: 703 → 397 lines (-43%)
- ✅ reports.py: 529 → 325 lines (-39%)
- ✅ clients.py: 517 → 197 lines (-62%)
- ✅ cases.py: 352 → 138 lines (-61%)
- ✅ rag_chat.py: 334 → 114 lines (-66%)
- ✅ rag_report.py: 484 → 168 lines (-65%)
- ✅ rag_ingest.py: 410 → 267 lines (-35%)
- ✅ evaluation_service.py: 599 → 394 lines (-34%)

### Remaining (7 files)
- ⏳ sessions.py: 424 lines (need 2nd pass)
- ⏳ ui_client_case_list.py: 452 lines (need 2nd pass)
- ⏳ rag_evaluation.py: 399 lines (need 2nd pass)
- ⏳ reports.py: 328 lines (minor cleanup)
- ⏳ session_service.py: 555 lines
- ⏳ client_case_service.py: 509 lines
- ⏳ rag_report_service.py: 495 lines

---

## Notes

- Some API files were refactored in the first pass but still exceed limits due to complexity
- Second pass refactoring should focus on splitting routers and extracting helpers
- All service files created in first pass are within limits
- Test coverage maintained at 100% pass rate throughout refactoring

---

**Last Updated**: 2025-11-30
**Next Action**: Start Phase 1 refactoring when ready
