# Multi-stage Dockerfile for Edge Device Fleet Manager

# Stage 1: Lint and type check
FROM python:3.11-slim as lint
WORKDIR /app

# Install system dependencies for linting
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install linting tools
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source code
COPY . .

# Run linting and type checking
RUN black --check .
RUN isort --check-only .
RUN flake8 .
RUN mypy edge_device_fleet_manager

# Stage 2: Test
FROM python:3.11-slim as test
WORKDIR /app

# Install system dependencies for testing
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source code and tests
COPY . .

# Run tests with coverage
RUN pytest --cov=edge_device_fleet_manager --cov-report=term-missing --cov-fail-under=90

# Stage 3: Build runtime image
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r edgefleet && useradd -r -g edgefleet edgefleet

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install runtime dependencies only
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application code
COPY edge_device_fleet_manager/ ./edge_device_fleet_manager/
COPY configs/ ./configs/

# Create necessary directories
RUN mkdir -p /app/plugins /app/logs /app/data \
    && chown -R edgefleet:edgefleet /app

# Switch to non-root user
USER edgefleet

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import edge_device_fleet_manager; print('OK')" || exit 1

# Expose default ports
EXPOSE 8000 9090

# Set default command
ENTRYPOINT ["python", "-m", "edge_device_fleet_manager.cli.main"]
CMD ["--help"]

# Labels for metadata
LABEL org.opencontainers.image.title="Edge Device Fleet Manager"
LABEL org.opencontainers.image.description="Production-grade Python CLI and library for IoT edge device management at scale"
LABEL org.opencontainers.image.vendor="Edge Fleet Team"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/edge-fleet/edge-device-fleet-manager"
LABEL org.opencontainers.image.documentation="https://edge-fleet.github.io/edge-device-fleet-manager"
