# Codebase Concerns

**Analysis Date:** 2026-02-11

## Tech Debt

**Bare Exception Handling:**
- Issue: Multiple code paths use bare `except:` clauses that silently swallow all exceptions, including system exits and keyboard interrupts, making debugging difficult and hiding critical failures.
- Files: `src/linkedin_mcp/agents/easy_apply_agent.py` (lines 156, 301), `src/linkedin_mcp/services/linkedin_auth_service.py` (multiple bare excepts)
- Impact: Silent failures mask bugs. Errors are not logged, making troubleshooting impossible. System may appear functional while critical operations fail.
- Fix approach: Replace bare `except:` with `except (SpecificException, AnotherException):` or use `except Exception as e:` with explicit logging. Never catch `SystemExit`, `KeyboardInterrupt`, or `GeneratorExit`.

**Global State in Services:**
- Issue: `src/core/api/services/outreach_service.py` and `src/core/api/services/job_service.py` use module-level globals `_executor` with manual cleanup via `atexit`. This is fragile and can cause issues during testing, forking, or multiple app instances.
- Files: `src/core/api/services/outreach_service.py` (lines 31-51), `src/core/api/services/job_service.py` (similar pattern)
- Impact: Race conditions possible between initialization and cleanup. Tests may interfere with each other. Resource leaks if process doesn't exit cleanly.
- Fix approach: Encapsulate thread pool in a context manager or dependency injection pattern. Use `asyncio` instead of ThreadPoolExecutor where possible.

**Bare Except in Browser Automation:**
- Issue: `src/linkedin_mcp/agents/easy_apply_agent.py` lines 156, 301 and `src/linkedin_mcp/services/linkedin_auth_service.py` have bare `except:` blocks in Selenium element finding loops that silently continue, potentially masking element lifecycle issues.
- Files: `src/linkedin_mcp/agents/easy_apply_agent.py` (lines 156, 301)
- Impact: Silent selector failures during form filling. Incorrect data may be submitted without warning.
- Fix approach: Catch `NoSuchElementException` and `TimeoutException` explicitly. Log each failure to track selector obsolescence.

**Unsafe Global Cache in Role Clustering:**
- Issue: `src/core/agents/tools/role_clustering.py` line 87 uses module-level dict `_title_cache` that persists across requests within the same process, shared across all threads/requests.
- Files: `src/core/agents/tools/role_clustering.py` (line 87)
- Impact: Memory growth over time (unbounded cache). Stale classifications if LLM behavior changes. No cache invalidation strategy.
- Fix approach: Implement time-based cache expiration (TTL) or use thread-safe `functools.lru_cache` with max size limits.

**Shared Database Without Connection Pooling Documentation:**
- Issue: Both `core-agent` (FastAPI) and `linkedin-mcp-server` write to the same SQLite database (`agent.db` and `companies.db`) concurrently without documented locking strategy. SQLite has single-writer limitation.
- Files: `src/core/db/agent_db.py`, `src/core/db/engine.py`
- Impact: Database lock contention under high concurrent load. Write conflicts possible between MCP and core-agent. No documented transaction isolation levels.
- Fix approach: Document SQLite WAL mode usage. Add connection pooling with timeout handling. Consider migration to PostgreSQL if scaling to >10 concurrent writers needed.

**Hardcoded Timeouts Without User Control:**
- Issue: Multiple long-running operations use hardcoded timeouts (600s in `src/core/queue/consumer.py:46`, 3600s in `src/core/agents/outreach_agent.py:147`) that are not configurable via environment or config.
- Files: `src/core/queue/consumer.py` (line 46), `src/core/agents/outreach_agent.py` (line 147)
- Impact: Cannot tune timeouts for slow networks or large batches without code changes. Deployments must handle hardcoded limits.
- Fix approach: Move all timeout constants to `src/config/config_loader.py` with sensible defaults and env var overrides.

## Known Bugs

**Consumer Not Cleaning Up on Timeout:**
- Symptoms: Kafka consumer hangs indefinitely on timeout; resources leak if consume() is called repeatedly.
- Files: `src/core/queue/consumer.py` (line 125 - close is in finally, but consumer may not fully disconnect on timeout)
- Trigger: Call `consumer.consume(timeout=5.0)` with no matching message - consumer stays subscribed after timeout.
- Workaround: Explicitly call `.close()` after consume() returns None.
- Fix: Ensure subscription cleanup on timeout in finally block.

**Session Count Not Tracked:**
- Symptoms: `SessionStore.count()` always returns 0, breaking session lifecycle monitoring.
- Files: `src/core/api/services/session_store.py` (line 72)
- Trigger: Calling `session_store.count()` returns hardcoded 0.
- Impact: Cannot monitor session accumulation or detect leaks via API.
- Fix approach: Implement count() to query database: `return len(self._db.get_session_list())`

**Role Reassignment Breaks on First Match:**
- Symptoms: When reassigning employees to new roles in `src/core/api/services/outreach_service.py`, the nested loop breaks on first reassignment, but should continue checking all employees if employee list is modified during iteration.
- Files: `src/core/api/services/outreach_service.py` (lines 287-306)
- Trigger: Reassign an employee from role A to role B, then reassign another employee.
- Impact: May miss reassignments or incorrectly modify clustered groups.
- Workaround: Build a mapping of reassignments first, then apply atomically.

**Kafka Message Payload Size Not Validated:**
- Symptoms: Large employee lists serialized as Kafka messages may exceed broker limits (default 1MB).
- Files: `src/core/queue/producer.py` (line 52)
- Trigger: Outreach search with >5000 employees generates large JSON payload.
- Impact: Kafka delivery failure with unclear error. Message silently dropped.
- Fix approach: Add pre-flight validation in `publish()` to check payload size and either reject or chunk.

## Security Considerations

**Credentials Passed in Request Bodies:**
- Risk: LinkedIn email/password sent as JSON in HTTP request bodies. Can be logged, stored, or intercepted.
- Files: `src/core/api/schemas/outreach_schemas.py`, `src/core/api/schemas/job_schemas.py`
- Current mitigation: HTTPS assumed (not enforced in code). No request body encryption.
- Recommendations:
  - Use OAuth instead of password storage.
  - Enforce HTTPS at load balancer level.
  - Add request logging filter to exclude credential fields.
  - Consider storing credentials in secure vault (e.g., HashiCorp Vault) instead of request payloads.

**Unvalidated User Input in Kafka Payloads:**
- Risk: Message templates and employee data from API requests are serialized directly to Kafka without schema validation. Malicious templates could be used to exfiltrate data or execute code.
- Files: `src/core/api/services/outreach_service.py` (line 231), `src/core/queue/producer.py` (line 52)
- Current mitigation: Pydantic validation on request schemas only.
- Recommendations:
  - Add schema validation on Kafka message deserialization.
  - Whitelist allowed template variables.
  - Sanitize message templates for code injection patterns.

**No Rate Limiting on API Endpoints:**
- Risk: API endpoints `/api/outreach/search` and `/api/outreach/send` can be called unlimited times, exhausting resources.
- Files: `src/core/api/controllers/outreach_controller.py`
- Current mitigation: Daily message limit at agent level, but not at API level.
- Recommendations:
  - Add middleware rate limiting (e.g., FastAPI-Limiter).
  - Implement per-user quotas if auth is added.
  - Monitor API call rates in logs.

**Trace IDs Exposed in Responses:**
- Risk: Trace IDs in Kafka responses can be correlated to identify user sessions or track individuals across searches.
- Files: `src/core/api/schemas/outreach_schemas.py` (trace_id fields in responses)
- Current mitigation: None.
- Recommendations:
  - Make trace_id response optional or return only via secure channel.
  - Hash trace_ids before including in client responses.

## Performance Bottlenecks

**Synchronous Kafka Consumer Blocks ThreadPool:**
- Problem: `src/core/agents/outreach_agent.py` line 146 blocks a thread pool worker waiting for Kafka results (up to 3600s). If all workers block, no new searches can start.
- Files: `src/core/agents/outreach_agent.py` (line 146-148), `src/core/queue/consumer.py`
- Cause: Using sync consumer in thread pool instead of async await pattern.
- Improvement path:
  - Convert to async/await with `asyncio` and `aiokafka`.
  - Or use callback-based model (publish result to Redis or database poll instead of blocking consumer).
  - Current workaround: Increase ThreadPoolExecutor max_workers, but this is not scalable.

**LLM Classification Blocks on Batch Processing:**
- Problem: `src/core/agents/tools/role_clustering.py` line 159 clusters ALL employees at once in batches of 50, blocking entire search workflow. No streaming or incremental results.
- Files: `src/core/agents/tools/role_clustering.py` (lines 159-161)
- Cause: Full batch required before response sent to client.
- Improvement path:
  - Stream classification results as they complete (WebSocket or Server-Sent Events).
  - Implement timeout-based partial results (return classifications in progress after T seconds).
  - Cache title classifications aggressively to skip LLM for known roles.

**Employee Search Materializes Full Result Set:**
- Problem: `src/core/agents/outreach_agent.py` line 163 loads entire search result into memory from DB. With 10K+ employees, memory spike is significant.
- Files: `src/core/agents/outreach_agent.py` (line 163), `src/core/db/agent_db.py` (lines 240-257)
- Cause: No pagination or streaming of results from SQLite.
- Improvement path:
  - Implement chunked loading with generators.
  - Add pagination to session storage.
  - Consider storing large result sets in external file (JSON lines format) instead of clustering in memory.

**Message Sending Not Rate-Limited by Time:**
- Problem: `src/core/api/services/outreach_service.py` applies daily limit but doesn't respect per-message delays. Sending 100 messages rapidly causes LinkedIn to flag as bot.
- Files: `src/core/api/services/outreach_service.py` (line 361), `src/config/config_loader.py` (lines 50-51 define delay range but usage not verified)
- Cause: Delay is configured but may not be applied in MCP layer.
- Improvement path:
  - Verify delay is actually applied during message sending.
  - Add jitter to avoid predictable patterns.
  - Implement circuit breaker when rapid bans occur.

## Fragile Areas

**Browser Selector Brittleness:**
- Files: `src/linkedin_mcp/graphs/message_send_graph.py` (lines 21-99 - CONNECT_SELECTORS, MESSAGE_SELECTORS, etc.)
- Why fragile: XPath and CSS selectors for LinkedIn elements are hardcoded and will break when LinkedIn changes UI (expected every 2-3 months). Multiple selectors provide fallback but maintenance burden is high.
- Safe modification: Any LinkedIn UI update requires regression testing. Maintain a test suite with screenshots that validates selectors still work.
- Test coverage: Selector validation tests exist (`src/linkedin_mcp/utils/linkedin_selectors.py`) but are brittle and require manual LinkedIn session to validate.

**Message Send State Machine:**
- Files: `src/linkedin_mcp/graphs/message_send_graph.py` (entire file, 527 lines)
- Why fragile: Complex state transitions with multiple exception handlers and edge cases. Easy to add feature without considering all state transitions. Browser state can become inconsistent (page loaded but element not found).
- Safe modification: Every state change must have explicit test case. Add invariant checks (e.g., assert driver at expected URL) at each transition.
- Test coverage: Limited - only 297 lines of tests in `tests/test_message_send_graph.py`. Many edge cases untested (timeout during modal transition, element stale during scroll, etc.).

**Employee Clustering LLM Prompt:**
- Files: `src/core/agents/tools/role_clustering.py` (lines 53-81)
- Why fragile: Role categories hardcoded in prompt. If categories change (e.g., add "Product Manager" role), prompt must be updated and all cached classifications become stale. JSON parsing of LLM response assumes strict format.
- Safe modification: Categories should be data-driven from config, not hardcoded. JSON response parsing should be defensive (validate against schema before use).
- Test coverage: No unit tests for classification logic. Integration tests exist but don't cover classification failures or edge cases (multi-role titles, non-English titles, etc.).

**Session Storage TTL Without Cleanup Thread:**
- Files: `src/core/api/services/session_store.py` (lines 47-53)
- Why fragile: Cleanup runs only when new session is created (line 37). If no new searches after inactive period, expired sessions persist in database indefinitely, causing gradual database bloat.
- Safe modification: Implement background cleanup job (e.g., schedule cleanup every 5 minutes) instead of lazy cleanup.
- Test coverage: No test for TTL expiration or cleanup. Database can grow unbounded.

**Kafka Topic Creation as Side Effect:**
- Files: `src/core/api/app.py` (line 44 calls `ensure_topics()`)
- Why fragile: Topic creation happens on app startup, but if Kafka is unavailable, app won't start (exception in `lifespan`). If topic creation fails partway through, retry logic missing.
- Safe modification: Make topic creation idempotent and non-blocking. Log warning instead of exception if Kafka unavailable at startup (allow degraded mode).

## Scaling Limits

**ThreadPoolExecutor Limited to 4 Workers:**
- Current capacity: 4 max concurrent outreach searches or 4 max concurrent job applications.
- Limit: Cannot process >4 simultaneous user requests. Additional requests queue, blocking indefinitely if no worker becomes available.
- Scaling path: Make max_workers configurable per config. For production: use async/await instead of ThreadPoolExecutor. For Docker: spin up multiple core-agent containers with load balancer.

**SQLite Single-Writer Bottleneck:**
- Current capacity: 1 concurrent write operation (search result insertion or message recording).
- Limit: With 4 concurrent threads all trying to write, SQLite locks occur frequently. Measurable slowdown when inserting >1000 search results per second.
- Scaling path: Enable SQLite WAL (Write-Ahead Logging) mode to allow concurrent reads. For >10 concurrent writers: migrate to PostgreSQL.

**Kafka Consumer Group Timeout:**
- Current capacity: Single consumer waits up to 3600s for batch completion.
- Limit: If MCP server is slow or network is unreliable, consumer blocks for hours, holding thread pool worker.
- Scaling path: Implement timeout with exponential backoff. Switch to polling (check database for completion instead of blocking Kafka consumer).

**Session Memory in Database:**
- Current capacity: Session TTL 3600s with no hard size limit. Each session stores full employee cluster data (10-100KB per session).
- Limit: Running 100 concurrent outreach searches = 1-10MB session storage. Database can become slow with >10K expired sessions still taking up space.
- Scaling path: Implement explicit session eviction policy. Store large sessions in external file system (S3, shared file volume) instead of database.

## Dependencies at Risk

**Undetected-Chromedriver (v3.5.0):**
- Risk: Unmaintained library (last update ~1 year ago). Chrome updates may break automation. No activity in issues/PRs.
- Impact: May fail to launch Chrome if Chrome version increments. Selector changes in LinkedIn could break without warning.
- Migration plan: Monitor for Chrome compatibility issues. If project becomes unavailable, switch to `playwright` (actively maintained, supports headless better).

**LangGraph Dependency (0.6.7):**
- Risk: Rapidly evolving library with breaking changes between versions. Current code tightly coupled to LangGraph state graph API.
- Impact: Upgrade could require refactoring agent definitions. Downtime during migration.
- Migration plan: Pin version and upgrade only when critical fixes available. Plan for refactoring every 6 months as library evolves.

**Kafka Brokers (confluent-kafka 2.6.0):**
- Risk: High dependency on Kafka availability. If broker is unavailable, all async operations (search, send) fail with no fallback queue.
- Impact: Service degradation cascades (API accepts requests but Kafka delivery fails silently).
- Migration plan: Add fallback to in-memory queue with eventual delivery. Implement circuit breaker to return error quickly if Kafka unavailable.

## Missing Critical Features

**No Idempotency Keys:**
- Problem: If API request is retried (network timeout, client retry logic), duplicate searches/sends will occur (no idempotency tracking).
- Blocks: Reliable retry handling. Delivery guarantees.
- Workaround: Client must implement own deduplication based on response task_id.
- Fix approach: Add idempotency_key parameter to requests, store in database to prevent duplicates.

**No Request Cancellation:**
- Problem: Once search or send is submitted via API, there is no way to cancel it (e.g., if user clicks cancel in UI).
- Blocks: User control of long-running operations.
- Fix approach: Add `DELETE /api/outreach/{task_id}` endpoint that signals cancellation via Kafka or database flag.

**No Search Progress Reporting:**
- Problem: Search waits 3600 seconds for completion with no progress feedback. User doesn't know if search is stalled or actually running.
- Blocks: Real-time user feedback.
- Fix approach: Publish progress events to Kafka as MCP processes each company (completion %, current company, etc.).

**No Error Recovery Strategy:**
- Problem: If MCP crashes during search, results are incomplete but no retry logic exists.
- Blocks: Robust batch processing.
- Fix approach: Add checkpointing (save progress every N companies) and resumable searches.

## Test Coverage Gaps

**No Tests for Kafka Consumer Timeout:**
- What's not tested: Behavior when MCP takes >3600s or never publishes completion.
- Files: `src/core/queue/consumer.py`, `src/core/agents/outreach_agent.py`
- Risk: Consumer may hang indefinitely or return incorrect state without detection.
- Priority: High - affects production stability.

**No Tests for Concurrent Outreach Requests:**
- What's not tested: Multiple simultaneous `/api/outreach/search` calls against same database.
- Files: `src/core/api/services/outreach_service.py`, `src/core/db/agent_db.py`
- Risk: Database lock contention, race conditions in session store.
- Priority: High - affects concurrent user experience.

**No Tests for Browser Selector Failures:**
- What's not tested: What happens when LinkedIn changes UI and selectors fail. Fallback logic and error paths.
- Files: `src/linkedin_mcp/graphs/message_send_graph.py`, `src/linkedin_mcp/graphs/employee_search_graph.py`
- Risk: Silent failures (pass statement in except blocks) mask broken automation.
- Priority: Critical - automation reliability depends on this.

**No Tests for CSV Import (Dataset Loading):**
- What's not tested: Large CSV parsing (company dataset), duplicate handling, malformed rows.
- Files: `scripts/cli.py` (import-dataset command)
- Risk: Dataset corruption or incomplete import not caught.
- Priority: Medium - one-time operation but affects entire outreach functionality.

**No Tests for Role Clustering Cache:**
- What's not tested: Title cache behavior, cache invalidation, memory growth with repeated classifications.
- Files: `src/core/agents/tools/role_clustering.py`
- Risk: Unbounded cache growth, stale classifications, incorrect clustering.
- Priority: Medium - affects clustering accuracy.

**No Tests for Session TTL Expiration:**
- What's not tested: Sessions actually expire after TTL, cleanup removes expired rows, database doesn't grow unbounded.
- Files: `src/core/api/services/session_store.py`, `src/core/db/agent_db.py`
- Risk: Database bloat, expired sessions returned to user.
- Priority: Medium - affects long-term stability.

---

*Concerns audit: 2026-02-11*
