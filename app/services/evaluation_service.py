"""RAG Evaluation Service with RAGAS and MLflow integration"""

import uuid
from datetime import datetime
from typing import Any, Optional

import mlflow
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationExperiment, EvaluationResult

# Load environment variables for OpenAI API key
load_dotenv()


class EvaluationService:
    """Service for running RAG evaluations using RAGAS and MLflow"""

    def __init__(self, mlflow_tracking_uri: str = "file:./mlruns"):
        """Initialize evaluation service

        Args:
            mlflow_tracking_uri: MLflow tracking URI (default: file:./mlruns)
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri
        mlflow.set_tracking_uri(mlflow_tracking_uri)

    async def create_experiment(
        self,
        db: Session,
        name: str,
        description: Optional[str] = None,
        experiment_type: str = "end_to_end",
        chunking_method: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        chunk_strategy: Optional[str] = None,  # NEW
        instruction_version: Optional[str] = None,
        instruction_template: Optional[str] = None,
        instruction_hash: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> EvaluationExperiment:
        """Create a new evaluation experiment

        Args:
            db: Database session
            name: Experiment name
            description: Experiment description
            experiment_type: Type of experiment
            chunking_method: Chunking method being tested
            chunk_size: Chunk size parameter
            chunk_overlap: Chunk overlap parameter
            chunk_strategy: Chunk strategy to filter by (e.g., rec_400_80)
            instruction_version: Instruction prompt version (e.g., "v2.0")
            instruction_template: Full instruction prompt template
            instruction_hash: SHA256 hash of instruction template
            config: Additional configuration

        Returns:
            Created experiment
        """
        # Create MLflow experiment
        mlflow_exp_name = f"rag_eval_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mlflow_experiment_id = mlflow.create_experiment(mlflow_exp_name)

        # Create database record
        experiment = EvaluationExperiment(
            name=name,
            description=description,
            experiment_type=experiment_type,
            chunking_method=chunking_method,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_strategy=chunk_strategy,  # NEW
            instruction_version=instruction_version,
            instruction_template=instruction_template,
            instruction_hash=instruction_hash,
            config_json=config,
            status="pending",
            mlflow_experiment_id=str(mlflow_experiment_id),
        )

        db.add(experiment)
        db.commit()
        db.refresh(experiment)

        return experiment

    async def run_evaluation(
        self,
        db: Session,
        experiment_id: uuid.UUID,
        test_cases: list[dict[str, Any]],
        include_ground_truth: bool = False,
    ) -> EvaluationExperiment:
        """Run evaluation on test cases

        Args:
            db: Database session
            experiment_id: Experiment ID
            test_cases: List of test cases with question, answer, contexts, ground_truth (optional)
            include_ground_truth: Whether test cases include ground truth for context recall

        Returns:
            Updated experiment with results
        """
        from app.services.evaluation_helpers import (
            calculate_aggregated_metrics,
            generate_rag_answers,
            get_document_ids_for_strategy,
            run_ragas_evaluation,
        )
        from app.services.openai_service import OpenAIService

        # Get experiment
        experiment = (
            db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.id == experiment_id)
            .first()
        )

        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Update status
        experiment.status = "running"
        db.commit()

        try:
            # Get document IDs for strategy
            document_ids, total_documents = await get_document_ids_for_strategy(
                db, experiment.chunk_strategy
            )

            # Store document snapshot in config_json
            config: dict[str, object] = experiment.config_json or {}
            config.update(
                {
                    "document_ids": document_ids,
                    "total_documents": total_documents,
                    "evaluation_timestamp": datetime.now().isoformat(),
                }
            )
            experiment.config_json = config

            # Generate RAG answers for test cases
            openai_service = OpenAIService()
            await generate_rag_answers(db, test_cases, experiment, openai_service)

            # Start MLflow run
            with mlflow.start_run(
                experiment_id=experiment.mlflow_experiment_id,
                run_name=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            ) as run:
                experiment.mlflow_run_id = run.info.run_id

                # Log parameters to MLflow
                self._log_mlflow_parameters(
                    experiment, len(test_cases), total_documents, document_ids
                )

                # Run RAGAS evaluation
                result, evaluation_time = await run_ragas_evaluation(
                    test_cases, include_ground_truth
                )

                # Convert to pandas and calculate metrics
                df = result.to_pandas()  # type: ignore[attr-defined]
                metrics = calculate_aggregated_metrics(df)

                # Update experiment with results
                experiment.total_queries = len(test_cases)
                experiment.avg_faithfulness = metrics["avg_faithfulness"]
                experiment.avg_answer_relevancy = metrics["avg_answer_relevancy"]
                experiment.avg_context_recall = metrics["avg_context_recall"]
                experiment.avg_context_precision = metrics["avg_context_precision"]
                experiment.avg_latency_ms = float(
                    (evaluation_time / len(test_cases)) * 1000
                )
                experiment.status = "completed"

                # Log metrics to MLflow
                self._log_mlflow_metrics(experiment)

                # Store individual results
                self._store_individual_results(db, experiment, test_cases, df)

                db.commit()
                db.refresh(experiment)

        except Exception as e:
            experiment.status = "failed"
            experiment.error_message = str(e)
            db.commit()
            if mlflow.active_run():
                mlflow.end_run()
            raise

        return experiment

    def _log_mlflow_parameters(
        self,
        experiment: EvaluationExperiment,
        total_queries: int,
        total_documents: int,
        document_ids: list[int],
    ) -> None:
        """Log experiment parameters to MLflow

        Args:
            experiment: Evaluation experiment
            total_queries: Total number of queries
            total_documents: Total number of documents
            document_ids: List of document IDs
        """
        if experiment.chunking_method:
            mlflow.log_param("chunking_method", experiment.chunking_method)
        if experiment.chunk_size:
            mlflow.log_param("chunk_size", experiment.chunk_size)
        if experiment.chunk_overlap:
            mlflow.log_param("chunk_overlap", experiment.chunk_overlap)
        if experiment.chunk_strategy:
            mlflow.log_param("chunk_strategy", experiment.chunk_strategy)
        if experiment.instruction_version:
            mlflow.log_param("instruction_version", experiment.instruction_version)
        if experiment.instruction_hash:
            mlflow.log_param("instruction_hash", experiment.instruction_hash)

        mlflow.log_param("total_queries", total_queries)
        mlflow.log_param("total_documents", total_documents)
        mlflow.log_param("document_ids", str(document_ids))

    def _log_mlflow_metrics(self, experiment: EvaluationExperiment) -> None:
        """Log experiment metrics to MLflow

        Args:
            experiment: Evaluation experiment with calculated metrics
        """
        if experiment.avg_faithfulness is not None:
            mlflow.log_metric("avg_faithfulness", experiment.avg_faithfulness)
        if experiment.avg_answer_relevancy is not None:
            mlflow.log_metric("avg_answer_relevancy", experiment.avg_answer_relevancy)
        if experiment.avg_context_recall is not None:
            mlflow.log_metric("avg_context_recall", experiment.avg_context_recall)
        if experiment.avg_context_precision is not None:
            mlflow.log_metric("avg_context_precision", experiment.avg_context_precision)
        if experiment.avg_latency_ms is not None:
            mlflow.log_metric("avg_latency_ms", experiment.avg_latency_ms)

    def _store_individual_results(
        self,
        db: Session,
        experiment: EvaluationExperiment,
        test_cases: list[dict[str, Any]],
        df,
    ) -> None:
        """Store individual evaluation results in database

        Args:
            db: Database session
            experiment: Evaluation experiment
            test_cases: List of test cases
            df: RAGAS results DataFrame
        """
        from app.services.evaluation_helpers import safe_metric

        for idx, case in enumerate(test_cases):
            result_record = EvaluationResult(
                experiment_id=experiment.id,
                question=case["question"],
                answer=case["answer"],
                contexts=case["contexts"],
                ground_truth=case.get("ground_truth"),
                faithfulness=safe_metric(df.iloc[idx]["faithfulness"])
                if "faithfulness" in df.columns
                else None,
                answer_relevancy=safe_metric(df.iloc[idx]["answer_relevancy"])
                if "answer_relevancy" in df.columns
                else None,
                context_recall=safe_metric(df.iloc[idx]["context_recall"])
                if "context_recall" in df.columns
                else None,
                context_precision=safe_metric(df.iloc[idx]["context_precision"])
                if "context_precision" in df.columns
                else None,
                latency_ms=case.get("latency_ms"),
                metadata_json=case.get("metadata"),
            )
            db.add(result_record)

    async def get_experiment(
        self, db: Session, experiment_id: uuid.UUID
    ) -> Optional[EvaluationExperiment]:
        """Get experiment by ID

        Args:
            db: Database session
            experiment_id: Experiment ID

        Returns:
            Experiment or None
        """
        return (
            db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.id == experiment_id)
            .first()
        )

    async def list_experiments(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        experiment_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[EvaluationExperiment]:
        """List experiments with filters

        Args:
            db: Database session
            limit: Maximum number of results
            offset: Offset for pagination
            experiment_type: Filter by experiment type
            status: Filter by status

        Returns:
            List of experiments
        """
        query = db.query(EvaluationExperiment)

        if experiment_type:
            query = query.filter(
                EvaluationExperiment.experiment_type == experiment_type
            )
        if status:
            query = query.filter(EvaluationExperiment.status == status)

        return (
            query.order_by(EvaluationExperiment.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    async def get_experiment_results(
        self,
        db: Session,
        experiment_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EvaluationResult]:
        """Get detailed results for an experiment

        Args:
            db: Database session
            experiment_id: Experiment ID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of evaluation results
        """
        return (
            db.query(EvaluationResult)
            .filter(EvaluationResult.experiment_id == experiment_id)
            .order_by(EvaluationResult.created_at)
            .offset(offset)
            .limit(limit)
            .all()
        )

    async def compare_experiments(
        self, db: Session, experiment_ids: list[uuid.UUID]
    ) -> dict[str, Any]:
        """Compare multiple experiments

        Args:
            db: Database session
            experiment_ids: List of experiment IDs to compare

        Returns:
            Comparison data
        """
        from app.services.evaluation_helpers import compare_experiment_metrics

        experiments = (
            db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.id.in_(experiment_ids))
            .all()
        )

        return compare_experiment_metrics(experiments)
