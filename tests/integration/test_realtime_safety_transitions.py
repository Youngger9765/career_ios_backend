"""
Integration tests for Realtime Safety Level Transitions

Tests if the system correctly transitions safety levels (and visual indicators)
when transcript content changes from dangerous to safe (or vice versa).

CRITICAL CONSTRAINT: Transcripts are CUMULATIVE (appended, not replaced)

Test Scenarios:
1. RED → GREEN: High-risk conversation + safe content → expect green
2. GREEN → RED: Safe conversation + dangerous content → expect red
3. RED → YELLOW → GREEN: Gradual de-escalation
4. GREEN → YELLOW → RED: Gradual escalation
"""

from fastapi.testclient import TestClient

from app.main import app

# Skip if GCP credentials not available
from tests.integration.test_realtime_api import (
    skip_without_gcp,
)


class TestSafetyLevelTransitions:
    """Test safety level transitions with cumulative transcripts"""

    @skip_without_gcp
    def test_red_to_green_transition(self):
        """
        Scenario 1: RED → GREEN Transition

        Initial State: High-risk conversation (violent language)
        Action: Append safe, positive conversation
        Expected:
        - Safety level: red → green
        - Circle color should change from red to green
        - Analysis interval should increase from 15s to 60s
        """
        with TestClient(app) as client:
            # Phase 1: Start with dangerous content (RED)
            initial_transcript = (
                "案主：我真的快要氣死了，我想打死他！這孩子就是不聽話！"
            )

            response_red = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": initial_transcript,
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我真的快要氣死了，我想打死他！這孩子就是不聽話！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response_red.status_code == 200
            data_red = response_red.json()

            # Verify RED safety level
            assert "safety_level" in data_red
            assert (
                data_red["safety_level"] == "red"
            ), f"Expected RED for violent content, got {data_red['safety_level']}"
            print(f"✅ Phase 1 - RED detected: {data_red['safety_level']}")
            print(f"   Summary: {data_red['summary']}")

            # Phase 2: Append positive, de-escalating content (expect GREEN)
            # CRITICAL: Cumulative transcript (append to initial)
            cumulative_transcript = f"""{initial_transcript}
諮詢師：我聽到你很生氣，讓我們一起深呼吸，慢慢來。
案主：好的...我試試看。（深呼吸）
諮詢師：你願意和我分享發生了什麼事嗎？
案主：其實我只是太累了，我知道不該對孩子發脾氣。謝謝你陪我冷靜下來。
諮詢師：你很棒，能夠覺察自己的情緒。我們一起想想如何和孩子溝通。
案主：好，我願意學習。我希望和孩子的關係可以更好。"""

            response_green = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": cumulative_transcript,
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我真的快要氣死了，我想打死他！這孩子就是不聽話！",
                        },
                        {
                            "speaker": "counselor",
                            "text": "我聽到你很生氣，讓我們一起深呼吸，慢慢來。",
                        },
                        {"speaker": "client", "text": "好的...我試試看。（深呼吸）"},
                        {
                            "speaker": "counselor",
                            "text": "你願意和我分享發生了什麼事嗎？",
                        },
                        {
                            "speaker": "client",
                            "text": "其實我只是太累了，我知道不該對孩子發脾氣。謝謝你陪我冷靜下來。",
                        },
                        {
                            "speaker": "counselor",
                            "text": "你很棒，能夠覺察自己的情緒。我們一起想想如何和孩子溝通。",
                        },
                        {
                            "speaker": "client",
                            "text": "好，我願意學習。我希望和孩子的關係可以更好。",
                        },
                    ],
                    "time_range": "1:00-2:00",
                },
            )

            assert response_green.status_code == 200
            data_green = response_green.json()

            # Verify GREEN safety level (de-escalation successful)
            assert "safety_level" in data_green
            assert (
                data_green["safety_level"] == "green"
            ), f"Expected GREEN after de-escalation, got {data_green['safety_level']}"
            print(f"✅ Phase 2 - GREEN detected: {data_green['safety_level']}")
            print(f"   Summary: {data_green['summary']}")
            print("   🎯 RED → GREEN transition successful!")

    @skip_without_gcp
    def test_green_to_red_transition(self):
        """
        Scenario 2: GREEN → RED Transition

        Initial State: Normal, safe conversation
        Action: Append dangerous, high-risk content
        Expected:
        - Safety level: green → red
        - Circle color should change from green to red
        - Analysis interval should decrease from 60s to 15s
        """
        with TestClient(app) as client:
            # Phase 1: Start with normal, safe content (GREEN)
            initial_transcript = """諮詢師：你好，今天想聊什麼呢？
案主：最近孩子在學校交了新朋友，我很開心。
諮詢師：聽起來很不錯！
案主：是的，他變得更開朗了。"""

            response_green = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": initial_transcript,
                    "speakers": [
                        {"speaker": "counselor", "text": "你好，今天想聊什麼呢？"},
                        {
                            "speaker": "client",
                            "text": "最近孩子在學校交了新朋友，我很開心。",
                        },
                        {"speaker": "counselor", "text": "聽起來很不錯！"},
                        {"speaker": "client", "text": "是的，他變得更開朗了。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response_green.status_code == 200
            data_green = response_green.json()

            # Verify GREEN safety level
            assert "safety_level" in data_green
            assert (
                data_green["safety_level"] == "green"
            ), f"Expected GREEN for calm content, got {data_green['safety_level']}"
            print(f"✅ Phase 1 - GREEN detected: {data_green['safety_level']}")
            print(f"   Summary: {data_green['summary']}")

            # Phase 2: Append dangerous content (expect RED)
            # CRITICAL: Cumulative transcript
            cumulative_transcript = f"""{initial_transcript}
諮詢師：那很好啊，你一定很欣慰。
案主：但是...昨天他又不聽話了，我真的受不了了！
諮詢師：發生了什麼事？
案主：他一直玩手機不寫功課，我氣到想打死他！他就是故意激怒我！
案主：我真的快要崩潰了，有時候我想乾脆去死算了。"""

            response_red = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": cumulative_transcript,
                    "speakers": [
                        {"speaker": "counselor", "text": "你好，今天想聊什麼呢？"},
                        {
                            "speaker": "client",
                            "text": "最近孩子在學校交了新朋友，我很開心。",
                        },
                        {"speaker": "counselor", "text": "聽起來很不錯！"},
                        {"speaker": "client", "text": "是的，他變得更開朗了。"},
                        {"speaker": "counselor", "text": "那很好啊，你一定很欣慰。"},
                        {
                            "speaker": "client",
                            "text": "但是...昨天他又不聽話了，我真的受不了了！",
                        },
                        {"speaker": "counselor", "text": "發生了什麼事？"},
                        {
                            "speaker": "client",
                            "text": "他一直玩手機不寫功課，我氣到想打死他！他就是故意激怒我！",
                        },
                        {
                            "speaker": "client",
                            "text": "我真的快要崩潰了，有時候我想乾脆去死算了。",
                        },
                    ],
                    "time_range": "1:00-2:00",
                },
            )

            assert response_red.status_code == 200
            data_red = response_red.json()

            # Verify RED safety level (escalation detected)
            assert "safety_level" in data_red
            assert (
                data_red["safety_level"] == "red"
            ), f"Expected RED after violent content added, got {data_red['safety_level']}"
            print(f"✅ Phase 2 - RED detected: {data_red['safety_level']}")
            print(f"   Summary: {data_red['summary']}")
            print("   🎯 GREEN → RED transition successful!")

    @skip_without_gcp
    def test_red_to_yellow_to_green_gradual_transition(self):
        """
        Scenario 3: RED → YELLOW → GREEN Gradual Transition

        Initial State: Critical risk (violent language)
        Action: Gradually add de-escalating content
        Expected:
        - Safety level: red → yellow → green
        - Circle gradient changes gradually
        - Analysis interval: 15s → 30s → 60s
        """
        with TestClient(app) as client:
            # Phase 1: RED (violent, crisis)
            red_transcript = (
                "案主：我快要受不了了！我想揍他一頓！這孩子就是故意氣死我的！"
            )

            response_red = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": red_transcript,
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我快要受不了了！我想揍他一頓！這孩子就是故意氣死我的！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response_red.status_code == 200
            data_red = response_red.json()
            assert data_red["safety_level"] == "red"
            print(f"✅ Phase 1 - RED: {data_red['safety_level']}")

            # Phase 2: YELLOW (frustration, but less extreme)
            yellow_transcript = f"""{red_transcript}
諮詢師：我聽到你的憤怒，先深呼吸好嗎？
案主：好...（呼吸）我真的很煩，他都不聽話。
諮詢師：你感覺很受挫，對嗎？
案主：對，我快被他氣死了，但我知道不能打他。"""

            response_yellow = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": yellow_transcript,
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我快要受不了了！我想揍他一頓！這孩子就是故意氣死我的！",
                        },
                        {
                            "speaker": "counselor",
                            "text": "我聽到你的憤怒，先深呼吸好嗎？",
                        },
                        {
                            "speaker": "client",
                            "text": "好...（呼吸）我真的很煩，他都不聽話。",
                        },
                        {"speaker": "counselor", "text": "你感覺很受挫，對嗎？"},
                        {
                            "speaker": "client",
                            "text": "對，我快被他氣死了，但我知道不能打他。",
                        },
                    ],
                    "time_range": "1:00-2:00",
                },
            )

            assert response_yellow.status_code == 200
            data_yellow = response_yellow.json()
            assert data_yellow["safety_level"] == "yellow"
            print(f"✅ Phase 2 - YELLOW: {data_yellow['safety_level']}")

            # Phase 3: GREEN (calm, positive)
            green_transcript = f"""{yellow_transcript}
諮詢師：你能覺察自己的情緒，這很好。我們一起想想怎麼辦。
案主：好的，謝謝你。我冷靜多了。
諮詢師：你想要和孩子建立更好的關係嗎？
案主：當然，我很愛他。我希望我們能好好溝通，不要總是吵架。
諮詢師：那我們來討論一些具體的溝通方法。
案主：好，我願意試試看。我相信我可以做得更好。"""

            response_green = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": green_transcript,
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我快要受不了了！我想揍他一頓！這孩子就是故意氣死我的！",
                        },
                        {
                            "speaker": "counselor",
                            "text": "我聽到你的憤怒，先深呼吸好嗎？",
                        },
                        {
                            "speaker": "client",
                            "text": "好...（呼吸）我真的很煩，他都不聽話。",
                        },
                        {"speaker": "counselor", "text": "你感覺很受挫，對嗎？"},
                        {
                            "speaker": "client",
                            "text": "對，我快被他氣死了，但我知道不能打他。",
                        },
                        {
                            "speaker": "counselor",
                            "text": "你能覺察自己的情緒，這很好。我們一起想想怎麼辦。",
                        },
                        {"speaker": "client", "text": "好的，謝謝你。我冷靜多了。"},
                        {
                            "speaker": "counselor",
                            "text": "你想要和孩子建立更好的關係嗎？",
                        },
                        {
                            "speaker": "client",
                            "text": "當然，我很愛他。我希望我們能好好溝通，不要總是吵架。",
                        },
                        {
                            "speaker": "counselor",
                            "text": "那我們來討論一些具體的溝通方法。",
                        },
                        {
                            "speaker": "client",
                            "text": "好，我願意試試看。我相信我可以做得更好。",
                        },
                    ],
                    "time_range": "2:00-3:00",
                },
            )

            assert response_green.status_code == 200
            data_green = response_green.json()
            assert data_green["safety_level"] == "green"
            print(f"✅ Phase 3 - GREEN: {data_green['safety_level']}")
            print("   🎯 RED → YELLOW → GREEN gradual transition successful!")

    @skip_without_gcp
    def test_green_to_yellow_to_red_escalation(self):
        """
        Scenario 4: GREEN → YELLOW → RED Escalation

        Initial State: Safe conversation
        Action: Gradually add escalating concerns
        Expected:
        - Safety level: green → yellow → red
        - Circle gradient changes from green to red
        - Analysis interval: 60s → 30s → 15s
        """
        with TestClient(app) as client:
            # Phase 1: GREEN (safe, calm)
            green_transcript = """諮詢師：今天感覺如何？
案主：還不錯，孩子最近表現很好。
諮詢師：很高興聽到這個消息。
案主：是的，我很開心。"""

            response_green = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": green_transcript,
                    "speakers": [
                        {"speaker": "counselor", "text": "今天感覺如何？"},
                        {"speaker": "client", "text": "還不錯，孩子最近表現很好。"},
                        {"speaker": "counselor", "text": "很高興聽到這個消息。"},
                        {"speaker": "client", "text": "是的，我很開心。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response_green.status_code == 200
            data_green = response_green.json()
            assert data_green["safety_level"] == "green"
            print(f"✅ Phase 1 - GREEN: {data_green['safety_level']}")

            # Phase 2: YELLOW (frustration emerging)
            yellow_transcript = f"""{green_transcript}
諮詢師：那很好，繼續保持。
案主：不過...今天他又開始不聽話了。
諮詢師：發生什麼事了？
案主：他說謊，我真的很煩，快被他氣死了。"""

            response_yellow = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": yellow_transcript,
                    "speakers": [
                        {"speaker": "counselor", "text": "今天感覺如何？"},
                        {"speaker": "client", "text": "還不錯，孩子最近表現很好。"},
                        {"speaker": "counselor", "text": "很高興聽到這個消息。"},
                        {"speaker": "client", "text": "是的，我很開心。"},
                        {"speaker": "counselor", "text": "那很好，繼續保持。"},
                        {"speaker": "client", "text": "不過...今天他又開始不聽話了。"},
                        {"speaker": "counselor", "text": "發生什麼事了？"},
                        {
                            "speaker": "client",
                            "text": "他說謊，我真的很煩，快被他氣死了。",
                        },
                    ],
                    "time_range": "1:00-2:00",
                },
            )

            assert response_yellow.status_code == 200
            data_yellow = response_yellow.json()
            assert data_yellow["safety_level"] == "yellow"
            print(f"✅ Phase 2 - YELLOW: {data_yellow['safety_level']}")

            # Phase 3: RED (violent, crisis)
            red_transcript = f"""{yellow_transcript}
諮詢師：你感覺很生氣...
案主：何止生氣！我真的受不了了！我想打死他！
案主：我恨死他了！他就是故意要把我逼瘋！
案主：我覺得活著沒意義，每天都是這樣的折磨。"""

            response_red = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": red_transcript,
                    "speakers": [
                        {"speaker": "counselor", "text": "今天感覺如何？"},
                        {"speaker": "client", "text": "還不錯，孩子最近表現很好。"},
                        {"speaker": "counselor", "text": "很高興聽到這個消息。"},
                        {"speaker": "client", "text": "是的，我很開心。"},
                        {"speaker": "counselor", "text": "那很好，繼續保持。"},
                        {"speaker": "client", "text": "不過...今天他又開始不聽話了。"},
                        {"speaker": "counselor", "text": "發生什麼事了？"},
                        {
                            "speaker": "client",
                            "text": "他說謊，我真的很煩，快被他氣死了。",
                        },
                        {"speaker": "counselor", "text": "你感覺很生氣..."},
                        {
                            "speaker": "client",
                            "text": "何止生氣！我真的受不了了！我想打死他！",
                        },
                        {
                            "speaker": "client",
                            "text": "我恨死他了！他就是故意要把我逼瘋！",
                        },
                        {
                            "speaker": "client",
                            "text": "我覺得活著沒意義，每天都是這樣的折磨。",
                        },
                    ],
                    "time_range": "2:00-3:00",
                },
            )

            assert response_red.status_code == 200
            data_red = response_red.json()
            assert data_red["safety_level"] == "red"
            print(f"✅ Phase 3 - RED: {data_red['safety_level']}")
            print("   🎯 GREEN → YELLOW → RED escalation detected successfully!")

    @skip_without_gcp
    def test_safety_level_affects_suggestions(self):
        """
        Verify that safety level affects the quality and urgency of suggestions

        RED should trigger more urgent, directive suggestions
        GREEN should provide more reflective, educational suggestions
        """
        with TestClient(app) as client:
            # Test RED - Should get urgent suggestions
            red_response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "案主：我想打死他！受不了了！我要去死算了！",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我想打死他！受不了了！我要去死算了！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert red_response.status_code == 200
            data_red = red_response.json()
            assert data_red["safety_level"] == "red"

            # RED suggestions should be more urgent/directive
            assert len(data_red["suggestions"]) > 0
            print(f"🔴 RED suggestions (urgent): {data_red['suggestions']}")

            # Test GREEN - Should get reflective suggestions
            green_response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "案主：我和孩子今天一起玩遊戲，很開心。我們的關係越來越好了。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我和孩子今天一起玩遊戲，很開心。我們的關係越來越好了。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert green_response.status_code == 200
            data_green = green_response.json()
            assert data_green["safety_level"] == "green"

            # GREEN suggestions should be more reflective/educational
            assert len(data_green["suggestions"]) > 0
            print(f"🟢 GREEN suggestions (reflective): {data_green['suggestions']}")

    @skip_without_gcp
    def test_cumulative_transcript_handling(self):
        """
        Verify that the system correctly handles cumulative transcripts

        The latest content should influence safety assessment most,
        but earlier context should still be considered.
        """
        with TestClient(app) as client:
            # Build cumulative transcript progressively
            base = "案主：孩子今天很乖。"

            # Add dangerous content
            dangerous = f"{base}\n案主：但昨天我想打死他！"

            # Add calming content
            calm = f"{dangerous}\n諮詢師：我們深呼吸，冷靜下來。\n案主：好的，我冷靜多了，謝謝。"

            # Test each stage
            response1 = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": base,
                    "speakers": [{"speaker": "client", "text": "孩子今天很乖。"}],
                    "time_range": "0:00-1:00",
                },
            )

            response2 = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": dangerous,
                    "speakers": [
                        {"speaker": "client", "text": "孩子今天很乖。"},
                        {"speaker": "client", "text": "但昨天我想打死他！"},
                    ],
                    "time_range": "1:00-2:00",
                },
            )

            response3 = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": calm,
                    "speakers": [
                        {"speaker": "client", "text": "孩子今天很乖。"},
                        {"speaker": "client", "text": "但昨天我想打死他！"},
                        {"speaker": "counselor", "text": "我們深呼吸，冷靜下來。"},
                        {"speaker": "client", "text": "好的，我冷靜多了，謝謝。"},
                    ],
                    "time_range": "2:00-3:00",
                },
            )

            # Verify transitions
            data1 = response1.json()
            data2 = response2.json()
            data3 = response3.json()

            print("📊 Cumulative handling:")
            print(f"   Stage 1 (calm): {data1['safety_level']}")
            print(f"   Stage 2 (add danger): {data2['safety_level']}")
            print(f"   Stage 3 (add calm): {data3['safety_level']}")

            # Stage 2 should detect danger even with calm beginning
            assert (
                data2["safety_level"] == "red"
            ), "Should detect dangerous content in cumulative transcript"
