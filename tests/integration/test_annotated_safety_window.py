"""
Comprehensive test suite for annotated safety window approach.

This test suite validates the improved safety assessment approach:
1. Full transcript sent to AI for context
2. Last 5-10 speaker turns annotated for safety assessment
3. AI instructed to assess safety based on annotated section only
4. Backend safety assessment serves as fallback validation

Test Categories:
- Experiment 1: RED → GREEN Relaxation
- Experiment 2: GREEN → RED Escalation
- Experiment 3: Compare Approaches
- Experiment 4: Boundary Cases
- Experiment 5: AI Compliance Check
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Skip if GCP credentials not available
from tests.integration.test_realtime_api import skip_without_gcp


class TestExperiment1RedToGreenRelaxation:
    """Experiment 1: Test RED → GREEN relaxation with annotated window.

    Objective: Verify that AI correctly assesses recent conversation as GREEN
    even when full transcript contains old dangerous content.
    """

    @skip_without_gcp
    def test_red_to_green_with_annotation(self):
        """Test RED → GREEN transition using annotated window.

        Scenario:
        - Full transcript starts with dangerous content ("打死")
        - Last 5-7 speaker turns are calm and positive
        - Expected: AI should assess as GREEN (recent conversation is calm)
        - Backend should also assess as GREEN (sliding window of 10 turns)

        Note: Need 11+ total speakers to push danger outside backend's 10-turn window
        """
        with TestClient(app) as client:
            # Build conversation: old danger + recent calm
            speakers = [
                {"speaker": "counselor", "text": "你好，今天想聊什麼？"},
                {
                    "speaker": "client",
                    "text": "我真的很想打死我兒子！",
                },  # RED keyword (turn 2)
                {"speaker": "counselor", "text": "我聽到你的憤怒了..."},
                {"speaker": "client", "text": "對不起，我不應該這樣說"},
                {"speaker": "counselor", "text": "沒關係，我們一起處理"},
                {"speaker": "client", "text": "謝謝你，我冷靜多了"},
                {"speaker": "counselor", "text": "很好，我們繼續"},
                {"speaker": "client", "text": "我知道要怎麼做了"},
                {"speaker": "counselor", "text": "你很棒"},
                {"speaker": "client", "text": "我會試試看的"},
                {"speaker": "counselor", "text": "加油"},
                {
                    "speaker": "client",
                    "text": "謝謝你的鼓勵",
                },  # 12 total turns, danger outside 10-turn window
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Expected: GREEN (recent conversation is calm)
            # Even though "打死" appeared earlier
            assert "safety_level" in data
            assert data["safety_level"] == "green", (
                f"Expected GREEN for calm recent conversation, got {data['safety_level']}. "
                f"AI should assess based on annotated recent window, not full transcript."
            )

            print("✅ Experiment 1.1 PASSED: RED → GREEN relaxation with annotation")
            print(f"   Safety Level: {data['safety_level']}")
            print(f"   Summary: {data['summary']}")

    @skip_without_gcp
    def test_red_to_green_with_long_history(self):
        """Test RED → GREEN with longer conversation history.

        Scenario:
        - Very long transcript (15+ speaker turns)
        - Multiple dangerous keywords in early conversation
        - Last 5 turns are calm and reflective
        - Expected: GREEN (should not be affected by old danger)
        """
        with TestClient(app) as client:
            speakers = [
                # Early conversation with multiple red keywords
                {"speaker": "client", "text": "我想打死他！我真的受不了了！"},
                {"speaker": "counselor", "text": "我理解你很生氣"},
                {"speaker": "client", "text": "我恨死他了，他就是故意氣我的"},
                {"speaker": "counselor", "text": "讓我們深呼吸"},
                {"speaker": "client", "text": "好..."},
                # Middle conversation - de-escalating
                {"speaker": "counselor", "text": "你願意和我聊聊嗎？"},
                {"speaker": "client", "text": "其實我只是太累了"},
                {"speaker": "counselor", "text": "我理解"},
                {"speaker": "client", "text": "我知道不該對孩子發脾氣"},
                {"speaker": "counselor", "text": "你能覺察這點很好"},
                # Recent conversation - calm (last 5 turns)
                {"speaker": "client", "text": "謝謝你陪我冷靜下來"},
                {"speaker": "counselor", "text": "不客氣，我們一起想辦法"},
                {"speaker": "client", "text": "我願意學習更好的方式"},
                {"speaker": "counselor", "text": "很好，我相信你可以"},
                {"speaker": "client", "text": "我會努力的，謝謝你"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-3:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert (
                data["safety_level"] == "green"
            ), f"Expected GREEN with long history and calm recent turns, got {data['safety_level']}"

            print(
                "✅ Experiment 1.2 PASSED: RED → GREEN with long conversation history"
            )
            print(f"   Total speakers: {len(speakers)}")
            print(f"   Safety Level: {data['safety_level']}")


class TestExperiment2GreenToRedEscalation:
    """Experiment 2: Test GREEN → RED escalation with annotated window.

    Objective: Verify that AI correctly detects new danger in recent conversation
    even when earlier conversation was calm.
    """

    @skip_without_gcp
    def test_green_to_red_with_annotation(self):
        """Test GREEN → RED transition using annotated window.

        Scenario:
        - Calm start, dangerous end
        - Last 5 turns contain dangerous keywords
        - Expected: RED (recent conversation has danger)
        """
        with TestClient(app) as client:
            speakers = [
                {"speaker": "counselor", "text": "你好"},
                {"speaker": "client", "text": "我最近還不錯"},
                {"speaker": "counselor", "text": "很好"},
                {"speaker": "client", "text": "孩子也很乖"},
                {"speaker": "counselor", "text": "那很棒"},
                {"speaker": "client", "text": "但是今天..."},  # Start of recent window
                {"speaker": "counselor", "text": "發生什麼事？"},
                {"speaker": "client", "text": "他又不聽話了"},
                {"speaker": "counselor", "text": "你感覺如何？"},
                {"speaker": "client", "text": "我真的想殺了他！"},  # Recent danger
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Expected: RED (recent conversation has danger)
            assert (
                data["safety_level"] == "red"
            ), f"Expected RED for recent dangerous content, got {data['safety_level']}"

            print("✅ Experiment 2.1 PASSED: GREEN → RED escalation detected")
            print(f"   Safety Level: {data['safety_level']}")

    @skip_without_gcp
    def test_sudden_escalation_at_boundary(self):
        """Test escalation at exact window boundary.

        Scenario:
        - Dangerous keyword appears at exactly 5th turn from end
        - Should be included in recent window
        - Expected: RED
        """
        with TestClient(app) as client:
            speakers = [
                {"speaker": "counselor", "text": "今天感覺如何？"},
                {"speaker": "client", "text": "還不錯"},
                {"speaker": "counselor", "text": "很好"},
                {"speaker": "client", "text": "謝謝"},
                {"speaker": "counselor", "text": "繼續保持"},
                {
                    "speaker": "client",
                    "text": "我想打死他",
                },  # Exactly at 5th turn from end
                {"speaker": "counselor", "text": "發生什麼事？"},
                {"speaker": "client", "text": "他不聽話"},
                {"speaker": "counselor", "text": "我理解"},
                {"speaker": "client", "text": "我很生氣"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert (
                data["safety_level"] == "red"
            ), f"Expected RED when danger at exact boundary, got {data['safety_level']}"

            print("✅ Experiment 2.2 PASSED: Escalation at window boundary detected")


class TestExperiment3CompareApproaches:
    """Experiment 3: Compare annotated approach vs. full transcript approach.

    Objective: Measure accuracy, context awareness, cost, and speed differences.
    """

    @skip_without_gcp
    def test_accuracy_with_old_danger(self):
        """Verify accuracy improvement: old danger should not affect current assessment.

        This test validates the core improvement of the annotated approach.
        Note: Need 11+ speakers to push danger outside backend's 10-turn window.
        """
        with TestClient(app) as client:
            # Scenario: Old danger + recent calm (12 total turns)
            speakers = [
                {"speaker": "client", "text": "我想打死他！我真的受不了！"},
                {"speaker": "counselor", "text": "我理解你的憤怒"},
                {"speaker": "client", "text": "對不起...我不應該這樣說"},
                {"speaker": "counselor", "text": "沒關係，我們一起處理"},
                {"speaker": "client", "text": "謝謝你"},
                {"speaker": "counselor", "text": "你願意深呼吸嗎？"},
                {"speaker": "client", "text": "好的（深呼吸）"},
                {"speaker": "counselor", "text": "感覺如何？"},
                {"speaker": "client", "text": "我冷靜多了，謝謝"},
                {"speaker": "counselor", "text": "很好"},
                {"speaker": "client", "text": "我會繼續努力"},
                {"speaker": "counselor", "text": "加油"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # With annotated approach: should be GREEN (recent calm)
            # With full transcript approach: might be RED (contains danger)
            assert (
                data["safety_level"] == "green"
            ), "Annotated approach should assess as GREEN for calm recent conversation"

            # Verify suggestions are context-aware (reference full history)
            assert len(data.get("suggestions", [])) > 0, "Should provide suggestions"

            print("✅ Experiment 3.1 PASSED: Accuracy with old danger")
            print(f"   Safety Level: {data['safety_level']} (should be GREEN)")
            print(f"   Suggestions: {data['suggestions'][:2]}")  # Show first 2

    @skip_without_gcp
    def test_context_awareness_in_suggestions(self):
        """Verify suggestions show understanding of full conversation history.

        While safety assessment focuses on recent window, suggestions should
        demonstrate awareness of full context.
        """
        with TestClient(app) as client:
            speakers = [
                {
                    "speaker": "client",
                    "text": "我之前經常打罵孩子",
                },  # Historical context
                {"speaker": "counselor", "text": "你願意改變嗎？"},
                {"speaker": "client", "text": "是的，我知道這樣不對"},
                {"speaker": "counselor", "text": "很好"},
                {
                    "speaker": "client",
                    "text": "最近我在學習溫和教養",
                },  # Recent positive change
                {"speaker": "counselor", "text": "進展如何？"},
                {"speaker": "client", "text": "孩子有變乖一點"},
                {"speaker": "counselor", "text": "那很棒"},
                {"speaker": "client", "text": "但有時還是會忍不住"},
                {"speaker": "counselor", "text": "這是正常的過程"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Safety level should reflect recent state (GREEN or YELLOW)
            assert (
                data["safety_level"] in ["green", "yellow"]
            ), f"Expected GREEN/YELLOW for recent positive change, got {data['safety_level']}"

            # Suggestions should reference both history and current state
            # (This is a qualitative check - we verify suggestions exist)
            assert len(data.get("suggestions", [])) > 0
            assert len(data.get("summary", "")) > 0

            print("✅ Experiment 3.2 PASSED: Context awareness in suggestions")
            print(f"   Safety Level: {data['safety_level']}")
            print(f"   Summary length: {len(data['summary'])} chars")


class TestExperiment4BoundaryCases:
    """Experiment 4: Test boundary cases for annotated window.

    Objective: Validate behavior at exact window boundaries and edge cases.
    """

    @skip_without_gcp
    def test_exactly_at_window_boundary(self):
        """Test danger at exactly 5th turn from end (boundary case).

        Should be included in recent window (window is last 5 turns).
        """
        with TestClient(app) as client:
            # Create exactly 10 speaker turns
            # Danger at turn 5 (6th from start, 5th from end)
            speakers = [
                {"speaker": "counselor", "text": "你好"},
                {"speaker": "client", "text": "你好"},
                {"speaker": "counselor", "text": "今天如何？"},
                {"speaker": "client", "text": "還可以"},
                {"speaker": "counselor", "text": "發生什麼事？"},
                {"speaker": "client", "text": "我想打死他"},  # Turn 6 (5th from end)
                {"speaker": "counselor", "text": "我理解"},
                {"speaker": "client", "text": "抱歉"},
                {"speaker": "counselor", "text": "沒關係"},
                {"speaker": "client", "text": "謝謝"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Danger at 5th turn from end should be included in window
            assert (
                data["safety_level"] == "red"
            ), f"Expected RED when danger at 5th turn from end, got {data['safety_level']}"

            print("✅ Experiment 4.1 PASSED: Boundary case - danger included")

    @skip_without_gcp
    def test_just_outside_window_boundary(self):
        """Test danger at 11th+ turn from end (outside 10-turn backend window).

        Should NOT be included in any window.
        Note: Backend window = last 10 turns, AI window = last 5 turns.
        With 15 total turns, danger at turn 4 is 12th from end (outside both windows).
        """
        with TestClient(app) as client:
            # 15 speaker turns total
            # Danger at turn 4 (12th from end) - outside both windows
            speakers = [
                {"speaker": "counselor", "text": "你好"},
                {"speaker": "client", "text": "你好"},
                {"speaker": "counselor", "text": "今天如何？"},
                {
                    "speaker": "client",
                    "text": "我想打死他",
                },  # Turn 4 (12th from end, outside both windows)
                {"speaker": "counselor", "text": "我理解"},
                {"speaker": "client", "text": "對不起"},
                {"speaker": "counselor", "text": "沒關係"},
                {"speaker": "client", "text": "我冷靜了"},
                {"speaker": "counselor", "text": "很好"},
                {"speaker": "client", "text": "謝謝你"},
                {"speaker": "counselor", "text": "不客氣"},
                {"speaker": "client", "text": "我會努力的"},
                {"speaker": "counselor", "text": "加油"},
                {"speaker": "client", "text": "好的"},
                {"speaker": "counselor", "text": "再見"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Danger at 6th turn from end should be outside window
            assert (
                data["safety_level"] == "green"
            ), f"Expected GREEN when danger outside window, got {data['safety_level']}"

            print("✅ Experiment 4.2 PASSED: Boundary case - danger excluded")

    @skip_without_gcp
    def test_very_short_conversation(self):
        """Test with conversation shorter than window size.

        Should evaluate entire conversation.
        """
        with TestClient(app) as client:
            # Only 3 speaker turns (less than 5-turn window)
            speakers = [
                {"speaker": "counselor", "text": "你好"},
                {
                    "speaker": "client",
                    "text": "我想打死他",
                },  # Danger in short conversation
                {"speaker": "counselor", "text": "我理解"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should detect danger even in short conversation
            assert (
                data["safety_level"] == "red"
            ), f"Expected RED in short conversation with danger, got {data['safety_level']}"

            print("✅ Experiment 4.3 PASSED: Short conversation handled correctly")


class TestExperiment5AIComplianceCheck:
    """Experiment 5: Verify AI follows annotation instructions.

    Objective: Validate that AI actually uses annotated section for safety
    assessment, not the full transcript.
    """

    @skip_without_gcp
    def test_ai_uses_annotated_section(self):
        """Verify AI assesses based on annotated section, not full transcript.

        This is the critical test: does AI follow the instruction to use
        only the annotated section for safety assessment?

        Note: Need 11+ total speakers to push danger outside backend's 10-turn window
        """
        with TestClient(app) as client:
            # Build conversation with clear distinction:
            # - Full transcript: contains multiple red keywords
            # - Annotated section (last 5): completely calm
            speakers = [
                # Old conversation with red keywords (outside 10-turn window)
                {"speaker": "client", "text": "我想打死他！我恨死他了！"},
                {"speaker": "counselor", "text": "我理解你的憤怒"},
                {"speaker": "client", "text": "我真的受不了了"},
                {"speaker": "counselor", "text": "讓我們深呼吸"},
                {"speaker": "client", "text": "好..."},
                {"speaker": "counselor", "text": "慢慢來"},
                {"speaker": "client", "text": "我試試看"},
                # Recent conversation - completely calm (last 5 turns)
                {"speaker": "counselor", "text": "感覺如何？"},
                {"speaker": "client", "text": "我現在冷靜多了"},
                {"speaker": "counselor", "text": "很好"},
                {"speaker": "client", "text": "謝謝你的幫助"},
                {"speaker": "counselor", "text": "不客氣"},
                {"speaker": "client", "text": "我知道該怎麼做了"},  # 13 total turns
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # CRITICAL TEST: If AI follows instructions, should be GREEN
            # If AI ignores annotation and reads full transcript, would be RED
            assert data["safety_level"] == "green", (
                f"AI should assess as GREEN based on annotated section (last 5 turns). "
                f"Got {data['safety_level']}, which suggests AI may be reading full transcript."
            )

            print("✅ Experiment 5.1 PASSED: AI follows annotation instruction")
            print(f"   Safety Level: {data['safety_level']} (confirms AI compliance)")

    @skip_without_gcp
    def test_ai_suggestions_use_full_context(self):
        """Verify suggestions reference full conversation, not just annotated section.

        While safety assessment uses annotated section, suggestions should
        demonstrate understanding of full context.
        Note: Avoid danger keywords to prevent backend window from triggering.
        """
        with TestClient(app) as client:
            speakers = [
                # Early context: parent struggling with anger
                {"speaker": "client", "text": "我之前經常對孩子發脾氣"},
                {"speaker": "counselor", "text": "你願意改變嗎？"},
                {"speaker": "client", "text": "是的，我想學習"},
                # Middle: learning process
                {"speaker": "counselor", "text": "很好，我們一起努力"},
                {"speaker": "client", "text": "我開始嘗試溫和教養"},
                {"speaker": "counselor", "text": "進展如何？"},
                # Recent: positive progress (last 5 turns)
                {"speaker": "client", "text": "孩子有變乖一點"},
                {"speaker": "counselor", "text": "那很棒"},
                {"speaker": "client", "text": "我也比較不會生氣了"},
                {"speaker": "counselor", "text": "你做得很好"},
                {"speaker": "client", "text": "謝謝你的鼓勵"},
            ]

            transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": transcript,
                    "speakers": speakers,
                    "time_range": "0:00-2:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Safety should be GREEN (recent conversation is positive)
            assert data["safety_level"] == "green"

            # Suggestions should exist and reference the journey
            # (Qualitative check - we verify they exist)
            assert len(data.get("suggestions", [])) > 0
            assert len(data.get("summary", "")) > 10  # Non-trivial summary

            print("✅ Experiment 5.2 PASSED: Suggestions use full context")
            print(f"   Safety Level: {data['safety_level']}")
            print(f"   Number of suggestions: {len(data.get('suggestions', []))}")


@pytest.mark.skip(
    reason="Feature not yet implemented - ANNOTATED_SAFETY_WINDOW_TURNS and _build_annotated_transcript missing"
)
class TestAnnotatedWindowConfiguration:
    """Test annotated window configuration and helper functions."""

    def test_annotated_window_constant_exists(self):
        """Verify annotated window configuration constant is defined."""
        from app.api.realtime import ANNOTATED_SAFETY_WINDOW_TURNS

        assert (
            ANNOTATED_SAFETY_WINDOW_TURNS == 5
        ), f"Expected ANNOTATED_SAFETY_WINDOW_TURNS=5, got {ANNOTATED_SAFETY_WINDOW_TURNS}"

    def test_build_annotated_transcript_function(self):
        """Verify _build_annotated_transcript helper function works correctly."""
        from app.api.realtime import _build_annotated_transcript

        # Test with normal conversation
        speakers = [
            {"speaker": "counselor", "text": "你好"},
            {"speaker": "client", "text": "你好"},
            {"speaker": "counselor", "text": "今天如何？"},
            {"speaker": "client", "text": "還不錯"},
            {"speaker": "counselor", "text": "很好"},
            {"speaker": "client", "text": "謝謝"},
            {"speaker": "counselor", "text": "不客氣"},
        ]

        transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])
        annotated = _build_annotated_transcript(transcript, speakers)

        # Verify structure
        assert "完整對話逐字稿" in annotated
        assert "【最近對話 - 用於安全評估】" in annotated
        assert "CRITICAL" in annotated

        # Verify last 5 turns are in annotated section
        # Last 5 speakers: "今天如何？", "還不錯", "很好", "謝謝", "不客氣"
        assert "今天如何" in annotated
        assert "還不錯" in annotated
        assert "謝謝" in annotated

        print("✅ Test PASSED: _build_annotated_transcript function works correctly")

    def test_annotated_transcript_with_short_conversation(self):
        """Test annotation with conversation shorter than window."""
        from app.api.realtime import _build_annotated_transcript

        # Only 3 speakers (less than 5-turn window)
        speakers = [
            {"speaker": "counselor", "text": "你好"},
            {"speaker": "client", "text": "你好"},
            {"speaker": "counselor", "text": "今天如何？"},
        ]

        transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])
        annotated = _build_annotated_transcript(transcript, speakers)

        # Should include all speakers in annotated section
        assert "你好" in annotated
        assert "今天如何" in annotated

        print("✅ Test PASSED: Short conversation annotation works correctly")


# Test Report Summary
class TestReportSummary:
    """Generate test report summary for experiment results."""

    def test_generate_summary_report(self, capsys):
        """Generate summary report of all experiments.

        This is not a real test, but a helper to generate a summary report.
        Run this last to get experiment results overview.
        """
        print("\n" + "=" * 80)
        print("ANNOTATED SAFETY WINDOW - EXPERIMENT REPORT SUMMARY")
        print("=" * 80)
        print("\nTest Categories:")
        print("  1. RED → GREEN Relaxation: 2 tests")
        print("  2. GREEN → RED Escalation: 2 tests")
        print("  3. Compare Approaches: 2 tests")
        print("  4. Boundary Cases: 3 tests")
        print("  5. AI Compliance Check: 2 tests")
        print("  6. Configuration Tests: 3 tests")
        print("\nTotal: 14 comprehensive tests")
        print("\nKey Metrics to Track:")
        print("  - Accuracy: Does AI assess recent state correctly?")
        print("  - Context Awareness: Do suggestions show full history understanding?")
        print("  - Cost: Token usage (cached tokens vs. prompt tokens)")
        print("  - Speed: Response latency (ms)")
        print("\nRun all tests with:")
        print("  pytest tests/integration/test_annotated_safety_window.py -v")
        print("=" * 80 + "\n")
