# Architecture

**Analysis Date:** 2026-02-11

## Pattern Overview

**Overall:** Distributed agentic system with LangGraph-based orchestration, microservice API layer, MCP protocol bridge, and RPA (Robotic Process Automation) browser automation.

**Key Characteristics:**
- LangGraph workflows orchestrate multi-stage agent pipelines
- Model Context Protocol (MCP) enables tool abstraction layer between agents and LinkedIn interactions
- FastAPI REST API provides external workflow submission (async task-based)
- Kafka message broker decouples async task completion from API responses
- Selenium WebDriver automation for LinkedIn interaction (RPA)
- SQLAlchemy ORM for persistent state and historical tracking
- Thread pool execution model for bounded concurrency control

## Layers

**API Layer (REST/HTTP):**
- Purpose: Expose workflow submission endpoints for external clients; handle synchronous request/asynchronous processing pattern
- Location: `src/core/api/`
- Contains: FastAPI application factory, route controllers, request/response schemas
- Depends on: Services layer, Kafka producer, database
- Used by: External clients, orchestration systems

**Service Layer (Business Logic):**
- Purpose: Coordinate workflow submission, thread pool management, and Kafka publishing
- Location: `src/core/api/services/`
- Contains: `JobService`, `OutreachService`, `SessionStore` - manage task lifecycle and messaging
- Depends on: Agent layer, Kafka producer, database
- Used by: API controllers, background tasks

**Agent Layer (Orchestration):**
- Purpose: Implement LangGraph workflows that compose steps into multi-stage pipelines
- Location: `src/core/agents/` (core job application logic), `src/linkedin_mcp/agents/` (MCP-specific agents)
- Contains: `JobApplicationAgent` (search→filter→apply flow), `EmployeeOutreachAgent` (search employees→send messages)
- Depends on: MCP client, LLM provider, tools, database, queue consumer
- Used by: Service layer via `_run()` methods

**Graph/Workflow Layer (State Machines):**
- Purpose: Define task graph DAGs with conditional edges and state transitions
- Location: `src/core/agents/` (core), `src/linkedin_mcp/graphs/` (MCP-specific)
- Contains: LangGraph `StateGraph` instances compiled into DAGs (job search, job application, employee search, message sending)
- Depends on: State models, node implementation functions
- Used by: Agents, graph initialization

**Provider Layer (External Integration):**
- Purpose: Abstract communication with external systems (LinkedIn MCP server, LLM APIs, Kafka)
- Location: `src/core/providers/` and `src/linkedin_mcp/providers/`
- Contains:
  - `LinkedInMCPClient`/`LinkedInMCPClientSync` - HTTP/stdio transport to MCP server
  - `llm_client` - LangChain LLM factory (OpenAI, HuggingFace)
  - `KafkaResultProducer`/`KafkaResultConsumer` - Kafka topic access
- Depends on: Configuration, external libraries (fastmcp, confluent-kafka, langchain)
- Used by: Agents, services

**MCP Server Layer (RPA Tool Bridge):**
- Purpose: Implement LinkedIn automation tools as MCP-compliant endpoints; manage browser sessions
- Location: `src/linkedin_mcp/`
- Contains: `linkedin_server.py` (FastMCP server), service implementations, tool registration
- Services inside:
  - `JobSearchService` - search jobs via RPA
  - `JobApplicationService` - apply to jobs via RPA
  - `EmployeeOutreachService` - search employees, send messages via RPA
- Depends on: Selenium WebDriver, graph implementations, browser manager
- Used by: Core agents via MCP client

**Database Layer (Persistence):**
- Purpose: Persist workflow state, search results, application history, and session data
- Location: `src/core/db/`
- Contains:
  - `models.py` - SQLAlchemy ORM models (JobApplication, MessageSent, SearchResult, Company, DailyQuota, SessionModel)
  - `engine.py` - connection and session factory
  - `agent_db.py` - query interface
- Depends on: SQLAlchemy, configuration
- Used by: Services, agents, database consumers

**Queue Layer (Event Distribution):**
- Purpose: Publish and consume async task results; decouple API from completion
- Location: `src/core/queue/`
- Contains:
  - `producer.py` - KafkaResultProducer for publishing task results
  - `consumer.py` - KafkaResultConsumer for listening to completions
  - `config.py` - topic definitions, Kafka configuration
  - `schemas.py` - Kafka message formats
- Depends on: Kafka broker, Pydantic
- Used by: Services, agents

**Configuration Layer (Environment & Settings):**
- Purpose: Load and validate application configuration from environment
- Location: `src/config/`
- Contains: `config_loader.py` (Pydantic BaseSettings), `trace_context.py` (contextvars for distributed tracing)
- Depends on: Environment variables, Python standard library
- Used by: All layers

**Utilities & Tools Layer:**
- Purpose: Shared helper functions and domain tools
- Location: `src/core/utils/`, `src/core/agents/tools/`, `src/linkedin_mcp/agents/tools/`
- Contains:
  - Logging configuration
  - CV analysis and parsing tools
  - Message templating
  - Browser management interfaces
  - LLM-based job filtering and form handling
- Used by: Agents, graphs, services

## Data Flow

**Job Application Workflow (Primary Flow):**

1. **Submission** - Client POSTs `JobApplyRequest` to `POST /api/jobs/apply`
2. **Service Validation** - `JobService.submit()` validates request, generates `task_id`, submits to thread pool
3. **Agent Execution** - `JobApplicationAgent.run()` initializes LangGraph and invokes workflow
4. **Workflow Steps:**
   - `search_jobs_node` - calls `LinkedInMCPClientSync.search_jobs()` → MCP server → Selenium RPA
   - Returns: List of `JobResult` objects with job details
   - `filter_jobs_node` - calls LLM to analyze CV vs job requirements using `ChatPromptTemplate`
   - Returns: Filtered jobs matching CV skills/experience
   - `apply_to_jobs_node` - calls `LinkedInMCPClientSync.apply_to_jobs()` → MCP server → Easy Apply forms
   - Returns: List of `ApplicationResult` with success/failure per job
5. **Result Publishing** - Agent result published to Kafka topic `job_results` via `KafkaResultProducer`
6. **Client Polling** - External client polls Kafka or `GET /api/jobs/{task_id}` for completion

**State Management:**

- **State Objects:** Defined as `TypedDict` for type safety
  - `JobApplicationAgentState` - job search, filter, apply state
  - `JobSearchState` - pagination, URL building, job collection
  - `JobApplicationState` - per-job application loop state
- **State Threading:** Passed through graph nodes; each node returns updated dict
- **Persistence:** State snapshots optionally saved to database via `AgentDB`
- **Cleanup:** Session data auto-expired via `SessionStore` TTL mechanism (3600s default)

**Outreach Workflow (Secondary Flow):**

1. **Search Phase:**
   - `OutreachService.run_search()` → `EmployeeOutreachAgent.run_search_only()`
   - Searches employees at multiple companies via MCP
   - Results published to `outreach_search_results` topic
   - Stored in `SearchResult` table with `batch_id` for tracking

2. **Send Phase:**
   - `OutreachService.run_send()` → `EmployeeOutreachAgent.run_send()`
   - Sends personalized messages per employee using per-employee templates
   - Results published to `outreach_results` topic
   - Stored in `MessageSent` table tracking success/error

## Key Abstractions

**LangGraph StateGraph:**
- Purpose: Declare workflow DAG as Python objects, compile to deterministic execution engine
- Examples: `src/core/agents/` agents, `src/linkedin_mcp/graphs/` graphs
- Pattern: Define states (TypedDict), add nodes (functions), define edges (deterministic/conditional), compile()

**MCP Tool Protocol:**
- Purpose: Standardize agent-to-tool communication; decouple agent logic from implementation
- Examples: `search_jobs`, `easy_apply_for_jobs`, `search_employees`, `send_messages_batch`
- Pattern: FastMCP server registers tools; clients discover and call via JSON-RPC over HTTP/stdio

**Provider Pattern:**
- Purpose: Abstract external dependencies (LLM, Kafka, MCP) for testability and swappability
- Examples: `LinkedInMCPClient`, `llm_client()`, `KafkaResultProducer`
- Pattern: Factory functions or classes encapsulating instantiation and configuration

**Session Store:**
- Purpose: Cache browser sessions and workflow state across requests
- Examples: `SessionStore` in `src/core/api/services/`
- Pattern: TTL-based in-memory cache with SQLAlchemy backend for persistence

**Interface Abstractions:**
- `IBrowserManager` - abstraction over Selenium WebDriver for browser lifecycle
- `IJobApplicationAgent` - contract for job application implementations
- `IJobApplicationService` - contract for job application service implementations
- Location: `src/linkedin_mcp/interfaces/`

## Entry Points

**HTTP API Server:**
- Location: `src/core/api/app.py`
- Triggers: `uvicorn src.core.api.app:app --host 0.0.0.0 --port 8000`
- Responsibilities:
  - Lifespan context manager initializes database, Kafka producer, session store
  - Routes POST `/api/jobs/apply` and `/api/outreach/...` to controllers
  - Ensures Kafka topics exist at startup
  - Cleans up resources on shutdown

**MCP Server:**
- Location: `src/linkedin_mcp/linkedin_server.py`
- Triggers: Run as subprocess via FastMCP stdio transport or HTTP endpoint
- Responsibilities:
  - Registers MCP tools for job search, job application, employee search, message sending
  - Manages browser lifecycle per tool execution
  - Handles RPA-specific errors (timeouts, stale elements)
  - Publishes search results to Kafka

**CLI Entry Point:**
- Location: `src/main.py`
- Triggers: `python src/main.py`
- Responsibilities:
  - Demonstrates standalone workflow execution
  - Loads LinkedIn credentials and CV data from files/env
  - Invokes `JobApplicationAgent` and reports results

## Error Handling

**Strategy:** Graceful degradation with context propagation

**Patterns:**

1. **Node-Level Try/Catch:**
   ```python
   def search_jobs_node(self, state: JobApplicationAgentState):
       try:
           # operation
       except Exception as e:
           # append to state["errors"]
           return {...state, "errors": [..., error_msg]}
   ```
   - Nodes catch exceptions and return updated state
   - Workflow continues; errors accumulated in state
   - Critical errors can short-circuit via conditional edges

2. **Service-Level Wrapping:**
   ```python
   try:
       result = agent.run(...)
       response = JobApplyResponse(...result)
   except Exception as e:
       response = JobApplyResponse(..., status=f"failed: {e}")
   ```
   - Services wrap agents; catch unhandled exceptions
   - Return error response to Kafka

3. **Logging & Observability:**
   - `loguru` used throughout for structured logging
   - `trace_id` (UUID) passed through contextvars for request tracing
   - `langfuse` integration for LangChain observability (traces, tokens)
   - Logs include task_id, trace_id for correlation

4. **Timeout Handling:**
   - Selenium WebDriver uses `WebDriverWait(timeout=30)` for element waits
   - Job searches limited by page count or timeout
   - MCP tool calls inherit client timeout from config

5. **Resource Cleanup:**
   - Browser sessions closed via `BrowserManagerService.cleanup()`
   - Thread pool shutdown via `atexit` handlers
   - Kafka producer flushed before exit

## Cross-Cutting Concerns

**Logging:** Handled via `loguru` with context-aware output
- Configure via `src/core/utils/logging_config.py`
- Structured fields: `trace_id`, `task_id`, `stage`
- Levels: INFO for workflow progress, ERROR for failures, DEBUG for timing

**Validation:** Handled via Pydantic models
- Request schemas in `src/core/api/schemas/`
- State models as TypedDict with typed fields
- Database models as SQLAlchemy declaratives
- Validation on instantiation; raises ValidationError on mismatch

**Authentication:** Handled per workflow
- LinkedIn credentials (email, password) passed in request
- Credentials used by MCP server to login during RPA
- No centralized auth service; credentials ephemeral

**Observability/Tracing:**
- Trace context via `contextvars` in `src/config/trace_context.py`
- `trace_id` (UUID) set at service layer, propagated to MCP calls
- Langfuse integration traces LLM calls in filtering step
- Kafka message headers include trace_id for end-to-end correlation

**Concurrency:**
- API uses async FastAPI endpoint with thread pool executor
- Thread pool bounded to 4 workers to prevent resource exhaustion
- Thread safety via immutable state passing in graph nodes
- Browser sessions isolated per thread (no sharing)

---

*Architecture analysis: 2026-02-11*
