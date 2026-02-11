---
phase: 04-quick-wins
plan: 01
subsystem: performance
tags: [cache, memory-management, lru, weakref, cleanup]

# Dependency graph
requires:
  - phase: 03-integration-validation
    provides: Gemini LLM integration with tracing
provides:
  - Bounded LRU cache for role clustering title cache (max 10k entries)
  - Automatic dead weakref pruning in BrowserManagerService
  - Removed dangerous pandas CSV loader (company_loader.py)
affects: [monitoring, memory-optimization]

# Tech tracking
tech-stack:
  added: []
  patterns: [bounded-lru-cache, weakref-pruning, cache-eviction-logging]

key-files:
  created: []
  modified:
    - config/agent.yaml
    - src/config/config_loader.py
    - src/core/agents/tools/role_clustering.py
    - src/linkedin_mcp/services/browser_manager_service.py
    - tests/test_outreach.py

key-decisions:
  - "Used OrderedDict-based BoundedLRUCache instead of functools.lru_cache to support batch dict updates"
  - "Default cache size of 10,000 titles balances memory usage (~1MB) with hit rate"
  - "Automatic pruning of dead weakrefs prevents gradual memory leak in browser instance tracking"

patterns-established:
  - "BoundedLRUCache pattern: OrderedDict with move_to_end() for LRU semantics and configurable max_size"
  - "Weakref pruning pattern: Call _prune_instances() before every append and iteration to prevent dead reference accumulation"

# Metrics
duration: 3.5min
completed: 2026-02-11
---

# Phase 04 Plan 01: RAM Safety Caps Summary

**Bounded LRU title cache (10k max), automatic weakref pruning, and dangerous CSV loader removal prevent unbounded memory growth**

## Performance

- **Duration:** 3.5 min
- **Started:** 2026-02-11T19:49:47Z
- **Completed:** 2026-02-11T19:53:14Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Bounded LRU cache with configurable max size (default 10,000) prevents unbounded growth of `_title_cache` in role_clustering.py
- Self-pruning weakref list in BrowserManagerService prevents accumulation of dead browser instance references
- Removed company_loader.py that could load 5GB CSV into memory via pandas.read_csv()
- All tests pass - 25/26 (1 LinkedIn auth integration test requires manual interaction)

## Task Commits

Each task was committed atomically:

1. **Task 1: Bounded LRU title cache with configurable max size (CACHE-01)** - `90f8199` (feat)
2. **Task 2: Prune dead weakrefs from BrowserManagerService._instances (CACHE-02)** - `cd42367` (feat)
3. **Task 3: Delete company_loader.py and update tests (QUERY-03)** - `ecdd036` (fix)

## Files Created/Modified

- `config/agent.yaml` - Added `title_cache_max_size: 10000` configuration field
- `src/config/config_loader.py` - Added `title_cache_max_size: int = 10000` to LLMConfig model
- `src/core/agents/tools/role_clustering.py` - Replaced unbounded dict with BoundedLRUCache class; added eviction logging
- `src/linkedin_mcp/services/browser_manager_service.py` - Added `_prune_instances()` classmethod; call before append and iteration
- `tests/test_outreach.py` - Removed company_loader imports and 7 test functions (81 lines deleted)

## Decisions Made

**1. OrderedDict-based cache instead of functools.lru_cache**
- Rationale: The cache stores batched LLM results via `_title_cache.update(all_validated)` - lru_cache only works on individual function calls, not dict-style batch updates
- Implementation: BoundedLRUCache wraps OrderedDict with LRU eviction via move_to_end()

**2. Default cache size of 10,000 titles**
- Rationale: Balances memory usage (~1MB for 10k string keys/values) with cache hit rate for typical outreach campaigns
- Configurable via `llm.title_cache_max_size` in agent.yaml

**3. Automatic weakref pruning before every access**
- Rationale: Dead references accumulate gradually during normal operation; pruning on-demand prevents the list from growing indefinitely
- Implementation: _prune_instances() called in __init__ before append and in cleanup_all() before iteration

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all three tasks completed successfully with expected outcomes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All RAM safety guardrails in place. Ready for:
- Streaming response optimization (Phase 05)
- State management patterns (Phase 06)
- Observability and monitoring (Phase 07)

Memory-safe foundation established for handling large employee datasets without OOM risk.

---
*Phase: 04-quick-wins*
*Completed: 2026-02-11*

## Self-Check: PASSED

All claimed files verified to exist:
- FOUND: config/agent.yaml
- FOUND: src/config/config_loader.py
- FOUND: src/core/agents/tools/role_clustering.py
- FOUND: src/linkedin_mcp/services/browser_manager_service.py
- FOUND: tests/test_outreach.py

All claimed commits verified to exist:
- FOUND: 90f8199 (CACHE-01)
- FOUND: cd42367 (CACHE-02)
- FOUND: ecdd036 (QUERY-03)
