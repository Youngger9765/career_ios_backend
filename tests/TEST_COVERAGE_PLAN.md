# API Test Coverage Plan

## ✅ Completed Tests

### Auth API (`tests/integration/test_auth_api.py`) - 10 tests
- [x] POST /api/auth/login - Success
- [x] POST /api/auth/login - Wrong password
- [x] POST /api/auth/login - Nonexistent user
- [x] POST /api/auth/login - Inactive user
- [x] GET /api/auth/me - Success
- [x] GET /api/auth/me - No token
- [x] GET /api/auth/me - Invalid token
- [x] PATCH /api/auth/me - Success ✅ NEW
- [x] PATCH /api/auth/me - No token ✅ NEW
- [x] PATCH /api/auth/me - Invalid token ✅ NEW

### Clients API (`tests/integration/test_clients_api.py`) - 11 tests ✅ NEW
- [x] POST /api/v1/clients - Create client (success)
- [x] POST /api/v1/clients - Create client (minimal fields)
- [x] POST /api/v1/clients - Unauthorized
- [x] GET /api/v1/clients - List all clients
- [x] GET /api/v1/clients?search=keyword - Search clients
- [x] GET /api/v1/clients/{id} - Get client details
- [x] GET /api/v1/clients/{id} - Not found (404)
- [x] PATCH /api/v1/clients/{id} - Update client
- [x] DELETE /api/v1/clients/{id} - Soft delete client
- [x] DELETE /api/v1/clients/{id} - Not found (404)
- [x] Pagination (skip, limit)

### Cases API (`tests/integration/test_cases_api_integration.py`) - 14 tests ✅ NEW
- [x] POST /api/v1/cases - Create case (success)
- [x] POST /api/v1/cases - Create case (minimal fields)
- [x] POST /api/v1/cases - Unauthorized
- [x] POST /api/v1/cases - Invalid client (404)
- [x] GET /api/v1/cases - List all cases
- [x] GET /api/v1/cases?client_id=xxx - Filter by client
- [x] GET /api/v1/cases/{id} - Get case details
- [x] GET /api/v1/cases/{id} - Not found (404)
- [x] PATCH /api/v1/cases/{id} - Update case
- [x] PATCH /api/v1/cases/{id} - Update status
- [x] DELETE /api/v1/cases/{id} - Soft delete case
- [x] DELETE /api/v1/cases/{id} - Not found (404)
- [x] Pagination (skip, limit)

### Sessions API (`tests/integration/test_sessions_api.py`) - 18 tests ✅ NEW
- [x] POST /api/v1/sessions - Create session (success)
- [x] POST /api/v1/sessions - Create with recordings
- [x] POST /api/v1/sessions - Minimal fields
- [x] POST /api/v1/sessions - Unauthorized
- [x] GET /api/v1/sessions - List all sessions
- [x] GET /api/v1/sessions?client_id=xxx - Filter by client
- [x] GET /api/v1/sessions/{id} - Get session details
- [x] GET /api/v1/sessions/{id} - Not found (404)
- [x] PATCH /api/v1/sessions/{id} - Update session
- [x] DELETE /api/v1/sessions/{id} - Soft delete session
- [x] DELETE /api/v1/sessions/{id} - Not found (404)
- [x] GET /api/v1/sessions/timeline?client_id=xxx - Get timeline
- [x] GET /api/v1/sessions/{id}/reflection - Get reflection
- [x] PUT /api/v1/sessions/{id}/reflection - Update reflection
- [x] Pagination (skip, limit)
- [x] POST /api/v1/sessions/{id}/recordings/append - All scenarios (existing)

### Reports API (`tests/integration/test_reports_api.py`) - 9 tests ✅ NEW
- [x] GET /api/v1/reports - List all reports
- [x] GET /api/v1/reports?session_id=xxx - Filter by session
- [x] GET /api/v1/reports/{id} - Get report details
- [x] GET /api/v1/reports/{id} - Not found (404)
- [x] PATCH /api/v1/reports/{id} - Update report (iOS only)
- [x] PATCH /api/v1/reports/{id} - Not found (404)
- [x] Pagination (skip, limit)
- [x] POST /api/v1/reports/generate - E2E flow (existing)

### Field Schemas API (`tests/integration/test_field_schemas_api.py`) - 4 tests ✅ NEW
- [x] GET /api/v1/field-schemas/client - Success
- [x] GET /api/v1/field-schemas/client - Unauthorized
- [x] GET /api/v1/field-schemas/case - Success
- [x] GET /api/v1/field-schemas/case - Unauthorized

---

## 📊 Test Coverage Summary

### Total Tests Written: **66 tests** ✅

| API Category | Test File | Test Count | Status |
|-------------|-----------|------------|--------|
| Auth | `test_auth_api.py` | 10 | ✅ Complete |
| Clients | `test_clients_api.py` | 11 | ✅ Complete |
| Cases | `test_cases_api_integration.py` | 14 | ✅ Complete |
| Sessions | `test_sessions_api.py` | 18 | ✅ Complete |
| Reports | `test_reports_api.py` | 9 | ✅ Complete |
| Field Schemas | `test_field_schemas_api.py` | 4 | ✅ Complete |

### Coverage by HTTP Method

- **GET**: 24 tests (list, detail, search, filter)
- **POST**: 14 tests (create operations)
- **PATCH/PUT**: 11 tests (update operations)
- **DELETE**: 7 tests (soft delete operations)
- **Error Cases**: 10 tests (404, 401, 403)

## 📋 TDD Workflow (Per Endpoint)

```
1. Write test (RED) ❌
   - Define expected behavior
   - Test happy path + edge cases

2. Run test → Should FAIL

3. Write/fix implementation (GREEN) ✅
   - Minimal code to pass test

4. Run test → Should PASS

5. Refactor ♻️
   - Improve code quality
   - Tests still GREEN

6. Commit 🚀
```

---

## 🧪 Test File Structure

```
tests/integration/
├── test_auth_api.py          ✅ Exists
├── test_clients_api.py        ❌ TODO
├── test_cases_api_integration.py ❌ TODO
├── test_sessions_api.py       ❌ TODO
├── test_reports_api.py        ❌ TODO
├── test_field_schemas_api.py  ❌ TODO
└── test_session_append_recording_api.py ✅ Exists
```

---

## 📊 Coverage Target

- **Minimum**: 80% code coverage
- **Goal**: 90%+ for API endpoints
- **Critical paths**: 100% (auth, CRUD operations)
