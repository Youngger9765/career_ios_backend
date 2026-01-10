# TODO

## Nice-to-Have (Low Priority)

### AI Output Validation 改進
- [ ] 抽取共用 validation helper function (`app/services/utils/ai_validation.py`)
- [ ] 加 `finish_reason` 檢查 (針對 max_tokens 較小的 services)
- [ ] AI output 監控 dashboard (fallback 使用率、over-limit warnings)

### Code Quality
- [ ] `keyword_analysis_service.py` 進一步模組化 (663 lines, 超過 400 limit)
