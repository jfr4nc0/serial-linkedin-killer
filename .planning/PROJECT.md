# Serial LinkedIn Killer — Gemini LLM Integration

## What This Is

A LinkedIn automation agent that searches for jobs, applies automatically, and performs outreach to employees at target companies. The system uses LangGraph workflows, an MCP-based browser automation layer, Kafka for async messaging, and a local LLM for tasks like role clustering and CV analysis. This milestone adds Gemini as a configurable LLM provider to handle large-scale role clustering that the local LLM can't keep up with.

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

### Active

- [ ] Add Gemini as a configurable LLM provider via `langchain-google-genai`
- [ ] Make LLM provider selection configurable (local vs Gemini) in config/env
- [ ] Wire Gemini provider into role clustering for large employee batches
- [ ] Ensure existing local LLM path continues to work unchanged

### Out of Scope

- Switching all LLM calls to Gemini — only role clustering needs it for now
- Adding other cloud LLM providers (OpenAI, Anthropic) — just Gemini this milestone
- Changing the role clustering algorithm itself — only the LLM backend
- UI/dashboard for provider selection — config file and env vars only

## Context

- The codebase already uses LangChain extensively (`langchain-openai 0.3.0` for the local LLM)
- `langchain-google-genai` fits naturally as a drop-in provider with the same `.invoke()` / `.batch()` interface
- The `GEMINI_API_KEY` is already set in `.env`
- Role clustering happens in `src/core/agents/tools/role_clustering.py` — it calls the LLM to classify employee titles into role categories
- The LLM client factory is at `src/core/providers/llm_client.py`
- The current local LLM runs on `localhost:8088` via an OpenAI-compatible API
- Model to use: `gemini-3-flash-preview` (fast, cost-effective for classification tasks)

## Constraints

- **LangChain compatibility**: Must use `langchain-google-genai` to stay consistent with existing patterns (tracing, callbacks, Langfuse integration)
- **Backward compatibility**: Local LLM must keep working — Gemini is additive, not a replacement
- **Config-driven**: Provider selection via `config/agent.yaml` or env vars, no code changes needed to switch

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `langchain-google-genai` over direct `genai` SDK | Consistent interface with existing LangChain patterns, Langfuse tracing works automatically | — Pending |
| Gemini for role clustering only (initially) | Targeted fix for the bottleneck, minimize blast radius | — Pending |
| Config-driven provider selection | Users can switch without code changes, supports different environments | — Pending |

---
*Last updated: 2026-02-11 after initialization*
