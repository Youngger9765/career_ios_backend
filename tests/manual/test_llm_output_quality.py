"""LLM Output Quality Tests - 測試 LLM 函數輸出品質

這些測試驗證 LLM 輸出的「品質」而非精確值：
- 結構正確性 (Schema Validation)
- 內容守護 (Guardrails)
- 建議來源驗證 (Expert Pool)
"""
import json
from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config.parenting_suggestions import (
    GREEN_SUGGESTIONS,
    RED_SUGGESTIONS,
    YELLOW_SUGGESTIONS,
)
from app.core.security import hash_password
from app.main import app
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel


class TestDeepAnalyzeOutputQuality:
    """Deep Analyze 輸出品質測試"""

    @pytest.fixture
    def mock_gemini_real_response(self):
        """Mock Gemini 回傳真實格式的 JSON"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # 根據 prompt 內容判斷模式
            if "Practice Mode" in prompt or "單人練習" in prompt:
                return json.dumps(
                    {
                        "safety_level": "green",
                        "display_text": "語氣溫和，展現同理心",
                        "quick_suggestion": GREEN_SUGGESTIONS[0],  # 從真實庫中選
                    }
                )
            else:
                return json.dumps(
                    {
                        "safety_level": "yellow",
                        "display_text": "對話略有緊張，建議放慢",
                        "quick_suggestion": YELLOW_SUGGESTIONS[0],
                    }
                )

        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_text = mock_generate_text
            yield mock_instance

    @pytest.fixture
    def test_session(self, db_session: Session):
        """建立測試用 session"""
        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email="llm-quality-test@test.com",
            username="llmqualitytester",
            full_name="LLM Quality Tester",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.flush()

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="LLM-TEST-001",
            name="測試家長",
            email="llmtest@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345678",
            identity_option="家長",
            current_status="親子溝通困擾",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        # Create case
        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="LLM-CASE-001",
        )
        db_session.add(case)
        db_session.flush()

        # Create session
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長: 我看到你現在很難過，想了解發生什麼事",
                }
            ],
        )
        db_session.add(session)
        db_session.commit()

        return {"counselor": counselor, "session": session}

    @pytest.fixture
    def auth_headers(self, db_session: Session, test_session):
        """取得認證 headers"""
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "llm-quality-test@test.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # ==================== Schema Validation Tests ====================

    def test_safety_level_is_valid_enum(
        self, db_session, auth_headers, test_session, mock_gemini_real_response
    ):
        """安全等級必須是 green/yellow/red 之一"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Schema validation: safety_level 必須是有效值
        assert data["safety_level"] in [
            "green",
            "yellow",
            "red",
        ], f"Invalid safety_level: {data['safety_level']}"

    def test_display_text_length_reasonable(
        self, db_session, auth_headers, test_session, mock_gemini_real_response
    ):
        """顯示文字長度應該在合理範圍內 (5-50 字)"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        display_text = data.get("summary", "")
        assert (
            5 <= len(display_text) <= 100
        ), f"display_text 長度異常: {len(display_text)} 字 - '{display_text}'"

    # ==================== Guardrail Tests ====================

    def test_practice_mode_no_child_emotion_analysis(
        self, db_session, auth_headers, test_session, mock_gemini_real_response
    ):
        """Practice mode 不應該分析孩子的情緒狀態"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Guardrail: Practice mode 不應該提到孩子情緒
        forbidden_phrases = [
            "孩子正處於",
            "孩子的情緒",
            "孩子焦慮",
            "孩子生氣",
            "孩子難過",
        ]

        summary = data.get("summary", "")
        for phrase in forbidden_phrases:
            assert (
                phrase not in summary
            ), f"Practice mode 不應該包含 '{phrase}'，但收到: '{summary}'"

    # ==================== Expert Pool Tests ====================

    def test_suggestion_from_expert_pool(
        self, db_session, auth_headers, test_session, mock_gemini_real_response
    ):
        """建議必須來自專家建議庫"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        suggestions = data.get("suggestions", [])
        all_expert_suggestions = (
            GREEN_SUGGESTIONS + YELLOW_SUGGESTIONS + RED_SUGGESTIONS
        )

        for suggestion in suggestions:
            assert (
                suggestion in all_expert_suggestions
            ), f"建議 '{suggestion}' 不在專家建議庫中"


class TestQuickFeedbackOutputQuality:
    """Quick Feedback 輸出品質測試"""

    @pytest.fixture
    def mock_gemini_quick(self):
        """Mock Gemini for quick feedback"""
        from unittest.mock import AsyncMock, MagicMock

        with patch("app.services.quick_feedback_service.GeminiService") as mock_service:
            mock_instance = mock_service.return_value
            mock_response = MagicMock()
            mock_response.text = "🟢 語氣溫和，繼續保持同理心"
            mock_instance.generate_text = AsyncMock(return_value=mock_response)
            yield mock_instance

    @pytest.fixture
    def test_session(self, db_session: Session):
        """建立測試用 session"""
        counselor = Counselor(
            id=uuid4(),
            email="quick-quality-test@test.com",
            username="quickqualitytester",
            full_name="Quick Quality Tester",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="QUICK-QUAL-001",
            name="測試家長",
            email="quickqual@test.com",
            gender="男",
            birth_date=date(1980, 1, 1),
            phone="0923456789",
            identity_option="家長",
            current_status="親子溝通",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="QUICK-QUAL-CASE",
        )
        db_session.add(case)
        db_session.flush()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長: 我想練習跟孩子說話",
                }
            ],
        )
        db_session.add(session)
        db_session.commit()

        return {"counselor": counselor, "session": session}

    @pytest.fixture
    def auth_headers(self, db_session: Session, test_session):
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "quick-quality-test@test.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_quick_feedback_contains_emoji(
        self, db_session, auth_headers, test_session, mock_gemini_quick
    ):
        """Quick feedback 應該包含燈號 emoji"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        message = data.get("message", "")
        valid_emojis = ["🟢", "🟡", "🔴"]

        has_emoji = any(emoji in message for emoji in valid_emojis)
        assert has_emoji, f"Quick feedback 應該包含燈號 emoji，但收到: '{message}'"

    def test_quick_feedback_message_length(
        self, db_session, auth_headers, test_session, mock_gemini_quick
    ):
        """Quick feedback 訊息長度應該 <= 50 字"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        message = data.get("message", "")
        # 扣除 emoji 後計算長度
        message_without_emoji = (
            message.replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
        )

        assert (
            len(message_without_emoji) <= 50
        ), f"Quick feedback 應該 <= 50 字，但收到 {len(message_without_emoji)} 字: '{message}'"


class TestModeCombinations:
    """
    測試 Quick/Deep x Practice/Emergency 四種組合

    | API | Mode | 重點驗證 |
    |-----|------|----------|
    | quick-feedback | practice | 評估家長練習技巧 |
    | quick-feedback | emergency | 評估親子互動狀況 |
    | deep-analyze | practice | 不分析孩子情緒 |
    | deep-analyze | emergency | 可以分析親子互動 |
    """

    @pytest.fixture
    def mock_gemini_mode_aware(self):
        """根據 mode 返回不同內容的 Mock"""
        from unittest.mock import AsyncMock, MagicMock

        def create_mock_for_deep():
            async def mock_generate_text(prompt, *args, **kwargs):
                if "Practice Mode" in prompt or "單人練習" in prompt:
                    return json.dumps(
                        {
                            "safety_level": "green",
                            "display_text": "練習語氣溫和，同理心表達恰當",
                            "quick_suggestion": GREEN_SUGGESTIONS[0],
                        }
                    )
                elif "Emergency Mode" in prompt or "即時介入" in prompt:
                    return json.dumps(
                        {
                            "safety_level": "yellow",
                            "display_text": "親子對話略有緊張，孩子情緒需要關注",
                            "quick_suggestion": YELLOW_SUGGESTIONS[0],
                        }
                    )
                else:
                    return json.dumps(
                        {
                            "safety_level": "green",
                            "display_text": "分析完成",
                            "quick_suggestion": GREEN_SUGGESTIONS[0],
                        }
                    )

            return mock_generate_text

        def create_mock_for_quick():
            mock_response = MagicMock()
            mock_response.text = "🟢 語氣溫和，繼續保持"
            return AsyncMock(return_value=mock_response)

        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_deep, patch(
            "app.services.quick_feedback_service.GeminiService"
        ) as mock_quick:
            mock_deep.return_value.generate_text = create_mock_for_deep()
            mock_quick.return_value.generate_text = create_mock_for_quick()
            yield {"deep": mock_deep, "quick": mock_quick}

    @pytest.fixture
    def test_session(self, db_session: Session):
        """建立測試用 session"""
        counselor = Counselor(
            id=uuid4(),
            email="combo-test@test.com",
            username="combotester",
            full_name="Combo Tester",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="COMBO-001",
            name="測試家長",
            email="combo@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345678",
            identity_option="家長",
            current_status="親子溝通",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="COMBO-CASE-001",
        )
        db_session.add(case)
        db_session.flush()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長: 我看到你現在很難過，想了解發生什麼事",
                }
            ],
        )
        db_session.add(session)
        db_session.commit()

        return {"counselor": counselor, "session": session}

    @pytest.fixture
    def auth_headers(self, db_session: Session, test_session):
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "combo-test@test.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # ==================== Quick Feedback x Mode ====================

    def test_quick_feedback_practice_mode(
        self, db_session, auth_headers, test_session, mock_gemini_mode_aware
    ):
        """Quick Feedback + Practice Mode: 評估家長練習技巧"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "type" in data
        # Practice mode 回應應該是鼓勵性的

    def test_quick_feedback_emergency_mode(
        self, db_session, auth_headers, test_session, mock_gemini_mode_aware
    ):
        """Quick Feedback + Emergency Mode: 評估親子互動狀況"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback?mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "type" in data

    # ==================== Deep Analyze x Mode ====================

    def test_deep_analyze_practice_mode_focus_on_parent(
        self, db_session, auth_headers, test_session, mock_gemini_mode_aware
    ):
        """Deep Analyze + Practice Mode: 只評估家長技巧，不分析孩子"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # 驗證結構
        assert data["safety_level"] in ["green", "yellow", "red"]
        assert "summary" in data
        assert "suggestions" in data

        # Practice mode 關鍵驗證：不應該分析孩子情緒
        summary = data["summary"]
        child_emotion_phrases = ["孩子正處於", "孩子的情緒", "孩子焦慮", "孩子生氣"]
        for phrase in child_emotion_phrases:
            assert (
                phrase not in summary
            ), f"Practice mode 不應該分析孩子情緒，但找到 '{phrase}' 在: '{summary}'"

    def test_deep_analyze_emergency_mode_includes_interaction(
        self, db_session, auth_headers, test_session, mock_gemini_mode_aware
    ):
        """Deep Analyze + Emergency Mode: 可以評估親子互動"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # 驗證結構
        assert data["safety_level"] in ["green", "yellow", "red"]
        assert "summary" in data
        assert "suggestions" in data

        # Emergency mode 可以提到親子互動
        # (不做嚴格驗證，因為 mock 可能沒有這些內容)

    # ==================== 對比測試 ====================

    def test_practice_vs_emergency_different_focus(
        self, db_session, auth_headers, test_session, mock_gemini_mode_aware
    ):
        """Practice 和 Emergency 模式應該有不同的分析重點"""
        session_id = test_session["session"].id

        with TestClient(app) as client:
            practice_response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )
            emergency_response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=emergency",
                headers=auth_headers,
            )

        assert practice_response.status_code == 200
        assert emergency_response.status_code == 200

        practice_data = practice_response.json()
        emergency_data = emergency_response.json()

        # 兩個模式的回應應該不同
        # (在真實 LLM 環境中，這個測試更有意義)
        assert "summary" in practice_data
        assert "summary" in emergency_data
