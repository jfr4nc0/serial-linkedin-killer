# Requirements: Serial LinkedIn Killer

**Defined:** 2026-02-11
**Core Value:** The outreach pipeline must handle large employee datasets without crashing — RAM guardrails prevent OOM kills

## v2.2 Requirements

Requirements for RAM safety caps. Each maps to roadmap phases.

### Bounded Caches

- [x] **CACHE-01**: `_title_cache` in role_clustering.py uses LRU eviction with configurable max size (default 10,000 entries)
- [x] **CACHE-02**: `_instances` weakref list in BrowserManagerService prunes dead references before each access

### Streaming Queries

- [x] **QUERY-01**: `CompanyDB.filter_companies()` yields results in chunks instead of loading all matching rows into memory
- [x] **QUERY-02**: `AgentDB.get_search_results()` returns results in paginated chunks instead of `.all()`
- [x] **QUERY-03**: `company_loader.py` pandas `read_csv()` path is removed (dead code, 5GB landmine)

### Memory Monitoring

- [ ] **MON-01**: Memory monitor utility using psutil reports current RSS and percent usage
- [ ] **MON-02**: Circuit breaker pauses outreach batch processing when memory exceeds configurable threshold (default 80%)
- [ ] **MON-03**: Memory usage is logged at key pipeline checkpoints (pre-search, post-cluster, pre-send)

### LangGraph State Optimization

- [ ] **STATE-01**: `EmployeeSearchGraph` pagination loop does not create O(n^2) intermediate list copies
- [ ] **STATE-02**: `JobSearchGraph` pagination loop does not create O(n^2) intermediate list copies

### Data Duplication Reduction

- [ ] **DEDUP-01**: Clustered employee data does not exist as 3+ simultaneous in-memory copies in `outreach_service.py`
- [ ] **DEDUP-02**: Intermediate employee lists in `outreach_agent.py` are cleared after consumption

## Future Requirements

### Advanced Memory Management

- **ADV-01**: Per-request memory budgets with automatic request rejection when budget exceeded
- **ADV-02**: Memory-aware job scheduling (defer large batches when system is under pressure)
- **ADV-03**: Garbage collection tuning for long-running FastAPI processes

## Out of Scope

| Feature | Reason |
|---------|--------|
| Replacing Kafka with lighter broker (Redpanda) | Current Kafka KRaft setup is already lean at 1G; not a RAM bottleneck |
| Rewriting LangGraph state management | Would require fundamental architecture change; targeted fixes sufficient |
| Adding swap space or increasing Docker memory limits | Band-aid, not a fix — masks unbounded growth |
| Profiling/benchmarking infrastructure | Useful but separate concern; this milestone is about prevention |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CACHE-01 | Phase 4 | Complete |
| CACHE-02 | Phase 4 | Complete |
| QUERY-03 | Phase 4 | Complete |
| QUERY-01 | Phase 5 | Complete |
| QUERY-02 | Phase 5 | Complete |
| STATE-01 | Phase 6 | Pending |
| STATE-02 | Phase 6 | Pending |
| DEDUP-01 | Phase 6 | Pending |
| DEDUP-02 | Phase 6 | Pending |
| MON-01 | Phase 7 | Pending |
| MON-02 | Phase 7 | Pending |
| MON-03 | Phase 7 | Pending |

**Coverage:**
- v2.2 requirements: 12 total
- Mapped to phases: 12/12 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-02-11 after Phase 5 completion*
