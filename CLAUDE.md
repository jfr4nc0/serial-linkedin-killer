# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated LinkedIn job application system using AI-powered form filling and job filtering. Three-phase workflow: search jobs on LinkedIn → filter by CV alignment using LLM → auto-complete Easy Apply forms.

## Commands

```bash
# Install dependencies
poetry install

# Run (interactive mode)
python job_applier.py run --interactive

# Run with config
python job_applier.py run --config ./config.yaml

# Other CLI commands
python job_applier.py init              # Create config file
python job_applier.py validate          # Validate config
python job_applier.py test-connection   # Test MCP server connection

# Run MCP server standalone
python -m linkedin_mcp.linkedin.linkedin_server --http --host localhost --port 8000

# Tests
python -m pytest tests/

# Docker
docker-compose up -d
```

## Architecture

```
CLI (Typer/Rich) → Core Agent (LangGraph) → LinkedIn MCP Server (FastMCP/HTTP) → Services (Selenium/LLM)
```

**Three layers:**

1. **CLI (`cli/`)** — Typer-based CLI with Rich UI. Config loading from YAML/env/args (priority: args > env > yaml > defaults). Entry point: `job_applier.py`.

2. **Core Agent (`src/core/`)** — LangGraph workflow with three nodes: `search_jobs`, `filter_jobs`, `apply_to_jobs`. Connects to MCP server via `LinkedInMCPClientSync`. Uses Langfuse for observability with trace ID correlation across the entire workflow.

3. **MCP Server (`linkedin_mcp/`)** — FastMCP server exposing two tools: `search_jobs` and `easy_apply_for_jobs`. Contains its own LangGraph workflows (`graphs/`), services for browser automation and auth, and an `EasyApplyAgent` for AI-powered form completion.

**Key design decisions:**
- CV data is JSON (not PDF) stored at `data/cv_data.json` — structured format with work_experience, skills, education, etc.
- LLM: Qwen3-30B-A3B-Thinking via Hugging Face Serverless API, temperature 0.1
- Browser automation uses undetected-chromedriver with user-agent rotation and randomized delays
- Services implement interfaces defined in `linkedin_mcp/linkedin/interfaces/`
- MCP transport recently migrated from stdio to HTTP

## Key Environment Variables

`LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`, `CV_FILE_PATH`, `HUGGING_FACE_HUB_TOKEN`, `MCP_SERVER_HOST`, `MCP_SERVER_PORT`

Optional: `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST`

## Naming Conventions

- `*_service.py` — business logic services
- `*_graph.py` — LangGraph workflow definitions
- `*_agent.py` — LangGraph agents
- `*_client.py` — MCP/API clients
- Interfaces in `interfaces/` directories (e.g., `IBrowserManager`, `IJobSearchService`)

## Logging

Structured logging via Loguru with trace ID binding. Log files: `logs/core_agent.log`, `logs/linkedin_mcp.log`, `logs/job_applier.log`. Configurable via `*_LOG_LEVEL` and `*_LOG_FILE` env vars.
