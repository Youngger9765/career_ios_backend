"""Tests for evaluation matrix helper functions"""

import uuid
from datetime import datetime

from app.services.evaluation.evaluation_matrix import (
    format_experiments,
    format_prompts,
    format_testsets,
)


class TestFormatTestsets:
    """Tests for format_testsets function"""

    def test_empty_list(self):
        """Should return empty list for no testsets"""
        result = format_testsets([])
        assert result == []

    def test_single_testset(self):
        """Should format single testset correctly"""
        test_id = uuid.uuid4()
        testset = type("obj", (object,), {"id": test_id, "name": "Test Set 1"})()

        result = format_testsets([testset])

        assert len(result) == 1
        assert result[0]["id"] == str(test_id)
        assert result[0]["name"] == "Test Set 1"

    def test_multiple_testsets(self):
        """Should format multiple testsets correctly"""
        id1, id2 = uuid.uuid4(), uuid.uuid4()
        testsets = [
            type("obj", (object,), {"id": id1, "name": "Set 1"})(),
            type("obj", (object,), {"id": id2, "name": "Set 2"})(),
        ]

        result = format_testsets(testsets)

        assert len(result) == 2
        assert result[0]["id"] == str(id1)
        assert result[1]["id"] == str(id2)


class TestFormatPrompts:
    """Tests for format_prompts function"""

    def test_empty_list(self):
        """Should return empty list for no prompts"""
        result = format_prompts([])
        assert result == []

    def test_single_prompt(self):
        """Should extract version field only"""
        prompts = [{"version": "v1", "template": "...", "hash": "abc"}]

        result = format_prompts(prompts)

        assert len(result) == 1
        assert result[0] == {"version": "v1"}
        assert "template" not in result[0]
        assert "hash" not in result[0]

    def test_multiple_prompts(self):
        """Should format multiple prompts correctly"""
        prompts = [
            {"version": "v1", "extra": "data"},
            {"version": "v2", "extra": "data"},
        ]

        result = format_prompts(prompts)

        assert len(result) == 2
        assert result[0] == {"version": "v1"}
        assert result[1] == {"version": "v2"}


class TestFormatExperiments:
    """Tests for format_experiments function"""

    def test_empty_list(self):
        """Should return empty list for no experiments"""
        result = format_experiments([])
        assert result == []

    def test_single_experiment_all_fields(self):
        """Should format all experiment fields correctly"""
        exp_id = uuid.uuid4()
        now = datetime.now()

        exp = type(
            "obj",
            (object,),
            {
                "id": exp_id,
                "name": "Test Exp",
                "status": "completed",
                "chunk_strategy": "recursive",
                "instruction_version": "v1",
                "avg_faithfulness": 0.8,
                "avg_answer_relevancy": 0.9,
                "avg_context_recall": 0.7,
                "avg_context_precision": 0.85,
                "total_queries": 10,
                "created_at": now,
                "chunking_method": "semantic",
                "chunk_size": 512,
                "chunk_overlap": 50,
            },
        )()

        result = format_experiments([exp])

        assert len(result) == 1
        assert result[0]["experiment_id"] == str(exp_id)
        assert result[0]["name"] == "Test Exp"
        assert result[0]["status"] == "completed"
        assert result[0]["chunk_strategy"] == "recursive"
        assert result[0]["avg_faithfulness"] == 0.8
        assert result[0]["total_queries"] == 10

    def test_experiment_with_none_values(self):
        """Should handle None values gracefully"""
        exp = type(
            "obj",
            (object,),
            {
                "id": uuid.uuid4(),
                "name": "Test",
                "status": "pending",
                "chunk_strategy": None,
                "instruction_version": None,
                "avg_faithfulness": None,
                "avg_answer_relevancy": None,
                "avg_context_recall": None,
                "avg_context_precision": None,
                "total_queries": None,
                "created_at": None,
                "chunking_method": None,
                "chunk_size": None,
                "chunk_overlap": None,
            },
        )()

        result = format_experiments([exp])

        assert len(result) == 1
        assert result[0]["chunk_strategy"] is None
        assert result[0]["avg_faithfulness"] is None
        assert result[0]["total_queries"] == 0  # None converts to 0
        assert result[0]["created_at"] is None

    def test_multiple_experiments(self):
        """Should format multiple experiments correctly"""
        id1, id2 = uuid.uuid4(), uuid.uuid4()
        experiments = [
            type(
                "obj",
                (object,),
                {
                    "id": id1,
                    "name": "Exp 1",
                    "status": "completed",
                    "chunk_strategy": "recursive",
                    "instruction_version": "v1",
                    "avg_faithfulness": 0.8,
                    "avg_answer_relevancy": 0.9,
                    "avg_context_recall": 0.7,
                    "avg_context_precision": 0.85,
                    "total_queries": 10,
                    "created_at": datetime.now(),
                    "chunking_method": "semantic",
                    "chunk_size": 512,
                    "chunk_overlap": 50,
                },
            )(),
            type(
                "obj",
                (object,),
                {
                    "id": id2,
                    "name": "Exp 2",
                    "status": "running",
                    "chunk_strategy": "fixed",
                    "instruction_version": "v2",
                    "avg_faithfulness": 0.7,
                    "avg_answer_relevancy": 0.8,
                    "avg_context_recall": 0.6,
                    "avg_context_precision": 0.75,
                    "total_queries": 5,
                    "created_at": datetime.now(),
                    "chunking_method": "fixed",
                    "chunk_size": 256,
                    "chunk_overlap": 25,
                },
            )(),
        ]

        result = format_experiments(experiments)

        assert len(result) == 2
        assert result[0]["experiment_id"] == str(id1)
        assert result[1]["experiment_id"] == str(id2)
