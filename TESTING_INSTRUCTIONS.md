# Testing Instructions - Admin Portal Fix

## Quick Test (2 minutes)

### 1. Start the server
```bash
# Make sure DEBUG=True in .env
poetry run uvicorn app.main:app --reload
```

### 2. Open Admin Portal
```
http://localhost:8000/admin
```

### 3. Test Create Counselor

Fill in the form:
- **Email**: `test1@example.com`
- **Username**: `testuser1`
- **Full Name**: `Test User One`
- **Phone**: `0912345678`
- **Tenant**: `career` (or any option)
- **Role**: `counselor`

Click **"建立會員"** (Create Member)

### Expected Results

**Success Case:**
```
✅ 建立成功！

臨時密碼: [random password shown]

請記下此密碼，稍後無法再次查看。
```

**Failure Cases (Improved Error Messages):**

1. **Duplicate Username:**
   ```
   ❌ 建立失敗

   錯誤代碼: 400
   詳細訊息:
   Username 'testuser1' already exists
   ```

2. **Duplicate Email in Same Tenant:**
   ```
   ❌ 建立失敗

   錯誤代碼: 400
   詳細訊息:
   Email 'test1@example.com' already exists in your tenant
   ```

3. **Validation Error (if you try invalid data):**
   ```
   ❌ 建立失敗

   錯誤代碼: 422
   詳細訊息:
   body.email: Invalid email format
   ```

### 4. Verify in Browser Console

Open Developer Tools (F12) → Console Tab

You should see:
```
Creating counselor with data: {email: "test1@example.com", ...}
Response status: 200
Success response: {counselor: {...}, temporary_password: "..."}
```

Or on error:
```
Response status: 400
Error response: {detail: "Username 'testuser1' already exists"}
```

## What Changed?

### Before (Broken UX)
```
❌ 建立失敗

錯誤代碼: 400
詳細訊息: [object Object]  ← Useless!
```

### After (Fixed UX)
```
❌ 建立失敗

錯誤代碼: 400
詳細訊息:
Username 'testuser1' already exists  ← Clear message!
```

## Testing Different Scenarios

### Scenario 1: Successful Creation
```
Email: unique@test.com
Username: uniqueuser
Full Name: Unique User
Phone: 0912345678
```
**Expected**: Success with temporary password

### Scenario 2: Duplicate Username
1. Create user with username `duplicate`
2. Try to create another user with same username `duplicate`
**Expected**: Error message about duplicate username

### Scenario 3: Duplicate Email in Same Tenant
1. Create user with email `same@test.com` in tenant `career`
2. Try to create another user with same email `same@test.com` in tenant `career`
**Expected**: Error message about duplicate email

### Scenario 4: Same Email in Different Tenant (Should Work)
1. Admin for `career` creates user with email `multi@test.com`
2. Admin for `island` creates user with same email `multi@test.com`
**Expected**: Both should succeed (multi-tenant isolation)
**Note**: In DEBUG mode, mock admin is always `career`, so can't test this yet

## Debug Mode Features

### Authentication Bypass
- **Frontend**: No token required (lines 449-454 in admin.html commented out)
- **Backend**: Returns mock admin when no token provided (DEBUG=True)
- **Mock Admin Details**:
  - Email: `debug@admin.local`
  - Tenant: `career`
  - Role: `ADMIN`

### Security Notes
- ⚠️ DEBUG mode should ONLY be used locally
- ⚠️ Production must set `DEBUG=False` in .env
- ⚠️ If you provide a token (even in DEBUG), it will validate normally

## Troubleshooting

### Issue: Still seeing "[object Object]"
**Solution**: Hard refresh the browser (Ctrl+Shift+R or Cmd+Shift+R)
- Browser may have cached old JavaScript

### Issue: Getting 401 Unauthorized
**Solution**: Check that DEBUG=True in .env
```bash
grep DEBUG .env
# Should show: DEBUG=True
```

### Issue: Server won't start
**Solution**: Check for syntax errors
```bash
poetry run python -c "from app.api.v1.admin_counselors import router"
```

### Issue: Database errors
**Solution**: Check database connection
```bash
poetry run python -c "from app.core.database import get_db; next(get_db())"
```

## Verification Checklist

- [ ] Server starts without errors
- [ ] Admin portal loads at `/admin`
- [ ] Can open "新增會員" modal
- [ ] Creating valid counselor succeeds
- [ ] Error messages are readable (not "[object Object]")
- [ ] Duplicate username shows clear error
- [ ] Duplicate email shows clear error
- [ ] Browser console shows detailed logs
- [ ] List refreshes after successful creation

## Next Steps

After verifying the fix works:

1. **Document in changelog**
   ```bash
   # Add to CHANGELOG.md under [Unreleased]
   ```

2. **Re-enable authentication** (future task)
   - Uncomment lines 449-454 in admin.html
   - Implement proper admin login flow
   - Remove DEBUG mode bypass

3. **Add more validation**
   - Email format validation on frontend
   - Phone number format validation
   - Password strength requirements

4. **Add integration tests**
   - Test error handling in `test_admin_counselors_api.py`
   - Test duplicate username/email scenarios
   - Test multi-tenant isolation

## Questions?

If you encounter any issues:
1. Check browser console (F12)
2. Check server logs
3. Verify .env has `DEBUG=True`
4. Try hard refresh (Ctrl+Shift+R)

---

**Last Updated**: 2025-12-23
**Tested On**: Local development environment
**Status**: Ready for testing
