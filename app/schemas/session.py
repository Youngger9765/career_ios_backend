"""
Session Schemas - 會談相關的所有 Schema 定義
包含：
- Session CRUD schemas
- Recording schemas
- Realtime counseling schemas (merged from realtime.py)
- Timeline schemas
- Reflection schemas
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.base import BaseSchema

# =============================================================================
# Realtime Counseling Enums & Models (merged from realtime.py)
# =============================================================================


class CounselingMode(str, Enum):
    """Counseling mode: emergency (simplified) or practice (detailed)"""

    emergency = "emergency"
    practice = "practice"


class SafetyLevel(str, Enum):
    """Safety level indicator for parent-child interaction"""

    red = "red"  # High risk: violent language, extreme emotions, crisis
    yellow = "yellow"  # Medium risk: escalating conflict, frustration
    green = "green"  # Safe: calm, positive interaction


class SpeakerSegment(BaseModel):
    """Speaker 片段（諮詢師或案主的對話）"""

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


class RAGSource(BaseModel):
    """RAG 知識庫來源"""

    title: str = Field(..., description="文件標題")
    content: str = Field(..., description="相關內容片段")
    score: float = Field(..., ge=0.0, le=1.0, description="相似度分數（0-1）")
    theory: str = Field(default="其他", description="所屬理論（正向教養、情緒教養等）")


class CacheMetadata(BaseModel):
    """Cache 元數據"""

    cache_name: str = Field(..., description="Cache 名稱")
    cache_created: bool = Field(..., description="是否為新建的 cache")
    cached_tokens: int = Field(default=0, description="從 cache 讀取的 token 數")
    prompt_tokens: int = Field(default=0, description="新增的 prompt token 數")
    error: str = Field(default="", description="錯誤訊息（如有）")
    message: str = Field(default="", description="狀態訊息（如有）")


class ProviderMetadata(BaseModel):
    """Provider performance metadata"""

    provider: str = Field(..., description="LLM provider used")
    latency_ms: int = Field(..., description="Response latency in milliseconds")
    model: str = Field(default="", description="Model name")


class ImprovementSuggestion(BaseModel):
    """改進建議"""

    issue: str = Field(..., description="待解決的議題")
    analyze: str = Field(..., description="溝通內容分析")
    suggestion: str = Field(..., description="建議下次可以這樣說")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "issue": "使用威脅語氣「你再不寫我就打你」",
                    "analyze": "這種語氣容易讓孩子產生恐懼，而非理解家長的期望。",
                    "suggestion": "可以換成：「我看到你現在不想寫功課，可以跟我說說為什麼嗎？」",
                }
            ]
        }
    }


# =============================================================================
# Realtime Analyze Request/Response
# =============================================================================


class RealtimeAnalyzeRequest(BaseModel):
    """即時分析請求（每 60 秒觸發一次）"""

    mode: CounselingMode = Field(
        default=CounselingMode.practice,
        description="Counseling mode: 'emergency' (simplified) or 'practice' (detailed, default)",
    )
    transcript: str = Field(..., min_length=1, description="完整逐字稿（過去 1 分鐘）")
    speakers: List[SpeakerSegment] = Field(..., description="Speaker 片段列表")
    time_range: str = Field(..., description="時間範圍（例如：0:00-1:00）")
    use_cache: bool = Field(default=True, description="是否使用 Gemini context caching")
    use_rag: bool = Field(default=False, description="是否使用 RAG 知識庫（預設關閉）")
    session_id: str = Field(default="", description="會談 session ID（用於 cache key）")

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
                    "transcript": "諮詢師：你最近工作上有什麼困擾嗎？\n案主：我覺得活著沒什麼意義...",
                    "speakers": [
                        {"speaker": "counselor", "text": "你最近工作上有什麼困擾嗎？"},
                        {"speaker": "client", "text": "我覺得活著沒什麼意義..."},
                    ],
                    "time_range": "0:00-1:00",
                }
            ]
        }
    }


class RealtimeAnalyzeResponse(BaseModel):
    """即時分析回應（AI 督導建議）"""

    safety_level: str = Field(
        ...,
        description="Safety level: 'green' (safe), 'yellow' (needs adjustment), 'red' (urgent correction)",
    )
    summary: str = Field(..., description="對話歸納（1-2 句）")
    alerts: List[str] = Field(..., description="提醒事項（3-5 點）")
    suggestions: List[str] = Field(..., description="建議回應（2-3 點）")
    time_range: str = Field(..., description="時間範圍")
    timestamp: str = Field(..., description="分析時間戳（ISO 8601 格式）")
    rag_sources: List[RAGSource] = Field(
        default=[], description="RAG 知識庫來源（可選）"
    )
    cache_metadata: CacheMetadata | None = Field(
        default=None, description="Cache 元數據（如有使用 cache）"
    )
    provider_metadata: ProviderMetadata | None = Field(
        default=None, description="Provider performance metadata"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "safety_level": "yellow",
                    "summary": "案主表達對工作的焦慮，提到「活著沒意義」，諮詢師開始評估風險",
                    "alerts": [
                        "⚠️ 案主提到「活著沒意義」，需立即評估自殺風險",
                        "⚠️ 注意案主情緒狀態，是否有憂鬱症狀",
                        "✅ 諮詢師使用反映情感技巧適當",
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


# =============================================================================
# Quick Feedback Request/Response
# =============================================================================


class QuickFeedbackRequest(BaseModel):
    """快速回饋請求（10-15 秒輪詢）"""

    recent_transcript: str = Field(..., min_length=1, description="最近 10 秒的逐字稿")

    @field_validator("recent_transcript")
    @classmethod
    def validate_transcript(cls, v: str) -> str:
        """驗證 transcript 不能為空白"""
        if not v or not v.strip():
            raise ValueError("recent_transcript cannot be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "recent_transcript": "家長：你再這樣我就生氣了！\n孩子：我不是故意的..."
                }
            ]
        }
    }


class QuickFeedbackResponse(BaseModel):
    """快速回饋回應（輕量 AI 雞湯文）"""

    message: str = Field(..., description="AI 生成的鼓勵訊息（20 字內）")
    type: str = Field(..., description="訊息類型：ai_generated 或 fallback")
    timestamp: str = Field(..., description="生成時間戳（ISO 8601 格式）")
    latency_ms: int = Field(..., description="延遲時間（毫秒）")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "深呼吸，保持冷靜",
                    "type": "ai_generated",
                    "timestamp": "2025-12-31T10:00:00Z",
                    "latency_ms": 1200,
                }
            ]
        }
    }


# =============================================================================
# Parents Report Request/Response
# =============================================================================


class ParentsReportRequest(BaseModel):
    """家長對話報告請求"""

    transcript: str = Field(..., min_length=1, description="完整對話逐字稿")
    session_id: str = Field(default="", description="會談 session ID（可選）")

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
                    "transcript": "家長：我今天真的氣死了，孩子又不寫功課...\n孩子：我就是不想寫！",
                    "session_id": "session-123",
                }
            ]
        }
    }


class ParentsReportReference(BaseModel):
    """報告參考資料（來自 RAG 教養理論）"""

    title: str = Field(..., description="參考資料標題")
    content: str = Field(..., description="相關內容摘要")
    source: str = Field(..., description="來源文件名稱")
    theory: str = Field(default="", description="所屬理論（正向教養、情緒教養等）")


class ParentsReportResponse(BaseModel):
    """家長對話報告回應"""

    encouragement: str = Field(
        ...,
        description="鼓勵標題（如：這次你已經做了一件重要的事：願意好好跟孩子談。）",
    )
    issue: str = Field(..., description="待解決的議題")
    analyze: str = Field(..., description="溝通內容分析")
    suggestion: str = Field(..., description="建議下次可以這樣說")
    references: List[ParentsReportReference] = Field(
        default=[], description="參考資料列表（來自 RAG 教養理論知識庫）"
    )
    timestamp: str = Field(..., description="生成時間戳（ISO 8601 格式）")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "encouragement": "這次你已經做了一件重要的事：願意好好跟孩子談。",
                    "issue": "對話陷入無效重複，缺乏雙向互動。",
                    "analyze": "重複相同的指令容易讓孩子產生「聽而不聞」的習慣，且未針對孩子的需求做出回應。",
                    "suggestion": "「我知道你還想玩，要停下來很難。你是想現在開始，還是再玩 3 分鐘？」",
                    "references": [
                        {
                            "title": "正向教養：溫和而堅定的教養方式",
                            "content": "當孩子不配合時，提供有限選擇讓孩子感受到自主權...",
                            "source": "正向教養指南.pdf",
                            "theory": "正向教養",
                        }
                    ],
                    "timestamp": "2025-12-26T10:00:00Z",
                }
            ]
        }
    }


# Recording-related schemas
class RecordingSegment(BaseModel):
    """錄音片段"""

    segment_number: int
    start_time: str
    end_time: str
    duration_seconds: int
    transcript_text: str
    transcript_sanitized: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "segment_number": 1,
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 10:30",
                    "duration_seconds": 1800,
                    "transcript_text": "諮詢師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                    "transcript_sanitized": "諮詢師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                }
            ]
        }
    }


class AppendRecordingRequest(BaseModel):
    """Append 錄音片段請求（iOS 友善版本）"""

    start_time: str
    end_time: str
    duration_seconds: Optional[
        int
    ] = None  # 選填，後端會自動從 start_time/end_time 計算
    transcript_text: str
    transcript_sanitized: Optional[str] = None


class AppendRecordingResponse(BaseModel):
    """Append 錄音片段響應"""

    session_id: UUID
    recording_added: RecordingSegment
    total_recordings: int
    transcript_text: str
    updated_at: datetime


# Session CRUD schemas
class SessionCreateRequest(BaseModel):
    """創建會談記錄請求"""

    case_id: UUID
    session_date: Optional[str] = None  # 選填，預設今天
    name: Optional[str] = None  # 選填，自動生成 "諮詢 - 日期時間"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    transcript: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    reflection: Optional[dict] = None
    recordings: Optional[List[RecordingSegment]] = None
    # Island Parents - 練習情境
    scenario: Optional[str] = None  # 情境標題
    scenario_description: Optional[str] = None  # 情境描述
    session_mode: Optional[
        str
    ] = None  # 模式：practice (對話練習) / emergency (親子溝通)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "case_id": "123e4567-e89b-12d3-a456-426614174000",
                    "session_date": "2025-01-15",
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 11:30",
                    "notes": "個案對職涯選擇表現出積極態度",
                    "session_mode": "practice",
                    "scenario": "功課問題",
                    "scenario_description": "孩子回家後不願意寫功課",
                }
            ]
        }
    }


class SessionUpdateRequest(BaseModel):
    """更新會談記錄請求"""

    session_date: Optional[str] = None
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    transcript: Optional[str] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None
    reflection: Optional[dict] = None
    recordings: Optional[List[RecordingSegment]] = None
    # Island Parents - 練習情境
    scenario: Optional[str] = None
    scenario_description: Optional[str] = None
    session_mode: Optional[str] = None  # 模式：practice / emergency


class SessionResponse(BaseModel):
    """會談記錄響應"""

    id: UUID
    client_id: UUID
    client_name: Optional[str] = None
    client_code: Optional[str] = None
    case_id: UUID
    session_number: int
    session_date: datetime
    name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    transcript_text: Optional[str] = None
    summary: Optional[str] = None
    duration_minutes: Optional[int]
    notes: Optional[str]
    reflection: Optional[dict] = None
    recordings: Optional[List[RecordingSegment]] = None
    # Island Parents - 練習情境
    scenario: Optional[str] = None
    scenario_description: Optional[str] = None
    session_mode: Optional[str] = None  # 模式：practice / emergency
    has_report: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    """會談記錄列表響應"""

    total: int
    items: List[SessionResponse]


# Timeline schemas
class TimelineSessionItem(BaseModel):
    """單次會談的時間線資訊"""

    session_id: UUID
    session_number: int
    date: str
    time_range: Optional[str] = None
    summary: Optional[str] = None
    has_report: bool
    report_id: Optional[UUID] = None


class SessionTimelineResponse(BaseModel):
    """會談歷程時間線響應"""

    client_id: UUID
    client_name: str
    client_code: str
    total_sessions: int
    sessions: List[TimelineSessionItem]


# Reflection schemas
class ReflectionRequest(BaseModel):
    """諮詢師反思請求"""

    reflection: dict


class ReflectionResponse(BaseModel):
    """諮詢師反思響應"""

    session_id: UUID
    reflection: Optional[dict] = None
    updated_at: datetime


# Legacy schemas (for backward compatibility)
class SessionBase(BaseSchema):
    session_date: datetime
    duration_minutes: Optional[int] = None
    room_number: Optional[str] = None
    notes: Optional[str] = None
    key_points: Optional[str] = None


class SessionCreate(SessionBase):
    case_id: UUID
    session_number: int


class AudioUpload(BaseSchema):
    session_id: UUID
    file_name: str
    file_size: int
    duration_seconds: Optional[int] = None


class KeywordAnalysisRequest(BaseModel):
    """Request for session-based keyword analysis (RESTful)."""

    transcript_segment: str = Field(
        ...,
        min_length=1,
        description="Partial transcript text to analyze",
    )

    @field_validator("transcript_segment")
    @classmethod
    def validate_transcript(cls, v: str) -> str:
        """Validate transcript segment is not empty."""
        if not v or not v.strip():
            raise ValueError("Transcript segment cannot be empty")
        return v.strip()


class KeywordAnalysisResponse(BaseModel):
    """Response for session-based keyword analysis with counselor insights."""

    keywords: list[str] = Field(description="Extracted keywords from transcript")
    categories: list[str] = Field(description="Categories of extracted keywords")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score of keyword extraction",
    )
    counselor_insights: str = Field(
        description="Insights and reminders for the counselor based on the analysis"
    )


class AnalysisLogEntry(BaseModel):
    """Single analysis log entry"""

    log_index: int = Field(description="Index of this log in the array (0-based)")
    analyzed_at: str = Field(description="ISO 8601 timestamp of analysis")
    transcript_segment: str = Field(description="Analyzed transcript segment")
    keywords: list[str] = Field(description="Extracted keywords")
    categories: list[str] = Field(description="Categories")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    counselor_insights: str = Field(description="Counselor insights")
    counselor_id: str = Field(description="ID of counselor who performed analysis")
    fallback: Optional[bool] = Field(
        default=False, description="Whether this was a fallback analysis"
    )


class AnalysisLogsResponse(BaseModel):
    """Response for GET analysis logs"""

    session_id: UUID
    total_logs: int = Field(description="Total number of analysis logs")
    logs: list[AnalysisLogEntry] = Field(description="List of analysis logs")


# =============================================================================
# Emotion Analysis Schemas (Island Parents - Real-time Emotion Feedback)
# =============================================================================


class EmotionFeedbackRequest(BaseModel):
    """
    Request for real-time emotion analysis of parent-child interaction.

    Used by Island Parents tenant to provide instant feedback on parent's
    communication tone and suggest gentle guidance.
    """

    context: str = Field(
        ...,
        min_length=1,
        description="對話上下文（可能包含多輪對話）",
    )
    target: str = Field(
        ...,
        min_length=1,
        description="要分析的目標句子",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "context": "小明：我今天考試不及格\n媽媽：你有認真準備嗎？",
                    "target": "你就是不用功！",
                }
            ]
        }
    }


class EmotionFeedbackResponse(BaseModel):
    """
    Response from emotion analysis with traffic light level and guidance hint.

    Level:
    - 1 (綠燈): 良好溝通，語氣平和、具同理心
    - 2 (黃燈): 警告，語氣稍顯急躁但未失控
    - 3 (紅燈): 危險，語氣激動、可能傷害親子關係

    Hint: 簡短引導語 (≤17 字)，具體、可行、同理
    """

    level: int = Field(
        ...,
        ge=1,
        le=3,
        description="情緒層級: 1=綠燈（良好）, 2=黃燈（警告）, 3=紅燈（危險）",
    )
    hint: str = Field(
        ...,
        max_length=17,
        description="引導語，最多 17 字",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"level": 3, "hint": "試著同理孩子的挫折感"},
                {"level": 2, "hint": "深呼吸，用平和語氣重述"},
                {"level": 1, "hint": "很好的同理心表達"},
            ]
        }
    }


# =============================================================================
# Deep Analysis Response
# =============================================================================


class DeepAnalysisResponse(BaseModel):
    """Deep analysis response for session safety assessment"""

    safety_level: SafetyLevel = Field(..., description="Safety level (green/yellow/red)")
    display_text: str = Field(
        ..., min_length=4, max_length=20, description="Short status display text"
    )
    quick_suggestion: str = Field(
        ..., min_length=5, max_length=20, description="Quick action suggestion"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "safety_level": "green",
                    "display_text": "對話安全",
                    "quick_suggestion": "繼續保持良好互動",
                }
            ]
        }
    }
