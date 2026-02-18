# Project Research Summary

**Project:** Serial LinkedIn Killer - v3.0 Content Campaign Intelligence
**Domain:** LinkedIn Marketing API integration with LLM-powered sentiment-driven content variants
**Researched:** 2026-02-12
**Confidence:** MEDIUM (official LinkedIn docs verified, library versions unverified, no real-time web access)

## Executive Summary

v3.0 adds LinkedIn Marketing API integration to enable content campaign intelligence: LLM-generated content variants with different sentiment angles, programmatic publishing to LinkedIn, engagement metrics tracking, and lead attribution analytics. The research reveals this is a **minimal extension** of the existing stack rather than a major architectural shift. The existing FastAPI + SQLAlchemy + LangChain + Kafka infrastructure already handles 90% of requirements — only OAuth2 library (authlib), scheduling (apscheduler), and database schema extensions are needed.

The recommended approach separates Marketing API concerns from existing RPA (browser automation) concerns. Marketing API calls live in Core Agent as a new provider, NOT in MCP Server which handles Selenium-based scraping. This architectural separation prevents authentication state desynchronization and maintains clear boundaries. Content generation reuses the existing LLM client factory (Gemini/local models), while metrics polling runs as an APScheduler background task within FastAPI's lifespan.

The critical risk is **LinkedIn Marketing API access tier confusion**. Development tier (default) has severe rate limits (500 API calls/day) that make multi-variant campaigns impossible. Standard tier requires support ticket approval (2-4 weeks lead time) and explicit justification. Apply for Standard tier access BEFORE starting development. Secondary risks include OAuth2 token expiration (60 days, manual re-auth required), content spam detection (LLM-generated variants flagged as bot activity), and metrics delay/sampling (24-48 hour lag for organic post impressions). All are mitigated through proactive user alerts, rate limiting, content diversity prompts, and delayed analytics polling.

## Key Findings

### Recommended Stack

The existing stack (FastAPI, SQLAlchemy, LangChain/Gemini, Kafka, SQLite) provides most infrastructure. Only two new dependencies required: **authlib** for OAuth2 token management (LinkedIn's authorization code flow with 60-day tokens) and **apscheduler** for periodic metrics polling (6-hour intervals to respect API rate limits). Alternative schedulers like Celery/RQ rejected as overkill — they require Redis/RabbitMQ brokers for simple polling tasks. No official LinkedIn Python SDK exists; build thin wrapper around httpx (already in stack) + authlib rather than rely on unmaintained unofficial libraries.

**Core new dependencies:**
- **authlib ^1.3.0**: OAuth2 token management (authorization code flow, token refresh) — industry-standard library, async-compatible with FastAPI
- **apscheduler ^3.10.4**: Background metrics polling scheduler — lightweight, in-process, integrates with FastAPI lifespan, uses existing SQLite for job persistence

**Reused existing stack:**
- **httpx**: HTTP client for LinkedIn API calls (already present)
- **sqlalchemy + alembic**: Campaign/variant/metrics tables (extend existing models.py)
- **LangChain + Gemini**: Content generation (reuse get_llm_client() factory)
- **FastAPI**: Campaign management endpoints (follow existing controller pattern)
- **Kafka**: Publish results and metrics updates (add 2 new topics)

**Critical version gap:** authlib 1.3.0 and apscheduler 3.10.4 availability not verified (training data January 2025, current February 2026). Check PyPI for latest stable versions during Phase 1 dependency installation.

### Expected Features

**Must have (table stakes):**
- Campaign CRUD lifecycle (create, read, update, delete campaigns with metadata)
- Content variant storage (each campaign → N variants with different sentiment text)
- Single-variant publishing (prove LinkedIn API integration works)
- Manual publishing trigger (user initiates posts via API endpoint)
- Basic engagement metrics (impressions, likes, shares, comments from LinkedIn API)
- Campaign status tracking (draft/active/paused/completed state machine)
- Error handling & retry (rate limits, transient failures, OAuth expiration)

**Should have (differentiators):**
- **LLM sentiment variant generation**: Input: product description → Output: 5-10 variants with tonal diversity (urgency, authority, calm, empathy, curiosity, etc.)
- **Parallel multi-variant campaigns**: Publish variants on different schedules, track separately
- **Lead fingerprinting**: Attribution linking inbound leads to campaign/variant (aggregate-based, LinkedIn API doesn't provide individual user engagement data)
- **Sentiment preset library**: Pre-engineered prompts for common tones (professional, enthusiastic, educational, provocative, storytelling)
- **Custom sentiment definitions**: Users define own tones ("Write in tone of CEO addressing shareholders")
- **Performance-based recommendations**: Analyze metrics, suggest "pause low performers, scale high performers"
- **A/B testing framework**: Statistical significance testing between variants
- **Engagement velocity tracking**: First 1hr, 6hr, 24hr engagement rates

**Defer (v2+):**
- Revenue attribution (requires CRM integration — Salesforce, HubSpot)
- Real-time dashboards (Kafka + periodic polling sufficient; defer UI)
- Multi-platform publishing (LinkedIn-first, extensible architecture for Twitter/Facebook later)
- Sentiment analysis of comments (collect comment text, defer NLP analysis)
- Auto-reply to comments (high-risk brand safety concern)
- Image/video generation (text-only posts initially)

**Critical path for MVP:** Campaign CRUD → Variant storage → LLM generation → Single-variant publish → Engagement metrics → Lead fingerprinting

### Architecture Approach

Extend Core Agent (port 8080) with new providers and services. MCP Server (port 3000) remains unchanged — it handles browser automation (job search, easy apply, employee search) via Selenium. Marketing API calls bypass browser automation entirely. This separation prevents authentication state desynchronization (RPA cookies ≠ OAuth2 tokens) and maintains fault isolation.

**Major components:**
1. **LinkedIn API Client** (`src/core/providers/linkedin_api_client.py`) — OAuth2 authorization flow, UGC Post creation, Share Statistics API. Wraps httpx + authlib. NOT added to MCP Server.
2. **Campaign Service** (`src/core/api/services/campaign_service.py`) — Business logic: CRUD, scheduling, publishing. Follows existing OutreachService pattern (async via thread pool, Kafka results publishing).
3. **Content Service** (`src/core/api/services/content_service.py`) — LLM-based variant generation using existing `get_llm_client()` factory. Sentiment presets → LangChain PromptTemplate variations.
4. **Metrics Poller** (`src/core/services/metrics_poller.py`) — APScheduler background task (6-hour intervals). Polls LinkedIn Share Statistics API for published campaigns, stores time-series snapshots in SQLite.
5. **Lead Engine** (`src/core/services/lead_engine.py`) — Delta-based attribution (compare current vs previous metrics snapshot, attribute new clicks/likes/comments as anonymous leads).
6. **Campaign Controller** (`src/core/api/controllers/campaign_controller.py`) — FastAPI REST endpoints: POST /api/campaigns, GET /api/campaigns/{id}/metrics, POST /api/campaigns/{id}/publish

**New database tables** (extend models.py):
- **campaigns**: id, organization_urn, base_message, created_at, scheduled_at, status
- **campaign_variants**: id, campaign_id, sentiment, content, ugc_post_urn, published_at, is_selected
- **campaign_metrics**: id, campaign_id, variant_id, polled_at, impressions, clicks, likes, comments, shares, engagement (time-series snapshots)
- **campaign_leads**: id, campaign_id, variant_id, lead_source (click/like/comment), attributed_at, fingerprint
- **linkedin_oauth_tokens**: organization_urn, access_token, refresh_token, expires_at, created_at

**New Kafka topics:**
- **campaign-publish-results**: Notify CLI when campaign published (producer: Campaign Service)
- **campaign-metrics-updates**: Notify CLI when metrics polled (producer: Metrics Poller)

**Data flow patterns:**
- Campaign creation → Content Service (LLM generation) → AgentDB
- Publishing → LinkedIn API Client (OAuth2 + UGC Post) → Kafka → CLI notification
- Metrics polling → LinkedIn API Client (Share Statistics) → AgentDB (time-series insert) → Kafka
- Lead attribution → Lead Engine (delta comparison) → AgentDB

**Background task integration:** Metrics poller starts in app.py lifespan startup (APScheduler.start()), shuts down in lifespan shutdown. Uses existing AgentDB connection management and SQLAlchemy job store for persistence.

### Critical Pitfalls

1. **Marketing API Access Tier Misunderstanding (CRITICAL)** — Development tier (default after approval) has 500 API calls/day limit. Multi-variant campaigns require 50+ calls minimum (5 variants × 10 posts = 50 creates + 50 analytics reads). Development tier expires after 12 months. Standard tier requires support ticket with justification, 2-4 weeks approval time. **Prevention:** Apply for Standard tier immediately, request all scopes upfront (`rw_organization_admin`, `w_organization_social`, `r_organization_social`), block API-dependent phases until approval confirmed. **Phase 0 (pre-dev) gate.**

2. **OAuth2 Token Lifecycle Mismanagement (CRITICAL)** — Access tokens expire after 60 days. No programmatic refresh tokens (restricted to select partners). All API calls fail with 401 Unauthorized when expired. Campaigns silently stop publishing. **Prevention:** Track token expiration (store `expires_in` from response), alert user 7 days before expiration ("LinkedIn API access expiring, re-authorize now"), detect 401 errors → pause campaign → notify user → provide re-auth link. Alternative: LinkedIn Developer Portal Token Generator for testing. **Phase 1 (authentication setup).**

3. **Content Spam Detection False Positives (CRITICAL)** — LLM-generated variants flagged as spam by LinkedIn's ML systems. Posts shadow-banned (0 impressions despite followers), account restricted, content removed. Detection criteria not public, but patterns include: identical structure, high frequency, excessive hashtags, all-caps, duplicate content. **Prevention:** Space variant posts 15-30 minutes apart (mimic human cadence), LLM prompt engineering for >70% text difference, max 3 hashtags, no URL shorteners, test with 2 variants → wait 24hrs → check `contentCertificationRecord.spamRestriction`, human review gate before publishing. **Phase 3 (content generation) + Phase 4 (publishing).**

4. **Mixing RPA Session State with OAuth2 Tokens (CRITICAL)** — Using Selenium browser sessions (cookies) for RPA AND OAuth2 tokens for API creates two independent authentication contexts. LinkedIn may flag this as suspicious (same account, two "different applications"). RPA cookies expire independently from OAuth2 tokens → race conditions (API works but RPA fails). **Prevention:** Separate authentication contexts entirely, never reuse browser cookies for API calls, document user requirements clearly (RPA needs email/password, API needs OAuth2 app credentials), implement per-feature authentication check. **Phase 1 (architecture decision).**

5. **Metrics Accuracy and Delay (MODERATE)** — LinkedIn analytics APIs return sampled data for organic posts with 24-48 hour delays. Engagement metrics (likes, comments, shares) update near-real-time, but impressions/CTR delayed. Campaign attribution unreliable when comparing variants posted in same time window. **Prevention:** Don't poll analytics until 48 hours post-publish for organic content, prioritize engagement-first metrics (likes/comments/shares) over impressions for early signals, acknowledge uncertainty in UI ("Estimated impressions: ~2,400 ±20%"), compare trends not absolutes. **Phase 5 (analytics).**

6. **Dark Posts vs Organic Posts Confusion (MODERATE)** — "Dark posts" (`visibility: DARK`) are ad-only content requiring Advertising API access + ad campaign setup. They're NOT "draft posts" — can't create dark post, test it, then publish organically. Mixing dark/organic in same campaign architecture creates permission errors. **Prevention:** Use organic-only (`visibility: PUBLIC`) for Phases 1-5, defer ads to Phase 6+ if Advertising API approved, clear naming ("Content Variants" not "Dark Posts"). **Phase 2 (architecture design).**

## Implications for Roadmap

Based on research, suggested 6-phase structure with clear dependency ordering:

### Phase 1: API Foundation & Authentication
**Rationale:** OAuth2 flow is prerequisite for all LinkedIn API operations. Token storage + expiration tracking prevents silent failures. Must verify Standard tier access approved before proceeding.

**Delivers:**
- LinkedIn API Client with OAuth2 authorization code flow
- Token storage in SQLite (linkedin_oauth_tokens table)
- Token expiration tracking and user alerts
- Database schema (5 new tables via Alembic migration)
- Kafka topic configuration (2 new topics)

**Addresses (from FEATURES.md):**
- Error handling & retry (token lifecycle)
- Campaign status tracking (DB schema foundation)

**Avoids (from PITFALLS.md):**
- OAuth2 token lifecycle mismanagement (Pitfall 2)
- Mixing RPA + API authentication (Pitfall 4)
- Marketing API tier misunderstanding (Pitfall 1) — gate at Phase 0

**Uses (from STACK.md):**
- authlib for OAuth2
- httpx for HTTP client (existing)
- SQLAlchemy for token persistence

**Phase Gate:** Verify Standard tier Marketing API access approved. If only Development tier, warn about rate limits and defer to Phase 6.

---

### Phase 2: Campaign Management Core
**Rationale:** CRUD operations provide foundation for content variants. State machine (draft/scheduled/published) prevents invalid publishing operations.

**Delivers:**
- Campaign Service (CRUD logic, follows OutreachService pattern)
- Campaign Controller (FastAPI REST endpoints)
- Pydantic schemas for request/response validation
- Campaign status state machine

**Addresses:**
- Campaign CRUD lifecycle (table stakes)
- Content variant storage (table stakes)
- Campaign status tracking (table stakes)

**Implements (from ARCHITECTURE.md):**
- Campaign Service with async via thread pool
- Campaign Controller with FastAPI routes
- AgentDB extension methods (insert_campaign, get_campaign_metrics)

**Avoids:**
- Data model fragmentation (warning from PITFALLS.md) — unified schema design

**Phase Gate:** None (standard CRUD patterns)

---

### Phase 3: LLM Content Variant Generation
**Rationale:** Content generation is core differentiator. Must engineer prompts for diversity to avoid spam detection. Human review gate ensures quality before publishing.

**Delivers:**
- Content Service using existing get_llm_client() factory
- Sentiment preset library (10 presets: urgency, authority, calm, empathy, curiosity, social proof, educational, provocative, inspirational, humorous)
- Custom sentiment prompt support
- Content diversity validation (>70% text difference between variants)
- Human review workflow

**Addresses:**
- LLM sentiment variant generation (differentiator)
- Sentiment preset library (differentiator)
- Custom sentiment definitions (differentiator)

**Uses (from STACK.md):**
- LangChain + Gemini (existing)
- LLM client factory pattern (reuse)

**Avoids (from PITFALLS.md):**
- Content spam detection (Pitfall 3) — diversity prompts, max 3 hashtags, no URL shorteners
- LLM content quality for professional platform (Pitfall 9) — prompts include "Write as SME, include 1 data point, avoid clichés"

**Research Flag:** Moderate — LLM prompt engineering for spam avoidance requires testing iteration. Plan 2-3 days for prompt tuning.

---

### Phase 4: LinkedIn Publishing Integration
**Rationale:** Single-variant publishing proves end-to-end flow (OAuth → UGC Post API → store LinkedIn URN). Rate limiting prevents spam detection. Error handling critical for OAuth expiration.

**Delivers:**
- LinkedIn API Client UGC Post creation method
- Publishing workflow (manual trigger initially, scheduled for Phase 5)
- Rate limiting (15-30 minute intervals between variants)
- Duplicate content detection handling
- Error handling (401 token expiration, 429 rate limits, 422 duplicate content)
- Kafka publish results notification

**Addresses:**
- Single-variant publishing (table stakes)
- Manual publishing trigger (table stakes)
- Error handling & retry (table stakes)
- Parallel multi-variant campaigns (differentiator) — infrastructure ready

**Implements (from ARCHITECTURE.md):**
- LinkedIn API Client UGC Post method
- Publishing flow via Campaign Service

**Avoids (from PITFALLS.md):**
- Content spam detection (Pitfall 3) — rate limiting
- Duplicate content restriction (Pitfall 13) — add unique suffix per variant
- Dark posts vs organic confusion (Pitfall 6) — organic-only (`visibility: PUBLIC`)

**Phase Gate:** Test with 2 variants, wait 24 hours, verify no `spamRestriction` flag before scaling.

---

### Phase 5: Engagement Analytics & Metrics Polling
**Rationale:** Metrics are value driver for variant comparison. 48-hour delay required for accurate organic post impressions. Background polling respects API rate limits.

**Delivers:**
- Metrics Poller (APScheduler background task, 6-hour intervals)
- LinkedIn API Client Share Statistics method
- Time-series metrics storage (campaign_metrics table)
- Engagement velocity tracking (1hr, 6hr, 24hr snapshots)
- Kafka metrics update notifications
- Metrics API endpoint (GET /api/campaigns/{id}/metrics)

**Addresses:**
- Basic engagement metrics (table stakes)
- Engagement velocity tracking (differentiator)
- A/B testing framework (differentiator) — data collection phase

**Uses (from STACK.md):**
- apscheduler for background polling
- FastAPI lifespan for scheduler initialization

**Avoids (from PITFALLS.md):**
- Metrics accuracy and delay (Pitfall 5) — 48hr wait period, trend-based comparisons
- Rate limit alert noise (Pitfall 8) — batch API calls (50 posts per request), track client-side quotas
- Synchronous polling in request handler (anti-pattern) — background task only

**Implements (from ARCHITECTURE.md):**
- Metrics Poller with APScheduler
- Background task initialization in app.py lifespan

**Research Flag:** Low — standard polling patterns, well-documented LinkedIn Share Statistics API.

---

### Phase 6: Lead Attribution & Intelligence
**Rationale:** Lead fingerprinting ties campaigns to business outcomes. Delta-based attribution (aggregate only, no individual user data from LinkedIn API). Performance recommendations enable optimization.

**Delivers:**
- Lead Engine (delta-based attribution comparing metrics snapshots)
- Campaign leads storage (campaign_leads table)
- Learning Engine (variant performance analysis, heuristic-based recommendations)
- UTM parameter generation for variant tracking
- Webhook endpoint for external lead capture system integration
- Insights API endpoint (GET /api/campaigns/{id}/insights)

**Addresses:**
- Lead fingerprinting (differentiator)
- Performance-based recommendations (differentiator)
- A/B testing framework (differentiator) — analysis phase

**Implements (from ARCHITECTURE.md):**
- Lead Engine with delta comparison
- Learning Engine with variant analysis

**Avoids (from PITFALLS.md):**
- Lead attribution multi-touch complexity (Pitfall 10) — acknowledge "last-touch only" limitation, document for users

**Research Flag:** Moderate — Attribution logic requires statistical heuristics tuning (median ± 1 std dev for high/low performers). Plan 3-4 days for recommendation algorithm validation.

**Phase Gate:** Verify sufficient metrics data (at least 48 hours post-publish, 2+ snapshots per variant) before enabling attribution.

---

### Phase Ordering Rationale

**Dependency chain:**
- Phase 1 (API + Auth) → all others (OAuth2 prerequisite)
- Phase 2 (Campaign CRUD) → Phase 3 (Content Generation) → Phase 4 (Publishing)
- Phase 4 (Publishing) → Phase 5 (Metrics Polling) → Phase 6 (Lead Attribution)

**Architectural groupings:**
- Phases 1-2: Foundation (database, API client, CRUD)
- Phases 3-4: Content pipeline (generation → publishing)
- Phases 5-6: Intelligence (metrics → attribution → recommendations)

**Pitfall avoidance:**
- Phase 0 gate (Marketing API Standard tier approval) prevents Development tier rate limit disaster
- Phase 1 (OAuth2 token tracking) prevents silent failures after 60 days
- Phase 3 (content diversity prompts) + Phase 4 (rate limiting) prevent spam detection
- Phase 5 (48hr delay) prevents premature optimization from incomplete metrics
- Organic-only architecture (Phases 1-5) defers Advertising API complexity to v4.0+

**Incremental value delivery:**
- Phase 2: Campaign management (no LinkedIn dependency yet, testable immediately)
- Phase 3: Content generation (LLM integration testable independently)
- Phase 4: First LinkedIn API integration (publishing proof-of-concept)
- Phase 5: Analytics value (variant comparison data)
- Phase 6: Business outcome (lead attribution, ROI calculation)

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (Content Generation):** LLM prompt engineering for spam avoidance requires iteration. No documented benchmarks for LinkedIn's spam detection thresholds. Plan testing cycles with small batches.
- **Phase 6 (Lead Attribution):** Statistical heuristics for performance recommendations need tuning. Delta-based attribution assumptions (e.g., "new clicks = new leads") may not hold — requires validation against actual CRM data if available.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (API Foundation):** OAuth2 authorization code flow well-documented by LinkedIn. Standard FastAPI patterns. Skip research.
- **Phase 2 (Campaign CRUD):** Standard REST API + SQLAlchemy patterns. Existing codebase has OutreachService as template. Skip research.
- **Phase 4 (Publishing):** LinkedIn UGC Post API well-documented. httpx HTTP client usage straightforward. Skip research.
- **Phase 5 (Metrics Polling):** APScheduler integration standard, LinkedIn Share Statistics API documented. Skip research.

**Overall research needs:** LOW for Phases 1, 2, 4, 5 (standard patterns + official docs). MODERATE for Phases 3, 6 (experimentation required).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core recommendations (authlib, apscheduler, httpx reuse) sound based on training data, but library versions unverified (authlib 1.3.0, apscheduler 3.10.4 availability unknown for Feb 2026). Requires PyPI check Phase 1. |
| Features | HIGH | Feature landscape based on standard content marketing automation patterns. LinkedIn Marketing API capabilities verified via official Microsoft Learn documentation (updated 2026-02-11). Table stakes vs differentiators align with existing RPA system analysis. |
| Architecture | HIGH | Architecture patterns match existing Core Agent + MCP Server separation. Service layer pattern verified in codebase (OutreachService). LLM client factory reuse confirmed. Database extensions follow existing models.py patterns. Background task integration via APScheduler standard for FastAPI. |
| Pitfalls | MEDIUM | Critical pitfalls (API tier, OAuth2 lifecycle, spam detection) verified in official LinkedIn docs. Integration-specific pitfalls (RPA + API coexistence) inferred from codebase analysis but unverified in production. No documented cases of IP correlation risk (theoretical). |

**Overall confidence:** MEDIUM

### Gaps to Address

**Library versions (MEDIUM priority):**
- authlib 1.3.0 and apscheduler 3.10.4 availability unverified (training data Jan 2025, current Feb 2026)
- **Resolution:** Check PyPI for latest stable versions during Phase 1 dependency installation. Fallback: authlib 1.2.x + apscheduler 3.9.x known stable.

**LinkedIn API endpoint specifics (LOW priority):**
- UGC Post API exact request schema not verified with live API (official docs reviewed but no test calls)
- Share Statistics API batch query parameter format assumed based on docs
- **Resolution:** Test OAuth2 flow in Phase 1 to catch integration issues early. Adjust endpoint URLs/schemas if LinkedIn updated API since docs review.

**LLM content quality benchmarks (MEDIUM priority):**
- No LinkedIn-specific data on what engagement rates constitute "good" performance for automated content
- Spam detection thresholds not publicly documented (>70% text difference is educated guess)
- **Resolution:** Start with conservative approach (2 variants, 30-minute spacing, human review). Iterate based on Phase 4 test results. Monitor `contentCertificationRecord` field.

**Lead attribution accuracy (LOW priority):**
- Delta-based attribution assumes "new clicks = new leads," but LinkedIn API only provides aggregate counts (no individual user data due to privacy)
- Multi-touch attribution not possible without external CRM integration
- **Resolution:** Document limitation clearly ("last-touch attribution only, anonymous aggregate"). Phase 6 can add CRM webhook integration for higher-fidelity attribution if user provides CRM access.

**RPA + API coexistence risks (LOW priority):**
- Theoretical risk: LinkedIn correlates API app ID with IP address, sees both API calls and suspicious browser activity from same IP
- No documented cases of this causing issues
- **Resolution:** Accept risk for MVP (low probability). If account flags appear, deploy Core Agent (RPA) and Campaign Manager (API) in separate Docker containers with different IPs. Document in runbook.

**Rate limit specifics (MEDIUM priority):**
- Share Statistics API rate limits not publicly documented by LinkedIn. Conservative estimate: ~100 requests/day per app.
- 6-hour polling interval assumes rate limits allow batch calls for 50 posts every 6 hours (8 API calls per day for 400 posts total)
- **Resolution:** Monitor response headers (`X-RateLimit-Remaining` if provided). If 429 Too Many Requests received, increase polling interval to 12 hours. Implement exponential backoff.

## Sources

### Primary (HIGH confidence)
- [LinkedIn Marketing API Overview](https://learn.microsoft.com/en-us/linkedin/marketing/) — API structure, versioning (li-lms-2026-01), product offerings
- [LinkedIn UGC Post API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/ugc-post-api) — Endpoint structure, permissions (`w_organization_social`, `r_organization_social`), schema for ugcPosts, max text length (3000 chars)
- [LinkedIn Share Statistics API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/share-statistics) — Metrics schema (impressionCount, clickCount, likeCount, commentCount, shareCount, engagement), 12-month rolling window, time-bound vs lifetime stats
- [LinkedIn OAuth2 Authorization Code Flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow) — 3-legged OAuth flow, token lifespan (60 days), required scopes, redirect URI validation
- [LinkedIn Increasing Access (API Tiers)](https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access) — Development vs Standard tier, rate limits (500/day Development, higher for Standard), approval process
- [LinkedIn Rate Limits](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits) — Rate limit structure, alerts at 75% threshold, 429 error responses

### Secondary (MEDIUM confidence)
- Existing codebase analysis:
  - `/src/linkedin_mcp/services/linkedin_auth_service.py` — RPA session cookie authentication via Selenium
  - `/src/core/api/services/outreach_service.py` — Service layer async pattern (thread pool, Kafka results)
  - `/src/core/providers/llm_client.py` — LLM client factory (Gemini/local)
  - `/src/core/db/models.py` — Database patterns (SQLAlchemy + Alembic)
  - `/src/core/api/app.py` — FastAPI lifespan pattern
  - `.planning/codebase/ARCHITECTURE.md` — System architecture analysis (Core Agent + MCP Server separation)
- authlib documentation (2024 knowledge) — OAuth2 library capabilities
- APScheduler documentation (2024 knowledge) — Background task scheduling patterns
- Social media campaign management best practices (2024 knowledge) — Content variant testing, A/B testing frameworks
- Lead attribution and UTM tracking standards (2024 knowledge) — Web analytics patterns

### Tertiary (LOW confidence, requires validation)
- LinkedIn spam detection patterns — Inferred from general anti-spam heuristics, not LinkedIn-specific documentation
- Rate limit specifics for Share Statistics API — Not publicly documented, conservative estimate based on standard LinkedIn API limits
- RPA + API IP correlation risk — Theoretical, no documented cases

---

*Research completed: 2026-02-12*
*Ready for roadmap: YES*
*Pre-development gate: Verify LinkedIn Marketing API Standard tier access approved*
