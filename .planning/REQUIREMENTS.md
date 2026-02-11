# Requirements: Serial LinkedIn Killer — Gemini LLM Integration

**Defined:** 2026-02-11
**Core Value:** Role clustering must process large employee datasets without stalling — Gemini unblocks this bottleneck

## v1 Requirements

### Provider Configuration

- [ ] **PROV-01**: User can select LLM provider ("local" or "gemini") via `config/agent.yaml` under `llm.provider`
- [ ] **PROV-02**: User can override LLM provider via `LLM_PROVIDER` environment variable
- [ ] **PROV-03**: User can configure Gemini model name via `llm.gemini_model` config (default: `gemini-3-flash-preview`)
- [ ] **PROV-04**: User can set Gemini API key via `GEMINI_API_KEY` environment variable

### LLM Client

- [ ] **LLM-01**: `get_llm_client()` returns a LangChain `BaseChatModel` configured for the selected provider
- [ ] **LLM-02**: Gemini client uses `langchain-google-genai` `ChatGoogleGenerativeAI` with configured model and API key
- [ ] **LLM-03**: Local LLM client continues to work unchanged when `provider=local` (backward compatible)
- [ ] **LLM-04**: LLM client caching works for both providers (separate cache keys per provider)

### Dependency & Integration

- [ ] **DEP-01**: `langchain-google-genai` added as Poetry dependency
- [ ] **INT-01**: Role clustering (`cluster_employees_by_role`) works with Gemini provider without code changes to `role_clustering.py`
- [ ] **INT-02**: Langfuse tracing works with Gemini provider (LangChain callback compatibility)

### Configuration Files

- [ ] **CFG-01**: `config/agent.yaml` updated with new `llm.provider` and `llm.gemini_model` fields with documented defaults
- [ ] **CFG-02**: `.env.example` updated with `GEMINI_API_KEY` and `LLM_PROVIDER` entries

## v2 Requirements

### Extended Provider Support

- **PROV-05**: User can add additional providers (OpenAI, Anthropic) via same config pattern
- **PROV-06**: Per-task provider selection (e.g., Gemini for clustering, local for CV analysis)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct `genai` SDK usage | LangChain integration provides consistent interface and tracing |
| Changing role clustering algorithm | Only swapping the LLM backend, not the classification logic |
| UI for provider selection | Config file and env vars sufficient for this milestone |
| Streaming/async Gemini calls | Current sync batch pattern is adequate |
| Other cloud LLM providers | Just Gemini this milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | Phase 1 | Pending |
| PROV-02 | Phase 1 | Pending |
| PROV-03 | Phase 1 | Pending |
| PROV-04 | Phase 1 | Pending |
| LLM-01 | Phase 1 | Pending |
| LLM-02 | Phase 1 | Pending |
| LLM-03 | Phase 1 | Pending |
| LLM-04 | Phase 1 | Pending |
| DEP-01 | Phase 1 | Pending |
| INT-01 | Phase 2 | Pending |
| INT-02 | Phase 2 | Pending |
| CFG-01 | Phase 1 | Pending |
| CFG-02 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-02-11 after initial definition*
