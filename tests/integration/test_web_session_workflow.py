"""
Integration test for Web Session Workflow
模擬 realtime_counseling.html 的完整流程
TDD - Write tests first
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestWebSessionWorkflow:
    """Test complete web session workflow:
    client+case creation → session creation → append → analyze
    """

    @pytest.fixture
    def test_client(self, db_session: Session):
        """Create TestClient that uses the test database session"""
        return TestClient(app)

    @pytest.fixture
    def counselor(self, db_session: Session):
        """Create and return authenticated counselor for island_parents tenant"""
        counselor = Counselor(
            id=uuid4(),
            email=f"web-counselor-{uuid4().hex[:8]}@test.com",
            username=f"webcounselor{uuid4().hex[:6]}",
            full_name="Web Test Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()
        db_session.refresh(counselor)
        return counselor

    @pytest.fixture
    def auth_headers(self, test_client: TestClient, counselor: Counselor):
        """Return auth headers with JWT token"""
        login_response = test_client.post(
            "/api/auth/login",
            json={
                "email": counselor.email,
                "password": "ValidP@ssw0rd123",
                "tenant_id": counselor.tenant_id,
            },
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_complete_web_session_workflow(
        self,
        test_client: TestClient,
        db_session: Session,
        auth_headers: dict,
    ):
        """Test complete workflow from client creation to analysis"""
        # Step 1: Create client + case using /api/v1/ui/client-case
        print("\n[Step 1] Creating client + case...")
        client_case_response = test_client.post(
            "/api/v1/ui/client-case",
            headers=auth_headers,
            json={
                "name": "Web 測試孩子",
                "email": f"webtest-{uuid4().hex[:8]}@example.com",
                "gender": "不透露",
                "birth_date": "2015-01-01",
                "phone": "0900000000",
                "identity_option": "其他",
                "current_status": "進行中",
                "case_summary": "Web 即時諮詢測試",
                "case_goals": "測試 Session workflow",
                "grade": "小學三年級",
                "relationship": "媽媽",
            },
        )
        assert (
            client_case_response.status_code == 201
        ), f"Client-case creation failed: {client_case_response.text}"
        client_case_data = client_case_response.json()
        assert "client_id" in client_case_data
        assert "case_id" in client_case_data
        case_id = client_case_data["case_id"]
        print(
            f"[Step 1] Created client_id={client_case_data['client_id']}, case_id={case_id}"
        )

        # Step 2: Create session using /api/v1/sessions
        print("\n[Step 2] Creating session...")
        session_response = test_client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "case_id": str(case_id),
                "session_date": "2025-01-01",
                "name": "Web 即時諮詢",
            },
        )
        assert (
            session_response.status_code == 201
        ), f"Session creation failed: {session_response.text}"
        session_data = session_response.json()
        assert "id" in session_data
        session_id = session_data["id"]
        print(f"[Step 2] Created session_id={session_id}")

        # Step 3: Append recording using /api/v1/sessions/{id}/recordings/append
        print("\n[Step 3] Appending recording...")
        append_response = test_client.post(
            f"/api/v1/sessions/{session_id}/recordings/append",
            headers=auth_headers,
            json={
                "start_time": "2025-01-01 10:00",
                "end_time": "2025-01-01 10:01",
                "duration_seconds": 60,
                "transcript_text": "家長：你再不寫功課我就生氣了！\n孩子：我不想寫...",
            },
        )
        assert (
            append_response.status_code == 200
        ), f"Append recording failed: {append_response.text}"
        append_data = append_response.json()
        assert "session_id" in append_data
        assert "total_recordings" in append_data
        assert append_data["total_recordings"] == 1
        print(
            f"[Step 3] Appended recording, total_recordings={append_data['total_recordings']}"
        )

        # Step 4: Analyze partial using /api/v1/sessions/{id}/analyze-partial
        print("\n[Step 4] Analyzing partial transcript...")
        analyze_response = test_client.post(
            f"/api/v1/sessions/{session_id}/analyze-partial",
            headers=auth_headers,
            json={
                "transcript_segment": "家長：你再不寫功課我就生氣了！\n孩子：我不想寫...",
                "mode": "practice",
            },
        )
        assert (
            analyze_response.status_code == 200
        ), f"Analyze partial failed: {analyze_response.text}"
        analysis_data = analyze_response.json()

        # Verify IslandParentAnalysisResponse structure
        assert "safety_level" in analysis_data
        assert "severity" in analysis_data
        assert "display_text" in analysis_data
        assert "action_suggestion" in analysis_data
        assert "suggested_interval_seconds" in analysis_data

        assert analysis_data["safety_level"] in ["red", "yellow", "green"]
        assert 1 <= analysis_data["severity"] <= 3
        assert isinstance(analysis_data["display_text"], str)
        assert isinstance(analysis_data["action_suggestion"], str)

        print("[Step 4] Analysis complete:")
        print(f"  safety_level={analysis_data['safety_level']}")
        print(f"  severity={analysis_data['severity']}")
        print(f"  display_text={analysis_data['display_text'][:50]}...")
        print(f"  action_suggestion={analysis_data['action_suggestion'][:50]}...")

        print("\n✅ Complete web session workflow test passed!")

    def test_web_workflow_multiple_analyses(
        self,
        test_client: TestClient,
        db_session: Session,
        auth_headers: dict,
    ):
        """Test multiple append+analyze cycles (simulating real-time counseling)"""
        # Step 1: Create client + case
        client_case_response = test_client.post(
            "/api/v1/ui/client-case",
            headers=auth_headers,
            json={
                "name": "多次分析測試孩子",
                "email": f"multitest-{uuid4().hex[:8]}@example.com",
                "gender": "不透露",
                "birth_date": "2015-01-01",
                "phone": "0900000001",
                "identity_option": "其他",
                "current_status": "進行中",
                "case_summary": "測試多次即時分析",
                "case_goals": "驗證 workflow 穩定性",
                "grade": "小學四年級",
                "relationship": "爸爸",
            },
        )
        assert client_case_response.status_code == 201
        case_id = client_case_response.json()["case_id"]

        # Step 2: Create session
        session_response = test_client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "case_id": str(case_id),
                "session_date": "2025-01-01",
                "name": "多次分析測試會談",
            },
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # Step 3-4: Append + Analyze (3 times)
        transcripts = [
            "家長：你今天在學校怎麼樣？\n孩子：還好啦...",
            "家長：功課寫完了嗎？\n孩子：還沒...",
            "家長：你怎麼都不說話？\n孩子：我不知道要說什麼...",
        ]

        for i, transcript in enumerate(transcripts, 1):
            print(f"\n[Cycle {i}] Append + Analyze...")

            # Append
            append_response = test_client.post(
                f"/api/v1/sessions/{session_id}/recordings/append",
                headers=auth_headers,
                json={
                    "start_time": f"2025-01-01 10:{i:02d}",
                    "end_time": f"2025-01-01 10:{i+1:02d}",
                    "duration_seconds": 60,
                    "transcript_text": transcript,
                },
            )
            assert append_response.status_code == 200
            assert append_response.json()["total_recordings"] == i

            # Analyze
            analyze_response = test_client.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                headers=auth_headers,
                json={
                    "transcript_segment": transcript,
                    "mode": "practice",
                },
            )
            assert analyze_response.status_code == 200
            analysis = analyze_response.json()
            assert "safety_level" in analysis
            print(f"[Cycle {i}] safety_level={analysis['safety_level']}")

        print("\n✅ Multiple analyses test passed!")

    def test_web_workflow_emergency_mode(
        self,
        test_client: TestClient,
        db_session: Session,
        auth_headers: dict,
    ):
        """Test workflow with emergency mode analysis"""
        # Create client + case + session
        client_case_response = test_client.post(
            "/api/v1/ui/client-case",
            headers=auth_headers,
            json={
                "name": "緊急模式測試",
                "email": f"emergency-{uuid4().hex[:8]}@example.com",
                "gender": "不透露",
                "birth_date": "2015-01-01",
                "phone": "0900000002",
                "identity_option": "其他",
                "current_status": "進行中",
                "grade": "小學五年級",
                "relationship": "媽媽",
            },
        )
        assert client_case_response.status_code == 201
        case_id = client_case_response.json()["case_id"]

        session_response = test_client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "case_id": str(case_id),
                "session_date": "2025-01-01",
                "name": "緊急模式測試會談",
            },
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # Append recording
        test_client.post(
            f"/api/v1/sessions/{session_id}/recordings/append",
            headers=auth_headers,
            json={
                "start_time": "2025-01-01 10:00",
                "end_time": "2025-01-01 10:01",
                "duration_seconds": 60,
                "transcript_text": "家長：你為什麼這麼不聽話！\n孩子：我討厭你！",
            },
        )

        # Analyze in emergency mode
        analyze_response = test_client.post(
            f"/api/v1/sessions/{session_id}/analyze-partial",
            headers=auth_headers,
            json={
                "transcript_segment": "家長：你為什麼這麼不聽話！\n孩子：我討厭你！",
                "mode": "emergency",
            },
        )
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()

        # Emergency mode should provide quick, concise feedback
        assert "safety_level" in analysis
        assert "display_text" in analysis
        assert "action_suggestion" in analysis

        print(f"\n[Emergency Mode] safety_level={analysis['safety_level']}")
        print(f"[Emergency Mode] display_text={analysis['display_text']}")
        print("\n✅ Emergency mode test passed!")
