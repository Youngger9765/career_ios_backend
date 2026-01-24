# 內部管理入口設定說明

## 📋 功能概述

`/internal` 路徑是內部管理入口，提供所有管理工具的連結。保護機制：

1. **隱藏路徑**：不公開顯示
2. **密碼保護**：Production 必須設定，Staging/Dev 可選
3. **Rate Limiting**：每分鐘最多 10 次請求

## 🔧 環境變數設定

### Production 環境（必須）
- **GitHub Secret**: `PROD_INTERNAL_PORTAL_PASSWORD`
- **密碼值**: `navicareer2026`
- **行為**: 未設定將無法訪問 `/internal`

### Staging 環境（可選）
- **GitHub Secret**: `INTERNAL_PORTAL_PASSWORD`
- **行為**: 未設定可以無密碼訪問（方便開發）

### 本地開發（可選）
在 `.env` 檔案中加入：
```bash
INTERNAL_PORTAL_PASSWORD=your-password-here
```

## 🚀 使用方式

訪問：`https://your-domain.com/internal`

- Production: 需要密碼 `navicareer2026`
- Staging/Dev: 可無密碼訪問（如果未設定）

## 📝 GitHub Secrets 設定

1. GitHub Repository → Settings → Secrets and variables → Actions
2. New repository secret
3. 設定：
   - **Name**: `PROD_INTERNAL_PORTAL_PASSWORD`
   - **Value**: `navicareer2026`

## ⚠️ 注意事項

- 所有管理頁面仍需 JWT Token 認證
- Production 未設定密碼將無法訪問
