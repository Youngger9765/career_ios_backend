"""
Unit tests for ScenarioGeneratorService
"""

import pytest

from app.services.scenario_generator_service import ScenarioGeneratorService


class TestScenarioGeneratorService:
    """測試情境生成服務"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return ScenarioGeneratorService()

    @pytest.fixture
    def sample_homework_transcript(self):
        """功課相關逐字稿範例"""
        return """
        媽媽：你回來了，功課寫完了嗎？
        孩子：還沒，我等一下再寫。
        媽媽：每天都這樣說，結果都拖到很晚。
        孩子：我先休息一下不行嗎？
        媽媽：你已經休息很久了，趕快去寫功課。
        孩子：好啦好啦，煩死了。
        """

    @pytest.fixture
    def sample_screen_time_transcript(self):
        """手機使用相關逐字稿範例"""
        return """
        爸爸：你又在玩手機了？
        孩子：我只是看一下而已。
        爸爸：看一下？你已經看了兩個小時了！
        孩子：哪有那麼久...
        爸爸：把手機放下，去做別的事。
        孩子：我朋友都可以玩，為什麼我不行？
        """

    @pytest.fixture
    def sample_grades_transcript(self):
        """成績相關逐字稿範例"""
        return """
        媽媽：這次考試考得怎麼樣？
        孩子：還好啦...
        媽媽：還好是多少分？
        孩子：數學 65 分...
        媽媽：65 分？你有認真讀書嗎？
        孩子：我有讀啊，可是太難了。
        """

    # === Prompt Building Tests (Unit Tests - No API calls) ===

    def test_build_scenario_prompt_contains_options(
        self, service, sample_homework_transcript
    ):
        """Test prompt includes all scenario options"""
        prompt = service._build_scenario_prompt(sample_homework_transcript)

        for option in service.SCENARIO_OPTIONS:
            assert option in prompt

    def test_build_scenario_prompt_contains_transcript(
        self, service, sample_homework_transcript
    ):
        """Test prompt includes transcript content"""
        prompt = service._build_scenario_prompt(sample_homework_transcript)

        assert "功課寫完了嗎" in prompt
        assert "趕快去寫功課" in prompt

    def test_build_description_prompt_contains_transcript(
        self, service, sample_homework_transcript
    ):
        """Test description prompt includes transcript"""
        prompt = service._build_description_prompt(sample_homework_transcript)

        assert "功課" in prompt
        assert "50" in prompt  # 50字限制

    def test_scenario_options_are_valid(self, service):
        """Test all scenario options are lowercase"""
        for option in service.SCENARIO_OPTIONS:
            assert option == option.lower()
            assert " " not in option  # No spaces

    # === Integration Tests (Require API - mark as slow) ===

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_scenario_homework(
        self, service, sample_homework_transcript
    ):
        """Test scenario generation for homework-related conversation"""
        scenario = await service.generate_scenario(sample_homework_transcript)

        assert scenario in service.SCENARIO_OPTIONS
        # Should identify as homework
        assert scenario == "homework"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_scenario_screen_time(
        self, service, sample_screen_time_transcript
    ):
        """Test scenario generation for screen time conversation"""
        scenario = await service.generate_scenario(sample_screen_time_transcript)

        assert scenario in service.SCENARIO_OPTIONS
        # Should identify as screen_time
        assert scenario == "screen_time"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_scenario_grades(self, service, sample_grades_transcript):
        """Test scenario generation for grades conversation"""
        scenario = await service.generate_scenario(sample_grades_transcript)

        assert scenario in service.SCENARIO_OPTIONS
        # Should identify as grades
        assert scenario == "grades"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_scenario_description_not_empty(
        self, service, sample_homework_transcript
    ):
        """Test scenario description is generated"""
        description = await service.generate_scenario_description(
            sample_homework_transcript
        )

        assert description is not None
        assert len(description) > 0
        assert len(description) <= 100  # Should be concise

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_both(self, service, sample_homework_transcript):
        """Test generating both scenario and description"""
        scenario, description = await service.generate_both(sample_homework_transcript)

        assert scenario in service.SCENARIO_OPTIONS
        assert description is not None
        assert len(description) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_scenario_with_short_transcript(self, service):
        """Test with very short transcript"""
        short_transcript = "孩子：我不想寫功課"
        scenario = await service.generate_scenario(short_transcript)

        # Should still return a valid option
        assert scenario in service.SCENARIO_OPTIONS

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_scenario_fallback_to_custom(self, service):
        """Test fallback to custom for ambiguous content"""
        ambiguous_transcript = "今天天氣真好"
        scenario = await service.generate_scenario(ambiguous_transcript)

        # Should return a valid option (likely custom)
        assert scenario in service.SCENARIO_OPTIONS
