.PHONY: help install dev lint format test openapi pre-commit-install pre-commit-run clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

dev: ## Install development dependencies
	uv sync --all-extras

lint: ## Run linting
	uv run ruff check src tests
	uv run mypy src

format: ## Format code
	uv run black src tests
	uv run ruff check --fix src tests

test: ## Run tests
	uv run pytest

openapi: ## Generate OpenAPI specification
	@echo "🔧 Generating OpenAPI specification..."
	uv run python scripts/generate_openapi.py
	@echo "✅ OpenAPI spec generated at docs/api/openapi.json"

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install
	@echo "✅ Pre-commit hooks installed"

pre-commit-run: ## Run pre-commit on all files
	uv run pre-commit run --all-files

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Development workflow commands
setup-dev: dev pre-commit-install ## Complete development setup
	@echo "🎉 Development environment ready!"
	@echo ""
	@echo "Available commands:"
	@echo "  make openapi     - Generate OpenAPI spec"
	@echo "  make lint        - Run linting"
	@echo "  make format      - Format code"
	@echo "  make test        - Run tests"
	@echo ""
	@echo "The OpenAPI spec will be auto-generated on commits when server code changes."

verify: lint test openapi ## Run all verification steps
	@echo "✅ All verification steps passed"
