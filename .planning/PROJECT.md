# Serial LinkedIn Killer

## What This Is

A LinkedIn automation agent that searches for jobs, applies automatically, and performs outreach to employees at target companies. The system uses LangGraph workflows, an MCP-based browser automation layer, Kafka for async messaging, and configurable LLM providers (local llama.cpp or Google Gemini) for tasks like role clustering and CV analysis. RAM guardrails prevent OOM crashes during large-scale outreach.

## Core Value

The outreach pipeline must handle large employee datasets (thousands of employees across many companies) without stalling or crashing — Gemini unblocks the LLM bottleneck, RAM guardrails prevent OOM kills.

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
- ✓ Bounded LRU cache for role clustering title cache (10k entries) — v2.2
- ✓ Weakref pruning for browser instance tracking — v2.2
- ✓ Chunked DB queries with yield_per for filter_companies and get_search_results — v2.2
- ✓ LangGraph Annotated reducers eliminate O(n^2) list copying — v2.2
- ✓ Eager deletion of intermediate employee data after consumption — v2.2
- ✓ psutil memory monitor with circuit breaker at 80% threshold — v2.2
- ✓ Memory logging at 3 pipeline checkpoints (pre-search, post-clustering, pre-send) — v2.2

### Active

(None — next milestone not yet defined)

### Out of Scope

- Switching all LLM calls to Gemini — only role clustering uses it for now
- Adding other cloud LLM providers (OpenAI, Anthropic) — just Gemini for now
- UI/dashboard for provider selection — config file and env vars only
- Replacing Kafka with lighter broker (Redpanda) — KRaft mode is already lean at 1G
- Per-request memory budgets — future ADV-01
- Memory-aware job scheduling — future ADV-02
- GC tuning for long-running FastAPI processes — future ADV-03

## Context

- **Tech stack**: Python 3.12, Poetry, LangChain 0.3.27, langchain-core 0.3.83, langchain-openai 0.3.35, langchain-google-genai 2.1.12, psutil 7.2.2
- **LLM providers**: Local llama.cpp at `localhost:8088` (default), Google Gemini via `GEMINI_API_KEY`
- **Provider selection**: `llm.provider` in `config/agent.yaml` or `LLM_PROVIDER` env var
- **Memory monitoring**: `memory.threshold_percent` in `config/agent.yaml` or `MEMORY_THRESHOLD_PERCENT` env var (default 80%)
- **Observability**: Langfuse tracing pre-bound to all LLM clients; memory checkpoints at pipeline stages
- **Key files**: `src/core/providers/llm_client.py` (factory), `src/config/config_loader.py` (config), `src/core/agents/tools/role_clustering.py` (consumer), `src/core/utils/memory_monitor.py` (memory), `src/core/api/services/outreach_service.py` (pipeline)
- Shipped v2.2 with 16 files modified (402 insertions, 130 deletions) across 10 feat commits

## Constraints

- **LangChain compatibility**: Must use `langchain-google-genai` to stay consistent with existing patterns
- **Backward compatibility**: Local LLM must keep working — Gemini is additive
- **Config-driven**: Provider and memory threshold selection via `config/agent.yaml` or env vars
- **Version pinning**: `langchain-google-genai~2.1.12` to avoid breaking langchain-core 0.3.x → 1.x upgrade

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `langchain-google-genai` over direct `genai` SDK | Consistent interface with existing LangChain patterns, Langfuse tracing works automatically | ✓ Good |
| Gemini for role clustering only (initially) | Targeted fix for the bottleneck, minimize blast radius | ✓ Good |
| Config-driven provider selection | Users can switch without code changes, supports different environments | ✓ Good |
| Pin to v2.1.12 (not v4.x) | v4.x requires langchain-core 1.x, would break existing stack | ✓ Good |
| Pre-bind Langfuse callbacks in factory | Enables tracing for all consumers without modifying consumer code | ✓ Good |
| OrderedDict-based BoundedLRUCache | Supports batch dict updates unlike functools.lru_cache | ✓ Good |
| filter_companies returns List[dict] with yield_per internal | Preserves len()/slice/truthiness consumer compatibility | ✓ Good |
| get_search_results changed to Iterator[dict] | Consumer only uses for-loop — generator safe | ✓ Good |
| LangGraph Annotated reducers with operator.add | Framework handles list append — nodes return deltas only | ✓ Good |
| Circuit breaker does GC then continues | Graceful degradation, not abort — pipeline still completes | ✓ Good |
| psutil lazy import in check_memory_threshold | Avoids circular imports with config_loader | ✓ Good |

---
*Last updated: 2026-02-12 after v2.2 milestone*
