# Technology Stack Additions

**Project:** Serial LinkedIn Killer - v3.0 Content Campaign Intelligence
**Researched:** 2026-02-12
**Confidence:** MEDIUM (training data + existing stack analysis; web verification unavailable)

## Executive Summary

LinkedIn Marketing API integration requires OAuth2 token management, API client for posts/metrics, campaign/variant persistence, and metrics polling. The existing stack (FastAPI, SQLAlchemy, LangChain, Kafka) already provides most infrastructure. Only minimal additions needed: OAuth2 library, HTTP client enhancements, DB models, and optional scheduling.

**Key principle:** Extend existing patterns, don't introduce new paradigms. Use httpx (already present), SQLAlchemy (already present), and LangChain (already present).

---

## NEW Dependencies

### Core LinkedIn Marketing API

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **authlib** | ^1.3.0 | OAuth2 token management (authorization code flow, token refresh) | Industry-standard OAuth2/OIDC library. LinkedIn uses OAuth 2.0 for Marketing API access. Supports token storage, automatic refresh, PKCE. Preferred over `requests-oauthlib` for better async support and modern OAuth flows. |
| **httpx** | ^0.28.1 *(existing)* | Async HTTP client for LinkedIn API calls | Already in stack. Use for Marketing API requests (posts, metrics). Supports async/await, connection pooling, timeout management. No new dependency. |

**Rationale for authlib:**
- LinkedIn Marketing API requires OAuth 2.0 with authorization code flow
- User-provided credentials → need token storage and refresh logic
- Authlib provides `OAuth2Session` for token lifecycle management
- Integrates cleanly with httpx for API requests
- Async-compatible (important for FastAPI endpoints)

### Database Extensions

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **sqlalchemy** | ^2.0.0 *(existing)* | Campaign, variant, metrics models | Already in stack. Extend `src/core/db/models.py` with new tables. No new dependency. |
| **alembic** | ^1.13.0 *(existing)* | Migration for new campaign tables | Already in stack. Create migration for Campaign, CampaignVariant, EngagementMetrics tables. No new dependency. |

**New tables needed:**
1. **Campaign** - campaign_id, name, created_at, status, sentiment_config
2. **CampaignVariant** - variant_id, campaign_id, sentiment_type, content, linkedin_post_id, published_at
3. **EngagementMetrics** - metric_id, variant_id, impressions, clicks, ctr, likes, shares, comments, collected_at
4. **Lead** - lead_id, variant_id, linkedin_profile_url, name, title, company, source_post_id, created_at

### Metrics Polling & Scheduling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **apscheduler** | ^3.10.4 | Background metrics polling scheduler | Lightweight, in-process scheduler for periodic LinkedIn API metrics collection. Alternatives (Celery, RQ) require Redis/RabbitMQ brokers — overkill for simple polling. APScheduler integrates with FastAPI lifespan, supports cron/interval triggers, and uses existing DB for job persistence. |

**Rationale:**
- Need periodic API calls to fetch engagement metrics (hourly/daily)
- APScheduler runs in FastAPI process → no new infrastructure
- Supports SQLAlchemy job store → leverages existing DB
- Alternative considered: Celery (rejected — too heavy, requires broker)

### Data Analysis (Optional)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pandas** | ^2.2.0 *(existing)* | Lead performance analytics, CSV export | Already in stack. Use for aggregating metrics, computing variant performance, generating reports. No new dependency. |
| **numpy** | ^1.26.0 *(recommended if pandas needs it)* | Pandas dependency for numerical operations | Likely already installed as pandas transitive dependency. Explicit inclusion ensures version compatibility. |

**Note:** Only add numpy if pandas installation doesn't pull it automatically. Check `poetry show pandas` dependencies first.

---

## Integration Points with Existing Stack

### 1. LLM Integration - Content Generation

**Existing:** `src/core/providers/llm_client.py` (factory pattern)
**Integration:**
- Create `src/core/agents/tools/content_generation.py`
- Use existing `get_llm_client()` factory
- Sentiment presets → LangChain PromptTemplate variations
- Reuse Langfuse tracing automatically

**No new dependencies.** LangChain + Gemini already handle content generation.

### 2. API Layer - Campaign Management Endpoints

**Existing:** FastAPI controllers in `src/core/api/controllers/`
**Integration:**
- Add `src/core/api/controllers/campaign_controller.py`
- Add `src/core/api/services/campaign_service.py`
- Follow existing dependency injection pattern (see `job_service.py`)
- Register router in `app.py`: `app.include_router(campaign_router)`

**No new dependencies.** FastAPI patterns already established.

### 3. Database - Campaign Persistence

**Existing:** SQLAlchemy models in `src/core/db/models.py`
**Integration:**
- Extend `models.py` with Campaign/Variant/Metrics/Lead tables
- Use existing `Base` declarative class
- Create Alembic migration: `alembic revision --autogenerate -m "add_campaign_tables"`
- Use existing `AgentDB` connection management

**No new dependencies.** SQLAlchemy + Alembic already present.

### 4. Configuration - LinkedIn API Credentials

**Existing:** Pydantic configs in `src/config/config_loader.py`
**Integration:**
- Add `LinkedInMarketingConfig` Pydantic model
- Fields: `client_id`, `client_secret`, `redirect_uri`, `token_storage_path`
- Add to `AgentConfig` model
- Add to `agent.yaml` with env var overrides (`LINKEDIN_MARKETING_CLIENT_ID`, etc.)

**No new dependencies.** Config pattern already established.

### 5. Observability - Metrics Collection Tracing

**Existing:** Langfuse tracing in `src/core/observability/langfuse_config.py`
**Integration:**
- Wrap LinkedIn API calls with Langfuse spans
- Track API latency, error rates, quota usage
- Follow existing `get_langfuse_callback()` pattern

**No new dependencies.** Langfuse already present.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **OAuth2 Library** | authlib | requests-oauthlib | requests-oauthlib lacks async support, less active maintenance, authlib more feature-complete |
| **HTTP Client** | httpx (existing) | requests (existing) | requests is sync-only; httpx already in stack and supports async |
| **Scheduler** | apscheduler | Celery | Celery requires Redis/RabbitMQ broker; overkill for simple polling; APScheduler in-process |
| **Scheduler** | apscheduler | cron + separate script | cron requires external orchestration; APScheduler integrates with FastAPI lifespan |
| **LinkedIn API Client** | Custom (httpx + authlib) | linkedin-api (unofficial) | Unofficial library reverse-engineers web scraping, not Marketing API; risky, violates ToS |
| **LinkedIn API Client** | Custom (httpx + authlib) | python-linkedin-v2 | Abandoned (last update 2019); doesn't support modern Marketing API endpoints |

**Key decision:** No official LinkedIn Marketing API Python SDK exists. Build thin wrapper around httpx + authlib rather than rely on unmaintained/unofficial libraries.

---

## Installation

### New Dependencies Only

```bash
# OAuth2 for LinkedIn Marketing API
poetry add authlib@^1.3.0

# Scheduling for metrics polling
poetry add apscheduler@^3.10.4

# Optional: Explicit numpy if pandas doesn't pull it
# Check first: poetry show pandas
# poetry add numpy@^1.26.0
```

### Verification

```bash
# Verify authlib installation
poetry run python -c "from authlib.integrations.httpx_client import AsyncOAuth2Client; print('✓ authlib OK')"

# Verify apscheduler installation
poetry run python -c "from apscheduler.schedulers.asyncio import AsyncIOScheduler; print('✓ apscheduler OK')"
```

---

## What NOT to Add

| Anti-Dependency | Reason |
|----------------|--------|
| **linkedin-api** (unofficial) | Reverse-engineered web scraping library; doesn't use Marketing API; violates ToS; unreliable |
| **python-linkedin-v2** | Abandoned (2019); doesn't support modern Marketing API endpoints |
| **Celery / RQ** | Heavyweight task queues require Redis/RabbitMQ brokers; overkill for simple metrics polling |
| **Redis** | Not needed — APScheduler can use existing SQLite for job persistence |
| **requests** (for new code) | Already have httpx; don't mix HTTP clients; httpx supports async |
| **BeautifulSoup** (for LinkedIn API) | Marketing API returns JSON, not HTML; no scraping needed |
| **New ORM (e.g., Tortoise, Piccolo)** | SQLAlchemy already present; don't fragment persistence layer |
| **Pydantic-settings** | Config pattern already works with Pydantic BaseModel + custom loader |
| **Dedicated sentiment analysis library (NLTK, spaCy, TextBlob)** | LLM (Gemini) already generates sentiment variants; adding NLP library is redundant |

**Principle:** Minimize new dependencies. Leverage existing stack. Only add what's strictly necessary.

---

## Configuration Schema Extensions

### agent.yaml additions

```yaml
linkedin_marketing:
  client_id: ""  # LinkedIn app client ID (or LINKEDIN_MARKETING_CLIENT_ID env var)
  client_secret: ""  # LinkedIn app client secret (or LINKEDIN_MARKETING_CLIENT_SECRET env var)
  redirect_uri: "http://localhost:8080/auth/linkedin/callback"  # OAuth callback URL
  token_storage_path: "./data/linkedin_tokens.json"  # Token persistence (or LINKEDIN_TOKEN_STORAGE_PATH env var)
  metrics_poll_interval_hours: 6  # How often to poll engagement metrics

campaigns:
  default_sentiment_presets:
    - professional
    - enthusiastic
    - educational
    - provocative
    - storytelling
  max_variants_per_campaign: 5
```

### Environment variables

```bash
# LinkedIn Marketing API
LINKEDIN_MARKETING_CLIENT_ID=your_client_id
LINKEDIN_MARKETING_CLIENT_SECRET=your_client_secret
LINKEDIN_MARKETING_REDIRECT_URI=http://localhost:8080/auth/linkedin/callback
LINKEDIN_TOKEN_STORAGE_PATH=./data/linkedin_tokens.json

# Optional: Metrics polling interval override
METRICS_POLL_INTERVAL_HOURS=6
```

---

## Database Schema Extensions

### New Models (add to src/core/db/models.py)

```python
class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    topic = Column(Text)
    sentiment_config = Column(Text)  # JSON of sentiment presets used
    created_at = Column(Float, default=time.time)
    status = Column(String, index=True)  # draft, published, archived


class CampaignVariant(Base):
    __tablename__ = "campaign_variants"

    variant_id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), index=True)
    sentiment_type = Column(String, nullable=False)  # professional, enthusiastic, etc.
    content = Column(Text, nullable=False)  # Generated post content
    linkedin_post_id = Column(String, unique=True)  # LinkedIn URN after publishing
    published_at = Column(Float)
    status = Column(String, index=True)  # pending, published, failed


class EngagementMetrics(Base):
    __tablename__ = "engagement_metrics"

    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(String, ForeignKey("campaign_variants.variant_id"), index=True)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)  # Click-through rate
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    collected_at = Column(Float, default=time.time, index=True)


class Lead(Base):
    __tablename__ = "leads"

    lead_id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(String, ForeignKey("campaign_variants.variant_id"), index=True)
    linkedin_profile_url = Column(String, unique=True)
    name = Column(String)
    title = Column(String)
    company = Column(String)
    source_post_id = Column(String)  # Which LinkedIn post generated this lead
    created_at = Column(Float, default=time.time, index=True)
```

### Indexes for Analytics Queries

```python
# Add to models.py after table definitions
Index('idx_metrics_variant_time', EngagementMetrics.variant_id, EngagementMetrics.collected_at)
Index('idx_leads_variant_time', Lead.variant_id, Lead.created_at)
Index('idx_variants_campaign_status', CampaignVariant.campaign_id, CampaignVariant.status)
```

---

## API Client Structure (Recommended Pattern)

### src/core/clients/linkedin_marketing_client.py

```python
"""LinkedIn Marketing API client using httpx + authlib."""

from authlib.integrations.httpx_client import AsyncOAuth2Client
from typing import Dict, List
import httpx

class LinkedInMarketingClient:
    """Async client for LinkedIn Marketing API."""

    BASE_URL = "https://api.linkedin.com/v2"

    def __init__(self, oauth_client: AsyncOAuth2Client):
        self.client = oauth_client

    async def create_post(self, author_urn: str, content: str) -> Dict:
        """Create LinkedIn post via UGC Posts API."""
        # Implementation using self.client.post(...)
        pass

    async def get_post_analytics(self, post_urn: str) -> Dict:
        """Fetch engagement metrics for a post."""
        # Implementation using self.client.get(...)
        pass
```

**Why this pattern:**
- Separates OAuth logic (authlib) from API calls (httpx)
- AsyncOAuth2Client handles token refresh automatically
- Testable (mock AsyncOAuth2Client in tests)
- Follows existing provider pattern (see `llm_client.py`)

---

## Scheduler Integration (Recommended Pattern)

### src/core/schedulers/metrics_scheduler.py

```python
"""APScheduler for periodic metrics collection."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

def create_metrics_scheduler(db_url: str) -> AsyncIOScheduler:
    """Create scheduler with SQLAlchemy job store."""
    jobstores = {
        'default': SQLAlchemyJobStore(url=db_url)
    }
    scheduler = AsyncIOScheduler(jobstores=jobstores)
    return scheduler

async def collect_metrics_job():
    """Background job to poll LinkedIn API for metrics."""
    # Fetch published variants from DB
    # Call LinkedIn API for each variant's analytics
    # Update EngagementMetrics table
    pass
```

**Integration with FastAPI:**
- Start scheduler in `app.py` lifespan startup
- Shutdown scheduler in lifespan shutdown
- Use existing `config.db.url` for job persistence

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **OAuth2 Library (authlib)** | HIGH | Industry standard; well-documented; async support confirmed in training data |
| **HTTP Client (httpx)** | HIGH | Already in stack; async support verified |
| **Scheduler (apscheduler)** | MEDIUM | Standard choice for in-process scheduling; training data supports SQLAlchemy integration |
| **LinkedIn API Endpoints** | LOW | Marketing API specifics (UGC Posts, Analytics endpoints) not verified with current docs; may need endpoint URL adjustments during implementation |
| **Database Schema** | HIGH | SQLAlchemy patterns match existing models.py |
| **Integration Points** | HIGH | Follows established patterns in codebase |

**Gaps:**
- LinkedIn Marketing API exact endpoint URLs/schemas not verified (no web access)
- authlib version 1.3.0 availability not verified (training data is Jan 2025; current is Feb 2026)
- apscheduler version 3.10.4 availability not verified

**Mitigation:**
- Check official LinkedIn Marketing API docs during implementation: https://learn.microsoft.com/en-us/linkedin/marketing/
- Verify authlib/apscheduler latest stable versions via PyPI before installation
- Test OAuth flow in Phase 1 (dependency setup) to catch integration issues early

---

## Sources

**Training Data Only:**
- authlib documentation (2024 knowledge)
- LinkedIn Marketing API general structure (2024 knowledge)
- APScheduler documentation (2024 knowledge)
- httpx/FastAPI async patterns (2024 knowledge)

**MEDIUM Confidence Overall:** Core recommendations (authlib, apscheduler, httpx reuse) are sound based on training data, but library versions and LinkedIn API endpoint specifics require verification during implementation.

**Next Steps for Validation:**
1. Check PyPI for latest authlib/apscheduler versions
2. Review LinkedIn Marketing API docs (UGC Posts API, Analytics API)
3. Verify OAuth 2.0 flow requirements (scopes: w_member_social, r_organization_social, rw_organization_admin)

---

*Stack additions researched: 2026-02-12*
*Confidence: MEDIUM (training data, no web verification)*
*Recommendation: Validate library versions and LinkedIn API endpoints before Phase 1 implementation*
