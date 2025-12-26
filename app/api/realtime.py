"""
Realtime STT Counseling API
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.realtime import (
    CacheMetadata,
    CodeerTokenMetadata,
    CounselingMode,
    ImprovementSuggestion,
    ParentsReportRequest,
    ParentsReportResponse,
    ProviderMetadata,
    RAGSource,
    RealtimeAnalyzeRequest,
    RealtimeAnalyzeResponse,
    SafetyLevel,
)
from app.services.cache_manager import CacheManager
from app.services.gbq_service import gbq_service
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.rag_chat_service import RAGChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime Counseling"])

# Initialize services
gemini_service = GeminiService()
openai_service = OpenAIService()
cache_manager = CacheManager()

# Safety assessment sliding window configuration
SAFETY_WINDOW_SPEAKER_TURNS = (
    10  # Number of recent speaker turns to evaluate (~1 minute)
)
SAFETY_WINDOW_CHARACTERS = 300  # Fallback: character count for sliding window

# Annotated window configuration for AI safety assessment
ANNOTATED_SAFETY_WINDOW_TURNS = (
    5  # Last 5-10 turns highlighted for AI safety evaluation
)

# System instruction for cache (固定不變的部分)
CACHE_SYSTEM_INSTRUCTION = """你是專業諮詢督導，分析即時諮詢對話。你的角色是站在案主與諮詢師之間，提供溫暖、同理且具體可行的專業建議。

【角色定義】CRITICAL - 必須嚴格遵守：
- "counselor" = 諮詢師/輔導師（專業助人者，提供協助的一方）
- "client" = 案主/個案/家長（求助者，有困擾需要協助的一方）
- 所有問題、困擾、症狀都是「案主/個案」面臨的，不是諮詢師的問題
- 分析焦點：案主的狀況、需求、風險
- 建議對象：給諮詢師的專業建議（如何協助案主）

【分析範圍】CRITICAL - 必須嚴格遵守：
🎯 **主要分析焦點**：最新一分鐘內的對話內容
   - 你會收到完整的對話記錄（可能長達數十分鐘）
   - 但你的分析必須聚焦在「最後出現的對話」（最新一分鐘）
   - 前面的對話僅作為背景脈絡參考，幫助你理解前因後果

【安全等級評估規則】CRITICAL - 必須嚴格遵守：
⚠️ **僅根據「【最近對話 - 用於安全評估】」區塊判斷安全等級**
   - 標註區塊顯示最近 5-10 個對話輪次
   - 不要因為完整逐字稿中出現過的危險詞就評估為高風險
   - 如果最近對話已經緩和、正向，即使之前有危險內容，也應評估為較低風險
   - 安全等級反映當前狀態，不是歷史狀態

🎯 **建議內容**：
   - 可以參考完整對話歷史，提供更有深度的建議
   - 但要聚焦在最近對話的當前狀態

【核心原則】同理優先、溫和引導、具體行動：

1. **同理與理解為先**
   - 永遠先理解與同理案主（家長）的感受和處境
   - 認可教養壓力、情緒失控是正常的人性反應
   - 避免批判、指責或讓案主感到被否定

2. **溫和、非批判的語氣**
   - ❌ 禁止用語：「表達出對孩子使用身體暴力的衝動」「可能造成傷害」「不當管教」
   - ✅ 建議用語：「理解到在教養壓力下，父母有時會感到情緒失控是很正常的」
   - ✅ 使用：「可以考慮」「或許」「試試看」等柔和引導詞
   - ✅ 焦點放在「如何調整」而非「哪裡做錯」

3. **具體、簡潔的建議**
   - 建議要具體可行，但保持簡短（不超過 50 字）
   - 避免抽象概念，用具體做法
   - 不要冗長的步驟說明或對話範例

【輸出格式】請提供以下 JSON 格式回應：

{
  "summary": "案主處境簡述（1-2 句）",
  "alerts": [
    "💡 同理案主感受（1 句）",
    "⚠️ 需關注的部分（1 句）"
  ],
  "suggestions": [
    "💡 核心建議（簡短，< 50 字）",
    "💡 具體做法（簡短，< 50 字）"
  ]
}

【語氣要求】溫和、同理、簡潔，避免批判或過度說教

【RAG 使用要求】CRITICAL - 必須嚴格遵守：
- 當分析涉及親子教養、兒童發展、管教策略等專業知識時，必須參考上方提供的「📚 相關親子教養知識庫內容」
- 優先使用知識庫中的理論、方法、建議（如正向教養、情緒教養等）
- 不要僅憑一般常識或想像回答專業問題
- 如果知識庫內容相關，請在建議中融入（不需明確標注來源）
"""

# Parenting-related keywords that trigger RAG search
# Keywords organized by category for better maintainability
PARENTING_KEYWORDS = [
    # === 基本詞彙 (Basic Terms) ===
    "親子",
    "孩子",
    "小孩",
    "兒童",
    "青少年",
    "教養",
    "育兒",
    "管教",
    "父母",
    "媽媽",
    "爸爸",
    "親職",
    "家庭",
    # === 情緒相關 (Emotions) ===
    "情緒",
    "生氣",
    "憤怒",
    "難過",
    "傷心",
    "害怕",
    "焦慮",
    "擔心",
    "壓力",
    "哭",
    "哭泣",
    "失望",
    "挫折",
    # === 行為問題 (Behavior Issues) ===
    "行為",
    "打人",
    "攻擊",
    "拒絕",
    "發脾氣",
    "叛逆",
    "不聽話",
    "頂嘴",
    # === 日常場景 (Daily Situations) ===
    "功課",
    "作業",
    "睡覺",
    "睡眠",
    "吃飯",
    "用餐",
    "收玩具",
    "刷牙",
    # === 人際關係 (Relationships) ===
    "手足",
    "兄弟",
    "姊妹",
    "朋友",
    "同學",
    "老師",
    "衝突",
    "爭吵",
    # === 教養概念 (Parenting Concepts) ===
    "溝通",
    "陪伴",
    "關係",
    "鼓勵",
    "讚美",
    "處罰",
    "獎勵",
    "尊重",
    "責任",
    "界限",
    "規則",
    "選擇",
    "後果",
    "分享",
    # === 發展相關 (Development) ===
    "發展",
    "成長",
    "學習",
    "青春期",
    "教育",
    "獨立",
    "自律",
    "自信",
    "自尊",
    # === 依附相關 (Attachment) ===
    "依附",
    "安全感",
    "信任",
    "分離",
    "連結",
]


def _detect_parenting_keywords(transcript: str) -> bool:
    """Detect if transcript contains parenting-related keywords.

    Args:
        transcript: The transcript text

    Returns:
        True if parenting keywords detected, False otherwise
    """
    transcript_lower = transcript.lower()
    for keyword in PARENTING_KEYWORDS:
        if keyword in transcript_lower:
            logger.info(f"Parenting keyword detected: {keyword}")
            return True
    return False


def _detect_parenting_theory(title: str) -> str:
    """Detect which parenting theory a document belongs to based on title.

    Args:
        title: Document title

    Returns:
        Theory name in Chinese (e.g., "正向教養", "情緒教養")
    """
    # Theory keyword mappings (Chinese, English, and file name patterns)
    theory_mappings = {
        "正向教養": ["正向教養", "Positive Discipline", "positive_discipline"],
        "情緒教養": [
            "情緒教養",
            "Emotional Coaching",
            "Emotion Coaching",
            "emotional_coaching",
        ],
        "依附理論": ["依附理論", "Attachment Theory", "attachment_theory"],
        "認知發展理論": ["認知發展", "Cognitive Development", "cognitive_development"],
        "自我決定論": ["自我決定", "Self-Determination", "self_determination"],
    }

    # Check each theory's keywords (case-insensitive)
    title_lower = title.lower()
    for theory_name, keywords in theory_mappings.items():
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return theory_name

    # Default if no match found
    return "其他"


async def _search_rag_knowledge(
    transcript: str, db: Session, top_k: int = 3, similarity_threshold: float = 0.5
) -> List[RAGSource]:
    """Search RAG knowledge base for relevant parenting content.

    Args:
        transcript: The transcript text to search
        db: Database session
        top_k: Number of top results to return
        similarity_threshold: Minimum similarity score (default 0.5)
            Note: Lowered from 0.7 to 0.5 based on production data analysis.
            Real-world similarity scores for relevant content typically max out
            at ~0.54-0.59, so 0.7 was too strict and prevented retrieval.

    Returns:
        List of RAG sources with title, content, and score
    """
    try:
        # Initialize RAG service
        rag_service = RAGChatService(db=db)

        # Generate embedding for transcript
        query_embedding = await openai_service.create_embedding(transcript)

        # Search similar chunks with parenting category filter
        rows = await rag_service.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            category="parenting",  # Filter for parenting documents only
        )

        # Build RAG sources response
        rag_sources = []
        for row in rows:
            # Detect theory from document title
            theory = _detect_parenting_theory(row.document_title)

            rag_sources.append(
                RAGSource(
                    title=row.document_title,
                    content=row.text[:300],  # Truncate to 300 chars
                    score=round(float(row.similarity_score), 2),
                    theory=theory,
                )
            )

        logger.info(f"RAG search found {len(rag_sources)} relevant sources")
        return rag_sources

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        # Return empty list on error (fallback)
        return []


def _assess_safety_level(transcript: str, speakers: List[dict]) -> SafetyLevel:
    """Assess safety level based on RECENT conversation (sliding window).

    Only evaluates the last ~1 minute of dialogue to allow rapid safety relaxation.
    This prevents dangerous keywords from earlier in the conversation from keeping
    the safety level elevated indefinitely.

    Safety levels:
    - RED: Violent language, extreme emotions, crisis indicators (high risk)
    - YELLOW: Escalating conflict, frustration, raised emotions (warning)
    - GREEN: Calm, positive interaction (safe)

    Args:
        transcript: The full conversation transcript (cumulative)
        speakers: List of speaker segments (used for sliding window)

    Returns:
        SafetyLevel enum: red, yellow, or green
    """
    # Strategy: Use last N speaker segments (approximate 1 minute)
    # Extract recent transcript from speakers array
    if speakers and len(speakers) > 0:
        # Take last N segments to approximate 1 minute of conversation
        recent_speakers = speakers[-SAFETY_WINDOW_SPEAKER_TURNS:]
        recent_transcript = "\n".join(
            [
                f"{seg.get('speaker', 'unknown')}: {seg.get('text', '')}"
                for seg in recent_speakers
            ]
        )
        logger.info(
            f"Using sliding window: last {len(recent_speakers)} speaker turns "
            f"({len(recent_transcript)} chars)"
        )
    else:
        # Fallback: use last N characters (approximate 1 minute)
        if len(transcript) > SAFETY_WINDOW_CHARACTERS:
            recent_transcript = transcript[-SAFETY_WINDOW_CHARACTERS:]
            logger.info(
                f"Using fallback window: last {SAFETY_WINDOW_CHARACTERS} characters"
            )
        else:
            recent_transcript = transcript
            logger.info("Using full transcript (shorter than window)")

    # Convert to lowercase for keyword matching
    text_lower = recent_transcript.lower()

    # RED indicators (high risk) - violence, extreme emotions, crisis
    red_keywords = [
        "打死",
        "滾",
        "殺",
        "恨死",
        "暴力",
        "打人",
        "揍",
        "受不了",
        "不想活",
        "去死",
    ]
    for keyword in red_keywords:
        if keyword in text_lower:
            logger.info(
                f"Safety level: RED detected (keyword: '{keyword}' in recent window)"
            )
            return SafetyLevel.red

    # YELLOW indicators (medium risk) - frustration, escalating conflict
    yellow_keywords = [
        "氣死",
        "煩死",
        "受夠",
        "不聽話",
        "說謊",
        "快瘋",
        "崩潰",
        "發火",
    ]
    for keyword in yellow_keywords:
        if keyword in text_lower:
            logger.info(
                f"Safety level: YELLOW detected (keyword: '{keyword}' in recent window)"
            )
            return SafetyLevel.yellow

    # GREEN (safe/positive) - default if no risk indicators found in recent window
    logger.info("Safety level: GREEN (calm/positive interaction in recent window)")
    return SafetyLevel.green


def _build_annotated_transcript(transcript: str, speakers: List[dict]) -> str:
    """Build annotated transcript with recent window highlighted for safety assessment.

    Args:
        transcript: Full conversation transcript
        speakers: List of speaker segments

    Returns:
        Annotated transcript with recent window marked for safety evaluation
    """
    # Build full transcript
    full_transcript = "\n".join(
        [f"{seg.get('speaker', 'unknown')}: {seg.get('text', '')}" for seg in speakers]
    )

    # Extract recent window for annotation
    recent_speakers = (
        speakers[-ANNOTATED_SAFETY_WINDOW_TURNS:]
        if len(speakers) > ANNOTATED_SAFETY_WINDOW_TURNS
        else speakers
    )
    recent_transcript = "\n".join(
        [
            f"{seg.get('speaker', 'unknown')}: {seg.get('text', '')}"
            for seg in recent_speakers
        ]
    )

    # Construct annotated prompt
    annotated = f"""完整對話逐字稿（供參考，理解背景脈絡）：
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
（請根據此區塊判斷當前安全等級）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{recent_transcript}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CRITICAL: 安全等級評估請只根據「【最近對話 - 用於安全評估】」區塊判斷，
完整對話僅作為理解脈絡參考。如果最近對話已緩和，即使之前有危險內容，
也應評估為較低風險。"""

    return annotated


def _build_emergency_prompt(transcript: str, rag_context: str) -> str:
    """Build simplified prompt for emergency mode using 200 expert suggestions.

    Emergency mode: Select 1-2 suggestions from expert pool, organized with Bridge technique.
    Bridge structure for RED scenarios: 穩住 → 同理 → 修正

    Args:
        transcript: The conversation transcript
        rag_context: RAG knowledge context (if available)

    Returns:
        Simplified prompt for emergency situations with expert suggestions
    """
    from app.config.parenting_suggestions import (
        GREEN_SUGGESTIONS,
        RED_SUGGESTIONS,
        YELLOW_SUGGESTIONS,
    )

    # Format suggestion lists for prompt
    green_list = "\n".join([f"  - {s}" for s in GREEN_SUGGESTIONS])
    yellow_list = "\n".join([f"  - {s}" for s in YELLOW_SUGGESTIONS])
    red_list = "\n".join([f"  - {s}" for s in RED_SUGGESTIONS])

    prompt = f"""你是親子諮詢 AI 督導。緊急模式 - 從專家建議中選 1-2 句！

【情境】
{transcript}

【專家建議句庫】請從以下 200 句專家建議中選擇最符合當前對話的：

🟢 綠色｜對話安全（選 1-2 句）：
{green_list}

🟡 黃色｜需要調整（選 1-2 句）：
{yellow_list}

🔴 紅色｜立刻修正（選 1-2 句）：
{red_list}

【分析步驟】：
1. 判斷對話安全等級（green/yellow/red）
   - green: 正向互動，家長有同理心，語氣溫和尊重
   - yellow: 有挫折感但仍可控，語氣開始緊繃或帶防衛
   - red: 威脅、暴力語言、極端情緒、可能造成傷害
2. 從對應顏色的建議句中選出最符合的 1-2 句
3. 建議必須是原句，不要改寫或自創

【Bridge 技巧】請按照以下結構組織回饋：
- 🟢 綠色：讚美 → 橋樑 → 延伸
- 🟡 黃色：肯定 → 提醒 → 替代
- 🔴 紅色：穩住 → 同理 → 修正（最重要！）

【紅色燈號的三階段設計】：
1. 先穩住：「理解在教養壓力下，情緒失控是很正常的」
2. 降低防衛：「你一定也很辛苦，想要孩子好但不知道怎麼做」
3. 再提醒：「這句話可能會讓孩子感到害怕，我們可以試試這樣說...」

【輸出格式】JSON 格式，必須包含以下欄位：
{{
  "safety_level": "green|yellow|red",
  "suggestions": [
    "從專家建議中選的句子1",
    "從專家建議中選的句子2"
  ]
}}

CRITICAL 規則：
- 只能選 1-2 個建議（從 200 句專家建議中選）
- 每句建議必須是原本的專家建議句，逐字照抄，不要自己改寫或創作
- 根據對話危險程度選擇對應顏色的建議
- 必須回傳 safety_level: "green" | "yellow" | "red"（此欄位必須存在）
- safety_level 和 suggestions 的顏色必須一致
- Emergency 模式重點：快速、精準、可立即執行

YOU MUST select 1-2 suggestions from the 200 expert suggestions above!
YOU MUST return safety_level field in JSON response!"""

    return prompt


def _build_practice_prompt(
    transcript: str, rag_context: str, annotated_transcript: str = ""
) -> str:
    """Build detailed prompt for practice mode using 200 expert suggestions (~1500 tokens).

    Practice mode: Select 3-4 suggestions from expert pool, organized with Bridge technique.
    Bridge structure varies by safety level (讚美→橋樑→延伸 for green, etc.)

    Args:
        transcript: The conversation transcript
        rag_context: RAG knowledge context (if available)
        annotated_transcript: Optional annotated transcript with safety window highlighted

    Returns:
        Detailed prompt for practice/learning situations with expert suggestions
    """
    from app.config.parenting_suggestions import (
        GREEN_SUGGESTIONS,
        RED_SUGGESTIONS,
        YELLOW_SUGGESTIONS,
    )

    # Format suggestion lists for prompt
    green_list = "\n".join([f"  - {s}" for s in GREEN_SUGGESTIONS])
    yellow_list = "\n".join([f"  - {s}" for s in YELLOW_SUGGESTIONS])
    red_list = "\n".join([f"  - {s}" for s in RED_SUGGESTIONS])

    # Use annotated transcript if provided, otherwise fall back to plain transcript
    dialogue_content = annotated_transcript if annotated_transcript else transcript

    # Use existing detailed prompt (same as CACHE_SYSTEM_INSTRUCTION style)
    prompt = f"""你是專業諮詢督導，分析即時諮詢對話。你的角色是站在案主與諮詢師之間，提供溫暖、同理且具體可行的專業建議。

【對話內容】
{dialogue_content}

【相關親子教養知識庫】
{rag_context if rag_context else "（無相關知識庫內容）"}

【專家建議句庫】請從以下 200 句專家建議中選擇 3-4 句最符合當前對話的：

🟢 綠色｜對話安全（選 3-4 句）：
{green_list}

🟡 黃色｜需要調整（選 3-4 句）：
{yellow_list}

🔴 紅色｜立刻修正（選 3-4 句）：
{red_list}

【分析步驟】：
1. 判斷對話安全等級（green/yellow/red）
   - green: 正向互動，家長有同理心，語氣溫和尊重
   - yellow: 有挫折感但仍可控，語氣開始緊繃或帶防衛
   - red: 威脅、暴力語言、極端情緒、可能造成傷害
2. 從對應顏色的建議句中選出最符合的 3-4 句
3. 建議必須是原句，不要改寫或自創

【Bridge 技巧】請按照以下結構組織回饋：
- 🟢 綠色：讚美 → 橋樑 → 延伸
- 🟡 黃色：肯定 → 提醒 → 替代
- 🔴 紅色：穩住 → 同理 → 修正（最重要！）

【紅色燈號的三階段設計】：
1. 先穩住：「理解在教養壓力下，情緒失控是很正常的」
2. 降低防衛：「你一定也很辛苦，想要孩子好但不知道怎麼做」
3. 再提醒：「這句話可能會讓孩子感到害怕，我們可以試試這樣說...」

【核心原則】同理優先、溫和引導、具體行動：

1. **同理與理解為先**
   - 永遠先理解與同理案主（家長）的感受和處境
   - 認可教養壓力、情緒失控是正常的人性反應
   - 避免批判、指責或讓案主感到被否定

2. **溫和、非批判的語氣**
   - ❌ 禁止用語：「表達出對孩子使用身體暴力的衝動」「可能造成傷害」「不當管教」
   - ✅ 建議用語：「理解到在教養壓力下，父母有時會感到情緒失控是很正常的」
   - ✅ 使用：「可以考慮」「或許」「試試看」等柔和引導詞

3. **具體、實用的建議**
   - 從 200 句專家建議中選擇最符合的
   - 避免抽象概念，用具體做法
   - 如果知識庫有相關內容，融入專業理論

【輸出格式】JSON 格式，必須包含以下欄位：

{{
  "safety_level": "green|yellow|red",
  "summary": "案主處境簡述（2-3 句）",
  "alerts": [
    "💡 同理案主感受",
    "⚠️ 需關注的部分",
    "✅ 正向的部分"
  ],
  "suggestions": [
    "從專家建議中選的句子1",
    "從專家建議中選的句子2",
    "從專家建議中選的句子3",
    "從專家建議中選的句子4"
  ]
}}

CRITICAL 規則：
- 必須選 3-4 個建議（從 200 句專家建議中選）
- 每句建議必須是原本的專家建議句，逐字照抄，不要自己改寫或創作
- 根據對話危險程度選擇對應顏色的建議
- 必須回傳 safety_level: "green" | "yellow" | "red"（此欄位必須存在）
- safety_level 和 suggestions 的顏色必須一致
- Practice 模式重點：深度分析、促進學習成長

【語氣要求】溫和、同理、專業，提供深度分析幫助家長學習成長。

YOU MUST select 3-4 suggestions from the 200 expert suggestions above!
YOU MUST return safety_level field in JSON response!"""

    return prompt


def _calculate_gemini_cost(usage_metadata: dict) -> float:
    """Calculate estimated cost for Gemini API usage

    Gemini 2.5 Flash pricing (as of 2025):
    - Input: $0.000075 per 1K tokens
    - Output: $0.0003 per 1K tokens
    - Cached input: $0.00001875 per 1K tokens (75% discount)
    """
    prompt_tokens = usage_metadata.get("prompt_token_count", 0)
    completion_tokens = usage_metadata.get("candidates_token_count", 0)
    cached_tokens = usage_metadata.get("cached_content_token_count", 0)

    # Subtract cached tokens from prompt tokens
    non_cached_prompt = max(0, prompt_tokens - cached_tokens)

    # Calculate costs
    prompt_cost = (non_cached_prompt / 1000) * 0.000075
    cached_cost = (cached_tokens / 1000) * 0.00001875
    completion_cost = (completion_tokens / 1000) * 0.0003

    return prompt_cost + cached_cost + completion_cost


async def write_to_gbq_async(data: dict) -> None:
    """Write realtime analysis result to BigQuery asynchronously

    This is a wrapper function that catches all exceptions to prevent
    GBQ write failures from affecting API response.

    Args:
        data: Analysis data to write to BigQuery
    """
    try:
        await gbq_service.write_analysis_log(data)
    except Exception as e:
        # Log error but don't raise - GBQ failures should not block API
        logger.error(
            f"Failed to write to BigQuery (non-blocking): {str(e)}", exc_info=True
        )


async def _analyze_with_codeer(
    transcript: str,
    speakers: List[dict],
    rag_context: str,
    db: Session,
    session_id: str = "",
    model: str = "gpt5-mini",
    custom_prompt: str = "",
) -> dict:
    """Analyze transcript using Codeer 親子專家 agent.

    Args:
        transcript: Full transcript text
        speakers: List of speaker segments
        rag_context: RAG knowledge context
        db: Database session
        session_id: Session ID for session pooling (optional)
        model: Codeer model selection (claude-sonnet, gemini-flash, or gpt5-mini)

    Returns:
        Dict with summary, alerts, suggestions
    """
    import json

    from app.services.codeer_client import CodeerClient, get_codeer_agent_id
    from app.services.codeer_session_pool import get_codeer_session_pool

    # Get agent ID based on model selection
    try:
        agent_id = get_codeer_agent_id(model)
        logger.info(f"Using Codeer model: {model}, agent_id: {agent_id}")
    except Exception as e:
        logger.error(f"Failed to get Codeer agent ID: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Create client with longer timeout for analysis
    client = CodeerClient()
    # Extend timeout to 60 seconds for LLM response
    client.client.timeout = httpx.Timeout(60.0)

    try:
        # Use custom prompt if provided (for mode-based routing)
        # Otherwise, use default system instruction
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Build analysis prompt similar to Gemini's
            # Format: system instruction + RAG context + transcript
            prompt = f"""{CACHE_SYSTEM_INSTRUCTION}

{rag_context if rag_context else ""}

【對話內容】
{transcript}

請分析以上對話，提供 JSON 格式回應。
"""

        # Create or reuse chat session with selected agent
        if session_id:
            # Use session pool for reuse
            pool = get_codeer_session_pool()
            chat = await pool.get_or_create_session(
                session_id, client, agent_id=agent_id
            )
            logger.info(f"Using session pool for {session_id} with agent {agent_id}")
        else:
            # Fallback: create new chat with selected agent
            # Use microsecond precision + model name to ensure unique chat names
            import uuid

            unique_suffix = (
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
            )
            chat = await client.create_chat(
                name=f"Realtime-{model}-{unique_suffix}",
                agent_id=agent_id,
            )
            logger.info(
                f"Created new chat (no session_id) with agent {agent_id}: {chat['name']}"
            )

        # Send message to Codeer agent (non-streaming for now)
        # CRITICAL: Must pass agent_id to match the agent used to create the chat
        try:
            response = await client.send_message(
                chat_id=chat["id"], message=prompt, stream=False, agent_id=agent_id
            )
        except Exception as api_error:
            # Handle Codeer API errors (e.g., agent mismatch, timeout, rate limit)
            logger.error(f"Codeer send_message failed: {api_error}")
            return {
                "summary": "Codeer 分析失敗",
                "alerts": [f"⚠️ API 錯誤: {str(api_error)}"],
                "suggestions": ["💡 請檢查 Codeer API 連線或稍後再試"],
                "token_usage": None,
            }

        # Fetch token usage from the latest assistant message
        token_usage_data = None
        try:
            # Fetch latest messages (limit=10 to ensure we get assistant response)
            # The order is: [latest system, latest assistant, user, ...]
            messages = await client.list_chat_messages(chat_id=chat["id"], limit=10)
            if messages and len(messages) > 0:
                # Find the latest assistant message (role='assistant')
                assistant_message = None
                for msg in messages:
                    if msg.get("role") == "assistant":
                        assistant_message = msg
                        break

                # Extract token_usage from assistant message's meta.token_usage
                if (
                    assistant_message
                    and "meta" in assistant_message
                    and "token_usage" in assistant_message["meta"]
                    and assistant_message["meta"]["token_usage"] is not None
                ):
                    token_usage = assistant_message["meta"]["token_usage"]
                    token_usage_data = {
                        "total_prompt_tokens": token_usage.get(
                            "total_prompt_tokens", 0
                        ),
                        "total_completion_tokens": token_usage.get(
                            "total_completion_tokens", 0
                        ),
                        "total_tokens": token_usage.get("total_tokens", 0),
                        "total_calls": token_usage.get("total_calls", 0),
                    }
                    logger.info(f"Codeer token usage: {token_usage_data}")
                else:
                    logger.warning(
                        "No assistant message found or token_usage not available"
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch Codeer token usage: {e}")

        # Parse Codeer response
        # Codeer returns dict with 'content', 'text', or 'message' field
        try:
            # Extract text from response
            if isinstance(response, dict):
                response_text = (
                    response.get("content")
                    or response.get("text")
                    or response.get("message")
                    or str(response)
                )
            else:
                response_text = str(response)

            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                # Fallback: treat as plain text
                json_text = response_text

            analysis = json.loads(json_text)

            # Ensure required fields exist
            if "summary" not in analysis:
                analysis["summary"] = "分析結果"
            if "alerts" not in analysis:
                analysis["alerts"] = []
            if "suggestions" not in analysis:
                analysis["suggestions"] = []

            # Add token usage to analysis result
            analysis["token_usage"] = token_usage_data

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Codeer response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")

            # Fallback response
            return {
                "summary": "Codeer 回應解析失敗",
                "alerts": [f"⚠️ 無法解析回應: {str(e)}"],
                "suggestions": ["💡 請檢查 Codeer agent 設定"],
                "token_usage": token_usage_data,
            }

    finally:
        # Always close the client
        await client.close()


@router.post("/analyze", response_model=RealtimeAnalyzeResponse)
async def analyze_transcript(
    request: RealtimeAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Analyze realtime counseling transcript with AI supervision.

    Returns summary, alerts, and suggestions for the counselor based on
    the conversation in the past 60 seconds.

    Supports multiple LLM providers: Gemini (default) and Codeer.
    Gemini supports explicit context caching for improved performance.

    This is a demo feature with no authentication required.
    """
    import time

    start_time = time.time()

    try:
        # Convert speakers to dict format for service
        speakers_dict = [
            {"speaker": s.speaker, "text": s.text} for s in request.speakers
        ]

        # Assess safety level based on transcript content
        safety_level = _assess_safety_level(request.transcript, speakers_dict)
        logger.info(f"Safety level assessed: {safety_level.value}")

        # Detect parenting keywords and trigger RAG if needed
        rag_sources = []
        rag_context = ""

        if _detect_parenting_keywords(request.transcript):
            logger.info("Parenting keywords detected, triggering RAG search")
            # Phase 2.1 Enhancement: Increased top_k and lowered threshold for richer context
            rag_sources = await _search_rag_knowledge(
                transcript=request.transcript,
                db=db,
                top_k=7,  # Increased from 3 to 7 for more diverse suggestions
                similarity_threshold=0.35,  # Lowered from 0.5 to 0.35 (production scores ~0.54-0.59)
            )

            # Build RAG context for Gemini prompt
            if rag_sources:
                rag_context_parts = ["\n\n📚 相關親子教養知識庫內容（供參考）：\n"]
                for idx, source in enumerate(rag_sources, 1):
                    # Phase 2.1 Enhancement: Full content without truncation for complete context
                    rag_context_parts.append(
                        f"[{idx}] {source.title}: {source.content}"
                    )
                rag_context = "\n".join(rag_context_parts)

        # Build annotated transcript for safety assessment
        annotated_transcript = _build_annotated_transcript(
            request.transcript, speakers_dict
        )
        logger.info(
            f"Built annotated transcript with {len(speakers_dict)} total speakers, "
            f"last {min(ANNOTATED_SAFETY_WINDOW_TURNS, len(speakers_dict))} highlighted"
        )

        # Select prompt based on counseling mode
        if request.mode == CounselingMode.emergency:
            logger.info("Using EMERGENCY mode (simplified prompt)")
            custom_prompt = _build_emergency_prompt(annotated_transcript, rag_context)
        else:
            logger.info("Using PRACTICE mode (detailed prompt)")
            custom_prompt = _build_practice_prompt(
                request.transcript, rag_context, annotated_transcript
            )

        # Initialize variables
        analysis = {}
        cache_metadata = None
        provider_metadata = None

        # Route to appropriate provider
        if request.provider == "codeer":
            logger.info(
                f"Using Codeer provider for analysis (model: {request.codeer_model})"
            )
            analysis = await _analyze_with_codeer(
                transcript=request.transcript,
                speakers=speakers_dict,
                rag_context=rag_context,
                db=db,
                session_id=request.session_id,
                model=request.codeer_model,
                custom_prompt=custom_prompt,
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract token usage from analysis result
            codeer_token_metadata = None
            if analysis.get("token_usage"):
                token_data = analysis["token_usage"]
                codeer_token_metadata = CodeerTokenMetadata(
                    total_prompt_tokens=token_data.get("total_prompt_tokens", 0),
                    total_completion_tokens=token_data.get(
                        "total_completion_tokens", 0
                    ),
                    total_tokens=token_data.get("total_tokens", 0),
                    total_calls=token_data.get("total_calls", 0),
                )

            provider_metadata = ProviderMetadata(
                provider="codeer",
                latency_ms=latency_ms,
                model=f"親子專家 (codeer-{request.codeer_model})",
                codeer_token_usage=codeer_token_metadata,
            )

        # Default to Gemini
        else:
            logger.info("Using Gemini provider for analysis")

            # Use cache if enabled and session_id is provided
            if request.use_cache and request.session_id:
                try:
                    logger.info(
                        f"Cache enabled for session {request.session_id}, "
                        f"attempting to get or create cache"
                    )

                    # Get or create cache with accumulated transcript
                    cached_content, is_new = await cache_manager.get_or_create_cache(
                        session_id=request.session_id,
                        system_instruction=CACHE_SYSTEM_INSTRUCTION,
                        accumulated_transcript=request.transcript,
                        ttl_seconds=7200,  # 2 hours
                    )

                    # Check if content is too short for caching
                    if cached_content is None:
                        logger.info(
                            "Content too short for caching, using standard analysis"
                        )
                        analysis = await gemini_service.analyze_realtime_transcript(
                            transcript=request.transcript,
                            speakers=speakers_dict,
                            rag_context=rag_context,
                            custom_prompt=custom_prompt,
                        )
                        cache_metadata = CacheMetadata(
                            cache_name="",
                            cache_created=False,
                            cached_tokens=0,
                            prompt_tokens=0,
                            message="對話內容較短，尚未啟用 cache（需 >= 1024 tokens）",
                        )
                    else:
                        # Analyze with cache
                        analysis = await gemini_service.analyze_with_cache(
                            cached_content=cached_content,
                            transcript=request.transcript,
                            speakers=speakers_dict,
                            rag_context=rag_context,
                            custom_prompt=custom_prompt,
                        )

                        # Extract cache metadata from usage_metadata
                        usage_metadata = analysis.get("usage_metadata", {})
                        cache_metadata = CacheMetadata(
                            cache_name=cached_content.name,
                            cache_created=is_new,
                            cached_tokens=usage_metadata.get(
                                "cached_content_token_count", 0
                            ),
                            prompt_tokens=usage_metadata.get("prompt_token_count", 0),
                        )

                        logger.info(
                            f"Cache analysis completed. Cache created: {is_new}, "
                            f"Cached tokens: {cache_metadata.cached_tokens}, "
                            f"Prompt tokens: {cache_metadata.prompt_tokens}"
                        )

                except Exception as cache_error:
                    # Cache failed, fallback to non-cached analysis
                    logger.warning(
                        f"Cache analysis failed, falling back to non-cached: {cache_error}"
                    )
                    analysis = await gemini_service.analyze_realtime_transcript(
                        transcript=request.transcript,
                        speakers=speakers_dict,
                        rag_context=rag_context,
                        custom_prompt=custom_prompt,
                    )
                    cache_metadata = CacheMetadata(
                        cache_name="",
                        cache_created=False,
                        cached_tokens=0,
                        prompt_tokens=0,
                        error=str(cache_error),
                    )
            else:
                # Cache disabled or no session_id, use standard analysis
                logger.info("Cache disabled or no session_id, using standard analysis")
                analysis = await gemini_service.analyze_realtime_transcript(
                    transcript=request.transcript,
                    speakers=speakers_dict,
                    rag_context=rag_context,
                    custom_prompt=custom_prompt,
                )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            provider_metadata = ProviderMetadata(
                provider="gemini", latency_ms=latency_ms, model="gemini-2.5-flash"
            )

        # Extract safety_level from LLM response, default to "green" if not present
        safety_level = analysis.get("safety_level", "green")

        # Validate safety_level (must be green, yellow, or red)
        if safety_level not in ["green", "yellow", "red"]:
            logger.warning(
                f"Invalid safety_level '{safety_level}' from LLM, defaulting to 'green'"
            )
            safety_level = "green"

        # Calculate response time in milliseconds
        response_time_ms = int((time.time() - start_time) * 1000)

        # Prepare data for BigQuery (asynchronous write)
        gbq_data = {
            "id": str(uuid.uuid4()),
            "tenant_id": "island_parents",  # Fixed for web version
            "session_id": None,  # Web version has no session concept
            "analyzed_at": datetime.now(timezone.utc),
            "analysis_type": request.mode.value,  # "emergency" or "practice"
            "safety_level": safety_level,  # "green", "yellow", or "red"
            "matched_suggestions": analysis.get("suggestions", []),
            "transcript_segment": request.transcript[:1000],  # Limit to 1000 chars
            "response_time_ms": response_time_ms,
            "created_at": datetime.now(timezone.utc),
        }

        # Schedule GBQ write as background task (non-blocking)
        background_tasks.add_task(write_to_gbq_async, gbq_data)

        # Build response
        return RealtimeAnalyzeResponse(
            safety_level=safety_level,
            summary=analysis.get("summary", ""),
            alerts=analysis.get("alerts", []),
            suggestions=analysis.get("suggestions", []),
            time_range=request.time_range,
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=rag_sources,
            cache_metadata=cache_metadata,
            provider_metadata=provider_metadata,
        )
    except Exception as e:
        logger.error(f"Realtime analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elevenlabs-token")
async def generate_elevenlabs_token():
    """Generate a single-use token for ElevenLabs Speech-to-Text WebSocket.

    This endpoint calls ElevenLabs API to generate a temporary token that
    can be used by the frontend to connect to their WebSocket service.
    This approach keeps the API key secure on the server side.

    Returns:
        Dict with 'token' key containing the single-use token

    Raises:
        HTTPException: If token generation fails
    """
    try:
        # Get API key from environment
        api_key = os.getenv("ELEVEN_LABS_API_KEY")
        if not api_key:
            logger.error("ELEVEN_LABS_API_KEY not found in environment")
            raise HTTPException(
                status_code=500, detail="ElevenLabs API key not configured"
            )

        # Call ElevenLabs API to generate single-use token
        # Token type: "realtime_scribe" for speech-to-text WebSocket
        url = "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe"
        headers = {"xi-api-key": api_key}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, timeout=30.0)

            if response.status_code != 200:
                logger.error(
                    f"ElevenLabs API error: {response.status_code} - {response.text}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate token: {response.text}",
                )

            token_data = response.json()
            logger.info("Successfully generated ElevenLabs token")

            return {"token": token_data.get("token")}

    except httpx.TimeoutException:
        logger.error("Timeout calling ElevenLabs API")
        raise HTTPException(
            status_code=504, detail="Timeout generating token from ElevenLabs"
        )
    except Exception as e:
        logger.error(f"Token generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Token generation failed: {e}")


@router.post("/parents-report", response_model=ParentsReportResponse)
async def generate_parents_report(
    request: ParentsReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Generate a comprehensive parenting communication report.

    Analyzes parent-child conversation transcript and provides:
    1. Summary/theme of the conversation (neutral stance)
    2. Communication highlights (what went well)
    3. Areas for improvement with specific suggestions
    4. Relevant RAG references from parenting knowledge base

    This endpoint queries the parenting RAG knowledge base and uses
    Gemini to generate structured feedback.

    Results are persisted to BigQuery for analytics.
    """
    import json
    import time
    import uuid

    # Track timing for GBQ
    start_time = datetime.now(timezone.utc)
    rag_start_time = None
    rag_end_time = None
    llm_start_time = None
    llm_end_time = None

    try:
        # Step 1: Search RAG knowledge base for relevant parenting content
        logger.info("Searching RAG for parenting-related content")
        rag_start_time = time.time()
        rag_sources = await _search_rag_knowledge(
            transcript=request.transcript,
            db=db,
            top_k=5,  # Get more sources for comprehensive report
            similarity_threshold=0.5,
        )
        rag_end_time = time.time()
        rag_search_time_ms = int((rag_end_time - rag_start_time) * 1000)

        # Step 2: Build RAG context for prompt
        rag_context = ""
        if rag_sources:
            rag_context_parts = ["\n\n📚 相關親子教養知識庫內容（供參考）：\n"]
            for idx, source in enumerate(rag_sources, 1):
                rag_context_parts.append(
                    f"[{idx}] {source.title} ({source.theory}): {source.content}"
                )
            rag_context = "\n".join(rag_context_parts)
            logger.info(f"Found {len(rag_sources)} relevant RAG sources")
        else:
            logger.info("No RAG sources found, proceeding without context")

        # Step 3: Build analysis prompt
        analysis_prompt = f"""你是專業的親子溝通分析師，負責分析家長與孩子的對話，提供建設性的回饋。

【對話逐字稿】
{request.transcript}

{rag_context}

【分析要求】
請以中性、客觀、溫和的立場分析這次對話，提供以下 4 個部分：

1. **對話主題與摘要**（summary）
   - 簡短說明這次對話的主題是什麼
   - 中性立場，不批判，讓家長知道「這次到底說了什麼」
   - 1-2 句話即可

2. **溝通亮點**（highlights）
   - 列出家長在溝通中做得好的地方
   - 例如：展現同理心、願意傾聽、嘗試理解孩子感受等
   - 用正向、鼓勵的語氣
   - 3-5 個亮點，每個 ≤ 30 字

3. **改進建議**（improvements）
   - 指出值得更好的地方
   - 提供具體、可操作的建議或換句話說
   - 溫和、非批判的語氣
   - 每個建議包含：
     * issue: 需要改進的地方（具體描述，≤ 40 字）
     * suggestion: 具體建議或換句話說（≤ 60 字）
   - 2-4 個建議

4. **知識庫參考**（rag_references）
   - 已自動提供上方的 RAG 知識庫內容
   - 你不需要額外處理，只需在分析時參考即可

【語氣要求】
- 溫和、同理、建設性
- 避免批判或讓家長感到被指責
- 用「可以試試」「或許」「換個方式」等柔和引導詞
- 焦點放在「如何做得更好」而非「哪裡做錯」

【輸出格式】
請以 JSON 格式回應（不要用 markdown code block，直接輸出 JSON）：

{{
  "summary": "對話主題摘要（1-2 句）",
  "highlights": [
    "亮點1（≤ 30 字）",
    "亮點2（≤ 30 字）",
    "亮點3（≤ 30 字）"
  ],
  "improvements": [
    {{
      "issue": "需要改進的地方（≤ 40 字）",
      "suggestion": "具體建議或換句話說（≤ 60 字）"
    }}
  ]
}}

⚠️ 重要：請確保 JSON 格式正確，不要在最後一個元素後面加逗號（trailing comma）！

請開始分析。"""

        # Step 4: Call Gemini for analysis
        logger.info("Calling Gemini for report generation")
        llm_start_time = time.time()
        gemini_response = await gemini_service.chat_completion(
            prompt=analysis_prompt,
            temperature=0.7,  # Higher temperature for more natural language
            return_metadata=True,  # Get usage metadata for observability
        )
        llm_end_time = time.time()
        llm_call_time_ms = int((llm_end_time - llm_start_time) * 1000)

        # Extract response text and metadata
        llm_raw_response = gemini_response["text"]
        usage_metadata = gemini_response.get("usage_metadata", {})

        # Step 5: Parse Gemini response
        try:
            # Try to extract JSON from response
            if "```json" in llm_raw_response:
                json_start = llm_raw_response.find("```json") + 7
                json_end = llm_raw_response.find("```", json_start)
                json_text = llm_raw_response[json_start:json_end].strip()
            elif "{" in llm_raw_response:
                json_start = llm_raw_response.find("{")
                json_end = llm_raw_response.rfind("}") + 1
                json_text = llm_raw_response[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

            # Remove trailing commas from JSON (common LLM mistake)
            import re

            json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)

            analysis = json.loads(json_text)
            logger.info("Successfully parsed Gemini response")

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.error(f"Response text: {llm_raw_response[:500]}")
            raise HTTPException(
                status_code=500, detail="Failed to parse AI analysis response"
            )

        # Step 6: Build response
        improvements_list = [
            ImprovementSuggestion(
                issue=item.get("issue", ""), suggestion=item.get("suggestion", "")
            )
            for item in analysis.get("improvements", [])
        ]

        response = ParentsReportResponse(
            summary=analysis.get("summary", ""),
            highlights=analysis.get("highlights", []),
            improvements=improvements_list,
            rag_references=rag_sources,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Step 7: Prepare GBQ data for analytics
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine safety level based on number of improvements
        # More improvements = more issues = higher concern level
        safety_level = "green"  # Default
        if len(improvements_list) >= 4:
            safety_level = "yellow"  # Multiple areas to improve
        elif len(improvements_list) >= 2:
            safety_level = "green"  # Normal feedback
        # Note: parents_report doesn't have explicit "red" level like realtime

        # Prepare comprehensive GBQ data for observability
        gbq_data = {
            # IDs and metadata
            "id": str(uuid.uuid4()),
            "tenant_id": "island_parents",
            "session_id": request.session_id if request.session_id else None,
            "request_id": str(uuid.uuid4()),
            # Timestamps
            "analyzed_at": start_time,
            "start_time": start_time,
            "end_time": end_time,
            "created_at": end_time,
            # Analysis type and result
            "analysis_type": "parents_report",
            "safety_level": safety_level,
            "matched_suggestions": [
                f"{imp.issue} → {imp.suggestion}" for imp in improvements_list
            ],
            "analysis_result": analysis,  # Full parsed JSON
            # Input data
            "transcript": request.transcript,  # Store full transcript
            "speakers": None,  # Parents report doesn't have speaker info
            # Prompts
            "system_prompt": None,  # Gemini doesn't separate system/user in this call
            "user_prompt": analysis_prompt,  # The full prompt
            "prompt_template": "parents_report_v1",
            # RAG information
            "rag_used": len(rag_sources) > 0,
            "rag_query": request.transcript[
                :200
            ],  # First 200 chars used for RAG search
            "rag_documents": [
                {
                    "content": source.content[:500],
                    "source": source.title,
                    "similarity": source.score,
                }
                for source in rag_sources
            ]
            if rag_sources
            else None,
            "rag_sources": [source.title for source in rag_sources]
            if rag_sources
            else [],
            "rag_top_k": 5,
            "rag_similarity_threshold": 0.5,
            "rag_search_time_ms": rag_search_time_ms if rag_start_time else None,
            # Model information
            "provider": "gemini",
            "model_name": "gemini-2.5-flash",
            "model_version": "2.5",
            # Timing breakdown
            "duration_ms": duration_ms,
            "api_response_time_ms": duration_ms,
            "llm_call_time_ms": llm_call_time_ms if llm_start_time else None,
            # LLM response
            "llm_raw_response": llm_raw_response,
            # Token usage (from Gemini usage_metadata)
            "prompt_tokens": usage_metadata.get("prompt_token_count"),
            "completion_tokens": usage_metadata.get("candidates_token_count"),
            "total_tokens": usage_metadata.get("total_token_count"),
            "cached_tokens": usage_metadata.get("cached_content_token_count"),
            "estimated_cost_usd": _calculate_gemini_cost(usage_metadata)
            if usage_metadata
            else None,
            # Cache info (not used in parents_report)
            "use_cache": False,
            "cache_hit": None,
            "cache_key": None,
            "gemini_cache_ttl": None,
            # Mode
            "mode": "parents_report",
        }

        # Schedule GBQ write as background task (non-blocking)
        background_tasks.add_task(write_to_gbq_async, gbq_data)

        logger.info(
            f"Parents report generated successfully in {duration_ms}ms with {len(improvements_list)} improvements"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Parents report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
