# Configuration Management Guide

## Overview

Configuration follows a **Single Source of Truth** pattern:

```
.env → app/core/config.py → All other modules
```

**NO fallback defaults** in service modules. All configuration must be defined in `app/core/config.py`.

## Gemini Configuration

### Core Settings

Located in `app/core/config.py`:

```python
# Gemini / Vertex AI (主要 LLM)
GEMINI_PROJECT_ID: str = "groovy-iris-473015-h3"
GEMINI_LOCATION: str = "global"  # Gemini 3 requires global endpoint
GEMINI_CHAT_MODEL: str = "gemini-3-flash-preview"  # Gemini 3 Flash (Dec 2025)
```

### Override in .env

To change configuration for local development or testing:

```bash
# .env
GEMINI_PROJECT_ID=your-project-id
GEMINI_LOCATION=global
GEMINI_CHAT_MODEL=gemini-3-flash-preview
```

### Usage in Services

**CORRECT** - Direct use of settings:

```python
from app.core.config import settings

class MyService:
    def __init__(self):
        self.project_id = settings.GEMINI_PROJECT_ID  # ✅
        self.location = settings.GEMINI_LOCATION      # ✅
```

**INCORRECT** - Fallback defaults (FORBIDDEN):

```python
# ❌ ANTI-PATTERN - DO NOT USE
self.project_id = getattr(settings, "GEMINI_PROJECT_ID", "default-value")
self.location = os.getenv("GEMINI_LOCATION", "global")
```

## Model Selection

### Available Models

1. **gemini-3-flash-preview** (Current default)
   - Location: `global`
   - Best for: Fast responses, real-time analysis
   - Used by: Realtime counseling, parenting RAG

2. **gemini-2.0-flash-exp** (Alternative)
   - Location: `us-central1`
   - Best for: Latest features, experiments

3. **gemini-1.5-pro** (Legacy)
   - Location: `us-central1`
   - Best for: Complex reasoning (higher cost)

### Switching Models

**Method 1: Update config.py (Recommended for permanent changes)**

```python
# app/core/config.py
GEMINI_CHAT_MODEL: str = "gemini-2.0-flash-exp"
GEMINI_LOCATION: str = "us-central1"  # Match model's region
```

**Method 2: Override in .env (Recommended for testing)**

```bash
# .env
GEMINI_CHAT_MODEL=gemini-2.0-flash-exp
GEMINI_LOCATION=us-central1
```

**Method 3: Override at service instantiation**

```python
# For specific use cases only
service = GeminiService(model_name="gemini-1.5-pro")
```

## Region Selection

### Available Regions

- **global**: Required for Gemini 3.x models
- **us-central1**: Supported by Gemini 1.x, 2.x models
- **asia-southeast1**: Regional alternative

### Important Notes

- Gemini 3 Flash **requires** `global` endpoint
- Gemini 2.0 Flash supports `us-central1`
- Always match region to model compatibility

## Test Scripts Configuration

### Central Config

All test scripts should use `scripts/test_config.py`:

```python
# ✅ CORRECT
from test_config import settings, API_BASE_URL

# Use settings
project_id = settings.GEMINI_PROJECT_ID
```

```python
# ❌ INCORRECT - Don't hardcode
API_BASE_URL = "https://..."  # Hardcoded
PROJECT_ID = "groovy-iris-473015-h3"  # Hardcoded
```

### API Endpoints

```python
from test_config import API_BASE_URL_STAGING, API_BASE_URL_LOCAL

# Staging
url = API_BASE_URL_STAGING  # Default

# Local testing
url = API_BASE_URL_LOCAL
```

## Configuration Verification

### Check Current Config

```bash
# In Python shell
python -c "from app.core.config import settings; print(f'Model: {settings.GEMINI_CHAT_MODEL}, Region: {settings.GEMINI_LOCATION}')"
```

### Verify .env Override

```bash
# 1. Set in .env
echo "GEMINI_CHAT_MODEL=gemini-2.0-flash-exp" >> .env

# 2. Verify
python -c "from app.core.config import settings; print(settings.GEMINI_CHAT_MODEL)"
# Should print: gemini-2.0-flash-exp
```

## Anti-Patterns (AVOID)

### 1. Fallback Defaults in Services

```python
# ❌ FORBIDDEN
self.model = getattr(settings, "GEMINI_CHAT_MODEL", "gemini-3-flash-preview")
```

**Why**: Creates multiple sources of truth, hard to track configuration.

**Fix**: Define all defaults in `config.py` only.

### 2. Environment Variables in Services

```python
# ❌ FORBIDDEN
import os
self.project_id = os.getenv("GEMINI_PROJECT_ID", "default")
```

**Why**: Bypasses pydantic validation, inconsistent with other config.

**Fix**: Use `settings.GEMINI_PROJECT_ID`.

### 3. Hardcoded Values

```python
# ❌ FORBIDDEN
self.model_name = "gemini-3-flash-preview"
```

**Why**: Can't override without code changes.

**Fix**: Use `settings.GEMINI_CHAT_MODEL`.

### 4. Try/Except Import Fallbacks

```python
# ❌ FORBIDDEN
try:
    from app.core.config import settings
    MODEL = settings.GEMINI_CHAT_MODEL
except ImportError:
    MODEL = "gemini-3-flash-preview"
```

**Why**: Hides import errors, creates silent failures.

**Fix**: Import should always succeed. If it fails, that's a bug.

## Troubleshooting

### Issue: Changes to .env not taking effect

**Cause**: Need to reload the app/scripts.

**Fix**:
```bash
# For API server
# Kill and restart the server

# For test scripts
# Just re-run the script (settings reload automatically)
```

### Issue: Import error "cannot import settings"

**Cause**: Python path not configured.

**Fix**:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### Issue: Model not supported in region

**Cause**: Model-region mismatch.

**Fix**:
- Gemini 3 Flash → `global`
- Gemini 2.0 Flash → `us-central1`
- Check [Vertex AI docs](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models) for compatibility

## Best Practices

1. **Always use settings from config.py** - Single source of truth
2. **Override in .env for testing** - Don't modify code
3. **Document model-region compatibility** - In comments
4. **Verify changes propagate** - Check before committing
5. **No hardcoded values** - Configuration should be centralized

## Related Files

- `/app/core/config.py` - Main configuration (SINGLE SOURCE OF TRUTH)
- `/.env` - Environment overrides (git-ignored)
- `/.env.example` - Template for .env
- `/scripts/test_config.py` - Central config for test scripts
- `/app/services/gemini_service.py` - Uses settings directly (no fallbacks)
- `/app/services/cache_manager.py` - Uses settings directly (no fallbacks)

---

**Version**: 1.0
**Last Updated**: 2025-12-31
**Author**: Phase 1 P1-A Configuration Refactoring
