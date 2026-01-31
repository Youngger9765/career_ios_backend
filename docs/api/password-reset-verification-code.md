# Password Reset API - Verification Code Flow

## Overview

The Password Reset API provides a secure, email-based password recovery system using 6-digit verification codes instead of URL-based tokens. This approach is more user-friendly, especially for mobile applications.

**Key Features:**
- 6-digit verification codes (instead of long URL tokens)
- 10-minute code expiration
- Rate limiting to prevent abuse
- Account lockout after 5 failed verification attempts
- Email-based delivery with customizable templates
- Multi-tenant support

## Security Features

| Feature | Implementation | Purpose |
|---------|---------------|---------|
| **Rate Limiting** | 5 requests/hour per IP | Prevent brute force attacks |
| **Code Expiration** | 10 minutes | Minimize attack window |
| **Account Lockout** | 15 minutes after 5 failed attempts | Prevent verification code guessing |
| **User Enumeration Protection** | Always return success | Hide whether email exists |
| **IP Tracking** | Log request and usage IP | Audit trail |
| **One-Time Use** | Token marked as used | Prevent replay attacks |

## API Endpoints

### 1. Request Password Reset

**POST** `/api/v1/auth/password-reset/request`

Send a password reset email with a 6-digit verification code.

**Request Body:**
```json
{
  "email": "user@example.com",
  "tenant_id": "test_tenant",
  "source": "app"  // Optional: "app" or "web"
}
```

**Response (200 OK):**
```json
{
  "message": "Password reset email sent successfully",
  "token": "abc123..."  // Only included in development/testing
}
```

**Rate Limit:** 5 requests/hour per IP

**Security Notes:**
- Always returns success (even if email doesn't exist) to prevent user enumeration
- Verification code is only sent to valid email addresses
- Previous unused codes are invalidated when a new request is made

---

### 2. Verify Verification Code

**POST** `/api/v1/auth/password-reset/verify-code`

Verify that a 6-digit code is valid before showing the password reset form.

**Request Body:**
```json
{
  "email": "user@example.com",
  "verification_code": "123456",
  "tenant_id": "test_tenant"
}
```

**Response (200 OK):**
```json
{
  "valid": true,
  "message": "Verification code is valid"
}
```

**Error Responses:**

| Status | Error | Reason |
|--------|-------|--------|
| `400` | `Invalid verification code` | Code doesn't match or doesn't exist |
| `400` | `Verification code has expired` | Code is older than 10 minutes |
| `400` | `Verification code has already been used` | Code was already used to reset password |
| `400` | `Too many failed attempts. Account is temporarily locked.` | 5+ failed attempts in last 15 minutes |

**Behavior:**
- Increments `verify_attempts` counter on failure
- Locks account for 15 minutes after 5 failed attempts
- Does NOT consume the code (can be verified multiple times before confirm)

---

### 3. Confirm Password Reset

**POST** `/api/v1/auth/password-reset/confirm`

Reset the password using the verified code.

**Request Body:**
```json
{
  "email": "user@example.com",
  "verification_code": "123456",
  "new_password": "SecurePassword123!",
  "tenant_id": "test_tenant"
}
```

**Response (200 OK):**
```json
{
  "message": "Password reset successfully"
}
```

**Error Responses:**

| Status | Error | Reason |
|--------|-------|--------|
| `400` | `Invalid verification code` | Code doesn't match or doesn't exist |
| `400` | `Verification code has expired` | Code is older than 10 minutes |
| `400` | `Verification code has already been used` | Code was already used |
| `400` | `Password must be at least 8 characters long` | Password too short |

**Behavior:**
- Marks the token as `used` and records `used_at` timestamp
- Updates the counselor's password hash
- Invalidates all previous reset codes for this email
- User can immediately login with the new password

---

## Client Implementation Examples

### iOS (Swift)

```swift
// Step 1: Request password reset
func requestPasswordReset(email: String, tenantId: String) async throws {
    let url = URL(string: "\(apiBaseURL)/api/v1/auth/password-reset/request")!
    let body = [
        "email": email,
        "tenant_id": tenantId,
        "source": "app"
    ]

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try JSONSerialization.data(withJSONObject: body)

    let (_, response) = try await URLSession.shared.data(for: request)
    guard (response as? HTTPURLResponse)?.statusCode == 200 else {
        throw PasswordResetError.requestFailed
    }

    // Show UI to enter 6-digit code
}

// Step 2: Verify code (optional but recommended)
func verifyCode(email: String, code: String, tenantId: String) async throws -> Bool {
    let url = URL(string: "\(apiBaseURL)/api/v1/auth/password-reset/verify-code")!
    let body = [
        "email": email,
        "verification_code": code,
        "tenant_id": tenantId
    ]

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try JSONSerialization.data(withJSONObject: body)

    let (data, response) = try await URLSession.shared.data(for: request)
    guard (response as? HTTPURLResponse)?.statusCode == 200 else {
        return false
    }

    let result = try JSONDecoder().decode(VerifyCodeResponse.self, from: data)
    return result.valid
}

// Step 3: Confirm password reset
func confirmPasswordReset(email: String, code: String, newPassword: String, tenantId: String) async throws {
    let url = URL(string: "\(apiBaseURL)/api/v1/auth/password-reset/confirm")!
    let body = [
        "email": email,
        "verification_code": code,
        "new_password": newPassword,
        "tenant_id": tenantId
    ]

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try JSONSerialization.data(withJSONObject: body)

    let (_, response) = try await URLSession.shared.data(for: request)
    guard (response as? HTTPURLResponse)?.statusCode == 200 else {
        throw PasswordResetError.confirmFailed
    }

    // Password reset successful, navigate to login
}
```

### Web (JavaScript/TypeScript)

```typescript
// Step 1: Request password reset
async function requestPasswordReset(email: string, tenantId: string): Promise<void> {
  const response = await fetch('/api/v1/auth/password-reset/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      tenant_id: tenantId,
      source: 'web'
    })
  });

  if (!response.ok) {
    throw new Error('Failed to request password reset');
  }

  // Show UI to enter 6-digit code
}

// Step 2: Verify code
async function verifyCode(email: string, code: string, tenantId: string): Promise<boolean> {
  const response = await fetch('/api/v1/auth/password-reset/verify-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      verification_code: code,
      tenant_id: tenantId
    })
  });

  if (!response.ok) {
    return false;
  }

  const data = await response.json();
  return data.valid;
}

// Step 3: Confirm password reset
async function confirmPasswordReset(
  email: string,
  code: string,
  newPassword: string,
  tenantId: string
): Promise<void> {
  const response = await fetch('/api/v1/auth/password-reset/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      verification_code: code,
      new_password: newPassword,
      tenant_id: tenantId
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to reset password');
  }

  // Password reset successful
}
```

---

## Email Template

The system sends HTML emails with the following structure:

**Subject:** `Reset Your Password - {tenant_name}`

**Body:**
```
Hi {counselor_name},

We received a request to reset your password. Use the verification code below to reset your password:

[123456]  <-- Large, prominent display

This code will expire in 10 minutes.

If you didn't request this password reset, you can safely ignore this email.

Need help? Contact our support team.
```

**Template Location:** `app/services/external/email_sender.py`

**Customization:**
- Tenant-specific branding via `tenant_id`
- Source-aware messaging (app vs web)
- Responsive HTML design
- Plain-text fallback

---

## Complete Flow Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ 1. POST /request (email, tenant_id)
       │
       ▼
┌─────────────┐     ┌──────────────┐
│   Backend   │────▶│ Email Server │
└──────┬──────┘     └──────────────┘
       │                    │
       │                    │ Send email with
       │                    │ verification code
       │                    ▼
       │            ┌──────────────┐
       │            │     User     │
       │            └──────┬───────┘
       │                   │
       │ 2. User receives  │
       │    code: 123456   │
       │                   │
       │◀──────────────────┘
       │
       │ 3. POST /verify-code (email, code, tenant_id)
       │
       ▼
┌─────────────┐
│   Backend   │──▶ Valid? ✓
└──────┬──────┘
       │
       │ 4. POST /confirm (email, code, new_password, tenant_id)
       │
       ▼
┌─────────────┐
│   Backend   │──▶ Password Updated ✓
└──────┬──────┘
       │
       │ 5. Success Response
       │
       ▼
┌─────────────┐
│   Client    │──▶ Navigate to Login
└─────────────┘
```

---

## Testing

### Manual Testing

```bash
# 1. Request password reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "tenant_id": "test_tenant"
  }'

# 2. Check email for code (or check database in dev)

# 3. Verify code
curl -X POST http://localhost:8000/api/v1/auth/password-reset/verify-code \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "verification_code": "123456",
    "tenant_id": "test_tenant"
  }'

# 4. Confirm password reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "verification_code": "123456",
    "new_password": "NewPassword123!",
    "tenant_id": "test_tenant"
  }'
```

### Automated Tests

```bash
# Run all password reset verification tests
poetry run pytest tests/integration/test_password_reset_verification.py -v

# Run specific test
poetry run pytest tests/integration/test_password_reset_verification.py::test_verify_code_success -v

# Run end-to-end flow test
poetry run pytest tests/integration/test_password_reset_verification.py::TestPasswordResetEndToEnd -v
```

---

## Migration from Token-based System

If migrating from the old URL token-based system:

### Old Flow (Deprecated)
```
POST /request → Email with URL → GET /verify?token=xxx → POST /confirm
```

### New Flow (Current)
```
POST /request → Email with 6-digit code → POST /verify-code → POST /confirm
```

### Key Changes:
1. **Removed:** `GET /verify` endpoint (token-based)
2. **Added:** `POST /verify-code` endpoint (code-based)
3. **Changed:** `/confirm` now accepts `verification_code` instead of `token`
4. **Backward Compatibility:** Old tokens are still stored but not used

### Database Schema:
```python
class PasswordResetToken:
    token: str  # Legacy field (still generated for backward compatibility)
    verification_code: str  # New 6-digit code
    code_expires_at: datetime  # 10 minutes
    verify_attempts: int  # Failed verification counter
    locked_until: datetime | None  # Lockout timestamp
```

---

## Troubleshooting

### Issue: User doesn't receive email

**Possible Causes:**
1. Email server configuration issue
2. Email in spam folder
3. Invalid email address
4. Rate limit exceeded

**Debug Steps:**
```bash
# Check database for token creation
SELECT * FROM password_reset_tokens
WHERE email = 'user@example.com'
ORDER BY created_at DESC LIMIT 1;

# Check email sender logs
grep "password reset email" /var/log/app.log
```

### Issue: "Verification code has expired"

**Causes:**
- Code is older than 10 minutes
- System time is incorrect

**Solution:**
- Request a new code
- Verify server time is synchronized (NTP)

### Issue: "Account is temporarily locked"

**Causes:**
- 5 failed verification attempts

**Solution:**
- Wait 15 minutes
- Or admin can manually clear lockout:
  ```sql
  UPDATE password_reset_tokens
  SET locked_until = NULL, verify_attempts = 0
  WHERE email = 'user@example.com';
  ```

### Issue: "Invalid verification code" (but code is correct)

**Possible Causes:**
1. Code already used
2. Wrong email/tenant_id combination
3. Code from previous request (invalidated)

**Debug:**
```sql
SELECT
  verification_code,
  used,
  code_expires_at,
  verify_attempts,
  locked_until
FROM password_reset_tokens
WHERE email = 'user@example.com'
ORDER BY created_at DESC LIMIT 1;
```

---

## Security Best Practices

1. **Never log verification codes** in production
2. **Always use HTTPS** in production
3. **Monitor failed attempts** for patterns
4. **Set up alerts** for unusual activity (e.g., 100+ requests/hour)
5. **Regularly clean up** expired tokens (scheduled job)
6. **Implement CAPTCHA** if abuse is detected
7. **Consider SMS backup** for high-security scenarios

---

## Related Documentation

- [Email Configuration Guide](../setup/email-configuration.md)
- [Rate Limiting Strategy](../architecture/rate-limiting.md)
- [Security Audit Logs](../architecture/audit-logs.md)
- [Multi-Tenant Setup](../architecture/multi-tenant.md)

---

**Last Updated:** 2026-02-01
**API Version:** v1
**Status:** Production Ready
