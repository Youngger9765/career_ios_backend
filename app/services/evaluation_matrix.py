"""Helper functions for evaluation matrix data preparation"""

from typing import Any


def format_testsets(testsets_db: list[Any]) -> list[dict[str, str]]:
    """Format testset database objects to API response format

    Args:
        testsets_db: List of EvaluationTestSet objects from database

    Returns:
        List of dicts with id and name fields
    """
    return [{"id": str(ts.id), "name": ts.name} for ts in testsets_db]


def format_prompts(prompts_list: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Format prompt versions to matrix format

    Args:
        prompts_list: List of prompt version dicts with version field

    Returns:
        List of dicts with version field only
    """
    return [{"version": p["version"]} for p in prompts_list]


def format_experiments(experiments_db: list[Any]) -> list[dict[str, Any]]:
    """Format experiment database objects to API response format

    Args:
        experiments_db: List of EvaluationExperiment objects from database

    Returns:
        List of experiment dicts with all relevant fields
    """
    from app.api.rag_evaluation import safe_float

    experiments_list = []
    for exp in experiments_db:
        experiments_list.append({
            "experiment_id": str(exp.id),
            "name": exp.name,
            "status": exp.status,
            "chunk_strategy": exp.chunk_strategy,
            "instruction_version": exp.instruction_version,
            "avg_faithfulness": safe_float(exp.avg_faithfulness),
            "avg_answer_relevancy": safe_float(exp.avg_answer_relevancy),
            "avg_context_recall": safe_float(exp.avg_context_recall),
            "avg_context_precision": safe_float(exp.avg_context_precision),
            "total_queries": exp.total_queries or 0,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "chunking_method": exp.chunking_method,
            "chunk_size": exp.chunk_size,
            "chunk_overlap": exp.chunk_overlap,
        })

    return experiments_list
