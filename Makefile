# Makefile for Edge Device Fleet Manager

.PHONY: help install install-dev test test-unit test-integration test-coverage lint format type-check security-check clean build docker-build docker-run docs serve-docs

# Default target
help:
	@echo "Edge Device Fleet Manager - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install package in production mode"
	@echo "  install-dev      Install package in development mode with all dependencies"
	@echo "  setup-hooks      Install pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-watch       Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run all linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run mypy type checking"
	@echo "  security-check   Run security scans"
	@echo "  pre-commit       Run all pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  run-dev          Run CLI in development mode"
	@echo "  debug-repl       Start debug REPL"
	@echo "  clean            Clean build artifacts"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  build            Build package"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run Docker container"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Build documentation"
	@echo "  serve-docs       Serve documentation locally"

# Setup targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

setup-hooks:
	pre-commit install
	pre-commit install --hook-type pre-push

# Testing targets
test:
	pytest

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

test-coverage:
	pytest --cov=edge_device_fleet_manager --cov-report=html --cov-report=term-missing --cov-report=xml

test-watch:
	pytest-watch

# Code quality targets
lint:
	flake8 edge_device_fleet_manager tests
	pylint edge_device_fleet_manager

format:
	black edge_device_fleet_manager tests
	isort edge_device_fleet_manager tests

type-check:
	mypy edge_device_fleet_manager

security-check:
	bandit -r edge_device_fleet_manager
	safety check

pre-commit:
	pre-commit run --all-files

# Development targets
run-dev:
	python -m edge_device_fleet_manager.cli.main --debug

debug-repl:
	python -m edge_device_fleet_manager.cli.main debug-repl

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .tox/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Build targets
build: clean
	python -m build

docker-build:
	docker build -t edge-device-fleet-manager:latest .

docker-run:
	docker run --rm -it edge-device-fleet-manager:latest

# Documentation targets
docs:
	mkdocs build

serve-docs:
	mkdocs serve

# AWS LocalStack setup for development
setup-localstack:
	@echo "Setting up LocalStack for development..."
	docker run -d --name localstack -p 4566:4566 localstack/localstack
	@echo "Waiting for LocalStack to start..."
	sleep 10
	@echo "Creating test secrets..."
	aws secretsmanager create-secret \
		--name edge-fleet-manager/encryption-key \
		--secret-string '{"key":"test-encryption-key-base64"}' \
		--endpoint-url http://localhost:4566 \
		--region us-east-1
	aws secretsmanager create-secret \
		--name edge-fleet-manager/secrets \
		--secret-string '{"database__password":"test_db_pass","mqtt__password":"test_mqtt_pass"}' \
		--endpoint-url http://localhost:4566 \
		--region us-east-1
	@echo "LocalStack setup complete!"

stop-localstack:
	docker stop localstack
	docker rm localstack

# Development environment setup
dev-setup: install-dev setup-hooks
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything is working."

# CI simulation
ci-check: format type-check lint security-check test-coverage
	@echo "All CI checks passed!"

# Release preparation
prepare-release: clean ci-check build
	@echo "Release preparation complete!"
	@echo "Built packages are in dist/"
