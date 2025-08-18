.PHONY: help dev up down migrate test clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: ## Start development environment
	docker-compose up --build

up: ## Start services
	docker-compose up -d

down: ## Stop services
	docker-compose down

migrate: ## Run database migrations
	docker-compose exec server alembic upgrade head

test: ## Run tests
	pytest tests/ -v

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

install: ## Install dependencies
	pip install poetry
	poetry install

format: ## Format code with black
	black src/ tests/

lint: ## Lint code with flake8
	flake8 src/ tests/

type-check: ## Type check with mypy
	mypy src/

check: format lint type-check ## Run all checks 