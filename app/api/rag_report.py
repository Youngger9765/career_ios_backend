"""API endpoints for case report generation"""

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Float, Integer, String, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/api/report", tags=["report"])


class ReportRequest(BaseModel):
    transcript: str
    top_k: int = 5
    similarity_threshold: float = 0.5


async def generate_report_stream(
    transcript: str,
    top_k: int,
    similarity_threshold: float,
    num_participants: int,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Generate case report with real-time progress updates using SSE

    Steps:
    1. Parse transcript structure
    2. Identify key issues and techniques
    3. RAG search for relevant theories
    4. Generate structured report
    """

    try:
        openai_service = OpenAIService()

        # Step 1: Parse transcript
        yield f"data: {json.dumps({'step': 1, 'status': 'processing', 'message': '正在分析逐字稿結構...'}, ensure_ascii=False)}\n\n"

        parse_prompt = f"""請分析以下職涯諮詢逐字稿，提取關鍵資訊：

逐字稿：
{transcript}

請以 JSON 格式回答（只要 JSON，不要其他文字）：
{{
  "client_name": "案主化名",
  "gender": "性別",
  "age": "年齡（若未提及則填'未提及'）",
  "occupation": "部門/職業或學校科系",
  "education": "學歷（若未提及則填'未提及'）",
  "location": "現居地（若未提及則填'未提及'）",
  "economic_status": "經濟狀況描述（若未提及則填'未提及'）",
  "family_relations": "家庭關係描述",
  "other_info": ["其他重要資訊1", "其他重要資訊2"],
  "main_concerns": ["主訴問題1", "主訴問題2"],
  "counseling_goals": ["晤談目標1", "晤談目標2"],
  "counselor_techniques": ["使用的諮詢技巧1", "技巧2"],
  "session_content": "晤談內容概述",
  "counselor_self_evaluation": "諮詢師對本次晤談的自我評估"
}}
"""

        parse_response = await openai_service.chat_completion(
            messages=[{"role": "user", "content": parse_prompt}], temperature=0.3
        )

        # Parse JSON from response
        try:
            parsed_data = json.loads(parse_response)
        except json.JSONDecodeError:
            # If not valid JSON, extract between { and }
            import re

            json_match = re.search(r"\{.*\}", parse_response, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group(0))
            else:
                parsed_data = {
                    "client_name": "未提供",
                    "gender": "未提及",
                    "age": "未提及",
                    "occupation": "未提及",
                    "education": "未提及",
                    "location": "未提及",
                    "economic_status": "未提及",
                    "family_relations": "未提及",
                    "other_info": [],
                    "main_concerns": [],
                    "counseling_goals": [],
                    "counselor_techniques": [],
                    "session_content": "無法解析",
                    "counselor_self_evaluation": "無法解析",
                }

        yield f"data: {json.dumps({'step': 1, 'status': 'completed', 'message': '逐字稿分析完成', 'data': parsed_data}, ensure_ascii=False)}\n\n"

        # Step 2: Identify key issues
        yield f"data: {json.dumps({'step': 2, 'status': 'processing', 'message': '正在識別關鍵議題和技巧...'}, ensure_ascii=False)}\n\n"

        main_concerns = parsed_data.get("main_concerns", [])
        techniques = parsed_data.get("counselor_techniques", [])

        yield f"data: {json.dumps({'step': 2, 'status': 'completed', 'message': f'識別到 {len(main_concerns)} 個關鍵議題', 'data': {'concerns': main_concerns, 'techniques': techniques}}, ensure_ascii=False)}\n\n"

        # Step 3: RAG search for relevant theories
        yield f"data: {json.dumps({'step': 3, 'status': 'processing', 'message': '正在檢索相關理論...'}, ensure_ascii=False)}\n\n"

        # Search for theories related to main concerns
        search_query = " ".join(main_concerns[:3])  # Top 3 concerns
        query_embedding = await openai_service.create_embedding(search_query)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        query_sql = text(
            """
            SELECT
                c.id as chunk_id,
                c.text,
                d.title as document_title,
                1 - (e.embedding <=> CAST(:query_embedding AS vector)) as similarity_score
            FROM chunks c
            JOIN embeddings e ON c.id = e.chunk_id
            JOIN documents d ON c.doc_id = d.id
            WHERE 1 - (e.embedding <=> CAST(:query_embedding AS vector)) >= :threshold
            ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """
        ).bindparams(
            bindparam("query_embedding", type_=String),
            bindparam("threshold", type_=Float),
            bindparam("top_k", type_=Integer),
        )

        result = await db.execute(
            query_sql,
            {
                "query_embedding": embedding_str,
                "threshold": similarity_threshold,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()
        theories = [
            {"text": row.text, "document": row.document_title, "score": float(row.similarity_score)}
            for row in rows
        ]

        yield f"data: {json.dumps({'step': 3, 'status': 'completed', 'message': f'檢索到 {len(theories)} 個相關理論', 'data': {'theories': theories}}, ensure_ascii=False)}\n\n"

        # Step 4: Generate structured report
        yield f"data: {json.dumps({'step': 4, 'status': 'processing', 'message': '正在生成個案報告...'}, ensure_ascii=False)}\n\n"

        # Construct context from theories
        context_parts = [f"[{i+1}] {theory['text']}" for i, theory in enumerate(theories)]
        context = "\n\n".join(context_parts)

        report_prompt = f"""你是一位專業的職涯諮詢督導。請根據以下資訊生成個案報告：

**案主基本資料：**
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
- 性別：{parsed_data.get('gender', '未提及')}
- 年齡：{parsed_data.get('age', '未提及')}
- 部門/職業（學校科系）：{parsed_data.get('occupation', '未提及')}
- 學歷：{parsed_data.get('education', '未提及')}
- 現居地：{parsed_data.get('location', '未提及')}
- 經濟狀況：{parsed_data.get('economic_status', '未提及')}
- 家庭關係：{parsed_data.get('family_relations', '未提及')}
- 其他重要資訊：{', '.join(parsed_data.get('other_info', []))}

**晤談內容概述：**
{parsed_data.get('session_content', '')}

**主訴問題：**
{', '.join(main_concerns)}

**晤談目標：**
{', '.join(parsed_data.get('counseling_goals', []))}

**使用的諮詢技巧：**
{', '.join(techniques)}

**相關理論參考：**
{context}

請生成結構化的個案報告，包含以下部分：

【主訴問題】
個案說的，此次想要討論的議題

【成因分析】
諮詢師您認為，個案為何會有這些主訴問題，請結合引用的理論 [1], [2] 等進行分析

【晤談目標（移動主訴）】
諮詢師對個案諮詢目標的假設，須與個案確認

【介入策略】
諮詢師判斷會需要帶個案做的事，結合理論說明

【目前成效評估】
上述目標和策略達成的狀況如何，目前打算如何修正

重要提醒：
1. 請使用專業、客觀、具同理心的語氣
2. 適當引用理論文獻 [1], [2] 等
3. 不要使用 markdown 格式（如 ##, ###, **, - 等符號）
4. 使用【標題】的格式來區分段落
5. 內容直接書寫，不要用項目符號
"""

        report_content = await openai_service.chat_completion(
            messages=[{"role": "user", "content": report_prompt}], temperature=0.6
        )

        # Step 5: Extract key dialogue excerpts (5-10 exchanges)
        yield f"data: {json.dumps({'step': 5, 'status': 'processing', 'message': '正在提取關鍵對話片段...'}, ensure_ascii=False)}\n\n"

        # Build speaker labels based on num_participants
        if num_participants == 2:
            speaker_instruction = (
                '- speaker 使用 "speaker1"（通常為諮詢師）和 "speaker2"（通常為個案）'
            )
            speaker_example = """  "dialogues": [
    {{"speaker": "speaker1", "order": 1, "text": "諮詢師的話"}},
    {{"speaker": "speaker2", "order": 2, "text": "個案的話"}},
    {{"speaker": "speaker1", "order": 3, "text": "諮詢師的話"}}
  ]"""
        else:
            speaker_labels = ", ".join([f'"speaker{i+1}"' for i in range(num_participants)])
            speaker_instruction = f"- speaker 使用 {speaker_labels}，根據逐字稿上下文判斷每位說話者"
            speaker_example = """  "dialogues": [
    {{"speaker": "speaker1", "order": 1, "text": "說話內容"}},
    {{"speaker": "speaker2", "order": 2, "text": "說話內容"}},
    {{"speaker": "speaker1", "order": 3, "text": "說話內容"}}
  ]"""

        excerpt_prompt = f"""請從以下逐字稿中，挑選 5-10 句最能體現個案樣貌和諮詢重點的關鍵對話。

逐字稿：
{transcript}

會談人數：{num_participants} 人

請以 JSON 格式回答（只要 JSON，不要其他文字）：
{{
{speaker_example}
}}

注意：
{speaker_instruction}
- 請根據逐字稿的語境和內容，自動判斷每句話是誰說的
- order 是對話順序編號
- 挑選能展現個案核心議題、情緒狀態、或關鍵轉變的對話
- 如果逐字稿中有明確標示說話者（如 Co:、Cl:、諮詢師：、個案：等），請參考這些標示
"""

        excerpt_response = await openai_service.chat_completion(
            messages=[{"role": "user", "content": excerpt_prompt}], temperature=0.3
        )

        try:
            excerpt_data = json.loads(excerpt_response)
            dialogues = excerpt_data.get("dialogues", [])
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"\{.*\}", excerpt_response, re.DOTALL)
            if json_match:
                excerpt_data = json.loads(json_match.group(0))
                dialogues = excerpt_data.get("dialogues", [])
            else:
                dialogues = []

        # Parse report into sections
        report = {
            "client_info": {
                "name": parsed_data.get("client_name", "未提供"),
                "gender": parsed_data.get("gender", "未提及"),
                "age": parsed_data.get("age", "未提及"),
                "occupation": parsed_data.get("occupation", "未提及"),
                "education": parsed_data.get("education", "未提及"),
                "location": parsed_data.get("location", "未提及"),
                "economic_status": parsed_data.get("economic_status", "未提及"),
                "family_relations": parsed_data.get("family_relations", "未提及"),
                "other_info": parsed_data.get("other_info", []),
            },
            "session_summary": {
                "content": parsed_data.get("session_content", ""),
                "self_evaluation": parsed_data.get("counselor_self_evaluation", ""),
            },
            "conceptualization": report_content,
            "main_concerns": main_concerns,
            "counseling_goals": parsed_data.get("counseling_goals", []),
            "techniques": techniques,
            "theories": theories,
            "dialogue_excerpts": dialogues,
        }

        yield f"data: {json.dumps({'step': 5, 'status': 'completed', 'message': '個案報告生成完成', 'data': {'report': report}}, ensure_ascii=False)}\n\n"

        # Final message
        yield f"data: {json.dumps({'step': 6, 'status': 'completed', 'message': '全部完成！'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'message': f'發生錯誤: {str(e)}'}, ensure_ascii=False)}\n\n"


@router.get("/generate")
async def generate_report(
    transcript: str,
    top_k: int = 5,
    similarity_threshold: float = 0.5,
    num_participants: int = 2,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate case report from transcript with real-time progress updates

    Returns: SSE stream with progress updates
    """

    return StreamingResponse(
        generate_report_stream(transcript, top_k, similarity_threshold, num_participants, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
