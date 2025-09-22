.PHONY: help install run dev test clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run server in production mode"
	@echo "  make dev        - Run server in development mode with mock data"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean cache files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up  - Start Docker containers"
	@echo "  make docker-down - Stop Docker containers"

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