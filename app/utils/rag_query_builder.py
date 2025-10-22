"""Enhanced RAG query builder for better theory retrieval"""

from typing import Dict, Any


def extract_key_demographics(parsed_data: Dict[str, Any]) -> str:
    """
    提取關鍵人口統計資料

    Args:
        parsed_data: 解析後的逐字稿資料

    Returns:
        str: 人口統計描述字串
    """
    parts = []

    age = parsed_data.get("age")
    if age:
        parts.append(f"{age}歲")

    gender = parsed_data.get("gender")
    if gender and gender != "未提及":
        parts.append(gender)

    education = parsed_data.get("education")
    if education and education != "未提及":
        parts.append(education)

    return " ".join(parts) if parts else ""


def extract_career_stage(parsed_data: Dict[str, Any]) -> str:
    """
    根據年齡和主訴識別生涯發展階段 (Super's Life-Span Theory)

    Super 生涯發展階段：
    - 成長期 (0-14歲)
    - 探索期 (15-24歲): 試探、轉換、嘗試
    - 建立期 (25-44歲): 立足、穩定、前進
    - 維持期 (45-64歲): 保持、更新、創新
    - 衰退期 (65歲+): 退縮、退休

    Args:
        parsed_data: 解析後的逐字稿資料

    Returns:
        str: 生涯階段描述
    """
    age = parsed_data.get("age")
    concerns = parsed_data.get("main_concerns", [])

    if not age:
        # 無年齡時嘗試從主訴推斷
        concerns_text = " ".join(concerns).lower()
        if any(kw in concerns_text for kw in ["探索", "試探", "嘗試", "迷茫", "方向"]):
            return "探索期"
        elif any(kw in concerns_text for kw in ["轉職", "立足", "發展", "晉升"]):
            return "建立期"
        elif any(kw in concerns_text for kw in ["維持", "倦怠", "穩定", "平衡"]):
            return "維持期"
        return ""

    # 根據年齡判斷
    if age <= 14:
        return "成長期"
    elif age <= 24:
        return "探索期"
    elif age <= 44:
        return "建立期"
    elif age <= 64:
        return "維持期"
    else:
        return "衰退期"


def build_enhanced_query(parsed_data: Dict[str, Any]) -> str:
    """
    構建增強版 RAG 查詢

    改進點：
    1. 加入人口統計資料（年齡、性別、教育程度）
    2. 加入生涯發展階段
    3. 結構化查詢而非簡單拼接

    Args:
        parsed_data: 解析後的逐字稿資料，包含：
            - age: 年齡
            - gender: 性別
            - education: 教育程度
            - main_concerns: 主訴問題列表
            - counselor_techniques: 諮詢師技巧列表

    Returns:
        str: 增強版查詢字串
    """
    query_parts = []

    # 1. 生涯階段（優先，幫助理論匹配）
    career_stage = extract_career_stage(parsed_data)
    if career_stage:
        query_parts.append(career_stage)

    # 2. 人口統計資料
    demographics = extract_key_demographics(parsed_data)
    if demographics:
        query_parts.append(demographics)

    # 3. 主訴問題（取前 3 個，避免噪音）
    main_concerns = parsed_data.get("main_concerns", [])
    if main_concerns:
        query_parts.extend(main_concerns[:3])

    # 4. 諮詢技巧（取前 2 個）
    techniques = parsed_data.get("counselor_techniques", [])
    if techniques:
        query_parts.extend(techniques[:2])

    # 5. 預設值（若無任何資訊）
    if not query_parts:
        return "職涯諮詢 生涯發展"

    # 構建結構化查詢
    # 格式：生涯階段 + 人口統計 + 主訴 + 技巧
    return " ".join(query_parts)
