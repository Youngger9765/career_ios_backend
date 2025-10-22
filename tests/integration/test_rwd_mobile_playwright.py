"""Playwright E2E tests for RWD mobile sidebar functionality"""
import time
from pathlib import Path

import pytest

try:
    from playwright.sync_api import expect, sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestMobileRWD:
    """Test responsive sidebar on mobile and desktop viewports"""

    @pytest.fixture
    def base_url(self):
        """Base URL for testing"""
        return "http://localhost:8000"

    def test_mobile_sidebar_hidden_by_default(self, base_url):
        """Test that sidebar is hidden by default on mobile"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # iPhone 12 viewport
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            # Sidebar should be hidden (has -translate-x-full class)
            sidebar = page.locator("#sidebar")
            assert sidebar.is_visible(), "Sidebar element should exist"

            # Check if sidebar has hidden transform class
            class_attr = sidebar.get_attribute("class")
            assert "-translate-x-full" in class_attr, "Sidebar should be hidden on mobile"

            browser.close()

    def test_mobile_hamburger_button_visible(self, base_url):
        """Test that hamburger menu button is visible on mobile"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            # Menu button should be visible
            menu_button = page.locator("#menu-button")
            expect(menu_button).to_be_visible()

            browser.close()

    def test_mobile_toggle_sidebar(self, base_url):
        """Test sidebar toggle functionality on mobile"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            sidebar = page.locator("#sidebar")
            menu_button = page.locator("#menu-button")

            # Initially hidden
            assert "-translate-x-full" in sidebar.get_attribute("class")

            # Click hamburger button
            menu_button.click()
            time.sleep(0.5)  # Wait for animation

            # Sidebar should be visible now
            class_after_click = sidebar.get_attribute("class")
            assert "-translate-x-full" not in class_after_click, \
                "Sidebar should be visible after clicking menu button"

            browser.close()

    def test_mobile_overlay_appears(self, base_url):
        """Test that overlay appears when sidebar is open on mobile"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            overlay = page.locator("#sidebar-overlay")
            menu_button = page.locator("#menu-button")

            # Overlay initially invisible (opacity-0)
            assert "opacity-0" in overlay.get_attribute("class")
            assert "pointer-events-none" in overlay.get_attribute("class")

            # Click menu button
            menu_button.click()
            time.sleep(0.5)

            # Overlay should be visible
            overlay_class = overlay.get_attribute("class")
            assert "opacity-100" in overlay_class, "Overlay should be visible (opacity-100)"
            assert "pointer-events-auto" in overlay_class, "Overlay should be clickable"

            browser.close()

    def test_mobile_close_on_overlay_click(self, base_url):
        """Test sidebar closes when clicking overlay on mobile"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            sidebar = page.locator("#sidebar")
            menu_button = page.locator("#menu-button")

            # Open sidebar
            menu_button.click()
            time.sleep(0.5)

            # Click on overlay area (right side of screen, outside sidebar)
            # Sidebar is 320px (w-80), click at x=330 (outside sidebar)
            page.mouse.click(330, 400)
            time.sleep(0.5)

            # Sidebar should be hidden again
            assert "-translate-x-full" in sidebar.get_attribute("class")

            browser.close()

    def test_desktop_sidebar_always_visible(self, base_url):
        """Test that sidebar is always visible on desktop"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Desktop viewport (1920x1080)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            # Sidebar should be visible
            sidebar = page.locator("#sidebar")
            expect(sidebar).to_be_visible()

            # Menu button should be hidden on desktop
            menu_button = page.locator("#menu-button")
            expect(menu_button).not_to_be_visible()

            browser.close()

    def test_mobile_screenshots(self, base_url):
        """Take screenshots of mobile view for manual verification"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()

            screenshots_dir = Path(__file__).parent.parent.parent / "htmlcov" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            # Screenshot 1: Sidebar closed
            page.screenshot(path=str(screenshots_dir / "mobile_sidebar_closed.png"))

            # Screenshot 2: Sidebar open
            menu_button = page.locator("#menu-button")
            menu_button.click()
            time.sleep(0.5)
            page.screenshot(path=str(screenshots_dir / "mobile_sidebar_open.png"))

            browser.close()

            # Verify screenshots exist
            assert (screenshots_dir / "mobile_sidebar_closed.png").exists()
            assert (screenshots_dir / "mobile_sidebar_open.png").exists()

    def test_tablet_view(self, base_url):
        """Test tablet viewport (medium breakpoint)"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # iPad viewport (768x1024 - exactly at md: breakpoint)
            context = browser.new_context(viewport={"width": 768, "height": 1024})
            page = context.new_page()

            page.goto(f"{base_url}/rag")
            page.wait_for_load_state("networkidle")

            sidebar = page.locator("#sidebar")
            expect(sidebar).to_be_visible()

            # At md: breakpoint, sidebar should be visible
            # Menu button should be hidden
            menu_button = page.locator("#menu-button")
            expect(menu_button).not_to_be_visible()

            browser.close()
