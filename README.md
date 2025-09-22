# Career Counseling Backend API

FastAPI-based backend service for the Career Counseling iOS application.

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)

### Installation

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Copy environment variables
cp .env.example .env

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Development with Mock Data

```bash
# Run with mock data enabled
MOCK_MODE=true poetry run uvicorn app.main:app --reload
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
career_ios_backend/
├── app/
│   ├── api/            # API endpoints
│   ├── core/           # Core configuration
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   ├── repositories/   # Data access layer
│   ├── utils/          # Utility functions
│   └── main.py         # Application entry
├── tests/              # Test files
├── alembic/            # Database migrations
├── scripts/            # Utility scripts
└── docker/             # Docker configurations
```

## Pipeline Flow

See `docs/pipeline.html` for interactive pipeline visualization.

## Testing

```bash
# Run tests
poetry run pytest

# With coverage
poetry run pytest --cov=app
```

## Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Production build
docker build -t career-backend .
docker run -p 8000:8000 career-backend
```