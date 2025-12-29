# SMTP Configuration for Password Reset Emails

## 問題說明

Password reset 功能在 staging 環境無法發送郵件，因為缺少 SMTP 環境變數配置。

## 解決方案

需要在 GitHub Secrets 中新增以下 4 個 secrets：

### 1. SMTP_USER
- **說明**：Gmail 帳號（用於發送郵件）
- **範例值**：`young.tsai.9765@gmail.com`
- **設定位置**：GitHub Repository → Settings → Secrets and variables → Actions → New repository secret

### 2. SMTP_PASSWORD
- **說明**：Gmail 應用程式密碼（**不是一般登入密碼**）
- **如何取得**：
  1. 登入 Gmail 帳號
  2. 前往：https://myaccount.google.com/apppasswords
  3. 選擇「郵件」和「其他裝置」
  4. 點擊「產生」
  5. 複製 16 位數的應用程式密碼（例如：`abcd efgh ijkl mnop`）
- **注意**：需要開啟 Google 帳戶的「兩步驟驗證」才能使用應用程式密碼

### 3. FROM_EMAIL
- **說明**：寄件人郵件地址（顯示在收件人的「寄件人」欄位）
- **建議值**：`noreply@careercreator.tw`
- **或使用**：與 SMTP_USER 相同的 Gmail 地址

### 4. APP_URL
- **說明**：應用程式的基礎 URL（用於生成密碼重設連結）
- **Staging 值**：`https://career-app-api-staging-kxaznpplqq-uc.a.run.app`
- **Production 值**：`https://career-app-api-kxaznpplqq-uc.a.run.app`（未來設定）

## 設定步驟

### Step 1: 取得 Gmail 應用程式密碼

1. 確保 Google 帳戶已開啟「兩步驟驗證」
2. 前往：https://myaccount.google.com/apppasswords
3. 產生新的應用程式密碼
4. 複製 16 位數密碼（記得保存，只會顯示一次）

### Step 2: 在 GitHub 新增 Secrets

1. 前往：https://github.com/[你的組織]/career_ios_backend/settings/secrets/actions
2. 點擊「New repository secret」
3. 依序新增 4 個 secrets：

   | Name | Value |
   |------|-------|
   | SMTP_USER | `young.tsai.9765@gmail.com` |
   | SMTP_PASSWORD | `你的16位數應用程式密碼` |
   | FROM_EMAIL | `noreply@careercreator.tw` |
   | APP_URL | `https://career-app-api-staging-kxaznpplqq-uc.a.run.app` |

### Step 3: 重新部署

設定完成後，push 任何變更到 `staging` 分支即可觸發重新部署。

```bash
git push origin staging
```

## 驗證

部署完成後，測試 password reset 功能：

1. 前往：https://career-app-api-staging-kxaznpplqq-uc.a.run.app/forgot-password?tenant=island_parents
2. 輸入郵件地址：`young.tsai.9765@gmail.com`
3. 送出表單
4. 檢查信箱是否收到密碼重設郵件

## 常見問題

### Q: 為什麼要用應用程式密碼而不是一般密碼？
A: Google 出於安全考量，不允許第三方應用程式直接使用一般密碼登入 Gmail SMTP。必須使用應用程式密碼。

### Q: 可以使用其他 SMTP 服務嗎？
A: 可以。如果使用 SendGrid、Mailgun 等服務，需要修改 `SMTP_HOST` 和 `SMTP_PORT`（目前預設為 Gmail）。

### Q: Production 環境也需要設定嗎？
A: 是的。未來部署到 production 時，需要設定相同的 secrets，但 APP_URL 要改為 production URL。

## 參考資料

- [Google 應用程式密碼說明](https://support.google.com/accounts/answer/185833)
- [GitHub Encrypted Secrets 文檔](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- 相關程式碼：`app/services/email_sender.py:509`
