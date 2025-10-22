"""Report quality validators for case conceptualization reports"""

import re
from typing import Dict


def validate_report_structure(report_text: str, use_legacy: bool = False) -> Dict:
    """
    檢查報告結構完整性

    確保報告包含所有必須的段落

    Args:
        report_text: 報告文字
        use_legacy: True = 檢查舊版5段式, False = 檢查新版10段式

    Returns:
        dict: {
            "complete": bool,
            "missing_sections": List[str],
            "coverage": float (0-100)
        }
    """
    if use_legacy:
        # Legacy version: 5 sections
        required_sections = [
            "【主訴問題】",
            "【成因分析】",
            "【晤談目標（移動主訴）】",
            "【介入策略】",
            "【目前成效評估】",
        ]
        total_sections = 5
    else:
        # Enhanced version: 10 sections
        required_sections = [
            "【一、案主基本資料】",
            "【二、主訴問題】",
            "【三、問題發展脈絡】",
            "【四、求助動機與期待】",
            "【五、多層次因素分析】",
            "【六、個案優勢與資源】",
            "【七、諮詢師的專業判斷】",
            "【八、諮商目標與介入策略】",
            "【九、預期成效與評估】",
            "【十、諮詢師自我反思】",
        ]
        total_sections = 10

    missing = []
    for section in required_sections:
        if section not in report_text:
            missing.append(section)

    coverage = (total_sections - len(missing)) / total_sections * 100

    return {
        "complete": len(missing) == 0,
        "missing_sections": missing,
        "coverage": round(coverage, 1),
    }


def validate_citations(report_text: str, use_legacy: bool = False) -> Dict:
    """
    檢查理論引用品質

    檢查三個核心段落是否有引用，以及引用說明的品質

    Args:
        report_text: 報告文字
        use_legacy: True = 檢查舊版段落, False = 檢查新版段落

    Returns:
        dict: {
            "section_details": Dict[str, Dict],
            "total_citations": int,
            "has_rationale": bool,
            "all_critical_sections_cited": bool
        }
    """
    if use_legacy:
        # Legacy version: 成因分析 and 介入策略
        critical_sections = {
            "【成因分析】": "成因分析需要理論支持",
            "【介入策略】": "介入策略需要技術引用",
        }
    else:
        # Enhanced version: 3 critical sections
        critical_sections = {
            "【五、多層次因素分析】": "因素分析需要理論支持",
            "【七、諮詢師的專業判斷】": "專業判斷需要理論依據",
            "【八、諮商目標與介入策略】": "介入策略需要技術引用",
        }

    results = {}
    for section, reason in critical_sections.items():
        section_text = extract_section(report_text, section)
        citations = re.findall(r"\[(\d+)\]", section_text)

        results[section] = {
            "has_citations": len(citations) > 0,
            "citation_count": len(citations),
            "reason": reason,
            "status": "✅" if len(citations) > 0 else "❌",
        }

    # 統計總引用數
    total_citations = len(re.findall(r"\[(\d+)\]", report_text))

    # 檢查是否有說明理由（關鍵詞）
    rationale_keywords = [
        "根據",
        "基於",
        "從",
        "理論指出",
        "顯示",
        "觀點",
        "依據",
        "因為",
        "由於",
        "考量",
    ]
    has_rationale = any(keyword in report_text for keyword in rationale_keywords)

    return {
        "section_details": results,
        "total_citations": total_citations,
        "has_rationale": has_rationale,
        "all_critical_sections_cited": all(
            r["has_citations"] for r in results.values()
        ),
    }


def extract_section(report_text: str, section_title: str) -> str:
    """
    提取特定段落的文字

    Args:
        report_text: 完整報告文字
        section_title: 段落標題（如「【五、多層次因素分析】」）

    Returns:
        str: 該段落的文字內容
    """
    # 找到該段落開始位置
    start_match = re.search(re.escape(section_title), report_text)
    if not start_match:
        return ""

    start = start_match.end()

    # 找到下一個【】段落（或結尾）
    next_section = re.search(r"【.+?】", report_text[start:])

    if next_section:
        end = start + next_section.start()
    else:
        end = len(report_text)

    return report_text[start:end].strip()


def calculate_quality_score(
    structure_validation: Dict, citation_validation: Dict
) -> float:
    """
    計算報告整體品質分數（0-100）

    評分標準：
    - 結構完整性：40%
    - 引用覆蓋率：40%
    - 引用品質：20%

    Args:
        structure_validation: validate_report_structure() 的結果
        citation_validation: validate_citations() 的結果

    Returns:
        float: 品質分數 (0-100)
    """
    score = 0

    # 1. 結構完整性 (40%)
    score += structure_validation["coverage"] * 0.4

    # 2. 引用覆蓋率 (40%)
    if citation_validation["all_critical_sections_cited"]:
        score += 40
    else:
        # 部分覆蓋（動態計算總段落數）
        total_critical_sections = len(citation_validation["section_details"])
        cited_count = sum(
            1
            for r in citation_validation["section_details"].values()
            if r["has_citations"]
        )
        if total_critical_sections > 0:
            score += (cited_count / total_critical_sections) * 40

    # 3. 引用品質 (20%)
    # 3a. 是否有說明理由 (10%)
    if citation_validation["has_rationale"]:
        score += 10

    # 3b. 引用數量 (10%)
    # 理想狀態：5-7 個引用
    citation_score = min(citation_validation["total_citations"] / 7, 1.0) * 10
    score += citation_score

    return round(score, 1)
