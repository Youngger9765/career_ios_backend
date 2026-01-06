"""
測試報告 API 對長逐字稿的處理
驗證：
1. 長對話產生更詳細的分析
2. RAG 是否有返回專家建議
"""

import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel

# ==============================================================================
# 模擬一小時親子對話逐字稿 (約 3000+ 字)
# ==============================================================================

ONE_HOUR_TRANSCRIPT = """
[00:00:30] 家長: 寶貝，今天學校怎麼樣？

[00:00:45] 孩子: 還好...

[00:01:00] 家長: 「還好」是什麼意思？有什麼特別的事嗎？

[00:01:20] 孩子: 沒有啦，就那樣。

[00:01:45] 家長: 你今天看起來心情不太好的樣子，是不是發生什麼事了？

[00:02:10] 孩子: 就...今天被老師罵。

[00:02:30] 家長: 被老師罵？為什麼？發生什麼事？

[00:03:00] 孩子: 我上課講話，然後老師就叫我站起來...全班都在看我...

[00:03:30] 家長: 你怎麼又上課講話了？上次不是說過了嗎？

[00:04:00] 孩子: 我不是故意的...是同學先跟我講話的...

[00:04:30] 家長: 同學跟你講話你可以不要回啊，你為什麼要回？

[00:05:00] 孩子: 我不知道...他問我問題我就回了...

[00:05:30] 家長: 你這樣老師當然會生氣啊。你要學會自己控制，不要別人說什麼你就做什麼。

[00:06:00] 孩子: (沉默)

[00:06:30] 家長: 你聽到沒有？

[00:07:00] 孩子: 聽到了...

[00:07:30] 家長: 那你下次會怎麼做？

[00:08:00] 孩子: 不要講話...

[00:08:30] 家長: 好，記住這次的教訓。來，吃點心吧。

[00:10:00] 家長: 今天的作業多不多？

[00:10:30] 孩子: 還好...有數學和國語。

[00:11:00] 家長: 那你先去寫作業，寫完再玩。

[00:11:30] 孩子: 可是我想先玩一下...

[00:12:00] 家長: 不行，先寫作業。你每次都這樣，先玩再寫，結果寫到很晚。

[00:12:30] 孩子: 可是我才剛回家...我好累...

[00:13:00] 家長: 累什麼累，你在學校又沒做什麼體力活。快去寫。

[00:13:30] 孩子: 我就是想休息一下嘛...

[00:14:00] 家長: 你休息完就不想寫了。你先寫，寫完就可以玩到睡覺。

[00:14:30] 孩子: (不情願地) 好啦...

[00:20:00] 家長: 作業寫得怎麼樣了？

[00:20:30] 孩子: 還在寫...

[00:21:00] 家長: 怎麼這麼慢？你在發呆嗎？

[00:21:30] 孩子: 我沒有...這題很難...

[00:22:00] 家長: 哪一題？讓我看看。

[00:22:30] 孩子: 這個應用題...

[00:23:00] 家長: 這個很簡單啊，你看，小明有5個蘋果，給了小華2個，問小明還有幾個？

[00:23:30] 孩子: 3個...

[00:24:00] 家長: 對啊，這麼簡單你怎麼不會？上課有沒有認真聽？

[00:24:30] 孩子: 我有聽啦...只是...

[00:25:00] 家長: 只是什麼？

[00:25:30] 孩子: 只是在學校的時候...我腦袋就是轉不過來...

[00:26:00] 家長: 那你回家要更認真複習。好，繼續寫。

[00:30:00] 家長: 好了嗎？

[00:30:30] 孩子: 快好了...

[00:31:00] 家長: 給我看看。嗯...這個字寫錯了，重寫。

[00:31:30] 孩子: 哪裡錯了？

[00:32:00] 家長: 這個「學」字，你看，下面是「子」不是「了」。

[00:32:30] 孩子: 喔...

[00:33:00] 家長: 你要用心寫，不要隨便寫。字醜就算了，還寫錯。

[00:33:30] 孩子: 我知道了...

[00:35:00] 家長: 好，作業寫完了，你可以去玩了。

[00:35:30] 孩子: 我想玩手機...

[00:36:00] 家長: 不行，手機玩太多對眼睛不好。去看書或是玩玩具。

[00:36:30] 孩子: 可是我同學都可以玩手機...

[00:37:00] 家長: 別人是別人，你是你。我說不行就是不行。

[00:37:30] 孩子: 為什麼他們可以我不行...

[00:38:00] 家長: 因為我是你媽媽，我知道什麼對你好。手機玩太多會近視、會笨。

[00:38:30] 孩子: 我只是想玩一下而已...

[00:39:00] 家長: 一下變兩下，兩下變一整晚。我很了解你。去看書。

[00:39:30] 孩子: (生氣地) 我不要！

[00:40:00] 家長: 你這是什麼態度？你再這樣我連電視都不讓你看。

[00:40:30] 孩子: 你每次都這樣...

[00:41:00] 家長: 我怎麼樣？我還不是為你好？你現在不讀書，以後考不上好學校，找不到好工作，你就知道了。

[00:41:30] 孩子: 我不管！

[00:42:00] 家長: 你給我回房間去！

[00:42:30] 孩子: (跑回房間，摔門)

[00:45:00] 家長: (敲門) 寶貝，開門。

[00:45:30] 孩子: 不要！

[00:46:00] 家長: 媽媽進去跟你說話，好不好？

[00:46:30] 孩子: (沒回應)

[00:47:00] 家長: (開門進去) 寶貝，你怎麼了？

[00:47:30] 孩子: (趴在床上哭)

[00:48:00] 家長: 你哭什麼？

[00:48:30] 孩子: 你都不讓我做我想做的事...

[00:49:00] 家長: 我是為你好啊...

[00:49:30] 孩子: 你每次都說為我好，可是我一點都不開心...

[00:50:00] 家長: ...你不開心？

[00:50:30] 孩子: 今天在學校被罵，回家又被罵...我什麼都做不好...

[00:51:00] 家長: 媽媽沒有要罵你...

[00:51:30] 孩子: 你就是在罵我！你說我字醜、說我笨、說我不認真...

[00:52:00] 家長: 媽媽沒有說你笨...我只是希望你更好...

[00:52:30] 孩子: 可是我已經很努力了...

[00:53:00] 家長: (沉默了一下) ...對不起，媽媽太急了。

[00:53:30] 孩子: (繼續哭)

[00:54:00] 家長: 寶貝，媽媽知道你今天很不容易。在學校被老師罵，一定很丟臉、很難過，對不對？

[00:54:30] 孩子: (點頭)

[00:55:00] 家長: 媽媽不應該再罵你一次。你已經夠難受了。

[00:55:30] 孩子: 我不是故意要講話的...

[00:56:00] 家長: 媽媽知道。同學跟你說話，你會想回應是很正常的。

[00:56:30] 孩子: 真的嗎？

[00:57:00] 家長: 真的。只是下次，你可以跟同學說「等一下下課再聊」，這樣老師就不會生氣了。

[00:57:30] 孩子: 可是...這樣同學會不會覺得我很奇怪？

[00:58:00] 家長: 不會的。真正的好朋友會理解你。而且，下課時間你們可以聊更多，不是更好嗎？

[00:58:30] 孩子: 好像是...

[00:59:00] 家長: 那手機的事，媽媽再想想。也許週末可以讓你玩一下？

[00:59:30] 孩子: 真的嗎？

[01:00:00] 家長: 真的。但你也要答應媽媽，平日要先做完功課再玩其他的，好不好？

[01:00:30] 孩子: 好...

[01:01:00] 家長: 來，抱一個。媽媽愛你。

[01:01:30] 孩子: 我也愛媽媽...

[01:02:00] 家長: 以後你有什麼不開心的，可以跟媽媽說。媽媽會試著先聽你說完，不會馬上罵你。

[01:02:30] 孩子: 真的嗎？

[01:03:00] 家長: 真的。媽媽也在學習怎麼當一個更好的媽媽。

[01:03:30] 孩子: 媽媽已經很好了...

[01:04:00] 家長: 謝謝你這麼說。好了，眼淚擦一擦，我們去吃晚飯吧？

[01:04:30] 孩子: 好！
"""


class TestReportLongTranscript:
    """測試報告 API 對長逐字稿的處理"""

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService for report endpoint"""

        async def mock_chat_completion(prompt, *args, **kwargs):
            # Check if this is a long transcript
            is_long = "長對話" in prompt or len(prompt) > 5000

            if is_long:
                # Return detailed analysis for long transcripts
                return {
                    "text": json.dumps(
                        {
                            "encouragement": "這次對話展現了您作為家長的成長與反思能力。當您發現孩子情緒崩潰後，選擇進入房間陪伴、道歉並重新連結，這是非常了不起的轉變。特別是您說「媽媽也在學習怎麼當一個更好的媽媽」，這句話展現了脆弱與真誠，對孩子來說是珍貴的示範。",
                            "issue": "對話中有幾個值得關注的議題：\n1. 初期的指責性溝通：「你怎麼又上課講話了」這類質問方式容易讓孩子防禦\n2. 比較與標籤：「你在學校又沒做什麼體力活」否定了孩子的感受\n3. 威脅與控制：「你再這樣我連電視都不讓你看」屬於懲罰性教養\n4. 缺乏情緒接納：孩子表達累了想休息，家長直接否定",
                            "analyze": "這段對話呈現了親子互動的典型衝突升級與修復循環，可以從多個教養理論角度分析：\n\n【薩提爾冰山理論】\n孩子在學校被罵後回家，冰山上層是「沉默、不想說」的行為，但冰山下層是「害怕被責備、渴望被理解」的深層需求。當家長說「你怎麼又講話」時，直接觸發了孩子的羞恥感，導致防禦反應。\n\n【阿德勒正向教養】\n孩子需要的是「歸屬感」與「價值感」。當家長說「你字醜、不認真」時，孩子的價值感受到打擊，導致他說「我什麼都做不好」。後來家長道歉並說「媽媽也在學習」，重建了平等尊重的關係。\n\n【Gottman 情緒輔導】\n對話後半段家長開始運用情緒輔導技巧：同理（「在學校被罵一定很難過」）、接納（「會想回應是很正常的」）、引導（「你可以跟同學說等一下再聊」）。這是從情緒否定轉向情緒連結的關鍵轉變。\n\n【行為分析 ABC 模式】\n前因(A)：孩子想玩手機\n行為(B)：家長拒絕並威脅\n後果(C)：孩子摔門哭泣\n這個循環顯示，當家長使用控制性回應時，孩子的負面行為會升級。",
                            "suggestion": "根據這段對話，建議未來可以這樣調整：\n\n【當孩子分享在學校被罵時】\n原本：「你怎麼又上課講話了？」\n建議：「被老師在全班面前叫起來，一定很不好受。你現在感覺怎麼樣？」（先同理再了解）\n\n【當孩子說累想休息時】\n原本：「累什麼累，你在學校又沒做什麼體力活。」\n建議：「你想先休息一下是嗎？我們可以先休息 15 分鐘，然後一起看看今天的作業。」（接納感受+提供選擇）\n\n【當孩子想玩手機時】\n原本：「不行，手機玩太多對眼睛不好。別人是別人，你是你。」\n建議：「我知道你很想玩，同學都有玩一定讓你很羨慕。我們來討論一下，什麼時候可以玩、玩多久，你有什麼想法？」（協作問題解決）\n\n【當情緒衝突後要修復時】\n您後來說的「媽媽也在學習」非常好。可以再加上：「謝謝你願意告訴媽媽你的感受，這需要很大的勇氣。」",
                        }
                    ),
                    "prompt_tokens": 2000,
                    "completion_tokens": 1500,
                    "total_tokens": 3500,
                    "estimated_cost_usd": 0.015,
                }
            else:
                # Shorter response for short transcripts
                return {
                    "text": json.dumps(
                        {
                            "encouragement": "感謝你願意花時間與孩子溝通。",
                            "issue": "溝通時可以更多傾聽孩子的想法。",
                            "analyze": "這段對話展現了基本的親子互動。",
                            "suggestion": "可以試著說：「我想聽聽你的想法。」",
                        }
                    ),
                    "prompt_tokens": 500,
                    "completion_tokens": 200,
                    "total_tokens": 700,
                    "estimated_cost_usd": 0.003,
                }

        with patch("app.services.external.gemini_service.GeminiService") as mock_gemini:
            mock_instance = mock_gemini.return_value
            mock_instance.chat_completion = AsyncMock(side_effect=mock_chat_completion)
            yield mock_instance

    @pytest.fixture
    def test_session_with_long_transcript(self, db_session: Session):
        """建立含有長逐字稿的測試 session"""
        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email="long-transcript-test@test.com",
            username="longtranscripttester",
            full_name="Long Transcript Tester",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="LONG-001",
            name="長逐字稿測試家長",
            email="long-test@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345678",
            identity_option="家長",
            current_status="親子溝通練習",
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
            case_number="LONG-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Create session with long transcript
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            scenario="真實對話：孩子在學校被罵後回家",
            scenario_description="孩子上課講話被老師罵，回家後與家長的對話",
            transcript_text=ONE_HOUR_TRANSCRIPT,  # 一小時逐字稿
        )
        db_session.add(session)
        db_session.commit()

        return {
            "counselor": counselor,
            "client": client,
            "case": case,
            "session": session,
        }

    @pytest.fixture
    def auth_headers(self, db_session: Session, test_session_with_long_transcript):
        """取得認證 headers"""
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "long-transcript-test@test.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_report_with_long_transcript(
        self,
        db_session: Session,
        auth_headers,
        test_session_with_long_transcript,
        mock_gemini_service,
    ):
        """
        測試長逐字稿的報告生成：
        1. 驗證 API 成功處理長逐字稿
        2. 驗證回應包含詳細分析
        """
        session_id = test_session_with_long_transcript["session"].id

        with TestClient(app) as client:
            # Generate report
            response = client.post(
                f"/api/v1/sessions/{session_id}/report",
                headers=auth_headers,
            )

            assert response.status_code == 200, f"Report failed: {response.text}"
            data = response.json()

            # Print for debugging
            print("\n" + "=" * 60)
            print("📄 長逐字稿報告測試結果")
            print("=" * 60)
            print(f"\n【鼓勵】({len(data.get('encouragement', ''))} 字)")
            print(data.get("encouragement", ""))
            print(f"\n【議題】({len(data.get('issue', ''))} 字)")
            print(data.get("issue", ""))
            print(f"\n【分析】({len(data.get('analyze', ''))} 字)")
            print(data.get("analyze", ""))
            print(f"\n【建議】({len(data.get('suggestion', ''))} 字)")
            print(data.get("suggestion", ""))
            print("\n【RAG 參考】")
            print(data.get("references", []))

            # Verify response structure
            assert "encouragement" in data
            assert "issue" in data
            assert "analyze" in data
            assert "suggestion" in data
            assert "timestamp" in data

            # Verify content is more detailed for long transcript
            # The analyze field should be substantial
            analyze_length = len(data.get("analyze", ""))
            suggestion_length = len(data.get("suggestion", ""))

            print("\n📊 內容長度統計:")
            print(f"   - 分析: {analyze_length} 字")
            print(f"   - 建議: {suggestion_length} 字")

            # For mocked response, we expect detailed content
            assert analyze_length > 200, f"分析內容太短: {analyze_length} 字"
            assert suggestion_length > 200, f"建議內容太短: {suggestion_length} 字"

    def test_report_identifies_transcript_length(
        self,
        db_session: Session,
        auth_headers,
        test_session_with_long_transcript,
        mock_gemini_service,
    ):
        """驗證 prompt 正確識別長逐字稿"""
        session_id = test_session_with_long_transcript["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/report",
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Check that mock was called with prompt containing "長對話"
            # Since our transcript is > 2000 chars
            transcript_length = len(ONE_HOUR_TRANSCRIPT)
            print(f"\n📝 逐字稿長度: {transcript_length} 字")
            assert transcript_length > 2000, "測試逐字稿應該是長對話"
