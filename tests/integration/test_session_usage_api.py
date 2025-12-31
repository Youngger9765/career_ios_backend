"""
Integration tests for SessionAnalysisLog and SessionUsage models
TDD - Write tests FIRST, then implement

These tests define the API contract for:
1. SessionAnalysisLog - Detailed analysis event tracking
2. SessionUsage - Flexible credit deduction with multiple pricing models
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel


class TestSessionAnalysisLogAPI:
    """Test SessionAnalysisLog CRUD and querying"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-analysis@test.com",
            username="analysiscounselor",
            full_name="Analysis Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor-analysis@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, counselor

    @pytest.fixture
    def test_session(self, db_session: Session, auth_headers):
        """Create test client, case, and session"""
        from datetime import date

        headers, counselor = auth_headers

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="分析日誌測試案主",
            code="ACLI001",
            email="acli001@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number="ACASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="測試逐字稿內容",
        )
        db_session.add(session)
        db_session.commit()

        return session, headers, counselor

    def test_create_session_analysis_log(self, db_session: Session, test_session):
        """Test POST /api/v1/sessions/{id}/analysis-logs - Create analysis log with all fields"""
        session, headers, counselor = test_session

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/analysis-logs",
                headers=headers,
                json={
                    "analysis_type": "keyword_extraction",
                    "transcript": "我感到很焦慮和壓力，不知道該選擇哪個職業方向。",
                    "analysis_result": {
                        "keywords": ["焦慮", "壓力", "職業方向"],
                        "categories": ["情緒", "職涯探索"],
                        "confidence": 0.92,
                    },
                    "safety_level": "yellow",
                    "risk_indicators": ["焦慮", "壓力"],
                    "rag_documents": [
                        {"doc_id": "doc-001", "relevance": 0.88},
                        {"doc_id": "doc-002", "relevance": 0.75},
                    ],
                    "rag_sources": ["職涯諮詢手冊", "心理健康指南"],
                    "token_usage": {
                        "prompt_tokens": 150,
                        "completion_tokens": 80,
                        "total_tokens": 230,
                    },
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["session_id"] == str(session.id)
            assert data["counselor_id"] == str(counselor.id)
            assert data["analysis_type"] == "keyword_extraction"
            assert (
                data["transcript"] == "我感到很焦慮和壓力，不知道該選擇哪個職業方向。"
            )
            assert data["analysis_result"]["keywords"] == ["焦慮", "壓力", "職業方向"]
            assert data["safety_level"] == "yellow"
            assert len(data["risk_indicators"]) == 2
            assert len(data["rag_documents"]) == 2
            assert len(data["rag_sources"]) == 2
            assert data["token_usage"]["total_tokens"] == 230
            assert "id" in data
            assert "analyzed_at" in data

    def test_session_analysis_log_multi_tenant(self, db_session: Session):
        """Test tenant isolation - counselor can't access other tenant's logs"""
        from datetime import date

        # Create two counselors in different tenants
        counselor1 = Counselor(
            id=uuid4(),
            email="tenant1@test.com",
            username="tenant1counselor",
            full_name="Tenant 1 Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="tenant1",
            role="counselor",
            is_active=True,
        )
        counselor2 = Counselor(
            id=uuid4(),
            email="tenant2@test.com",
            username="tenant2counselor",
            full_name="Tenant 2 Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="tenant2",
            role="counselor",
            is_active=True,
        )
        db_session.add_all([counselor1, counselor2])
        db_session.commit()

        # Create session for tenant1
        client1 = Client(
            id=uuid4(),
            counselor_id=counselor1.id,
            tenant_id="tenant1",
            name="Tenant 1 Client",
            code="T1CLI001",
            email="t1@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client1)
        db_session.commit()

        case1 = Case(
            id=uuid4(),
            case_number="T1CASE001",
            counselor_id=counselor1.id,
            client_id=client1.id,
            tenant_id="tenant1",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case1)
        db_session.commit()

        session1 = SessionModel(
            id=uuid4(),
            case_id=case1.id,
            tenant_id="tenant1",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(session1)
        db_session.commit()

        # Login as tenant2 counselor
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "tenant2@test.com",
                    "password": "password123",
                    "tenant_id": "tenant2",
                },
            )
            token2 = login_response.json()["access_token"]
            headers2 = {"Authorization": f"Bearer {token2}"}

            # Try to create log for tenant1's session - should fail
            response = client.post(
                f"/api/v1/sessions/{session1.id}/analysis-logs",
                headers=headers2,
                json={
                    "analysis_type": "keyword_extraction",
                    "transcript": "測試",
                    "result_data": {},
                },
            )

            assert response.status_code == 404

    def test_session_analysis_log_rag_data(self, db_session: Session, test_session):
        """Test analysis log with complex RAG documents and sources (JSON fields)"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/analysis-logs",
                headers=headers,
                json={
                    "analysis_type": "rag_query",
                    "transcript": "如何處理職場衝突？",
                    "result_data": {
                        "answer": "建議使用非暴力溝通技巧...",
                        "sources_used": 3,
                    },
                    "rag_documents": [
                        {
                            "doc_id": "doc-101",
                            "title": "職場溝通技巧",
                            "relevance": 0.95,
                            "chunk_id": "chunk-1",
                        },
                        {
                            "doc_id": "doc-102",
                            "title": "衝突管理指南",
                            "relevance": 0.88,
                            "chunk_id": "chunk-5",
                        },
                        {
                            "doc_id": "doc-103",
                            "title": "職涯發展手冊",
                            "relevance": 0.72,
                            "chunk_id": "chunk-12",
                        },
                    ],
                    "rag_sources": [
                        "職場溝通技巧 (第3章)",
                        "衝突管理指南 (案例研究)",
                        "職涯發展手冊 (附錄A)",
                    ],
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["analysis_type"] == "rag_query"
            assert len(data["rag_documents"]) == 3
            assert data["rag_documents"][0]["relevance"] == 0.95
            assert data["rag_documents"][1]["title"] == "衝突管理指南"
            assert len(data["rag_sources"]) == 3

    def test_session_analysis_log_token_metrics(
        self, db_session: Session, test_session
    ):
        """Test analysis log token usage tracking"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/analysis-logs",
                headers=headers,
                json={
                    "analysis_type": "summarization",
                    "transcript": "長段逐字稿...",
                    "result_data": {"summary": "簡短摘要"},
                    "token_usage": {
                        "prompt_tokens": 1200,
                        "completion_tokens": 300,
                        "total_tokens": 1500,
                        "model": "gemini-1.5-pro",
                    },
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["token_usage"]["prompt_tokens"] == 1200
            assert data["token_usage"]["completion_tokens"] == 300
            assert data["token_usage"]["total_tokens"] == 1500
            assert data["token_usage"]["model"] == "gemini-1.5-pro"

    def test_query_by_safety_level(self, db_session: Session, test_session):
        """Test GET /api/v1/sessions/{id}/analysis-logs?safety_level=red - Query by safety level"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            # Create logs with different safety levels
            for level in ["green", "yellow", "red", "yellow"]:
                client.post(
                    f"/api/v1/sessions/{session.id}/analysis-logs",
                    headers=headers,
                    json={
                        "analysis_type": "keyword_extraction",
                        "transcript": f"測試 {level}",
                        "result_data": {},
                        "safety_level": level,
                    },
                )

            # Query only red level logs
            response = client.get(
                f"/api/v1/sessions/{session.id}/analysis-logs?safety_level=red",
                headers=headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1
            for log in data["items"]:
                assert log["safety_level"] == "red"

            # Query yellow level logs
            response = client.get(
                f"/api/v1/sessions/{session.id}/analysis-logs?safety_level=yellow",
                headers=headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 2


class TestSessionUsageAPI:
    """Test SessionUsage with flexible pricing models"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-usage@test.com",
            username="usagecounselor",
            full_name="Usage Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            available_credits=1000.0,  # Start with credits
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor-usage@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, counselor

    @pytest.fixture
    def test_session(self, db_session: Session, auth_headers):
        """Create test client, case, and session"""
        from datetime import date

        headers, counselor = auth_headers

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="使用量測試案主",
            code="UCLI001",
            email="ucli001@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number="UCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()

        return session, headers, counselor

    def test_create_session_usage_in_progress(self, db_session: Session, test_session):
        """Test POST /api/v1/sessions/{id}/usage - Create usage record with in_progress status"""
        session, headers, counselor = test_session

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["session_id"] == str(session.id)
            assert data["counselor_id"] == str(counselor.id)
            assert data["usage_type"] == "voice_call"
            assert data["status"] == "in_progress"
            assert data["start_time"] is not None
            assert data["end_time"] is None
            assert data["credits_deducted"] == 0
            assert "id" in data

    def test_session_usage_time_based_pricing(self, db_session: Session, test_session):
        """Test time-based pricing: pricing_rule: {unit: minute, rate: 1.0}"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            start_time = datetime.now(timezone.utc)

            # Test 1: 30 seconds = 0.5 minutes = 0.5 credits
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "completed",
                    "start_time": start_time.isoformat(),
                    "end_time": (start_time + timedelta(seconds=30)).isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "completed"
            assert data["duration_seconds"] == 30
            assert data["credits_deducted"] == 0.5
            assert data["pricing_rule"]["unit"] == "minute"
            assert data["pricing_rule"]["rate"] == 1.0

            # Test 2: 90 seconds = 1.5 minutes = 1.5 credits
            session2 = SessionModel(
                id=uuid4(),
                case_id=session.case_id,
                tenant_id="career",
                session_number=2,
                session_date=datetime.now(timezone.utc),
            )
            db_session.add(session2)
            db_session.commit()

            response = client.post(
                f"/api/v1/sessions/{session2.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "completed",
                    "start_time": start_time.isoformat(),
                    "end_time": (start_time + timedelta(seconds=90)).isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["duration_seconds"] == 90
            assert data["credits_deducted"] == 1.5

    def test_session_usage_token_based_pricing(self, db_session: Session, test_session):
        """Test token-based pricing: pricing_rule: {unit: token, rate: 0.001}"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            # Test 1: 1000 tokens * 0.001 = 1.0 credits
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "text_analysis",
                    "status": "completed",
                    "token_usage": {
                        "prompt_tokens": 600,
                        "completion_tokens": 400,
                        "total_tokens": 1000,
                    },
                    "pricing_rule": {"unit": "token", "rate": 0.001},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "completed"
            assert data["token_usage"]["total_tokens"] == 1000
            assert data["credits_deducted"] == 1.0
            assert data["pricing_rule"]["unit"] == "token"

            # Test 2: 5000 tokens * 0.001 = 5.0 credits
            session2 = SessionModel(
                id=uuid4(),
                case_id=session.case_id,
                tenant_id="career",
                session_number=2,
                session_date=datetime.now(timezone.utc),
            )
            db_session.add(session2)
            db_session.commit()

            response = client.post(
                f"/api/v1/sessions/{session2.id}/usage",
                headers=headers,
                json={
                    "usage_type": "text_analysis",
                    "status": "completed",
                    "token_usage": {
                        "prompt_tokens": 3000,
                        "completion_tokens": 2000,
                        "total_tokens": 5000,
                    },
                    "pricing_rule": {"unit": "token", "rate": 0.001},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["token_usage"]["total_tokens"] == 5000
            assert data["credits_deducted"] == 5.0

    def test_session_usage_analysis_based_pricing(
        self, db_session: Session, test_session
    ):
        """Test analysis-based pricing: pricing_rule: {unit: analysis, rate: 2.0}"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            # Test: 3 analyses * 2.0 = 6.0 credits
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "keyword_analysis",
                    "status": "completed",
                    "analysis_count": 3,
                    "pricing_rule": {"unit": "analysis", "rate": 2.0},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "completed"
            assert data["analysis_count"] == 3
            assert data["credits_deducted"] == 6.0
            assert data["pricing_rule"]["unit"] == "analysis"
            assert data["pricing_rule"]["rate"] == 2.0

    def test_session_usage_multi_tenant(self, db_session: Session):
        """Test tenant isolation - counselor can't access other tenant's usage"""
        from datetime import date

        # Create two counselors in different tenants
        counselor1 = Counselor(
            id=uuid4(),
            email="usage-tenant1@test.com",
            username="usagetenant1",
            full_name="Usage Tenant 1 Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="tenant1",
            role="counselor",
            is_active=True,
        )
        counselor2 = Counselor(
            id=uuid4(),
            email="usage-tenant2@test.com",
            username="usagetenant2",
            full_name="Usage Tenant 2 Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="tenant2",
            role="counselor",
            is_active=True,
        )
        db_session.add_all([counselor1, counselor2])
        db_session.commit()

        # Create session for tenant1
        client1 = Client(
            id=uuid4(),
            counselor_id=counselor1.id,
            tenant_id="tenant1",
            name="Usage Tenant 1 Client",
            code="UT1CLI001",
            email="ut1@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client1)
        db_session.commit()

        case1 = Case(
            id=uuid4(),
            case_number="UT1CASE001",
            counselor_id=counselor1.id,
            client_id=client1.id,
            tenant_id="tenant1",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case1)
        db_session.commit()

        session1 = SessionModel(
            id=uuid4(),
            case_id=case1.id,
            tenant_id="tenant1",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(session1)
        db_session.commit()

        # Login as tenant2 counselor
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "usage-tenant2@test.com",
                    "password": "password123",
                    "tenant_id": "tenant2",
                },
            )
            token2 = login_response.json()["access_token"]
            headers2 = {"Authorization": f"Bearer {token2}"}

            # Try to create usage for tenant1's session - should fail
            response = client.post(
                f"/api/v1/sessions/{session1.id}/usage",
                headers=headers2,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 404

    def test_session_usage_unique_session_id(self, db_session: Session, test_session):
        """Test unique constraint - can't create multiple usage records for same session"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            # Create first usage record
            response1 = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )
            assert response1.status_code == 201

            # Try to create second usage record for same session - should fail
            response2 = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response2.status_code == 400
            assert "already exists" in response2.json()["detail"].lower()

    def test_session_usage_status_transitions(self, db_session: Session, test_session):
        """Test status transitions: in_progress -> completed"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            # Create usage in progress
            start_time = datetime.now(timezone.utc)
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "start_time": start_time.isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )
            assert response.status_code == 201
            usage_id = response.json()["id"]

            # Update to completed
            end_time = start_time + timedelta(minutes=5)  # 5 minutes
            response = client.patch(
                f"/api/v1/sessions/{session.id}/usage/{usage_id}",
                headers=headers,
                json={
                    "status": "completed",
                    "end_time": end_time.isoformat(),
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["end_time"] is not None
            assert data["duration_seconds"] == 300
            assert data["credits_deducted"] == 5.0  # 5 minutes * 1.0 rate

    def test_session_usage_credit_deduction(self, db_session: Session, test_session):
        """Test credit deduction workflow - verify credits are deducted after completion"""
        session, headers, counselor = test_session

        # Get initial credits
        initial_available = counselor.available_credits

        with TestClient(app) as client:
            # Create and complete usage
            start_time = datetime.now(timezone.utc)
            end_time = start_time + timedelta(minutes=10)

            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "completed",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["credits_deducted"] == 10.0

            # Verify counselor credits were deducted
            db_session.refresh(counselor)
            assert counselor.available_credits == initial_available - 10.0


class TestSessionUsageIntegration:
    """Integration tests combining SessionAnalysisLog and SessionUsage"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-integration@test.com",
            username="integrationcounselor",
            full_name="Integration Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            available_credits=1000.0,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor-integration@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, counselor

    @pytest.fixture
    def test_session(self, db_session: Session, auth_headers):
        """Create test client, case, and session"""
        from datetime import date

        headers, counselor = auth_headers

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="整合測試案主",
            code="ICLI001",
            email="icli001@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number="ICASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()

        return session, headers, counselor

    def test_complete_usage_workflow(self, db_session: Session, test_session):
        """Test complete workflow: Session -> Analysis Logs -> Usage -> Credit calculation"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            # Step 1: Create multiple analysis logs
            for i in range(3):
                response = client.post(
                    f"/api/v1/sessions/{session.id}/analysis-logs",
                    headers=headers,
                    json={
                        "analysis_type": "keyword_extraction",
                        "transcript": f"測試片段 {i+1}",
                        "result_data": {"keywords": [f"關鍵字{i+1}"]},
                        "token_usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 50,
                            "total_tokens": 150,
                        },
                    },
                )
                assert response.status_code == 201

            # Step 2: Create usage record based on analyses
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "keyword_analysis",
                    "status": "completed",
                    "analysis_count": 3,
                    "pricing_rule": {"unit": "analysis", "rate": 2.0},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["analysis_count"] == 3
            assert data["credits_deducted"] == 6.0

            # Step 3: Verify analysis logs exist
            response = client.get(
                f"/api/v1/sessions/{session.id}/analysis-logs",
                headers=headers,
            )

            assert response.status_code == 200
            logs = response.json()
            assert logs["total"] == 3

    def test_cascade_deletion(self, db_session: Session, test_session):
        """Test cascade deletion - deleting session cascades to logs and usage"""
        session, headers, _ = test_session

        with TestClient(app) as client:
            # Create analysis log
            client.post(
                f"/api/v1/sessions/{session.id}/analysis-logs",
                headers=headers,
                json={
                    "analysis_type": "keyword_extraction",
                    "transcript": "測試",
                    "result_data": {},
                },
            )

            # Create usage record
            client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            # Delete session
            response = client.delete(
                f"/api/v1/sessions/{session.id}",
                headers=headers,
            )

            assert response.status_code == 204

            # Verify analysis logs are deleted
            response = client.get(
                f"/api/v1/sessions/{session.id}/analysis-logs",
                headers=headers,
            )
            assert response.status_code == 404

            # Verify usage is deleted (or session_id is set to null)
            response = client.get(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
            )
            assert response.status_code == 404
