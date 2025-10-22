# Test Suite Documentation

## Test Organization

### Fast Tests (137 tests, ~56 seconds)
Run with: `pytest tests/ -m "not slow"`

- **Unit Tests** (75 tests in `tests/unit/`)
  - Config, Database, Services, Validators, etc.
  - No external dependencies
  
- **Service Tests** (25 tests in `tests/test_services.py` + `tests/test_main.py`)
  - STTService, SanitizerService, ReportGenerationService
  - Uses mocks for OpenAI/external APIs

- **RAG Tests** (37 tests in `tests/rag/`)
  - OpenAI service tests
  - RAG chat API tests
  - Uses mocks for OpenAI/database

### Slow Tests (14 tests, >5 minutes)
Run with: `pytest tests/ -m "slow"`

- **Integration Tests** (14 tests in `tests/integration/`)
  - Calls real OpenAI API
  - End-to-end report generation
  - Format validation (JSON, HTML, Markdown)

## Running Tests

```bash
# Run all fast tests (recommended for development)
pytest tests/ -m "not slow"

# Run all tests including slow integration tests
pytest tests/

# Run only integration tests
pytest tests/ -m "integration"

# Run specific test file
pytest tests/unit/test_config.py -v

# Run with coverage
pytest tests/ -m "not slow" --cov=app --cov-report=html
```

## CI/CD Recommendations

```yaml
# Fast tests on every commit
- name: Run fast tests
  run: pytest tests/ -m "not slow" --maxfail=1

# Integration tests on scheduled/manual runs
- name: Run integration tests
  run: pytest tests/ -m "slow"
  if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
```

## Test Markers

- `@pytest.mark.slow` - Tests that take >1 minute
- `@pytest.mark.integration` - Tests that call real APIs
- `@pytest.mark.asyncio` - Async tests

## Notes

- Integration tests require valid `OPENAI_API_KEY` environment variable
- Fast tests use mocks and fixtures - no external dependencies needed
