"""Helper functions for RAG evaluation service"""

import asyncio
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from sqlalchemy import String, bindparam, text
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationExperiment
from app.services.external.openai_service import OpenAIService


def safe_metric(value) -> Optional[float]:
    """Convert metric to float, return None if NaN

    Args:
        value: Metric value to convert

    Returns:
        Float value or None if NaN
    """
    if value is None:
        return None
    f = float(value)
    return None if math.isnan(f) else f


async def get_document_ids_for_strategy(
    db: Session, chunk_strategy: Optional[str]
) -> Tuple[List[int], int]:
    """Get document IDs that have chunks with specified strategy

    Args:
        db: Database session
        chunk_strategy: Chunk strategy to filter by (None for all)

    Returns:
        Tuple of (document_ids, total_documents)
    """
    if chunk_strategy:
        result = db.execute(
            text(
                """
                SELECT DISTINCT doc_id
                FROM chunks
                WHERE chunk_strategy = :strategy
                ORDER BY doc_id
            """
            ),
            {"strategy": chunk_strategy},
        )
    else:
        result = db.execute(text("SELECT DISTINCT doc_id FROM chunks ORDER BY doc_id"))

    document_ids = [row.doc_id for row in result]
    return document_ids, len(document_ids)


async def search_similar_chunks(
    db: Session,
    question: str,
    chunk_strategy: Optional[str],
    openai_service: OpenAIService,
) -> List[str]:
    """Search for similar chunks using vector similarity

    Args:
        db: Database session
        question: Question to search for
        chunk_strategy: Optional chunk strategy filter
        openai_service: OpenAI service for embeddings

    Returns:
        List of chunk text strings
    """
    # Generate embedding for question
    question_embedding = await openai_service.create_embedding(question)
    embedding_str = "[" + ",".join(map(str, question_embedding)) + "]"

    # Build SQL query
    if chunk_strategy:
        query = text(
            """
            SELECT
                c.id as chunk_id,
                c.doc_id,
                d.title AS document_title,
                c.text,
                1 - (e.embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM chunks c
            JOIN embeddings e ON c.id = e.chunk_id
            JOIN documents d ON c.doc_id = d.id
            WHERE c.chunk_strategy = :chunk_strategy
            ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
            LIMIT 7
        """
        ).bindparams(
            bindparam("query_embedding", type_=String),
            bindparam("chunk_strategy", type_=String),
        )
        result = db.execute(
            query,
            {"query_embedding": embedding_str, "chunk_strategy": chunk_strategy},
        )
    else:
        query = text(
            """
            SELECT
                c.id as chunk_id,
                c.doc_id,
                d.title AS document_title,
                c.text,
                1 - (e.embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM chunks c
            JOIN embeddings e ON c.id = e.chunk_id
            JOIN documents d ON c.doc_id = d.id
            ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
            LIMIT 7
        """
        ).bindparams(bindparam("query_embedding", type_=String))
        result = db.execute(query, {"query_embedding": embedding_str})

    chunks = result.fetchall()
    return [chunk.text for chunk in chunks]


async def generate_rag_answers(
    db: Session,
    test_cases: List[Dict[str, Any]],
    experiment: EvaluationExperiment,
    openai_service: OpenAIService,
) -> None:
    """Generate RAG answers for test cases that don't have answers

    Args:
        db: Database session
        test_cases: List of test case dictionaries (modified in place)
        experiment: Evaluation experiment
        openai_service: OpenAI service for embeddings and completions
    """
    for case in test_cases:
        # Skip if answer already provided
        if case.get("answer"):
            continue

        question = case["question"]

        # Search for similar chunks
        contexts = await search_similar_chunks(
            db, question, experiment.chunk_strategy, openai_service
        )
        case["contexts"] = contexts

        # Generate answer using OpenAI with retrieved contexts
        system_prompt = (
            experiment.instruction_template
            or """你是一位專業的職涯諮詢師，根據提供的文件內容回答問題。

請遵循以下原則：
1. 僅使用提供的文件內容回答
2. 如果文件中沒有相關資訊，請誠實說明
3. 保持專業、友善的語氣
4. 提供具體、可操作的建議"""
        )

        context_text = "\n\n".join(
            [f"[文件 {i+1}]\n{chunk}" for i, chunk in enumerate(contexts)]
        )

        answer = await openai_service.chat_completion(
            messages=[
                {"role": "system", "content": str(system_prompt)},
                {
                    "role": "user",
                    "content": f"參考文件：\n{context_text}\n\n問題：{question}",
                },  # type: ignore[dict-item]
            ],
            temperature=0.7,
        )

        case["answer"] = answer


async def run_ragas_evaluation(
    test_cases: List[Dict[str, Any]], include_ground_truth: bool
) -> Tuple[Any, float]:
    """Run RAGAS evaluation on test cases dataset

    Args:
        test_cases: List of test cases with question, answer, contexts, ground_truth
        include_ground_truth: Whether to include ground truth metrics

    Returns:
        Tuple of (ragas_result, evaluation_time_seconds)
    """
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

    # Configure RAGAS to use gpt-4o-mini
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # type: ignore[call-arg]
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # Select metrics based on whether we have ground truth
    metrics = [faithfulness, answer_relevancy]
    if include_ground_truth and ground_truths:
        metrics.extend([context_recall, context_precision])

    # Run RAGAS evaluation in a separate thread
    start_time = time.time()

    def run_ragas_sync():
        return evaluate(dataset, metrics=metrics, llm=llm, embeddings=embeddings)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_ragas_sync)

    evaluation_time = time.time() - start_time

    return result, evaluation_time


def calculate_aggregated_metrics(df) -> Dict[str, Optional[float]]:
    """Calculate aggregated metrics from RAGAS results DataFrame

    Args:
        df: RAGAS results pandas DataFrame

    Returns:
        Dictionary with avg_faithfulness, avg_answer_relevancy, etc.
    """
    return {
        "avg_faithfulness": safe_metric(df["faithfulness"].mean())
        if "faithfulness" in df.columns
        else None,
        "avg_answer_relevancy": safe_metric(df["answer_relevancy"].mean())
        if "answer_relevancy" in df.columns
        else None,
        "avg_context_recall": safe_metric(df["context_recall"].mean())
        if "context_recall" in df.columns
        else None,
        "avg_context_precision": safe_metric(df["context_precision"].mean())
        if "context_precision" in df.columns
        else None,
    }


def compare_experiment_metrics(experiments: List[Any]) -> Dict[str, Any]:
    """Compare multiple evaluation experiments

    Args:
        experiments: List of EvaluationExperiment objects

    Returns:
        Comparison dictionary with best performers
    """
    comparison: dict[str, object] = {
        "experiments": [],
        "best_faithfulness": None,
        "best_answer_relevancy": None,
        "best_context_recall": None,
        "best_context_precision": None,
    }

    best_faithfulness_score = 0.0
    best_answer_relevancy_score = 0.0
    best_context_recall_score = 0.0
    best_context_precision_score = 0.0

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
        comparison["experiments"].append(exp_data)  # type: ignore[union-attr, attr-defined]

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

        if (
            exp.avg_context_recall
            and exp.avg_context_recall > best_context_recall_score
        ):
            best_context_recall_score = exp.avg_context_recall
            comparison["best_context_recall"] = exp.name

        if (
            exp.avg_context_precision
            and exp.avg_context_precision > best_context_precision_score
        ):
            best_context_precision_score = exp.avg_context_precision
            comparison["best_context_precision"] = exp.name

    return comparison
