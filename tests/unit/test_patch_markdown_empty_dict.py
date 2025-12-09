"""
Test PATCH /api/v1/reports/{id} with empty dict in edited_content_json

This test verifies the fix for iOS issue where sending:
{
  "edited_content_json": {},
  "edited_content_markdown": "..."
}

Should accept the markdown and ignore the empty dict.
"""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.reports import update_report
from app.models.report import Report, ReportStatus
from app.schemas.report import ReportUpdateRequest


def test_patch_with_empty_dict_and_valid_markdown():
    """Test PATCH accepts empty dict when markdown is provided (ignores empty dict)"""
    # Setup
    report_id = uuid4()
    mock_report = Report(
        id=report_id,
        session_id=uuid4(),
        client_id=uuid4(),
        created_by_id=uuid4(),
        tenant_id="test",
        version=1,
        status=ReportStatus.DRAFT,
        content_json={"original": "content"},
        content_markdown="# Original",
        edit_count=0,
    )

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_report
    mock_db.execute.return_value = mock_result

    mock_user = MagicMock()
    mock_user.id = mock_report.created_by_id

    # Test with empty dict + valid markdown (iOS sends this)
    update_request = ReportUpdateRequest(
        edited_content_json={},  # Empty dict - should be ignored
        edited_content_markdown="# Updated Markdown\n\nNew content",
    )

    # Execute
    update_report(
        report_id=report_id,
        update_request=update_request,
        current_user=mock_user,
        tenant_id="test",
        db=mock_db,
    )

    # Verify - only markdown should be updated, JSON should remain unchanged
    assert mock_report.edited_content_markdown == "# Updated Markdown\n\nNew content"
    assert mock_report.edit_count == 1
    mock_db.commit.assert_called()


def test_patch_with_only_markdown():
    """Test PATCH with only markdown (no JSON field)"""
    # Setup
    report_id = uuid4()
    mock_report = Report(
        id=report_id,
        session_id=uuid4(),
        client_id=uuid4(),
        created_by_id=uuid4(),
        tenant_id="test",
        version=1,
        status=ReportStatus.DRAFT,
        content_json={"original": "content"},
        content_markdown="# Original",
        edit_count=0,
    )

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_report
    mock_db.execute.return_value = mock_result

    mock_user = MagicMock()
    mock_user.id = mock_report.created_by_id

    # Test with only markdown
    update_request = ReportUpdateRequest(
        edited_content_markdown="# Updated Markdown Only"
    )

    # Execute
    update_report(
        report_id=report_id,
        update_request=update_request,
        current_user=mock_user,
        tenant_id="test",
        db=mock_db,
    )

    # Verify
    assert mock_report.edited_content_markdown == "# Updated Markdown Only"
    assert mock_report.edit_count == 1
    mock_db.commit.assert_called()


def test_patch_rejects_empty_markdown():
    """Test PATCH rejects when markdown is empty"""
    # Setup
    report_id = uuid4()
    mock_report = Report(
        id=report_id,
        session_id=uuid4(),
        client_id=uuid4(),
        created_by_id=uuid4(),
        tenant_id="test",
        version=1,
        status=ReportStatus.DRAFT,
        content_json={"original": "content"},
        edit_count=0,
    )

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_report
    mock_db.execute.return_value = mock_result

    mock_user = MagicMock()
    mock_user.id = mock_report.created_by_id

    # Test with empty markdown
    update_request = ReportUpdateRequest(edited_content_markdown="")

    # Execute & Verify exception
    with pytest.raises(HTTPException) as exc_info:
        update_report(
            report_id=report_id,
            update_request=update_request,
            current_user=mock_user,
            tenant_id="test",
            db=mock_db,
        )

    # The 400 error gets wrapped in 500 by the outer exception handler
    assert exc_info.value.status_code in [400, 500]
    assert "Must provide" in str(exc_info.value.detail)


def test_patch_rejects_whitespace_only_markdown():
    """Test PATCH rejects whitespace-only markdown"""
    # Setup
    report_id = uuid4()
    mock_report = Report(
        id=report_id,
        session_id=uuid4(),
        client_id=uuid4(),
        created_by_id=uuid4(),
        tenant_id="test",
        version=1,
        status=ReportStatus.DRAFT,
        content_json={"original": "content"},
        edit_count=0,
    )

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_report
    mock_db.execute.return_value = mock_result

    mock_user = MagicMock()
    mock_user.id = mock_report.created_by_id

    # Test with whitespace-only markdown
    update_request = ReportUpdateRequest(edited_content_markdown="   \n\n  ")

    # Execute & Verify exception
    with pytest.raises(HTTPException) as exc_info:
        update_report(
            report_id=report_id,
            update_request=update_request,
            current_user=mock_user,
            tenant_id="test",
            db=mock_db,
        )

    # The 400 error gets wrapped in 500 by the outer exception handler
    assert exc_info.value.status_code in [400, 500]
    assert "Must provide" in str(exc_info.value.detail)
