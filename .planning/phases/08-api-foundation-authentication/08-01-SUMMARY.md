---
phase: 08-api-foundation-authentication
plan: 01
subsystem: core-infrastructure
tags: [dependencies, configuration, database, kafka, oauth]
dependency-graph:
  requires: []
  provides: [campaign-config, campaign-db-schema, campaign-topics]
  affects: [config-loader, db-models, queue-config]
tech-stack:
  added: [authlib-1.6.7, apscheduler-3.11.2]
  patterns: [oauth2-config, campaign-config-management, db-migration-pattern]
key-files:
  created:
    - alembic/versions/20260212_1600_e7dc9d6ea445_add_campaign_tables_and_oauth_tokens.py
  modified:
    - pyproject.toml
    - src/config/config_loader.py
    - config/agent.yaml
    - src/core/db/models.py
    - src/core/queue/config.py
    - src/core/queue/producer.py
decisions:
  - Chose authlib for OAuth2 token management (industry standard, well-maintained)
  - Set 6.0 hour default poll interval for metrics (balances freshness with API rate limits)
  - Used String PKs with uuid4 for campaigns (supports distributed generation)
  - No SQLAlchemy ForeignKey constraints (keeps schema simple, consistent with existing models)
  - No refresh_token column in LinkedInOAuthToken (LinkedIn doesn't provide programmatic refresh)
metrics:
  duration: 294s
  completed: 2026-02-12T19:02:25Z
  tasks: 3
  commits: 3
---

# Phase 08 Plan 01: API Foundation & Authentication Summary

**One-liner:** OAuth2 configuration, campaign database schema (5 tables), and Kafka topics for LinkedIn API integration.

## Tasks Completed

### Task 1: Add dependencies and campaign configuration
- **Commit:** 7f1e712
- **Files:** pyproject.toml, poetry.lock, src/config/config_loader.py, config/agent.yaml
- **What:** Added authlib (OAuth2) and apscheduler (background polling) dependencies. Created LinkedInAPIConfig and CampaignConfig pydantic models with env var overrides for client_id, client_secret, redirect_uri, organization_urn. Added linkedin_api and campaign sections to agent.yaml with sensible defaults (5 sentiments, 6hr poll interval, 15-30min post stagger).

### Task 2: Add campaign database models and migration
- **Commit:** 39c18c6
- **Files:** src/core/db/models.py, alembic/versions/20260212_1600_e7dc9d6ea445_*.py
- **What:** Added 5 new SQLAlchemy models: Campaign (base message, status, scheduling), CampaignVariant (sentiment-based content variants with LinkedIn URNs), CampaignMetric (engagement metrics per variant), CampaignLead (attribution tracking), LinkedInOAuthToken (60-day access tokens). Generated and applied Alembic migration with indexes on campaign_id, variant_id, organization_urn, status.

### Task 3: Add campaign Kafka topic constants
- **Commit:** feb5b34
- **Files:** src/core/queue/config.py, src/core/queue/producer.py
- **What:** Added TOPIC_CAMPAIGN_PUBLISH_RESULTS and TOPIC_CAMPAIGN_METRICS_UPDATES constants. Included both in ALL_TOPICS for automatic creation on startup. Re-exported from producer.py for downstream use.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Fixed Alembic database state mismatch**
- **Found during:** Task 2, migration generation
- **Issue:** Database contained columns from migration 001 but Alembic version table was empty, causing "duplicate column name: company_name" error when attempting to run `alembic upgrade head`
- **Fix:** Ran `alembic stamp 001` to mark existing migration as applied without re-running it, allowing new migration to be generated
- **Files modified:** None (state-only fix)
- **Commit:** N/A (not code change)

## Verification Results

All verification checks passed:
1. ✅ `poetry install --no-root` succeeded with authlib and apscheduler resolved
2. ✅ Config loads with linkedin_api.redirect_uri and campaign.poll_interval_hours defaults
3. ✅ `alembic upgrade head` succeeded (5 new tables created)
4. ✅ All 5 models (Campaign, CampaignVariant, CampaignMetric, CampaignLead, LinkedInOAuthToken) import cleanly
5. ✅ ALL_TOPICS contains 6 topics (4 existing + 2 new)

## Key Decisions Made

1. **authlib over requests-oauthlib:** authlib is more actively maintained and has better OAuth2 provider integration for LinkedIn's 3-legged OAuth flow.

2. **6-hour poll interval default:** Balances metric freshness with LinkedIn's rate limits (Development tier: 500 calls/app/24hrs). Can be adjusted via config.

3. **String PKs with uuid4 for campaigns:** Enables distributed campaign generation without coordination. Consistent with production patterns for distributed systems.

4. **No refresh_token column:** LinkedIn OAuth2 tokens have 60-day expiry with NO programmatic refresh (manual re-auth required). Storing refresh_token would be misleading.

5. **No SQLAlchemy ForeignKey constraints:** Keeps schema simple and consistent with existing models (Company, SearchResult, MessageSent). Indexes on campaign_id/variant_id provide query performance without referential integrity overhead.

## Impact Analysis

**Downstream Dependencies:**
- Phase 8 Plan 2 (OAuth Implementation) will use LinkedInAPIConfig and LinkedInOAuthToken
- Phase 9 (Variant Generation) will use CampaignConfig.default_sentiments and max_variants
- Phase 10 (Publishing) will use TOPIC_CAMPAIGN_PUBLISH_RESULTS and post_stagger_minutes
- Phase 11 (Metrics Collection) will use CampaignMetric model and TOPIC_CAMPAIGN_METRICS_UPDATES

**Configuration:**
- Env vars: LINKEDIN_API_CLIENT_ID, LINKEDIN_API_CLIENT_SECRET, LINKEDIN_API_REDIRECT_URI, LINKEDIN_API_ORGANIZATION_URN
- Config sections: linkedin_api, campaign (loaded from agent.yaml with overrides)

**Database:**
- New tables: campaigns, campaign_variants, campaign_metrics, campaign_leads, linkedin_oauth_tokens
- Indexes: organization_urn, status, campaign_id (2x), variant_id (2x)

**Kafka:**
- New topics: campaign-publish-results, campaign-metrics-updates (auto-created on startup via ensure_topics())

## Self-Check: PASSED

**Created files verified:**
```
FOUND: alembic/versions/20260212_1600_e7dc9d6ea445_add_campaign_tables_and_oauth_tokens.py
```

**Commits verified:**
```
FOUND: 7f1e712 (Task 1: dependencies and config)
FOUND: 39c18c6 (Task 2: database models and migration)
FOUND: feb5b34 (Task 3: Kafka topics)
```

**Models verified:**
```
✓ Campaign, CampaignVariant, CampaignMetric, CampaignLead, LinkedInOAuthToken all importable
```

**Config verified:**
```
✓ linkedin_api.client_id, linkedin_api.redirect_uri, campaign.max_variants all load from agent.yaml
```

**Topics verified:**
```
✓ TOPIC_CAMPAIGN_PUBLISH_RESULTS and TOPIC_CAMPAIGN_METRICS_UPDATES in ALL_TOPICS (count=6)
```
