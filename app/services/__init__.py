# Services module - backward compatible re-exports
# All imports from app.services.<module> continue to work
# fmt: off
# ruff: noqa: I001
# isort: skip_file

# Import submodules for backward compatibility with patch targets like
# "app.services.keyword_analysis_service" - this makes the submodules
# accessible as attributes of app.services
from app.services.analysis import keyword_analysis_service  # noqa: F401
from app.services.core import quick_feedback_service as quick_feedback_service_module  # noqa: F401
from app.services.core import session_service  # noqa: F401
from app.services.external import email_sender as email_sender_module  # noqa: F401
from app.services.external import gbq_service as gbq_service_module  # noqa: F401
from app.services.external import gemini_service as gemini_service_module  # noqa: F401
from app.services.rag import rag_retriever  # noqa: F401
from app.services.reporting import report_service as report_service_module  # noqa: F401

# Clients
from app.services.clients.client_service import ClientService
from app.services.clients.case_service import CaseService
from app.services.clients.client_case_service import ClientCaseService

# Evaluation
from app.services.evaluation.evaluation_service import EvaluationService
from app.services.evaluation.evaluation_prompts_service import EvaluationPromptsService
from app.services.evaluation.evaluation_recommendations_service import (
    EvaluationRecommendationsService,
)

# Reporting
from app.services.reporting.report_service import ReportGenerationService, report_service
from app.services.reporting.report_operations_service import ReportOperationsService
from app.services.reporting.rag_report_service import RAGReportService

# RAG
from app.services.rag.rag_chat_service import Citation, IntentResult, RAGChatService
from app.services.rag.rag_retriever import RAGRetriever
from app.services.rag.rag_ingest_service import RAGIngestService
from app.services.rag.chunking import ChunkingService
from app.services.rag.pdf_service import PDFService

# External
from app.services.external.gemini_service import GeminiService, gemini_service
from app.services.external.openai_service import OpenAIService
from app.services.external.gbq_service import GBQService, gbq_service
from app.services.external.email_sender import EmailSenderService, email_sender
from app.services.external.storage import StorageService

# Core
from app.services.core.session_service import SessionService
from app.services.core.recording_service import RecordingService
from app.services.core.reflection_service import ReflectionService
from app.services.core.timeline_service import TimelineService
from app.services.core.credit_billing import CreditBillingService
from app.services.core.billing_analyzer import BillingAnalyzerService, billing_analyzer
from app.services.core.session_summary_service import (
    SessionSummaryService,
    session_summary_service,
)
from app.services.core.encouragement_service import (
    EncouragementService,
    encouragement_service,
)
from app.services.core.quick_feedback_service import (
    QuickFeedbackService,
    quick_feedback_service,
)
from app.services.core.scenario_generator_service import (
    ScenarioGeneratorService,
    scenario_generator_service,
)

# Analysis
from app.services.analysis.analysis_log_service import AnalysisLogService
from app.services.analysis.keyword_analysis_service import KeywordAnalysisService
from app.services.analysis.transcript_parser import TranscriptParser
from app.services.analysis.dialogue_extractor import DialogueExtractor
from app.services.analysis.sanitizer_service import SanitizerService, sanitizer_service
# fmt: on

__all__ = [
    # Clients
    "ClientService",
    "CaseService",
    "ClientCaseService",
    # Evaluation
    "EvaluationService",
    "EvaluationPromptsService",
    "EvaluationRecommendationsService",
    # Reporting
    "ReportGenerationService",
    "report_service",
    "ReportOperationsService",
    "RAGReportService",
    # RAG
    "Citation",
    "IntentResult",
    "RAGChatService",
    "RAGRetriever",
    "RAGIngestService",
    "ChunkingService",
    "PDFService",
    # External
    "GeminiService",
    "gemini_service",
    "OpenAIService",
    "GBQService",
    "gbq_service",
    "EmailSenderService",
    "email_sender",
    "StorageService",
    # Core
    "SessionService",
    "RecordingService",
    "ReflectionService",
    "TimelineService",
    "CreditBillingService",
    "BillingAnalyzerService",
    "billing_analyzer",
    "SessionSummaryService",
    "session_summary_service",
    "EncouragementService",
    "encouragement_service",
    "QuickFeedbackService",
    "quick_feedback_service",
    "ScenarioGeneratorService",
    "scenario_generator_service",
    # Analysis
    "AnalysisLogService",
    "KeywordAnalysisService",
    "TranscriptParser",
    "DialogueExtractor",
    "SanitizerService",
    "sanitizer_service",
]
