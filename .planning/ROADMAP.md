# Roadmap: Serial LinkedIn Killer

## Milestones

- ✅ **v2.1 Gemini LLM Integration** — Phases 1-3 (shipped 2026-02-11)
- 🚧 **v2.2 RAM Safety Caps** — Phases 4-7 (in progress)

## Phases

<details>
<summary>✅ v2.1 Gemini LLM Integration (Phases 1-3) — SHIPPED 2026-02-11</summary>

- [x] Phase 1: Dependency Setup (1/1 plans) — completed 2026-02-11
- [x] Phase 2: Provider Configuration & Client Factory (1/1 plans) — completed 2026-02-11
- [x] Phase 3: Integration & Validation (1/1 plans) — completed 2026-02-11

</details>

---

## 🚧 v2.2 RAM Safety Caps (In Progress)

**Milestone Goal:** Add memory guardrails so the outreach pipeline never crashes from unbounded RAM consumption — graceful degradation instead of OOM kills.

**Phase Numbering:**
- Integer phases (4, 5, 6, 7): Planned milestone work
- Decimal phases (e.g., 4.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 4: Quick Wins** — Bounded caches and dead code removal (completed 2026-02-11)
- [x] **Phase 5: Streaming Queries** — Paginated DB access replaces `.all()` (completed 2026-02-11)
- [ ] **Phase 6: State Optimization** — Memory-efficient LangGraph data flow
- [ ] **Phase 7: Memory Monitoring** — RAM usage tracking with circuit breakers

---

## Phase Details

### Phase 4: Quick Wins
**Goal**: Simple bounded caches and dead code removal prevent runaway growth
**Depends on**: Nothing (first phase of v2.2)
**Requirements**: CACHE-01, CACHE-02, QUERY-03
**Success Criteria** (what must be TRUE):
  1. `_title_cache` in role_clustering.py automatically evicts old entries when size limit is reached
  2. `_instances` weakref list in BrowserManagerService contains no dead references when accessed
  3. `company_loader.py` pandas read_csv path is deleted and cannot be called
**Plans:** 1 plan

Plans:
- [x] 04-01-PLAN.md — Bounded caches, weakref pruning, and dead code removal (CACHE-01, CACHE-02, QUERY-03) — completed 2026-02-11

---

### Phase 5: Streaming Queries
**Goal**: Database queries paginate results instead of loading all rows into memory
**Depends on**: Phase 4
**Requirements**: QUERY-01, QUERY-02
**Success Criteria** (what must be TRUE):
  1. `CompanyDB.filter_companies()` yields results in configurable chunk sizes
  2. `AgentDB.get_search_results()` returns paginated results without loading all matching rows
  3. Existing consumers of both query methods work correctly with chunked results
**Plans:** 1 plan

Plans:
- [x] 05-01-PLAN.md — Chunked filter_companies and generator-based get_search_results (QUERY-01, QUERY-02) — completed 2026-02-11

---

### Phase 6: State Optimization
**Goal**: LangGraph state and data flow avoid O(n^2) memory copying
**Depends on**: Phase 5
**Requirements**: STATE-01, STATE-02, DEDUP-01, DEDUP-02
**Success Criteria** (what must be TRUE):
  1. `EmployeeSearchGraph` pagination loop does not create intermediate list copies on each iteration
  2. `JobSearchGraph` pagination loop does not create intermediate list copies on each iteration
  3. Clustered employee data exists in only 1-2 in-memory copies (not 3+) during outreach processing
  4. Intermediate employee lists in `outreach_agent.py` are cleared after use
**Plans:** 2 plans

Plans:
- [ ] 06-01-PLAN.md — LangGraph Annotated reducers for employee and job search graphs (STATE-01, STATE-02)
- [ ] 06-02-PLAN.md — Memory deduplication in outreach service and agent (DEDUP-01, DEDUP-02)

---

### Phase 7: Memory Monitoring
**Goal**: Pipeline monitors RAM usage and gracefully degrades before OOM
**Depends on**: Phase 6
**Requirements**: MON-01, MON-02, MON-03
**Success Criteria** (what must be TRUE):
  1. Memory monitor utility reports current RSS and percent usage on demand
  2. Outreach batch processing pauses when memory exceeds configured threshold (default 80%)
  3. Memory usage is logged at search start, post-clustering, and pre-send checkpoints
  4. Circuit breaker logs warning with current memory stats when threshold is exceeded
**Plans**: TBD

Plans:
- [ ] 07-01: [To be planned]

---

## Progress

**Execution Order:**
Phases execute in numeric order: 4 → 5 → 6 → 7

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Dependency Setup | v2.1 | 1/1 | ✓ Complete | 2026-02-11 |
| 2. Provider Configuration & Client Factory | v2.1 | 1/1 | ✓ Complete | 2026-02-11 |
| 3. Integration & Validation | v2.1 | 1/1 | ✓ Complete | 2026-02-11 |
| 4. Quick Wins | v2.2 | 1/1 | ✓ Complete | 2026-02-11 |
| 5. Streaming Queries | v2.2 | 1/1 | ✓ Complete | 2026-02-11 |
| 6. State Optimization | v2.2 | 0/2 | Not started | — |
| 7. Memory Monitoring | v2.2 | 0/TBD | Not started | — |
