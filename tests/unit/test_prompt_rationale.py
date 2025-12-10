"""Unit tests for prompt rationale requirements (M2.2)"""

from app.utils.prompt_enhancer import (
    add_rationale_examples,
    validate_prompt_has_rationale_requirements,
)


class TestPromptRationaleExamples:
    """測試 prompt 中的理由示範"""

    def test_add_good_examples(self):
        """測試加入正確示範"""
        base_prompt = "請撰寫報告"

        enhanced_prompt = add_rationale_examples(base_prompt)

        # 應包含正確示範（✅）
        assert "✅" in enhanced_prompt or "正確" in enhanced_prompt
        assert "根據" in enhanced_prompt
        assert "理論" in enhanced_prompt

    def test_add_bad_examples(self):
        """測試加入錯誤示範"""
        base_prompt = "請撰寫報告"

        enhanced_prompt = add_rationale_examples(base_prompt)

        # 應包含錯誤示範（❌）
        assert "❌" in enhanced_prompt or "錯誤" in enhanced_prompt
        assert "案主" in enhanced_prompt

    def test_example_quality(self):
        """測試示範品質"""
        base_prompt = "請撰寫報告"

        enhanced_prompt = add_rationale_examples(base_prompt)

        # 應該有對比
        assert enhanced_prompt.count("✅") >= 1
        assert enhanced_prompt.count("❌") >= 1

        # 應該明確指出差異
        assert (
            "說明理由" in enhanced_prompt
            or "因為" in enhanced_prompt
            or "根據" in enhanced_prompt
        )


class TestPromptValidation:
    """測試 prompt 是否符合理由要求"""

    def test_valid_prompt_with_rationale_requirements(self):
        """測試包含理由要求的 prompt"""
        prompt = """
        請撰寫報告，並說明理由。

        範例：
        ✅ 正確：根據 Super 理論 [1]，案主處於探索期，因此建議...
        ❌ 錯誤：案主年齡 25 歲。[1]
        """

        result = validate_prompt_has_rationale_requirements(prompt)

        assert result["has_examples"] is True
        assert result["has_good_example"] is True
        assert result["has_bad_example"] is True

    def test_invalid_prompt_without_examples(self):
        """測試缺少示範的 prompt"""
        prompt = "請撰寫報告並引用理論 [1]"

        result = validate_prompt_has_rationale_requirements(prompt)

        assert result["has_examples"] is False

    def test_prompt_with_only_good_examples(self):
        """測試只有正確示範的 prompt"""
        prompt = """
        範例：
        ✅ 根據理論 [1]，案主...
        """

        result = validate_prompt_has_rationale_requirements(prompt)

        assert result["has_good_example"] is True
        assert result["has_bad_example"] is False


class TestRationaleEnforcement:
    """測試理由強制要求"""

    def test_rationale_keywords_present(self):
        """測試理由關鍵詞存在"""
        prompt = add_rationale_examples("請撰寫報告")

        # 應包含引導詞
        rationale_keywords = ["根據", "基於", "因為", "由於", "考量", "理由"]

        assert any(kw in prompt for kw in rationale_keywords)

    def test_explicit_instruction(self):
        """測試明確指示"""
        prompt = add_rationale_examples("請撰寫報告")

        # 應明確要求說明理由
        assert "說明" in prompt or "解釋" in prompt or "為何" in prompt


class TestPromptStructure:
    """測試 prompt 結構"""

    def test_examples_before_task(self):
        """測試示範應在任務描述之後"""
        base_prompt = "請撰寫個案報告\n\n【五、多層次因素分析】"

        enhanced_prompt = add_rationale_examples(base_prompt)

        # 原始內容應保留
        assert "請撰寫個案報告" in enhanced_prompt
        assert "【五、多層次因素分析】" in enhanced_prompt

        # 示範應該加入
        assert "✅" in enhanced_prompt or "範例" in enhanced_prompt

    def test_preserves_original_content(self):
        """測試保留原始內容"""
        base_prompt = "這是重要的指示\n請務必遵守"

        enhanced_prompt = add_rationale_examples(base_prompt)

        # 原始內容必須完整保留
        assert "這是重要的指示" in enhanced_prompt
        assert "請務必遵守" in enhanced_prompt
