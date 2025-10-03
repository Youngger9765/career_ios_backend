"""RAG Evaluation Service with RAGAS and MLflow integration"""

import asyncio
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Optional

import mlflow
from datasets import Dataset
from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
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
        # Get experiment
        experiment = db.query(EvaluationExperiment).filter(
            EvaluationExperiment.id == experiment_id
        ).first()

        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Update status
        experiment.status = "running"
        db.commit()

        try:
            # Start MLflow run
            with mlflow.start_run(
                experiment_id=experiment.mlflow_experiment_id,
                run_name=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            ) as run:
                experiment.mlflow_run_id = run.info.run_id

                # Log parameters
                if experiment.chunking_method:
                    mlflow.log_param("chunking_method", experiment.chunking_method)
                if experiment.chunk_size:
                    mlflow.log_param("chunk_size", experiment.chunk_size)
                if experiment.chunk_overlap:
                    mlflow.log_param("chunk_overlap", experiment.chunk_overlap)

                mlflow.log_param("total_queries", len(test_cases))

                # Prepare dataset for RAGAS
                questions = []
                answers = []
                contexts = []
                ground_truths = []

                for case in test_cases:
                    questions.append(case["question"])
                    answers.append(case["answer"])
                    contexts.append(case["contexts"])
                    if include_ground_truth and "ground_truth" in case:
                        ground_truths.append(case["ground_truth"])

                dataset_dict = {
                    "question": questions,
                    "answer": answers,
                    "contexts": contexts,
                }

                if include_ground_truth and ground_truths:
                    dataset_dict["ground_truth"] = ground_truths

                dataset = Dataset.from_dict(dataset_dict)

                # Select metrics based on whether we have ground truth
                metrics = [faithfulness, answer_relevancy]
                if include_ground_truth and ground_truths:
                    metrics.extend([context_recall, context_precision])
                else:
                    metrics.append(context_precision)

                # Run RAGAS evaluation in a separate thread to avoid uvloop/nest_asyncio conflict
                start_time = time.time()

                # Create a wrapper function to run evaluate in a thread
                def run_ragas_sync():
                    return evaluate(dataset, metrics=metrics)

                # Execute in thread pool to avoid event loop conflicts
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_ragas_sync)

                evaluation_time = time.time() - start_time

                # Convert to pandas for easier access
                df = result.to_pandas()

                # Calculate aggregated metrics (convert numpy types to Python native types)
                avg_faithfulness = (
                    float(df["faithfulness"].mean()) if "faithfulness" in df.columns else None
                )
                avg_answer_relevancy = (
                    float(df["answer_relevancy"].mean()) if "answer_relevancy" in df.columns else None
                )
                avg_context_recall = (
                    float(df["context_recall"].mean())
                    if "context_recall" in df.columns
                    else None
                )
                avg_context_precision = (
                    float(df["context_precision"].mean())
                    if "context_precision" in df.columns
                    else None
                )

                # Update experiment with aggregated results (ensure Python native types)
                experiment.total_queries = len(test_cases)
                experiment.avg_faithfulness = float(avg_faithfulness) if avg_faithfulness is not None else None
                experiment.avg_answer_relevancy = float(avg_answer_relevancy) if avg_answer_relevancy is not None else None
                experiment.avg_context_recall = float(avg_context_recall) if avg_context_recall is not None else None
                experiment.avg_context_precision = float(avg_context_precision) if avg_context_precision is not None else None
                experiment.avg_latency_ms = float((evaluation_time / len(test_cases)) * 1000)
                experiment.status = "completed"

                # Log metrics to MLflow
                if avg_faithfulness is not None:
                    mlflow.log_metric("avg_faithfulness", avg_faithfulness)
                if avg_answer_relevancy is not None:
                    mlflow.log_metric("avg_answer_relevancy", avg_answer_relevancy)
                if avg_context_recall is not None:
                    mlflow.log_metric("avg_context_recall", avg_context_recall)
                if avg_context_precision is not None:
                    mlflow.log_metric("avg_context_precision", avg_context_precision)
                if experiment.avg_latency_ms is not None:
                    mlflow.log_metric("avg_latency_ms", experiment.avg_latency_ms)

                # Store individual results
                for idx, case in enumerate(test_cases):
                    result_record = EvaluationResult(
                        experiment_id=experiment.id,
                        question=case["question"],
                        answer=case["answer"],
                        contexts=case["contexts"],
                        ground_truth=case.get("ground_truth"),
                        faithfulness=float(df.iloc[idx]["faithfulness"])
                        if "faithfulness" in df.columns
                        else None,
                        answer_relevancy=float(df.iloc[idx]["answer_relevancy"])
                        if "answer_relevancy" in df.columns
                        else None,
                        context_recall=float(df.iloc[idx]["context_recall"])
                        if "context_recall" in df.columns
                        else None,
                        context_precision=float(df.iloc[idx]["context_precision"])
                        if "context_precision" in df.columns
                        else None,
                        latency_ms=case.get("latency_ms"),
                        metadata_json=case.get("metadata"),
                    )
                    db.add(result_record)

                db.commit()
                db.refresh(experiment)

        except Exception as e:
            experiment.status = "failed"
            experiment.error_message = str(e)
            db.commit()
            raise

        return experiment

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
        return db.query(EvaluationExperiment).filter(
            EvaluationExperiment.id == experiment_id
        ).first()

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
            query = query.filter(EvaluationExperiment.experiment_type == experiment_type)
        if status:
            query = query.filter(EvaluationExperiment.status == status)

        return query.order_by(EvaluationExperiment.created_at.desc()).offset(offset).limit(limit).all()

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
        experiments = (
            db.query(EvaluationExperiment)
            .filter(EvaluationExperiment.id.in_(experiment_ids))
            .all()
        )

        comparison = {
            "experiments": [],
            "best_faithfulness": None,
            "best_answer_relevancy": None,
            "best_context_recall": None,
            "best_context_precision": None,
        }

        best_faithfulness_score = 0
        best_answer_relevancy_score = 0
        best_context_recall_score = 0
        best_context_precision_score = 0

        for exp in experiments:
            exp_data = {
                "id": str(exp.id),
                "name": exp.name,
                "chunking_method": exp.chunking_method,
                "chunk_size": exp.chunk_size,
                "chunk_overlap": exp.chunk_overlap,
                "avg_faithfulness": exp.avg_faithfulness,
                "avg_answer_relevancy": exp.avg_answer_relevancy,
                "avg_context_recall": exp.avg_context_recall,
                "avg_context_precision": exp.avg_context_precision,
                "total_queries": exp.total_queries,
            }
            comparison["experiments"].append(exp_data)

            # Track best scores
            if exp.avg_faithfulness and exp.avg_faithfulness > best_faithfulness_score:
                best_faithfulness_score = exp.avg_faithfulness
                comparison["best_faithfulness"] = exp.name

            if (
                exp.avg_answer_relevancy
                and exp.avg_answer_relevancy > best_answer_relevancy_score
            ):
                best_answer_relevancy_score = exp.avg_answer_relevancy
                comparison["best_answer_relevancy"] = exp.name

            if exp.avg_context_recall and exp.avg_context_recall > best_context_recall_score:
                best_context_recall_score = exp.avg_context_recall
                comparison["best_context_recall"] = exp.name

            if (
                exp.avg_context_precision
                and exp.avg_context_precision > best_context_precision_score
            ):
                best_context_precision_score = exp.avg_context_precision
                comparison["best_context_precision"] = exp.name

        return comparison
