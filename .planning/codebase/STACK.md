# Technology Stack

**Analysis Date:** 2026-02-11

## Languages

**Primary:**
- Python 3.12 - Entire application codebase, CLI, agents, MCP server

## Runtime

**Environment:**
- Python 3.12.x (via Poetry)

**Package Manager:**
- Poetry 1.x
- Lockfile: `poetry.lock` (present, 596KB)

## Frameworks

**Core:**
- FastAPI 0.115.0 - REST API for core agent (`src/core/api/app.py`)
- LangGraph 0.6.7 - Workflow orchestration for job application and outreach agents (`src/core/agent.py`, `src/core/agents/outreach_agent.py`)
- LangChain 0.3.27 - LLM prompting and tool integration
- FastMCP 2.12.3 - Model Context Protocol server for LinkedIn automation (`src/linkedin_mcp/linkedin_server.py`)

**Testing:**
- pytest 9.0.2 - Unit and integration test framework (`tests/` directory)

**Build/Dev:**
- setuptools 80.9.0 - Python packaging
- pre-commit 4.3.0 - Git hooks management (`.pre-commit-config.yaml`)
- black 25.9.0 - Code formatting
- isort 6.0.1 - Import sorting
- basedpyright 1.37.2 - Static type checking (`pyrightconfig.json`)

## Key Dependencies

**Critical:**
- langchain-openai 0.3.0 - OpenAI-compatible LLM client wrapper (`src/core/providers/llm_client.py`)
- selenium 4.15.0 - WebDriver for LinkedIn browser automation
- undetected-chromedriver 3.5.0 - Anti-detection Chrome driver for avoiding LinkedIn blocks (`src/linkedin_mcp/services/browser_manager_service.py`)
- beautifulsoup4 4.12.0 - HTML parsing for job descriptions
- confluent-kafka 2.6.0 - Kafka producer/admin client for message publishing (`src/core/queue/producer.py`)
- sqlalchemy 2.0.0 - ORM for database persistence (`src/core/db/agent_db.py`)
- alembic 1.13.0 - Database migrations (`alembic.ini`, `alembic/` directory)

**Infrastructure:**
- fastapi 0.115.0 - HTTP framework
- uvicorn 0.37.0 - ASGI web server
- pydantic 2.0.0 - Data validation and settings management
- loguru 0.7.0 - Structured logging (`src/core/utils/logging_config.py`)

**Browser & Web Scraping:**
- webdriver-manager 4.0.0 - Automatic ChromeDriver version management
- fake-useragent 1.4.0 - User-agent rotation for anti-detection
- requests 2.31.0 - HTTP client
- httpx 0.28.1 - Async HTTP client
- websockets 14.0+ - WebSocket support

**Document Processing:**
- pdfplumber 0.10.0 - PDF text extraction (primary)
- pypdf 5.0.0 - Fallback PDF reader (`src/core/agents/tools/cv_analysis_tools.py`)
- lxml 4.9.0 - XML/HTML processing (BeautifulSoup dependency)

**Data & Configuration:**
- pyyaml 6.0.0 - YAML config file parsing (`config/agent.yaml`)
- pandas 2.2.0 - Data processing
- python-dotenv 1.0.0 - Environment variable loading

**CLI & UX:**
- click 8.1.0 - Command-line interface helpers
- typer 0.15.0 - Modern CLI framework (`src/cli/client.py`)
- rich 13.7.0 - Rich terminal output

**Observability:**
- langfuse 2.0.0 - Tracing and monitoring (optional, requires env vars) (`src/core/observability/langfuse_config.py`)

## Configuration

**Environment:**
Configured via:
1. `.env` file (secrets, see `.env.example`)
2. `config/agent.yaml` (service configuration)
3. Environment variables override both

**Key Environment Variables:**
- `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD` - LinkedIn credentials
- `HUGGING_FACE_HUB_TOKEN` - HF Serverless API token (optional for embeddings)
- `LANGFUSE_*` - Optional observability credentials
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka broker address (default: localhost:9092)
- `MCP_SERVER_HOST`, `MCP_SERVER_PORT` - LinkedIn MCP server location
- `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_API_KEY` - Local LLM inference server (llama.cpp compatible)
- `DATABASE_URL` - Agent database (default: sqlite:///./data/agent.db)
- Database URLs: `DATABASE_URL`, `COMPANY_DATABASE_URL`
- API: `API_HOST`, `API_PORT` (default: 0.0.0.0:8080)
- Logging: `LOG_LEVEL`, `LOG_FILE`, `CORE_AGENT_LOG_LEVEL`, `LINKEDIN_MCP_LOG_LEVEL`

**Build:**
- Docker: `Dockerfile.agent`, `Dockerfile.mcp-server` (multi-stage builds)
- Docker Compose: `docker-compose.yml` (Kafka, Core Agent, LinkedIn MCP Server)
- SQLAlchemy config in `src/core/db/engine.py` (SQLite with WAL mode, connection pooling)

## Platform Requirements

**Development:**
- Python 3.12+
- Chrome/Chromium browser (tested on 143)
- Linux/macOS/Windows (Docker recommended for full stack)
- 2GB+ RAM for browser automation

**Production:**
- Docker + Docker Compose
- Linux container runtime (headless Chrome support)
- Kafka 7.7.0 (KRaft mode, no Zookeeper)
- SQLite or compatible SQL database
- Local LLM server (e.g., llama.cpp on port 8088) or OpenAI-compatible API

**Memory & Resources:**
- Core Agent: 2GB memory limit, 1GB reservation (docker-compose)
- LinkedIn MCP Server: 2GB limit, 1GB reservation
- Kafka: 1GB limit

---

*Stack analysis: 2026-02-11*
