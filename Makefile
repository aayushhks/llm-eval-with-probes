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

db-revision:  ## Generate a new alembic migration (use: make db-revision msg="something")
	cd backend && uv run alembic revision --autogenerate -m "$(msg)"

db-upgrade:  ## Apply all pending migrations
	cd backend && uv run alembic upgrade head

db-downgrade:  ## Roll back one migration
	cd backend && uv run alembic downgrade -1

eval-v1:  ## Run full eval with prompt v1
	cd backend && uv run python ../scripts/run_eval.py --prompt v1

eval-v2:  ## Run full eval with prompt v2
	cd backend && uv run python ../scripts/run_eval.py --prompt v2