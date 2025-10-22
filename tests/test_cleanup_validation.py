"""Test cleanup validation - ensure no critical imports break after cleanup"""
import pytest
from pathlib import Path


class TestCleanupValidation:
    """Validate that cleanup operations don't break the codebase"""

    def test_core_database_imports_work(self):
        """Test that core.database can be imported"""
        from app.core.database import Base, SessionLocal, engine, get_db

        assert Base is not None
        assert SessionLocal is not None
        assert engine is not None
        assert get_db is not None

    def test_no_old_database_imports_in_app(self):
        """Verify no app code uses old app.database imports"""
        app_dir = Path(__file__).parent.parent / "app"

        # Search for old imports
        old_imports = []
        for py_file in app_dir.rglob("*.py"):
            if py_file.name == "database.py":
                # Skip the database.py file itself
                continue

            content = py_file.read_text()
            if "from app.database import" in content:
                old_imports.append(str(py_file.relative_to(app_dir.parent)))

        assert len(old_imports) == 0, f"Found old imports in: {old_imports}"

    def test_no_old_database_imports_in_tests(self):
        """Verify no test code uses old app.database imports"""
        tests_dir = Path(__file__).parent

        old_imports = []
        for py_file in tests_dir.rglob("*.py"):
            if py_file.name == "test_cleanup_validation.py":
                # Skip this test file
                continue

            content = py_file.read_text()
            if "from app.database import" in content:
                old_imports.append(str(py_file.relative_to(tests_dir.parent)))

        assert len(old_imports) == 0, f"Found old imports in tests: {old_imports}"

    def test_temporary_files_removed(self):
        """Verify temporary files are removed"""
        root = Path(__file__).parent.parent

        temp_files = [
            "fix_migration.py",
            "gcp-service-account.json",
            "server.log",
        ]

        for temp_file in temp_files:
            file_path = root / temp_file
            assert not file_path.exists(), f"Temporary file still exists: {temp_file}"

    def test_test_scripts_moved_to_tests(self):
        """Verify manual scripts are renamed (not in pytest discovery)"""
        root = Path(__file__).parent.parent

        # These should NOT be in root
        root_test_files = [
            "test_eval_flow.py",
            "test_ragas.py",
            "test_matrix_debug.py",
            "test_matrix_frontend.py",
        ]

        for test_file in root_test_files:
            assert not (root / test_file).exists(), f"Test file still in root: {test_file}"

        # Manual scripts should be renamed to manual_*
        assert (root / "tests" / "integration" / "manual_eval_flow.py").exists()
        assert (root / "tests" / "integration" / "manual_matrix_debug.py").exists()
        assert (root / "tests" / "integration" / "manual_matrix_frontend.py").exists()
        assert (root / "tests" / "rag" / "manual_ragas.py").exists()

    def test_old_batch_eval_removed(self):
        """Verify old batch_eval_all_strategies.py is removed"""
        root = Path(__file__).parent.parent
        old_script = root / "batch_eval_all_strategies.py"

        assert not old_script.exists(), "Old batch_eval_all_strategies.py still exists"

    def test_docs_archived(self):
        """Verify completed project docs are archived"""
        docs_dir = Path(__file__).parent.parent / "docs"
        archive_dir = docs_dir / "archive" / "2025-10"

        # These should be in archive
        archived_docs = [
            "報告生成改善_完工報告.md",
            "報告生成改善_施工計畫.md",
            "API_CHANGES_report_quality.md",
        ]

        for doc in archived_docs:
            # Should NOT be in docs root
            assert not (docs_dir / doc).exists(), f"Doc not archived: {doc}"
            # SHOULD be in archive
            assert (archive_dir / doc).exists(), f"Doc not in archive: {doc}"


class TestAllImportsStillWork:
    """Ensure all critical imports still work after cleanup"""

    def test_main_app_imports(self):
        """Test main app imports"""
        from app.main import app
        assert app is not None

    def test_api_imports(self):
        """Test API module imports"""
        from app.api import rag_chat, rag_ingest, rag_search
        assert rag_chat is not None
        assert rag_ingest is not None
        assert rag_search is not None

    def test_service_imports(self):
        """Test service imports"""
        from app.services import report_service, openai_service
        assert report_service is not None
        assert openai_service is not None

    def test_model_imports(self):
        """Test model imports"""
        from app.models import user, session, report, agent
        assert user is not None
        assert session is not None
        assert report is not None
        assert agent is not None
