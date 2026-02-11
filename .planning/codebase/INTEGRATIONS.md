# External Integrations

**Analysis Date:** 2026-02-11

## APIs & External Services

**LinkedIn Platform:**
- LinkedIn job search, easy apply, employee search, and messaging
  - SDK/Client: Custom MCP client via FastMCP (`src/core/providers/linkedin_mcp_client.py`, `src/linkedin_mcp/linkedin_server.py`)
  - Auth: Browser-based (Selenium) using `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`
  - Protocol: Model Context Protocol over HTTP (port 3000)
  - Tools exposed: `search_jobs`, `easy_apply_for_jobs`, `search_employees`, `search_employees_batch`, `send_messages_batch`

**LLM Inference:**
- OpenAI-compatible API for job filtering, CV analysis, form filling
  - SDK/Client: `langchain-openai` 0.3.0 (`src/core/providers/llm_client.py`)
  - Base URL: `LOCAL_LLM_BASE_URL` (default: http://localhost:8088/v1)
  - API Key: `LOCAL_LLM_API_KEY` (default: "not-needed")
  - Use cases: CV structure analysis, job-CV alignment, form field completion
  - Config location: `config/agent.yaml` (`llm.base_url`, `llm.api_key`, `llm.temperature`, `llm.max_tokens`)

**Hugging Face (Optional):**
- Serverless inference for embeddings or specialized models
  - Token: `HUGGING_FACE_HUB_TOKEN` (env var)
  - Integrated via `langchain-huggingface` 0.3.1 (in dependencies)
  - Status: Optional, not actively used in current codebase but available for future enhancements

## Data Storage

**Databases:**
- **Agent Database (Sessions, Applications, Messages):**
  - Type: SQLite (primary)
  - Connection: `src/core/db/agent.db` (default via `DATABASE_URL`)
  - URL format: `sqlite:///./data/agent.db`
  - Client: SQLAlchemy 2.0.0 with custom ORM models
  - Tables: `sessions`, `job_applications`, `messages_sent`, `daily_quota`, `search_results`
  - Location: `src/core/db/models.py` (Pydantic models), `src/core/db/agent_db.py` (repository pattern)
  - Features: WAL mode (write-ahead logging), connection pooling, expiring sessions with TTL

- **Company Database (Outreach):**
  - Type: SQLite
  - Path: `./data/companies.db` (via `COMPANY_DATABASE_URL`)
  - Contains: Company profiles, industry, size, location data
  - Loaded from: CSV dataset import (`scripts/cli.py import-dataset`)
  - Used by: Outreach workflows to filter target companies

**File Storage:**
- Local filesystem only
  - CV data: `./data/cv_data.json` (JSON format, not PDF)
  - Dataset: `./data/free_company_dataset.csv` (for outreach)
  - Logs: `./logs/` (configured in `.env.example`)
  - Results: `./results/` (optional, controlled by `SAVE_RESULTS`)

**Caching:**
- In-memory: Session store with TTL (`src/core/api/services/session_store.py`, default 3600s)
- LLM client caching: Single cached instance per process (`src/core/providers/llm_client.py`)

## Authentication & Identity

**Auth Provider:**
- Custom (LinkedIn browser login)
  - Implementation: Selenium/undetected-chromedriver automated login (`src/linkedin_mcp/services/linkedin_auth_service.py`)
  - Credentials: `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD` env vars
  - MFA: Not explicitly supported; assumes no 2FA on account
  - Session management: Browser session per MCP server instance

## Monitoring & Observability

**Error Tracking:**
- Langfuse (optional)
  - Credentials: `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST`
  - Host: `https://cloud.langfuse.com` (default)
  - Config location: `src/core/observability/langfuse_config.py`
  - Integration: LangGraph callback handler for tracing workflows
  - Status: Optional; gracefully disabled if credentials missing

**Logs:**
- Loguru structured logging (`src/core/utils/logging_config.py`)
- Output: Console and file (`./logs/job_applier.log`, `./logs/core_agent.log`, `./logs/linkedin_mcp.log`)
- Log levels: Configurable via `LOG_LEVEL`, `CORE_AGENT_LOG_LEVEL`, `LINKEDIN_MCP_LOG_LEVEL`
- Structured fields: trace_id for request correlation across services

## CI/CD & Deployment

**Hosting:**
- Docker containers (docker-compose.yml)
  - Core Agent: FastAPI service on port 8080
  - LinkedIn MCP Server: FastMCP service on port 3000
  - Kafka: Confluent Kafka 7.7.0 (KRaft, no Zookeeper) on port 9092

**CI Pipeline:**
- None detected in codebase
- Pre-commit hooks: black, isort formatting checks (`.pre-commit-config.yaml`)
- Type checking: basedpyright static analysis (`pyrightconfig.json`)

## Environment Configuration

**Required env vars:**
- `LINKEDIN_EMAIL` - LinkedIn account email
- `LINKEDIN_PASSWORD` - LinkedIn account password
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka broker (default: localhost:9092)
- `MCP_SERVER_HOST`, `MCP_SERVER_PORT` - LinkedIn MCP server (default: localhost:3000)

**Optional env vars:**
- `HUGGING_FACE_HUB_TOKEN` - For HF models
- `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY` - Observability
- `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_API_KEY` - Custom LLM endpoint
- `DATABASE_URL` - Agent database (default: sqlite:///./data/agent.db)
- `COMPANY_DATABASE_URL` - Company database
- `API_HOST`, `API_PORT` - API binding
- `LOG_LEVEL`, `*_LOG_FILE` - Logging configuration

**Secrets location:**
- `.env` file (not committed, `.env.example` provides template)
- Docker Compose environment section

## Webhooks & Callbacks

**Incoming:**
- HTTP POST endpoints (`src/core/api/controllers/`):
  - `POST /jobs/search` - Trigger job search workflow
  - `POST /jobs/apply` - Trigger job applications
  - `POST /outreach/search` - Trigger employee search
  - `POST /outreach/send` - Trigger outreach messages

**Outgoing:**
- Kafka topics (event stream):
  - `job-results` - Job search and application results
  - `outreach-results` - Message send results
  - `outreach-search-results` - Employee search results
  - `mcp-search-complete` - MCP search completion signal
  - Config location: `src/core/queue/config.py`
  - Producer: `src/core/queue/producer.py` (confluent-kafka)

## Message Broker (Kafka)

**Configuration:**
- Bootstrap servers: `KAFKA_BOOTSTRAP_SERVERS` env var (default: localhost:9092)
- Mode: KRaft (no Zookeeper required)
- Topics: Auto-created at startup via `src/core/queue/config.py::ensure_topics()`
- Message format: JSON (Pydantic model serialization)
- Batching: 32KB batch size, 10ms linger time

**Integration Points:**
- Core Agent publishes results after workflow completion (`src/core/queue/producer.py`)
- CLI consumes results from Kafka topics
- MCP Server publishes search completion signals

## Browser Automation

**WebDriver:**
- Selenium 4.15.0 with undetected-chromedriver 3.5.0
- Chrome version: Configurable (default: 143, env var `CHROME_VERSION`)
- Anti-detection: Fake user agents, automation flag removal
- Service: `src/linkedin_mcp/services/browser_manager_service.py`
- Features:
  - Single session reuse across multiple operations
  - Headless/headed modes configurable
  - Automatic cleanup on exit/shutdown
  - Xvfb display support for headless Linux

## Data Processing

**PDF Extraction:**
- pdfplumber 0.10.0 (primary)
- pypdf 5.0.0 (fallback)
- Location: `src/core/agents/tools/cv_analysis_tools.py::read_pdf_cv()`

**HTML Parsing:**
- BeautifulSoup4 4.12.0
- Used for: Job description extraction, page scraping

**CSV Import:**
- pandas 2.2.0
- Company dataset loading for outreach targeting

---

*Integration audit: 2026-02-11*
