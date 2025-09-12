.PHONY: help install dev test lint format check clean docs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@egrep '^(.+)\s*:.*##\s*(.+)' $(MAKEFILE_LIST) | column -t -c 2 -s ':#'

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pre-commit
	pre-commit install

dev: ## Run development server
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit/

test-integration: ## Run integration tests only
	pytest tests/integration/

test-contract: ## Run contract tests only
	pytest tests/contract/

test-cov: ## Run tests with coverage
	pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run linting (ruff)
	ruff check src/ tests/

lint-fix: ## Run linting with auto-fix
	ruff check --fix src/ tests/

format: ## Format code (black + ruff)
	black src/ tests/
	ruff format src/ tests/

format-check: ## Check if code is formatted
	black --check src/ tests/
	ruff format --check src/ tests/

type-check: ## Run type checking (mypy)
	mypy src/

check: format-check lint type-check ## Run all checks

clean: ## Clean up temporary files
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

docs: ## Generate documentation
	@echo "Documentation generation not set up yet"

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files