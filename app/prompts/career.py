"""
Career Counseling Prompts

Prompts for career tenant real-time analysis.
Note: Career uses RAG-based report generation (see rag_report_prompt_builder.py)

Version: v1
Date: 2025-01-04
"""

# ==============================================================================
# DEEP ANALYSIS PROMPT (Career)
# ==============================================================================

DEEP_ANALYSIS_PROMPT = """你是職涯諮詢專家，分析個案的職涯困惑和諮詢對話。

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
    "counselor_insights": "給諮詢師的洞見（50字內）",
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "個案當前狀況描述",
    "action_suggestion": "建議諮詢師採取的行動"
}}

注意：
- keywords: 職涯相關關鍵詞（焦慮、迷惘、轉職等）
- categories: 職涯類別（職涯探索、工作壓力、人際關係等）
- safety_level: green=穩定, yellow=需關注, red=危機
- severity: 1=輕微, 2=中等, 3=嚴重
"""

# Backward compatibility
CAREER_ANALYSIS_PROMPT = DEEP_ANALYSIS_PROMPT


# ==============================================================================
# REPORT PROMPT (Career - Simple Version)
# Note: For RAG-based reports, use rag_report_prompt_builder.py
# ==============================================================================

REPORT_PROMPT = """你是職涯諮詢督導，協助生成個案報告。

背景資訊：
{context}

完整對話記錄：
{full_transcript}

請生成結構化的個案報告，返回 JSON 格式：

{{
    "summary": "諮詢摘要（100字內）",
    "main_concerns": ["主訴問題1", "主訴問題2"],
    "analysis": "成因分析（結合職涯理論）",
    "counseling_goals": ["諮詢目標1", "諮詢目標2"],
    "intervention_strategy": "介入策略說明",
    "progress_evaluation": "目前成效評估",
    "next_steps": ["下次諮詢建議1", "建議2"],
    "generated_at": "報告生成時間"
}}

注意：
- 使用專業、客觀、具同理心的語氣
- 每個欄位都要有實質內容
- 主訴問題來自個案陳述
- 介入策略需結合職涯理論
"""
