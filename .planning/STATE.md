# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-12)

**Core value:** Content campaign system that publishes LLM-generated sentiment variants via LinkedIn API, collects engagement metrics, and learns which approach generates the best leads.
**Current focus:** v3.0 Content Campaign Intelligence -- Phase 10 (Content Generation)

## Current Position

Phase: 10 - Content Generation
Plan: 2/2
Status: In Progress
Last activity: 2026-02-12 -- Completed Phase 10 Plan 02 (Content Controller)

Progress: [█████.....] 50% (3.0/6 v3.0 phases complete)

## Performance Metrics

**Velocity (v2.1 + v2.2 + v3.0):**
- Total plans completed: 14
- Average duration: 2.9 min
- Total execution time: 0.66 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 1 | 132s | 132s |
| 02 | 1 | 153s | 153s |
| 03 | 1 | 165s | 165s |
| 04 | 1 | 207s | 207s |
| 05 | 1 | 280s | 280s |
| 06 | 2 | 389s | 195s |
| 07 | 1 | 234s | 234s |
| 08 | 2 | 517s | 259s |
| 09 | 2 | 250s | 125s |
| 10 | 2 | 340s | 170s |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

**v3.0 architecture decisions (from research):**
- LinkedIn API client lives in Core Agent (NOT MCP Server) -- separate from RPA auth
- OAuth2 via authlib, background polling via apscheduler
- Community Management API with Posts endpoint (`/rest/posts`), NOT deprecated UGC Posts API
- Organic posts only for v3.0 (no dark posts/ads)
- 5 new DB tables, 2 new Kafka topics
- Spam prevention: stagger posts 15-30 min, >70% text diversity between variants

**Phase 8 Plan 1 decisions:**
- Chose authlib over requests-oauthlib for OAuth2 (better LinkedIn provider integration)
- Set 6.0 hour default poll interval for metrics (balances freshness with API rate limits)
- Used String PKs with uuid4 for campaigns (supports distributed generation)
- No SQLAlchemy ForeignKey constraints (keeps schema simple, consistent with existing models)
- No refresh_token column in LinkedInOAuthToken (LinkedIn doesn't provide programmatic refresh)
- [Phase 08-02]: Used httpx for HTTP requests instead of authlib's OAuth2Session (KISS principle)
- [Phase 08-02]: Implemented sync client pattern (consistent with existing codebase)
- [Phase 08-02]: Token expiry warning threshold in CampaignConfig (7 days default)

**Phase 9 Plan 1 decisions:**
- Campaign service follows standalone service pattern (not AgentDB subclass) for CRUD operations
- Status transitions enforced via VALID_TRANSITIONS dict state machine
- Soft delete sets status='deleted' preserving all variants, metrics, and leads
- Only draft campaigns allow base_message/scheduled_at updates
- Variants created with empty content field (filled by Phase 10)
- Latest metrics aggregation uses subquery to get max polled_at per variant

**Phase 9 Plan 2 decisions:**
- Campaign controller follows outreach_controller pattern (Depends injection, lazy import getter)
- Default sentiments/organization_urn applied from config if not provided in request
- POST /api/campaigns returns 201 with full campaign details (not just ID)
- Status transitions return 404 for not found, 400 for invalid transitions
- Error categorization: ValueError with "not found" -> 404, other ValueError -> 400

**Phase 10 Plan 1 decisions:**
- Used difflib.SequenceMatcher for text diversity (stdlib, no external deps)
- Set 0.7 (70%) default diversity threshold for spam prevention
- ContentGenerationService only regenerates empty variants (supports partial regeneration)
- LLM prompt includes 1300 character limit for LinkedIn post constraints
- Custom sentiment prompts supported alongside 10 presets

**Phase 10 Plan 2 decisions:**
- Generation endpoint accepts optional custom_prompts for flexibility
- Edit endpoint validates both variant_id and campaign_id for security
- ContentGenerationService initialized in app lifespan with shared DB engine
- Error handling follows established pattern: ValueError with "not found" -> 404, other ValueError -> 400

### Pending Todos

- Verify LinkedIn Marketing API Standard tier access is approved before starting Phase 8
- Check PyPI for latest stable authlib and apscheduler versions during Phase 8

### Blockers/Concerns

- Development tier has 500 calls/app/24hrs limit -- Standard tier required for multi-variant campaigns
- OAuth2 tokens expire after 60 days with no programmatic refresh (manual re-auth required)
- LLM content spam detection thresholds not publicly documented (>70% text difference is educated guess)

## Session Continuity

Last session: 2026-02-12
Stopped at: Completed Phase 10 Plan 02 (Content Controller)
Resume file: None
