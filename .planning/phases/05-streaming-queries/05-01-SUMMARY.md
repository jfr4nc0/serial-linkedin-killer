---
phase: 05-streaming-queries
plan: 01
subsystem: database
tags: [sqlalchemy, yield_per, streaming, memory-optimization, orm]

# Dependency graph
requires:
  - phase: 04-quick-wins
    provides: Bounded LRU cache and weakref pruning for memory optimization
provides:
  - Chunked query execution for CompanyDB.filter_companies using yield_per
  - Generator-based AgentDB.get_search_results for lazy iteration
  - Memory-safe query patterns avoiding ORM object/dict memory spikes
affects: [06-streaming-state, 07-monitoring]

# Tech tracking
tech-stack:
  added: []
  patterns: [yield_per pagination, generator-based queries, lazy iteration]

key-files:
  created: []
  modified:
    - src/core/agents/tools/company_db.py
    - src/core/db/agent_db.py
    - src/core/agents/outreach_agent.py
    - tests/test_outreach.py

key-decisions:
  - "CompanyDB.filter_companies still returns List[dict] (not generator) to preserve consumer compatibility with len(), slicing, and truthiness checks"
  - "AgentDB.get_search_results changed to Iterator[dict] since consumer only iterates with for-loop"
  - "Default chunk_size of 500 balances memory efficiency with query overhead"

patterns-established:
  - "yield_per pattern: Use when query results need conversion but consumers require list operations (len, slice)"
  - "Generator pattern: Use when consumers only iterate and don't need list operations"
  - "Session scope must cover entire yield_per iteration to avoid lazy loading errors"

# Metrics
duration: 5min
completed: 2026-02-11
---

# Phase 05 Plan 01: Streaming Queries Summary

**Replaced .all() with yield_per chunked iteration in two critical query hotspots, preventing OOM from concurrent ORM object and dict materialization**

## Performance

- **Duration:** 5 min (280s)
- **Started:** 2026-02-11T20:31:01Z
- **Completed:** 2026-02-11T20:35:41Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- CompanyDB.filter_companies uses yield_per(500) internally while maintaining List[dict] return type for backward compatibility
- AgentDB.get_search_results changed to Iterator[dict] with yield_per(500) for true lazy streaming
- All consumers work unchanged (outreach_service.py uses len/slice on filter_companies; outreach_agent.py iterates db_results)
- Tests verify chunked behavior produces identical results regardless of chunk_size

## Task Commits

Each task was committed atomically:

1. **Task 1: Chunked filter_companies with yield_per (QUERY-01)** - `c5b897e` (feat)
2. **Task 2: Generator-based get_search_results with yield_per (QUERY-02)** - `bd374d5` (feat)

## Files Created/Modified

- `src/core/agents/tools/company_db.py` - Added yield_per chunked iteration in filter_companies, chunk_size parameter with default 500
- `src/core/db/agent_db.py` - Changed get_search_results to generator with yield_per, return type Iterator[dict]
- `src/core/agents/outreach_agent.py` - Added comment documenting lazy iteration behavior of db_results
- `tests/test_outreach.py` - Added tests for chunk_size parameter and generator behavior (test_db_filter_companies_chunk_size, test_get_search_results_returns_iterable, test_get_search_results_chunk_size, test_get_search_results_empty)

## Decisions Made

**1. CompanyDB.filter_companies returns List[dict] (not generator)**
- **Rationale:** Both consumers in outreach_service.py (lines 109, 420) call len(), use slicing, and check truthiness. Changing to generator would break all of these operations.
- **Memory win:** Comes from avoiding peak where ALL ORM objects AND ALL dicts coexist. With yield_per, only chunk_size ORM objects are alive at any time while dicts accumulate incrementally.

**2. AgentDB.get_search_results returns Iterator[dict] (generator)**
- **Rationale:** Single consumer in outreach_agent.py (line 164) only uses for-loop iteration. Never calls len(), never indexes, never checks truthiness. Generator is fully compatible.
- **Memory win:** True streaming - neither ORM objects nor dicts accumulate in memory. Each row is yielded, processed, and discarded.

**3. Default chunk_size of 500**
- **Rationale:** Balances memory efficiency with database round-trip overhead. SQLAlchemy fetches 500 rows at a time, keeping memory bounded while minimizing query latency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Streaming query patterns established and tested
- Ready for Phase 06 (Streaming State Management) to handle stateful iteration and resumption
- Memory-safe query foundation enables large-scale outreach without OOM risk

## Self-Check: PASSED

- ✓ FOUND: 05-01-SUMMARY.md
- ✓ FOUND: c5b897e (Task 1 commit)
- ✓ FOUND: bd374d5 (Task 2 commit)
- ✓ FOUND: src/core/agents/tools/company_db.py
- ✓ FOUND: src/core/db/agent_db.py

---
*Phase: 05-streaming-queries*
*Completed: 2026-02-11*
