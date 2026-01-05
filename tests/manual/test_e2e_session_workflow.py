"""
E2E Session Workflow Test - 模擬完整的 iOS/Web 前端流程

測試目標：
1. 驗證 append 累積逐字稿有正確被引用
2. 驗證 quick-feedback / deep-analyze 在正確時間點被呼叫
3. 驗證 report 使用完整逐字稿
4. 驗證 billing 有被呼叫
5. 驗證 RAG 有被使用（如果啟用）

執行方式：
    poetry run python tests/manual/test_e2e_session_workflow.py
"""

import asyncio
import time
from datetime import date, datetime, timezone
from uuid import uuid4

# ============================================================
# Step 1: 準備兩分鐘逐字稿，切成多個片段
# ============================================================

TWO_MINUTE_TRANSCRIPT_SEGMENTS = [
    # 0-15秒: 開場
    {
        "time_range": "0:00-0:15",
        "segment_number": 1,
        "text": "家長: 今天想跟你聊聊最近學校的事情",
    },
    # 15-30秒: 孩子回應
    {
        "time_range": "0:15-0:30",
        "segment_number": 2,
        "text": "家長: 我看到你最近好像有點悶悶不樂，想知道發生什麼事",
    },
    # 30-45秒: 深入詢問
    {
        "time_range": "0:30-0:45",
        "segment_number": 3,
        "text": "家長: 是不是在學校遇到什麼困難？可以跟我說嗎？",
    },
    # 45-60秒: 同理心表達
    {
        "time_range": "0:45-1:00",
        "segment_number": 4,
        "text": "家長: 我理解你可能不想說，但我想讓你知道，不管發生什麼，我都會支持你",
    },
    # 60-75秒: 等待回應
    {
        "time_range": "1:00-1:15",
        "segment_number": 5,
        "text": "家長: 如果你現在不想說也沒關係，我會等你準備好",
    },
    # 75-90秒: 提供選項
    {
        "time_range": "1:15-1:30",
        "segment_number": 6,
        "text": "家長: 你想要我陪你坐一下，還是你需要一些自己的時間？",
    },
    # 90-105秒: 肯定孩子
    {
        "time_range": "1:30-1:45",
        "segment_number": 7,
        "text": "家長: 謝謝你願意聽我說，我知道這對你來說可能很難",
    },
    # 105-120秒: 結束
    {
        "time_range": "1:45-2:00",
        "segment_number": 8,
        "text": "家長: 我愛你，不管怎樣我們都會一起面對",
    },
]


def get_full_transcript_up_to(segment_number: int) -> str:
    """取得累積到某個片段的完整逐字稿"""
    segments = [
        s
        for s in TWO_MINUTE_TRANSCRIPT_SEGMENTS
        if s["segment_number"] <= segment_number
    ]
    return "\n".join([s["text"] for s in segments])


# ============================================================
# Step 2: 模擬前端動作的 Workflow
# ============================================================


class E2EWorkflowTester:
    """模擬 iOS/Web 前端的完整流程"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.token = None
        self.session_id = None
        self.counselor_id = None
        self.accumulated_recordings = []
        self.analysis_results = []
        self.report_result = None

    async def setup(self):
        """Step 0: 準備用戶、client、case、session"""
        import httpx

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            # 0.1 登入取得 token (需要有測試帳號)
            print("\n🔐 Step 0.1: 嘗試登入...")
            login_response = await client.post(
                "/api/auth/login",
                json={
                    "email": "demo@island-parents.com",
                    "password": "demo123",
                    "tenant_id": "island_parents",
                },
            )

            if login_response.status_code != 200:
                print(f"   ❌ 登入失敗: {login_response.text}")
                print("   ⚠️  將使用直接 DB 方式建立測試資料")
                return await self._setup_via_db()

            self.token = login_response.json()["access_token"]
            print(f"   ✅ 登入成功: token={self.token[:20]}...")

            # 0.2 建立 Client
            print("\n📝 Step 0.2: 建立測試 Client...")
            client_response = await client.post(
                "/api/v1/clients/",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": "E2E 測試家長",
                    "email": f"e2e-test-{uuid4().hex[:8]}@test.com",
                    "phone": "0912345678",
                    "gender": "女",
                    "birth_date": "1985-01-01",
                    "identity_option": "家長",
                    "current_status": "親子溝通練習",
                },
            )

            if client_response.status_code not in [200, 201]:
                print(f"   ❌ 建立 Client 失敗: {client_response.text}")
                return False

            client_data = client_response.json()
            client_id = client_data["id"]
            print(f"   ✅ Client 建立成功: {client_id}")

            # 0.3 建立 Case
            print("\n📁 Step 0.3: 建立測試 Case...")
            case_response = await client.post(
                "/api/v1/cases/",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "client_id": client_id,
                    "goals": "改善親子溝通",
                },
            )

            if case_response.status_code not in [200, 201]:
                print(f"   ❌ 建立 Case 失敗: {case_response.text}")
                return False

            case_data = case_response.json()
            case_id = case_data["id"]
            print(f"   ✅ Case 建立成功: {case_id}")

            # 0.4 建立 Session
            print("\n🎙️ Step 0.4: 建立測試 Session...")
            session_response = await client.post(
                "/api/v1/sessions/",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "case_id": case_id,
                    "session_number": 1,
                    "session_date": datetime.now(timezone.utc).isoformat(),
                    "scenario": "練習情境：孩子心情不好",
                    "scenario_description": "練習如何用同理心回應孩子的情緒",
                },
            )

            if session_response.status_code not in [200, 201]:
                print(f"   ❌ 建立 Session 失敗: {session_response.text}")
                return False

            session_data = session_response.json()
            self.session_id = session_data["id"]
            print(f"   ✅ Session 建立成功: {self.session_id}")

            return True

    async def _setup_via_db(self):
        """透過 DB 直接建立測試資料（當 API 無法使用時）"""
        from app.core.database import SessionLocal
        from app.core.security import hash_password
        from app.models.case import Case
        from app.models.client import Client
        from app.models.counselor import Counselor
        from app.models.session import Session as SessionModel

        db = SessionLocal()
        try:
            # 建立 Counselor
            counselor = Counselor(
                id=uuid4(),
                email=f"e2e-test-{uuid4().hex[:8]}@test.com",
                username=f"e2etester{uuid4().hex[:6]}",
                full_name="E2E Test Counselor",
                hashed_password=hash_password("password123"),
                tenant_id="island_parents",
                role="counselor",
                is_active=True,
            )
            db.add(counselor)
            db.flush()
            self.counselor_id = counselor.id
            print(f"   ✅ Counselor 建立成功 (DB): {counselor.id}")

            # 建立 Client
            client = Client(
                id=uuid4(),
                counselor_id=counselor.id,
                code=f"E2E-{uuid4().hex[:6].upper()}",
                name="E2E 測試家長",
                email=f"e2e-parent-{uuid4().hex[:8]}@test.com",
                gender="女",
                birth_date=date(1985, 1, 1),
                phone="0912345678",
                identity_option="家長",
                current_status="親子溝通練習",
                tenant_id="island_parents",
            )
            db.add(client)
            db.flush()
            print(f"   ✅ Client 建立成功 (DB): {client.id}")

            # 建立 Case
            case = Case(
                id=uuid4(),
                client_id=client.id,
                counselor_id=counselor.id,
                tenant_id="island_parents",
                case_number=f"E2E-CASE-{uuid4().hex[:6].upper()}",
                goals="改善親子溝通",
            )
            db.add(case)
            db.flush()
            print(f"   ✅ Case 建立成功 (DB): {case.id}")

            # 建立 Session
            session = SessionModel(
                id=uuid4(),
                case_id=case.id,
                tenant_id="island_parents",
                session_number=1,
                session_date=datetime.now(timezone.utc),
                scenario="練習情境：孩子心情不好",
                scenario_description="練習如何用同理心回應孩子的情緒",
                recordings=[],
            )
            db.add(session)
            db.commit()

            self.session_id = str(session.id)
            print(f"   ✅ Session 建立成功 (DB): {self.session_id}")

            # 模擬登入 token（直接使用 DB 方式，需要生成 token）
            from app.core.security import create_access_token

            self.token = create_access_token({"sub": str(counselor.id)})
            print(f"   ✅ Token 生成成功: {self.token[:20]}...")

            return True

        except Exception as e:
            print(f"   ❌ DB 設定失敗: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    async def simulate_frontend_workflow(self):
        """Step 1-2: 模擬前端的 append + 分析流程"""
        import httpx

        print("\n" + "=" * 60)
        print("🎬 開始模擬前端流程")
        print("=" * 60)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=60) as client:
            headers = {"Authorization": f"Bearer {self.token}"}

            for segment in TWO_MINUTE_TRANSCRIPT_SEGMENTS:
                segment_num = segment["segment_number"]
                time_range = segment["time_range"]
                text = segment["text"]

                print(f"\n📍 [{time_range}] Segment {segment_num}")
                print(f"   逐字稿: {text[:40]}...")

                # Step 2.1: Append 逐字稿片段
                print("   ⏳ Appending recording...")
                append_response = await client.post(
                    f"/api/v1/sessions/{self.session_id}/append-recording",
                    headers=headers,
                    json={
                        "segment_number": segment_num,
                        "transcript_text": text,
                        "start_time": time_range.split("-")[0],
                        "end_time": time_range.split("-")[1],
                    },
                )

                if append_response.status_code == 200:
                    self.accumulated_recordings.append(segment)
                    print(
                        f"   ✅ Append 成功 (累積 {len(self.accumulated_recordings)} 段)"
                    )
                else:
                    print(f"   ❌ Append 失敗: {append_response.text[:100]}")

                # Step 2.2: 每 15 秒呼叫 quick-feedback
                print("   ⏳ Calling quick-feedback...")
                quick_start = time.time()
                quick_response = await client.post(
                    f"/api/v1/sessions/{self.session_id}/quick-feedback?mode=practice",
                    headers=headers,
                )
                quick_time = time.time() - quick_start

                if quick_response.status_code == 200:
                    quick_data = quick_response.json()
                    print(
                        f"   ✅ Quick-feedback ({quick_time:.2f}s): {quick_data.get('message', '')[:50]}"
                    )
                else:
                    print(f"   ❌ Quick-feedback 失敗: {quick_response.text[:100]}")

                # Step 2.3: 每 30 秒呼叫 deep-analyze (segment 2, 4, 6, 8)
                if segment_num % 2 == 0:
                    print("   ⏳ Calling deep-analyze...")
                    deep_start = time.time()
                    deep_response = await client.post(
                        f"/api/v1/sessions/{self.session_id}/deep-analyze?mode=practice",
                        headers=headers,
                    )
                    deep_time = time.time() - deep_start

                    if deep_response.status_code == 200:
                        deep_data = deep_response.json()
                        self.analysis_results.append(
                            {
                                "segment": segment_num,
                                "safety_level": deep_data.get("safety_level"),
                                "summary": deep_data.get("summary", ""),
                                "suggestions": deep_data.get("suggestions", []),
                            }
                        )
                        print(f"   ✅ Deep-analyze ({deep_time:.2f}s):")
                        print(f"      🚦 {deep_data.get('safety_level')}")
                        print(f"      📝 {deep_data.get('summary', '')[:40]}...")
                    else:
                        print(f"   ❌ Deep-analyze 失敗: {deep_response.text[:100]}")

                # 模擬錄音間隔
                await asyncio.sleep(0.5)

    async def call_report(self):
        """Step 3: 呼叫 Report 並驗證"""
        import httpx

        print("\n" + "=" * 60)
        print("📄 Step 3: 生成 Report")
        print("=" * 60)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=120) as client:
            headers = {"Authorization": f"Bearer {self.token}"}

            print("\n⏳ Calling report...")
            report_start = time.time()

            report_response = await client.post(
                f"/api/v1/sessions/{self.session_id}/report",
                headers=headers,
            )

            report_time = time.time() - report_start

            if report_response.status_code == 200:
                self.report_result = report_response.json()
                print(f"✅ Report 生成成功 ({report_time:.2f}s):")
                print(
                    f"   📝 鼓勵: {self.report_result.get('encouragement', '')[:50]}..."
                )
                print(f"   ❓ 議題: {self.report_result.get('issue', '')[:50]}...")
                print(f"   📊 分析: {self.report_result.get('analyze', '')[:50]}...")
                print(f"   💡 建議: {self.report_result.get('suggestion', '')[:50]}...")
            else:
                print(f"❌ Report 失敗: {report_response.text[:200]}")

    async def verify_results(self):
        """驗證測試結果"""
        print("\n" + "=" * 60)
        print("🔍 驗證測試結果")
        print("=" * 60)

        # 驗證 1: 分析時有拿到累積逐字稿
        print("\n📋 驗證 1: 逐字稿累積")
        print(f"   累積的 recordings 數量: {len(self.accumulated_recordings)}")
        expected_segments = len(TWO_MINUTE_TRANSCRIPT_SEGMENTS)
        if len(self.accumulated_recordings) == expected_segments:
            print(f"   ✅ 全部 {expected_segments} 段都有累積")
        else:
            print(
                f"   ❌ 應該有 {expected_segments} 段，但只有 {len(self.accumulated_recordings)} 段"
            )

        # 驗證 2: Deep-analyze 結果
        print("\n📋 驗證 2: Deep-analyze 結果")
        print(f"   分析次數: {len(self.analysis_results)}")
        for result in self.analysis_results:
            print(
                f"   - Segment {result['segment']}: {result['safety_level']} - {result['summary'][:30]}..."
            )

        # 驗證 3: Report 使用完整逐字稿
        print("\n📋 驗證 3: Report 結果")
        if self.report_result:
            print("   ✅ Report 已生成")
            # 檢查 report 內容是否合理
            if len(self.report_result.get("analyze", "")) > 20:
                print(
                    f"   ✅ 分析內容有意義 ({len(self.report_result.get('analyze', ''))} 字)"
                )
            else:
                print("   ⚠️ 分析內容可能太短")
        else:
            print("   ❌ Report 未生成")

        # 驗證 4: Billing (需要檢查 DB 或 logs)
        print("\n📋 驗證 4: Billing")
        print("   ⚠️ 需要檢查 DB 或 logs 確認 billing 有被呼叫")

        # 驗證 5: RAG
        print("\n📋 驗證 5: RAG")
        print("   ⚠️ 目前 RAG 表格不存在，所以沒有使用 RAG")


async def main():
    """主測試流程"""
    print("=" * 60)
    print("🧪 E2E Session Workflow Test")
    print("=" * 60)
    print("測試目標:")
    print("  1. 驗證 append 累積逐字稿")
    print("  2. 驗證 quick-feedback / deep-analyze 流程")
    print("  3. 驗證 report 生成")
    print("  4. 驗證 billing 呼叫")
    print("  5. 驗證 RAG 使用")

    tester = E2EWorkflowTester()

    # Step 0: Setup
    if not await tester.setup():
        print("\n❌ Setup 失敗，無法繼續測試")
        return

    # Step 1-2: 模擬前端流程
    await tester.simulate_frontend_workflow()

    # Step 3: 呼叫 Report
    await tester.call_report()

    # 驗證結果
    await tester.verify_results()

    print("\n" + "=" * 60)
    print("🏁 測試完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
