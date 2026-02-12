# Roadmap: Serial LinkedIn Killer

## Milestones

- [x] **v2.1 Gemini LLM Integration** -- Phases 1-3 (shipped 2026-02-11)
- [x] **v2.2 RAM Safety Caps** -- Phases 4-7 (shipped 2026-02-12)
- [ ] **v3.0 Content Campaign Intelligence** -- Phases 8-13 (active)

## Phases

<details>
<summary>v2.1 Gemini LLM Integration (Phases 1-3) -- SHIPPED 2026-02-11</summary>

- [x] Phase 1: Dependency Setup (1/1 plans) -- completed 2026-02-11
- [x] Phase 2: Provider Configuration & Client Factory (1/1 plans) -- completed 2026-02-11
- [x] Phase 3: Integration & Validation (1/1 plans) -- completed 2026-02-11

</details>

<details>
<summary>v2.2 RAM Safety Caps (Phases 4-7) -- SHIPPED 2026-02-12</summary>

- [x] Phase 4: Quick Wins (1/1 plans) -- completed 2026-02-11
- [x] Phase 5: Streaming Queries (1/1 plans) -- completed 2026-02-11
- [x] Phase 6: State Optimization (2/2 plans) -- completed 2026-02-11
- [x] Phase 7: Memory Monitoring (1/1 plans) -- completed 2026-02-12

</details>

### v3.0 Content Campaign Intelligence (Phases 8-13)

---

#### Phase 8: API Foundation & Authentication

**Goal:** System has LinkedIn API infrastructure (database tables, Kafka topics, OAuth2 client) fully operational and separated from existing RPA authentication.

**Dependencies:** None (first phase of v3.0)

**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05

**Plans:** 2 plans

Plans:
- [x] 08-01-PLAN.md -- Infrastructure foundation (deps, config, DB schema, Kafka topics)
- [x] 08-02-PLAN.md -- LinkedIn API client with OAuth2 and FastAPI endpoints

**Success Criteria:**

1. User can configure LinkedIn API credentials (client_id, client_secret) via agent.yaml or environment variables and initiate OAuth2 authorization code flow that stores tokens in the database
2. System tracks token expiration and alerts user 7 days before the 60-day expiry, and detects 401 responses to pause affected operations and prompt re-authorization
3. Five new database tables exist via Alembic migration (campaigns, campaign_variants, campaign_metrics, campaign_leads, linkedin_oauth_tokens) and two new Kafka topics are configured (campaign-publish-results, campaign-metrics-updates)
4. LinkedIn API client uses Community Management API Posts endpoint with versioned headers, fully separated from existing RPA browser session authentication
5. Campaign configuration section exists in agent.yaml with defaults for sentiments, max variants, poll interval, and LinkedIn API credentials

---

#### Phase 9: Campaign Management

**Goal:** Users can create, view, update, and delete content campaigns with full lifecycle tracking through a REST API.

**Dependencies:** Phase 8 (database schema, config infrastructure)

**Requirements:** CAMP-01, CAMP-02, CAMP-03, CAMP-04, CAMP-05, CAMP-06

**Plans:** 2 plans

Plans:
- [x] 09-01-PLAN.md -- Campaign schemas and service (CRUD + status lifecycle)
- [x] 09-02-PLAN.md -- Campaign REST API controller and app registration

**Success Criteria:**

1. User can create a campaign with a base message, selected sentiments, and optional schedule via POST endpoint, and the campaign starts in "draft" status
2. User can list all campaigns with status, variant count, and latest metrics summary via GET endpoint
3. User can view a single campaign's full details including all variants and their content, update base message or schedule before publishing, and soft-delete a campaign while preserving historical data
4. Campaign status transitions follow a valid lifecycle: draft -> scheduled -> active -> paused -> completed -> failed, with invalid transitions rejected

---

#### Phase 10: Content Generation

**Goal:** System generates diverse LLM-powered content variants from a base message using configurable sentiment strategies, with human review before publishing.

**Dependencies:** Phase 9 (campaign CRUD to store variants against)

**Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, GEN-05

**Success Criteria:**

1. User triggers variant generation for a campaign and receives multiple content variants with different sentiment angles, generated via the existing LLM client factory (Gemini or local provider)
2. System provides 10 sentiment presets (urgency, authority, calm, empathy, curiosity, social proof, educational, provocative, inspirational, humorous) and user can also define custom sentiment prompts
3. User can review generated variants and manually edit content before any variant is marked for publishing
4. System validates that generated variants have greater than 70% text difference from each other to reduce spam detection risk

---

#### Phase 11: LinkedIn Publishing

**Goal:** System publishes content variants to LinkedIn via the Posts API with staggered timing, proper error handling, and async result notification.

**Dependencies:** Phase 8 (LinkedIn API client, OAuth2 tokens), Phase 10 (generated variants to publish)

**Requirements:** PUB-01, PUB-02, PUB-03, PUB-04, PUB-05, PUB-06

**Success Criteria:**

1. User can manually trigger publishing of a single variant, and the system publishes it via the Posts API (`/rest/posts`) with versioned headers (not deprecated UGC Posts API), storing the returned LinkedIn post URN
2. User can publish multiple variants with staggered timing (configurable interval, default 15-30 minutes between posts) to mimic human cadence
3. System handles publishing errors gracefully: 401 (pauses campaign, notifies user to re-auth), 429 (backs off and retries), 422 (reports duplicate content to user)
4. System publishes results to the campaign-publish-results Kafka topic after each successful or failed publish attempt

---

#### Phase 12: Metrics & Analytics

**Goal:** System automatically polls LinkedIn for engagement metrics on published posts and presents time-series analytics with engagement velocity tracking.

**Dependencies:** Phase 11 (published posts with stored URNs to poll metrics for)

**Requirements:** MET-01, MET-02, MET-03, MET-04, MET-05, MET-06

**Success Criteria:**

1. Metrics poller runs as an APScheduler background task within FastAPI lifespan, polling LinkedIn Organization Share Statistics API on a configurable interval (default 6 hours)
2. System stores time-series metric snapshots per variant (impressions, clicks, likes, comments, shares, engagement, unique impressions) and calculates engagement velocity at 6hr, 24hr, and 48hr post-publish intervals
3. User can view metrics for a campaign's variants via API endpoint, including per-variant breakdowns and velocity data
4. System publishes metrics updates to the campaign-metrics-updates Kafka topic after each polling cycle

---

#### Phase 13: Lead Attribution & Intelligence

**Goal:** System attributes engagement to campaigns/variants, generates performance recommendations, and provides A/B testing analysis to guide campaign optimization.

**Dependencies:** Phase 12 (metrics data to analyze and attribute)

**Requirements:** LEAD-01, LEAD-02, LEAD-03, LEAD-04, INTEL-01, INTEL-02, INTEL-03, INTEL-04

**Success Criteria:**

1. System generates UTM parameters per variant for link tracking and attributes anonymous leads from engagement metric deltas (new clicks, likes, comments between snapshots)
2. User can view attributed leads per campaign and per variant via API endpoint, and the system accepts external lead capture webhooks with UTM parameter matching
3. System analyzes variant performance and identifies best/worst performing sentiments per campaign, generating heuristic recommendations (pause variants below 50% of median after 48hr, scale variants above 150% of median)
4. User can view insights, recommendations, and A/B testing results (statistical significance between variant engagement rates) via API endpoint

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Dependency Setup | v2.1 | 1/1 | Complete | 2026-02-11 |
| 2. Provider Configuration & Client Factory | v2.1 | 1/1 | Complete | 2026-02-11 |
| 3. Integration & Validation | v2.1 | 1/1 | Complete | 2026-02-11 |
| 4. Quick Wins | v2.2 | 1/1 | Complete | 2026-02-11 |
| 5. Streaming Queries | v2.2 | 1/1 | Complete | 2026-02-11 |
| 6. State Optimization | v2.2 | 2/2 | Complete | 2026-02-11 |
| 7. Memory Monitoring | v2.2 | 1/1 | Complete | 2026-02-12 |
| 8. API Foundation & Authentication | v3.0 | 2/2 | Complete | 2026-02-12 |
| 9. Campaign Management | v3.0 | 2/2 | Complete | 2026-02-12 |
| 10. Content Generation | v3.0 | 0/? | Not Started | -- |
| 11. LinkedIn Publishing | v3.0 | 0/? | Not Started | -- |
| 12. Metrics & Analytics | v3.0 | 0/? | Not Started | -- |
| 13. Lead Attribution & Intelligence | v3.0 | 0/? | Not Started | -- |
