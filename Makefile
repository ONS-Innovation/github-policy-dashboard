.DEFAULT_GOAL := all


.PHONY: all
all: ## Show the available make targets.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

.PHONY: clean
clean: ## Clean the temporary files.
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache

.PHONY: format
format:  ## Format the code.
	poetry run black .
	poetry run ruff check . --fix

.PHONY: black
black:
	poetry run black src
	poetry run black aws_lambda


.PHONY: ruff
ruff:
	poetry run ruff check src --fix
	poetry run ruff check aws_lambda --fix


.PHONY: pylint
pylint:
	poetry run pylint src
	poetry run pylint aws_lambda


.PHONY: lint
lint:  ## Run Python linter
	make black
	make ruff || true
	make pylint || true


.PHONY: mypy
mypy:  ## Run mypy.
	poetry run mypy src
	poetry run mypy aws_lambda


.PHONY: install
install:  ## Install the dependencies excluding dev.
	poetry install --only main --no-root


.PHONY: install-dev
install-dev:  ## Install the dependencies including dev.
	poetry install --no-root


.PHONY: run-local
run-local:  ## Run locally.
	streamlit run src/app.py
