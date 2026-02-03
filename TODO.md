# TODO

**Last Updated**: 2026-02-04

---

## 👤 Young 負責項目

### 基礎設施
- [x] **Production DB 設定** ✅ (2026-02-04)
  - ⚠️ **暫時方案**：PROD 與 Staging 共用同一個 Supabase DB
  - 原 Staging DB (ehvgueyrxpvkleqidkdu) 轉正為 Production
  - GitHub Secrets 已更新 (PROD_DATABASE_URL, PROD_SUPABASE_*)

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
