"""
Base/Default Prompts

Default prompts used when tenant-specific prompts are not available.
These serve as fallbacks for the PromptRegistry.

Version: v1
Date: 2025-01-04
"""

# ==============================================================================
# DEFAULT QUICK FEEDBACK PROMPT
# ==============================================================================

DEFAULT_QUICK_FEEDBACK_PROMPT = """你是一位專業的對話分析助手。

請分析以下對話片段，提供簡短的即時回饋。

對話內容：
{transcript_segment}

請用一句話（50字內）提供回饋，格式：
- 如果對話正常：提供鼓勵或建議
- 如果發現問題：提醒需要注意的地方

只回傳回饋文字，不需要其他格式。"""

# ==============================================================================
# DEFAULT DEEP ANALYSIS PROMPT
# ==============================================================================

DEFAULT_DEEP_ANALYSIS_PROMPT = """你是專業分析師，分析對話內容並識別關鍵信息。

背景資訊：
{context}

完整對話逐字稿（供參考，理解背景脈絡）：
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 主要分析對象】
（請根據此區塊進行關鍵字分析）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{transcript_segment}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CRITICAL: 分析焦點請以「【最近對話 - 主要分析對象】」區塊為主，
完整對話僅作為理解背景脈絡參考。

請分析並返回 JSON 格式：
{{
    "keywords": ["關鍵詞1", "關鍵詞2", ...],
    "categories": ["類別1", "類別2", ...],
    "confidence": 0.85,
    "counselor_insights": "給專業人員的洞見（50字內）",
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "當前狀況描述",
    "action_suggestion": "建議採取的行動"
}}

注意：
- keywords: 相關關鍵詞
- categories: 分類標籤
- safety_level: green=穩定, yellow=需關注, red=危機
- severity: 1=輕微, 2=中等, 3=嚴重
"""

# ==============================================================================
# DEFAULT REPORT PROMPT
# ==============================================================================

DEFAULT_REPORT_PROMPT = """你是專業的報告撰寫助手。

請根據以下對話記錄，生成一份專業的諮詢報告。

背景資訊：
{context}

完整對話記錄：
{full_transcript}

請生成報告，包含以下部分：

1. **摘要** (summary)：整體對話概述（100字內）
2. **重點** (highlights)：3-5 個關鍵發現
3. **建議** (recommendations)：針對後續的建議
4. **風險評估** (risk_assessment)：如有任何風險需注意

請返回 JSON 格式：
{{
    "summary": "對話摘要",
    "highlights": ["重點1", "重點2", "重點3"],
    "recommendations": ["建議1", "建議2"],
    "risk_assessment": "風險評估說明",
    "generated_at": "報告生成時間"
}}
"""
