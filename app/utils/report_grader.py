"""LLM-based report quality grading system

Uses LLM (OpenAI or Gemini) to evaluate report quality like a real supervisor would.
"""

import json
import logging
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


async def grade_report_with_llm(
    report_text: str,
    use_legacy: bool,
    client: Optional[AsyncOpenAI] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    使用 LLM 評分個案概念化報告品質

    模擬真實督導的評分方式，評估內容品質而非只檢查形式

    Args:
        report_text: 完整的概念化報告文字
        use_legacy: True = 舊版5段式, False = 新版10段式
        client: OpenAI async client (optional, for backward compatibility)
        provider: "openai" or "gemini" (default: from settings.DEFAULT_LLM_PROVIDER)

    Returns:
        dict: {
            "structure_score": float (0-25),
            "theory_score": float (0-35),
            "depth_score": float (0-25),
            "professionalism_score": float (0-15),
            "total_score": float (0-100),
            "grade": str,
            "feedback": str,
            "strengths": List[str],
            "improvements": List[str]
        }
    """

    # 根據「個案概念化能力評量表」設定評分標準
    grading_prompt = f"""
你是一位經驗豐富的職涯諮商督導，請依據「個案概念化能力評量表」的標準評分這份個案概念化報告。

【評量表八大向度】（參考專業督導使用的標準化評量工具）

一、當事人的問題（15分）
1. 求助的主要問題是否清楚陳述
2. 當事人對自己問題的看法是否呈現
3. 當事人所呈現各個問題間的關聯性與一致性
4. 希望達成問題的完整後順序

二、當事人問題的演變（15分）
1. 問題出現的時間、頻率、強度與持續度
2. 問題的形成與發展
3. 曾嘗試的解決方法與其結果
4. 問題對當事人造成的影響
5. 問題產生的關聯及意義

三、當事人的求助原因（10分）
1. 引發當事人求助的起因
2. 希望達成的求助目標

四、當事人問題的相關因素（25分）
- 個人背景屬性因素（性別、年齡、排行等）
- 生理因素
- 人格因素
- 早期經驗
- 認知因素
- 情感因素
- 行為因素
- 人際因素
- 環境（家庭、學校、社區等）因素
- 阻力與助力（包括環境與個人）

五、當事人的功能評估（10分）
1. 整體的心理、社會及職業功能適應狀況之評估
2. 精神異常、人格異常或心智發展障礙之評估
3. 心智功能受醫療藥物及藥物使用之評估

六、對當事人問題的判斷（10分）
1. 對當事人問題的假設
2. 對當事人問題的判斷
3. 對當事人問題判斷的理論取向

七、諮商計劃與策略的形成（10分）
1. 諮商目標
2. 諮商策略
3. 諮商技術
4. 諮商介入步驟
5. 轉介的評估與進行轉介

八、對諮商計劃實施的評估（5分）
1. 當事人在改變過程中可能的進展
2. 當事人在改變過程中可能的助力
3. 當事人在改變過程中可能的阻力
4. 預期改變的結果

{'⚠️ 舊版5段式報告：因結構簡化、缺少多層次分析，總分上限約 70-75 分' if use_legacy else '✅ 新版10段式報告：結構完整、要求嚴格，符合標準可達 90-100 分'}

【報告內容】
{report_text}

【評分要求】
1. 請嚴格依照「個案概念化能力評量表」的標準評分
2. 舊版報告缺少「問題演變」「功能評估」等段落，這些項目應給予較低分數
3. 新版報告若理論引用不具體（只有 [1][2] 沒有理論名稱），「理論取向」項目扣分
4. 找出具體的優點（至少3項）和改進建議（至少3項）
5. 總分 = 各向度分數總和（滿分100）
6. 等級判定：≥90優秀、≥75良好、≥60及格、<60需改進

請以 JSON 格式回應：
{{
    "problem_clarity_score": 數字 (0-15),
    "problem_clarity_feedback": "當事人問題評分說明",
    "problem_evolution_score": 數字 (0-15),
    "problem_evolution_feedback": "問題演變評分說明",
    "help_seeking_score": 數字 (0-10),
    "help_seeking_feedback": "求助原因評分說明",
    "related_factors_score": 數字 (0-25),
    "related_factors_feedback": "相關因素評分說明（需考量多層次：個人、生理、人格、認知、情感、行為、人際、環境）",
    "function_assessment_score": 數字 (0-10),
    "function_assessment_feedback": "功能評估評分說明",
    "problem_judgment_score": 數字 (0-10),
    "problem_judgment_feedback": "問題判斷評分說明（需有明確理論取向）",
    "counseling_plan_score": 數字 (0-10),
    "counseling_plan_feedback": "諮商計劃評分說明",
    "implementation_eval_score": 數字 (0-5),
    "implementation_eval_feedback": "實施評估評分說明",
    "total_score": 數字,
    "grade": "等級",
    "overall_feedback": "整體評語",
    "strengths": ["優點1", "優點2", "優點3"],
    "improvements": ["建議1", "建議2", "建議3"]
}}
"""

    # Determine provider
    if provider is None:
        provider = settings.DEFAULT_LLM_PROVIDER

    try:
        # Use Gemini or OpenAI
        if provider == "gemini":
            # Add JSON instruction to prompt for Gemini
            full_prompt = f"""你是職涯諮商領域的資深督導，擅長評估個案概念化報告的品質。你的評分客觀、嚴謹，能提供具體且有建設性的回饋。

{grading_prompt}

重要：請確保回應是有效的 JSON 格式，不要包含任何 markdown 標記（如 ```json 或 ```）。直接返回 JSON 物件。"""

            response_text = await gemini_service.chat_completion(
                prompt=full_prompt,
                temperature=0.3,
                max_tokens=8000,  # Increased from 4000 to prevent JSON truncation
                response_format={"type": "json_object"},
            )

            # Log first 500 characters of response for debugging
            logger.debug(
                f"Gemini raw response (first 500 chars): {response_text[:500]}"
            )

            # Try to parse JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as json_error:
                # Log full response for debugging
                logger.error(
                    f"Failed to parse Gemini JSON response. Error: {json_error}"
                )
                logger.error(
                    f"Error position: line {json_error.lineno}, column {json_error.colno}"
                )
                logger.error(f"Raw response (full): {response_text}")

                # Try to clean and re-parse
                logger.info("Attempting to clean and re-parse response...")
                cleaned_text = response_text.strip()

                # Remove markdown code block markers
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                    logger.debug("Removed ```json prefix")
                elif cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                    logger.debug("Removed ``` prefix")

                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                    logger.debug("Removed ``` suffix")

                cleaned_text = cleaned_text.strip()

                try:
                    result = json.loads(cleaned_text)
                    logger.info("Successfully parsed after cleaning response")
                except json.JSONDecodeError as retry_error:
                    logger.error(
                        f"Failed to parse even after cleaning. Retry error: {retry_error}"
                    )
                    logger.error(
                        f"Cleaned text (first 500 chars): {cleaned_text[:500]}"
                    )
                    raise ValueError(
                        f"Failed to parse LLM response as JSON after cleaning. "
                        f"Original error: {json_error}. "
                        f"Please check logs for full response."
                    ) from json_error
        else:
            # OpenAI path
            if client is None:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "你是職涯諮商領域的資深督導，擅長評估個案概念化報告的品質。你的評分客觀、嚴謹，能提供具體且有建設性的回饋。",
                    },
                    {"role": "user", "content": grading_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("OpenAI response content is None")
            result = json.loads(content)

        # 確保所有必要欄位都存在
        required_fields = [
            "problem_clarity_score",
            "problem_evolution_score",
            "help_seeking_score",
            "related_factors_score",
            "function_assessment_score",
            "problem_judgment_score",
            "counseling_plan_score",
            "implementation_eval_score",
            "total_score",
            "grade",
        ]

        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")

        # 驗證分數範圍（依照個案概念化能力評量表）
        if not (0 <= result["problem_clarity_score"] <= 15):
            raise ValueError(
                f"Invalid problem_clarity_score: {result['problem_clarity_score']}"
            )
        if not (0 <= result["problem_evolution_score"] <= 15):
            raise ValueError(
                f"Invalid problem_evolution_score: {result['problem_evolution_score']}"
            )
        if not (0 <= result["help_seeking_score"] <= 10):
            raise ValueError(
                f"Invalid help_seeking_score: {result['help_seeking_score']}"
            )
        if not (0 <= result["related_factors_score"] <= 25):
            raise ValueError(
                f"Invalid related_factors_score: {result['related_factors_score']}"
            )
        if not (0 <= result["function_assessment_score"] <= 10):
            raise ValueError(
                f"Invalid function_assessment_score: {result['function_assessment_score']}"
            )
        if not (0 <= result["problem_judgment_score"] <= 10):
            raise ValueError(
                f"Invalid problem_judgment_score: {result['problem_judgment_score']}"
            )
        if not (0 <= result["counseling_plan_score"] <= 10):
            raise ValueError(
                f"Invalid counseling_plan_score: {result['counseling_plan_score']}"
            )
        if not (0 <= result["implementation_eval_score"] <= 5):
            raise ValueError(
                f"Invalid implementation_eval_score: {result['implementation_eval_score']}"
            )
        if not (0 <= result["total_score"] <= 100):
            raise ValueError(f"Invalid total_score: {result['total_score']}")

        return result

    except json.JSONDecodeError as e:
        # This should be caught by inner try-catch, but just in case
        logger.error(f"Uncaught JSON decode error: {e}")
        raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e
    except ValueError:
        # Re-raise ValueError (including JSON parsing errors)
        raise
    except Exception as e:
        logger.exception(f"Unexpected error grading report with LLM: {e}")
        raise RuntimeError(f"Error grading report with LLM: {e}") from e


def get_quality_grade(score: float) -> str:
    """
    根據分數返回等級

    Args:
        score: 品質分數 (0-100)

    Returns:
        str: 等級標籤
    """
    if score >= 90:
        return "優秀"
    elif score >= 75:
        return "良好"
    elif score >= 60:
        return "及格"
    else:
        return "需改進"
