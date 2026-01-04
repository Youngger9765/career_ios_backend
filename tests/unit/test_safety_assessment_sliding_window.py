"""
Unit tests for sliding window safety assessment mechanism.

Tests verify that the safety level assessment only evaluates the RECENT
conversation (last ~1 minute) rather than the entire cumulative transcript.
This allows rapid safety level relaxation when the conversation improves.
"""

from app.api.realtime import _assess_safety_level
from app.schemas.session import SafetyLevel


class TestSlidingWindowSafetyAssessment:
    """Test sliding window mechanism for safety level assessment"""

    def test_green_when_no_dangerous_keywords(self):
        """Test GREEN level when no dangerous keywords present"""
        transcript = "諮詢師：你今天感覺如何？\n案主：我感覺很好，謝謝。"
        speakers = [
            {"speaker": "counselor", "text": "你今天感覺如何？"},
            {"speaker": "client", "text": "我感覺很好，謝謝。"},
        ]

        safety_level = _assess_safety_level(transcript, speakers)
        assert safety_level == SafetyLevel.green

    def test_yellow_when_frustration_keywords_in_window(self):
        """Test YELLOW level when frustration keywords present in recent window"""
        transcript = "諮詢師：孩子的情況如何？\n案主：他真的氣死我了，完全不聽話。"
        speakers = [
            {"speaker": "counselor", "text": "孩子的情況如何？"},
            {"speaker": "client", "text": "他真的氣死我了，完全不聽話。"},
        ]

        safety_level = _assess_safety_level(transcript, speakers)
        assert safety_level == SafetyLevel.yellow

    def test_red_when_violent_keywords_in_window(self):
        """Test RED level when violent keywords present in recent window"""
        transcript = "諮詢師：發生什麼事了？\n案主：我真想打死他！"
        speakers = [
            {"speaker": "counselor", "text": "發生什麼事了？"},
            {"speaker": "client", "text": "我真想打死他！"},
        ]

        safety_level = _assess_safety_level(transcript, speakers)
        assert safety_level == SafetyLevel.red

    def test_rapid_relaxation_outside_window(self):
        """
        Test that safety level relaxes when dangerous keywords are OUTSIDE the window.

        This is the key test for the sliding window mechanism.
        Scenario:
        - 0:00 - Dangerous keyword "打死" (RED)
        - 0:30-1:30 - Multiple safe messages (11+ speaker turns)
        - Expected: GREEN (dangerous keyword is outside 10-turn window)
        """
        # Simulate a conversation where danger was EARLIER (outside window)
        speakers = [
            # Turn 0 (OLD - DANGER, but outside window)
            {"speaker": "client", "text": "我真想打死他！"},
            {"speaker": "counselor", "text": "我理解你的感受"},
            # Turns 1-10 (RECENT - SAFE, within window)
            {"speaker": "client", "text": "謝謝你聽我說"},
            {"speaker": "counselor", "text": "不客氣"},
            {"speaker": "client", "text": "我現在冷靜多了"},
            {"speaker": "counselor", "text": "很好"},
            {"speaker": "client", "text": "我想我需要學習情緒管理"},
            {"speaker": "counselor", "text": "這是很好的想法"},
            {"speaker": "client", "text": "你有什麼建議嗎？"},
            {"speaker": "counselor", "text": "我們可以一起探討"},
            {"speaker": "client", "text": "好的"},
            {"speaker": "counselor", "text": "首先要認識情緒"},
        ]

        # Build cumulative transcript (includes old danger)
        transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

        # The last 10 speaker turns should NOT include the dangerous keyword
        # So safety level should be GREEN
        safety_level = _assess_safety_level(transcript, speakers)
        assert (
            safety_level == SafetyLevel.green
        ), "Expected GREEN when dangerous keyword is outside the 10-turn window"

    def test_no_relaxation_within_window(self):
        """
        Test that safety level stays RED when dangerous keywords are WITHIN the window.

        Scenario:
        - Recent 8 turns, with "打死" in turn 5
        - Expected: RED (still within 10-turn window)
        """
        speakers = [
            {"speaker": "counselor", "text": "你今天感覺如何？"},
            {"speaker": "client", "text": "還可以"},
            {"speaker": "counselor", "text": "孩子的情況呢？"},
            {"speaker": "client", "text": "他又不聽話了"},
            {"speaker": "counselor", "text": "你有什麼感受？"},
            {"speaker": "client", "text": "我真想打死他！"},  # Turn 5 - DANGER
            {"speaker": "counselor", "text": "我理解你的憤怒"},
            {"speaker": "client", "text": "謝謝你"},
        ]

        transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

        # Dangerous keyword is in recent window (turn 5 of 8)
        safety_level = _assess_safety_level(transcript, speakers)
        assert (
            safety_level == SafetyLevel.red
        ), "Expected RED when dangerous keyword is within the 10-turn window"

    def test_fallback_to_character_window(self):
        """
        Test fallback to character-based window when speakers array is empty.

        Scenario:
        - Empty speakers array
        - Long transcript with old danger + recent safe content
        - Should use last 300 characters only
        """
        # Build transcript: old danger + enough safe content to push it out of window
        old_danger = "案主：我真想打死他！"
        # Need ~400+ chars to ensure last 300 chars don't include danger
        # Each repetition is ~13 chars, need 35+ repetitions
        safe_content = "諮詢師：我理解你的感受。" * 35  # ~455 chars

        transcript = f"{old_danger}\n{safe_content}"
        speakers = []  # Empty array to trigger fallback

        # Last 300 chars should NOT include "打死"
        assert "打死" not in transcript[-300:], "Test setup error: danger in window"

        safety_level = _assess_safety_level(transcript, speakers)
        assert (
            safety_level == SafetyLevel.green
        ), "Expected GREEN when using character fallback window"

    def test_short_transcript_uses_full_content(self):
        """
        Test that short transcripts use full content (no truncation).

        Scenario:
        - Transcript shorter than window size
        - Should evaluate entire content
        """
        transcript = "諮詢師：你好\n案主：我真的很生氣"
        speakers = [
            {"speaker": "counselor", "text": "你好"},
            {"speaker": "client", "text": "我真的很生氣"},
        ]

        # "生氣" is not in dangerous keywords, should be GREEN
        safety_level = _assess_safety_level(transcript, speakers)
        assert safety_level == SafetyLevel.green

    def test_yellow_relaxes_to_green_outside_window(self):
        """
        Test YELLOW -> GREEN relaxation outside window.

        Scenario:
        - Old YELLOW keyword "氣死"
        - 11+ turns of safe conversation
        - Expected: GREEN
        """
        speakers = [
            # Turn 0 (OLD - YELLOW, but outside window)
            {"speaker": "client", "text": "他氣死我了"},
            {"speaker": "counselor", "text": "我理解"},
            # Turns 1-10 (RECENT - SAFE)
            {"speaker": "client", "text": "但現在好多了"},
            {"speaker": "counselor", "text": "很好"},
            {"speaker": "client", "text": "我學會深呼吸"},
            {"speaker": "counselor", "text": "繼續保持"},
            {"speaker": "client", "text": "謝謝你的建議"},
            {"speaker": "counselor", "text": "不客氣"},
            {"speaker": "client", "text": "我會繼續努力"},
            {"speaker": "counselor", "text": "加油"},
            {"speaker": "client", "text": "好的"},
            {"speaker": "counselor", "text": "下次見"},
        ]

        transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

        safety_level = _assess_safety_level(transcript, speakers)
        assert (
            safety_level == SafetyLevel.green
        ), "Expected GREEN when YELLOW keyword is outside window"

    def test_exact_window_boundary(self):
        """
        Test behavior at exact window boundary (10 turns).

        Scenario:
        - Exactly 10 speaker turns total
        - Dangerous keyword in turn 0
        - Expected: Should evaluate all 10 turns (danger included)
        """
        speakers = [
            {"speaker": "client", "text": "我想打死他"},  # Turn 0 - DANGER
            {"speaker": "counselor", "text": "理解"},
            {"speaker": "client", "text": "現在好了"},
            {"speaker": "counselor", "text": "很好"},
            {"speaker": "client", "text": "謝謝"},
            {"speaker": "counselor", "text": "不客氣"},
            {"speaker": "client", "text": "再見"},
            {"speaker": "counselor", "text": "再見"},
            {"speaker": "client", "text": "下次見"},
            {"speaker": "counselor", "text": "好"},
        ]

        transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

        # Exactly 10 turns, danger is in the window
        safety_level = _assess_safety_level(transcript, speakers)
        assert (
            safety_level == SafetyLevel.red
        ), "Expected RED when exactly 10 turns and danger is included"

    def test_multiple_keywords_in_window(self):
        """
        Test prioritization when multiple keywords present.

        Scenario:
        - Both RED and YELLOW keywords in recent window
        - Expected: RED (higher priority)
        """
        speakers = [
            {"speaker": "client", "text": "他氣死我了"},  # YELLOW
            {"speaker": "counselor", "text": "發生什麼事？"},
            {"speaker": "client", "text": "而且我想打死他！"},  # RED
            {"speaker": "counselor", "text": "理解你的憤怒"},
        ]

        transcript = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

        safety_level = _assess_safety_level(transcript, speakers)
        assert (
            safety_level == SafetyLevel.red
        ), "Expected RED when both RED and YELLOW keywords present (RED has priority)"


class TestWindowConfiguration:
    """Test window configuration constants"""

    def test_window_constants_exist(self):
        """Verify that window configuration constants are defined"""
        from app.api.realtime import (
            SAFETY_WINDOW_CHARACTERS,
            SAFETY_WINDOW_SPEAKER_TURNS,
        )

        assert SAFETY_WINDOW_SPEAKER_TURNS == 10
        assert SAFETY_WINDOW_CHARACTERS == 300
