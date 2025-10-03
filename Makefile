.PHONY: help install run dev test clean docker-build docker-up docker-down
.PHONY: db-check db-auto db-generate db-upgrade db-reset test-api test-service

help:
	@echo "📋 Available commands:"
	@echo ""
	@echo "  Database Migration (自動化):"
	@echo "    make db-check     - 檢查資料庫狀態"
	@echo "    make db-auto      - 🚀 自動生成並執行 migration"
	@echo "    make db-generate  - 從 models 生成 migration"
	@echo "    make db-upgrade   - 執行 migration"
	@echo "    make db-reset     - 重置 Alembic 版本表"
	@echo ""
	@echo "  Development:"
	@echo "    make install      - Install dependencies"
	@echo "    make run          - Run server in production mode"
	@echo "    make dev          - Run server in development mode with mock data"
	@echo ""
	@echo "  Testing:"
	@echo "    make test         - Run all tests"
	@echo "    make test-api     - Run API tests"
	@echo "    make test-service - Run Service tests"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-build - Build Docker image"
	@echo "    make docker-up    - Start Docker containers"
	@echo "    make docker-down  - Stop Docker containers"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make format       - Format code"
	@echo "    make lint         - Lint code"
	@echo "    make clean        - Clean cache files"

install:
	poetry install

run:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	MOCK_MODE=true poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	poetry run pytest

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

format:
	poetry run black app/
	poetry run ruff check app/ --fix

lint:
	poetry run black --check app/
	poetry run ruff check app/
	poetry run mypy app/

# Database Migration
db-check:
	@echo "🔍 檢查資料庫狀態..."
	@python scripts/manage_db.py check

db-auto:
	@echo "🚀 自動生成並執行 migration..."
	@python scripts/manage_db.py auto

db-generate:
	@echo "🔨 生成 migration..."
	@python scripts/manage_db.py generate

db-upgrade:
	@echo "⬆️  執行 migration..."
	@python scripts/manage_db.py upgrade

db-reset:
	@echo "🔄 重置 Alembic..."
	@python scripts/manage_db.py reset

# Additional Tests
test-api:
	@echo "🧪 執行 API 測試..."
	@poetry run pytest tests/test_cases.py -v

test-service:
	@echo "🧪 執行 Service 測試..."
	@poetry run pytest tests/test_services.py -v