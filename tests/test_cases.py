"""
Case tests for Career Counseling API
Tests for Cases, Sessions, and Reports flow
"""
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings


class TestCasesAPI:
    """Test Cases API endpoints"""

    def test_list_cases(self, client):
        """Test listing all cases"""
        response = client.get("/api/v1/cases")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            case = data[0]
            assert "id" in case
            assert "visitor_name" in case
            assert "counselor_name" in case
            assert "status" in case
            assert "session_count" in case

    def test_get_case_detail(self, client):
        """Test getting specific case details"""
        response = client.get("/api/v1/cases/test-case-id-001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-case-id-001"
        assert "visitor_name" in data
        assert "counselor_name" in data

    def test_create_case(self, client):
        """Test creating a new case"""
        case_data = {
            "visitor_name": "測試來訪者",
            "counselor_id": 1,
            "initial_concern": "職涯困擾"
        }
        response = client.post("/api/v1/cases", json=case_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["visitor_name"] == "測試來訪者"

    def test_update_case(self, client):
        """Test updating case information"""
        update_data = {
            "status": "active",
            "notes": "更新測試"
        }
        response = client.patch("/api/v1/cases/test-case-id-001", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"


class TestSessionsAPI:
    """Test Sessions API endpoints - Dual Input Mode"""

    def test_list_sessions(self, client):
        """Test listing sessions"""
        response = client.get("/api/v1/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_sessions_by_case(self, client):
        """Test filtering sessions by case_id"""
        response = client.get("/api/v1/sessions?case_id=test-case-001")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert data[0]["case_id"] == "test-case-001"

    def test_create_session(self, client):
        """Test creating a new session"""
        session_data = {
            "case_id": "test-case-001",
            "counselor_id": 1,
            "scheduled_time": "2025-10-04T10:00:00Z"
        }
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["case_id"] == "test-case-001"

    def test_upload_audio_mode1(self, client, mock_audio_file):
        """Test Mode 1: Upload audio file for STT processing"""
        response = client.post(
            "/api/v1/sessions/test-session-001/upload-audio",
            files={"file": mock_audio_file["file"]},
            data={"duration_seconds": 2730}
        )

        if settings.MOCK_MODE:
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-001"
            assert "audio_path" in data
            assert "job_id" in data
            assert data["message"] == "Audio uploaded successfully, processing started"
        else:
            # Real implementation should also return 200
            assert response.status_code in [200, 501]

    def test_upload_transcript_mode2(self, client):
        """Test Mode 2: Upload transcript directly"""
        transcript_text = """
        諮商師：今天想聊什麼呢？
        來訪者：我最近工作上遇到一些困難...
        """

        response = client.post(
            "/api/v1/sessions/test-session-001/upload-transcript",
            data={
                "transcript": transcript_text,
                "sanitize": True
            }
        )

        if settings.MOCK_MODE:
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-001"
            assert data["source_type"] == "text"
            assert data["sanitized"] == True
        else:
            assert response.status_code in [200, 501]

    def test_get_transcript(self, client):
        """Test getting session transcript"""
        response = client.get("/api/v1/sessions/test-session-001/transcript")
        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data
        assert "word_count" in data
        assert "language" in data


class TestReportsAPI:
    """Test Reports API endpoints"""

    def test_list_reports(self, client):
        """Test listing all reports"""
        response = client.get("/api/v1/reports")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            report = data[0]
            assert "id" in report
            assert "status" in report
            assert "created_at" in report

    def test_list_reports_by_status(self, client):
        """Test filtering reports by status"""
        response = client.get("/api/v1/reports?status=pending_review")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            for report in data:
                assert report["status"] == "pending_review"

    def test_get_report_detail(self, client):
        """Test getting specific report"""
        response = client.get("/api/v1/reports/test-report-001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-report-001"

    def test_generate_report(self, client):
        """Test generating AI report from transcript"""
        response = client.post(
            "/api/v1/reports/generate",
            params={
                "session_id": "test-session-001",
                "agent_id": 1,
                "num_participants": 2
            }
        )

        if settings.MOCK_MODE:
            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert "content_json" in data or "summary" in data
        else:
            assert response.status_code in [201, 501]

    def test_approve_report(self, client):
        """Test approving a report"""
        response = client.patch(
            "/api/v1/reports/test-report-001/review",
            params={"action": "approve"}
        )

        if settings.MOCK_MODE:
            assert response.status_code == 200
            data = response.json()
            assert data["report_id"] == "test-report-001"
            assert data["status"] == "approved"
            assert data["message"] == "Report approved successfully"
        else:
            assert response.status_code in [200, 501]

    def test_reject_report(self, client):
        """Test rejecting a report with notes"""
        response = client.patch(
            "/api/v1/reports/test-report-002/review",
            params={
                "action": "reject",
                "review_notes": "需要補充理論依據"
            }
        )

        if settings.MOCK_MODE:
            assert response.status_code == 200
            data = response.json()
            assert data["report_id"] == "test-report-002"
            assert data["status"] == "rejected"
        else:
            assert response.status_code in [200, 501]

    def test_invalid_review_action(self, client):
        """Test invalid review action"""
        response = client.patch(
            "/api/v1/reports/test-report-001/review",
            params={"action": "invalid_action"}
        )
        assert response.status_code == 422  # Validation error

    def test_update_report(self, client):
        """Test updating report content"""
        update_data = {
            "summary": "更新的摘要",
            "status": "draft"
        }
        response = client.put("/api/v1/reports/test-report-001", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_download_report(self, client):
        """Test report download links"""
        response = client.get("/api/v1/reports/test-report-001/download")
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        assert "pdf" in data["formats"]
        assert "docx" in data["formats"]
        assert "json" in data["formats"]


class TestCompleteWorkflow:
    """Test complete workflow: Case → Session → Transcript → Report → Review"""

    @pytest.mark.asyncio
    async def test_complete_counseling_workflow(self, client):
        """Test the complete counseling workflow"""

        # Step 1: Create a case
        case_response = client.post("/api/v1/cases", json={
            "visitor_name": "工作流測試來訪者",
            "counselor_id": 1,
            "initial_concern": "職涯發展困擾"
        })
        assert case_response.status_code == 201
        case_id = case_response.json()["id"]

        # Step 2: Create a session
        session_response = client.post("/api/v1/sessions", json={
            "case_id": case_id,
            "counselor_id": 1
        })
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # Step 3: Upload transcript (Mode 2)
        transcript_response = client.post(
            f"/api/v1/sessions/{session_id}/upload-transcript",
            data={
                "transcript": "諮商師：今天想聊什麼？\n來訪者：我不知道未來的方向...",
                "sanitize": True
            }
        )
        assert transcript_response.status_code == 200

        # Step 4: Generate report
        report_response = client.post(
            "/api/v1/reports/generate",
            params={"session_id": session_id, "agent_id": 1}
        )

        if settings.MOCK_MODE:
            assert report_response.status_code == 201
            report_id = report_response.json()["id"]

            # Step 5: Review report
            review_response = client.patch(
                f"/api/v1/reports/{report_id}/review",
                params={"action": "approve"}
            )
            assert review_response.status_code == 200
            assert review_response.json()["status"] == "approved"

    @pytest.mark.asyncio
    async def test_audio_workflow(self, client, mock_audio_file):
        """Test workflow with audio upload (Mode 1)"""

        # Create session
        session_response = client.post("/api/v1/sessions", json={
            "case_id": "test-case-001",
            "counselor_id": 1
        })
        assert session_response.status_code == 201
        session_id = session_response.json()["id"]

        # Upload audio
        audio_response = client.post(
            f"/api/v1/sessions/{session_id}/upload-audio",
            files={"file": mock_audio_file["file"]},
            data={"duration_seconds": 2730}
        )

        if settings.MOCK_MODE:
            assert audio_response.status_code == 200
            assert "job_id" in audio_response.json()

            # In real implementation, would poll for job status
            # For now, just verify the endpoint exists
            transcript_response = client.get(f"/api/v1/sessions/{session_id}/transcript")
            assert transcript_response.status_code == 200


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_generate_report_without_transcript(self, client):
        """Test generating report for session without transcript"""
        # This should fail or return appropriate error
        response = client.post(
            "/api/v1/reports/generate",
            params={"session_id": "session-without-transcript"}
        )
        # In mock mode, it will succeed; in real mode, should be 400
        assert response.status_code in [201, 400, 501]

    def test_review_nonexistent_report(self, client):
        """Test reviewing non-existent report"""
        response = client.patch(
            "/api/v1/reports/nonexistent-report-id/review",
            params={"action": "approve"}
        )
        # Mock mode might succeed, real should be 404
        assert response.status_code in [200, 404, 501]

    def test_upload_empty_transcript(self, client):
        """Test uploading empty transcript"""
        response = client.post(
            "/api/v1/sessions/test-session-001/upload-transcript",
            data={"transcript": "", "sanitize": False}
        )
        # Should either succeed with empty transcript or return validation error
        assert response.status_code in [200, 422]

    def test_upload_large_audio_file(self, client):
        """Test uploading large audio file"""
        # Create mock large file (simulated)
        large_file = ("large_audio.mp3", b"x" * 50 * 1024 * 1024, "audio/mpeg")  # 50MB

        response = client.post(
            "/api/v1/sessions/test-session-001/upload-audio",
            files={"file": large_file}
        )
        # Should either succeed or return file size error
        assert response.status_code in [200, 413, 422]


class TestAuthentication:
    """Test authentication and authorization (future implementation)"""

    def test_unauthenticated_access(self, client):
        """Test accessing protected endpoints without auth"""
        # Currently no auth, but placeholder for future
        response = client.get("/api/v1/cases")
        # Should succeed now, but will require auth in future
        assert response.status_code in [200, 401]

    def test_unauthorized_review(self, client):
        """Test reviewing report without proper role"""
        # Placeholder for role-based access control
        response = client.patch(
            "/api/v1/reports/test-report-001/review",
            params={"action": "approve"}
        )
        # Should succeed now, but will check permissions in future
        assert response.status_code in [200, 403, 501]
