# Feature Landscape: Content Campaign Intelligence

**Domain:** LinkedIn Content Marketing Automation with Sentiment-Driven Variants
**Researched:** 2026-02-12
**Confidence:** MEDIUM (training data only, WebSearch unavailable for verification)

## Research Notes

This research is based on training data about LinkedIn Marketing API, content campaign systems, and social media analytics patterns. WebSearch was unavailable to verify current LinkedIn API capabilities or industry best practices for 2026. Key findings should be validated against official LinkedIn Marketing API documentation before implementation.

## Table Stakes

Features users expect from a content campaign system. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Campaign CRUD | Basic lifecycle management | Low | Database, API endpoints | Create/Read/Update/Delete campaigns with metadata |
| Content variant storage | Campaigns have multiple posts | Low | Database schema for variants | Each campaign → N variants with different text |
| Single-variant publishing | Prove API integration works | Medium | LinkedIn API OAuth2, posting endpoint | Publish one post to LinkedIn via API |
| Manual publishing trigger | User initiates posts | Low | API endpoint, auth | User clicks "publish" → post goes live |
| Basic engagement metrics | Know if content performs | Medium | LinkedIn API polling, metrics storage | Impressions, likes, shares, comments (API-provided) |
| Campaign status tracking | See what's running/completed | Low | State machine in DB | Draft/Active/Paused/Completed states |
| Error handling & retry | API calls fail sometimes | Medium | Retry logic, error logging | Handle rate limits, transient failures |

## Differentiators

Features that set this product apart from basic social media schedulers.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **LLM sentiment variant generation** | Automates content creation with tonal diversity | High | LLM provider (Gemini/local), prompt engineering | Input: product description → Output: 5-10 variants with different sentiment angles |
| **Parallel multi-variant campaigns** | Test multiple approaches simultaneously | Medium | Publishing scheduler, variant tracking | Publish variants on different schedules, track separately |
| **Lead fingerprinting** | Attribution: which content → which lead | High | LinkedIn lead tracking, correlation logic | Match inbound leads to campaign/variant that generated them |
| **Sentiment preset library** | Pre-engineered prompts for common tones | Low | Prompt templates database | Urgency, authority, calm, empathy, curiosity, social proof, educational, etc. |
| **Custom sentiment definitions** | Users define their own tones | Medium | User-defined prompt storage, LLM integration | "Write in the tone of a CEO addressing shareholders" |
| **Performance-based recommendations** | System learns what works | High | Analytics aggregation, heuristic/ML scoring | "Pause low performers, scale high performers" |
| **Revenue attribution** | Track which campaigns → $$ | Very High | CRM integration, conversion tracking pixels | Requires external integrations (Salesforce, HubSpot, etc.) |
| **A/B testing framework** | Statistical significance testing | Medium | Metrics comparison, statistical tests | Determine if variant A beats variant B with confidence |
| **Engagement velocity tracking** | How fast content gains traction | Medium | Time-series metrics, velocity calculation | First 1hr, 6hr, 24hr engagement rates |
| **Audience overlap analysis** | Who engages across variants | Medium | LinkedIn API viewer data (if available) | Identify if same users engage with multiple variants |

## Anti-Features

Features to explicitly NOT build (scope creep, maintenance burden, or wrong problem).

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Full social media scheduler** | Competing with Buffer/Hootsuite, out of scope | Focus on LinkedIn-only, campaign-centric approach |
| **Image/video generation** | Adds complexity, different problem domain | Support text-only posts initially; allow URL attachments |
| **Multi-platform publishing** | LinkedIn API patterns don't translate to Twitter/FB | LinkedIn-first, extensible architecture for future |
| **Built-in CRM** | Reinventing the wheel | Integrate with external CRMs via webhooks/API |
| **Real-time dashboards** | Over-engineering for MVP | Kafka + periodic polling is sufficient; dashboards = future |
| **Sentiment analysis of comments** | Interesting but not core value | Collect comment text, defer analysis to Phase 2+ |
| **Auto-reply to comments** | High-risk automation (brand safety) | Notification-only; human handles replies |
| **Influencer identification** | Different product category | Focus on company's own content performance |
| **Content calendar UI** | UI is out of scope (CLI/API first) | JSON config or CLI args for scheduling |

## Feature Dependencies

```
Campaign CRUD
  └─> Content variant storage
       └─> LLM sentiment variant generation
            └─> Sentiment preset library
            └─> Custom sentiment definitions
       └─> Single-variant publishing
            └─> Manual publishing trigger
            └─> Parallel multi-variant campaigns
                 └─> Basic engagement metrics
                      └─> Engagement velocity tracking
                      └─> A/B testing framework
                           └─> Performance-based recommendations
            └─> Lead fingerprinting
                 └─> Revenue attribution (external integration)
```

**Critical path for MVP:**
1. Campaign CRUD → 2. Variant storage → 3. LLM generation → 4. Single-variant publish → 5. Engagement metrics → 6. Lead fingerprinting

## User Workflows

### Workflow 1: Create Campaign with Sentiment Variants

**Goal:** Generate and store multiple content variants for a product/service announcement.

**Steps:**
1. User provides product/service description (text blob, 200-500 words)
2. User selects sentiment presets (e.g., "urgency", "authority", "calm") OR defines custom sentiment
3. System calls LLM with prompt: "Rewrite this as LinkedIn post in [sentiment] tone"
4. LLM generates N variants (one per sentiment), each 1-3 paragraphs
5. System stores campaign with variants in database
6. User reviews variants, can regenerate or manually edit
7. Campaign status → "Draft"

**Complexity:** Medium (LLM integration, prompt engineering)

**API Interface:**
```json
POST /api/campaigns/create
{
  "name": "Q1 Product Launch",
  "product_description": "...",
  "sentiments": ["urgency", "authority", "calm"],
  "custom_sentiment_prompt": "Write as a thought leader in fintech",
  "llm_provider": "gemini"  // or "local"
}

Response:
{
  "campaign_id": "uuid",
  "variants": [
    {"variant_id": "uuid", "sentiment": "urgency", "content": "...", "status": "draft"},
    {"variant_id": "uuid", "sentiment": "authority", "content": "...", "status": "draft"},
    ...
  ]
}
```

### Workflow 2: Publish Multi-Variant Campaign

**Goal:** Post variants to LinkedIn with staggered timing to test different sentiments.

**Steps:**
1. User selects campaign (status="Draft")
2. User defines publish schedule for each variant:
   - Variant A (urgency) → publish immediately
   - Variant B (authority) → publish in 2 hours
   - Variant C (calm) → publish in 24 hours
3. System queues publish tasks (could use Kafka or in-memory scheduler)
4. At scheduled time, system calls LinkedIn API:
   - OAuth2 token (user-provided)
   - POST to `/v2/ugcPosts` (or similar endpoint)
   - Stores LinkedIn post ID in database
5. Campaign status → "Active"
6. System begins metrics polling (see Workflow 3)

**Complexity:** Medium (OAuth2 flow, LinkedIn API, task scheduling)

**API Interface:**
```json
POST /api/campaigns/{campaign_id}/publish
{
  "credentials": {
    "access_token": "user-linkedin-oauth-token",
    "linkedin_person_urn": "urn:li:person:..."
  },
  "schedule": [
    {"variant_id": "uuid", "publish_at": "2026-02-12T10:00:00Z"},
    {"variant_id": "uuid", "publish_at": "2026-02-12T12:00:00Z"}
  ]
}

Response:
{
  "campaign_id": "uuid",
  "status": "active",
  "scheduled_publishes": [
    {"variant_id": "uuid", "linkedin_post_id": "urn:li:share:...", "published_at": "..."}
  ]
}
```

**LinkedIn API Notes (LOW CONFIDENCE - needs verification):**
- OAuth2 with `w_member_social` scope for posting
- REST endpoint: `POST /v2/ugcPosts` (LinkedIn's UGC API)
- Requires author URN (user or organization)
- Rate limits: unknown, need to verify current limits

### Workflow 3: Collect Engagement Metrics

**Goal:** Track how each variant performs (impressions, CTR, engagement).

**Steps:**
1. System runs periodic polling (every 1 hour for first 24hr, then every 6hr)
2. For each published variant:
   - Call LinkedIn API: `GET /v2/socialActions/{shareUrn}/statistics`
   - Parse metrics: impressions, clicks, likes, comments, shares
   - Store in time-series database (or SQLite with timestamp)
3. Calculate derived metrics:
   - CTR = (clicks / impressions) * 100
   - Engagement rate = (likes + comments + shares) / impressions
   - Engagement velocity = engagement in first 1hr, 6hr, 24hr
4. Expose metrics via API endpoint

**Complexity:** Medium (API polling, time-series storage, rate limit handling)

**API Interface:**
```json
GET /api/campaigns/{campaign_id}/metrics

Response:
{
  "campaign_id": "uuid",
  "variants": [
    {
      "variant_id": "uuid",
      "sentiment": "urgency",
      "metrics": {
        "impressions": 1500,
        "clicks": 75,
        "likes": 120,
        "comments": 8,
        "shares": 15,
        "ctr": 5.0,
        "engagement_rate": 9.53,
        "velocity": {
          "1hr": {"impressions": 200, "engagement": 15},
          "6hr": {"impressions": 800, "engagement": 60},
          "24hr": {"impressions": 1500, "engagement": 143}
        }
      }
    },
    ...
  ]
}
```

**LinkedIn API Notes (LOW CONFIDENCE):**
- Metrics endpoint: `/v2/organizationalEntityShareStatistics` or similar
- Polling frequency limits: unknown, need verification
- Metrics lag: typically 1-3 hours behind real-time

### Workflow 4: Lead Fingerprinting (Attribution)

**Goal:** Identify which campaign/variant generated which leads.

**Steps:**
1. System generates UTM parameters or tracking tokens for each variant's URL
   - Example: `?utm_source=linkedin&utm_campaign=q1_launch&utm_content=urgency_variant`
2. When publishing, system appends tracking params to any links in post content
3. When lead converts (fills form, signs up, etc.):
   - Lead capture system (external) sends webhook to this system
   - Webhook includes UTM params or tracking token
   - System matches token → variant → campaign
4. System stores lead attribution in database
5. Aggregates lead quality metrics per variant/sentiment

**Complexity:** High (requires external integration, webhook handling, token management)

**Data Model:**
```
Lead {
  lead_id: uuid
  campaign_id: uuid
  variant_id: uuid
  sentiment: string
  source_url: string
  utm_params: json
  converted_at: timestamp
  lead_quality_score: float  // if available from CRM
  revenue_attributed: float  // if available
}
```

**API Interface:**
```json
POST /api/campaigns/leads/webhook
{
  "email": "lead@example.com",
  "utm_source": "linkedin",
  "utm_campaign": "q1_launch",
  "utm_content": "urgency_variant",
  "lead_score": 85,
  "conversion_value": 5000
}

Response:
{
  "lead_id": "uuid",
  "matched_variant": "uuid",
  "matched_campaign": "uuid"
}
```

**Tracking Mechanisms (LOW CONFIDENCE - needs research):**
- UTM parameters (widely supported, but relies on URL clicks)
- LinkedIn Conversion Tracking pixel (requires LinkedIn Insight Tag setup)
- LinkedIn Lead Gen Forms (native form fills, direct API integration)
- First-party tracking tokens in URLs (custom solution)

### Workflow 5: Optimization Recommendations

**Goal:** System analyzes performance and recommends actions.

**Steps:**
1. System aggregates metrics across all variants in campaign
2. Applies heuristics or simple ML scoring:
   - High performer: engagement rate > median + 1 std dev
   - Low performer: engagement rate < median - 1 std dev
   - Winner: statistically significant improvement in CTR/leads
3. Generates recommendations:
   - "Pause low performers (variant C, D)"
   - "Scale high performers (variant A): create follow-up campaign with similar sentiment"
   - "Test variations of winning sentiment (authority) with different hooks"
4. Exposes recommendations via API

**Complexity:** Medium (statistical analysis, heuristic rules)

**API Interface:**
```json
GET /api/campaigns/{campaign_id}/recommendations

Response:
{
  "campaign_id": "uuid",
  "status": "active",
  "recommendations": [
    {
      "type": "pause",
      "variant_id": "uuid",
      "reason": "Engagement rate 40% below median",
      "confidence": "high"
    },
    {
      "type": "scale",
      "variant_id": "uuid",
      "reason": "Highest CTR (8.2%) and lead conversion (12 leads)",
      "confidence": "high",
      "suggested_action": "Create follow-up campaign with 'authority' sentiment"
    },
    {
      "type": "test",
      "sentiment": "authority",
      "reason": "Winning sentiment, test variations",
      "confidence": "medium"
    }
  ]
}
```

**Recommendation Logic (heuristics for MVP):**
- Pause: engagement rate < 50% of campaign median after 48hr
- Scale: engagement rate > 150% of median + leads > 5
- Test: winning sentiment identified, suggest A/B test with hook variations

## MVP Recommendation

**Phase 1: Core Campaign + Variant Generation**
1. Campaign CRUD (database schema, API endpoints)
2. LLM sentiment variant generation (Gemini integration, preset prompts)
3. Variant storage and retrieval
4. Sentiment preset library (5-7 common presets)

**Phase 2: LinkedIn Publishing**
5. OAuth2 credential management (user-provided tokens)
6. Single-variant publishing to LinkedIn API
7. Error handling and retry logic
8. Campaign status state machine

**Phase 3: Metrics & Attribution**
9. Engagement metrics polling (LinkedIn API)
10. Time-series metrics storage
11. Lead fingerprinting (UTM tracking + webhook)
12. Metrics aggregation and API

**Phase 4: Intelligence & Optimization**
13. A/B testing framework (statistical comparisons)
14. Engagement velocity tracking
15. Optimization recommendations (heuristic-based)

**Defer to Phase 5+:**
- Revenue attribution (requires CRM integration)
- Real-time dashboards (API-first, defer UI)
- Multi-platform publishing (LinkedIn-only MVP)
- Advanced ML for recommendations (heuristics sufficient initially)
- Auto-reply or comment analysis (high-risk automation)

## Feature Complexity Breakdown

| Feature | Complexity | Estimated Effort | Blockers/Risks |
|---------|------------|------------------|----------------|
| Campaign CRUD | Low | 1-2 days | None |
| Variant storage | Low | 1 day | None |
| LLM variant generation | High | 3-5 days | Prompt engineering quality, LLM cost |
| Sentiment presets | Low | 1 day | None |
| OAuth2 management | Medium | 2-3 days | User must provide tokens (security) |
| LinkedIn publishing | Medium | 3-4 days | API rate limits, authentication edge cases |
| Engagement metrics | Medium | 3-4 days | API polling cadence, rate limits |
| Lead fingerprinting | High | 5-7 days | External system integration, webhook reliability |
| A/B testing | Medium | 2-3 days | Statistical test selection (t-test, chi-square) |
| Recommendations | Medium | 3-4 days | Heuristic tuning, avoiding false positives |

**Total estimated effort for MVP (Phases 1-3):** 20-30 days

## Sentiment Preset Catalog

Expected sentiment strategies for content variant generation:

| Preset | Tone Characteristics | Example Hook | Use Case |
|--------|---------------------|--------------|----------|
| **Urgency** | Time-sensitive, scarcity, FOMO | "Limited time only", "Don't miss out" | Product launches, sales |
| **Authority** | Expert, data-driven, credible | "Industry research shows...", "As a leader in X" | Thought leadership, B2B |
| **Calm** | Reassuring, stable, trust-building | "Take your time", "Here's what you need to know" | Education, onboarding |
| **Empathy** | Understanding, relatable, human | "We know how hard it is...", "You're not alone" | Customer support, community |
| **Curiosity** | Question-driven, mystery, intrigue | "What if you could...", "Here's a secret" | Engagement bait, viral content |
| **Social Proof** | Testimonial-focused, popularity | "Join 10,000 customers", "See what others are saying" | Conversions, trust-building |
| **Educational** | How-to, informative, value-first | "Learn how to...", "The complete guide to" | Content marketing, SEO |
| **Provocative** | Contrarian, debate-sparking | "Unpopular opinion:", "Everyone's wrong about X" | Engagement, polarizing |
| **Inspirational** | Aspirational, motivational | "Imagine a world where...", "You can achieve X" | Brand building, vision |
| **Humorous** | Light, witty, entertaining | Jokes, puns, self-deprecation | Virality, brand personality |

**Implementation:** Each preset maps to a prompt template that instructs the LLM to rewrite input in that tone.

## Expected Behaviors: Summary Table

| Behavior | Expected Pattern | Complexity | Notes |
|----------|------------------|------------|-------|
| **Campaign Creation** | User input → LLM → variants stored | Medium | Synchronous API call, async LLM generation |
| **Variant Generation** | 1 input → N outputs (one per sentiment) | High | Prompt engineering critical |
| **Publishing** | API call → LinkedIn post → store post ID | Medium | OAuth2 required, rate limits |
| **Metrics Collection** | Periodic polling → time-series storage | Medium | Hourly for 24hr, then 6hr cadence |
| **Lead Attribution** | Webhook → parse UTM → match variant | High | Requires external integration |
| **Optimization** | Metrics → heuristics → recommendations | Medium | Statistical tests + business rules |

## Open Questions (Require Further Research)

1. **LinkedIn API specifics:**
   - Current UGC posting endpoint path and request format?
   - Metrics endpoint for share statistics?
   - OAuth2 scope requirements for posting + metrics?
   - Rate limits for posting and polling?

2. **Lead tracking mechanisms:**
   - Does LinkedIn provide conversion tracking pixel/API?
   - Can we access LinkedIn Lead Gen Form submissions programmatically?
   - UTM parameter reliability (do they persist through LinkedIn's link shortener)?

3. **Metrics lag and accuracy:**
   - How delayed are LinkedIn's engagement metrics?
   - Are draft posts supported (schedule future publish)?

4. **Multi-variant posting:**
   - Can same user post multiple times in short succession without penalties?
   - Does LinkedIn detect/penalize duplicate content with slight variations?

## Sources

**Training data (as of January 2025):**
- LinkedIn Marketing API patterns (unverified for 2026)
- Social media campaign management best practices
- Sentiment analysis and LLM content generation patterns
- Lead attribution and UTM tracking standards

**Confidence level:** MEDIUM overall
- HIGH for general campaign patterns and LLM integration (consistent with project's existing stack)
- LOW for LinkedIn API specifics (requires official documentation verification)
- MEDIUM for lead attribution patterns (standard web analytics, but LinkedIn-specific details unknown)

**Next steps:** Validate LinkedIn Marketing API capabilities with official documentation before Phase 2 implementation.
