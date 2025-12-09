"""Unit test for JSON column persistence issue (TDD RED-GREEN-REFACTOR)

This test demonstrates the bug where JSON columns are not marked as modified
and thus don't persist to the database.

Test approach: Use simplified in-memory SQLite database to isolate the issue.
"""

import pytest
from sqlalchemy import JSON, Column, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# Simplified model for testing (SQLite compatible)
class Base(DeclarativeBase):
    pass


class TestReport(Base):
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String)
    content_json = Column(JSON)
    edited_content_json = Column(JSON)
    edited_content_markdown = Column(Text)
    edit_count = Column(Integer, default=0)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_local()


@pytest.fixture
def sample_report(in_memory_db: Session):
    """Create a sample report in the database"""
    report = TestReport(
        tenant_id="test_tenant",
        content_json={
            "client_name": "測試個案",
            "conceptualization": "原始報告內容",
        },
    )
    in_memory_db.add(report)
    in_memory_db.commit()
    in_memory_db.refresh(report)
    return report


class TestJSONColumnPersistence:
    """測試 JSON column 的持久化問題 (TDD)"""

    def test_json_column_update_without_flag_modified_fails(
        self, in_memory_db: Session, sample_report: TestReport
    ):
        """
        ❌ RED TEST: 這個測試預期會失敗

        問題: 直接賦值 JSON column，SQLAlchemy 不會偵測到變更
        結果: commit() 後重新查詢，資料沒有更新
        """
        report_id = sample_report.id

        # Step 1: 更新 edited_content_json (模擬 PATCH endpoint)
        report = in_memory_db.execute(
            select(TestReport).where(TestReport.id == report_id)
        ).scalar_one()

        # 直接賦值 JSON column (這是問題所在)
        report.edited_content_json = {
            "client_name": "測試個案",
            "conceptualization": "編輯後的內容",
            "_test_marker": "persistence_test",
        }
        report.edit_count = 1

        # Commit
        in_memory_db.commit()

        # Step 2: 清除 session cache，重新查詢
        in_memory_db.expire_all()
        persisted_report = in_memory_db.execute(
            select(TestReport).where(TestReport.id == report_id)
        ).scalar_one()

        # Step 3: 驗證 - 這裡會失敗！
        # 因為 JSON column 沒有被標記為 modified，所以 commit 沒有真正寫入
        assert (
            persisted_report.edited_content_json is not None
        ), "edited_content_json should persist"

        assert (
            persisted_report.edited_content_json.get("_test_marker")
            == "persistence_test"
        ), "❌ BUG: JSON column was not marked as modified, changes lost!"

        assert (
            persisted_report.edit_count == 1
        ), "edit_count should persist (non-JSON column works fine)"

    def test_json_column_update_with_flag_modified_succeeds(
        self, in_memory_db: Session, sample_report: TestReport
    ):
        """
        ✅ GREEN TEST: 使用 flag_modified() 後應該成功

        解決方法: 使用 sqlalchemy.orm.attributes.flag_modified()
        結果: commit() 後重新查詢，資料正確更新
        """
        from sqlalchemy.orm import attributes

        report_id = sample_report.id

        # Step 1: 更新 edited_content_json (模擬修正後的 PATCH endpoint)
        report = in_memory_db.execute(
            select(TestReport).where(TestReport.id == report_id)
        ).scalar_one()

        # 賦值 JSON column
        report.edited_content_json = {
            "client_name": "測試個案",
            "conceptualization": "編輯後的內容",
            "_test_marker": "persistence_test_fixed",
        }
        report.edit_count = 1

        # ✅ 關鍵修正: 標記 JSON column 為 modified
        attributes.flag_modified(report, "edited_content_json")

        # Commit
        in_memory_db.commit()

        # Step 2: 清除 session cache，重新查詢
        in_memory_db.expire_all()
        persisted_report = in_memory_db.execute(
            select(TestReport).where(TestReport.id == report_id)
        ).scalar_one()

        # Step 3: 驗證 - 這次應該成功！
        assert persisted_report.edited_content_json is not None
        assert (
            persisted_report.edited_content_json.get("_test_marker")
            == "persistence_test_fixed"
        )
        assert persisted_report.edit_count == 1

    def test_markdown_column_also_needs_flag_modified(
        self, in_memory_db: Session, sample_report: TestReport
    ):
        """測試 Text column (markdown) 通常不需要 flag_modified，但為了保險起見也加上"""
        from sqlalchemy.orm import attributes

        report_id = sample_report.id

        report = in_memory_db.execute(
            select(TestReport).where(TestReport.id == report_id)
        ).scalar_one()

        report.edited_content_markdown = "# 編輯後\n\n新內容"
        # Text column 通常會自動偵測，但還是加上 flag_modified 保險
        attributes.flag_modified(report, "edited_content_markdown")

        in_memory_db.commit()
        in_memory_db.expire_all()

        persisted_report = in_memory_db.execute(
            select(TestReport).where(TestReport.id == report_id)
        ).scalar_one()

        assert persisted_report.edited_content_markdown == "# 編輯後\n\n新內容"
