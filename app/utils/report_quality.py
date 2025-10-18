"""Report quality summary generation"""

from datetime import datetime
from typing import Dict, List, Any

from app.utils.report_validators import (
    validate_report_structure,
    validate_citations,
    calculate_quality_score
)


def generate_quality_summary(
    report: Dict[str, Any],
    report_text: str,
    theories: List[Dict]
) -> Dict[str, Any]:
    """
    生成報告品質摘要

    整合結構驗證和引用驗證結果，計算整體品質分數

    Args:
        report: 完整報告 dict
        report_text: 報告的 conceptualization 文字
        theories: 引用的理論列表

    Returns:
        dict: 品質摘要，包含結構、引用、內容指標和總分
    """
    # 結構驗證
    structure_validation = validate_report_structure(report_text)

    # 引用驗證
    citation_validation = validate_citations(report_text)

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
