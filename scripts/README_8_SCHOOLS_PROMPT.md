# 8 大流派 Prompt 測試指南

**版本**: v1 (測試版)
**日期**: 2025-12-31
**目的**: P2 Phase 2 快速驗證 - 8 大流派整合 + 逐字稿級別話術

---

## 📁 檔案說明

### 1. Prompt 檔案
- **路徑**: `/app/prompts/island_parents_8_schools_practice_v1.py`
- **內容**: 8 大流派整合的 Practice Mode Prompt
- **用途**: 測試版 Prompt，可直接在 service 中引用測試

### 2. 測試腳本
- **路徑**: `/scripts/test_8_schools_prompt.py`
- **內容**: 自動化測試腳本，包含 5 個真實場景
- **用途**: 快速驗證 Prompt 效果，生成比較報告

### 3. 比較文檔
- **路徑**: `/scripts/PROMPT_COMPARISON.md`
- **內容**: 新舊 Prompt 的詳細比較分析
- **用途**: 決策參考

### 4. 測試結果 (執行後生成)
- **路徑**: `/scripts/test_8_schools_prompt_results.json`
- **內容**: 完整的測試結果數據
- **用途**: 數據分析、客戶展示

---

## 🚀 快速開始

### Step 1: 執行測試

```bash
cd /Users/young/project/career_ios_backend
poetry run python scripts/test_8_schools_prompt.py
```

### Step 2: 查看結果

測試完成後會顯示：
- ✅ 每個場景的 Response Time
- ✅ Token 用量 (prompt + completion)
- ✅ 成本估算
- ✅ detailed_scripts 範例
- ✅ 理論來源標註
- ✅ 與舊 Prompt 的比較數據

### Step 3: 檢查輸出檔案

```bash
# 查看完整測試結果 (JSON)
cat scripts/test_8_schools_prompt_results.json | jq '.'

# 或使用 Python 美化輸出
poetry run python -m json.tool scripts/test_8_schools_prompt_results.json
```

---

## 📊 測試場景

腳本會測試以下 5 個真實親子互動場景：

1. **孩子拒絕寫作業** (YELLOW)
   - 測試：同理連結 + 提供選擇
   - 理論：薩提爾模式 + Dr. Becky + 阿德勒

2. **手足衝突** (YELLOW)
   - 測試：協作解決問題 + 性別意識
   - 理論：情緒輔導 + Ross Greene + 社會意識教養

3. **情緒崩潰（哭鬧）** (RED)
   - 測試：全腦教養 + 情緒安撫
   - 理論：人際神經生物學 + 情緒輔導 + Dr. Becky

4. **挑戰權威（頂嘴）** (YELLOW)
   - 測試：溫和而堅定 + 協商
   - 理論：阿德勒 + Ross Greene + 薩提爾

5. **分離焦慮** (YELLOW)
   - 測試：依附安全感 + 情緒調節
   - 理論：依附理論 + 情緒輔導 + 神經生物學

---

## 📈 評估標準

### 1. Token 用量
- **目標**: 1800-2400 tokens/次
- **對比**: vs 原版 900-1000 tokens
- **預期增加**: +100-140%

### 2. Response Time
- **目標**: < 3000 ms
- **對比**: vs 原版 ~1500 ms
- **可接受範圍**: < 5000 ms

### 3. 功能覆蓋率
- **detailed_scripts**: ≥ 80% (4/5 場景)
- **theoretical_frameworks**: ≥ 80% (4/5 場景)
- **話術長度**: 150-300 字

### 4. 品質評估
- **理論標註正確性**: ≥ 90%
- **話術可執行性**: ≥ 80%
- **safety_level 準確度**: ≥ 90%

---

## 🔍 測試結果分析

執行測試後，檢查以下指標：

### 1. 平均 Token 使用量
```
新版: ___ tokens (預期 1800-2400)
舊版: ___ tokens (預期 900-1000)
增加: ___% (預期 100-140%)
```

### 2. 平均 Response Time
```
新版: ___ ms (預期 < 3000)
舊版: ___ ms (預期 ~1500)
差異: ___% (預期 < 100%)
```

### 3. 平均成本
```
新版: $___ USD (預期 $0.0012-0.0018)
舊版: $___ USD (預期 $0.0005-0.0006)
增加: ___% (預期 140-200%)
```

### 4. 新功能覆蓋率
```
detailed_scripts: __/5 (預期 ≥ 4/5)
theoretical_frameworks: __/5 (預期 ≥ 4/5)
```

---

## ✅ 驗收標準

符合以下條件即可進入 Phase 3 (全面實作)：

- [ ] Token 用量在預期範圍內 (1800-2400)
- [ ] Response Time < 3000 ms
- [ ] detailed_scripts 覆蓋率 ≥ 80%
- [ ] 話術長度符合要求 (150-300 字)
- [ ] 理論標註正確且有意義
- [ ] 客戶確認符合期望
- [ ] 成本增加可接受 (+140-200%)

---

## 🐛 常見問題

### Q1: 測試失敗怎麼辦？
```bash
# 檢查 Gemini API 設定
echo $GEMINI_API_KEY

# 檢查網路連線
ping -c 3 generativelanguage.googleapis.com

# 查看詳細錯誤
poetry run python scripts/test_8_schools_prompt.py 2>&1 | tee test_error.log
```

### Q2: Token 用量超出預期？
- 檢查 `transcript_segment` 是否過長（應限制在 500 字內）
- 檢查 Prompt 是否有重複內容
- 考慮優化 Prompt 結構

### Q3: detailed_scripts 覆蓋率低？
- 檢查 AI Response 是否包含此欄位
- 檢查 JSON 解析是否正確
- 調整 Prompt 指令，強調必填

### Q4: 成本過高？
- 考慮折衷方案：新增 `detailed_mode=True` 參數
- 讓用戶選擇是否需要詳細話術
- 或僅在 Practice Mode 啟用

---

## 📝 下一步

### 如果測試通過：
1. ✅ 更新 `PROMPT_COMPARISON.md` 的測試結果區塊
2. ✅ 準備客戶展示材料（挑選 2-3 個最佳範例）
3. ✅ 等待客戶確認
4. ✅ 進入 Phase 3: 全面實作

### 如果測試失敗：
1. 🔍 分析失敗原因
2. 🔧 調整 Prompt 或測試場景
3. 🔄 重新測試
4. 📊 記錄調整過程

---

## 📞 聯絡資訊

- **專案**: career_ios_backend (island_parents 租戶)
- **任務**: P2 Phase 2 - 8 大流派 Prompt 測試
- **參考**: TODO.md Line 888-1186

---

**祝測試順利！** 🎉
