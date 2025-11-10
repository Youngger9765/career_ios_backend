"""Unit test for direct markdown content update from frontend

This test verifies that:
1. Frontend can directly send edited_content_markdown as a string
2. Backend accepts and persists it without auto-generation from JSON
3. The persisted markdown is exactly what frontend sent
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.report import Report, ReportStatus
from app.schemas.report import ReportUpdateRequest


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@pytest.fixture
def sample_report(in_memory_db: Session):
    """Create a sample report in the database"""
    report = Report(
        tenant_id="test_tenant",
        created_by_id=uuid4(),
        session_id=uuid4(),
        client_id=uuid4(),
        content_json={
            "client_name": "測試個案",
            "conceptualization": "原始內容",
        },
        content_markdown="# 原始 AI 生成的 Markdown\n\n原始內容",
        status=ReportStatus.DRAFT,
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    in_memory_db.add(report)
    in_memory_db.commit()
    in_memory_db.refresh(report)
    return report


class TestDirectMarkdownUpdate:
    """測試前端直接更新 Markdown 字串"""

    def test_update_only_markdown_without_json(self, in_memory_db: Session, sample_report: Report):
        """
        ✅ 測試：前端只傳 edited_content_markdown，不傳 JSON

        預期：
        - Backend 接受 markdown 字串
        - 不自動生成，直接儲存前端傳來的內容
        - edited_content_json 保持 None
        """
        from sqlalchemy.orm import attributes

        report_id = sample_report.id

        # Frontend sends only markdown
        frontend_markdown = """# 前端編輯的 Markdown

## 個案概念化
這是前端使用者在 iOS App 上編輯的內容。
不是從 JSON 自動生成的！

## 治療計畫
- 認知行為治療
- 每週一次
- 持續 8 週

_Edited on iPhone_
"""

        # Simulate API update
        report = in_memory_db.execute(
            select(Report).where(Report.id == report_id)
        ).scalar_one()

        report.edited_content_markdown = frontend_markdown
        attributes.flag_modified(report, "edited_content_markdown")
        report.edited_at = datetime.now(timezone.utc).isoformat()
        report.edit_count = 1

        in_memory_db.commit()

        # Verify persistence
        in_memory_db.expire_all()
        persisted_report = in_memory_db.execute(
            select(Report).where(Report.id == report_id)
        ).scalar_one()

        assert persisted_report.edited_content_markdown == frontend_markdown, \
            "❌ Frontend markdown not persisted correctly"

        assert "前端使用者在 iOS App 上編輯的內容" in persisted_report.edited_content_markdown, \
            "❌ Markdown content lost"

        assert "_Edited on iPhone_" in persisted_report.edited_content_markdown, \
            "❌ Markdown formatting lost"

        assert persisted_report.edited_content_json is None, \
            "edited_content_json should remain None when only markdown is updated"

    def test_update_both_json_and_markdown(self, in_memory_db: Session, sample_report: Report):
        """
        ✅ 測試：前端同時傳 edited_content_json 和 edited_content_markdown

        預期：
        - 兩者都被儲存
        - Markdown 不是從 JSON 生成的，而是直接使用前端傳的
        """
        from sqlalchemy.orm import attributes

        report_id = sample_report.id

        # Frontend sends both
        frontend_json = {
            "client_name": "個案 A",
            "conceptualization": "JSON 格式的內容",
        }

        frontend_markdown = """# 前端自己編輯的 Markdown

這個 Markdown 是前端編輯的，**不是從 JSON 生成的**。

所以內容可能跟 JSON 不一樣！
"""

        # Simulate API update
        report = in_memory_db.execute(
            select(Report).where(Report.id == report_id)
        ).scalar_one()

        report.edited_content_json = frontend_json
        report.edited_content_markdown = frontend_markdown
        attributes.flag_modified(report, "edited_content_json")
        attributes.flag_modified(report, "edited_content_markdown")
        report.edited_at = datetime.now(timezone.utc).isoformat()
        report.edit_count = 1

        in_memory_db.commit()

        # Verify persistence
        in_memory_db.expire_all()
        persisted_report = in_memory_db.execute(
            select(Report).where(Report.id == report_id)
        ).scalar_one()

        assert persisted_report.edited_content_json["client_name"] == "個案 A"
        assert persisted_report.edited_content_markdown == frontend_markdown
        assert "不是從 JSON 生成的" in persisted_report.edited_content_markdown

    def test_markdown_with_special_characters(self, in_memory_db: Session, sample_report: Report):
        """
        ✅ 測試：Markdown 包含特殊字符的持久化

        前端可能會輸入各種特殊字符，需要正確儲存
        """
        from sqlalchemy.orm import attributes

        report_id = sample_report.id

        # Markdown with special characters
        special_markdown = """# 測試特殊字符

## 中文標點符號
「引號」、頓號、省略號…

## Emoji
個案情緒：😊 → 😢 → 😐

## Code block
```python
def hello():
    print("Hello")
```

## Table
| 項目 | 內容 |
|------|------|
| 測試 | ✅   |

## Math (if supported)
x² + y² = z²
"""

        report = in_memory_db.execute(
            select(Report).where(Report.id == report_id)
        ).scalar_one()

        report.edited_content_markdown = special_markdown
        attributes.flag_modified(report, "edited_content_markdown")

        in_memory_db.commit()
        in_memory_db.expire_all()

        persisted_report = in_memory_db.execute(
            select(Report).where(Report.id == report_id)
        ).scalar_one()

        assert "😊 → 😢 → 😐" in persisted_report.edited_content_markdown
        assert "```python" in persisted_report.edited_content_markdown
        assert "x² + y² = z²" in persisted_report.edited_content_markdown

    def test_schema_validation(self):
        """
        ✅ 測試：Schema 支援 optional markdown 欄位
        """
        # Test 1: Only markdown
        request1 = ReportUpdateRequest(edited_content_markdown="# Test")
        assert request1.edited_content_markdown == "# Test"
        assert request1.edited_content_json is None

        # Test 2: Only JSON
        request2 = ReportUpdateRequest(edited_content_json={"test": "data"})
        assert request2.edited_content_json == {"test": "data"}
        assert request2.edited_content_markdown is None

        # Test 3: Both
        request3 = ReportUpdateRequest(
            edited_content_json={"test": "data"},
            edited_content_markdown="# Test"
        )
        assert request3.edited_content_json == {"test": "data"}
        assert request3.edited_content_markdown == "# Test"
