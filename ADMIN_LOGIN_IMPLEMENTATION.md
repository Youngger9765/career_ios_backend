# Admin Portal Login Authentication Implementation

## Overview

Implemented a complete login authentication system for the Admin Portal with the following features:

- Beautiful login page with tenant selection
- Token-based authentication using JWT
- Automatic logout on token expiration (401 errors)
- Debug mode support for development
- Secure password input
- Error message display
- Session persistence using localStorage

## Implementation Details

### 1. Login Page UI (`/admin`)

**Location**: `/Users/young/project/career_ios_backend/app/templates/admin.html`

**Features**:
- Clean, modern login card design matching admin portal aesthetics
- Tenant selection dropdown (Career, Island, Island Parents)
- Email and password input fields
- Form validation (required fields, email format)
- Error message display area
- "Skip Login (Debug Mode)" button (only shown when DEBUG=true)

**Visual Design**:
- Gradient header matching admin portal theme
- Responsive layout (centered card)
- Smooth animations (fadeIn)
- Focus states with visual feedback
- Error messages in red with border

### 2. Authentication Flow

**On Page Load**:
1. Check if token exists in localStorage (`admin_token`)
2. If no token and not DEBUG mode → show login page
3. If token exists → verify with `/api/auth/me`
4. If verification fails (401) → auto logout and show login page
5. If verification succeeds → load admin portal

**Login Process**:
1. User enters email, password, and selects tenant
2. POST request to `/api/auth/login`
3. On success:
   - Store `access_token` in localStorage as `admin_token`
   - Store `tenant_id` in localStorage as `admin_tenant`
   - Hide login page, show admin portal
   - Call `checkAuth()` to load user info
4. On failure:
   - Display error message in red box
   - Keep login form visible

**Logout Process**:
1. User clicks "Logout" button in header
2. Clear `admin_token` and `admin_tenant` from localStorage
3. Reset token and currentUser variables
4. Show login page

**Token Expiration Handling**:
- All API calls use `fetchWithAuth()` helper
- Automatically detects 401 responses
- Triggers logout and redirects to login page
- Prevents infinite loops and handles errors gracefully

### 3. Token Management

**Storage**:
- Token stored in `localStorage.admin_token`
- Tenant stored in `localStorage.admin_tenant`
- Persists across browser sessions

**Security**:
- Password input uses `type="password"`
- Token sent via `Authorization: Bearer {token}` header
- Automatic cleanup on logout
- No sensitive data in error messages

**Session Management**:
- Token validated on page load
- Automatic logout on 401 errors
- User info fetched from `/api/auth/me`
- Tenant selector updates from authenticated user's tenant

### 4. API Integration

**Endpoints Used**:
- `POST /api/auth/login` - Login with email/password/tenant_id
- `GET /api/auth/me` - Get current user info and verify token

**Request Format**:
```json
{
  "email": "admin@example.com",
  "password": "password123",
  "tenant_id": "career"
}
```

**Response Format**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**fetchWithAuth() Helper**:
```javascript
async function fetchWithAuth(url, options = {}) {
    const headers = options.headers || {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    options.headers = headers;

    const res = await fetch(url, options);

    if (res.status === 401 && token) {
        handleLogout();
        throw new Error('Session expired');
    }

    return res;
}
```

### 5. Debug Mode Support

**Configuration**:
- Controlled by `settings.DEBUG` in FastAPI
- Passed to template as `debug_mode` variable
- JavaScript variable: `DEBUG_MODE = {{ 'true' if debug_mode else 'false' }}`

**Debug Features**:
- "Skip Login (Debug Mode)" button visible only when DEBUG=true
- Allows testing without authentication
- Shows "Admin (Debug Mode)" in header
- All API calls still work without token (for development)

**Production Behavior**:
- When DEBUG=false, debug button hidden
- Login required to access admin portal
- Token verification enforced

### 6. Updated Files

**Modified**:
1. `/Users/young/project/career_ios_backend/app/templates/admin.html`
   - Added login page HTML and CSS
   - Updated authentication logic
   - Added `fetchWithAuth()` helper
   - Updated all API calls to use token
   - Added automatic logout on 401

2. `/Users/young/project/career_ios_backend/app/main.py`
   - Updated `/admin` route to pass `debug_mode` to template

**No New Files Created** (all changes integrated into existing files)

## Usage Instructions

### For Development (DEBUG=true)

1. Visit `http://localhost:8000/admin`
2. Either:
   - Click "Skip Login (Debug Mode)" to bypass authentication
   - Or enter valid credentials and login normally

### For Production (DEBUG=false)

1. Visit admin portal URL
2. See login page automatically
3. Select tenant from dropdown
4. Enter email and password
5. Click "Login" button
6. On success → redirected to admin portal
7. On failure → error message shown

### Testing Login

**Create Test User** (if not exists):
```python
# Run in Python/iPython or create via register API
from app.core.database import SessionLocal
from app.models.counselor import Counselor, CounselorRole
from app.core.security import hash_password

db = SessionLocal()
counselor = Counselor(
    email="admin@career.com",
    username="admin",
    full_name="Admin User",
    hashed_password=hash_password("admin123"),
    tenant_id="career",
    role=CounselorRole.ADMIN,
    is_active=True
)
db.add(counselor)
db.commit()
db.close()
```

**Test Login**:
- Email: `admin@career.com`
- Password: `admin123`
- Tenant: `career`

### Logout

- Click "Logout" button in header
- Automatically redirected to login page
- Token cleared from localStorage

## Security Features

1. **Password Protection**:
   - Input type="password" hides password
   - No password stored in localStorage
   - Only JWT token stored

2. **Token Expiration**:
   - Automatic detection of expired tokens
   - 401 responses trigger logout
   - No manual refresh needed

3. **CSRF Protection**:
   - Tokens sent via Authorization header
   - Not vulnerable to CSRF attacks

4. **Error Handling**:
   - Generic error messages (no info leakage)
   - Network errors handled gracefully
   - No stack traces shown to users

5. **Session Isolation**:
   - Different storage keys (`admin_token` vs `token`)
   - Prevents conflicts with other apps
   - Tenant stored separately

## API Call Updates

All API functions updated to use `fetchWithAuth()`:

- `loadMembers()` - List counselors
- `createCounselor()` - Create new counselor
- `updateCounselor()` - Update counselor info
- `confirmDelete()` - Delete counselor
- `submitChangePassword()` - Change password
- `showCreditDetails()` - Load credit info
- `submitAddCredit()` - Add credits
- `addCredits()` - Legacy credit function

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires JavaScript enabled
- Requires localStorage support
- Responsive design (mobile-friendly)

## Future Enhancements

Possible improvements for production:

1. **Remember Me**:
   - Checkbox to persist login longer
   - Extended token expiration

2. **Password Reset**:
   - "Forgot Password" link
   - Email-based reset flow

3. **Multi-Factor Authentication**:
   - SMS or authenticator app
   - Enhanced security for admin access

4. **Session Timeout Warning**:
   - Show warning before token expires
   - Option to refresh token

5. **Login Attempt Tracking**:
   - Rate limiting
   - Lockout after failed attempts
   - IP-based restrictions

6. **Audit Logging**:
   - Log all login attempts
   - Track admin actions
   - Security monitoring

## Troubleshooting

**Issue**: Login page not showing
- **Solution**: Check if token exists in localStorage, clear it manually

**Issue**: "Session expired" immediately after login
- **Solution**: Check server time vs client time, verify token not expired

**Issue**: 401 error loop
- **Solution**: Clear localStorage, refresh page, check API server status

**Issue**: "Skip Debug" button not showing
- **Solution**: Verify DEBUG=true in settings, check template rendering

**Issue**: Token not included in API calls
- **Solution**: Verify `fetchWithAuth()` used, check localStorage has token

## Testing Checklist

- [ ] Login page displays on first visit (no token)
- [ ] Valid credentials login successfully
- [ ] Invalid credentials show error message
- [ ] Token stored in localStorage after login
- [ ] Admin portal loads after successful login
- [ ] User info shown in header (name/email)
- [ ] Tenant selector matches logged-in tenant
- [ ] Logout button clears token and shows login page
- [ ] 401 errors trigger automatic logout
- [ ] Debug mode shows "Skip Login" button
- [ ] Skip Login works in debug mode
- [ ] All admin functions work with token
- [ ] Token expiration redirects to login
- [ ] Error messages display correctly
- [ ] Mobile responsive design works

## Summary

Successfully implemented a complete login authentication system for the Admin Portal with:

- Beautiful, user-friendly login interface
- Secure token-based authentication
- Automatic token expiration handling
- Debug mode for development
- Seamless integration with existing admin portal
- All API calls updated to use authentication
- Production-ready security features

The implementation maintains the existing admin portal functionality while adding robust authentication and session management.
