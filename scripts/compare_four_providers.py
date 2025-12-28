"""
Complete Experiment Script: Compare Four LLM Providers

Tests four solutions with 8/9/10 minute transcripts:
1. Gemini with Explicit Context Caching (existing)
2. Codeer Claude Sonnet 4.5 (new)
3. Codeer Gemini 2.5 Flash (new)
4. Codeer GPT-5 Mini (new)

Comparison dimensions:
- Quality (structure, relevance, professionalism, completeness)
- Speed (latency in milliseconds)
- Cost (USD)

Usage:
    poetry run python scripts/compare_four_providers.py
    poetry run python scripts/compare_four_providers.py --provider gemini
    poetry run python scripts/compare_four_providers.py --duration 10
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import services (must be after path setup)
from app.services.cache_manager import CacheManager  # noqa: E402
from app.services.codeer_client import CodeerClient, get_codeer_agent_id  # noqa: E402
from app.services.codeer_session_pool import get_codeer_session_pool  # noqa: E402
from app.services.gemini_service import GeminiService  # noqa: E402

logger = logging.getLogger(__name__)
console = Console()

# System instruction (same as in realtime API)
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

【語氣要求】溫和、同理、簡潔，避免批判或過度說教。
"""


# ============================================================================
# Quality Evaluation Functions
# ============================================================================


def evaluate_structure(response: dict) -> float:
    """Evaluate response structure (0-100)

    Checks:
    - Has summary field with content
    - Has alerts field as list
    - Has suggestions field as list
    - All required fields present

    Args:
        response: Analysis response dictionary

    Returns:
        Score 0-100
    """
    score = 0.0

    # Check summary (25 points)
    if "summary" in response:
        if response["summary"] and len(response["summary"]) > 10:
            score += 25
        elif response["summary"]:
            score += 15  # Has summary but too short

    # Check alerts (25 points)
    if "alerts" in response:
        alerts = response["alerts"]
        if isinstance(alerts, list):
            if len(alerts) >= 2:
                score += 25
            elif len(alerts) == 1:
                score += 15
            elif len(alerts) == 0:
                score += 5  # Has field but empty

    # Check suggestions (25 points)
    if "suggestions" in response:
        suggestions = response["suggestions"]
        if isinstance(suggestions, list):
            if len(suggestions) >= 2:
                score += 25
            elif len(suggestions) == 1:
                score += 15
            elif len(suggestions) == 0:
                score += 5  # Has field but empty

    # Check JSON validity (25 points)
    required_fields = ["summary", "alerts", "suggestions"]
    if all(field in response for field in required_fields):
        score += 25

    return min(score, 100)


def evaluate_relevance(response: dict, transcript: str) -> float:
    """Evaluate response relevance to transcript (0-100)

    Checks:
    - Mentions parenting/child-related keywords
    - Mentions specific issues from transcript
    - Provides contextual suggestions

    Args:
        response: Analysis response dictionary
        transcript: Original transcript text

    Returns:
        Score 0-100
    """
    score = 0.0

    # Extract all text from response
    response_text = ""
    if "summary" in response:
        response_text += response.get("summary", "")
    if "alerts" in response:
        response_text += " ".join(response.get("alerts", []))
    if "suggestions" in response:
        response_text += " ".join(response.get("suggestions", []))

    response_text_lower = response_text.lower()
    transcript_lower = transcript.lower()

    # Parenting keywords (30 points)
    parenting_keywords = ["孩子", "小孩", "親子", "教養", "父母", "家長", "案主"]
    keyword_count = sum(1 for kw in parenting_keywords if kw in response_text_lower)
    score += min(keyword_count * 10, 30)

    # Issue-specific keywords (40 points)
    # Extract key topics from transcript
    issues = []
    if "功課" in transcript_lower or "作業" in transcript_lower:
        issues.append("功課")
    if "叛逆" in transcript_lower or "唱反調" in transcript_lower:
        issues.append("叛逆")
    if "吵架" in transcript_lower or "衝突" in transcript_lower:
        issues.append("吵架")
    if "手機" in transcript_lower or "電視" in transcript_lower:
        issues.append("3C")

    # Check if response mentions these issues
    if issues:
        mentioned_count = sum(1 for issue in issues if issue in response_text_lower)
        score += (mentioned_count / len(issues)) * 40
    else:
        score += 20  # Default if no clear issues

    # Actionable suggestions (30 points)
    actionable_keywords = ["試試", "可以", "建議", "或許", "嘗試", "考慮"]
    actionable_count = sum(1 for kw in actionable_keywords if kw in response_text_lower)
    score += min(actionable_count * 10, 30)

    return min(score, 100)


def evaluate_professionalism(response: dict) -> float:
    """Evaluate professional quality (0-100)

    Checks:
    - Uses professional counseling terminology
    - Provides specific actionable advice
    - Follows parenting principles
    - Avoids judgmental language

    Args:
        response: Analysis response dictionary

    Returns:
        Score 0-100
    """
    score = 0.0

    # Extract all text
    response_text = ""
    if "summary" in response:
        response_text += response.get("summary", "")
    if "alerts" in response:
        response_text += " ".join(response.get("alerts", []))
    if "suggestions" in response:
        response_text += " ".join(response.get("suggestions", []))

    # Professional terminology (30 points)
    professional_terms = [
        "同理",
        "理解",
        "感受",
        "情緒",
        "溝通",
        "引導",
        "關係",
        "陪伴",
        "支持",
        "尊重",
        "信任",
    ]
    term_count = sum(1 for term in professional_terms if term in response_text)
    score += min(term_count * 6, 30)

    # Avoids judgmental language (30 points)
    judgmental_phrases = [
        "不當",
        "錯誤",
        "不應該",
        "必須",
        "一定要",
        "暴力",
        "傷害",
        "批評",
        "指責",
    ]
    judgmental_count = sum(
        1 for phrase in judgmental_phrases if phrase in response_text
    )
    if judgmental_count == 0:
        score += 30
    elif judgmental_count <= 2:
        score += 15

    # Empathetic tone (20 points)
    empathy_keywords = ["理解", "感受", "辛苦", "不容易", "正常", "可以"]
    empathy_count = sum(1 for kw in empathy_keywords if kw in response_text)
    score += min(empathy_count * 5, 20)

    # Concrete suggestions (20 points)
    # Check if suggestions are concrete (not too abstract)
    suggestions = response.get("suggestions", [])
    if suggestions:
        concrete_count = 0
        for suggestion in suggestions:
            # Concrete suggestions usually have specific actions or numbers
            if any(
                word in suggestion
                for word in ["分鐘", "時間", "方式", "表", "規則", "步驟"]
            ):
                concrete_count += 1

        if concrete_count > 0:
            score += (concrete_count / len(suggestions)) * 20

    return min(score, 100)


def evaluate_completeness(response: dict) -> float:
    """Evaluate response completeness (0-100)

    Checks:
    - Number of alerts (3-5 is ideal)
    - Number of suggestions (2-3 is ideal)
    - Content length (not too short, not too long)
    - RAG sources cited (if applicable)

    Args:
        response: Analysis response dictionary

    Returns:
        Score 0-100
    """
    score = 0.0

    # Alerts count (30 points)
    alerts = response.get("alerts", [])
    if len(alerts) >= 3 and len(alerts) <= 5:
        score += 30
    elif len(alerts) == 2 or len(alerts) == 6:
        score += 20
    elif len(alerts) >= 1:
        score += 10

    # Suggestions count (30 points)
    suggestions = response.get("suggestions", [])
    if len(suggestions) >= 2 and len(suggestions) <= 3:
        score += 30
    elif len(suggestions) == 1 or len(suggestions) == 4:
        score += 20
    elif len(suggestions) >= 1:
        score += 10

    # Summary length (20 points)
    summary = response.get("summary", "")
    summary_len = len(summary)
    if summary_len >= 20 and summary_len <= 100:
        score += 20
    elif summary_len >= 10 and summary_len <= 150:
        score += 15
    elif summary_len > 0:
        score += 5

    # Average suggestion length (20 points)
    # Ideal: < 50 characters per suggestion
    if suggestions:
        avg_len = sum(len(s) for s in suggestions) / len(suggestions)
        if avg_len <= 50:
            score += 20
        elif avg_len <= 80:
            score += 15
        elif avg_len <= 120:
            score += 10

    return min(score, 100)


def evaluate_quality(response: dict, transcript: str) -> dict:
    """Comprehensive quality evaluation (0-100)

    Weighted scoring:
    - Structure: 20%
    - Relevance: 30%
    - Professionalism: 30%
    - Completeness: 20%

    Args:
        response: Analysis response dictionary
        transcript: Original transcript text

    Returns:
        Dict with total_score and breakdown
    """
    scores = {
        "structure": evaluate_structure(response),
        "relevance": evaluate_relevance(response, transcript),
        "professionalism": evaluate_professionalism(response),
        "completeness": evaluate_completeness(response),
    }

    total_score = (
        scores["structure"] * 0.2
        + scores["relevance"] * 0.3
        + scores["professionalism"] * 0.3
        + scores["completeness"] * 0.2
    )

    return {
        "total_score": round(total_score, 1),
        "breakdown": {k: round(v, 1) for k, v in scores.items()},
    }


# ============================================================================
# Cost Calculation Functions
# ============================================================================


def calculate_gemini_cost(usage_metadata: dict) -> dict:
    """Calculate Gemini API cost

    Gemini 3 Flash pricing (as of Dec 2025):
    - Input: $0.50 per 1M tokens ($0.0000005 per token)
    - Cached input: $0.125 per 1M tokens ($0.000000125 per token)
    - Output: $3.00 per 1M tokens ($0.000003 per token)

    Args:
        usage_metadata: Dict with token counts from Gemini response

    Returns:
        Dict with cost breakdown (USD)
    """
    # Extract token counts
    prompt_tokens = usage_metadata.get("prompt_token_count", 0)
    cached_tokens = usage_metadata.get("cached_content_token_count", 0)
    output_tokens = usage_metadata.get("candidates_token_count", 0)

    # Calculate costs (USD)
    input_cost = prompt_tokens * 0.0000005  # $0.50 per 1M
    cached_cost = cached_tokens * 0.000000125  # $0.125 per 1M (75% discount)
    output_cost = output_tokens * 0.000003  # $3.00 per 1M

    total_cost = input_cost + cached_cost + output_cost

    return {
        "total_cost": round(total_cost, 6),
        "breakdown": {
            "input_tokens": prompt_tokens,
            "cached_tokens": cached_tokens,
            "output_tokens": output_tokens,
            "input_cost": round(input_cost, 6),
            "cached_cost": round(cached_cost, 6),
            "output_cost": round(output_cost, 6),
        },
    }


def calculate_codeer_cost(api_calls: int, estimated_tokens: int = 0) -> dict:
    """Calculate Codeer API cost (estimated)

    NOTE: Codeer pricing is not public. This is a placeholder estimate.
    Assumption: $0.01 per API call (needs to be verified)

    Args:
        api_calls: Number of API calls made
        estimated_tokens: Estimated token count (if available)

    Returns:
        Dict with cost breakdown (USD)
    """
    # Placeholder pricing (needs verification)
    cost_per_call = 0.01  # $0.01 per call

    total_cost = api_calls * cost_per_call

    return {
        "total_cost": round(total_cost, 6),
        "breakdown": {
            "api_calls": api_calls,
            "cost_per_call": cost_per_call,
            "estimated_tokens": estimated_tokens,
        },
        "note": "Codeer pricing is estimated (actual pricing may vary)",
    }


# ============================================================================
# RAG Search Helper
# ============================================================================

# Parenting keywords for RAG search
PARENTING_KEYWORDS = [
    "孩子",
    "小孩",
    "親子",
    "教養",
    "育兒",
    "手足",
    "兄弟",
    "姊妹",
    "家長",
    "父母",
]


async def _search_rag_for_experiment(transcript: str) -> str:
    """Search RAG knowledge base for parenting content

    Args:
        transcript: Transcript text to search

    Returns:
        Formatted RAG context string (empty if no results)
    """
    from app.core.database import SessionLocal
    from app.services.openai_service import OpenAIService
    from app.services.rag_chat_service import RAGChatService

    # Detect parenting keywords
    transcript_lower = transcript.lower()
    has_parenting = any(kw in transcript_lower for kw in PARENTING_KEYWORDS)

    if not has_parenting:
        logger.info("No parenting keywords detected, skipping RAG")
        return ""

    logger.info("Parenting keywords detected, triggering RAG search")

    # Search RAG (Supabase database)
    db = SessionLocal()
    try:
        # Initialize services
        rag_service = RAGChatService(db=db)
        openai_service = OpenAIService()

        # Generate embedding for transcript
        query_embedding = await openai_service.create_embedding(transcript)

        # Search similar chunks with parenting category filter
        rows = await rag_service.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=3,
            similarity_threshold=0.7,
            category="parenting",  # Filter for parenting documents only
        )

        if not rows:
            logger.info("No RAG results found")
            return ""

        logger.info(f"Found {len(rows)} RAG results")

        # Format RAG context
        rag_parts = ["\n\n📚 相關親子教養知識庫內容（供參考）：\n"]
        for idx, row in enumerate(rows, 1):
            rag_parts.append(f"[{idx}] {row.document_title}: {row.text[:200]}...")

        rag_context = "\n".join(rag_parts)
        logger.info(f"RAG context length: {len(rag_context)} chars")

        return rag_context

    except Exception as e:
        logger.error(f"RAG search failed: {e}", exc_info=True)
        return ""
    finally:
        db.close()


# ============================================================================
# Test Functions
# ============================================================================


async def test_gemini_with_cache(
    transcript: str,
    speakers: List[dict],
    time_range: str,
    session_id: str,
) -> dict:
    """Test Gemini with explicit context caching

    Args:
        transcript: Full transcript text
        speakers: List of speaker segments
        time_range: Time range string (e.g., "0:00-8:00")
        session_id: Session ID for caching

    Returns:
        Dict with analysis, metadata, latency, cost
    """
    start_time = time.time()

    # Initialize services
    gemini_service = GeminiService()
    cache_manager = CacheManager()

    try:
        # Get or create cache
        cached_content, is_new = await cache_manager.get_or_create_cache(
            session_id=session_id,
            system_instruction=CACHE_SYSTEM_INSTRUCTION,
            accumulated_transcript=transcript,
            ttl_seconds=7200,
        )

        # Search RAG knowledge base
        rag_context = await _search_rag_for_experiment(transcript)
        logger.info(
            f"Gemini RAG enabled: {bool(rag_context)}, length: {len(rag_context)}"
        )

        if cached_content is None:
            # Content too short, use standard analysis
            logger.info("Content too short for caching, using standard analysis")
            analysis = await gemini_service.analyze_realtime_transcript(
                transcript=transcript,
                speakers=speakers,
                rag_context=rag_context,
            )

            usage_metadata = {}
            cache_hit = False
        else:
            # Use cached analysis
            analysis = await gemini_service.analyze_with_cache(
                cached_content=cached_content,
                transcript=transcript,
                speakers=speakers,
                rag_context=rag_context,
            )

            usage_metadata = analysis.get("usage_metadata", {})
            cache_hit = not is_new

        latency = time.time() - start_time

        # Calculate cost
        cost_data = calculate_gemini_cost(usage_metadata)

        return {
            "provider": "gemini",
            "model": "gemini-3-flash-preview",
            "analysis": {
                "summary": analysis.get("summary", ""),
                "alerts": analysis.get("alerts", []),
                "suggestions": analysis.get("suggestions", []),
            },
            "latency_ms": int(latency * 1000),
            "cache_hit": cache_hit,
            "usage_metadata": usage_metadata,
            "cost_data": cost_data,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Gemini test failed: {e}")
        return {
            "provider": "gemini",
            "model": "gemini-3-flash-preview",
            "error": str(e),
            "latency_ms": int((time.time() - start_time) * 1000),
        }


async def test_codeer_model(
    model: str,
    transcript: str,
    speakers: List[dict],
    time_range: str,
    session_id: str,
) -> dict:
    """Test Codeer model with session pooling

    Args:
        model: Model name (claude-sonnet, gemini-flash, gpt5-mini)
        transcript: Full transcript text
        speakers: List of speaker segments
        time_range: Time range string
        session_id: Session ID for pooling

    Returns:
        Dict with analysis, metadata, latency, cost
    """
    start_time = time.time()

    # Get agent ID
    try:
        agent_id = get_codeer_agent_id(model)
    except Exception as e:
        logger.error(f"Failed to get agent ID for {model}: {e}")
        return {
            "provider": "codeer",
            "model": model,
            "error": f"Agent configuration error: {e}",
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    # Create client
    client = CodeerClient()
    client.client.timeout = httpx.Timeout(60.0)

    try:
        # Build prompt
        prompt = f"""{CACHE_SYSTEM_INSTRUCTION}

【最新對話逐字稿】
{transcript}

【Speaker 片段】
{json.dumps(speakers, ensure_ascii=False, indent=2)}

請使用 retrieve_context_source Tool 搜尋親子教養相關知識庫內容來輔助回答。
請分析以上對話，提供 JSON 格式回應。
"""

        # Get or create session
        pool = get_codeer_session_pool()
        chat = await pool.get_or_create_session(
            session_id=session_id,
            client=client,
            agent_id=agent_id,
        )

        # Send message
        response = await client.send_message(
            chat_id=chat["id"],
            message=prompt,
            stream=False,
            agent_id=agent_id,
        )

        # Parse response
        if isinstance(response, dict):
            response_text = (
                response.get("content")
                or response.get("text")
                or response.get("message")
                or str(response)
            )
        else:
            response_text = str(response)

        # Extract JSON
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "{" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_text = response_text[json_start:json_end]
        else:
            json_text = response_text

        analysis = json.loads(json_text)

        # Ensure required fields
        if "summary" not in analysis:
            analysis["summary"] = "分析結果"
        if "alerts" not in analysis:
            analysis["alerts"] = []
        if "suggestions" not in analysis:
            analysis["suggestions"] = []

        latency = time.time() - start_time

        # Calculate cost (estimated)
        cost_data = calculate_codeer_cost(api_calls=1)

        return {
            "provider": "codeer",
            "model": model,
            "analysis": {
                "summary": analysis.get("summary", ""),
                "alerts": analysis.get("alerts", []),
                "suggestions": analysis.get("suggestions", []),
            },
            "latency_ms": int(latency * 1000),
            "session_reused": True,  # Assuming session pool worked
            "cost_data": cost_data,
            "timestamp": datetime.now().isoformat(),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Codeer response: {e}")
        return {
            "provider": "codeer",
            "model": model,
            "error": f"JSON parse error: {e}",
            "latency_ms": int((time.time() - start_time) * 1000),
        }
    except Exception as e:
        logger.error(f"Codeer test failed for {model}: {e}")
        return {
            "provider": "codeer",
            "model": model,
            "error": str(e),
            "latency_ms": int((time.time() - start_time) * 1000),
        }
    finally:
        await client.close()


async def run_single_test(
    provider: str,
    model: str,
    transcript_data: dict,
    session_id: str,
) -> dict:
    """Run single test case

    Args:
        provider: Provider name (gemini or codeer)
        model: Model name (for Codeer: claude-sonnet, gemini-flash, gpt5-mini)
        transcript_data: Transcript data dict
        session_id: Session ID

    Returns:
        Test result dict
    """
    transcript = transcript_data["transcript"]
    speakers = transcript_data["speakers"]
    time_range = transcript_data["time_range"]

    if provider == "gemini":
        result = await test_gemini_with_cache(
            transcript=transcript,
            speakers=speakers,
            time_range=time_range,
            session_id=session_id,
        )
    else:  # codeer
        result = await test_codeer_model(
            model=model,
            transcript=transcript,
            speakers=speakers,
            time_range=time_range,
            session_id=session_id,
        )

    # Add quality evaluation if analysis succeeded
    if "analysis" in result and "error" not in result:
        quality_score = evaluate_quality(result["analysis"], transcript)
        result["quality_score"] = quality_score

    return result


# ============================================================================
# Main Experiment Runner
# ============================================================================


async def run_experiment(
    provider_filter: str = None,
    duration_filter: int = None,
) -> List[dict]:
    """Run complete experiment

    Args:
        provider_filter: Optional provider filter (gemini, codeer, claude, gemini-flash, gpt5)
        duration_filter: Optional duration filter (8, 9, 10)

    Returns:
        List of test results
    """
    # Load test data
    data_path = project_root / "tests" / "data" / "long_transcripts.json"
    with open(data_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    results = []

    # Define test matrix
    durations = [8, 9, 10] if duration_filter is None else [duration_filter]

    providers_config = [
        ("gemini", "gemini-3-flash-preview"),
        ("codeer", "claude-sonnet"),
        ("codeer", "gemini-flash"),
        ("codeer", "gpt5-mini"),
    ]

    # Apply provider filter
    if provider_filter:
        if provider_filter == "gemini":
            providers_config = [("gemini", "gemini-2.5-flash")]
        elif provider_filter == "codeer":
            providers_config = [
                ("codeer", "claude-sonnet"),
                ("codeer", "gemini-flash"),
                ("codeer", "gpt5-mini"),
            ]
        elif provider_filter in ["claude", "claude-sonnet"]:
            providers_config = [("codeer", "claude-sonnet")]
        elif provider_filter in ["gemini-flash"]:
            providers_config = [("codeer", "gemini-flash")]
        elif provider_filter in ["gpt5", "gpt5-mini"]:
            providers_config = [("codeer", "gpt5-mini")]

    # Run tests
    total_tests = len(durations) * len(providers_config)
    current_test = 0

    console.print(
        Panel(
            f"[bold cyan]Starting LLM Provider Comparison Experiment[/bold cyan]\n"
            f"Total tests: {total_tests}\n"
            f"Durations: {durations} minutes\n"
            f"Providers: {len(providers_config)} configurations",
            title="Experiment Setup",
        )
    )

    for duration in durations:
        transcript_data = test_data[f"{duration}min"]

        console.print(
            f"\n[bold yellow]Testing {duration}-minute transcript: {transcript_data['topic']}[/bold yellow]"
        )

        for provider, model in providers_config:
            current_test += 1
            session_id = f"experiment-{duration}min-{model}"

            display_name = (
                f"{provider.upper()} - {model}"
                if provider == "codeer"
                else f"{provider.upper()}"
            )

            console.print(
                f"  [{current_test}/{total_tests}] Testing {display_name}...", end=" "
            )

            result = await run_single_test(
                provider=provider,
                model=model,
                transcript_data=transcript_data,
                session_id=session_id,
            )

            # Add test metadata
            result["duration_minutes"] = duration
            result["topic"] = transcript_data["topic"]
            result["test_number"] = current_test

            results.append(result)

            # Display quick feedback
            if "error" in result:
                console.print(f"[red]FAILED[/red] - {result['error'][:50]}")
            else:
                latency = result["latency_ms"]
                quality = result.get("quality_score", {}).get("total_score", 0)
                console.print(
                    f"[green]OK[/green] - {latency}ms, Quality: {quality:.1f}/100"
                )

    return results


# ============================================================================
# Results Analysis and Visualization
# ============================================================================


def analyze_results(results: List[dict]):
    """Analyze and display experiment results

    Args:
        results: List of test result dicts
    """
    console.print("\n")
    console.print(
        Panel("[bold cyan]Experiment Results Analysis[/bold cyan]", expand=False)
    )

    # Filter out failed tests
    successful_results = [r for r in results if "error" not in r]
    failed_results = [r for r in results if "error" in r]

    if failed_results:
        console.print(f"\n[yellow]Warning: {len(failed_results)} tests failed[/yellow]")
        for r in failed_results:
            console.print(
                f"  - {r['provider']} {r.get('model', '')}: {r['error'][:100]}"
            )

    if not successful_results:
        console.print("[red]No successful tests to analyze[/red]")
        return

    # Group results by duration
    results_by_duration = {}
    for r in successful_results:
        duration = r["duration_minutes"]
        if duration not in results_by_duration:
            results_by_duration[duration] = []
        results_by_duration[duration].append(r)

    # ========================================================================
    # Speed Comparison Table
    # ========================================================================
    table_speed = Table(
        title="⚡ Speed Comparison (Latency in milliseconds)",
        show_header=True,
        header_style="bold magenta",
    )
    table_speed.add_column("Duration", style="cyan", justify="center")
    table_speed.add_column("Gemini\n(cache)", justify="right")
    table_speed.add_column("Codeer\nClaude", justify="right")
    table_speed.add_column("Codeer\nGemini", justify="right")
    table_speed.add_column("Codeer\nGPT-5", justify="right")

    for duration in sorted(results_by_duration.keys()):
        duration_results = results_by_duration[duration]

        # Extract latencies
        latencies = {}
        for r in duration_results:
            key = f"{r['provider']}-{r.get('model', '')}"
            latencies[key] = r["latency_ms"]

        table_speed.add_row(
            f"{duration} min",
            f"{latencies.get('gemini-gemini-3-flash-preview', 'N/A')}",
            f"{latencies.get('codeer-claude-sonnet', 'N/A')}",
            f"{latencies.get('codeer-gemini-flash', 'N/A')}",
            f"{latencies.get('codeer-gpt5-mini', 'N/A')}",
        )

    console.print(table_speed)

    # ========================================================================
    # Quality Comparison Table
    # ========================================================================
    table_quality = Table(
        title="⭐ Quality Comparison (Score 0-100)",
        show_header=True,
        header_style="bold magenta",
    )
    table_quality.add_column("Duration", style="cyan", justify="center")
    table_quality.add_column("Gemini\n(cache)", justify="right")
    table_quality.add_column("Codeer\nClaude", justify="right")
    table_quality.add_column("Codeer\nGemini", justify="right")
    table_quality.add_column("Codeer\nGPT-5", justify="right")

    for duration in sorted(results_by_duration.keys()):
        duration_results = results_by_duration[duration]

        # Extract quality scores
        quality_scores = {}
        for r in duration_results:
            key = f"{r['provider']}-{r.get('model', '')}"
            quality = r.get("quality_score", {}).get("total_score", 0)
            quality_scores[key] = f"{quality:.1f}"

        table_quality.add_row(
            f"{duration} min",
            quality_scores.get("gemini-gemini-3-flash-preview", "N/A"),
            quality_scores.get("codeer-claude-sonnet", "N/A"),
            quality_scores.get("codeer-gemini-flash", "N/A"),
            quality_scores.get("codeer-gpt5-mini", "N/A"),
        )

    console.print("\n")
    console.print(table_quality)

    # ========================================================================
    # Cost Comparison Table
    # ========================================================================
    table_cost = Table(
        title="💰 Cost Comparison (USD)", show_header=True, header_style="bold magenta"
    )
    table_cost.add_column("Duration", style="cyan", justify="center")
    table_cost.add_column("Gemini\n(cache)", justify="right")
    table_cost.add_column("Codeer\nClaude", justify="right")
    table_cost.add_column("Codeer\nGemini", justify="right")
    table_cost.add_column("Codeer\nGPT-5", justify="right")

    for duration in sorted(results_by_duration.keys()):
        duration_results = results_by_duration[duration]

        # Extract costs
        costs = {}
        for r in duration_results:
            key = f"{r['provider']}-{r.get('model', '')}"
            cost = r.get("cost_data", {}).get("total_cost", 0)
            costs[key] = f"${cost:.6f}"

        table_cost.add_row(
            f"{duration} min",
            costs.get("gemini-gemini-3-flash-preview", "N/A"),
            costs.get("codeer-claude-sonnet", "N/A"),
            costs.get("codeer-gemini-flash", "N/A"),
            costs.get("codeer-gpt5-mini", "N/A"),
        )

    console.print("\n")
    console.print(table_cost)

    # ========================================================================
    # Overall Summary and Winner
    # ========================================================================
    console.print("\n")
    console.print(Panel("[bold green]🏆 Overall Summary[/bold green]", expand=False))

    # Calculate averages
    avg_metrics = {}

    for r in successful_results:
        key = f"{r['provider']}-{r.get('model', '')}"
        if key not in avg_metrics:
            avg_metrics[key] = {
                "latencies": [],
                "quality_scores": [],
                "costs": [],
            }

        avg_metrics[key]["latencies"].append(r["latency_ms"])
        avg_metrics[key]["quality_scores"].append(
            r.get("quality_score", {}).get("total_score", 0)
        )
        avg_metrics[key]["costs"].append(r.get("cost_data", {}).get("total_cost", 0))

    # Calculate and display averages
    console.print("\n[bold]Average Metrics Across All Tests:[/bold]")

    for key, metrics in avg_metrics.items():
        avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"])
        avg_quality = sum(metrics["quality_scores"]) / len(metrics["quality_scores"])
        avg_cost = sum(metrics["costs"]) / len(metrics["costs"])

        display_name = key.replace("-", " ").title()
        console.print(f"\n[cyan]{display_name}:[/cyan]")
        console.print(f"  Speed: {avg_latency:.0f} ms")
        console.print(f"  Quality: {avg_quality:.1f} / 100")
        console.print(f"  Cost: ${avg_cost:.6f}")

    # Determine winner (weighted scoring: Quality 60%, Speed 40%)
    console.print(
        "\n[bold yellow]Weighted Scoring (Quality 60%, Speed 40%):[/bold yellow]"
    )
    console.print(
        "[dim]Note: Cost data shown for reference only, not included in scoring[/dim]"
    )

    # Normalize metrics (0-100 scale)
    max_latency = max(
        sum(m["latencies"]) / len(m["latencies"]) for m in avg_metrics.values()
    )
    max_cost = (
        max(sum(m["costs"]) / len(m["costs"]) for m in avg_metrics.values()) or 0.000001
    )

    weighted_scores = {}

    for key, metrics in avg_metrics.items():
        avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"])
        avg_quality = sum(metrics["quality_scores"]) / len(metrics["quality_scores"])
        avg_cost = sum(metrics["costs"]) / len(metrics["costs"])

        # Normalize (higher is better)
        speed_score = (1 - avg_latency / max_latency) * 100
        quality_score = avg_quality
        cost_score = (1 - avg_cost / max_cost) * 100

        # Weighted total (Quality 60%, Speed 40%, Cost 0%)
        weighted_total = (quality_score * 0.6) + (speed_score * 0.4)

        weighted_scores[key] = {
            "total": weighted_total,
            "quality": quality_score,
            "speed": speed_score,
            "cost": cost_score,  # Keep for reference
        }

        display_name = key.replace("-", " ").title()
        console.print(f"\n[cyan]{display_name}:[/cyan]")
        console.print(f"  Quality Score: {quality_score:.1f}")
        console.print(f"  Speed Score: {speed_score:.1f}")
        console.print(f"  Cost: ${avg_cost:.6f} [dim](reference only)[/dim]")
        console.print(f"  [bold]Weighted Total: {weighted_total:.1f}[/bold]")

    # Find winner
    winner_key = max(weighted_scores.keys(), key=lambda k: weighted_scores[k]["total"])
    winner_name = winner_key.replace("-", " ").title()
    winner_score = weighted_scores[winner_key]["total"]

    console.print("\n")
    console.print(
        Panel(
            f"[bold green]🏆 Winner: {winner_name}[/bold green]\n"
            f"Weighted Score: {winner_score:.1f} / 100",
            title="Recommendation",
            border_style="green",
        )
    )


def save_results(results: List[dict], output_path: str = "experiment_results.json"):
    """Save experiment results to JSON file

    Args:
        results: List of test result dicts
        output_path: Output file path
    """
    output_file = project_root / output_path

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "test_config": {
                    "durations": [8, 9, 10],
                    "providers": [
                        "gemini-3-flash (with cache)",
                        "codeer-claude-sonnet",
                        "codeer-gemini-flash",
                        "codeer-gpt5-mini",
                    ],
                },
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    console.print(f"\n[green]Results saved to: {output_file}[/green]")


# ============================================================================
# Main Entry Point
# ============================================================================


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Compare four LLM providers for counseling analysis"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=[
            "gemini",
            "codeer",
            "claude",
            "claude-sonnet",
            "gemini-flash",
            "gpt5",
            "gpt5-mini",
        ],
        help="Filter by provider (optional)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        choices=[8, 9, 10],
        help="Filter by duration in minutes (optional)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="experiment_results.json",
        help="Output file path (default: experiment_results.json)",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run experiment
    try:
        results = await run_experiment(
            provider_filter=args.provider,
            duration_filter=args.duration,
        )

        # Analyze results
        analyze_results(results)

        # Save results
        save_results(results, output_path=args.output)

    except Exception as e:
        console.print(f"\n[red]Experiment failed: {e}[/red]")
        logger.exception("Experiment error")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
