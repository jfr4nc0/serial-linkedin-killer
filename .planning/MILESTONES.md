# Milestones

## v2.1 Gemini LLM Integration (Shipped: 2026-02-11)

**Phases completed:** 3 phases, 3 plans, 6 tasks

**Key accomplishments:**
- Gemini as configurable LLM provider via langchain-google-genai (pinned v2.1.12)
- Config-driven provider selection (local LLM vs Gemini) via agent.yaml or env vars
- Gemini wired into role clustering with automatic Langfuse tracing
- Backward-compatible — local LLM path unchanged

---

## v2.2 RAM Safety Caps (Shipped: 2026-02-12)

**Phases completed:** 4 phases, 5 plans, 10 feat commits

**Key accomplishments:**
- Bounded LRU cache (10k entries) for role clustering title cache + automatic weakref pruning
- Chunked DB queries with yield_per — filter_companies and get_search_results never load all ORM rows
- LangGraph Annotated reducers eliminate O(n^2) list copying in employee/job search pagination
- Eager deletion of intermediate employee lists cuts peak memory copies from 3+ to 2
- psutil-based memory monitor with circuit breaker at 80% threshold + 3 pipeline checkpoints

---
