.DEFAULT_GOAL := help
.PHONY: help init run test lint format typecheck migrate makemigrations shell docker-build

PYTHON := uv run python
MANAGE := $(PYTHON) manage.py

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## Bootstrap project: replace placeholders, install deps + pre-commit hooks
	@bash scripts/bootstrap.sh

run: ## Start local development server
	$(MANAGE) runserver 0.0.0.0:$${PORT:-8000}

test: ## Run test suite
	uv run pytest $(ARGS)

test-cov: ## Run tests with coverage report
	uv run pytest --cov --cov-report=term-missing $(ARGS)

lint: ## Run ruff linter
	uv run ruff check .

lint-fix: ## Run ruff with auto-fix
	uv run ruff check --fix .

format: ## Run black formatter
	uv run black .

format-check: ## Check formatting without modifying files
	uv run black --check .

typecheck: ## Run pyright type checker
	uv run pyright

migrate: ## Apply database migrations
	$(MANAGE) migrate

makemigrations: ## Create new migrations
	$(MANAGE) makemigrations $(ARGS)

shell: ## Open Django shell
	$(MANAGE) shell

shell-plus: ## Open Django shell_plus (requires django-extensions)
	$(MANAGE) shell_plus

collectstatic: ## Collect static files
	$(MANAGE) collectstatic --noinput

docker-build: ## Build production Docker image
	docker build -t sic_core:local .

docker-up: ## Start docker-compose services
	docker compose up -d

docker-up-prod: ## Start production-like docker compose profile
	docker compose -f docker-compose.prod.yml up -d

docker-down: ## Stop docker-compose services
	docker compose down

docker-down-prod: ## Stop production-like docker compose profile
	docker compose -f docker-compose.prod.yml down

docker-logs: ## Tail docker-compose logs
	docker compose logs -f

docker-logs-prod: ## Tail production-like docker compose logs
	docker compose -f docker-compose.prod.yml logs -f

export-schema: ## Export OpenAPI schema to file
	@bash scripts/export_schema.sh

pre-commit: ## Run pre-commit hooks against all files
	uv run pre-commit run --all-files
