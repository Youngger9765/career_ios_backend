"""Prompt enhancement utilities for better rationale generation"""

from typing import Dict


def add_rationale_examples(base_prompt: str) -> str:
    """
    在 prompt 中加入正確/錯誤示範，強化理由說明要求

    Args:
        base_prompt: 原始 prompt 文字

    Returns:
        str: 加入示範後的 prompt
    """
    rationale_guidance = """

【重要：理論引用必須說明理由】

✅ 正確示範：
- 「根據 Super 生涯發展理論 [1]，案主 28 歲處於探索期，此階段個體會經歷試探與轉換，因此出現職涯迷茫是正常發展任務。」
- 「基於自我效能理論 [2]，案主過去成功經驗不足導致信心低落，建議透過小步驟成功經驗累積來提升效能感。」
- 「從敘事治療觀點 [3]，案主的問題故事受家庭期待影響，透過外化對話可協助其重新建構生涯敘事。」

❌ 錯誤示範（缺乏理由說明）：
- 「案主年齡 28 歲，處於探索期 [1]。」（只陳述事實，未說明理論如何支持判斷）
- 「使用卡片排序法 [2]。」（未解釋為何此技術適合此個案）
- 「參考理論 [3][4][5]。」（堆砌引用，無具體應用）

引用格式要求：
1. 說明理論內容（該理論認為什麼）
2. 連結個案情況（案主符合哪些特徵）
3. 推論結論（因此如何判斷/介入）
"""

    return base_prompt + rationale_guidance


def validate_prompt_has_rationale_requirements(prompt: str) -> Dict[str, bool]:
    """
    驗證 prompt 是否包含理由要求

    檢查項目：
    - 是否有示範
    - 是否有正確示範（✅）
    - 是否有錯誤示範（❌）

    Args:
        prompt: 要檢查的 prompt 文字

    Returns:
        dict: 驗證結果
    """
    has_good_example = "✅" in prompt and ("正確" in prompt or "根據" in prompt)
    has_bad_example = "❌" in prompt and ("錯誤" in prompt or "缺乏" in prompt)

    has_examples = (
        ("範例" in prompt or "示範" in prompt or "✅" in prompt or "❌" in prompt)
        and (has_good_example or has_bad_example)
    )

    return {
        "has_examples": has_examples,
        "has_good_example": has_good_example,
        "has_bad_example": has_bad_example
    }
