---
phase: 06-state-optimization
plan: 01
subsystem: graphs
tags: [langgraph, annotated-reducer, operator-add, state-optimization, typeddict]

# Dependency graph
requires:
  - phase: none
    provides: existing EmployeeSearchState, JobSearchState, and their graph node implementations
provides:
  - Annotated[List, operator.add] reducers on EmployeeSearchState (collected_employees, errors)
  - Annotated[List, operator.add] reducers on JobSearchState (collected_jobs, errors)
  - Delta-only node returns in employee_search_graph.py and job_search_graph.py
affects: [06-state-optimization, graphs, pagination]

# Tech tracking
tech-stack:
  added: []
  patterns: [langgraph-annotated-reducer, delta-dict-returns]

key-files:
  created: []
  modified:
    - src/linkedin_mcp/model/outreach_types.py
    - src/linkedin_mcp/graphs/employee_search_graph.py
    - src/linkedin_mcp/model/job_search_state.py
    - src/linkedin_mcp/graphs/job_search_graph.py

key-decisions:
  - "extracted_urls (set) left unchanged -- mutated in-place via .add(), no copy problem"
  - "total_found (plain int) still computed with state addition since it has no reducer"

patterns-established:
  - "LangGraph Annotated reducer: use Annotated[List[T], operator.add] for accumulating list fields in TypedDict state"
  - "Delta-dict returns: graph nodes return only changed keys, never {**state, ...} spread"

# Metrics
duration: 3min
completed: 2026-02-11
---

# Phase 6 Plan 1: LangGraph Annotated Reducers Summary

**Annotated[List, operator.add] reducers on EmployeeSearchState and JobSearchState eliminate O(n^2) list copying in pagination loops**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-11T20:58:12Z
- **Completed:** 2026-02-11T21:01:41Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- EmployeeSearchState and JobSearchState use LangGraph Annotated reducers for their accumulating list fields (collected_employees/collected_jobs and errors)
- All employee_search_graph nodes return only new/delta items -- LangGraph reducer handles append automatically
- All job_search_graph nodes return only delta dicts -- removed all {**state, ...} spread patterns and list concatenation
- _check_pagination returns empty dict instead of full state, preventing duplicate item injection via reducer

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Annotated reducers to EmployeeSearchState and fix employee_search_graph nodes** - `edd7cf4` (feat)
2. **Task 2: Add Annotated reducers to JobSearchState and fix job_search_graph nodes** - `38557aa` (feat)

## Files Created/Modified
- `src/linkedin_mcp/model/outreach_types.py` - Added Annotated reducers for collected_employees and errors in EmployeeSearchState
- `src/linkedin_mcp/graphs/employee_search_graph.py` - Changed _extract_employees and error returns to delta-only dicts
- `src/linkedin_mcp/model/job_search_state.py` - Added Annotated reducers for collected_jobs and errors in JobSearchState
- `src/linkedin_mcp/graphs/job_search_graph.py` - Removed all {**state} spreads and list concatenations, delta-only returns

## Decisions Made
- `extracted_urls` (set) left unchanged -- it is mutated in-place via `.add()` and does not suffer from the O(n^2) copy problem
- `total_found` (plain int, no reducer) still uses `state["total_found"] + len(page_jobs)` since it needs the accumulated value

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both graph state types now use LangGraph Annotated reducers for all accumulating list fields
- Ready for 06-02 (if applicable) or Phase 7
- Note: job_application_graph.py still has a `state["errors"] +` pattern but is out of scope for this plan

## Self-Check: PASSED

- All 4 modified files exist on disk
- SUMMARY.md created at .planning/phases/06-state-optimization/06-01-SUMMARY.md
- Commit edd7cf4 (Task 1) found in git log
- Commit 38557aa (Task 2) found in git log
- No stale list concatenation patterns in either graph file
- Both state TypedDicts contain Annotated[List, operator.add] reducers
- Both graphs import cleanly (poetry run python -c import check passed)

---
*Phase: 06-state-optimization*
*Completed: 2026-02-11*
