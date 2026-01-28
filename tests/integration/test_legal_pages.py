"""
Integration tests for Terms of Service and Privacy Policy pages
"""
import pytest
from fastapi.testclient import TestClient


def test_island_parents_terms_page_returns_200(client: TestClient):
    """Test Terms of Service page loads successfully"""
    response = client.get("/island-parents/terms")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_island_parents_terms_page_contains_title(client: TestClient):
    """Test Terms page contains correct title"""
    response = client.get("/island-parents/terms")
    assert "服務條款" in response.text
    assert "Terms of Service" in response.text


def test_island_parents_terms_page_has_sections(client: TestClient):
    """Test Terms page has all required sections"""
    response = client.get("/island-parents/terms")

    # Check for main sections
    assert "服務說明" in response.text
    assert "使用者責任" in response.text
    assert "訂閱與付款" in response.text
    assert "退款政策" in response.text
    assert "免責聲明" in response.text


def test_island_parents_terms_page_has_toc(client: TestClient):
    """Test Terms page has table of contents"""
    response = client.get("/island-parents/terms")
    assert "目錄" in response.text
    assert "#section-1" in response.text


def test_island_parents_privacy_page_returns_200(client: TestClient):
    """Test Privacy Policy page loads successfully"""
    response = client.get("/island-parents/privacy")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_island_parents_privacy_page_contains_title(client: TestClient):
    """Test Privacy page contains correct title"""
    response = client.get("/island-parents/privacy")
    assert "隱私權政策" in response.text
    assert "Privacy Policy" in response.text


def test_island_parents_privacy_page_has_sections(client: TestClient):
    """Test Privacy page has all required sections"""
    response = client.get("/island-parents/privacy")

    # Check for GDPR/PIPA compliance sections
    assert "資料蒐集" in response.text
    assert "資料使用" in response.text
    assert "資料安全" in response.text
    assert "您的權利" in response.text
    assert "Cookie 政策" in response.text


def test_island_parents_privacy_page_mentions_gdpr_rights(client: TestClient):
    """Test Privacy page covers GDPR user rights"""
    response = client.get("/island-parents/privacy")
    assert "查詢與閱覽" in response.text
    assert "更正" in response.text
    assert "刪除" in response.text


def test_island_parents_privacy_page_has_contact_info(client: TestClient):
    """Test Privacy page has contact information"""
    response = client.get("/island-parents/privacy")
    assert "support@islandparents.com" in response.text


def test_island_parents_terms_page_has_last_updated_date(client: TestClient):
    """Test Terms page shows last updated date"""
    response = client.get("/island-parents/terms")
    assert "2026" in response.text  # Year should be present
    assert "最後更新" in response.text


def test_island_parents_privacy_page_has_last_updated_date(client: TestClient):
    """Test Privacy page shows last updated date"""
    response = client.get("/island-parents/privacy")
    assert "2026" in response.text  # Year should be present
    assert "最後更新" in response.text
