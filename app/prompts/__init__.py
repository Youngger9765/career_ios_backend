"""
Prompt Templates Module

Centralized prompt templates for multi-tenant AI analysis.
Each tenant has its own prompt file for clean separation.

Structure:
- base.py: Default prompts (fallback)
- career.py: Career counseling prompts (career tenant)
- parenting.py: Parenting coaching prompts (island_parents tenant)

Usage:
    from app.prompts import PromptRegistry

    # Get prompt for specific tenant and type
    prompt = PromptRegistry.get_prompt("island_parents", "quick")
    prompt = PromptRegistry.get_prompt("career", "deep", mode="practice")
    prompt = PromptRegistry.get_prompt("island_parents", "report")

    # Falls back to default if tenant-specific not available
    prompt = PromptRegistry.get_prompt("unknown_tenant", "quick")  # Returns DEFAULT
"""

from typing import Optional

# Import default prompts
from app.prompts.base import (
    DEFAULT_DEEP_ANALYSIS_PROMPT,
    DEFAULT_QUICK_FEEDBACK_PROMPT,
    DEFAULT_REPORT_PROMPT,
)

# Import career prompts
from app.prompts.career import (
    CAREER_ANALYSIS_PROMPT,
)
from app.prompts.career import (
    DEEP_ANALYSIS_PROMPT as CAREER_DEEP_PROMPT,
)
from app.prompts.career import (
    REPORT_PROMPT as CAREER_REPORT_PROMPT,
)

# Import parenting prompts
from app.prompts.parenting import (
    EMERGENCY_MODE_PROMPT,
    ISLAND_PARENTS_8_SCHOOLS_EMERGENCY_PROMPT,
    ISLAND_PARENTS_8_SCHOOLS_PRACTICE_PROMPT,
    PRACTICE_MODE_PROMPT,
    QUICK_FEEDBACK_EMERGENCY_PROMPT,
    QUICK_FEEDBACK_PRACTICE_PROMPT,
)
from app.prompts.parenting import (
    REPORT_PROMPT as PARENTING_REPORT_PROMPT,
)


class PromptRegistry:
    """
    Centralized registry for tenant-specific prompts.

    Supports three prompt types:
    - quick: Quick feedback (toast-style, ~50 chars)
    - deep: Deep analysis (detailed JSON response)
    - report: Session report generation

    Each tenant can have custom prompts, with fallback to default.
    """

    # Tenant alias mapping (allows flexible tenant naming)
    TENANT_ALIAS = {
        "career": "career",
        "island": "island_parents",
        "island_parents": "island_parents",
    }

    # Prompt registry: {tenant: {prompt_type: {mode: prompt}}}
    _PROMPTS = {
        # Default prompts (fallback for any tenant)
        "_default": {
            "quick": {"default": DEFAULT_QUICK_FEEDBACK_PROMPT},
            "deep": {"default": DEFAULT_DEEP_ANALYSIS_PROMPT},
            "report": {"default": DEFAULT_REPORT_PROMPT},
        },
        # Career tenant
        "career": {
            # Career doesn't need quick feedback, uses default
            "deep": {"default": CAREER_DEEP_PROMPT},
            "report": {"default": CAREER_REPORT_PROMPT},
        },
        # Island Parents tenant
        "island_parents": {
            "quick": {
                "practice": QUICK_FEEDBACK_PRACTICE_PROMPT,
                "emergency": QUICK_FEEDBACK_EMERGENCY_PROMPT,
                "default": QUICK_FEEDBACK_PRACTICE_PROMPT,  # Default to practice
            },
            "deep": {
                "practice": PRACTICE_MODE_PROMPT,
                "emergency": EMERGENCY_MODE_PROMPT,
                "default": PRACTICE_MODE_PROMPT,  # Default to practice
            },
            "report": {"default": PARENTING_REPORT_PROMPT},
        },
    }

    @classmethod
    def get_prompt(
        cls,
        tenant_id: str,
        prompt_type: str,
        mode: Optional[str] = None,
    ) -> str:
        """
        Get prompt for a specific tenant and type.

        Args:
            tenant_id: Tenant identifier (e.g., "career", "island_parents", "island")
            prompt_type: Type of prompt ("quick", "deep", "report")
            mode: Optional mode for prompts with variants (e.g., "practice", "emergency")

        Returns:
            Prompt string, falls back to default if tenant-specific not found.

        Example:
            >>> PromptRegistry.get_prompt("island_parents", "quick")
            >>> PromptRegistry.get_prompt("island_parents", "deep", mode="emergency")
            >>> PromptRegistry.get_prompt("career", "report")
        """
        # Resolve tenant alias
        resolved_tenant = cls.TENANT_ALIAS.get(tenant_id, tenant_id)

        # Get tenant prompts, fallback to default
        tenant_prompts = cls._PROMPTS.get(resolved_tenant, {})
        default_prompts = cls._PROMPTS.get("_default", {})

        # Get prompt type dict
        type_prompts = tenant_prompts.get(prompt_type, {})
        default_type_prompts = default_prompts.get(prompt_type, {})

        # Resolve mode
        mode_key = mode or "default"

        # Try tenant-specific first, then default
        prompt = type_prompts.get(mode_key) or type_prompts.get("default")
        if not prompt:
            prompt = default_type_prompts.get(mode_key) or default_type_prompts.get(
                "default"
            )

        return prompt or ""

    @classmethod
    def list_tenants(cls) -> list:
        """List all available tenants (excluding _default)."""
        return [k for k in cls._PROMPTS.keys() if not k.startswith("_")]

    @classmethod
    def list_prompt_types(cls, tenant_id: str) -> list:
        """List available prompt types for a tenant."""
        resolved_tenant = cls.TENANT_ALIAS.get(tenant_id, tenant_id)
        tenant_prompts = cls._PROMPTS.get(resolved_tenant, {})
        return list(tenant_prompts.keys())


# Backward compatibility exports
__all__ = [
    # Registry
    "PromptRegistry",
    # Default prompts
    "DEFAULT_QUICK_FEEDBACK_PROMPT",
    "DEFAULT_DEEP_ANALYSIS_PROMPT",
    "DEFAULT_REPORT_PROMPT",
    # Career prompts
    "CAREER_ANALYSIS_PROMPT",
    # Parenting prompts (legacy names)
    "ISLAND_PARENTS_8_SCHOOLS_EMERGENCY_PROMPT",
    "ISLAND_PARENTS_8_SCHOOLS_PRACTICE_PROMPT",
]
