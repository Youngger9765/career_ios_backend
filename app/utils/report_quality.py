"""Report quality summary generation"""

from datetime import datetime
from typing import Dict, List, Any
from openai import AsyncOpenAI

from app.utils.report_validators import (
    validate_report_structure,
    validate_citations,
    calculate_quality_score
)
from app.utils.report_grader import grade_report_with_llm


def generate_quality_summary(
    report: Dict[str, Any],
    report_text: str,
    theories: List[Dict],
    use_legacy: bool = False
) -> Dict[str, Any]:
    """
    生成報告品質摘要

    整合結構驗證和引用驗證結果，計算整體品質分數

    Args:
        report: 完整報告 dict
        report_text: 報告的 conceptualization 文字
        theories: 引用的理論列表
        use_legacy: True = 舊版5段式驗證, False = 新版10段式驗證

    Returns:
        dict: 品質摘要，包含結構、引用、內容指標和總分
    """
    # 結構驗證（根據版本使用不同標題清單）
    structure_validation = validate_report_structure(report_text, use_legacy=use_legacy)

    # 引用驗證（根據版本使用不同段落標題）
    citation_validation = validate_citations(report_text, use_legacy=use_legacy)

    # 內容指標
    content_metrics = {
        "total_length": len(report_text),
        "avg_section_length": len(report_text) // 10 if report_text else 0,
        "theory_count": len(theories),
        "has_reflection": "【十、諮詢師自我反思】" in report_text
    }

    # 計算總分
    overall_score = calculate_quality_score(structure_validation, citation_validation)

    # Count how many critical sections have citations
    critical_sections_cited_count = sum(
        1 for r in citation_validation["section_details"].values()
        if r["has_citations"]
    )

    return {
        "structure_quality": {
            "coverage": structure_validation["coverage"],  # Frontend expects "coverage" not "completeness"
            "completeness": structure_validation["coverage"],  # Keep for backward compatibility
            "missing_sections": structure_validation["missing_sections"],
            "status": "✅ 完整" if structure_validation["complete"] else f"❌ 缺少 {len(structure_validation['missing_sections'])} 個段落"
        },
        "citation_quality": {
            "total_citations": citation_validation["total_citations"],
            "critical_sections_cited": critical_sections_cited_count,  # Return count (0-3), not boolean
            "all_critical_sections_cited": citation_validation["all_critical_sections_cited"],  # Keep boolean for logic
            "has_rationale": citation_validation["has_rationale"],
            "section_details": citation_validation["section_details"],
            "status": "✅ 完整引用" if citation_validation["all_critical_sections_cited"] else "❌ 部分段落未引用"
        },
        "content_metrics": content_metrics,
        "overall_score": overall_score,
        "grade": get_quality_grade(overall_score),
        "timestamp": datetime.now().isoformat()
    }


async def generate_quality_summary_with_llm(
    report: Dict[str, Any],
    report_text: str,
    theories: List[Dict],
    use_legacy: bool,
    openai_client: AsyncOpenAI
) -> Dict[str, Any]:
    """
    使用 LLM 生成報告品質摘要（更準確的評分）

    Args:
        report: 完整報告 dict
        report_text: 報告的 conceptualization 文字
        theories: 引用的理論列表
        use_legacy: True = 舊版5段式, False = 新版10段式
        openai_client: OpenAI async client

    Returns:
        dict: LLM 評分結果
    """
    # 使用 LLM 評分
    llm_grade = await grade_report_with_llm(
        report_text=report_text,
        use_legacy=use_legacy,
        client=openai_client
    )

    # 同時保留舊的驗證器結果作為參考
    structure_validation = validate_report_structure(report_text, use_legacy=use_legacy)
    citation_validation = validate_citations(report_text, use_legacy=use_legacy)

    critical_sections_cited_count = sum(
        1 for r in citation_validation["section_details"].values()
        if r["has_citations"]
    )

    return {
        "problem_clarity": {
            "score": llm_grade["problem_clarity_score"],
            "max_score": 15,
            "feedback": llm_grade.get("problem_clarity_feedback", ""),
        },
        "problem_evolution": {
            "score": llm_grade["problem_evolution_score"],
            "max_score": 15,
            "feedback": llm_grade.get("problem_evolution_feedback", ""),
        },
        "help_seeking": {
            "score": llm_grade["help_seeking_score"],
            "max_score": 10,
            "feedback": llm_grade.get("help_seeking_feedback", ""),
        },
        "related_factors": {
            "score": llm_grade["related_factors_score"],
            "max_score": 25,
            "feedback": llm_grade.get("related_factors_feedback", ""),
        },
        "function_assessment": {
            "score": llm_grade["function_assessment_score"],
            "max_score": 10,
            "feedback": llm_grade.get("function_assessment_feedback", ""),
        },
        "problem_judgment": {
            "score": llm_grade["problem_judgment_score"],
            "max_score": 10,
            "feedback": llm_grade.get("problem_judgment_feedback", ""),
        },
        "counseling_plan": {
            "score": llm_grade["counseling_plan_score"],
            "max_score": 10,
            "feedback": llm_grade.get("counseling_plan_feedback", ""),
        },
        "implementation_eval": {
            "score": llm_grade["implementation_eval_score"],
            "max_score": 5,
            "feedback": llm_grade.get("implementation_eval_feedback", ""),
        },
        "citation_quality": {
            "total_citations": citation_validation["total_citations"],
            "critical_sections_cited": critical_sections_cited_count,
            "section_details": citation_validation["section_details"],
            "status": "✅ 完整引用" if citation_validation["all_critical_sections_cited"] else "❌ 部分段落未引用"
        },
        "content_metrics": {
            "total_length": len(report_text),
            "avg_section_length": len(report_text) // (5 if use_legacy else 10),
            "theory_count": len(theories),
            "has_reflection": "【十、諮詢師自我反思】" in report_text if not use_legacy else False
        },
        "overall_score": llm_grade["total_score"],
        "grade": llm_grade["grade"],
        "overall_feedback": llm_grade.get("overall_feedback", ""),
        "strengths": llm_grade.get("strengths", []),
        "improvements": llm_grade.get("improvements", []),
        "grading_method": "llm",
        "evaluation_standard": "個案概念化能力評量表（8向度）",
        "timestamp": datetime.now().isoformat()
    }


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
