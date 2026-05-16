.PHONY: help install up down logs test lint format backend-shell db-shell clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install:  ## Install backend deps locally (outside Docker)
	cd backend && uv sync

up:  ## Start everything (Postgres + backend + frontend)
	docker compose up --build

up-d:  ## Start in background
	docker compose up --build -d

down:  ## Stop everything
	docker compose down

logs:  ## Tail backend logs
	docker compose logs -f backend

test:  ## Run backend tests
	cd backend && uv run pytest -v

lint:  ## Lint and type-check
	cd backend && uv run ruff check . && uv run mypy app

format:  ## Auto-format
	cd backend && uv run ruff format . && uv run ruff check . --fix

backend-shell:  ## Shell into backend container
	docker compose exec backend bash

db-shell:  ## Postgres psql
	docker compose exec db psql -U eval -d eval

clean:  ## Remove all containers, volumes, caches
	docker compose down -v
	rm -rf backend/.venv backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
