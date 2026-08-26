PYTHON_VERSION = 3.10

.PHONY: requirements
## Install/sync all dependencies into .venv
requirements:
	uv sync

.PHONY: lint
## Check formatting and lint without changing files
lint:
	uv run ruff format --check
	uv run ruff check

.PHONY: format
## Auto-fix lint issues and format source
format:
	uv run ruff check --fix
	uv run ruff format

.PHONY: test
## Run tests that do not hit the network
test:
	uv run pytest -m "not network"

.PHONY: clean
## Delete compiled Python files and tooling caches
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

.PHONY: clean-cache
## Delete the ESPN HTTP cache (safe; it refetches on demand)
clean-cache:
	rm -rf data/cache/espn
