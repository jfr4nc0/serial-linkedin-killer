# Serial LinkedIn Killer

## What This Is

A LinkedIn automation agent that searches for jobs, applies automatically, and performs outreach to employees at target companies. The system uses LangGraph workflows, an MCP-based browser automation layer, Kafka for async messaging, and configurable LLM providers (local llama.cpp or Google Gemini) for tasks like role clustering and CV analysis.

## Core Value

Role clustering must process large employee datasets (thousands of employees across many companies) without stalling — Gemini integration unblocks this bottleneck while keeping the local LLM available as an option.

## Requirements

### Validated

- ✓ Job search via LinkedIn RPA (MCP tools) — existing
- ✓ Job application via Easy Apply automation — existing
- ✓ CV analysis and job-CV alignment via LLM — existing
- ✓ Employee search across multiple companies — existing
- ✓ Batch message sending with personalized templates — existing
- ✓ Role clustering via LLM classification (local LLM) — existing
- ✓ Kafka-based async result publishing — existing
- ✓ SQLite persistence for sessions, applications, messages — existing
- ✓ Configurable local LLM via OpenAI-compatible API — existing
- ✓ REST API for workflow submission — existing
- ✓ Docker Compose deployment — existing
- ✓ Gemini as configurable LLM provider via `langchain-google-genai` — v2.1
- ✓ Config-driven LLM provider selection (local vs Gemini) — v2.1
- ✓ Gemini wired into role clustering with automatic Langfuse tracing — v2.1
- ✓ Backward-compatible local LLM path unchanged — v2.1

### Active

(None — define with `/gsd:new-milestone`)

### Out of Scope

- Switching all LLM calls to Gemini — only role clustering uses it for now
- Adding other cloud LLM providers (OpenAI, Anthropic) — just Gemini for now
- Changing the role clustering algorithm itself — only the LLM backend
- UI/dashboard for provider selection — config file and env vars only

## Context

- **Tech stack**: Python 3.12, Poetry, LangChain 0.3.27, langchain-core 0.3.83, langchain-openai 0.3.35, langchain-google-genai 2.1.12
- **LLM providers**: Local llama.cpp at `localhost:8088` (default), Google Gemini via `GEMINI_API_KEY`
- **Provider selection**: `llm.provider` in `config/agent.yaml` or `LLM_PROVIDER` env var
- **Observability**: Langfuse tracing pre-bound to all LLM clients via callback handler
- **Key files**: `src/core/providers/llm_client.py` (factory), `src/config/config_loader.py` (config), `src/core/agents/tools/role_clustering.py` (consumer)
- Shipped v2.1 with 501 LOC across key files (68 llm_client, 151 config_loader, 174 tests, 54 agent.yaml, 54 .env.example)

## Constraints

- **LangChain compatibility**: Must use `langchain-google-genai` to stay consistent with existing patterns
- **Backward compatibility**: Local LLM must keep working — Gemini is additive
- **Config-driven**: Provider selection via `config/agent.yaml` or env vars, no code changes needed to switch
- **Version pinning**: `langchain-google-genai~2.1.12` to avoid breaking langchain-core 0.3.x → 1.x upgrade

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `langchain-google-genai` over direct `genai` SDK | Consistent interface with existing LangChain patterns, Langfuse tracing works automatically | ✓ Good — seamless integration, zero consumer changes |
| Gemini for role clustering only (initially) | Targeted fix for the bottleneck, minimize blast radius | ✓ Good — focused scope, clean implementation |
| Config-driven provider selection | Users can switch without code changes, supports different environments | ✓ Good — works via config file and env var override |
| Pin to v2.1.12 (not v4.x) | v4.x requires langchain-core 1.x, would break existing stack | ✓ Good — avoided breaking upgrade, all existing packages compatible |
| Pre-bind Langfuse callbacks in factory | Enables tracing for all consumers without modifying consumer code | ✓ Good — INT-01 satisfied (zero changes to role_clustering.py) |
| Provider-specific cache keys | Prevents cross-provider pollution when switching at runtime | ✓ Good — both providers coexist cleanly |
| LLM_PROVIDER checked at call-time | Config is cached globally; checking at call-time enables runtime switching | ✓ Good — env var changes take effect immediately |

---
*Last updated: 2026-02-11 after v2.1 milestone*
