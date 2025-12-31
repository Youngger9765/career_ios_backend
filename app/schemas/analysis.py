"""
Analysis Schemas - Multi-tenant partial analysis support
Supports both career and island_parents tenants with different response formats
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.realtime import CounselingMode


class AnalyzePartialRequest(BaseModel):
    """通用 partial 分析請求（支援所有租戶）"""

    transcript_segment: str = Field(
        ...,
        min_length=1,
        description="最近 60 秒的逐字稿",
    )
    mode: Optional[CounselingMode] = Field(
        default=CounselingMode.practice,
        description="諮詢模式：practice (詳細教學) 或 emergency (快速建議)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transcript_segment": "個案：我最近對未來感到很焦慮...",
                    "mode": "practice",
                }
            ]
        }


class RAGDocument(BaseModel):
    """RAG 檢索到的文件"""

    doc_id: Optional[str] = None
    title: str
    content: str
    relevance_score: float
    chunk_id: Optional[str] = None


class DetailedScript(BaseModel):
    """
    詳細話術範例（逐字稿級別）
    用於 8 Schools of Parenting 整合 - Practice Mode
    """

    situation: str = Field(
        ...,
        description="當前情境簡述（1 句話）",
        min_length=1,
    )
    parent_script: str = Field(
        ...,
        description="家長可以使用的逐字稿話術（100-300 字），包含核心同理陳述、提供選擇或設限、可立即使用的對話",
        min_length=50,
    )
    child_likely_response: str = Field(
        ...,
        description="孩子可能的回應（簡短）",
        min_length=1,
    )
    theory_basis: str = Field(
        ...,
        description="理論來源標註（例如：薩提爾 + Dr. Becky + 阿德勒）",
        min_length=1,
    )
    step: str = Field(
        ...,
        description="對應步驟（例如：同理連結 → 即時話術）",
        min_length=1,
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "situation": "當孩子拒絕寫作業時",
                    "parent_script": "（蹲下平視）我看到你現在不想寫作業，好像很累。是不是今天在學校已經很努力了？\n\n我們現在先不談作業。你是要先休息 10 分鐘，還是我陪你一起做？你覺得哪一個比較容易開始？",
                    "child_likely_response": "可能選擇休息或陪伴",
                    "theory_basis": "薩提爾 + Dr. Becky + 阿德勒",
                    "step": "同理連結 → 即時話術",
                }
            ]
        }


class IslandParentAnalysisResponse(BaseModel):
    """
    Island Parents 租戶專用 response
    用於親子對話分析，提供紅黃綠燈安全等級
    支援 8 Schools of Parenting Integration (v1)
    """

    safety_level: str = Field(
        ...,
        description="安全等級：red (情緒崩潰/衝突升級), yellow (需要調整), green (溝通順暢)",
    )
    severity: int = Field(
        ...,
        ge=1,
        le=3,
        description="嚴重程度：1=輕微, 2=中等, 3=嚴重",
    )
    display_text: str = Field(
        ...,
        description="給家長的提示文字，描述當前狀況",
    )
    action_suggestion: str = Field(
        ...,
        description="建議採取的行動或調整方式",
    )
    suggested_interval_seconds: int = Field(
        default=15,
        description="建議多久後再次分析（秒）",
    )
    rag_documents: List[RAGDocument] = Field(
        default_factory=list,
        description="相關的親子教養文獻",
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="關鍵詞（可選，給 iOS 用）",
    )
    categories: List[str] = Field(
        default_factory=list,
        description="類別（可選）",
    )
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage details (prompt_tokens, completion_tokens, total_tokens)",
    )

    # 8 Schools of Parenting 新增欄位（v1）
    detailed_scripts: Optional[List[DetailedScript]] = Field(
        default=None,
        description="詳細話術範例（逐字稿級別），Practice Mode 提供，Emergency Mode 不提供",
    )
    theoretical_frameworks: Optional[List[str]] = Field(
        default=None,
        description="使用的教養流派標註（例如：['薩提爾模式', 'Dr. Becky Kennedy', '阿德勒正向教養']）",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "safety_level": "yellow",
                    "severity": 2,
                    "display_text": "您注意到孩子提到「不想去學校」，這可能是焦慮的徵兆",
                    "action_suggestion": "建議先同理孩子的感受，避免直接質問原因",
                    "suggested_interval_seconds": 15,
                    "rag_documents": [],
                    "keywords": ["焦慮", "學校"],
                    "categories": ["情緒"],
                    "detailed_scripts": [
                        {
                            "situation": "當孩子拒絕去學校時",
                            "parent_script": "（蹲下平視）我看到你說不想去學校，好像有點擔心。是不是學校發生了什麼事讓你不舒服？\n\n我們現在先不談要不要去。你可以先告訴我，你最擔心的是什麼？",
                            "child_likely_response": "可能說出具體擔憂或保持沉默",
                            "theory_basis": "薩提爾 + Dr. Becky + 情緒輔導",
                            "step": "同理連結 → 情緒標註",
                        }
                    ],
                    "theoretical_frameworks": [
                        "薩提爾模式",
                        "Dr. Becky Kennedy",
                        "情緒輔導",
                    ],
                }
            ]
        }


class CareerAnalysisResponse(BaseModel):
    """
    Career 租戶 response（向後兼容 + 新增欄位）
    用於職涯諮詢，分析個案的職涯困惑
    """

    keywords: List[str] = Field(
        ...,
        description="職涯相關關鍵詞",
    )
    categories: List[str] = Field(
        ...,
        description="職涯類別",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="關鍵詞提取信心分數",
    )
    counselor_insights: str = Field(
        ...,
        description="給諮詢師的洞見和提醒",
    )

    # 新增欄位（逐步遷移到與 island_parents 一致的格式）
    safety_level: Optional[str] = Field(
        default=None,
        description="安全等級（可選）",
    )
    severity: Optional[int] = Field(
        default=None,
        ge=1,
        le=3,
        description="嚴重程度（可選）",
    )
    display_text: Optional[str] = Field(
        default=None,
        description="顯示文字（可選）",
    )
    action_suggestion: Optional[str] = Field(
        default=None,
        description="行動建議（可選）",
    )
    rag_documents: Optional[List[RAGDocument]] = Field(
        default=None,
        description="相關的職涯諮詢文獻（可選）",
    )
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage details (prompt_tokens, completion_tokens, total_tokens)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "keywords": ["焦慮", "職涯"],
                    "categories": ["情緒", "職涯探索"],
                    "confidence": 0.95,
                    "counselor_insights": "個案提到對未來感到迷惘，建議探索職涯價值觀",
                    "safety_level": "yellow",
                    "severity": 2,
                    "display_text": "個案提到焦慮和壓力",
                    "action_suggestion": "建議探索職涯價值觀",
                }
            ]
        }
