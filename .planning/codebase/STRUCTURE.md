# Codebase Structure

**Analysis Date:** 2026-02-11

## Directory Layout

```
serial-linkedin-killer/
├── src/                          # Main application source code
│   ├── __init__.py              # Package exports (JobApplicationAgent, CVAnalysis, etc.)
│   ├── main.py                  # CLI entry point for standalone execution
│   ├── config/                  # Application configuration and context
│   │   ├── config_loader.py     # Pydantic BaseSettings for env vars
│   │   └── trace_context.py     # contextvars for distributed tracing
│   ├── core/                    # Core agent and API implementation
│   │   ├── agent.py             # JobApplicationAgent - main orchestrator
│   │   ├── api/                 # REST API layer
│   │   │   ├── app.py           # FastAPI app factory and lifespan
│   │   │   ├── controllers/     # Route handlers
│   │   │   │   ├── job_controller.py     # POST /api/jobs/apply
│   │   │   │   └── outreach_controller.py # Outreach endpoints
│   │   │   ├── services/        # Business logic orchestration
│   │   │   │   ├── job_service.py        # JobService - workflow submission
│   │   │   │   ├── outreach_service.py   # OutreachService - multi-phase
│   │   │   │   └── session_store.py      # SessionStore - TTL caching
│   │   │   └── schemas/         # Pydantic models for validation
│   │   │       ├── job_schemas.py        # JobApplyRequest, JobApplyResponse
│   │   │       ├── outreach_schemas.py   # OutreachRunRequest, etc.
│   │   │       └── common.py             # TaskResponse, shared models
│   │   ├── agents/              # LangGraph agents (core logic)
│   │   │   ├── outreach_agent.py # EmployeeOutreachAgent - search/send workflow
│   │   │   └── tools/           # Tool implementations and utilities
│   │   │       ├── cv_analysis_tools.py  # PDF parsing, CV analysis
│   │   │       ├── cv_loader.py          # CV data extraction
│   │   │       ├── message_template.py   # Jinja2 template rendering
│   │   │       ├── role_clustering.py    # K-means employee role grouping
│   │   │       └── company_db.py         # Company database queries
│   │   ├── db/                  # Database layer
│   │   │   ├── models.py        # SQLAlchemy ORM (JobApplication, MessageSent, etc.)
│   │   │   ├── engine.py        # Connection/session factory
│   │   │   └── agent_db.py      # Query interface
│   │   ├── model/               # State and data models
│   │   │   ├── job_application_agent_state.py # JobApplicationAgentState TypedDict
│   │   │   ├── application_request.py    # ApplicationRequest alias
│   │   │   ├── application_result.py     # ApplicationResult fields
│   │   │   ├── job_result.py             # JobResult alias
│   │   │   ├── job_search_request.py     # JobSearchRequest alias
│   │   │   ├── cv_analysis.py            # CVAnalysis - experience, skills, roles
│   │   │   ├── outreach_state.py         # OutreachAgentState - search/send state
│   │   │   └── __init__.py               # Model exports
│   │   ├── providers/           # External service abstractions
│   │   │   ├── linkedin_mcp_client.py # LinkedInMCPClient - async HTTP transport
│   │   │   ├── linkedin_mcp_client_sync.py # LinkedInMCPClientSync - sync wrapper
│   │   │   └── llm_client.py    # get_llm_client() factory
│   │   ├── queue/               # Kafka message layer
│   │   │   ├── producer.py      # KafkaResultProducer - publish results
│   │   │   ├── consumer.py      # KafkaResultConsumer - listen for events
│   │   │   ├── config.py        # Topic definitions, broker config
│   │   │   └── schemas.py       # Pydantic messages (MCPSearchComplete, etc.)
│   │   ├── observability/       # Observability integrations
│   │   │   └── langfuse_config.py # Langfuse setup for LLM tracing
│   │   └── utils/               # Shared utilities
│   │       └── logging_config.py # Loguru configuration
│   ├── cli/                     # Command-line interface (if used)
│   ├── linkedin_mcp/            # MCP Server implementation (LinkedIn automation)
│   │   ├── linkedin_server.py   # FastMCP server entry point
│   │   ├── agents/              # MCP-specific agents (agent implementation)
│   │   │   ├── easy_apply_agent.py # EasyApplyAgent - form filling logic
│   │   │   └── tools/           # MCP tool definitions
│   │   │       ├── job_tools.py # search_jobs, easy_apply_for_jobs
│   │   │       ├── employee_tools.py # search_employees, search_employees_batch
│   │   │       └── __init__.py  # register_all_tools() function
│   │   ├── graphs/              # LangGraph workflows (RPA state machines)
│   │   │   ├── job_search_graph.py      # JobSearchGraph - URL build, navigate, extract
│   │   │   ├── job_application_graph.py # JobApplicationGraph - per-job application loop
│   │   │   ├── employee_search_graph.py # EmployeeSearchGraph - employee extraction
│   │   │   ├── message_send_graph.py    # MessageSendGraph - message composition/sending
│   │   │   └── linkedin_auth_graph.py   # LinkedInAuthGraph - login workflow
│   │   ├── services/            # MCP service implementations
│   │   │   ├── job_search_service.py       # JobSearchService - graph orchestration
│   │   │   ├── job_application_service.py  # JobApplicationService
│   │   │   └── employee_outreach_service.py # EmployeeOutreachService
│   │   ├── model/               # MCP-specific state models
│   │   │   ├── job_search_state.py # JobSearchState TypedDict
│   │   │   ├── types.py         # JobResult, ApplicationResult, CVAnalysis
│   │   │   └── ...
│   │   ├── interfaces/          # Service contracts
│   │   │   ├── services.py      # IBrowserManager, IJobApplicationService
│   │   │   └── agents.py        # IJobApplicationAgent
│   │   ├── providers/           # Selenium and browser management
│   │   │   └── browser_manager_service.py # BrowserManagerService singleton
│   │   ├── observability/       # Logging/tracing for MCP
│   │   │   └── langfuse_config.py
│   │   └── utils/               # MCP utilities
│   │       └── logging_config.py # MCP-specific logging setup
│   └── ...
├── tests/                       # Test suite
│   ├── test_job_application.py  # Integration tests for job workflow
│   ├── test_search_jobs.py      # Job search tests
│   ├── test_outreach.py         # Outreach workflow tests
│   ├── test_cv_json_integration.py # CV parsing tests
│   ├── test_message_send_graph.py  # Message sending tests
│   └── data/                    # Test fixtures
│       └── cv_analysis.json     # Sample CV analysis output
├── alembic/                     # Database migrations
│   └── versions/                # Migration scripts
├── config/                      # Configuration files (YAML, env examples)
├── docs/                        # Documentation and diagrams
│   └── diagrams/                # Architecture diagrams
├── scripts/                     # Utility scripts
├── assets/                      # Static assets
├── pyproject.toml               # Poetry dependencies and metadata
├── poetry.lock                  # Locked dependency versions
├── alembic.ini                  # Alembic configuration
├── pyrightconfig.json           # Type checking configuration
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .env.example                 # Environment variable template
├── Dockerfile.agent             # Agent container image
├── Dockerfile.mcp-server        # MCP server container image
├── docker-compose.yml           # Multi-container orchestration
└── README.md                    # Project overview
```

## Directory Purposes

**src/**
- Purpose: All application code, organized by domain and responsibility
- Contains: Main agents, API, MCP server, database, queue, utilities
- Key files: `main.py` (CLI), `core/agent.py` (core orchestrator), `linkedin_mcp/linkedin_server.py` (MCP)

**src/config/**
- Purpose: Environment and application configuration
- Contains: Pydantic BaseSettings loader, contextvars for tracing
- Key files: `config_loader.py` (env parsing), `trace_context.py` (trace_id management)

**src/core/**
- Purpose: Core agent logic, API, and supporting infrastructure
- Contains: Agents, API, database, queue, models, providers
- Key files: `agent.py` (JobApplicationAgent), `api/app.py` (FastAPI factory)

**src/core/api/**
- Purpose: HTTP REST API for external workflow submission
- Contains: Controllers, services, schemas
- Key files: `app.py` (FastAPI entry), controllers (route handlers), services (business logic)

**src/core/agents/**
- Purpose: LangGraph agents and tools for core workflows
- Contains: `EmployeeOutreachAgent`, CV analysis tools, company database tools
- Key files: `outreach_agent.py` (outreach orchestration), `tools/` (domain tools)

**src/core/db/**
- Purpose: Database persistence layer with SQLAlchemy ORM
- Contains: Models (JobApplication, MessageSent, Company, SearchResult), engine, query interface
- Key files: `models.py` (ORM definitions), `agent_db.py` (query wrapper)

**src/core/model/**
- Purpose: Type-safe state and data models (TypedDict, Pydantic)
- Contains: JobApplicationAgentState, CVAnalysis, JobResult, ApplicationResult, OutreachState
- Key files: All are small model definitions; `__init__.py` exports public types

**src/core/providers/**
- Purpose: Abstractions for external services (MCP client, LLM, Kafka)
- Contains: MCP client (async and sync), LLM factory, Kafka producer
- Key files: `linkedin_mcp_client_sync.py` (core MCP integration), `llm_client.py` (LLM factory)

**src/core/queue/**
- Purpose: Kafka-based async messaging for workflow results
- Contains: Producer, consumer, topic config, message schemas
- Key files: `producer.py` (publish results), `config.py` (topic definitions)

**src/linkedin_mcp/**
- Purpose: MCP Server implementation; handles LinkedIn automation via RPA
- Contains: Server, agents, graphs, services, browser management
- Key files: `linkedin_server.py` (FastMCP entry), graphs (state machines), services (orchestration)

**src/linkedin_mcp/graphs/**
- Purpose: LangGraph state machines for RPA workflows
- Contains: JobSearchGraph, JobApplicationGraph, EmployeeSearchGraph, MessageSendGraph
- Key files: Each graph implements browser automation steps as nodes

**src/linkedin_mcp/agents/tools/**
- Purpose: MCP tool implementations registered as callable endpoints
- Contains: search_jobs, easy_apply_for_jobs, search_employees, send_messages_batch
- Key files: `job_tools.py`, `employee_tools.py`

**tests/**
- Purpose: Integration and end-to-end test suite
- Contains: Test cases for job application, search, outreach, CV parsing
- Key files: Test file per major workflow (`test_job_application.py`, `test_outreach.py`)

**alembic/**
- Purpose: Database schema versioning and migrations
- Contains: Migration scripts for schema changes
- Key files: `versions/` contains timestamped migration files

## Key File Locations

**Entry Points:**
- `src/main.py`: Standalone CLI for job application workflow
- `src/core/api/app.py`: HTTP API server (FastAPI)
- `src/linkedin_mcp/linkedin_server.py`: MCP server for LinkedIn RPA tools

**Configuration:**
- `src/config/config_loader.py`: Environment variable schema and defaults
- `pyproject.toml`: Python dependencies and project metadata
- `.env.example`: Example environment variables
- `alembic.ini`: Database migration tool config

**Core Logic:**
- `src/core/agent.py`: JobApplicationAgent - main orchestration (search→filter→apply)
- `src/core/agents/outreach_agent.py`: EmployeeOutreachAgent - outreach workflows
- `src/linkedin_mcp/linkedin_server.py`: MCP server and tool registration

**API/Controllers:**
- `src/core/api/controllers/job_controller.py`: POST /api/jobs/apply endpoint
- `src/core/api/controllers/outreach_controller.py`: Outreach endpoints
- `src/core/api/services/job_service.py`: JobService - task submission and execution
- `src/core/api/services/outreach_service.py`: OutreachService - outreach orchestration

**Database:**
- `src/core/db/models.py`: SQLAlchemy ORM (all tables)
- `src/core/db/agent_db.py`: Query wrapper and interface
- `src/core/db/engine.py`: Connection and session factory
- `alembic/versions/`: Migration scripts

**State & Models:**
- `src/core/model/job_application_agent_state.py`: JobApplicationAgentState (main workflow state)
- `src/core/model/outreach_state.py`: OutreachAgentState (outreach workflow state)
- `src/linkedin_mcp/model/job_search_state.py`: JobSearchState (RPA search state)

**Tools & Utilities:**
- `src/core/agents/tools/cv_analysis_tools.py`: CV parsing and analysis
- `src/core/agents/tools/cv_loader.py`: CV data extraction from JSON
- `src/core/agents/tools/message_template.py`: Jinja2 template rendering
- `src/core/agents/tools/role_clustering.py`: Employee role grouping (K-means)
- `src/linkedin_mcp/agents/tools/job_tools.py`: Job search and application MCP tools
- `src/linkedin_mcp/agents/tools/employee_tools.py`: Employee search MCP tools

**Messaging:**
- `src/core/queue/producer.py`: KafkaResultProducer - publish results
- `src/core/queue/consumer.py`: KafkaResultConsumer - listen for events
- `src/core/queue/config.py`: Kafka broker config and topic names

**Observability:**
- `src/core/observability/langfuse_config.py`: Langfuse integration for LLM tracing
- `src/core/utils/logging_config.py`: Loguru structured logging setup
- `src/config/trace_context.py`: Distributed trace ID management

**Interfaces:**
- `src/linkedin_mcp/interfaces/services.py`: IBrowserManager, IJobApplicationService, IEmployeeOutreachService
- `src/linkedin_mcp/interfaces/agents.py`: IJobApplicationAgent

## Naming Conventions

**Files:**
- `*_agent.py`: LangGraph agent implementations (e.g., `outreach_agent.py`)
- `*_graph.py`: LangGraph state machine definitions (e.g., `job_search_graph.py`)
- `*_service.py`: Business logic orchestrators (e.g., `job_service.py`)
- `*_controller.py`: FastAPI route handlers (e.g., `job_controller.py`)
- `*_schemas.py`: Pydantic request/response models (e.g., `job_schemas.py`)
- `*_tools.py`: Tool implementations or utilities (e.g., `cv_analysis_tools.py`)
- `*_state.py`: TypedDict state models (e.g., `job_search_state.py`)
- `*_config.py`: Configuration or setup modules (e.g., `langfuse_config.py`)

**Directories:**
- `agents/`: LangGraph agent classes and tool implementations
- `graphs/`: LangGraph StateGraph definitions (RPA workflows)
- `services/`: Service layer with business logic
- `controllers/`: HTTP route handlers
- `schemas/`: Pydantic models for validation
- `tools/`: Utility tools and domain logic
- `providers/`: External service abstractions
- `queue/`: Kafka producer/consumer and messaging
- `model/`: State and data models
- `db/`: Database layer (ORM, engine, queries)
- `interfaces/`: Service and agent contracts (ABC)
- `observability/`: Logging and tracing setup
- `utils/`: Shared utilities and helpers

**Functions/Classes:**
- Classes use PascalCase: `JobApplicationAgent`, `KafkaResultProducer`
- Functions use snake_case: `search_jobs()`, `get_llm_client()`
- State models use PascalCase: `JobApplicationAgentState`, `JobSearchState`
- Private/internal use leading underscore: `_build_graph()`, `_run()`

## Where to Add New Code

**New Feature (e.g., add resume optimization):**
- Implementation: `src/core/agents/tools/` or `src/linkedin_mcp/agents/tools/`
  - Example: `src/core/agents/tools/resume_optimization.py`
- If requires new API endpoint:
  - Controller: `src/core/api/controllers/` (new file or add route to existing)
  - Schema: `src/core/api/schemas/` (extend existing or new file)
  - Service: `src/core/api/services/` (extend existing or new service class)
- If requires new workflow graph:
  - Graph: `src/linkedin_mcp/graphs/resume_graph.py`
  - Agent: Add node to existing agent or create new in `src/core/agents/`
- Tests: `tests/test_resume_optimization.py`

**New Component/Module (e.g., add LinkedIn recruiter outreach):**
- Agent: `src/core/agents/recruiter_outreach_agent.py`
- Database models: Add to `src/core/db/models.py`
- MCP tools: `src/linkedin_mcp/agents/tools/recruiter_tools.py`
- Graph: `src/linkedin_mcp/graphs/recruiter_outreach_graph.py`
- Service: `src/core/api/services/recruiter_service.py`
- Controller: `src/core/api/controllers/recruiter_controller.py`
- Schemas: `src/core/api/schemas/recruiter_schemas.py`
- Tests: `tests/test_recruiter_outreach.py`

**New Utility/Helper (e.g., add company validation):**
- Shared helpers: `src/core/utils/company_validator.py` or `src/core/agents/tools/`
- If used by RPA: `src/linkedin_mcp/utils/` or `src/linkedin_mcp/agents/tools/`
- Example: `src/core/agents/tools/company_validation.py`

**New Tool/Integration:**
- MCP tool: Implement in `src/linkedin_mcp/agents/tools/` and register in `register_all_tools()`
- Service integration: `src/core/providers/` (e.g., `slack_notification.py`)
- Database integration: Add model to `src/core/db/models.py`, migration in `alembic/versions/`

**New Workflow Graph:**
- Location: `src/linkedin_mcp/graphs/{feature}_graph.py` (RPA-specific)
  - Or `src/core/agents/` (core agent logic)
- Pattern: Subclass or instantiate `StateGraph`, define state TypedDict, add nodes, compile()
- Register in: Agent that uses it or service that orchestrates it

**Testing:**
- Unit tests: `tests/test_{feature}.py`
- Fixtures: `tests/data/` for JSON test data
- Mocks: Use pytest fixtures, mock Kafka/MCP calls

## Special Directories

**alembic/**
- Purpose: Database schema versioning using Alembic
- Generated: Yes (migration scripts auto-created by `alembic revision --autogenerate`)
- Committed: Yes, all migrations tracked in git
- Run: `alembic upgrade head` to apply migrations

**tests/data/**
- Purpose: Test fixtures and example data
- Generated: No (manually created)
- Committed: Yes
- Usage: Reference in tests via `tests/data/cv_analysis.json`

**.env (not committed)**
- Purpose: Runtime environment variables
- Generated: Yes (template: `.env.example`)
- Committed: No (security: contains secrets)
- Must be created locally from `.env.example`

**docs/diagrams/**
- Purpose: Architecture and workflow diagrams
- Generated: No (manually created)
- Committed: Yes
- Format: Markdown, PlantUML, or diagram tools

**alembic/versions/**
- Purpose: Timestamped database migration scripts
- Generated: Yes (via `alembic revision`)
- Committed: Yes, critical for schema consistency
- Format: Python files with upgrade() and downgrade() functions

**poetry.lock**
- Purpose: Locked dependency versions for reproducible builds
- Generated: Yes (via `poetry lock`)
- Committed: Yes, ensures consistent environments
- Update: `poetry update` or `poetry add new-package`

---

*Structure analysis: 2026-02-11*
