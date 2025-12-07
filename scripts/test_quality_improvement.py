#!/usr/bin/env python3
"""
測試新舊版本報告品質對比

使用方式:
1. 先切回 staging 分支生成「舊版」報告
2. 切回 feature 分支生成「新版」報告
3. 對比品質分數
"""

from app.utils.report_quality import generate_quality_summary
from app.utils.report_validators import (
    calculate_quality_score,
    validate_citations,
    validate_report_structure,
)

# 測試用逐字稿
TEST_TRANSCRIPT = """
諮詢師：早安，今天想聊什麼？
個案：老師您好，我是小美，28歲，碩士畢業，現在在科技公司當軟體工程師。
最近工作感到很迷茫，不知道未來要做什麼。每天寫code很無聊，看不到意義。

諮詢師：什麼時候開始有這種感覺？
個案：大概3個月前升遷失敗之後。我發現自己好像不適合當主管，但繼續當工程師又覺得沒前途。
我爸媽一直希望我穩定，但我自己也不知道想要什麼。

諮詢師：聽起來你在職涯發展上遇到瓶頸，也在思考自己的價值觀。
個案：對，我覺得我缺乏方向，也不知道自己的優勢在哪。有時候會懷疑自己的能力。

諮詢師：今天的諮詢你希望得到什麼？
個案：希望能找到職涯方向，知道自己適合做什麼，還有提升工作動機。

諮詢師：好的，我們今天可以先用卡片排序來釐清你的價值觀，再用生涯幻遊探索可能的方向。
個案：好的，謝謝老師。
"""


def analyze_old_version_report(report_text: str):
    """分析舊版報告（手動貼上）"""
    print("=" * 60)
    print("📊 舊版報告分析（staging 分支）")
    print("=" * 60)

    structure = validate_report_structure(report_text)
    citation = validate_citations(report_text)
    score = calculate_quality_score(structure, citation)

    print(f"\n結構完整性: {structure['coverage']}%")
    print(f"缺少段落: {len(structure['missing_sections'])} 個")
    if structure["missing_sections"]:
        for section in structure["missing_sections"][:3]:
            print(f"  - {section}")

    print("\n理論引用:")
    print(f"  總引用數: {citation['total_citations']}")
    print(
        f"  核心段落完整: {'✅' if citation['all_critical_sections_cited'] else '❌'}"
    )
    print(f"  有理由說明: {'✅' if citation['has_rationale'] else '❌'}")

    print(f"\n品質分數: {score:.1f}/100")
    print(f"等級: {get_grade(score)}")

    return {
        "structure_coverage": structure["coverage"],
        "citation_count": citation["total_citations"],
        "has_rationale": citation["has_rationale"],
        "score": score,
    }


def analyze_new_version_report(report_text: str, theories: list):
    """分析新版報告（feature 分支）"""
    print("\n" + "=" * 60)
    print("📊 新版報告分析（feature 分支）")
    print("=" * 60)

    report = {"client_name": "小美", "conceptualization": report_text}

    summary = generate_quality_summary(report, report_text, theories)

    print(f"\n結構完整性: {summary['structure_quality']['completeness']}%")
    print(f"狀態: {summary['structure_quality']['status']}")

    print("\n理論引用:")
    print(f"  總引用數: {summary['citation_quality']['total_citations']}")
    print(
        f"  核心段落完整: {'✅' if summary['citation_quality']['critical_sections_cited'] else '❌'}"
    )
    print(
        f"  有理由說明: {'✅' if summary['citation_quality']['has_rationale'] else '❌'}"
    )
    print(f"  狀態: {summary['citation_quality']['status']}")

    print("\n內容指標:")
    print(f"  總字數: {summary['content_metrics']['total_length']}")
    print(f"  理論數量: {summary['content_metrics']['theory_count']}")
    print(f"  有反思: {'✅' if summary['content_metrics']['has_reflection'] else '❌'}")

    print(f"\n品質分數: {summary['overall_score']:.1f}/100")
    print(f"等級: {summary['grade']}")

    return {
        "structure_coverage": summary["structure_quality"]["completeness"],
        "citation_count": summary["citation_quality"]["total_citations"],
        "has_rationale": summary["citation_quality"]["has_rationale"],
        "score": summary["overall_score"],
    }


def compare_versions(old_metrics: dict, new_metrics: dict):
    """對比新舊版本"""
    print("\n" + "=" * 60)
    print("📈 改善對比")
    print("=" * 60)

    improvements = []

    # 結構完整性
    structure_diff = (
        new_metrics["structure_coverage"] - old_metrics["structure_coverage"]
    )
    print(
        f"\n結構完整性: {old_metrics['structure_coverage']:.0f}% → {new_metrics['structure_coverage']:.0f}% ",
        end="",
    )
    if structure_diff > 0:
        print(f"(+{structure_diff:.0f}% ✅)")
        improvements.append(f"結構完整性提升 {structure_diff:.0f}%")
    else:
        print("(無變化)")

    # 引用數量
    citation_diff = new_metrics["citation_count"] - old_metrics["citation_count"]
    print(
        f"引用數量: {old_metrics['citation_count']} → {new_metrics['citation_count']} ",
        end="",
    )
    if citation_diff > 0:
        print(f"(+{citation_diff} ✅)")
        improvements.append(f"引用數量增加 {citation_diff} 個")
    else:
        print("(無變化)")

    # 理由說明
    old_rationale = "✅" if old_metrics["has_rationale"] else "❌"
    new_rationale = "✅" if new_metrics["has_rationale"] else "❌"
    print(f"理由說明: {old_rationale} → {new_rationale} ", end="")
    if new_metrics["has_rationale"] and not old_metrics["has_rationale"]:
        print("(新增 ✅)")
        improvements.append("新增理由說明")
    else:
        print()

    # 品質分數
    score_diff = new_metrics["score"] - old_metrics["score"]
    print(
        f"\n品質分數: {old_metrics['score']:.1f} → {new_metrics['score']:.1f} ", end=""
    )
    if score_diff > 0:
        print(f"(+{score_diff:.1f} ✅)")
        improvements.append(f"品質分數提升 {score_diff:.1f} 分")
    else:
        print("(無變化)")

    print(
        f"\n等級變化: {get_grade(old_metrics['score'])} → {get_grade(new_metrics['score'])}"
    )

    if improvements:
        print("\n✅ 改善項目:")
        for i, improvement in enumerate(improvements, 1):
            print(f"  {i}. {improvement}")

    # 計算改善百分比
    if old_metrics["score"] > 0:
        improvement_pct = (score_diff / old_metrics["score"]) * 100
        print(f"\n📊 整體改善: {improvement_pct:.1f}%")


def get_grade(score: float) -> str:
    """取得等級"""
    if score >= 90:
        return "優秀"
    elif score >= 75:
        return "良好"
    elif score >= 60:
        return "及格"
    else:
        return "需改進"


def main():
    print("\n" + "=" * 60)
    print("🧪 報告品質改善驗證測試")
    print("=" * 60)

    print("\n測試逐字稿:")
    print("-" * 60)
    print(TEST_TRANSCRIPT[:200] + "...")

    print("\n\n請按照以下步驟操作:")
    print("1. 切換到 staging 分支，啟動服務，生成報告（舊版）")
    print("2. 複製報告內容，貼到此處")
    print("3. 切換到 feature 分支，啟動服務，生成報告（新版）")
    print("4. 複製報告內容，貼到此處")
    print("5. 程式會自動對比品質")

    print("\n\n或者，貼上已有的報告進行分析:")
    print("-" * 60)

    # 讓使用者貼上報告
    print("\n請貼上舊版報告 (staging)，輸入 END 結束:")
    old_report_lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        old_report_lines.append(line)

    old_report = "\n".join(old_report_lines)

    if old_report.strip():
        old_metrics = analyze_old_version_report(old_report)

        print("\n\n請貼上新版報告 (feature)，輸入 END 結束:")
        new_report_lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            new_report_lines.append(line)

        new_report = "\n".join(new_report_lines)

        if new_report.strip():
            # 假設有7個理論
            theories = [{"id": i} for i in range(1, 8)]
            new_metrics = analyze_new_version_report(new_report, theories)

            # 對比
            compare_versions(old_metrics, new_metrics)

    print("\n\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
