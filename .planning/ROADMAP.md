# Roadmap: Serial LinkedIn Killer — Gemini LLM Integration

## Overview

This milestone integrates Gemini as a configurable LLM provider to unblock role clustering bottlenecks when processing large employee datasets. The journey moves from adding the dependency, through configurable provider selection and client factory implementation, to validated end-to-end integration with existing workflows while maintaining backward compatibility with the local LLM.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Dependency Setup** - Add langchain-google-genai library ✓ (2026-02-11)
- [x] **Phase 2: Provider Configuration & Client Factory** - Config-driven LLM provider selection with working client factory ✓ (2026-02-11)
- [ ] **Phase 3: Integration & Validation** - Role clustering works with Gemini and tracing is operational

## Phase Details

### Phase 1: Dependency Setup
**Goal**: Gemini LangChain library is available for use
**Depends on**: Nothing (first phase)
**Requirements**: DEP-01
**Success Criteria** (what must be TRUE):
  1. `langchain-google-genai` package is installed via Poetry
  2. `ChatGoogleGenerativeAI` can be imported without errors
  3. Poetry lock file includes the new dependency with correct version constraints
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Add langchain-google-genai v2.1.12 and verify imports ✓

### Phase 2: Provider Configuration & Client Factory
**Goal**: LLM provider is configurable and client factory returns correct provider instances
**Depends on**: Phase 1
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, LLM-01, LLM-02, LLM-03, LLM-04, CFG-01, CFG-02
**Success Criteria** (what must be TRUE):
  1. User can set `llm.provider` to "local" or "gemini" in `config/agent.yaml` and system uses correct provider
  2. User can override provider via `LLM_PROVIDER` environment variable and it takes precedence over config file
  3. User can configure Gemini model name via `llm.gemini_model` config with default `gemini-3-flash-preview`
  4. `get_llm_client()` returns `ChatOpenAI` instance when provider is "local" with unchanged behavior
  5. `get_llm_client()` returns `ChatGoogleGenerativeAI` instance when provider is "gemini" with configured API key and model
  6. LLM client caching works for both providers with separate cache keys preventing cross-provider pollution
  7. `.env.example` documents `GEMINI_API_KEY` and `LLM_PROVIDER` with usage examples
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Config schema extension, provider factory, and env var documentation ✓

### Phase 3: Integration & Validation
**Goal**: Role clustering uses Gemini when configured with full observability
**Depends on**: Phase 2
**Requirements**: INT-01, INT-02
**Success Criteria** (what must be TRUE):
  1. `cluster_employees_by_role` tool executes successfully with Gemini provider without code changes to `role_clustering.py`
  2. Role clustering produces correct classifications when using Gemini (same quality as local LLM)
  3. Langfuse tracing captures Gemini LLM calls with provider identification in trace metadata
  4. User can switch between local and Gemini providers via config change without application restart
**Plans**: TBD

Plans:
- [ ] 03-01: [Plan not yet created]

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Dependency Setup | 1/1 | ✓ Complete | 2026-02-11 |
| 2. Provider Configuration & Client Factory | 1/1 | ✓ Complete | 2026-02-11 |
| 3. Integration & Validation | 0/TBD | Not started | - |
