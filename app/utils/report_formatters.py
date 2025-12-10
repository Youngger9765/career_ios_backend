"""
Report formatters - Refactored to eliminate duplication

Design Pattern: Template Method + Strategy Pattern
- Common logic extracted to base formatter
- Format-specific logic in separate strategies
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ReportFormatter(ABC):
    """Base formatter with common report processing logic"""

    def format(self, report: Dict[str, Any]) -> str:
        """
        Template method for formatting reports

        Args:
            report: Report data dictionary

        Returns:
            Formatted report string
        """
        sections = []

        sections.append(self._format_header())
        sections.append(self._format_client_info(report.get("client_info", {})))
        sections.append(
            self._format_list_section("主訴問題", report.get("main_concerns", []))
        )
        sections.append(
            self._format_list_section("晤談目標", report.get("counseling_goals", []))
        )
        sections.append(
            self._format_list_section("諮詢技巧", report.get("techniques", []))
        )
        sections.append(
            self._format_text_section("個案概念化", report.get("conceptualization", ""))
        )
        sections.append(self._format_theories(report.get("theories", [])))
        sections.append(self._format_dialogues(report.get("dialogue_excerpts", [])))

        return self._wrap_document("".join(sections))

    @abstractmethod
    def _format_header(self) -> str:
        """Format document header"""
        pass

    @abstractmethod
    def _format_client_info(self, client_info: Dict[str, Any]) -> str:
        """Format client information section"""
        pass

    @abstractmethod
    def _format_list_section(self, title: str, items: List[str]) -> str:
        """Format a section with list of items"""
        pass

    @abstractmethod
    def _format_text_section(self, title: str, content: str) -> str:
        """Format a section with text content"""
        pass

    @abstractmethod
    def _format_theories(self, theories: List[Dict[str, Any]]) -> str:
        """Format theories section"""
        pass

    @abstractmethod
    def _format_dialogues(self, dialogues: List[Dict[str, Any]]) -> str:
        """Format dialogues section"""
        pass

    @abstractmethod
    def _wrap_document(self, content: str) -> str:
        """Wrap content in document structure"""
        pass

    @staticmethod
    def _normalize_value(value: Any) -> str:
        """
        Normalize values for display

        Handles list values by joining with commas
        """
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)


class HTMLReportFormatter(ReportFormatter):
    """HTML-specific report formatter"""

    def _format_header(self) -> str:
        return "<h1>個案報告</h1>"

    def _format_client_info(self, client_info: Dict[str, Any]) -> str:
        html = "<h2>案主基本資料</h2><table border='1'>"
        for key, value in client_info.items():
            normalized = self._normalize_value(value)
            html += f"<tr><th>{key}</th><td>{normalized}</td></tr>"
        html += "</table>"
        return html

    def _format_list_section(self, title: str, items: List[str]) -> str:
        html = f"<h2>{title}</h2><ul>"
        for item in items:
            html += f"<li>{item}</li>"
        html += "</ul>"
        return html

    def _format_text_section(self, title: str, content: str) -> str:
        return f"<h2>{title}</h2><pre>{content}</pre>"

    def _format_theories(self, theories: List[Dict[str, Any]]) -> str:
        html = "<h2>相關理論文獻</h2><ul>"
        for theory in theories:
            doc = theory.get("document", "未知文獻")
            score = theory.get("score", 0.0)
            text = theory.get("text", "")
            html += f"<li><b>{doc}</b> (相似度: {score:.2f})<br>{text[:200]}...</li>"
        html += "</ul>"
        return html

    def _format_dialogues(self, dialogues: List[Dict[str, Any]]) -> str:
        html = "<h2>關鍵對話摘錄</h2><ol>"
        for dialogue in dialogues:
            speaker = dialogue.get("speaker", "")
            text = dialogue.get("text", "")
            html += f"<li><b>{speaker}</b>: {text}</li>"
        html += "</ol>"
        return html

    def _wrap_document(self, content: str) -> str:
        return f"<html><body>{content}</body></html>"


class MarkdownReportFormatter(ReportFormatter):
    """Markdown-specific report formatter"""

    def _format_header(self) -> str:
        return "# 個案報告\n\n"

    def _format_client_info(self, client_info: Dict[str, Any]) -> str:
        md = "## 案主基本資料\n\n"
        for key, value in client_info.items():
            normalized = self._normalize_value(value)
            md += f"- **{key}**: {normalized}\n"
        md += "\n"
        return md

    def _format_list_section(self, title: str, items: List[str]) -> str:
        md = f"## {title}\n\n"
        for item in items:
            md += f"- {item}\n"
        md += "\n"
        return md

    def _format_text_section(self, title: str, content: str) -> str:
        return f"## {title}\n\n{content}\n\n"

    def _format_theories(self, theories: List[Dict[str, Any]]) -> str:
        md = "## 相關理論文獻\n\n"
        for i, theory in enumerate(theories, 1):
            doc = theory.get("document", "未知文獻")
            score = theory.get("score", 0.0)
            text = theory.get("text", "")
            md += f"### [{i}] {doc}\n\n"
            md += f"**相似度**: {score:.2f}\n\n"
            md += f"{text[:200]}...\n\n"
        return md

    def _format_dialogues(self, dialogues: List[Dict[str, Any]]) -> str:
        md = "## 關鍵對話摘錄\n\n"
        for dialogue in dialogues:
            order = dialogue.get("order", 0)
            speaker = dialogue.get("speaker", "")
            text = dialogue.get("text", "")
            md += f"{order}. **{speaker}**: {text}\n"
        md += "\n"
        return md

    def _wrap_document(self, content: str) -> str:
        return content


# Helper function to unwrap RAG response
def unwrap_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract actual report from wrapped RAG API response

    RAG API returns: {"mode": "...", "report": {...}, "quality_summary": {...}}
    Formatters need: {"client_info": {...}, "main_concerns": [...], ...}

    Args:
        data: Either wrapped RAG response or already unwrapped report

    Returns:
        Unwrapped report data

    Examples:
        >>> wrapped = {"mode": "enhanced", "report": {"client_info": {...}}}
        >>> unwrap_report(wrapped)
        {"client_info": {...}}

        >>> already_unwrapped = {"client_info": {...}}
        >>> unwrap_report(already_unwrapped)
        {"client_info": {...}}
    """
    if isinstance(data, dict) and "report" in data:
        return data["report"]
    return data


# Factory function for easy access
def create_formatter(format_type: str) -> ReportFormatter:
    """
    Create appropriate formatter based on type

    Args:
        format_type: "html" or "markdown"

    Returns:
        ReportFormatter instance

    Raises:
        ValueError: If format_type is not supported
    """
    formatters = {
        "html": HTMLReportFormatter,
        "markdown": MarkdownReportFormatter,
    }

    formatter_class = formatters.get(format_type.lower())
    if not formatter_class:
        raise ValueError(
            f"Unsupported format: {format_type}. Supported: {list(formatters.keys())}"
        )

    return formatter_class()
