"""Database models for RAG evaluation system"""

from sqlalchemy import Column, Float, Integer, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class EvaluationExperiment(Base, BaseModel):
    """Evaluation experiment run"""

    __tablename__ = "evaluation_experiments"

    # Experiment metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    experiment_type = Column(
        String(50), nullable=False, default="chunking"
    )  # chunking, retrieval, generation, end_to_end

    # Configuration
    chunking_method = Column(String(50), nullable=True)  # fixed, recursive, semantic, etc.
    chunk_size = Column(Integer, nullable=True)
    chunk_overlap = Column(Integer, nullable=True)
    chunk_strategy = Column(String(100), nullable=True)  # NEW: strategy filter for evaluation
    config_json = Column(JSON, nullable=True)  # Additional config parameters

    # Instruction Prompt Versioning
    instruction_version = Column(String(50), nullable=True)  # e.g., "v2.0", "v2.1"
    instruction_template = Column(Text, nullable=True)  # Full prompt template
    instruction_hash = Column(String(64), nullable=True)  # SHA256 hash for quick comparison

    # Status
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)

    # MLflow tracking
    mlflow_run_id = Column(String(255), nullable=True)
    mlflow_experiment_id = Column(String(255), nullable=True)

    # Results (aggregated)
    total_queries = Column(Integer, nullable=True, default=0)
    avg_faithfulness = Column(Float, nullable=True)
    avg_answer_relevancy = Column(Float, nullable=True)
    avg_context_recall = Column(Float, nullable=True)
    avg_context_precision = Column(Float, nullable=True)
    avg_latency_ms = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)

    # Relationships
    results = relationship(
        "EvaluationResult", back_populates="experiment", cascade="all, delete-orphan"
    )


class EvaluationResult(Base, BaseModel):
    """Individual evaluation result for a single query"""

    __tablename__ = "evaluation_results"

    experiment_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_experiments.id"), nullable=False)

    # Query details
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    contexts = Column(JSON, nullable=False)  # List of retrieved context strings
    ground_truth = Column(Text, nullable=True)  # Optional ground truth answer

    # RAGAS metrics
    faithfulness = Column(Float, nullable=True)
    answer_relevancy = Column(Float, nullable=True)
    context_recall = Column(Float, nullable=True)
    context_precision = Column(Float, nullable=True)

    # Performance metrics
    latency_ms = Column(Float, nullable=True)
    retrieval_latency_ms = Column(Float, nullable=True)
    generation_latency_ms = Column(Float, nullable=True)

    # Cost metrics
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)

    # Additional metadata
    metadata_json = Column(JSON, nullable=True)

    # Relationship
    experiment = relationship("EvaluationExperiment", back_populates="results")


class EvaluationTestSet(Base, BaseModel):
    """Pre-defined test sets for evaluation"""

    __tablename__ = "evaluation_testsets"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Test cases stored as JSON
    # Format: [{"question": "...", "ground_truth": "...", "contexts": [...]}, ...]
    test_cases = Column(JSON, nullable=False)

    # Metadata
    total_cases = Column(Integer, nullable=False, default=0)
    category = Column(String(100), nullable=True)  # e.g., "career_counseling", "interview_prep"


class DocumentQualityMetric(Base, BaseModel):
    """Track document quality metrics over time"""

    __tablename__ = "document_quality_metrics"

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    # Document quality dimensions
    content_accuracy = Column(Float, nullable=True)  # 0-1
    structural_score = Column(Float, nullable=True)  # 0-1
    expertise_depth = Column(Float, nullable=True)  # 0-1
    readability_score = Column(Float, nullable=True)  # 0-100

    # Coverage metrics
    topic_coverage = Column(JSON, nullable=True)
    knowledge_depth = Column(JSON, nullable=True)

    # Metadata
    evaluated_by = Column(String(100), nullable=True)  # human, ai, hybrid
    evaluation_notes = Column(Text, nullable=True)
