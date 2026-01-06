# 登入失敗訊息規範

本文檔定義登入相關的錯誤訊息標準，用於防止帳號列舉攻擊（Account Enumeration）。

---

## 資安原則

### ❌ 問題：訊息過於具體

**不安全的錯誤訊息**:
```
❌ "此帳號不存在"
❌ "密碼錯誤"
❌ "此Email尚未註冊"
❌ "帳號已停用"
```

**風險**: 攻擊者可以透過錯誤訊息差異，推測出哪些帳號存在於系統中

---

### ✅ 解決方案：統一模糊訊息

**安全的錯誤訊息**:
```
✅ "登入資料有誤，請確認帳號與密碼"
✅ "Login credentials are incorrect"
```

**優點**: 無論是帳號不存在、密碼錯誤、帳號停用，都返回相同訊息

---

## Backend API 規範

### 登入 API (`POST /api/v1/auth/login`)

#### 所有失敗情況統一返回

**HTTP Status**: `401 Unauthorized`

**Response Body**:
```json
{
  "detail": "登入資料有誤，請確認帳號與密碼"
}
```

#### 涵蓋的失敗情況

1. ✅ 帳號不存在
2. ✅ 密碼錯誤
3. ✅ 帳號已停用 (`is_active = False`)
4. ✅ 帳號已刪除
5. ✅ 其他驗證失敗

#### 實作示例

```python
# app/api/auth.py

@router.post("/login")
async def login(request: LoginRequest, db=Depends(get_db)):
    # 統一錯誤訊息
    UNIFIED_ERROR = "登入資料有誤，請確認帳號與密碼"

    # 查詢用戶
    user = db.query(Counselor).filter(
        Counselor.username == request.username
    ).first()

    # 情況1: 帳號不存在
    if not user:
        raise HTTPException(status_code=401, detail=UNIFIED_ERROR)

    # 情況2: 密碼錯誤
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail=UNIFIED_ERROR)

    # 情況3: 帳號已停用
    if not user.is_active:
        raise HTTPException(status_code=401, detail=UNIFIED_ERROR)

    # 成功登入
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 註冊 API (`POST /api/v1/auth/register`)

#### Email 已存在

**HTTP Status**: `400 Bad Request`

**Response Body**:
```json
{
  "detail": "此 Email 已被使用"
}
```

**說明**: 註冊時可以明確告知 Email 已存在，因為這是公開註冊流程的合理回饋

#### Username 已存在

**HTTP Status**: `400 Bad Request`

**Response Body**:
```json
{
  "detail": "此帳號名稱已被使用"
}
```

---

### 密碼重設 API

#### 請求重設 (`POST /api/v1/auth/password-reset/request`)

**統一成功訊息** (無論 Email 是否存在):

**HTTP Status**: `200 OK`

**Response Body**:
```json
{
  "message": "若此 Email 存在於系統中，您將收到密碼重設信件"
}
```

**說明**:
- Email 存在 → 實際發送重設信件
- Email 不存在 → 不發送信件，但返回相同訊息
- 防止攻擊者透過此 API 列舉有效 Email

---

## Frontend UI 規範

### 登入失敗提示

**統一錯誤訊息 UI**:

```
┌─────────────────────────────────┐
│  登入失敗                        │
│  登入資料有誤，請確認帳號與密碼   │
│                                 │
│          [ 確定 ]               │
└─────────────────────────────────┘
```

**CSS Class**: `.login-error-unified`

### 不要顯示的訊息

❌ "帳號不存在，是否要註冊？"
❌ "密碼錯誤，忘記密碼請點此"
❌ "您的帳號已被停用，請聯繫管理員"

**原因**: 這些訊息洩漏了系統內部狀態

---

## 其他認證相關訊息

### Token 過期

**HTTP Status**: `401 Unauthorized`

**Response Body**:
```json
{
  "detail": "登入已過期，請重新登入"
}
```

### Token 無效

**HTTP Status**: `401 Unauthorized`

**Response Body**:
```json
{
  "detail": "登入資訊無效，請重新登入"
}
```

### 權限不足

**HTTP Status**: `403 Forbidden`

**Response Body**:
```json
{
  "detail": "您沒有權限執行此操作"
}
```

**說明**: 此情況可以明確告知權限不足，因為用戶已通過認證

---

## 日誌記錄規範

### 安全日誌 (Security Log)

**登入失敗時應記錄** (僅內部使用，不回傳給前端):

```python
import logging

security_logger = logging.getLogger("security")

# 失敗原因: 記錄在 server log，不回傳給用戶
if not user:
    security_logger.warning(
        f"Login failed: user not found - username={request.username}, "
        f"ip={request.client.host}"
    )
    raise HTTPException(status_code=401, detail=UNIFIED_ERROR)

if not verify_password(request.password, user.hashed_password):
    security_logger.warning(
        f"Login failed: wrong password - username={request.username}, "
        f"ip={request.client.host}"
    )
    raise HTTPException(status_code=401, detail=UNIFIED_ERROR)

if not user.is_active:
    security_logger.warning(
        f"Login failed: account inactive - username={request.username}, "
        f"user_id={user.id}"
    )
    raise HTTPException(status_code=401, detail=UNIFIED_ERROR)
```

### 日誌用途

1. **分析攻擊模式**: 偵測暴力破解、帳號列舉嘗試
2. **合規稽核**: 滿足資安稽核要求
3. **問題排查**: 協助用戶解決登入問題（客服查看）
4. **監控告警**: 設定異常登入嘗試的告警規則

---

## Rate Limiting (速率限制)

### 登入 API 限流

**規則**:
- 每個 IP: 10 次/分鐘
- 每個帳號: 5 次/分鐘

**超過限制時的錯誤訊息**:

**HTTP Status**: `429 Too Many Requests`

**Response Body**:
```json
{
  "detail": "登入嘗試次數過多，請稍後再試"
}
```

**實作示例**:
```python
from fastapi_limiter.depends import RateLimiter

@router.post(
    "/login",
    dependencies=[Depends(RateLimiter(times=10, minutes=1))]
)
async def login(...):
    ...
```

---

## 測試檢查清單

### Backend API 測試

- [ ] 帳號不存在 → 返回統一錯誤訊息
- [ ] 密碼錯誤 → 返回統一錯誤訊息
- [ ] 帳號停用 → 返回統一錯誤訊息
- [ ] 所有失敗情況的 HTTP status code = 401
- [ ] 所有失敗情況的錯誤訊息文字相同
- [ ] 密碼重設請求（Email 不存在）→ 返回成功訊息但不發信
- [ ] 登入失敗有正確記錄到 security log

### Frontend UI 測試

- [ ] 登入失敗時顯示統一錯誤訊息
- [ ] 錯誤訊息不洩漏帳號是否存在
- [ ] 錯誤訊息不洩漏密碼是否正確
- [ ] 錯誤訊息不洩漏帳號狀態（停用/刪除）

---

## 參考資料

### OWASP 指南
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Credential Stuffing Prevention](https://owasp.org/www-community/attacks/Credential_stuffing)

### CWE 弱點
- [CWE-204: Observable Response Discrepancy](https://cwe.mitre.org/data/definitions/204.html)
- [CWE-209: Generation of Error Message Containing Sensitive Information](https://cwe.mitre.org/data/definitions/209.html)

---

## 版本歷史

- **v1.0** (2025-12-31): 初版建立，定義登入失敗訊息統一規範
- 基於資安最佳實踐和 OWASP 建議

---

**文件維護**: Backend 開發團隊
**最後更新**: 2025-12-31
**相關 Issue**: TODO.md #4.5 登入失敗提示語統一（資安）
