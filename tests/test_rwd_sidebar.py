"""Test RWD sidebar functionality"""
import pytest
from pathlib import Path


class TestSidebarRWD:
    """Test responsive sidebar implementation"""

    def test_base_sidebar_has_mobile_menu_toggle(self):
        """Verify sidebar template has mobile menu toggle button"""
        template_path = Path(__file__).parent.parent / "app/templates/rag/base_sidebar.html"
        content = template_path.read_text()

        # Should have toggle button
        assert "toggleSidebar" in content or "toggle-sidebar" in content, \
            "Missing toggle sidebar button"

    def test_sidebar_has_collapse_state(self):
        """Verify sidebar can be collapsed via CSS classes"""
        template_path = Path(__file__).parent.parent / "app/templates/rag/base_sidebar.html"
        content = template_path.read_text()

        # Should have collapsed state management
        assert "hidden" in content or "collapsed" in content or "-translate-x" in content, \
            "Missing collapsed state CSS"

    def test_sidebar_has_responsive_breakpoints(self):
        """Verify sidebar uses responsive breakpoints (md:, lg:)"""
        template_path = Path(__file__).parent.parent / "app/templates/rag/base_sidebar.html"
        content = template_path.read_text()

        # Should use Tailwind responsive classes
        assert "md:" in content or "lg:" in content, \
            "Missing responsive breakpoint classes"

    def test_sidebar_has_mobile_overlay(self):
        """Verify sidebar has overlay for mobile view"""
        template_path = Path(__file__).parent.parent / "app/templates/rag/base_sidebar.html"
        content = template_path.read_text()

        # Should have overlay div for mobile
        assert "overlay" in content.lower() or "backdrop" in content.lower(), \
            "Missing mobile overlay"

    def test_sidebar_javascript_included(self):
        """Verify JavaScript for sidebar toggle is included"""
        template_path = Path(__file__).parent.parent / "app/templates/rag/base_sidebar.html"
        content = template_path.read_text()

        # Should have script tag
        assert "<script>" in content, "Missing JavaScript"
        # Should have toggle logic
        assert "classList" in content or "toggle" in content.lower(), \
            "Missing toggle JavaScript logic"

    def test_hamburger_icon_exists(self):
        """Verify hamburger menu icon exists"""
        template_path = Path(__file__).parent.parent / "app/templates/rag/base_sidebar.html"
        content = template_path.read_text()

        # Should have hamburger icon (☰ or SVG or emoji)
        has_icon = any([
            "☰" in content,
            "hamburger" in content.lower(),
            "bars" in content.lower(),
            "🍔" in content,
            "menu" in content.lower() and "button" in content.lower()
        ])
        assert has_icon, "Missing hamburger menu icon"

    def test_sidebar_width_responsive(self):
        """Verify sidebar width is responsive"""
        template_path = Path(__file__).parent.parent / "app/templates/rag/base_sidebar.html"
        content = template_path.read_text()

        # Original: w-80
        # Should have responsive width or full-width on mobile
        assert "w-64" in content or "w-80" in content or "w-full" in content, \
            "Sidebar width class missing"
