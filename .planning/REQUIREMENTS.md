# Requirements: Serial LinkedIn Killer v3.0

**Defined:** 2026-02-12
**Core Value:** Content campaign system that publishes LLM-generated sentiment variants via LinkedIn API, collects engagement metrics, and learns which approach generates the best leads.

## v3.0 Requirements

Requirements for Content Campaign Intelligence milestone. Each maps to roadmap phases.

### Authentication

- [ ] **AUTH-01**: User can configure LinkedIn API credentials (client_id, client_secret) via config file or environment variables
- [ ] **AUTH-02**: User can authenticate via OAuth2 authorization code flow and receive access token stored in database
- [ ] **AUTH-03**: System tracks token expiration (60-day lifecycle) and alerts user 7 days before expiry
- [ ] **AUTH-04**: System detects expired/invalid tokens (401 responses), pauses affected campaigns, and notifies user with re-auth link
- [ ] **AUTH-05**: OAuth2 authentication context is fully separated from existing RPA browser session authentication

### Campaign Management

- [ ] **CAMP-01**: User can create a campaign with a base message, selected sentiments, and optional schedule
- [ ] **CAMP-02**: User can list all campaigns with status, variant count, and latest metrics summary
- [ ] **CAMP-03**: User can view a campaign's full details including all variants and their content
- [ ] **CAMP-04**: User can update a campaign's base message or schedule before publishing
- [ ] **CAMP-05**: User can delete a campaign (soft delete preserving historical data)
- [ ] **CAMP-06**: Campaign tracks lifecycle status: draft, scheduled, active, paused, completed, failed

### Content Generation

- [ ] **GEN-01**: System generates multiple content variants from a base message using LLM (Gemini or local provider via existing factory)
- [ ] **GEN-02**: System provides sentiment presets (urgency, authority, calm, empathy, curiosity, social proof, educational, provocative, inspirational, humorous)
- [ ] **GEN-03**: User can define custom sentiment prompts for variant generation
- [ ] **GEN-04**: User can review and manually edit generated variants before publishing
- [ ] **GEN-05**: System ensures content diversity between variants to reduce spam detection risk (>70% text difference)

### Publishing

- [ ] **PUB-01**: System publishes content to LinkedIn via Posts API (`/rest/posts`) with versioned headers (not deprecated UGC Posts API)
- [ ] **PUB-02**: User can manually trigger publishing of a single variant
- [ ] **PUB-03**: User can publish multiple variants with staggered timing (configurable interval, default 15-30 min)
- [ ] **PUB-04**: System stores LinkedIn post URN (share/ugcPost) after successful publish
- [ ] **PUB-05**: System handles publishing errors: 401 (token expired), 429 (rate limit), 422 (duplicate content)
- [ ] **PUB-06**: System publishes results to Kafka topic for async notification

### Metrics Collection

- [ ] **MET-01**: System polls LinkedIn Organization Share Statistics API for published post metrics on configurable interval (default 6 hours)
- [ ] **MET-02**: System stores time-series metrics snapshots: impressions, clicks, likes, comments, shares, engagement, unique impressions
- [ ] **MET-03**: User can view metrics for a campaign's variants via API endpoint
- [ ] **MET-04**: System calculates engagement velocity (snapshots at 6hr, 24hr, 48hr post-publish)
- [ ] **MET-05**: Metrics poller runs as background task within FastAPI lifespan (APScheduler)
- [ ] **MET-06**: System publishes metrics updates to Kafka topic for async notification

### Lead Attribution

- [ ] **LEAD-01**: System generates UTM parameters per variant for link tracking in post content
- [ ] **LEAD-02**: System attributes anonymous leads from engagement metric deltas (new clicks, likes, comments between snapshots)
- [ ] **LEAD-03**: User can view attributed leads per campaign and per variant via API endpoint
- [ ] **LEAD-04**: System accepts external lead capture webhooks with UTM parameter matching to variant/campaign

### Intelligence

- [ ] **INTEL-01**: System analyzes variant performance and identifies best/worst performing sentiments per campaign
- [ ] **INTEL-02**: System generates heuristic recommendations: pause low performers (<50% of median after 48hr), scale high performers (>150% of median)
- [ ] **INTEL-03**: User can view insights and recommendations via API endpoint
- [ ] **INTEL-04**: System compares variants with A/B testing framework (statistical significance between engagement rates)

### Infrastructure

- [ ] **INFRA-01**: Database schema extended with 5 new tables via Alembic migration (campaigns, campaign_variants, campaign_metrics, campaign_leads, linkedin_oauth_tokens)
- [ ] **INFRA-02**: Two new Kafka topics configured (campaign-publish-results, campaign-metrics-updates)
- [ ] **INFRA-03**: LinkedIn API client uses Community Management API with Posts API endpoint and versioned headers
- [ ] **INFRA-04**: Campaign configuration section added to agent.yaml (default sentiments, max variants, poll interval, LinkedIn API credentials)

## Future Requirements

Deferred beyond v3.0. Tracked but not in current roadmap.

### Advanced Attribution

- **ADV-ATTR-01**: Revenue attribution via CRM webhook integration (Salesforce, HubSpot)
- **ADV-ATTR-02**: Multi-touch attribution tracking (all variants a lead interacted with before conversion)
- **ADV-ATTR-03**: LinkedIn Conversions API integration for precise conversion tracking

### Advanced Analytics

- **ADV-ANAL-01**: Audience overlap analysis across variants
- **ADV-ANAL-02**: Advanced ML-based recommendations (beyond heuristics)
- **ADV-ANAL-03**: Sentiment analysis of post comments

### Platform Extension

- **ADV-PLAT-01**: Multi-platform publishing (Twitter/X, Facebook)
- **ADV-PLAT-02**: Image/video content generation and publishing
- **ADV-PLAT-03**: LinkedIn Advertising API integration (dark posts, sponsored content)
- **ADV-PLAT-04**: Real-time dashboards and UI

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Full social media scheduler | Competing with Buffer/Hootsuite; focus on LinkedIn campaign intelligence |
| Image/video generation | Different problem domain; text-only posts for v3.0 |
| Multi-platform publishing | LinkedIn API patterns don't translate; LinkedIn-first |
| Built-in CRM | Reinventing the wheel; integrate via webhooks if needed |
| Real-time dashboards | Over-engineering for MVP; API-first, defer UI |
| Auto-reply to comments | High-risk brand safety automation |
| Advertising API / Dark posts | Requires separate API approval and ad spend; organic-only for v3.0 |
| Comment sentiment analysis | Interesting but not core campaign intelligence value |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | — | Pending |
| AUTH-02 | — | Pending |
| AUTH-03 | — | Pending |
| AUTH-04 | — | Pending |
| AUTH-05 | — | Pending |
| CAMP-01 | — | Pending |
| CAMP-02 | — | Pending |
| CAMP-03 | — | Pending |
| CAMP-04 | — | Pending |
| CAMP-05 | — | Pending |
| CAMP-06 | — | Pending |
| GEN-01 | — | Pending |
| GEN-02 | — | Pending |
| GEN-03 | — | Pending |
| GEN-04 | — | Pending |
| GEN-05 | — | Pending |
| PUB-01 | — | Pending |
| PUB-02 | — | Pending |
| PUB-03 | — | Pending |
| PUB-04 | — | Pending |
| PUB-05 | — | Pending |
| PUB-06 | — | Pending |
| MET-01 | — | Pending |
| MET-02 | — | Pending |
| MET-03 | — | Pending |
| MET-04 | — | Pending |
| MET-05 | — | Pending |
| MET-06 | — | Pending |
| LEAD-01 | — | Pending |
| LEAD-02 | — | Pending |
| LEAD-03 | — | Pending |
| LEAD-04 | — | Pending |
| INTEL-01 | — | Pending |
| INTEL-02 | — | Pending |
| INTEL-03 | — | Pending |
| INTEL-04 | — | Pending |
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| INFRA-04 | — | Pending |

**Coverage:**
- v3.0 requirements: 39 total
- Mapped to phases: 0 (pending roadmap creation)
- Unmapped: 39

---
*Requirements defined: 2026-02-12*
*Last updated: 2026-02-12 after initial definition*
