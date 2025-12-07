"""
Realtime STT Counseling Schemas
用於即時語音轉文字諮商輔助功能
"""
from typing import List

from pydantic import BaseModel, Field, field_validator


class SpeakerSegment(BaseModel):
    """Speaker 片段（諮商師或案主的對話）"""

    speaker: str = Field(..., description="說話者角色: counselor 或 client")
    text: str = Field(..., description="說話內容")

    @field_validator("speaker")
    @classmethod
    def validate_speaker(cls, v: str) -> str:
        """驗證 speaker 只能是 counselor 或 client"""
        if v not in ["counselor", "client"]:
            raise ValueError("speaker must be 'counselor' or 'client'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{"speaker": "counselor", "text": "你最近工作上有什麼困擾嗎？"}]
        }
    }


class RealtimeAnalyzeRequest(BaseModel):
    """即時分析請求（每 60 秒觸發一次）"""

    transcript: str = Field(..., min_length=1, description="完整逐字稿（過去 1 分鐘）")
    speakers: List[SpeakerSegment] = Field(..., description="Speaker 片段列表")
    time_range: str = Field(..., description="時間範圍（例如：0:00-1:00）")

    @field_validator("transcript")
    @classmethod
    def validate_transcript(cls, v: str) -> str:
        """驗證 transcript 不能為空白"""
        if not v or not v.strip():
            raise ValueError("transcript cannot be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transcript": "諮商師：你最近工作上有什麼困擾嗎？\n案主：我覺得活著沒什麼意義...",
                    "speakers": [
                        {"speaker": "counselor", "text": "你最近工作上有什麼困擾嗎？"},
                        {"speaker": "client", "text": "我覺得活著沒什麼意義..."},
                    ],
                    "time_range": "0:00-1:00",
                }
            ]
        }
    }


class RAGSource(BaseModel):
    """RAG 知識庫來源"""

    title: str = Field(..., description="文件標題")
    content: str = Field(..., description="相關內容片段")
    score: float = Field(..., ge=0.0, le=1.0, description="相似度分數（0-1）")


class RealtimeAnalyzeResponse(BaseModel):
    """即時分析回應（AI 督導建議）"""

    summary: str = Field(..., description="對話歸納（1-2 句）")
    alerts: List[str] = Field(..., description="提醒事項（3-5 點）")
    suggestions: List[str] = Field(..., description="建議回應（2-3 點）")
    time_range: str = Field(..., description="時間範圍")
    timestamp: str = Field(..., description="分析時間戳（ISO 8601 格式）")
    rag_sources: List[RAGSource] = Field(
        default=[], description="RAG 知識庫來源（可選）"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "案主表達對工作的焦慮，提到「活著沒意義」，諮商師開始評估風險",
                    "alerts": [
                        "⚠️ 案主提到「活著沒意義」，需立即評估自殺風險",
                        "⚠️ 注意案主情緒狀態，是否有憂鬱症狀",
                        "✅ 諮商師使用反映情感技巧適當",
                    ],
                    "suggestions": [
                        "💡 建議直接評估：「當你說活著沒意義，是否曾想過結束生命？」",
                        "💡 探索工作壓力來源：「主管盯著你的感覺，能具體說說是什麼樣的情況嗎？」",
                    ],
                    "time_range": "0:00-1:00",
                    "timestamp": "2025-12-06T10:01:00Z",
                    "rag_sources": [
                        {
                            "title": "職涯諮詢概論",
                            "content": "探索工作價值觀的方法...",
                            "score": 0.85,
                        }
                    ],
                }
            ]
        }
    }
