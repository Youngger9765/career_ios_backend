"""API endpoints for case report generation"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.gemini_service import gemini_service
from app.services.openai_service import OpenAIService
from app.services.transcript_parser import TranscriptParser
from app.services.rag_retriever import RAGRetriever
from app.services.dialogue_extractor import DialogueExtractor


# Report schemas for structured output
class EnhancedReportSchema(BaseModel):
    """10段式增強報告結構"""
    section_2_main_issue: str = Field(description="二、主訴問題 - 個案陳述與諮詢師觀察")
    section_3_development: str = Field(description="三、問題發展脈絡 - 出現時間、持續頻率、影響程度")
    section_4_help_seeking: str = Field(description="四、求助動機與期待 - 引發因素、期待目標")
    section_5_multilevel_analysis: str = Field(description="五、多層次因素分析 - 個人、人際、環境、發展因素（必須引用理論[1][2]）")
    section_6_strengths: str = Field(description="六、個案優勢與資源 - 心理優勢、社會資源")
    section_7_professional_judgment: str = Field(description="七、諮詢師的專業判斷 - 問題假設、理論依據（必須引用理論[3][4]）")
    section_8_goals_strategies: str = Field(description="八、諮商目標與介入策略 - SMART目標、介入技術（必須引用理論[5][6]）")
    section_9_expected_outcomes: str = Field(description="九、預期成效與評估 - 短期指標、長期指標、可能調整")
    section_10_self_reflection: str = Field(description="十、諮詢師自我反思 - 本次晤談優點和可改進處")


class LegacyReportSchema(BaseModel):
    """5段式舊版報告結構"""
    main_issue: str = Field(description="主訴問題 - 個案說的，此次想要討論的議題")
    cause_analysis: str = Field(description="成因分析 - 諮詢師認為個案為何會有這些主訴問題，結合引用的理論[1][2]分析")
    counseling_goal: str = Field(description="晤談目標（移動主訴）- 諮詢師對個案諮詢目標的假設")
    intervention: str = Field(description="介入策略 - 諮詢師判斷會需要帶個案做的事，結合理論說明")
    effectiveness: str = Field(description="目前成效評估 - 上述目標和策略達成的狀況")

router = APIRouter(prefix="/api/report", tags=["report"])


def format_report_as_html(report: dict) -> str:
    """Convert report to HTML format"""
    html = "<html><body>"
    html += "<h1>個案報告</h1>"

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
    mode: str = "enhanced"  # "legacy", "enhanced", or "comparison"


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

        # Step 1: Parse transcript using TranscriptParser service
        parser = TranscriptParser(openai_service)
        parsed_result = await parser.parse(request.transcript)

        # Extract data from standardized format
        parsed_data = {
            "client_name": parsed_result["client_info"]["name"],
            "gender": parsed_result["client_info"]["gender"],
            "age": parsed_result["client_info"]["age"],
            "occupation": parsed_result["client_info"]["occupation"],
            "education": parsed_result["client_info"]["education"],
            "location": parsed_result["client_info"]["location"],
            "economic_status": parsed_result["client_info"]["economic_status"],
            "family_relations": parsed_result["client_info"]["family_relations"],
            "other_info": parsed_result["client_info"]["other_info"],
            "main_concerns": parsed_result["main_concerns"],
            "counseling_goals": parsed_result["counseling_goals"],
            "counselor_techniques": parsed_result["counselor_techniques"],
            "session_content": parsed_result["session_content"],
            "counselor_self_evaluation": parsed_result["counselor_self_evaluation"],
        }

        # Step 2: RAG search for relevant theories using RAGRetriever service
        main_concerns = parsed_data.get("main_concerns", [])
        techniques = parsed_data.get("counselor_techniques", [])
        search_terms = main_concerns[:3] + techniques[:2]
        search_query = " ".join(search_terms) if search_terms else "職涯諮詢 生涯發展"

        retriever = RAGRetriever(openai_service)
        theories = await retriever.search(
            query=search_query,
            top_k=request.top_k,
            threshold=request.similarity_threshold,
            db=db
        )

        # Step 3: Generate structured report with enhanced context format
        context_parts = []
        for i, theory in enumerate(theories):
            doc_title = theory.get('document', '未知文獻')
            theory_text = theory['text']
            score = theory['score']

            context_parts.append(
                f"[{i+1}] **來源文獻：{doc_title}**\n"
                f"   相似度分數：{score:.2f}\n"
                f"   內容：{theory_text}"
            )

        context = "\n\n".join(context_parts)

        # Add explicit RAG instruction
        rag_instruction = f"""
⚠️⚠️⚠️ 重要：理論引用規則 ⚠️⚠️⚠️

你【必須】使用以下 RAG 檢索到的 {len(theories)} 個理論文獻，【不可】使用你自己記憶中的理論！

引用時：
1. 必須從 [1] 到 [{len(theories)}] 中選擇
2. 必須提取文獻來源或內容中的理論名稱（例如：Super 生涯發展理論、Holland 類型論、認知行為理論）
3. 引用格式：「根據 [理論名稱] [數字]，...」
4. 如果文獻中沒有明確理論名稱，則引用「來源文獻名稱 [數字]」

範例：
✅ 正確：「根據 Super 生涯發展理論 [1]，案主處於探索期...」（如果 [1] 的內容或來源提到 Super）
✅ 正確：「依據職涯諮詢精選文章 [3]，...」（如果不知道具體理論名稱，用文獻名）
❌ 錯誤：引用 RAG 未提供的理論（例如 Freud、Maslow 等，如果它們不在下列文獻中）
❌ 錯誤：「根據理論 [1]」（沒有說明理論名稱）
"""

        # Determine use_legacy flag based on mode
        use_legacy = (request.mode == "legacy")

        # Choose prompt based on use_legacy flag
        if use_legacy:
            # Legacy version: Enhanced 5-section prompt with content requirements
            report_prompt = f"""{rag_instruction}

你是一位專業的職涯諮詢督導。請根據以下資訊生成個案報告：

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
1. ⚠️ 每個段落必須有實質內容，每段至少寫5-8句完整的段落文字，絕對不可只寫「-」、「無」、「待評估」或留空
2. 每個段落都要深入分析，提供具體的觀察、推論和建議
3. 請使用專業、客觀、具同理心的語氣
4. 適當引用理論文獻 [1], [2] 等
5. 不要使用 markdown 格式（如 ##, ###, **, - 等符號）
6. 使用【標題】的格式來區分段落
7. 內容直接書寫成段落，不要用項目符號或短句
"""
        else:
            # Enhanced version: Structured 10-section prompt with validation
            report_prompt = f"""{rag_instruction}

你是職涯諮詢督導，協助新手諮詢師撰寫個案概念化報告。

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

⚠️ 重要：請嚴格按照以下結構生成個案報告，段落【二】到【十】都必須完整包含！

【一、案主基本資料】
根據逐字稿提取的資訊整理如下（若逐字稿未提及則省略該項）：
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
{f"- 性別：{parsed_data.get('gender')}" if parsed_data.get('gender') != '未提及' else ""}
{f"- 年齡：{parsed_data.get('age')}" if parsed_data.get('age') != '未提及' else ""}
{f"- 部門/職業：{parsed_data.get('occupation')}" if parsed_data.get('occupation') != '未提及' else ""}
{f"- 學歷：{parsed_data.get('education')}" if parsed_data.get('education') != '未提及' else ""}
{f"- 現居地：{parsed_data.get('location')}" if parsed_data.get('location') != '未提及' else ""}
{f"- 經濟狀況：{parsed_data.get('economic_status')}" if parsed_data.get('economic_status') != '未提及' else ""}
{f"- 家庭關係：{parsed_data.get('family_relations')}" if parsed_data.get('family_relations') != '未提及' else ""}

註：本段僅呈現逐字稿中提及的資訊。若資訊不完整，不影響後續專業分析的品質。

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

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「根據 Super 生涯發展理論 [1]，案主處於探索期...」
✅ 正確：「從社會認知職業理論 (SCCT) [2] 的觀點來看...」
❌ 錯誤：「根據理論 [1]」（缺少理論名稱）
❌ 錯誤：「根據文獻」（沒有數字引用）

【六、個案優勢與資源】
- 心理優勢：（情緒調適、動機）
- 社會資源：（支持系統）

【七、諮詢師的專業判斷】⭐ 核心段落（必須引用理論 [3][4]）
- 問題假設：（為何有這些困擾）
- 理論依據：（用什麼理論支持判斷）引用 [3][4]
- 理論取向：（採用的觀點）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「基於認知行為理論 [3]，我認為問題源於...」
✅ 正確：「從 Holland 類型論 [4] 的角度來看...」
❌ 錯誤：「根據理論 [3]」（缺少理論名稱）

【八、諮商目標與介入策略】⭐ 核心段落（必須引用 [5][6]）
- 諮商目標：（SMART 格式，具體可衡量）
- 介入技術：（使用的方法）引用 [5][6]
- 技術理由：（為何這技術適合此個案）
- 介入步驟：（執行順序）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「選擇敘事治療技術 [5]，因為此方法能幫助案主重新建構生涯故事...」
✅ 正確：「根據焦點解決短期治療 (SFBT) [6]，設定具體可達成的目標...」
❌ 錯誤：「理論 [5] 指出...」（缺少理論名稱）

【九、預期成效與評估】
- 短期指標：（3 個月內如何判斷進步）
- 長期指標：（6-12 個月目標）
- 可能調整：（什麼情況需改變策略）

【十、諮詢師自我反思】
{parsed_data.get('counselor_self_evaluation', '請反思本次晤談優點和可改進處')}

格式要求：
1. 必須包含上述所有段落，用【】標題
2. 第五、七、八段落必須引用理論，格式為「理論名稱 [數字]」
3. 每個引用必須完整說明理論名稱，例如「Super 生涯發展理論 [1]」而非「理論 [1]」
4. 引用時要說明為何此理論適用於個案
5. 不用 markdown（##, **, -）
6. 每段至少 3-5 句，內容充實且具體
7. 必須考慮多層次因素：生理、心理、社會、文化
"""

            # M2.2: Add rationale examples to prompt (only for enhanced version)
            from app.utils.prompt_enhancer import add_rationale_examples
            report_prompt = add_rationale_examples(report_prompt)

        if request.rag_system == "gemini":
            report_content = await gemini_service.chat_completion(report_prompt, temperature=0.6)
        else:
            report_content = await openai_service.chat_completion(
                messages=[{"role": "user", "content": report_prompt}],
                temperature=0.6,
                max_tokens=8000  # Maximum tokens for comprehensive report generation
            )

        # Step 4: Extract key dialogue excerpts using DialogueExtractor service
        extractor = DialogueExtractor(openai_service if request.rag_system != "gemini" else gemini_service)
        dialogues = await extractor.extract(request.transcript, request.num_participants)

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

        # Handle comparison mode: generate both versions
        if request.mode == "comparison":
            # Generate legacy version
            legacy_request = ReportRequest(
                transcript=request.transcript,
                num_participants=request.num_participants,
                rag_system=request.rag_system,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                output_format="json",
                mode="legacy"
            )
            legacy_result = await generate_report(legacy_request, db)

            # Generate enhanced version
            enhanced_request = ReportRequest(
                transcript=request.transcript,
                num_participants=request.num_participants,
                rag_system=request.rag_system,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                output_format="json",
                mode="enhanced"
            )
            enhanced_result = await generate_report(enhanced_request, db)

            return {
                "mode": "comparison",
                "legacy": legacy_result,
                "enhanced": enhanced_result,
                "format": "json"
            }

        # Generate quality summary using LLM (for more accurate grading)
        from app.utils.report_quality import generate_quality_summary_with_llm
        quality_summary = await generate_quality_summary_with_llm(
            report=report,
            report_text=report_content,
            theories=theories,
            use_legacy=use_legacy,
            openai_client=openai_service.client
        )

        # Format based on output_format
        if request.output_format == "html":
            formatted_report = format_report_as_html(report)
            result = {
                "mode": request.mode,
                "report": formatted_report,
                "format": "html"
            }
            if quality_summary:
                result["quality_summary"] = quality_summary
            return result
        elif request.output_format == "markdown":
            formatted_report = format_report_as_markdown(report)
            result = {
                "mode": request.mode,
                "report": formatted_report,
                "format": "markdown"
            }
            if quality_summary:
                result["quality_summary"] = quality_summary
            return result
        else:  # json (default)
            result = {
                "mode": request.mode,
                "report": report,
                "format": "json"
            }
            if quality_summary:
                result["quality_summary"] = quality_summary
            return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
