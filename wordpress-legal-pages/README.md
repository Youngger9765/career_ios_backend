# WordPress Legal Pages

## 檔案說明

| 檔案 | 狀態 | 說明 |
|------|------|------|
| `landing-page.html` | ✅ 完成 | 主要 Landing Page（Hero + 3 Features + CTA） |
| `privacy-policy.html` | ✅ 完成 | 隱私權政策 WordPress 版本（10 章節完整） |
| `terms-of-service.html` | ✅ 完成 | 服務條款 WordPress 版本（10 章節完整） |

## 使用方式（WordPress Elementor）

### 1. 開啟檔案
```bash
open privacy-policy.html
```

### 2. 複製全部內容
- 選取全部（Cmd+A / Ctrl+A）
- 複製（Cmd+C / Ctrl+C）

### 3. 貼到 Elementor
1. WordPress 後台 → Pages → Add New
2. Edit with Elementor
3. 拖曳「HTML」widget 到頁面
4. 貼上複製的內容
5. Publish

## 特點

✅ **純 HTML + Inline CSS** - 不需外部樣式檔
✅ **響應式設計** - 自動適應手機/平板/桌面
✅ **完整內容** - 10 個章節，GDPR/PIPA 合規
✅ **專業排版** - 清晰易讀

## 原始版本

原始 Jinja2 模板位於：
```
app/templates/
├── landing.html              # Landing page
└── island_parents/
    ├── legal_base.html       # 法律頁面基礎模板
    ├── privacy.html          # 隱私權政策
    └── terms.html            # 服務條款
```

這些檔案用於 FastAPI 後端，有完整的 TOC 導航和互動功能。

## 客製化

要修改內容，只需編輯 HTML 檔案中的文字部分。

要修改樣式，搜尋並替換：
- **顏色**: `#111827`, `#374151`, `#6b7280`
- **字體大小**: `font-size: 24px`
- **間距**: `margin`, `padding`

## 更新記錄

- **2026-01-31**: 建立 WordPress 版本（從 Jinja2 轉換）
  - ✅ Privacy Policy 完整轉換
  - ✅ Terms of Service 完整轉換
- **2026-01-27**: 原始 Jinja2 版本建立
