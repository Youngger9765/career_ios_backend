"""
Realtime STT Counseling Schemas
用於即時語音轉文字諮詢輔助功能
"""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


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
    session_id: str = Field(default="", description="會談 session ID（用於 cache key）")
    provider: str = Field(
        default="gemini", description="LLM provider: 'gemini' or 'codeer'"
    )
    codeer_model: str = Field(
        default="gpt5-mini",
        description="Codeer model selection (when provider='codeer'): 'claude-sonnet', 'gemini-flash', or 'gpt5-mini'",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """驗證 provider 只能是 gemini 或 codeer"""
        if v not in ["gemini", "codeer"]:
            raise ValueError("provider must be 'gemini' or 'codeer'")
        return v

    @field_validator("codeer_model")
    @classmethod
    def validate_codeer_model(cls, v: str) -> str:
        """驗證 codeer_model 只能是支持的模型"""
        valid_models = [
            "claude-sonnet",
            "claude",
            "gemini-flash",
            "gemini",
            "gpt5-mini",
            "gpt5",
            "gpt",
        ]
        if v.lower() not in valid_models:
            raise ValueError(
                f"codeer_model must be one of: {', '.join(['claude-sonnet', 'gemini-flash', 'gpt5-mini'])}"
            )
        return v.lower()

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


class CodeerTokenMetadata(BaseModel):
    """Codeer token usage metadata"""

    total_prompt_tokens: int = Field(default=0, description="Total prompt tokens used")
    total_completion_tokens: int = Field(
        default=0, description="Total completion tokens used"
    )
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_calls: int = Field(default=0, description="Total API calls")


class ProviderMetadata(BaseModel):
    """Provider performance metadata"""

    provider: str = Field(..., description="LLM provider used")
    latency_ms: int = Field(..., description="Response latency in milliseconds")
    model: str = Field(default="", description="Model name")
    codeer_token_usage: CodeerTokenMetadata | None = Field(
        default=None, description="Codeer token usage (if provider='codeer')"
    )


class RealtimeAnalyzeResponse(BaseModel):
    """即時分析回應（AI 督導建議）"""

    safety_level: SafetyLevel = Field(
        ..., description="Safety level: red (high risk), yellow (warning), green (safe)"
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


class ImprovementSuggestion(BaseModel):
    """改進建議"""

    issue: str = Field(..., description="需要改進的地方")
    suggestion: str = Field(..., description="具體建議或換句話說")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "issue": "使用威脅語氣「你再不寫我就打你」",
                    "suggestion": "可以換成：「我看到你現在不想寫功課，可以跟我說說為什麼嗎？」",
                }
            ]
        }
    }


class ParentsReportResponse(BaseModel):
    """家長對話報告回應"""

    summary: str = Field(..., description="對話主題與回饋摘要（中性立場）")
    highlights: List[str] = Field(..., description="溝通亮點列表")
    improvements: List[ImprovementSuggestion] = Field(..., description="改進建議列表")
    rag_references: List[RAGSource] = Field(..., description="相關親子教養知識庫參考")
    timestamp: str = Field(..., description="生成時間戳（ISO 8601 格式）")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "這次對話主要討論孩子不寫功課的問題，家長表達了挫折與擔心。",
                    "highlights": [
                        "嘗試理解孩子的感受",
                        "願意花時間陪伴孩子討論問題",
                        "認知到情緒管理的重要性",
                    ],
                    "improvements": [
                        {
                            "issue": "使用威脅語氣「你再不寫我就打你」",
                            "suggestion": "可以換成：「我看到你現在不想寫功課，可以跟我說說為什麼嗎？」",
                        }
                    ],
                    "rag_references": [
                        {
                            "title": "正向教養：如何不打不罵教孩子",
                            "content": "正向教養強調尊重孩子，透過連結建立合作關係...",
                            "score": 0.85,
                            "theory": "正向教養",
                        }
                    ],
                    "timestamp": "2025-12-26T10:00:00Z",
                }
            ]
        }
    }
