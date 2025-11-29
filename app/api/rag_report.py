"""API endpoints for case report generation"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.openai_service import OpenAIService
from app.services.rag_report_service import RAGReportService

router = APIRouter(prefix="/api/report", tags=["report"])


def format_report_as_html(report: dict) -> str:
    """Convert report to HTML format (refactored to use formatter)"""
    from app.utils.report_formatters import HTMLReportFormatter

    formatter = HTMLReportFormatter()
    return formatter.format(report)


def format_report_as_markdown(report: dict) -> str:
    """Convert report to Markdown format (refactored to use formatter)"""
    from app.utils.report_formatters import MarkdownReportFormatter

    formatter = MarkdownReportFormatter()
    return formatter.format(report)


class ReportRequest(BaseModel):
    transcript: str
    num_participants: int = 2
    rag_system: str = "gemini"  # "openai" or "gemini" - 預設使用 Gemini
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
        service = RAGReportService(openai_service, db, request.rag_system)

        # Handle comparison mode: generate both versions
        if request.mode == "comparison":
            legacy_request = ReportRequest(
                transcript=request.transcript,
                num_participants=request.num_participants,
                rag_system=request.rag_system,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                output_format="json",
                mode="legacy",
            )
            legacy_result = await generate_report(legacy_request, db)

            enhanced_request = ReportRequest(
                transcript=request.transcript,
                num_participants=request.num_participants,
                rag_system=request.rag_system,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                output_format="json",
                mode="enhanced",
            )
            enhanced_result = await generate_report(enhanced_request, db)

            return {
                "mode": "comparison",
                "legacy": legacy_result,
                "enhanced": enhanced_result,
                "format": "json",
            }

        # Parse transcript
        parsed_data = await service.parse_transcript(request.transcript)

        # Search for relevant theories
        theories = await service.search_theories(
            main_concerns=parsed_data.get("main_concerns", []),
            techniques=parsed_data.get("counselor_techniques", []),
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        # Build prompt components
        rag_instruction = service.build_rag_instruction(len(theories))
        context = service.build_theory_context(theories)

        # Generate report content
        use_legacy = request.mode == "legacy"
        if use_legacy:
            prompt = service.build_legacy_prompt(parsed_data, context, rag_instruction)
        else:
            prompt = service.build_enhanced_prompt(
                parsed_data, context, rag_instruction
            )

        report_content = await service.generate_report_content(prompt)

        # Extract dialogue excerpts
        dialogues = await service.extract_dialogues(
            request.transcript, request.num_participants
        )

        # Build final report
        report = service.build_report_dict(
            parsed_data, report_content, theories, dialogues
        )

        # Generate quality summary
        quality_summary = await service.generate_quality_summary(
            report, report_content, use_legacy
        )

        # Format based on output_format
        if request.output_format == "html":
            formatted_report = format_report_as_html(report)
            html_result: dict[str, object] = {
                "mode": request.mode,
                "report": formatted_report,
                "format": "html",
            }
            if quality_summary:
                html_result["quality_summary"] = quality_summary
            return html_result
        elif request.output_format == "markdown":
            formatted_report = format_report_as_markdown(report)
            md_result: dict[str, object] = {
                "mode": request.mode,
                "report": formatted_report,
                "format": "markdown",
            }
            if quality_summary:
                md_result["quality_summary"] = quality_summary
            return md_result
        else:  # json (default)
            json_result: dict[str, object] = {
                "mode": request.mode,
                "report": report,
                "format": "json",
            }
            if quality_summary:
                json_result["quality_summary"] = quality_summary
            return json_result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report: {str(e)}"
        )
