Edge Device Fleet Manager is a production-grade Python CLI and library to discover, configure, monitor, and maintain IoT edge devices at scale. It features a hot-reloadable plugin-driven CLI, multi-tier configuration with encrypted secrets, and async device discovery over mDNS/SSDP. A domain-driven repository with event sourcing powers telemetry ingestion via MQTT, advanced analytics, and real-time dashboards. Persistence uses SQLAlchemy/Alembic with encrypted fields, while dynamic visualizations and multi-format reporting (CSV/PDF/HTML) complete the toolchain. Backed by rigorous CI/CD, observability (Prometheus, Jaeger, Sentry), and end-to-end testing, it’s built to be robust and extensible.

1. Code Execution

<img width="1920" height="1200" alt="code_execution1" src="https://github.com/user-attachments/assets/a3478235-685e-4f01-84af-16695952f155" />

<img width="1920" height="1200" alt="code_execution2" src="https://github.com/user-attachments/assets/999bf967-7374-48e0-b9cb-44cb81d76376" />

<img width="1920" height="1200" alt="code_execution3" src="https://github.com/user-attachments/assets/a4c9bef6-8f67-492a-9894-d7ca0b1d80bd" />

<img width="1920" height="1200" alt="code_execution1" src="https://github.com/user-attachments/assets/f0d0e797-b363-4913-aa06-a4d73fe44190" />

<img width="1920" height="1200" alt="code_execution" src="https://github.com/user-attachments/assets/52d62c24-7936-4493-b816-10b02f019ef0" />

<img width="1920" height="1200" alt="code_execution2" src="https://github.com/user-attachments/assets/170f3ac8-fbc9-4c70-8613-544790a7118a" />

<img width="1920" height="1200" alt="code_execution3" src="https://github.com/user-attachments/assets/0b8b6696-b9ac-43c3-a716-0885bbb5366b" />

<img width="1920" height="1200" alt="code_execution" src="https://github.com/user-attachments/assets/340807f9-5aba-4a1e-9ca0-46707c0cd805" />

<img width="1920" height="1200" alt="code_execution1" src="https://github.com/user-attachments/assets/8f32ba3c-bb9d-4c08-a684-7e972a54c298" />

<img width="1920" height="1200" alt="code_execution2" src="https://github.com/user-attachments/assets/e4981393-457b-450a-9ef7-76489a8cb044" />

<img width="1920" height="1200" alt="code_execution1" src="https://github.com/user-attachments/assets/85585e7f-cbf3-4904-8f48-2336c1a40461" />

<img width="1920" height="1200" alt="code_execution2" src="https://github.com/user-attachments/assets/74515c50-489d-4fd4-8d7c-b0195360c4b0" />

<img width="1920" height="1200" alt="code_execution1" src="https://github.com/user-attachments/assets/ddc0eb65-9244-408f-b182-9cc984b71212" />

<img width="1920" height="1200" alt="code_execution2" src="https://github.com/user-attachments/assets/e41ac1b0-84e9-4be3-b031-c10404234cbd" />

2. Test Execution

<img width="1920" height="1200" alt="test_execution1" src="https://github.com/user-attachments/assets/a5fc8556-be7f-40ef-a823-95ff4038f3e0" />

<img width="1920" height="1200" alt="test_execution2" src="https://github.com/user-attachments/assets/e98e4123-1840-479d-98de-69d5e21268cd" />

<img width="1920" height="1200" alt="test_execution1" src="https://github.com/user-attachments/assets/125d000d-8e9d-4729-9314-b208f3cc608b" />

<img width="1920" height="1200" alt="test_execution2" src="https://github.com/user-attachments/assets/ca27302c-6972-498d-acd0-1eabaa81054a" />

<img width="1920" height="1200" alt="test_execution1" src="https://github.com/user-attachments/assets/ea3d117f-a42a-4c11-a173-66876bc849c4" />

<img width="1920" height="1200" alt="test_execution2" src="https://github.com/user-attachments/assets/eb3f62cd-bc0b-473d-be98-784663954b87" />

<img width="1920" height="1200" alt="test_execution1" src="https://github.com/user-attachments/assets/2f7015f0-07ef-439e-8d9c-13afba3cead1" />

<img width="1920" height="1200" alt="test_execution2" src="https://github.com/user-attachments/assets/1b7cf141-10a2-4d5b-b2d4-9d76182a1c44" />

<img width="1920" height="1200" alt="test_execution" src="https://github.com/user-attachments/assets/d9ef548b-1483-4f5f-ab58-9afab27e5f4c" />

<img width="1920" height="1200" alt="test_execution1" src="https://github.com/user-attachments/assets/413e03a2-a238-4e89-9778-0715d57e9b4d" />

<img width="1920" height="1200" alt="test_execution2" src="https://github.com/user-attachments/assets/f505ee11-3745-4e2c-a9f2-a248f83de948" />

<img width="1920" height="1200" alt="test_execution1" src="https://github.com/user-attachments/assets/5641f356-9897-410b-b87a-719abbfbf82b" />

<img width="1920" height="1200" alt="test_execution2" src="https://github.com/user-attachments/assets/7149bb45-1e6e-45fb-9e6c-105830f99161" />

<img width="1920" height="1200" alt="test_execution1" src="https://github.com/user-attachments/assets/4f3ff8bc-8b61-4af1-889f-d37791e74de9" />

<img width="1920" height="1200" alt="test_execution2" src="https://github.com/user-attachments/assets/050343c2-06df-44cb-823f-b36b569404a1" />

Project Features Mapped to Conversations

Conversation 1: A production-grade plugin-driven CLI enables discovery and hot-reloading of commands via Watchdog. Config management merges YAML defaults, .env overrides, and AWS Secrets Manager–encrypted secrets with automatic key rotation. Shared context propagates across sync and async commands via ContextVars. Structured JSON logging with sampling and Sentry integration captures correlation IDs and errors. Pre-commit hooks enforce formatting, linting, type‑checks, and scanning. A hidden debug REPL provides inspection. A GitHub Actions CI pipeline runs linting, type‑checks, testing, and builds semantically tagged Docker images.

Conversation 2: A high‑performance async discovery module uses mDNS and SSDP via asyncio and zeroconf to enumerate IoT edge devices. A token‑bucket rate limiter enforces per‑host and global quotas with exponential‑backoff retries and full jitter, differentiating timeouts from no‑response. Raw JSON and XML payloads parse into Pydantic models with validation. OpenTelemetry spans trace discovery calls to Jaeger with metadata. A Redis cache stores discovered devices with TTL. A Rich‑driven CLI batch mode accepts subnet lists, displays progress bars and retries failed shards.

Conversation 3: The domain‑driven repository models IoT edge devices as aggregate roots, enforcing invariants via factory methods for DeviceID, Model, and FirmwareVersion. A generic Repository interface offers in‑memory and SQLAlchemy‑backed implementations switchable at runtime. Thread safety uses asyncio locks for async flows and reentrant threading locks for sync contexts. Domain events like DeviceAdded and DeviceUpdated stream to Kafka via aiokafka, with consumers updating read models or triggering webhooks. Bulk CSV import via pandas supports 50k+ records with chunk validation and Rich table summaries.

Conversation 4: The telemetry ingestion and analytics pipeline ingests MQTT device metrics via asyncio‑mqtt, buffering messages in sliding windows processed via RxPY operators. Events persist to PostgreSQL JSONB using SQLAlchemy, with CQRS projections populating analytics tables for anomaly detection and uptime queries. Computations like moving averages and outlier detection run concurrently in a ProcessPoolExecutor to maximize throughput. Metrics including ingestion rate, latency, and error count are exposed via prometheus_client. A Rich TUI dashboard displays detailed real‑time analytics.

Conversation 5: The persistence layer uses robust SQLAlchemy Core to define declarative models for devices and telemetry with indexes and constraints. Alembic integration provides auto‑generated migrations tested on SQLite and PostgreSQL via pytest fixtures. At startup, schema drift detection compares models to the database, auto‑patching missing columns or aborting with a diff. Sensitive fields encrypt via a SQLAlchemy TypeDecorator using Fernet keys from AWS KMS rotated every ninety days. A backup/restore CLI streams compressed S3 dumps with multipart upload and checksum verification.

Conversation 6: The dynamic visualization and dashboard feature offers a modular plotting engine that discovers visualizer plugins via entry points, each implementing a draw(ax, data) interface. A headless FastAPI server serves cached SVG and PNG charts from Redis, invalidating on data updates and supporting WebSocket live reload. JSON‑driven GridSpec layouts enable subplot configurations with dual axes and colorblind‑friendly themes. A Bokeh dashboard polls Prometheus metrics for real‑time browser updates. CLI flags override DPI, figure size, and output format. Hot reload support enabled.

Conversation 7: The enterprise‑grade export and alerting feature refactors reporting into a Strategy pattern, loading CSVReporter, PDFReporter, and HTMLReporter via entry points. HTML reports use Jinja2 templates with Chart.js for interactive, responsive charts. PDF reports embed watermarks, encryption, and metadata per user permissions using PyPDF2. A send‑alert CLI integrates Twilio SMS and SendGrid email with templated messages, retry logic, and logs delivery statuses in an audit database. A Dockerized HTTP server securely serves reports over HTTPS with Let’s Encrypt and certificate renewal.

Conversation 8: The CI/CD, packaging, and observability feature ensures production readiness with a robust DevOps pipeline. A tox.ini matrix tests multiple Python versions across environments in parallel. A multi‑stage Dockerfile separates linting (flake8, mypy), testing (pytest --cov), and runtime into minimal images. GitHub Actions run CodeQL scans, test suites, coverage reporting, and build‑and‑push semantic‑versioned Docker images on tags. MkDocs generates and deploys documentation to GitHub Pages with live badges. Sentry captures performance spans, and a prometheus_client exporter provides metrics for Grafana dashboards.















