# TODO

**Last Updated**: 2026-02-07

---

## 👤 Young 負責項目

### 基礎設施
- [x] **Production DB 設定** ✅ (2026-02-04)
  - ⚠️ **暫時方案**：PROD 與 Staging 共用同一個 Supabase DB
  - 原 Staging DB (ehvgueyrxpvkleqidkdu) 轉正為 Production
  - GitHub Secrets 已更新 (PROD_DATABASE_URL, PROD_SUPABASE_*)

### App Store 審核準備
- [x] **Apple Review 帳號** ✅ (2026-02-06)
  - 帳號: apple_review@islandparents.app / Island2026
  - 已加入 seed script (`scripts/seed_db.py`)
  - PROD/Staging DB 已建立並驗證可登入
  - IOS_GUIDE_PARENTS.md 已更新至 v1.12

### 密碼規則
- [x] **簡化密碼規則** ✅ (2026-02-06)
  - letter (a-z/A-Z，不分大小寫) + digit (0-9), min 8 chars
  - RFC 7807 error format with `password_rules` dict
  - Staging 已測試 4 種 scenario 全部正確

### Email 驗證
- [x] **GET verify-email route** ✅ (2026-02-06)
  - 新增 GET `/{tenant}/verify-email` 支援 email link 點擊
  - Staging 已測試

### iOS 開發文件
- [x] **IOS_GUIDE_PARENTS.md 文件補齊** ✅ (2026-02-07)
  - 新增 `password_rules` 欄位說明表（型別 + 用途）
  - 修正 verify-email URL 格式（GET `/{tenant}/verify-email`）
  - Section 16.3.3 拆分 GET（瀏覽器）+ POST（程式化）兩種方式
  - PROD + Staging 已部署

---

### Firebase Hosting Proxy
- [x] **Firebase Hosting 反向代理** ✅ (2026-02-07)
  - `island-parents-app.web.app` → Cloud Run PROD（island_parents 租戶）
  - `groovy-iris-473015-h3.web.app` → Cloud Run PROD（備用）
  - 多站架構：每個租戶可有獨立 URL，共用同一 Cloud Run
  - 免費方案（Firebase Hosting Free Tier: 10GB/月流量）
  - 最多 36 個 sites / project

---

### 待處理
- [ ] **全站切換 Firebase Hosting URL** 🟡 待處理
  - 目標：所有 API 請求改走 `island-parents-app.web.app`
  - iOS 端：修改 base URL config（1 個變數）
  - 後端：修改 `APP_URL` 環境變數（GitHub Secrets）→ 驗證信連結改用 Firebase URL
  - 優先級：App Store 上架前完成
  - ⚠️ 舊的 Cloud Run URL 仍可用，不影響既有功能

- [ ] **找新的 Staging DB** 🟡 待處理
  - 目的：分離 Staging/Production 環境
  - 選項：Supabase Free Tier / Neon / Railway
  - ⚠️ 風險：目前 Staging 測試會影響 Production 資料
  - 建議：1-2 週內完成

---

## 待外部決策

### 使用量軟性上限（防濫用機制）
- [ ] **設定每月使用量 Soft Cap** 🔴 待規格確認
  - 對外：「一個月無限使用」（行銷話術）
  - 實際：後端設定隱藏上限
  - 需確認：上限數值、計數範圍、超限行為、重置週期
  - 🔴 阻塞：需要產品/商業決策

### AI Output Validation - Dashboard
- [ ] AI output 監控 dashboard 🔴 待設計需求
  - fallback 使用率、over-limit warnings
  - 建議：先完成基礎 validation，dashboard 可延後
