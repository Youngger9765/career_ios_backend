#!/bin/bash

# Quick start script for development

echo "🚀 Starting Career Counseling Backend..."

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Python $required_version or higher is required. Found: Python $python_version"
    exit 1
fi

# Install Poetry if not installed
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "📚 Installing dependencies..."
poetry install

# Set MOCK_MODE to true for demo
export MOCK_MODE=true

# Start the server
echo "✅ Starting FastAPI server in MOCK mode..."
echo "📊 Pipeline Demo: http://localhost:8000/static/pipeline.html"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""

poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000