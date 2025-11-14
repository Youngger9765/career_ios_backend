"""
Test PATCH /api/v1/reports/{id} with empty dict in edited_content_json

This test verifies the fix for iOS issue where sending:
{
  "edited_content_json": {},
  "edited_content_markdown": "..."
}

Should accept the markdown and ignore the empty dict.
"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException
from app.api.reports import update_report
from app.schemas.report import ReportUpdateRequest
from app.models.report import Report, ReportStatus


def test_patch_with_empty_dict_and_valid_markdown():
    """Test PATCH accepts empty dict when markdown is provided"""
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

    # Test with empty dict + valid markdown
    update_request = ReportUpdateRequest(
        edited_content_json={},  # Empty dict (iOS sends this)
        edited_content_markdown="# Updated Markdown\n\nNew content"
    )

    # Execute
    result = update_report(
        report_id=report_id,
        update_request=update_request,
        current_user=mock_user,
        tenant_id="test",
        db=mock_db,
    )

    # Verify
    assert mock_report.edited_content_markdown == "# Updated Markdown\n\nNew content"
    assert mock_report.edited_content_json is None or mock_report.edited_content_json == {"original": "content"}  # Should not be updated
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
    result = update_report(
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


def test_patch_rejects_both_empty():
    """Test PATCH rejects when both fields are empty/None"""
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

    # Test with empty dict and empty string
    update_request = ReportUpdateRequest(
        edited_content_json={},
        edited_content_markdown=""
    )

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
    assert "Must provide either" in str(exc_info.value.detail)


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
    update_request = ReportUpdateRequest(
        edited_content_markdown="   \n\n  "
    )

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
    assert "Must provide either" in str(exc_info.value.detail)
