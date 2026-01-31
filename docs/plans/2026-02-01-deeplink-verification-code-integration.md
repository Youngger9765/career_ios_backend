# Deeplink Integration for Verification Code Password Reset

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate deeplink redirect with the new verification code password reset flow, ensuring users are redirected back to the app after successful password reset when initiated from in-app browser.

**Architecture:** The existing deeplink mechanism in `reset_password.html` already works for token-based reset. We need to ensure it continues working when the password reset flow transitions to verification code. The deeplink triggers on successful password confirmation, redirecting to `islandparent://auth/forgot-password-done` with 3-second fallback to web.

**Tech Stack:** HTML/JavaScript (browser), deeplink protocol (iOS), FastAPI (backend)

**Dependencies:**
- Verification code implementation must be complete first (`docs/plans/2026-01-31-password-reset-verification-code.md`)
- Current deeplink implementation in `app/templates/reset_password.html` (Line 441-472)

---

## Current State Analysis

**Existing Deeplink Implementation:**
- Location: `app/templates/reset_password.html` Line 441-472
- Trigger: After successful password reset (`response.ok` in Line 392)
- Mechanism:
  - Reads `?source=app` URL parameter
  - Executes `window.location.href = 'islandparent://auth/forgot-password-done'`
  - 3-second fallback to `/island-parents` if app doesn't catch deeplink

**What's Changing:**
- Password reset API endpoint changes from token-based to verification code-based
- API call changes from `/api/v1/auth/password-reset/confirm` with `token` to same endpoint with `verification_code`
- HTML form changes from auto-filled token input to manual 6-digit code input

**What Stays the Same:**
- Deeplink trigger point (after successful API response)
- Deeplink URL (`islandparent://auth/forgot-password-done`)
- Fallback mechanism
- Source parameter handling

---

## Task 1: Verify Current Deeplink Still Works

**Goal:** Confirm existing deeplink implementation will work with verification code flow without modification.

**Files:**
- Read: `app/templates/reset_password.html:392-472`

**Step 1: Analyze API response handling**

Current code (Line 392-398):
```javascript
if (response.ok) {
    // Hide form and show success state
    form.style.display = 'none';
    successState.style.display = 'block';

    // Handle deeplink redirect based on source parameter
    handleSuccessRedirect();
}
```

**Analysis:**
- ✅ Deeplink triggers on `response.ok` (HTTP 200)
- ✅ Not dependent on response body structure
- ✅ Works with any successful password reset

**Step 2: Verify source parameter flow**

Current flow:
1. App opens URL with `?source=app`
2. JavaScript reads `urlParams.get('source')` (Line 444)
3. If source === 'app', triggers deeplink (Line 446-464)

**Analysis:**
- ✅ Source parameter independent of token vs code
- ✅ Will work with verification code flow

**Step 3: Document conclusion**

Write to plan:
```
CONCLUSION: Existing deeplink implementation is API-agnostic.
It only depends on:
1. HTTP 200 response from password reset confirm endpoint
2. ?source=app URL parameter

Both will be preserved in verification code implementation.
NO CHANGES NEEDED to deeplink code.
```

**Step 4: Commit analysis**

```bash
git add docs/plans/2026-02-01-deeplink-verification-code-integration.md
git commit -m "docs: analyze deeplink compatibility with verification code"
```

---

## Task 2: Update HTML Form for Verification Code Input

**Goal:** Modify `reset_password.html` to accept 6-digit verification code instead of token.

**Files:**
- Modify: `app/templates/reset_password.html:194-206`

**Step 2.1: Update token input field to verification code**

Replace token input section (Line 194-206) with:

```html
<!-- Verification Code Input -->
<div class="mb-4">
    <label for="verificationCode" class="block text-gray-700 font-semibold mb-2 text-sm md:text-base">驗證碼</label>
    <input
        type="text"
        id="verificationCode"
        name="verificationCode"
        class="input-field font-mono text-xl tracking-widest text-center"
        placeholder="000000"
        maxlength="6"
        pattern="[0-9]{6}"
        inputmode="numeric"
        required
        autocomplete="off"
    >
    <p class="text-xs text-gray-500 mt-1">請輸入收到的 6 位數驗證碼</p>
</div>
```

**Changes:**
- Changed `id` and `name` from "token" to "verificationCode"
- Added `maxlength="6"` for 6-digit limit
- Added `pattern="[0-9]{6}"` for numeric validation
- Changed `inputmode="numeric"` for mobile keyboard
- Styled with `text-xl tracking-widest text-center` for better UX
- Updated placeholder and help text

**Step 2.2: Remove auto-fill token logic**

Delete or comment out (Line 283-288):

```javascript
// Auto-fill token from URL query parameter
const urlParams = new URLSearchParams(window.location.search);
const tokenFromUrl = urlParams.get('token');
if (tokenFromUrl) {
    document.getElementById('token').value = tokenFromUrl;
    showAlert('重置代碼已自動填入', 'info');
}
```

Replace with:

```javascript
// Note: Verification code is NOT auto-filled from URL
// User must manually enter the 6-digit code from their email
const urlParams = new URLSearchParams(window.location.search);
const sourceParam = urlParams.get('source'); // Preserve for deeplink
```

**Reason:** Verification codes should not be in URL (security risk).

**Step 2.3: Commit**

```bash
git add app/templates/reset_password.html
git commit -m "feat: update reset password form for 6-digit verification code input"
```

---

## Task 3: Update JavaScript API Call to Use Verification Code

**Goal:** Modify form submission to send `verification_code` instead of `token`.

**Files:**
- Modify: `app/templates/reset_password.html:346-390`

**Step 3.1: Update form value extraction**

Replace (Line 353-355):

```javascript
// Get form values
const token = document.getElementById('token').value.trim();
const newPassword = newPasswordInput.value;
const confirmPassword = document.getElementById('confirmPassword').value;
```

With:

```javascript
// Get form values
const verificationCode = document.getElementById('verificationCode').value.trim();
const newPassword = newPasswordInput.value;
const confirmPassword = document.getElementById('confirmPassword').value;
```

**Step 3.2: Update validation**

Replace (Line 358-361):

```javascript
if (!token) {
    showAlert('請輸入重置代碼', 'error');
    return;
}
```

With:

```javascript
if (!verificationCode) {
    showAlert('請輸入驗證碼', 'error');
    return;
}

// Validate verification code format
if (!/^\d{6}$/.test(verificationCode)) {
    showAlert('驗證碼必須是 6 位數字', 'error');
    return;
}
```

**Step 3.3: Update API request body**

Replace (Line 384-387):

```javascript
body: JSON.stringify({
    token: token,
    new_password: newPassword
})
```

With:

```javascript
body: JSON.stringify({
    email: emailFromUrl, // Will add email extraction in next step
    verification_code: verificationCode,
    new_password: newPassword,
    tenant_id: 'island_parents' // Will make dynamic later
})
```

**Step 3.4: Add email extraction from URL**

Add after line 289 (after urlParams definition):

```javascript
// Extract email from URL (will be passed by app)
const emailFromUrl = urlParams.get('email') || '';
if (!emailFromUrl) {
    showAlert('缺少 email 參數', 'error');
}
```

**Step 3.5: Commit**

```bash
git add app/templates/reset_password.html
git commit -m "feat: update password reset API call to use verification code"
```

---

## Task 4: Ensure Deeplink Triggers After Verification Code Success

**Goal:** Verify deeplink still triggers correctly with new API structure.

**Files:**
- Read: `app/templates/reset_password.html:392-398`
- Test: Manual testing required

**Step 4.1: Review success handling code**

Current code (Line 392-398):
```javascript
if (response.ok) {
    // Hide form and show success state
    form.style.display = 'none';
    successState.style.display = 'block';

    // Handle deeplink redirect based on source parameter
    handleSuccessRedirect();
}
```

**Verification:**
- ✅ Only depends on `response.ok` (HTTP 200)
- ✅ Calls `handleSuccessRedirect()` which reads `source` parameter
- ✅ No dependency on API response structure

**Step 4.2: Document test plan**

Create test checklist:

```markdown
## Manual Testing Checklist

### Setup
1. Backend verification code API is deployed
2. iOS app configured to open in-app browser with:
   - URL: `/island-parents/reset-password?source=app&email=test@example.com`

### Test Cases

**TC1: Happy Path - App Source**
1. Open in-app browser from iOS app
2. Verify URL contains `?source=app&email=xxx`
3. Enter 6-digit verification code from email
4. Enter new password
5. Click submit
6. ✅ Should redirect to `islandparent://auth/forgot-password-done`
7. ✅ App should close browser and show success

**TC2: Deeplink Fallback - App Not Installed**
1. Open in mobile Safari (not in app)
2. Add `?source=app` manually to URL
3. Complete reset flow
4. ✅ Should show "App 未開啟，返回登入頁面..."
5. ✅ After 1.5s, redirect to `/island-parents`

**TC3: Web Source - No Deeplink**
1. Open without `?source=app` parameter
2. Complete reset flow
3. ✅ Should show "返回登入頁面..."
4. ✅ Redirect to `/island-parents` (no deeplink attempt)

**TC4: Invalid Verification Code**
1. Enter wrong 6-digit code
2. ✅ Should show error message
3. ✅ Should NOT trigger deeplink
4. ✅ Form stays visible

**TC5: Expired Verification Code**
1. Use code older than 15 minutes
2. ✅ Should show "驗證碼已過期"
3. ✅ Should NOT trigger deeplink
```

**Step 4.3: Commit test plan**

```bash
git add docs/plans/2026-02-01-deeplink-verification-code-integration.md
git commit -m "docs: add manual testing checklist for deeplink integration"
```

---

## Task 5: Add Email Parameter to Reset Password URL

**Goal:** Ensure reset password page receives email via URL parameter for API calls.

**Files:**
- Modify: `app/services/external/email_sender.py` (after verification code changes)

**Note:** This task assumes the verification code implementation has updated the email service.

**Step 5.1: Check current email template**

After verification code implementation, email should contain:
- 6-digit verification code (in email body)
- NO link (just the code)

**Step 5.2: Add instruction in email**

Update email template to include:

```html
<p>請回到 App 中輸入此驗證碼以完成密碼重設。</p>
```

**Step 5.3: Document URL format for app**

Add to email documentation:

```markdown
## App Integration

When user initiates password reset from app, the app should:

1. Call `/api/v1/auth/password-reset/request` with user's email
2. Open in-app browser to:
   ```
   /island-parents/reset-password?source=app&email={user_email}
   ```
3. User receives email with 6-digit code
4. User returns to in-app browser (still open)
5. User enters code and new password
6. On success, browser closes via deeplink

**URL Parameters:**
- `source=app` - Triggers deeplink redirect after success
- `email={email}` - Pre-fills user's email for API call
```

**Step 5.4: Commit**

```bash
git add app/services/external/email_sender.py docs/
git commit -m "docs: add app integration instructions for verification code flow"
```

---

## Task 6: Handle Edge Cases

**Goal:** Add error handling for edge cases in deeplink flow.

**Files:**
- Modify: `app/templates/reset_password.html`

**Step 6.1: Add email parameter validation**

Update email extraction (from Task 3):

```javascript
// Extract and validate email from URL
const urlParams = new URLSearchParams(window.location.search);
const emailFromUrl = urlParams.get('email');
const sourceParam = urlParams.get('source');

// Validate email if present
if (sourceParam === 'app' && !emailFromUrl) {
    showAlert('錯誤：缺少 email 參數。請重新從 App 開啟此頁面。', 'error');
    document.getElementById('resetPasswordForm').style.display = 'none';
}

// Basic email validation
if (emailFromUrl && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailFromUrl)) {
    showAlert('錯誤：email 格式不正確', 'error');
}
```

**Step 6.2: Add network timeout for deeplink**

Update `handleSuccessRedirect()` to handle stuck states:

```javascript
function handleSuccessRedirect() {
    const urlParams = new URLSearchParams(window.location.search);
    const source = urlParams.get('source');

    if (source === 'app') {
        const deeplinkUrl = 'islandparent://auth/forgot-password-done';
        document.getElementById('successMessage').textContent = '正在跳轉到 App...';

        // Trigger deeplink
        window.location.href = deeplinkUrl;

        // Fallback mechanism with timeout
        let fallbackTriggered = false;

        const fallbackTimer = setTimeout(() => {
            if (!fallbackTriggered && document.visibilityState === 'visible') {
                fallbackTriggered = true;
                console.log('Deeplink not handled by app, falling back to web redirect');
                document.getElementById('successMessage').textContent = 'App 未開啟，返回登入頁面...';
                setTimeout(() => {
                    window.location.href = '/island-parents';
                }, 1500);
            }
        }, 3000);

        // Clear timer if page becomes hidden (app opened)
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                clearTimeout(fallbackTimer);
            }
        });
    } else {
        // Web source or no source - redirect to login page
        document.getElementById('successMessage').textContent = '返回登入頁面...';
        setTimeout(() => {
            window.location.href = '/island-parents';
        }, 1500);
    }
}
```

**Step 6.3: Commit**

```bash
git add app/templates/reset_password.html
git commit -m "feat: add edge case handling for deeplink and email validation"
```

---

## Task 7: Update Documentation

**Goal:** Document the complete verification code + deeplink flow for iOS team.

**Files:**
- Create: `docs/api/password-reset-deeplink-flow.md`

**Step 7.1: Write flow documentation**

Create `docs/api/password-reset-deeplink-flow.md`:

```markdown
# Password Reset with Verification Code + Deeplink Flow

## Overview

The password reset flow for iOS app uses verification codes sent via email, with in-app browser for password entry and deeplink redirect back to app.

## Complete Flow

### 1. User Initiates Reset

**Location:** iOS App - Forgot Password Screen

**Actions:**
1. User taps "Forgot Password"
2. User enters email address
3. App calls API:

```http
POST /api/v1/auth/password-reset/request
Content-Type: application/json

{
  "email": "user@example.com",
  "tenant_id": "island_parents",
  "source": "app"
}
```

4. App shows "驗證碼已發送到您的信箱"

### 2. App Opens In-App Browser

**URL Format:**
```
https://career-app-api-staging-xxx.run.app/island-parents/reset-password?source=app&email={user_email}
```

**URL Parameters:**
- `source=app` - Required for deeplink redirect
- `email={email}` - User's email for API calls

**Why in-app browser?**
- User can see form while checking email
- Seamless transition back to app via deeplink

### 3. User Receives Email

**Email contains:**
- 6-digit verification code (e.g., 485921)
- Expiry time (15 minutes)
- Instructions to return to app

**Email does NOT contain:**
- Clickable links (no token-based links)

### 4. User Completes Reset in Browser

**In-app browser shows:**
1. Verification code input (6 digits)
2. New password input
3. Confirm password input

**User actions:**
1. Switch to email app
2. Copy 6-digit code
3. Return to in-app browser
4. Paste code
5. Enter new password
6. Submit

**API call:**
```http
POST /api/v1/auth/password-reset/confirm
Content-Type: application/json

{
  "email": "user@example.com",
  "verification_code": "485921",
  "new_password": "NewPassword123",
  "tenant_id": "island_parents"
}
```

### 5. Deeplink Redirect

**On success (HTTP 200):**

Browser executes:
```javascript
window.location.href = 'islandparent://auth/forgot-password-done';
```

**iOS app handles:**
```swift
// AppDelegate or SceneDelegate
func application(_ app: UIApplication,
                open url: URL,
                options: [UIApplication.OpenURLOptionsKey : Any]) -> Bool {

    if url.scheme == "islandparent" && url.host == "auth" {
        if url.path == "/forgot-password-done" {
            // Close in-app browser
            dismiss(animated: true) {
                // Show success message
                self.showAlert("密碼重設成功", "請使用新密碼登入")
            }
            return true
        }
    }
    return false
}
```

### 6. Fallback Mechanism

**If app doesn't open within 3 seconds:**

Browser shows: "App 未開啟，返回登入頁面..."

Then redirects to: `/island-parents` (login page)

**This handles:**
- App was force-closed
- Deeplink handler failed
- Testing in Safari (not in app)

## Error Scenarios

### Invalid Verification Code
- HTTP 400
- Error: "Invalid verification code. X attempts remaining."
- After 5 attempts: HTTP 429 (locked for 15 minutes)

### Expired Code
- HTTP 400
- Error: "Verification code has expired. Please request a new one."
- User must restart from Step 1

### Network Error
- Browser shows: "網路錯誤，請檢查您的連線"
- User can retry

### Missing Parameters
- If `email` missing and `source=app`: Show error, disable form
- If `source` missing: No deeplink, normal web flow

## iOS Integration Checklist

- [ ] Register URL scheme `islandparent://` in Info.plist
- [ ] Implement deeplink handler for `auth/forgot-password-done`
- [ ] In-app browser preserves state when backgrounded
- [ ] Handle case where browser is manually closed
- [ ] Test fallback mechanism (Safari, not in app)
- [ ] Show success message after deeplink
- [ ] Clear any password reset state in app

## Testing

See `docs/plans/2026-02-01-deeplink-verification-code-integration.md` for complete test cases.

## Security Notes

1. **Verification code never in URL** - Prevents leakage via browser history
2. **15-minute expiry** - Reduces brute force window
3. **5-attempt limit** - Locks account after failed attempts
4. **One-time use** - Code invalidated after successful reset
5. **Source validation** - Email parameter validated server-side

## Backend Endpoints

```
POST /api/v1/auth/password-reset/request
POST /api/v1/auth/password-reset/verify-code (optional)
POST /api/v1/auth/password-reset/confirm
```

See `docs/api/password-reset-verification-code.md` for API specs.
```

**Step 7.2: Commit**

```bash
git add docs/api/password-reset-deeplink-flow.md
git commit -m "docs: add complete password reset + deeplink flow documentation"
```

---

## Task 8: Update iOS Integration Guide

**Goal:** Update existing iOS guide with verification code flow.

**Files:**
- Modify: `IOS_API_GUIDE.md` or `IOS_GUIDE_PARENTS.md`

**Step 8.1: Add section on password reset**

Add to authentication section:

```markdown
### Password Reset (Verification Code Flow)

**New in v2.0:** Password reset now uses 6-digit verification codes instead of email links.

#### Step 1: Request Reset

```swift
func requestPasswordReset(email: String) async throws {
    let url = URL(string: "\(baseURL)/api/v1/auth/password-reset/request")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")

    let body: [String: Any] = [
        "email": email,
        "tenant_id": "island_parents",
        "source": "app"
    ]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)

    let (data, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw APIError.requestFailed
    }
}
```

#### Step 2: Open In-App Browser

```swift
import SafariServices

func openPasswordResetPage(email: String) {
    let urlString = "\(baseURL)/island-parents/reset-password?source=app&email=\(email)"
    guard let url = URL(string: urlString) else { return }

    let safari = SFSafariViewController(url: url)
    safari.dismissButtonStyle = .close
    present(safari, animated: true)
}
```

#### Step 3: Handle Deeplink

Register URL scheme in `Info.plist`:

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>islandparent</string>
        </array>
        <key>CFBundleURLName</key>
        <string>com.yourcompany.islandparents</string>
    </dict>
</array>
```

Handle deeplink in AppDelegate:

```swift
func application(_ app: UIApplication,
                open url: URL,
                options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {

    guard url.scheme == "islandparent",
          url.host == "auth",
          url.path == "/forgot-password-done" else {
        return false
    }

    // Close Safari view controller
    presentedViewController?.dismiss(animated: true) {
        // Show success
        DispatchQueue.main.async {
            let alert = UIAlertController(
                title: "密碼重設成功",
                message: "請使用新密碼登入",
                preferredStyle: .alert
            )
            alert.addAction(UIAlertAction(title: "確定", style: .default))

            UIApplication.shared.windows.first?.rootViewController?
                .present(alert, animated: true)
        }
    }

    return true
}
```

#### Complete Flow Example

```swift
class ForgotPasswordViewController: UIViewController {

    @IBAction func resetPasswordTapped() {
        guard let email = emailTextField.text, !email.isEmpty else {
            showError("請輸入 email")
            return
        }

        Task {
            do {
                // Step 1: Request reset
                try await requestPasswordReset(email: email)

                // Step 2: Show success message
                showSuccess("驗證碼已發送到 \(email)")

                // Step 3: Open in-app browser
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                    self.openPasswordResetPage(email: email)
                }

            } catch {
                showError("發送失敗：\(error.localizedDescription)")
            }
        }
    }
}
```

**User Journey:**
1. User enters email → Taps "重設密碼"
2. App calls API → Shows "驗證碼已發送"
3. App opens in-app browser
4. User checks email → Gets 6-digit code
5. User enters code in browser → Enters new password → Submits
6. Browser redirects via deeplink → App closes browser → Shows success
```

**Step 8.2: Commit**

```bash
git add IOS_API_GUIDE.md
git commit -m "docs: add verification code password reset guide for iOS"
```

---

## Task 9: Final Integration Test

**Goal:** End-to-end test of verification code + deeplink flow.

**Prerequisites:**
- Verification code backend implementation complete
- Frontend changes committed
- Documentation updated

**Step 9.1: Setup test environment**

1. Deploy backend to staging
2. Ensure email service configured
3. Test user account ready

**Step 9.2: Execute test flow**

Follow manual test checklist from Task 4.

**Step 9.3: Document test results**

Create test report:

```markdown
# Password Reset Verification Code + Deeplink Test Report

**Date:** 2026-02-01
**Tester:** [Name]
**Environment:** Staging

## Test Results

| Test Case | Status | Notes |
|-----------|--------|-------|
| TC1: Happy Path | ✅ PASS | Deeplink worked, app closed browser |
| TC2: Fallback | ✅ PASS | Showed fallback message after 3s |
| TC3: Web Source | ✅ PASS | No deeplink, normal redirect |
| TC4: Invalid Code | ✅ PASS | Error shown, no deeplink |
| TC5: Expired Code | ✅ PASS | Expiry message shown |

## Issues Found

[None / List any issues]

## Screenshots

[Attach screenshots of each test case]
```

**Step 9.4: Commit test report**

```bash
git add docs/testing/password-reset-deeplink-test-report.md
git commit -m "test: add password reset deeplink integration test report"
```

---

## Summary

**Total Tasks:** 9
**Estimated Time:** 3-4 hours (assuming verification code backend is complete)
**Complexity:** Medium

**Dependencies:**
- ✅ Verification code backend (separate plan)
- ✅ iOS URL scheme registration
- ✅ Email service configured

**Key Changes:**
- ✅ Updated HTML form for 6-digit code input
- ✅ Modified API calls to use verification_code
- ✅ Preserved existing deeplink mechanism (no changes needed!)
- ✅ Added edge case handling
- ✅ Complete documentation for iOS team

**What Doesn't Change:**
- Deeplink URL (`islandparent://auth/forgot-password-done`)
- Fallback mechanism (3-second timeout)
- Source parameter handling

**Next Steps:**
1. Wait for verification code backend to complete
2. Deploy frontend changes
3. iOS team implements in-app browser + deeplink handler
4. End-to-end testing

---

## Rollback Plan

If deeplink breaks:

1. Check browser console for errors
2. Verify `?source=app` parameter present
3. Test in Safari (should fallback to web redirect)
4. Verify iOS URL scheme registered correctly
5. Check `handleSuccessRedirect()` function (Line 441-472)

Quick fix: Remove `?source=app` parameter to disable deeplink temporarily.

---

**Plan Version:** 1.0
**Created:** 2026-02-01
**Author:** Claude (Sonnet 4.5)
**Dependencies:** `docs/plans/2026-01-31-password-reset-verification-code.md`
