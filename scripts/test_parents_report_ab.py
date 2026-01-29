#!/usr/bin/env python3
"""
A/B Testing script for Parents Report Prompt Refinement

Compares OLD (academic) vs NEW (accessible) prompt outputs.
"""

import asyncio
import json
import re
from typing import Dict, List

# Sample transcript (10-minute parent-child dialogue)
SAMPLE_TRANSCRIPT = """
媽媽：寶貝，功課寫完了嗎？都快八點了。
孩子：還沒...我不想寫。
媽媽：不想寫也要寫啊！你看你同學都寫完了。
孩子：我就是不想寫嘛！
媽媽：你這是什麼態度？功課是你自己的事，不寫以後怎麼辦？
孩子：我不管！我就是不想寫！
媽媽：（生氣）你再這樣我就不讓你看電視了！
孩子：（哭）我討厭你！你都不了解我！
媽媽：我不了解你？我每天這麼辛苦還不是為了你好？
孩子：（繼續哭）我壓力好大...
媽媽：壓力大就不用寫功課了嗎？你看人家別的小孩...
孩子：你為什麼要一直拿我跟別人比？我就是我！
媽媽：我這是在激勵你啊！你要努力一點。
孩子：可是我真的很累...今天考試考不好，老師還罵我...
媽媽：考不好就要更認真啊！你看你這次數學又錯那麼多。
孩子：（小聲）我已經很努力了...
媽媽：努力哪夠？你要更努力才行！來，快點去寫功課。
孩子：（沉默，慢慢走開）
媽媽：（嘆氣）這孩子...怎麼這麼不懂事...
"""

# Academic terminology to detect
# NOTE: Removed simple terms that users find acceptable (歸屬感, 價值感, 同理, 界限)
# Only flagging truly academic jargon and expert name-dropping
ACADEMIC_TERMS = [
    "Gottman", "阿德勒", "薩提爾", "Adler", "Satir", "Dan Siegel", "Ross Greene", "Becky Kennedy",
    "冰山理論", "冰山下", "情緒教練時刻", "情緒教練", "黃金情緒教育時刻", "黃金時刻",
    "權力鬥爭循環", "權力鬥爭", "和善而堅定",
    "正向教養", "情緒智商", "全腦教養",
    "學派觀點", "理論指出", "專家認為"
]


def count_academic_terms(text: str) -> Dict[str, int]:
    """Count frequency of academic terminology in text"""
    counts = {}
    for term in ACADEMIC_TERMS:
        count = len(re.findall(term, text, re.IGNORECASE))
        if count > 0:
            counts[term] = count
    return counts


def calculate_readability_score(text: str) -> Dict[str, any]:
    """Simple readability metrics"""
    # Count sentences (rough estimate by punctuation)
    sentences = len(re.findall(r'[。！？]', text))

    # Average sentence length
    chars = len(text)
    avg_sentence_length = chars / sentences if sentences > 0 else 0

    # Academic term density
    academic_counts = count_academic_terms(text)
    total_academic_terms = sum(academic_counts.values())
    academic_density = (total_academic_terms / chars) * 1000 if chars > 0 else 0

    return {
        "total_chars": chars,
        "sentences": sentences,
        "avg_sentence_length": avg_sentence_length,
        "academic_terms_found": academic_counts,
        "total_academic_terms": total_academic_terms,
        "academic_density_per_1000_chars": round(academic_density, 2)
    }


async def generate_report_with_prompt(
    transcript: str,
    use_new_prompt: bool = False
) -> Dict:
    """
    Generate report using OLD or NEW prompt.

    NOTE: This is a MOCK for now. In real implementation, this would:
    1. Set USE_VERNACULAR_PROMPT env var
    2. Call the actual ParentsReportService
    3. Return the generated report
    """
    # TODO: Replace with actual service call
    if use_new_prompt:
        # Simulated NEW prompt output (more accessible)
        return {
            "encouragement": "你有注意到孩子說壓力大",
            "issue": "這次對話中，當孩子說「我壓力好大」時，我們可能錯過了一個很好的機會...",
            "analyze": """當孩子說「我壓力好大」「今天考試考不好，老師還罵我」時，這其實是很難得的時刻——孩子願意跟你說心裡話。

研究發現，如果這時候我們能停下來好好聽孩子說，而不是急著講道理，孩子會更願意跟我們分享。但這次對話中，媽媽用「壓力大就不用寫功課了嗎」來回應，這會讓孩子覺得自己的感受不被接納。

當我們拿孩子跟別人比較時（「你看人家別的小孩」「你看你同學都寫完了」），孩子心裡會想「我不夠好」「我不如別人」。這種比較不但不會激勵孩子，反而會讓孩子覺得自己不屬於這個家，更沒動力去改變。

當孩子大喊「我討厭你！你都不了解我！」時，表面上是生氣，但孩子真正想說的可能是「我需要你理解我」「我需要有人聽我說話」。如果我們只看到表面的不禮貌，就會錯過真正的問題。

對話中多次使用威脅（「你再這樣我就不讓你看電視了」）和命令（「快點去寫功課」），這種方式會引發孩子的抗拒。研究顯示，當孩子感到被控制時，會本能地用反抗來捍衛自主權。""",
            "suggestion": """當孩子說「我壓力好大」時，可以這樣回應：

「我注意到你說壓力大，而且看起來你今天心情不太好，是嗎？」（先確認情緒）

「聽起來你今天過得很不容易...考試考不好，老師又罵你，真的很辛苦。」（同理孩子的感受，停頓，給孩子說話的空間）

「是因為考試和老師的事情讓你覺得難過、挫折嗎？」（幫助孩子說出感受）

「我們一起想想看，怎麼做可以讓你感覺好一點？功課的事，我們等你心情好一點再來想辦法。」（引導解決問題）

---

針對功課的議題，可以試試「溫柔但堅定」的方式：

「我看到你今天真的很累了，考試的事讓你壓力很大。」（理解孩子）

「功課還是要完成的，這是你的責任。」（堅守界限）

「我們一起想想看，有什麼方法可以讓寫功課變得輕鬆一點？要不要我陪你一起寫？或是你想先休息10分鐘？」（合作解決）

---

當孩子說「你為什麼要一直拿我跟別人比」時，可以這樣回應：

「你說得對，我不應該拿你跟別人比。每個人都有自己的節奏。媽媽是擔心你，但我說錯話了，對不起。」（承認錯誤，修復關係）

「我想了解，是什麼讓你覺得寫功課這麼困難？是題目太難？還是你不知道從哪裡開始？」（探索真正的問題）"""
        }
    else:
        # Simulated OLD prompt output (academic)
        return {
            "encouragement": "你有注意到孩子說壓力大",
            "issue": "這次對話中主要有三個需要改進的地方...",
            "analyze": """從 **Gottman 情緒教養理論** 來看，這次對話中媽媽錯失了多個寶貴的情緒輔導機會。當孩子說「我壓力好大」「今天考試考不好，老師還罵我」時，這是 Gottman 所說的「黃金情緒教育時刻」（emotional moments），是建立親子連結和培養情緒智商的最佳時機。

根據 **阿德勒正向教養** 的核心概念，孩子需要「歸屬感」（belonging）和「價值感」（significance）才能產生內在動機。當媽媽說「你看人家別的小孩」「你看你同學都寫完了」時，這類比較會深深傷害孩子的歸屬感。

從 **薩提爾冰山理論** 來分析，當孩子大喊「我討厭你！你都不了解我！」時，這只是冰山的表面行為。冰山下隱藏的是更深層的心理需求：「我需要被看見」「我需要被理解」。

此外，對話中媽媽使用了多次威脅和命令，這種高壓控制的溝通模式會引發孩子的抗拒和反抗，陷入權力鬥爭的循環中。""",
            "suggestion": """當孩子說「我壓力好大」時，可以運用 **Gottman 情緒教養五步驟**：

**第一步（覺察情緒）**：「我注意到你說壓力大...」

**第二步（把握時機）**：先放下功課的議題...

**第三步（同理傾聽）**：「聽起來你今天過得很不容易...」

**第四步（協助命名情緒）**：「是因為考試和老師的事情讓你覺得難過、挫折嗎？」

**第五步（引導問題解決）**：「我們一起想想看...」

---

針對功課的議題，可以運用 **阿德勒正向教養** 的「和善而堅定」（kind and firm）原則：

**和善的部分**：「我看到你今天真的很累了...」

**堅定的部分**：「功課還是要完成的，這是你的責任。」

**合作解決**：「我們一起想想看...」"""
        }


async def run_ab_test():
    """Run A/B test comparing OLD vs NEW prompt"""
    print("=" * 80)
    print("🧪 Parents Report Prompt A/B Testing")
    print("=" * 80)
    print()

    # Generate reports
    print("📝 Generating reports...")
    report_old = await generate_report_with_prompt(SAMPLE_TRANSCRIPT, use_new_prompt=False)
    report_new = await generate_report_with_prompt(SAMPLE_TRANSCRIPT, use_new_prompt=True)

    # Analyze both
    print("\n" + "=" * 80)
    print("📊 REPORT A: OLD PROMPT (Academic Style)")
    print("=" * 80)

    analyze_old = report_old["analyze"]
    suggestion_old = report_old["suggestion"]
    combined_old = analyze_old + "\n" + suggestion_old

    metrics_old = calculate_readability_score(combined_old)
    print(f"\n📈 Readability Metrics:")
    print(f"   Total chars: {metrics_old['total_chars']}")
    print(f"   Sentences: {metrics_old['sentences']}")
    print(f"   Avg sentence length: {metrics_old['avg_sentence_length']:.1f} chars")
    print(f"   Academic terms found: {metrics_old['total_academic_terms']}")
    print(f"   Academic density: {metrics_old['academic_density_per_1000_chars']} per 1000 chars")

    if metrics_old['academic_terms_found']:
        print(f"\n🔍 Academic terms detected:")
        for term, count in metrics_old['academic_terms_found'].items():
            print(f"   - {term}: {count}x")

    print("\n" + "=" * 80)
    print("📊 REPORT B: NEW PROMPT (Accessible Style)")
    print("=" * 80)

    analyze_new = report_new["analyze"]
    suggestion_new = report_new["suggestion"]
    combined_new = analyze_new + "\n" + suggestion_new

    metrics_new = calculate_readability_score(combined_new)
    print(f"\n📈 Readability Metrics:")
    print(f"   Total chars: {metrics_new['total_chars']}")
    print(f"   Sentences: {metrics_new['sentences']}")
    print(f"   Avg sentence length: {metrics_new['avg_sentence_length']:.1f} chars")
    print(f"   Academic terms found: {metrics_new['total_academic_terms']}")
    print(f"   Academic density: {metrics_new['academic_density_per_1000_chars']} per 1000 chars")

    if metrics_new['academic_terms_found']:
        print(f"\n🔍 Academic terms detected:")
        for term, count in metrics_new['academic_terms_found'].items():
            print(f"   - {term}: {count}x")

    # Comparison
    print("\n" + "=" * 80)
    print("📊 COMPARISON")
    print("=" * 80)

    improvement_density = (
        (metrics_old['academic_density_per_1000_chars'] -
         metrics_new['academic_density_per_1000_chars']) /
        metrics_old['academic_density_per_1000_chars'] * 100
    ) if metrics_old['academic_density_per_1000_chars'] > 0 else 0

    print(f"\n✅ Academic density reduction: {improvement_density:.1f}%")
    print(f"   OLD: {metrics_old['academic_density_per_1000_chars']} terms/1000 chars")
    print(f"   NEW: {metrics_new['academic_density_per_1000_chars']} terms/1000 chars")

    print(f"\n✅ Academic term count reduction:")
    print(f"   OLD: {metrics_old['total_academic_terms']} terms")
    print(f"   NEW: {metrics_new['total_academic_terms']} terms")

    # Success criteria
    print("\n" + "=" * 80)
    print("🎯 SUCCESS CRITERIA")
    print("=" * 80)

    success = True

    if metrics_new['academic_density_per_1000_chars'] < metrics_old['academic_density_per_1000_chars']:
        print("✅ PASS: Academic density reduced")
    else:
        print("❌ FAIL: Academic density did not reduce")
        success = False

    if metrics_new['total_academic_terms'] < metrics_old['total_academic_terms']:
        print("✅ PASS: Academic term count reduced")
    else:
        print("❌ FAIL: Academic term count did not reduce")
        success = False

    # Check if NEW still has some professional terms (not zero)
    if 0 < metrics_new['total_academic_terms'] < metrics_old['total_academic_terms']:
        print("✅ PASS: Maintains professional credibility (some terms retained)")
    elif metrics_new['total_academic_terms'] == 0:
        print("⚠️  WARNING: No academic terms at all (may lack authority)")

    print("\n" + "=" * 80)
    if success:
        print("🎉 A/B TEST PASSED - NEW PROMPT IS BETTER")
    else:
        print("⚠️  A/B TEST FAILED - NEEDS FURTHER REFINEMENT")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(run_ab_test())
