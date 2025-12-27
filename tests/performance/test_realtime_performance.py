"""
Performance tests for Realtime Analysis API

Tests the performance of:
1. /api/v1/realtime/analyze - 10-minute transcript analysis
2. /api/v1/sessions/{session_id}/recordings/append - Append recording
3. Combined iOS flow (append + analyze-partial if exists)

Usage:
    poetry run pytest tests/performance/test_realtime_performance.py -v -s
"""
import json
import time
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def transcript_10min():
    """Load 10-minute transcript from test data"""
    test_data_path = Path(__file__).parent.parent / "data" / "long_transcripts.json"
    with open(test_data_path) as f:
        data = json.load(f)
    return data["10min"]


@pytest.fixture
def transcript_10min_v2():
    """Load 10-minute transcript v2 from test data"""
    test_data_path = Path(__file__).parent.parent / "data" / "long_transcripts_v2.json"
    with open(test_data_path) as f:
        data = json.load(f)
    return data["10min"]


@pytest.fixture
def auth_token(client):
    """Get authentication token"""
    # Use test credentials
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword"},
    )
    if response.status_code == 200:
        return response.json()["access_token"]

    # If test user doesn't exist, create one
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword",
            "full_name": "Test User",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword"},
    )
    return response.json()["access_token"]


class TestRealtimePerformance:
    """Performance tests for Realtime Analysis"""

    def test_realtime_analyze_10min_transcript_v1(self, client, transcript_10min):
        """
        Test 1: Realtime analyze with 10-minute transcript (手足衝突)

        Expected performance:
        - Total time: < 2000 ms (2 seconds)
        - Should include RAG search + AI analysis
        """
        print("\n" + "=" * 80)
        print("TEST 1: Realtime Analyze - 10 min transcript (手足衝突)")
        print("=" * 80)

        request_data = {
            "transcript": transcript_10min["transcript"],
            "speakers": transcript_10min["speakers"],
            "time_range": transcript_10min["time_range"],
            "mode": "practice",
        }

        # Measure performance
        start_time = time.time()
        response = client.post("/api/v1/realtime/analyze", json=request_data)
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000

        # Print results
        print("\n📊 Performance Results:")
        print(f"   - Total Duration: {duration_ms:.2f} ms")
        print(f"   - Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n✅ Analysis Results:")
            print(f"   - Safety Level: {result.get('safety_level', 'N/A')}")
            print(f"   - Issues Count: {len(result.get('issues', []))}")
            if result.get("suggestions"):
                print(f"   - Suggestions: {len(result.get('suggestions', []))}")

            # Check if within expected time
            if duration_ms < 2000:
                print("\n✅ PASS: Within target time (< 2000 ms)")
            else:
                print("\n⚠️  WARNING: Exceeded target time (> 2000 ms)")
        else:
            print(f"\n❌ ERROR: {response.text}")

        print("=" * 80)

        # Assertions
        assert response.status_code == 200
        assert duration_ms < 5000, f"Too slow: {duration_ms:.2f} ms (target: < 2000 ms)"

    def test_realtime_analyze_10min_transcript_v2(self, client, transcript_10min_v2):
        """
        Test 2: Realtime analyze with 10-minute transcript v2 (青少年网络成瘾)

        Expected performance:
        - Total time: < 2000 ms (2 seconds)
        """
        print("\n" + "=" * 80)
        print("TEST 2: Realtime Analyze - 10 min transcript v2 (青少年网络成瘾)")
        print("=" * 80)

        request_data = {
            "transcript": transcript_10min_v2["transcript"],
            "speakers": transcript_10min_v2["speakers"],
            "time_range": transcript_10min_v2["time_range"],
            "mode": "practice",
        }

        # Measure performance
        start_time = time.time()
        response = client.post("/api/v1/realtime/analyze", json=request_data)
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000

        # Print results
        print("\n📊 Performance Results:")
        print(f"   - Total Duration: {duration_ms:.2f} ms")
        print(f"   - Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n✅ Analysis Results:")
            print(f"   - Safety Level: {result.get('safety_level', 'N/A')}")
            print(f"   - Issues Count: {len(result.get('issues', []))}")

            if duration_ms < 2000:
                print("\n✅ PASS: Within target time (< 2000 ms)")
            else:
                print("\n⚠️  WARNING: Exceeded target time (> 2000 ms)")
        else:
            print(f"\n❌ ERROR: {response.text}")

        print("=" * 80)

        assert response.status_code == 200
        assert duration_ms < 5000, f"Too slow: {duration_ms:.2f} ms"


class TestiOSFlowPerformance:
    """Performance tests for iOS recording flow"""

    def test_append_recording_1min(self, client, auth_token, transcript_10min):
        """
        Test 3: Append 1-minute recording segment

        Expected performance:
        - Append time: < 100 ms
        """
        print("\n" + "=" * 80)
        print("TEST 3: iOS Flow - Append Recording (1 min segment)")
        print("=" * 80)

        # Create test session first
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Create client
        client_response = client.post(
            "/api/v1/clients",
            json={
                "code": "TEST001",
                "name": "测试案主",
                "gender": "其他",
                "birth_year": 1990,
            },
            headers=headers,
        )
        client_id = client_response.json()["id"]

        # Create case
        case_response = client.post(
            "/api/v1/cases",
            json={
                "client_id": client_id,
                "case_number": "CASE001",
                "status": "active",
            },
            headers=headers,
        )
        case_id = case_response.json()["id"]

        # Create session
        session_response = client.post(
            "/api/v1/sessions",
            json={
                "case_id": case_id,
                "date": "2025-12-27",
                "duration_minutes": 60,
                "session_type": "individual",
                "transcript": "",
            },
            headers=headers,
        )
        session_id = session_response.json()["id"]

        # Extract 1-minute segment (first 3-4 speaker turns)
        one_min_transcript = "\n".join(
            [f"{s['speaker']}: {s['text']}" for s in transcript_10min["speakers"][:4]]
        )

        append_data = {
            "start_time": "2025-12-27T10:00:00Z",
            "end_time": "2025-12-27T10:01:00Z",
            "duration_seconds": 60,
            "transcript_text": one_min_transcript,
            "transcript_sanitized": one_min_transcript,
        }

        # Measure append performance
        start_time = time.time()
        response = client.post(
            f"/api/v1/sessions/{session_id}/recordings/append",
            json=append_data,
            headers=headers,
        )
        end_time = time.time()

        append_duration_ms = (end_time - start_time) * 1000

        # Print results
        print("\n📊 Append Performance:")
        print(f"   - Duration: {append_duration_ms:.2f} ms")
        print(f"   - Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   - Recording ID: {result.get('recording_id')}")
            print(f"   - Total Recordings: {result.get('total_recordings')}")

            if append_duration_ms < 100:
                print("\n✅ PASS: Within target time (< 100 ms)")
            else:
                print("\n⚠️  WARNING: Exceeded target time (> 100 ms)")
        else:
            print(f"\n❌ ERROR: {response.text}")

        print("=" * 80)

        assert response.status_code == 200
        assert append_duration_ms < 200, f"Append too slow: {append_duration_ms:.2f} ms"

    def test_complete_ios_flow_performance(self, client, auth_token, transcript_10min):
        """
        Test 4: Complete iOS flow (append + potential analyze)

        Expected performance:
        - Frontend waiting time: < 2000 ms (2 seconds)
        - Background tasks don't block frontend
        """
        print("\n" + "=" * 80)
        print("TEST 4: Complete iOS Flow - Append + Analysis")
        print("=" * 80)

        headers = {"Authorization": f"Bearer {auth_token}"}

        # Create session (reuse setup from test_append_recording_1min)
        client_response = client.post(
            "/api/v1/clients",
            json={
                "code": "TEST002",
                "name": "测试案主2",
                "gender": "其他",
                "birth_year": 1990,
            },
            headers=headers,
        )
        client_id = client_response.json()["id"]

        case_response = client.post(
            "/api/v1/cases",
            json={
                "client_id": client_id,
                "case_number": "CASE002",
                "status": "active",
            },
            headers=headers,
        )
        case_id = case_response.json()["id"]

        session_response = client.post(
            "/api/v1/sessions",
            json={
                "case_id": case_id,
                "date": "2025-12-27",
                "duration_minutes": 60,
                "session_type": "individual",
                "transcript": "",
            },
            headers=headers,
        )
        session_id = session_response.json()["id"]

        # Extract 1-minute segment
        one_min_transcript = "\n".join(
            [f"{s['speaker']}: {s['text']}" for s in transcript_10min["speakers"][:4]]
        )

        append_data = {
            "start_time": "2025-12-27T10:00:00Z",
            "end_time": "2025-12-27T10:01:00Z",
            "duration_seconds": 60,
            "transcript_text": one_min_transcript,
            "transcript_sanitized": one_min_transcript,
        }

        # Measure complete flow
        overall_start = time.time()

        # Step 1: Append
        append_start = time.time()
        append_response = client.post(
            f"/api/v1/sessions/{session_id}/recordings/append",
            json=append_data,
            headers=headers,
        )
        append_end = time.time()

        # Step 2: If there's analyze-partial endpoint, call it
        # (Currently not implemented, so we skip)

        overall_end = time.time()

        # Calculate durations
        append_duration_ms = (append_end - append_start) * 1000
        total_frontend_time_ms = (overall_end - overall_start) * 1000

        # Print results
        print("\n📊 Complete Flow Performance:")
        print(f"   - Append Duration: {append_duration_ms:.2f} ms")
        print(f"   - Total Frontend Time: {total_frontend_time_ms:.2f} ms")
        print("\n📌 Note: Background tasks (DB writes, GBQ) run async")
        print("   - Estimated background time: ~110-550 ms (not blocking)")

        if total_frontend_time_ms < 2000:
            print("\n✅ PASS: Within target time (< 2000 ms)")
        else:
            print("\n⚠️  WARNING: Exceeded target time (> 2000 ms)")

        print("=" * 80)

        assert append_response.status_code == 200
        assert (
            total_frontend_time_ms < 2000
        ), f"Frontend waiting too long: {total_frontend_time_ms:.2f} ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
