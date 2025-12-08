"""
RAG Report Schemas
Structured output schemas for report generation
"""
from pydantic import BaseModel, Field


class EnhancedReportSchema(BaseModel):
    """10段式增強報告結構"""

    section_2_main_issue: str = Field(description="二、主訴問題 - 個案陳述與諮詢師觀察")
    section_3_development: str = Field(
        description="三、問題發展脈絡 - 出現時間、持續頻率、影響程度"
    )
    section_4_help_seeking: str = Field(
        description="四、求助動機與期待 - 引發因素、期待目標"
    )
    section_5_multilevel_analysis: str = Field(
        description="五、多層次因素分析 - 個人、人際、環境、發展因素（必須引用理論[1][2]）"
    )
    section_6_strengths: str = Field(
        description="六、個案優勢與資源 - 心理優勢、社會資源"
    )
    section_7_professional_judgment: str = Field(
        description="七、諮詢師的專業判斷 - 問題假設、理論依據（必須引用理論[3][4]）"
    )
    section_8_goals_strategies: str = Field(
        description="八、諮詢目標與介入策略 - SMART目標、介入技術（必須引用理論[5][6]）"
    )
    section_9_expected_outcomes: str = Field(
        description="九、預期成效與評估 - 短期指標、長期指標、可能調整"
    )
    section_10_self_reflection: str = Field(
        description="十、諮詢師自我反思 - 本次晤談優點和可改進處"
    )


class LegacyReportSchema(BaseModel):
    """5段式舊版報告結構"""

    main_issue: str = Field(description="主訴問題 - 個案說的，此次想要討論的議題")
    cause_analysis: str = Field(
        description="成因分析 - 諮詢師認為個案為何會有這些主訴問題，結合引用的理論[1][2]分析"
    )
    counseling_goal: str = Field(
        description="晤談目標（移動主訴）- 諮詢師對個案諮詢目標的假設"
    )
    intervention: str = Field(
        description="介入策略 - 諮詢師判斷會需要帶個案做的事，結合理論說明"
    )
    effectiveness: str = Field(description="目前成效評估 - 上述目標和策略達成的狀況")
