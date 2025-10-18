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
from app.services.gemini_service import gemini_service

router = APIRouter(prefix="/api/report", tags=["report"])


def format_report_as_html(report: dict) -> str:
    """Convert report to HTML format"""
    html = "<html><body>"
    html += f"<h1>個案報告</h1>"

    # Client info
    html += "<h2>案主基本資料</h2><table border='1'>"
    for key, value in report['client_info'].items():
        if isinstance(value, list):
            value = ", ".join(value)
        html += f"<tr><th>{key}</th><td>{value}</td></tr>"
    html += "</table>"

    # Main concerns
    html += "<h2>主訴問題</h2><ul>"
    for concern in report['main_concerns']:
        html += f"<li>{concern}</li>"
    html += "</ul>"

    # Goals
    html += "<h2>晤談目標</h2><ul>"
    for goal in report['counseling_goals']:
        html += f"<li>{goal}</li>"
    html += "</ul>"

    # Techniques
    html += "<h2>諮詢技巧</h2><ul>"
    for technique in report['techniques']:
        html += f"<li>{technique}</li>"
    html += "</ul>"

    # Conceptualization
    html += "<h2>個案概念化</h2>"
    html += f"<pre>{report['conceptualization']}</pre>"

    # Theories
    html += "<h2>相關理論文獻</h2><ul>"
    for theory in report['theories']:
        html += f"<li><b>{theory['document']}</b> (相似度: {theory['score']:.2f})<br>{theory['text'][:200]}...</li>"
    html += "</ul>"

    # Dialogues
    html += "<h2>關鍵對話摘錄</h2><ol>"
    for dialogue in report['dialogue_excerpts']:
        html += f"<li><b>{dialogue['speaker']}</b>: {dialogue['text']}</li>"
    html += "</ol>"

    html += "</body></html>"
    return html


def format_report_as_markdown(report: dict) -> str:
    """Convert report to Markdown format"""
    md = "# 個案報告\n\n"

    # Client info
    md += "## 案主基本資料\n\n"
    for key, value in report['client_info'].items():
        if isinstance(value, list):
            value = ", ".join(value)
        md += f"- **{key}**: {value}\n"
    md += "\n"

    # Main concerns
    md += "## 主訴問題\n\n"
    for concern in report['main_concerns']:
        md += f"- {concern}\n"
    md += "\n"

    # Goals
    md += "## 晤談目標\n\n"
    for goal in report['counseling_goals']:
        md += f"- {goal}\n"
    md += "\n"

    # Techniques
    md += "## 諮詢技巧\n\n"
    for technique in report['techniques']:
        md += f"- {technique}\n"
    md += "\n"

    # Conceptualization
    md += "## 個案概念化\n\n"
    md += f"{report['conceptualization']}\n\n"

    # Theories
    md += "## 相關理論文獻\n\n"
    for i, theory in enumerate(report['theories'], 1):
        md += f"### [{i}] {theory['document']}\n\n"
        md += f"**相似度**: {theory['score']:.2f}\n\n"
        md += f"{theory['text'][:200]}...\n\n"

    # Dialogues
    md += "## 關鍵對話摘錄\n\n"
    for dialogue in report['dialogue_excerpts']:
        md += f"{dialogue['order']}. **{dialogue['speaker']}**: {dialogue['text']}\n"
    md += "\n"

    return md


class ReportRequest(BaseModel):
    transcript: str
    num_participants: int = 2
    rag_system: str = "openai"  # "openai" or "gemini"
    top_k: int = 7
    similarity_threshold: float = 0.25  # Lowered from 0.5 to 0.25 for better recall
    output_format: str = "json"  # "json", "html", or "markdown"
    use_legacy: bool = False  # True = 舊版邏輯（無驗證），False = 新版（有驗證）


async def generate_report_stream(
    transcript: str,
    top_k: int,
    similarity_threshold: float,
    num_participants: int,
    rag_system: str,
    output_format: str,
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

        # Step 3: RAG search for relevant theories (always use OpenAI embeddings)
        yield f"data: {json.dumps({'step': 3, 'status': 'processing', 'message': '正在檢索相關理論...'}, ensure_ascii=False)}\n\n"

        # M2.1: Enhanced query construction with demographics + career stage
        from app.utils.rag_query_builder import build_enhanced_query

        search_query = build_enhanced_query(parsed_data)

        # Always use OpenAI embedding for search
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

        result = db.execute(
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
        yield f"data: {json.dumps({'step': 4, 'status': 'processing', 'message': f'正在生成個案報告（使用 {rag_system.upper()} 模型）...'}, ensure_ascii=False)}\n\n"

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

        # Use selected LLM model based on rag_system
        if rag_system == "gemini":
            report_content = await gemini_service.chat_completion(report_prompt, temperature=0.6)
        else:
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

        # Use selected LLM model based on rag_system
        if rag_system == "gemini":
            excerpt_response = await gemini_service.chat_completion(excerpt_prompt, temperature=0.3)
        else:
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

        # Format report based on output_format
        if output_format == "html":
            formatted_report = format_report_as_html(report)
            yield f"data: {json.dumps({'step': 5, 'status': 'completed', 'message': '個案報告生成完成', 'data': {'report': formatted_report, 'format': 'html'}}, ensure_ascii=False)}\n\n"
        elif output_format == "markdown":
            formatted_report = format_report_as_markdown(report)
            yield f"data: {json.dumps({'step': 5, 'status': 'completed', 'message': '個案報告生成完成', 'data': {'report': formatted_report, 'format': 'markdown'}}, ensure_ascii=False)}\n\n"
        else:  # json (default)
            yield f"data: {json.dumps({'step': 5, 'status': 'completed', 'message': '個案報告生成完成', 'data': {'report': report, 'format': 'json'}}, ensure_ascii=False)}\n\n"

        # Final message
        yield f"data: {json.dumps({'step': 6, 'status': 'completed', 'message': '全部完成！'}, ensure_ascii=False)}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'message': f'發生錯誤: {str(e)}'}, ensure_ascii=False)}\n\n"


@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate case report from transcript - direct JSON response

    Args:
        request: Request body containing transcript and optional parameters
            - transcript (str): Counseling transcript text
            - rag_system (str): LLM model - "openai" (GPT-4.1 Mini) or "gemini" (Gemini 2.5 Flash)
            - num_participants (int): Number of participants in session
            - top_k (int): Number of theory documents to retrieve
            - similarity_threshold (float): Similarity threshold for RAG retrieval

    Returns: Complete report as JSON
    """

    try:
        openai_service = OpenAIService()

        # Step 1: Parse transcript
        parse_prompt = f"""請分析以下職涯諮詢逐字稿，提取關鍵資訊：

逐字稿：
{request.transcript}

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

        # Step 2: RAG search for relevant theories
        main_concerns = parsed_data.get("main_concerns", [])
        techniques = parsed_data.get("counselor_techniques", [])
        search_terms = main_concerns[:3] + techniques[:2]
        search_query = " ".join(search_terms) if search_terms else "職涯諮詢 生涯發展"

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

        result = db.execute(
            query_sql,
            {
                "query_embedding": embedding_str,
                "threshold": request.similarity_threshold,
                "top_k": request.top_k,
            },
        )

        rows = result.fetchall()
        theories = [
            {"text": row.text, "document": row.document_title, "score": float(row.similarity_score)}
            for row in rows
        ]

        # Step 3: Generate structured report
        context_parts = [f"[{i+1}] {theory['text']}" for i, theory in enumerate(theories)]
        context = "\n\n".join(context_parts)

        # Choose prompt based on use_legacy flag
        if request.use_legacy:
            # Legacy version: Simple 5-section prompt (staging logic)
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
        else:
            # Enhanced version: Structured 10-section prompt with validation
            report_prompt = f"""你是職涯諮詢督導，協助新手諮詢師撰寫個案概念化報告。

你的優勢：快速從大量文獻中找到最適合此個案的理論和策略。

【案主資料】
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
- 性別：{parsed_data.get('gender', '未提及')}
- 年齡：{parsed_data.get('age', '未提及')}
- 部門/職業：{parsed_data.get('occupation', '未提及')}
- 學歷：{parsed_data.get('education', '未提及')}
- 現居地：{parsed_data.get('location', '未提及')}
- 經濟狀況：{parsed_data.get('economic_status', '未提及')}
- 家庭關係：{parsed_data.get('family_relations', '未提及')}

【晤談摘要】
{parsed_data.get('session_content', '')}

【主訴】{', '.join(main_concerns)}
【目標】{', '.join(parsed_data.get('counseling_goals', []))}
【技巧】{', '.join(techniques)}

【相關理論文獻】（請在適當段落引用 [1], [2]）
{context}

請生成以下結構的個案報告（所有段落必須包含）：

【一、案主基本資料】
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
- 性別：{parsed_data.get('gender', '未提及')}
- 年齡：{parsed_data.get('age', '未提及')}
- 部門/職業：{parsed_data.get('occupation', '未提及')}
- 學歷：{parsed_data.get('education', '未提及')}
- 現居地：{parsed_data.get('location', '未提及')}
- 經濟狀況：{parsed_data.get('economic_status', '未提及')}
- 家庭關係：{parsed_data.get('family_relations', '未提及')}

【二、主訴問題】
- 個案陳述：（個案原話中的困擾）
- 諮詢師觀察：（你在晤談中觀察到的議題）

【三、問題發展脈絡】
- 出現時間：（何時開始）
- 持續頻率：（多久發生一次）
- 影響程度：（對生活/工作的影響）

【四、求助動機與期待】
- 引發因素：（為何此時求助）
- 期待目標：（希望改善什麼）

【五、多層次因素分析】⭐ 核心段落（必須引用理論 [1][2]）
分析以下層次，並引用理論：
- 個人因素：（年齡/生涯階段、性格、能力）
- 人際因素：（家庭、社會支持）
- 環境因素：（職場/學校、經濟）
- 發展因素：（生涯成熟度、早期經驗）

引用要求：必須說明「根據理論 [X]，案主...」或「從 [X] 觀點...」

【六、個案優勢與資源】
- 心理優勢：（情緒調適、動機）
- 社會資源：（支持系統）

【七、諮詢師的專業判斷】⭐ 核心段落（必須引用理論 [3][4]）
- 問題假設：（為何有這些困擾）
- 理論依據：（用什麼理論支持判斷）引用 [3][4]
- 理論取向：（採用的觀點）

引用要求：說明「基於理論 [X]，我認為問題源於...」

【八、諮商目標與介入策略】⭐ 核心段落（必須引用 [5][6]）
- 諮商目標：（SMART 格式，具體可衡量）
- 介入技術：（使用的方法）引用 [5][6]
- 技術理由：（為何這技術適合此個案）
- 介入步驟：（執行順序）

引用要求：說明「選擇此技術因為...，理論 [X] 指出...」

【九、預期成效與評估】
- 短期指標：（3 個月內如何判斷進步）
- 長期指標：（6-12 個月目標）
- 可能調整：（什麼情況需改變策略）

【十、諮詢師自我反思】
{parsed_data.get('counselor_self_evaluation', '請反思本次晤談優點和可改進處')}

格式要求：
1. 必須包含上述所有段落，用【】標題
2. 第五、七、八段落必須引用理論 [1][2] 格式
3. 每個引用要說明為何適用
4. 不用 markdown（##, **, -）
5. 每段至少 2-3 句，不可空白
"""

            # M2.2: Add rationale examples to prompt (only for enhanced version)
            from app.utils.prompt_enhancer import add_rationale_examples
            report_prompt = add_rationale_examples(report_prompt)

        if request.rag_system == "gemini":
            report_content = await gemini_service.chat_completion(report_prompt, temperature=0.6)
        else:
            report_content = await openai_service.chat_completion(
                messages=[{"role": "user", "content": report_prompt}], temperature=0.6
            )

        # Step 4: Extract key dialogue excerpts
        if request.num_participants == 2:
            speaker_instruction = '- speaker 使用 "speaker1"（通常為諮詢師）和 "speaker2"（通常為個案）'
            speaker_example = """  "dialogues": [
    {{"speaker": "speaker1", "order": 1, "text": "諮詢師的話"}},
    {{"speaker": "speaker2", "order": 2, "text": "個案的話"}},
    {{"speaker": "speaker1", "order": 3, "text": "諮詢師的話"}}
  ]"""
        else:
            speaker_labels = ", ".join([f'"speaker{i+1}"' for i in range(request.num_participants)])
            speaker_instruction = f"- speaker 使用 {speaker_labels}，根據逐字稿上下文判斷每位說話者"
            speaker_example = """  "dialogues": [
    {{"speaker": "speaker1", "order": 1, "text": "說話內容"}},
    {{"speaker": "speaker2", "order": 2, "text": "說話內容"}},
    {{"speaker": "speaker1", "order": 3, "text": "說話內容"}}
  ]"""

        excerpt_prompt = f"""請從以下逐字稿中，挑選 5-10 句最能體現個案樣貌和諮詢重點的關鍵對話。

逐字稿：
{request.transcript}

會談人數：{request.num_participants} 人

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

        if request.rag_system == "gemini":
            excerpt_response = await gemini_service.chat_completion(excerpt_prompt, temperature=0.3)
        else:
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

        # Build final report
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

        # Generate quality summary (for both versions, to enable comparison)
        from app.utils.report_quality import generate_quality_summary
        quality_summary = generate_quality_summary(report, report_content, theories, use_legacy=request.use_legacy)

        # Format based on output_format
        if request.output_format == "html":
            formatted_report = format_report_as_html(report)
            result = {
                "report": formatted_report,
                "format": "html"
            }
            if quality_summary:
                result["quality_summary"] = quality_summary
            return result
        elif request.output_format == "markdown":
            formatted_report = format_report_as_markdown(report)
            result = {
                "report": formatted_report,
                "format": "markdown"
            }
            if quality_summary:
                result["quality_summary"] = quality_summary
            return result
        else:  # json (default)
            result = {
                "report": report,
                "format": "json"
            }
            if quality_summary:
                result["quality_summary"] = quality_summary
            return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
