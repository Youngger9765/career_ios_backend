"""
AI Service Pricing Configuration
所有 AI 服務的定價資訊集中管理

Pricing sources:
- ElevenLabs: https://elevenlabs.io/pricing
- Gemini: https://ai.google.dev/pricing

Last updated: 2025-02-07
"""

# ============================================================================
# ElevenLabs Pricing
# ============================================================================

# ElevenLabs Scribe v2 Realtime STT
# https://elevenlabs.io/pricing (as of 2025-02)
ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_HOUR = 0.40
ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND = (
    ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_HOUR / 3600
)

# ============================================================================
# Gemini Pricing
# ============================================================================

# Gemini Flash Lite (gemini-flash-lite-latest)
# https://ai.google.dev/pricing (as of 2025-02)
# Used for: Emotion Analysis (real-time feedback)
GEMINI_FLASH_LITE_INPUT_USD_PER_1M_TOKENS = 0.075
GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M_TOKENS = 0.30

# Gemini 1.5 Flash (gemini-1.5-flash-latest)
# Used for: Deep Analysis (analyze_partial), Quick Feedback
GEMINI_1_5_FLASH_INPUT_USD_PER_1M_TOKENS = 0.50
GEMINI_1_5_FLASH_OUTPUT_USD_PER_1M_TOKENS = 3.00

# Gemini 1.5 Flash (gemini-1.5-flash-latest)
# Used for: Report Generation (parents report)
# Higher tier pricing applies to longer context windows
GEMINI_1_5_FLASH_REPORT_INPUT_USD_PER_1M_TOKENS = 1.25
GEMINI_1_5_FLASH_REPORT_OUTPUT_USD_PER_1M_TOKENS = 5.00

# Gemini 3 Flash (gemini-3-flash-preview)
# Used for: Report Generation, Deep Analysis
GEMINI_3_FLASH_INPUT_USD_PER_1M_TOKENS = 0.50
GEMINI_3_FLASH_OUTPUT_USD_PER_1M_TOKENS = 3.00

# ============================================================================
# Model Name Normalization
# ============================================================================


def normalize_model_name(model_name: str) -> str:
    """
    Normalize model name by removing 'models/' prefix if present.

    Google's Gemini API returns model names in two formats:
    - Vertex AI: "models/gemini-1.5-flash-latest"
    - Generative AI SDK: "gemini-1.5-flash-latest"

    This function ensures consistent pricing lookups regardless of format.

    Args:
        model_name: Model name (with or without "models/" prefix)

    Returns:
        Normalized model name without prefix

    Example:
        >>> normalize_model_name("models/gemini-1.5-flash-latest")
        "gemini-1.5-flash-latest"
        >>> normalize_model_name("gemini-1.5-flash-latest")
        "gemini-1.5-flash-latest"
    """
    return model_name.replace("models/", "")


# ============================================================================
# Model Name to Pricing Mapping
# ============================================================================

# Map model names to their pricing tiers
# Note: Only unprefixed versions are stored; normalize_model_name() handles
# both "models/gemini-*" and "gemini-*" formats
MODEL_PRICING_MAP = {
    "gemini-flash-lite-latest": {
        "input_price": GEMINI_FLASH_LITE_INPUT_USD_PER_1M_TOKENS,
        "output_price": GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M_TOKENS,
        "display_name": "Gemini Flash Lite",
    },
    "gemini-1.5-flash-latest": {
        "input_price": GEMINI_1_5_FLASH_INPUT_USD_PER_1M_TOKENS,
        "output_price": GEMINI_1_5_FLASH_OUTPUT_USD_PER_1M_TOKENS,
        "display_name": "Gemini Flash 1.5",
    },
    "gemini-3-flash-preview": {
        "input_price": GEMINI_3_FLASH_INPUT_USD_PER_1M_TOKENS,
        "output_price": GEMINI_3_FLASH_OUTPUT_USD_PER_1M_TOKENS,
        "display_name": "Gemini 3 Flash",
    },
}


# ============================================================================
# Cost Calculation Helpers
# ============================================================================


def calculate_gemini_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_1m: float,
    output_price_per_1m: float,
) -> float:
    """
    計算 Gemini token 成本

    Args:
        input_tokens: 輸入 token 數量
        output_tokens: 輸出 token 數量
        input_price_per_1m: 每百萬輸入 token 價格 (USD)
        output_price_per_1m: 每百萬輸出 token 價格 (USD)

    Returns:
        總成本 (USD)

    Example:
        >>> calculate_gemini_cost(1000, 500, 0.075, 0.30)
        0.00025  # (1000/1M * 0.075) + (500/1M * 0.30)
    """
    input_cost = (input_tokens / 1_000_000) * input_price_per_1m
    output_cost = (output_tokens / 1_000_000) * output_price_per_1m
    return input_cost + output_cost


def calculate_elevenlabs_cost(duration_seconds: float) -> float:
    """
    計算 ElevenLabs Scribe v2 Realtime 成本

    Args:
        duration_seconds: 音訊時長（秒）

    Returns:
        成本 (USD)

    Example:
        >>> calculate_elevenlabs_cost(3600)  # 1 hour
        0.40
        >>> calculate_elevenlabs_cost(1800)  # 30 minutes
        0.20
    """
    return duration_seconds * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND


def get_model_pricing(model_name: str) -> dict:
    """
    Get pricing information for a given model

    Args:
        model_name: Model name (with or without "models/" prefix)

    Returns:
        Dictionary with input_price, output_price, display_name

    Raises:
        KeyError: If model not found in pricing map
    """
    normalized = normalize_model_name(model_name)
    if normalized not in MODEL_PRICING_MAP:
        raise KeyError(
            f"Unknown model: {model_name} (normalized: {normalized}). "
            f"Available models: {list(MODEL_PRICING_MAP.keys())}"
        )
    return MODEL_PRICING_MAP[normalized]


def calculate_cost_for_model(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate cost for a specific model based on its pricing tier

    Args:
        model_name: Model name (with or without "models/" prefix)
        input_tokens: Input token count
        output_tokens: Output token count

    Returns:
        Total cost (USD)

    Example:
        >>> calculate_cost_for_model("gemini-flash-lite-latest", 1000, 500)
        0.00025
        >>> calculate_cost_for_model("models/gemini-flash-lite-latest", 1000, 500)
        0.00025  # Same result after normalization
    """
    pricing = get_model_pricing(model_name)  # Will normalize internally
    return calculate_gemini_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_price_per_1m=pricing["input_price"],
        output_price_per_1m=pricing["output_price"],
    )
