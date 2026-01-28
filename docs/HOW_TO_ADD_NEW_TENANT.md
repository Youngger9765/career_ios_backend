# 如何新增租戶（How to Add New Tenant）

## 📍 需要更新的位置

新增租戶時，需要更新以下 **1 個檔案**：

### 1. `app/utils/tenant.py` ⭐ **唯一需要更新的檔案**

```python
# Valid tenant IDs (資料庫格式：snake_case)
VALID_TENANTS = ["island_parents", "island", "career", "new_tenant"]  # ← 新增這裡

# Tenant ID to URL path mapping (URL 格式：kebab-case)
TENANT_URL_MAP = {
    "island_parents": "island-parents",
    "island": "island",
    "career": "career",
    "new_tenant": "new-tenant",  # ← 新增這裡（資料庫格式 → URL 格式）
}
```

**說明：**
- ✅ **URL 使用連字號**（kebab-case）：`new-tenant`，符合業界慣例
- ✅ **資料庫使用底線**（snake_case）：`new_tenant`，符合程式碼慣例
- ✅ **需要更新兩個地方**：`VALID_TENANTS` 和 `TENANT_URL_MAP`

### 2. `app/services/external/email_sender.py` （可選，用於 Email 顯示名稱）

如果新租戶需要發送 Email（如密碼重設），建議更新顯示名稱：

```python
# Tenant name mapping
tenant_names = {
    "career": "Career",
    "island": "浮島",
    "island_parents": "浮島親子",
    "new_tenant": "新租戶名稱",  # ← 新增這裡（用於 Email 標題）
}
```

**說明：**
- 這個映射用於 Email 標題，例如：`Password Reset Request - 新租戶名稱`
- 如果不更新，會使用預設值 `"Career"`

## 📝 新增租戶步驟

### 範例：新增 `new_tenant` 租戶

#### 步驟 1：更新 `app/utils/tenant.py`

```python
# 第 7 行：新增到 VALID_TENANTS
VALID_TENANTS = ["island_parents", "island", "career", "new_tenant"]

# 第 10-14 行：新增到 TENANT_URL_MAP
TENANT_URL_MAP = {
    "island_parents": "island-parents",
    "island": "island",
    "career": "career",
    "new_tenant": "new-tenant",  # 新增這行
}
```

#### 步驟 2：更新 `app/services/external/email_sender.py`（可選）

```python
# 第 48-52 行：新增到 tenant_names
tenant_names = {
    "career": "Career",
    "island": "浮島",
    "island_parents": "浮島親子",
    "new_tenant": "新租戶",  # 新增這行
}
```

## ✅ 完成後自動支援的功能

更新上述檔案後，新租戶會自動支援：

1. ✅ **動態路由**
   - `/new-tenant/forgot-password` ✅
   - `/new-tenant/reset-password` ✅

2. ✅ **租戶驗證**
   - `validate_tenant("new_tenant")` → `True` ✅

3. ✅ **格式轉換**
   - URL → DB：`new-tenant` → `new_tenant` ✅
   - DB → URL：`new_tenant` → `new-tenant` ✅

4. ✅ **Email 連結**
   - Email 中的重置密碼連結會自動使用 `/new-tenant/reset-password` ✅

5. ✅ **路徑偵測**
   - 從 `/new-tenant/login` 自動偵測為 `new_tenant` ✅

## 🧪 測試新租戶

更新後，執行測試確認：

```bash
# 測試工具函數
pytest tests/unit/test_tenant_utils.py -v

# 測試路由（需要資料庫）
pytest tests/integration/test_tenant_routes.py::TestDynamicTenantForgotPasswordRoute::test_new_tenant_forgot_password_route -v
```

## 📋 檢查清單

新增租戶時，確認以下項目：

- [ ] 更新 `app/utils/tenant.py` 中的 `VALID_TENANTS`
- [ ] 更新 `app/utils/tenant.py` 中的 `TENANT_URL_MAP`
- [ ] （可選）更新 `app/services/external/email_sender.py` 中的 `tenant_names`
- [ ] 執行單元測試確認
- [ ] 測試動態路由是否正常運作
- [ ] 測試 Email 連結是否正確

## 💡 注意事項

1. **命名規則**
   - 資料庫格式：使用 `snake_case`（例如：`new_tenant`）
   - URL 格式：使用 `kebab-case`（例如：`new-tenant`）

2. **大小寫敏感**
   - 所有租戶 ID 都是大小寫敏感的
   - `new_tenant` ≠ `New_Tenant` ≠ `NEW_TENANT`

3. **URL 格式轉換**
   - `snake_case` 中的底線 `_` 會轉換為連字號 `-`
   - 例如：`new_tenant` → `new-tenant`

4. **向後兼容**
   - 新增租戶不會影響現有租戶
   - 所有現有路由繼續運作

