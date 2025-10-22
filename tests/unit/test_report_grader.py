"""Unit tests for report_grader - 報告品質評分系統測試"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.utils.report_grader import get_quality_grade, grade_report_with_llm


class TestGetQualityGrade:
    """測試等級判定函數"""

    def test_grade_excellent(self):
        """測試優秀等級 (≥90)"""
        assert get_quality_grade(100) == "優秀"
        assert get_quality_grade(95) == "優秀"
        assert get_quality_grade(90) == "優秀"

    def test_grade_good(self):
        """測試良好等級 (75-89)"""
        assert get_quality_grade(89) == "良好"
        assert get_quality_grade(80) == "良好"
        assert get_quality_grade(75) == "良好"

    def test_grade_pass(self):
        """測試及格等級 (60-74)"""
        assert get_quality_grade(74) == "及格"
        assert get_quality_grade(65) == "及格"
        assert get_quality_grade(60) == "及格"

    def test_grade_needs_improvement(self):
        """測試需改進等級 (<60)"""
        assert get_quality_grade(59) == "需改進"
        assert get_quality_grade(40) == "需改進"
        assert get_quality_grade(0) == "需改進"

    def test_grade_boundary_values(self):
        """測試邊界值"""
        assert get_quality_grade(89.9) == "良好"
        assert get_quality_grade(90.0) == "優秀"
        assert get_quality_grade(74.9) == "及格"
        assert get_quality_grade(75.0) == "良好"
        assert get_quality_grade(59.9) == "需改進"
        assert get_quality_grade(60.0) == "及格"


class TestGradeReportWithLLM:
    """測試 LLM 報告評分功能"""

    @pytest.fixture
    def mock_openai_client(self):
        """建立 Mock OpenAI Client"""
        return AsyncMock()

    @pytest.fixture
    def valid_grading_response(self):
        """有效的評分回應 JSON"""
        return {
            "problem_clarity_score": 12,
            "problem_clarity_feedback": "問題陳述清楚，能具體說明求助原因",
            "problem_evolution_score": 10,
            "problem_evolution_feedback": "問題演變過程描述完整",
            "help_seeking_score": 8,
            "help_seeking_feedback": "求助動機明確",
            "related_factors_score": 20,
            "related_factors_feedback": "多層次因素分析完整",
            "function_assessment_score": 8,
            "function_assessment_feedback": "功能評估全面",
            "problem_judgment_score": 8,
            "problem_judgment_feedback": "問題判斷有理論依據",
            "counseling_plan_score": 8,
            "counseling_plan_feedback": "諮商計劃具體可行",
            "implementation_eval_score": 4,
            "implementation_eval_feedback": "實施評估完整",
            "total_score": 78,
            "grade": "良好",
            "overall_feedback": "整體報告品質良好，結構完整",
            "strengths": ["理論應用得當", "分析深入", "計劃具體"],
            "improvements": ["可加強功能評估", "建議補充更多案例", "理論引用可更明確"]
        }

    @pytest.mark.asyncio
    async def test_grade_report_success_new_format(
        self, mock_openai_client, valid_grading_response
    ):
        """測試新版10段式報告評分成功"""
        # Mock OpenAI API response
        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_grading_response)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Execute
        result = await grade_report_with_llm(
            report_text="這是一份完整的新版10段式個案概念化報告...",
            use_legacy=False,
            client=mock_openai_client
        )

        # Verify
        assert result["total_score"] == 78
        assert result["grade"] == "良好"
        assert result["problem_clarity_score"] == 12
        assert len(result["strengths"]) >= 3
        assert len(result["improvements"]) >= 3

        # 驗證 API 被正確呼叫
        mock_openai_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs

        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert len(call_kwargs["messages"]) == 2
        assert "督導" in call_kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_grade_report_success_legacy_format(
        self, mock_openai_client
    ):
        """測試舊版5段式報告評分（分數較低）"""
        legacy_response = {
            "problem_clarity_score": 10,
            "problem_clarity_feedback": "問題陳述基本清楚",
            "problem_evolution_score": 5,  # 舊版缺少此段落
            "problem_evolution_feedback": "缺少問題演變分析",
            "help_seeking_score": 7,
            "help_seeking_feedback": "求助動機尚可",
            "related_factors_score": 15,  # 舊版分析較淺
            "related_factors_feedback": "因素分析不夠深入",
            "function_assessment_score": 3,  # 舊版缺少
            "function_assessment_feedback": "缺少功能評估",
            "problem_judgment_score": 6,
            "problem_judgment_feedback": "理論依據不明確",
            "counseling_plan_score": 6,
            "counseling_plan_feedback": "計劃較籠統",
            "implementation_eval_score": 2,
            "implementation_eval_feedback": "實施評估簡略",
            "total_score": 54,
            "grade": "需改進",
            "overall_feedback": "舊版格式結構簡化，建議升級為新版10段式",
            "strengths": ["基本問題描述清楚", "有初步諮商計劃", "文字表達流暢"],
            "improvements": ["補充問題演變分析", "加強功能評估", "理論引用需具體化"]
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(legacy_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await grade_report_with_llm(
            report_text="這是舊版5段式報告...",
            use_legacy=True,
            client=mock_openai_client
        )

        assert result["total_score"] == 54
        assert result["grade"] == "需改進"
        assert result["problem_evolution_score"] <= 5  # 舊版此項分數低
        assert result["function_assessment_score"] <= 3  # 舊版此項分數低

        # 驗證 prompt 包含舊版提示
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        user_prompt = call_kwargs["messages"][1]["content"]
        assert "舊版5段式報告" in user_prompt or "use_legacy" in str(result)

    @pytest.mark.asyncio
    async def test_grade_report_excellent_score(self, mock_openai_client):
        """測試優秀報告 (≥90分)"""
        excellent_response = {
            "problem_clarity_score": 14,
            "problem_clarity_feedback": "問題陳述極為清晰具體",
            "problem_evolution_score": 14,
            "problem_evolution_feedback": "問題演變分析深入完整",
            "help_seeking_score": 9,
            "help_seeking_feedback": "求助動機分析透徹",
            "related_factors_score": 24,
            "related_factors_feedback": "多層次因素分析極為完整",
            "function_assessment_score": 9,
            "function_assessment_feedback": "功能評估全面且專業",
            "problem_judgment_score": 9,
            "problem_judgment_feedback": "理論取向明確且應用得當",
            "counseling_plan_score": 9,
            "counseling_plan_feedback": "諮商計劃具體且有理論基礎",
            "implementation_eval_score": 5,
            "implementation_eval_feedback": "實施評估完整詳盡",
            "total_score": 93,
            "grade": "優秀",
            "overall_feedback": "這是一份優秀的個案概念化報告",
            "strengths": ["理論應用專業", "分析層次清晰", "計劃可行性高", "符合督導標準"],
            "improvements": ["已達優秀水準", "可考慮加入更多實證研究", "持續保持"]
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(excellent_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await grade_report_with_llm(
            report_text="這是一份優秀的新版報告...",
            use_legacy=False,
            client=mock_openai_client
        )

        assert result["total_score"] >= 90
        assert result["grade"] == "優秀"

    @pytest.mark.asyncio
    async def test_grade_report_missing_required_field(self, mock_openai_client):
        """測試缺少必要欄位的錯誤處理"""
        incomplete_response = {
            "problem_clarity_score": 10,
            # 缺少其他必要欄位
            "total_score": 70
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(incomplete_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(RuntimeError) as exc_info:
            await grade_report_with_llm(
                report_text="測試報告",
                use_legacy=False,
                client=mock_openai_client
            )

        assert "Missing required field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_grade_report_invalid_score_range(self, mock_openai_client):
        """測試分數超出範圍的錯誤處理"""
        invalid_response = {
            "problem_clarity_score": 20,  # 超過上限15
            "problem_clarity_feedback": "測試",
            "problem_evolution_score": 10,
            "problem_evolution_feedback": "測試",
            "help_seeking_score": 8,
            "help_seeking_feedback": "測試",
            "related_factors_score": 20,
            "related_factors_feedback": "測試",
            "function_assessment_score": 8,
            "function_assessment_feedback": "測試",
            "problem_judgment_score": 8,
            "problem_judgment_feedback": "測試",
            "counseling_plan_score": 8,
            "counseling_plan_feedback": "測試",
            "implementation_eval_score": 4,
            "implementation_eval_feedback": "測試",
            "total_score": 86,
            "grade": "良好"
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(invalid_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(RuntimeError) as exc_info:
            await grade_report_with_llm(
                report_text="測試報告",
                use_legacy=False,
                client=mock_openai_client
            )

        assert "Invalid problem_clarity_score" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_grade_report_json_decode_error(self, mock_openai_client):
        """測試 JSON 解析錯誤"""
        mock_message = MagicMock()
        mock_message.content = "This is not valid JSON"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError) as exc_info:
            await grade_report_with_llm(
                report_text="測試報告",
                use_legacy=False,
                client=mock_openai_client
            )

        assert "Failed to parse LLM response as JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_grade_report_openai_api_error(self, mock_openai_client):
        """測試 OpenAI API 錯誤"""
        from openai import RateLimitError

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_body = {"error": {"message": "Rate limit exceeded"}}

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                "Rate limit exceeded",
                response=mock_response,
                body=mock_body
            )
        )

        with pytest.raises(RuntimeError) as exc_info:
            await grade_report_with_llm(
                report_text="測試報告",
                use_legacy=False,
                client=mock_openai_client
            )

        assert "Error grading report with LLM" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_grade_report_all_scores_at_boundaries(self, mock_openai_client):
        """測試所有分數在邊界值的情況"""
        boundary_response = {
            "problem_clarity_score": 15,  # 最大值
            "problem_clarity_feedback": "完美",
            "problem_evolution_score": 15,  # 最大值
            "problem_evolution_feedback": "完美",
            "help_seeking_score": 10,  # 最大值
            "help_seeking_feedback": "完美",
            "related_factors_score": 25,  # 最大值
            "related_factors_feedback": "完美",
            "function_assessment_score": 10,  # 最大值
            "function_assessment_feedback": "完美",
            "problem_judgment_score": 10,  # 最大值
            "problem_judgment_feedback": "完美",
            "counseling_plan_score": 10,  # 最大值
            "counseling_plan_feedback": "完美",
            "implementation_eval_score": 5,  # 最大值
            "implementation_eval_feedback": "完美",
            "total_score": 100,  # 滿分
            "grade": "優秀",
            "overall_feedback": "滿分報告",
            "strengths": ["完美", "卓越", "專業"],
            "improvements": ["無需改進", "保持水準", "持續精進"]
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(boundary_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await grade_report_with_llm(
            report_text="完美報告",
            use_legacy=False,
            client=mock_openai_client
        )

        assert result["total_score"] == 100
        assert result["problem_clarity_score"] == 15
        assert result["related_factors_score"] == 25


class TestReportGraderRealWorldScenarios:
    """真實場景測試"""

    @pytest.fixture
    def mock_openai_client(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_real_counseling_report_with_theory(self, mock_openai_client):
        """測試真實諮商報告（含理論引用）"""
        real_report = """
        【個案概念化報告】

        一、當事人的問題
        案主小明（化名）因職涯發展困擾前來諮商...

        六、對當事人問題的判斷
        根據 Super 的生涯發展理論與 Holland 的職業興趣理論...
        """

        grading_response = {
            "problem_clarity_score": 13,
            "problem_clarity_feedback": "問題陳述清楚且具體",
            "problem_evolution_score": 11,
            "problem_evolution_feedback": "演變過程描述完整",
            "help_seeking_score": 8,
            "help_seeking_feedback": "動機明確",
            "related_factors_score": 21,
            "related_factors_feedback": "多層次分析完整",
            "function_assessment_score": 8,
            "function_assessment_feedback": "評估全面",
            "problem_judgment_score": 9,  # 有明確理論取向，給高分
            "problem_judgment_feedback": "理論應用得當：Super 生涯發展理論、Holland 職業興趣理論",
            "counseling_plan_score": 8,
            "counseling_plan_feedback": "計劃具體",
            "implementation_eval_score": 4,
            "implementation_eval_feedback": "評估完整",
            "total_score": 82,
            "grade": "良好",
            "overall_feedback": "理論引用明確，符合專業標準",
            "strengths": ["理論基礎扎實", "分析有依據", "專業術語使用正確"],
            "improvements": ["可補充更多案例", "建議加入實證研究", "強化評估工具"]
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(grading_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await grade_report_with_llm(
            report_text=real_report,
            use_legacy=False,
            client=mock_openai_client
        )

        assert result["total_score"] >= 80
        assert result["problem_judgment_score"] >= 8  # 有理論應用
        assert "理論" in result["problem_judgment_feedback"]

    @pytest.mark.asyncio
    async def test_report_with_only_citation_numbers(self, mock_openai_client):
        """測試只有引用編號沒有理論名稱的報告（應扣分）"""
        report_with_numbers_only = """
        六、對當事人問題的判斷
        根據相關理論 [1][2] 分析，案主的問題...
        （沒有明確寫出理論名稱）
        """

        grading_response = {
            "problem_clarity_score": 10,
            "problem_clarity_feedback": "問題陳述尚可",
            "problem_evolution_score": 9,
            "problem_evolution_feedback": "演變描述基本完整",
            "help_seeking_score": 7,
            "help_seeking_feedback": "動機描述一般",
            "related_factors_score": 18,
            "related_factors_feedback": "分析尚可",
            "function_assessment_score": 7,
            "function_assessment_feedback": "評估基本完整",
            "problem_judgment_score": 5,  # 理論引用不具體，扣分
            "problem_judgment_feedback": "理論引用不具體：只有 [1][2] 沒有理論名稱",
            "counseling_plan_score": 7,
            "counseling_plan_feedback": "計劃基本合理",
            "implementation_eval_score": 3,
            "implementation_eval_feedback": "評估簡略",
            "total_score": 66,
            "grade": "及格",
            "overall_feedback": "理論引用需明確化",
            "strengths": ["結構完整", "文字流暢", "有引用意識"],
            "improvements": ["理論名稱需明確標示", "避免只用編號", "加強理論說明"]
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(grading_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await grade_report_with_llm(
            report_text=report_with_numbers_only,
            use_legacy=False,
            client=mock_openai_client
        )

        assert result["total_score"] < 70
        assert result["problem_judgment_score"] <= 6  # 理論不具體，扣分
