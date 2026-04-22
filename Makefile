.PHONY: check fmt test lint-docs

check:
	uv run ruff check
	uv run ruff format --check
	uv run mypy src tests
	uv run pytest -x -q

fmt:
	uv run ruff format
	uv run ruff check --fix

test:
	uv run pytest

lint-docs:
	npx -y markdownlint-cli2 "**/*.md" "#node_modules"
