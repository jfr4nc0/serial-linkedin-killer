# Architecture Patterns: LinkedIn API Content Campaigns

**Domain:** Content campaign intelligence with LLM-generated variants
**Researched:** 2026-02-12

## Executive Summary

This document describes how LinkedIn API content campaigns integrate with the existing Core Agent + MCP Server + Kafka architecture. The campaign system adds **direct LinkedIn API integration** to Core Agent (bypassing MCP's Selenium-based RPA), enabling programmatic content publishing, metrics polling, and lead attribution analytics.

**Key Decision:** LinkedIn API calls live in Core Agent, NOT in MCP Server. MCP handles browser automation for scraping; Core Agent handles authenticated API workflows.

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CORE AGENT (Port 8080)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  FastAPI Routes  │  │  Campaign Svc    │  │ Content Svc  │  │
│  │                  │  │                  │  │              │  │
│  │ /campaigns/*     │→ │ CRUD             │→ │ LLM Variants │  │
│  │ /content/*       │  │ Scheduling       │  │ Generation   │  │
│  │ /metrics/*       │  │ Publishing       │  │              │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                              ↓                       ↓          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ LinkedIn API     │  │  Metrics Poller  │  │ Lead Engine  │  │
│  │ Client           │  │  (Background)    │  │              │  │
│  │                  │  │                  │  │ Attribution  │  │
│  │ OAuth2 + Posts   │  │ Schedule: 6h     │  │ Fingerprint  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│         ↓                       ↓                    ↓          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              SQLite (agent.db)                            │  │
│  │  - campaigns                                              │  │
│  │  - campaign_variants                                      │  │
│  │  - campaign_metrics (time-series snapshots)               │  │
│  │  - campaign_leads                                         │  │
│  │  - linkedin_oauth_tokens                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Kafka Producer                               │  │
│  │  Topics:                                                  │  │
│  │  - campaign-publish-results                               │  │
│  │  - campaign-metrics-updates                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    MCP SERVER (Port 3000)                        │
├─────────────────────────────────────────────────────────────────┤
│  Selenium Browser Automation (unchanged)                        │
│  - search_jobs                                                  │
│  - easy_apply                                                   │
│  - search_employees                                             │
│  - send_messages                                                │
│  - search_employees_batch                                       │
└─────────────────────────────────────────────────────────────────┘
     ↑
     | (NOT used for LinkedIn API campaigns)
     |
```

## Component Boundaries

| Component | Responsibility | Location | Communicates With |
|-----------|---------------|----------|-------------------|
| **Campaign Controller** | REST endpoints for campaign CRUD, publishing, metrics retrieval | `src/core/api/controllers/campaign_controller.py` | Campaign Service |
| **Campaign Service** | Business logic: create, schedule, publish campaigns | `src/core/api/services/campaign_service.py` | Content Service, LinkedIn API Client, Kafka |
| **Content Service** | LLM-based content variant generation (by sentiment) | `src/core/api/services/content_service.py` | LLM Client (existing) |
| **LinkedIn API Client** | OAuth2 flow + UGC Post creation + Share Statistics | `src/core/providers/linkedin_api_client.py` | LinkedIn REST API |
| **Metrics Poller** | Background task: polls LinkedIn Share Statistics API every 6h | `src/core/services/metrics_poller.py` | LinkedIn API Client, AgentDB |
| **Lead Engine** | Fingerprint leads from metrics (who engaged with content) | `src/core/services/lead_engine.py` | AgentDB, Kafka |
| **Learning Engine** | Analyze which variants perform best, recommend next actions | `src/core/services/learning_engine.py` | AgentDB (reads metrics) |
| **AgentDB (Extended)** | New tables: campaigns, variants, metrics, leads, oauth_tokens | `src/core/db/agent_db.py` | All services |

## Data Flow

### 1. Campaign Creation Flow

```
User → CLI/API
  ↓
POST /api/campaigns/create
  {
    "organization_urn": "urn:li:organization:12345",
    "base_message": "Check out our new feature!",
    "sentiments": ["professional", "casual", "excited"],
    "schedule": "2026-02-15T10:00:00Z"
  }
  ↓
Campaign Service
  ↓
Content Service → LLM Client (generate 3 variants)
  ↓
AgentDB.insert(campaign, variants)
  ↓
Return campaign_id
```

### 2. Publishing Flow

```
Scheduled time OR Manual trigger
  ↓
POST /api/campaigns/{id}/publish
  ↓
Campaign Service
  ↓
LinkedIn API Client.create_ugc_post()
  - author: organization URN
  - text: selected variant.content
  - visibility: PUBLIC
  ↓
LinkedIn API returns ugc_post_urn
  ↓
AgentDB.update(variant.ugc_post_urn, published_at)
  ↓
Kafka Producer → campaign-publish-results
  {
    "campaign_id": "uuid",
    "variant_id": "uuid",
    "ugc_post_urn": "urn:li:ugcPost:123",
    "status": "published"
  }
  ↓
CLI Consumer receives notification
```

### 3. Metrics Polling Flow

```
APScheduler (every 6 hours)
  ↓
Metrics Poller.run()
  ↓
AgentDB.get_published_campaigns(last_12_months)
  ↓
For each campaign.ugc_post_urn:
  LinkedIn API.get_share_statistics(ugc_post_urn)
  {
    "impressionCount": 5287,
    "clickCount": 78,
    "likeCount": 14,
    "commentCount": 24,
    "shareCount": 5,
    "engagement": 0.0228
  }
  ↓
AgentDB.insert(campaign_metrics snapshot)
  - campaign_id
  - variant_id
  - polled_at (timestamp)
  - impressions, clicks, likes, comments, shares, engagement
  ↓
Kafka Producer → campaign-metrics-updates
  {
    "campaign_id": "uuid",
    "variant_id": "uuid",
    "metrics": {...}
  }
```

### 4. Lead Attribution Flow

```
Metrics Poller detects engagement increase
  ↓
Lead Engine.attribute_leads(campaign_id)
  ↓
Compare current metrics vs last snapshot
  ↓
If clicks increased:
  - Create lead fingerprint (anonymous for API limitations)
  - Store in campaign_leads table:
    {
      "campaign_id": "uuid",
      "variant_id": "uuid",
      "lead_source": "click",
      "attributed_at": timestamp
    }
  ↓
Learning Engine analyzes:
  - Which sentiment performed best
  - Time-of-day patterns
  - Engagement velocity
  ↓
Store recommendations in campaign_insights table
```

## New vs Modified Components

### NEW Components

| Component | Path | Purpose |
|-----------|------|---------|
| **campaign_controller.py** | `src/core/api/controllers/campaign_controller.py` | FastAPI routes for campaigns |
| **campaign_service.py** | `src/core/api/services/campaign_service.py` | Campaign orchestration logic |
| **content_service.py** | `src/core/api/services/content_service.py` | LLM variant generation |
| **linkedin_api_client.py** | `src/core/providers/linkedin_api_client.py` | LinkedIn REST API wrapper |
| **metrics_poller.py** | `src/core/services/metrics_poller.py` | Background polling task |
| **lead_engine.py** | `src/core/services/lead_engine.py` | Lead attribution logic |
| **learning_engine.py** | `src/core/services/learning_engine.py` | Variant performance analysis |
| **campaign_schemas.py** | `src/core/api/schemas/campaign_schemas.py` | Pydantic models for campaigns |

### MODIFIED Components

| Component | Changes |
|-----------|---------|
| **app.py** | Add campaign router, initialize metrics poller background task |
| **models.py** | Add 5 new tables: campaigns, campaign_variants, campaign_metrics, campaign_leads, linkedin_oauth_tokens |
| **agent_db.py** | Add methods: `insert_campaign()`, `get_campaign_metrics()`, `get_campaign_leads()` |
| **config/agent.yaml** | Add `linkedin_api` section: `client_id`, `client_secret`, `redirect_uri`, `metrics_poll_interval` |
| **queue/config.py** | Add topics: `campaign-publish-results`, `campaign-metrics-updates` |

### UNCHANGED Components

- **MCP Server** (no changes - campaigns bypass browser automation)
- **Outreach Service** (existing message workflow untouched)
- **Job Service** (existing job application workflow untouched)

## New Database Tables

### campaigns

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | UUID |
| organization_urn | TEXT NOT NULL | LinkedIn org URN (urn:li:organization:12345) |
| base_message | TEXT NOT NULL | Original message before LLM variants |
| created_at | FLOAT NOT NULL | Epoch timestamp |
| scheduled_at | FLOAT NULL | When to publish (NULL = manual) |
| status | TEXT NOT NULL | draft, scheduled, published, failed |

### campaign_variants

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | UUID |
| campaign_id | TEXT NOT NULL FK | References campaigns(id) |
| sentiment | TEXT NOT NULL | professional, casual, excited, etc. |
| content | TEXT NOT NULL | LLM-generated variant |
| ugc_post_urn | TEXT NULL | LinkedIn URN after publishing |
| published_at | FLOAT NULL | Epoch timestamp |
| is_selected | INTEGER DEFAULT 0 | 1 if this variant was published |

### campaign_metrics

Time-series snapshots (polled every 6h).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| campaign_id | TEXT NOT NULL FK | References campaigns(id) |
| variant_id | TEXT NOT NULL FK | References campaign_variants(id) |
| polled_at | FLOAT NOT NULL | When metrics were fetched |
| impressions | INTEGER DEFAULT 0 | |
| clicks | INTEGER DEFAULT 0 | |
| likes | INTEGER DEFAULT 0 | |
| comments | INTEGER DEFAULT 0 | |
| shares | INTEGER DEFAULT 0 | |
| engagement | FLOAT DEFAULT 0.0 | Calculated by LinkedIn |
| unique_impressions | INTEGER DEFAULT 0 | |

**Index:** `CREATE INDEX idx_metrics_campaign_variant ON campaign_metrics(campaign_id, variant_id, polled_at)`

### campaign_leads

Attributed leads from engagement spikes.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| campaign_id | TEXT NOT NULL FK | References campaigns(id) |
| variant_id | TEXT NOT NULL FK | References campaign_variants(id) |
| lead_source | TEXT NOT NULL | click, like, comment, share |
| attributed_at | FLOAT NOT NULL | When lead was attributed |
| fingerprint | TEXT NULL | Future: demographic info if available |

### linkedin_oauth_tokens

OAuth2 tokens for LinkedIn API (per organization).

| Column | Type | Description |
|--------|------|-------------|
| organization_urn | TEXT PRIMARY KEY | LinkedIn org URN |
| access_token | TEXT NOT NULL | OAuth2 access token (~500 chars) |
| refresh_token | TEXT NULL | For programmatic refresh (if available) |
| expires_at | FLOAT NOT NULL | Epoch timestamp |
| created_at | FLOAT NOT NULL | Epoch timestamp |

## New Kafka Topics

| Topic | Purpose | Producer | Consumer |
|-------|---------|----------|----------|
| **campaign-publish-results** | Notify CLI when campaign is published | Campaign Service | CLI consumer |
| **campaign-metrics-updates** | Notify CLI when metrics are polled | Metrics Poller | CLI consumer |

## New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/campaigns` | POST | Create new campaign (generates variants via LLM) |
| `/api/campaigns` | GET | List all campaigns (with pagination) |
| `/api/campaigns/{id}` | GET | Get campaign + variants + latest metrics |
| `/api/campaigns/{id}` | PUT | Update campaign (base_message, schedule) |
| `/api/campaigns/{id}` | DELETE | Delete campaign (soft delete) |
| `/api/campaigns/{id}/publish` | POST | Publish campaign (posts selected variant to LinkedIn) |
| `/api/campaigns/{id}/metrics` | GET | Get time-series metrics for campaign |
| `/api/campaigns/{id}/leads` | GET | Get attributed leads for campaign |
| `/api/campaigns/{id}/insights` | GET | Get learning engine recommendations |
| `/api/oauth/linkedin/authorize` | GET | Redirect to LinkedIn OAuth2 authorization |
| `/api/oauth/linkedin/callback` | GET | Handle OAuth2 callback, store tokens |

## Integration with Existing Patterns

### 1. Service Layer Pattern (Existing)

Campaign Service follows same pattern as Outreach Service:

```python
# src/core/api/services/campaign_service.py
class CampaignService:
    def __init__(self, producer: KafkaResultProducer):
        self._producer = producer
        self._config = load_config()

    def submit_publish(self, campaign_id: str) -> str:
        """Async publish via thread pool (same as outreach)"""
        task_id = str(uuid.uuid4())
        future = _get_executor().submit(self._run_publish, task_id, campaign_id)
        future.add_done_callback(_log_future_exception)
        return task_id
```

### 2. LLM Client Reuse (Existing)

Content Service uses existing `get_llm_client()` factory:

```python
# src/core/api/services/content_service.py
from src.core.providers.llm_client import get_llm_client

class ContentService:
    def generate_variants(self, base_message: str, sentiments: list[str]) -> list[dict]:
        llm = get_llm_client()  # Reuses existing Gemini/Local factory
        variants = []
        for sentiment in sentiments:
            prompt = f"Rewrite this as {sentiment}: {base_message}"
            result = llm.invoke(prompt)
            variants.append({"sentiment": sentiment, "content": result.content})
        return variants
```

### 3. Background Task Pattern (NEW)

Metrics poller runs as APScheduler background task (initialized in `app.py` lifespan):

```python
# src/core/api/app.py
from apscheduler.schedulers.background import BackgroundScheduler
from src.core.services.metrics_poller import MetricsPoller

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _metrics_poller

    # Existing initialization...

    # NEW: Start metrics poller
    _metrics_poller = MetricsPoller(agent_db=_agent_db)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _metrics_poller.run,
        'interval',
        hours=6,  # Poll every 6 hours
        id='metrics_poller'
    )
    scheduler.start()

    yield

    # Shutdown
    scheduler.shutdown()
```

### 4. Database Access Pattern (Existing)

Campaign tables extend existing AgentDB class:

```python
# src/core/db/agent_db.py (extended)
class AgentDB:
    # ... existing methods ...

    def insert_campaign(self, campaign: dict) -> str:
        """Insert campaign and return campaign_id"""
        session = self.get_session()
        # ...

    def get_campaign_metrics(self, campaign_id: str, since: float = None) -> list[dict]:
        """Get time-series metrics snapshots"""
        # ...
```

## LinkedIn API Client Architecture

### OAuth2 Flow

```python
# src/core/providers/linkedin_api_client.py
class LinkedInAPIClient:
    """Handles LinkedIn API OAuth2 + UGC Posts + Metrics."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://api.linkedin.com"

    def get_authorization_url(self, state: str) -> str:
        """Step 1: Generate OAuth2 authorization URL"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "w_organization_social r_organization_social rw_organization_admin"
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> dict:
        """Step 2: Exchange authorization code for access token"""
        response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri
            }
        )
        return response.json()  # {access_token, expires_in, scope}

    def create_ugc_post(self, access_token: str, organization_urn: str, text: str) -> str:
        """Publish UGC post to LinkedIn"""
        response = requests.post(
            f"{self.base_url}/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json"
            },
            json={
                "author": organization_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
        )
        ugc_post_urn = response.headers.get("x-restli-id")
        return ugc_post_urn

    def get_share_statistics(self, access_token: str, organization_urn: str, ugc_post_urns: list[str]) -> dict:
        """Fetch metrics for specific UGC posts"""
        # Build query params for multiple posts
        posts_param = "&".join([f"ugcPosts[{i}]={urn}" for i, urn in enumerate(ugc_post_urns)])
        url = f"{self.base_url}/rest/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity={organization_urn}&{posts_param}"

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Linkedin-Version": "202601"  # Current versioned API
            }
        )
        return response.json()
```

### Token Storage

Tokens stored in SQLite (encrypted at rest recommended but not required for MVP):

```python
# src/core/db/agent_db.py
def store_oauth_token(self, organization_urn: str, token_data: dict):
    """Store LinkedIn OAuth token"""
    session = self.get_session()
    # Upsert token
    expires_at = time.time() + token_data["expires_in"]
    session.execute(
        """
        INSERT OR REPLACE INTO linkedin_oauth_tokens
        (organization_urn, access_token, refresh_token, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (organization_urn, token_data["access_token"],
         token_data.get("refresh_token"), expires_at, time.time())
    )
    session.commit()

def get_valid_token(self, organization_urn: str) -> str | None:
    """Get valid access token (checks expiry)"""
    session = self.get_session()
    result = session.execute(
        """
        SELECT access_token, expires_at FROM linkedin_oauth_tokens
        WHERE organization_urn = ? AND expires_at > ?
        """,
        (organization_urn, time.time())
    ).fetchone()
    return result[0] if result else None
```

## Metrics Polling Strategy

### Polling Interval

- **Default:** Every 6 hours
- **Configurable:** `linkedin_api.metrics_poll_interval` in `agent.yaml`
- **Rationale:** LinkedIn metrics update within minutes but polling too frequently hits rate limits

### Rate Limits

LinkedIn API rate limits (as of 2026-01):
- **Share Statistics API:** ~100 requests/day per app
- **Strategy:** Batch multiple ugc_post_urns in single request (LinkedIn supports List() param)

```python
# src/core/services/metrics_poller.py
class MetricsPoller:
    def run(self):
        """Poll metrics for all published campaigns in last 12 months"""
        campaigns = self.agent_db.get_published_campaigns(since=time.time() - 365*24*3600)

        # Group by organization to batch API calls
        by_org = {}
        for campaign in campaigns:
            org_urn = campaign["organization_urn"]
            if org_urn not in by_org:
                by_org[org_urn] = []
            by_org[org_urn].append(campaign)

        for org_urn, org_campaigns in by_org.items():
            token = self.agent_db.get_valid_token(org_urn)
            if not token:
                logger.warning(f"No valid token for {org_urn}, skipping metrics poll")
                continue

            # Batch API call (up to 50 posts per request to stay under limits)
            ugc_post_urns = [c["ugc_post_urn"] for c in org_campaigns]
            for batch in self._chunk(ugc_post_urns, 50):
                metrics = self.linkedin_client.get_share_statistics(token, org_urn, batch)
                self._store_metrics(metrics)
                time.sleep(1)  # Rate limiting buffer
```

### Error Handling

- **401 Unauthorized:** Token expired → notify user to re-authenticate
- **429 Rate Limited:** Back off exponentially, skip this poll cycle
- **500 LinkedIn Error:** Log and continue (don't crash poller)

## Lead Attribution Strategy

LinkedIn API **does NOT** provide individual user engagement data (who clicked/liked). Lead attribution is **aggregate-based**:

```python
# src/core/services/lead_engine.py
class LeadEngine:
    def attribute_leads(self, campaign_id: str):
        """Attribute leads from metrics deltas"""
        # Get last 2 snapshots
        snapshots = self.agent_db.get_campaign_metrics(campaign_id, limit=2)
        if len(snapshots) < 2:
            return  # Need at least 2 snapshots to compare

        current = snapshots[0]
        previous = snapshots[1]

        # Calculate deltas
        new_clicks = current["clicks"] - previous["clicks"]
        new_likes = current["likes"] - previous["likes"]
        new_comments = current["comments"] - previous["comments"]

        # Create anonymous lead fingerprints
        if new_clicks > 0:
            for _ in range(new_clicks):
                self.agent_db.insert_lead({
                    "campaign_id": campaign_id,
                    "variant_id": current["variant_id"],
                    "lead_source": "click",
                    "attributed_at": time.time()
                })
        # Repeat for likes, comments...
```

**Future Enhancement:** If user enables LinkedIn Lead Gen Forms, actual lead data (name, email) can be synced via [Lead Sync API](https://learn.microsoft.com/en-us/linkedin/marketing/lead-sync/).

## Learning Engine Recommendations

```python
# src/core/services/learning_engine.py
class LearningEngine:
    def analyze_campaign(self, campaign_id: str) -> dict:
        """Analyze which variant performed best"""
        variants = self.agent_db.get_campaign_variants(campaign_id)
        metrics = self.agent_db.get_campaign_metrics(campaign_id)

        # Group metrics by variant
        by_variant = {}
        for m in metrics:
            vid = m["variant_id"]
            if vid not in by_variant:
                by_variant[vid] = []
            by_variant[vid].append(m)

        # Calculate engagement rate for each variant
        results = []
        for v in variants:
            variant_metrics = by_variant.get(v["id"], [])
            if not variant_metrics:
                continue
            latest = variant_metrics[0]
            engagement_rate = latest["engagement"]
            results.append({
                "sentiment": v["sentiment"],
                "content": v["content"],
                "engagement_rate": engagement_rate,
                "impressions": latest["impressions"],
                "clicks": latest["clicks"]
            })

        # Sort by engagement
        results.sort(key=lambda x: x["engagement_rate"], reverse=True)

        return {
            "best_sentiment": results[0]["sentiment"] if results else None,
            "worst_sentiment": results[-1]["sentiment"] if results else None,
            "recommendations": [
                f"'{results[0]['sentiment']}' tone had {results[0]['engagement_rate']:.2%} engagement",
                f"Avoid '{results[-1]['sentiment']}' tone (only {results[-1]['engagement_rate']:.2%} engagement)"
            ] if len(results) > 1 else []
        }
```

## Build Order (Considering Dependencies)

### Phase 1: Foundation (No Dependencies)

1. **Database Schema:** Add 5 new tables to `models.py` + Alembic migration
2. **Kafka Topics:** Add 2 new topics to `queue/config.py`
3. **Pydantic Schemas:** Define `campaign_schemas.py` for request/response models

### Phase 2: LinkedIn API Client (Depends on Phase 1)

4. **OAuth2 Client:** `linkedin_api_client.py` with authorization + token exchange
5. **UGC Post Creation:** Add `create_ugc_post()` method
6. **Share Statistics:** Add `get_share_statistics()` method
7. **Token Storage:** Extend `agent_db.py` with token CRUD

### Phase 3: Content Generation (Depends on Phase 1, 2)

8. **Content Service:** `content_service.py` using existing `get_llm_client()`
9. **Variant Generation:** LLM prompts for sentiment-based variants

### Phase 4: Campaign Orchestration (Depends on Phase 1, 2, 3)

10. **Campaign Service:** `campaign_service.py` with CRUD + publish logic
11. **Campaign Controller:** `campaign_controller.py` with FastAPI routes
12. **App Integration:** Add router to `app.py`

### Phase 5: Metrics & Analytics (Depends on Phase 1, 2, 4)

13. **Metrics Poller:** `metrics_poller.py` with APScheduler background task
14. **Lead Engine:** `lead_engine.py` with delta-based attribution
15. **Learning Engine:** `learning_engine.py` with variant analysis
16. **Background Task Init:** Add poller to `app.py` lifespan

### Phase 6: CLI Integration (Depends on all phases)

17. **CLI Commands:** Add `campaign create`, `campaign publish`, `campaign metrics`
18. **Kafka Consumer:** Subscribe to `campaign-*` topics for async results

## Configuration Changes

Add to `config/agent.yaml`:

```yaml
linkedin_api:
  client_id: ""  # LinkedIn app client ID
  client_secret: ""  # LinkedIn app client secret (env var recommended)
  redirect_uri: "http://localhost:8080/api/oauth/linkedin/callback"
  metrics_poll_interval: 6  # hours

campaigns:
  default_sentiments:
    - professional
    - casual
    - excited
  max_variants_per_campaign: 5
```

Environment variables (for secrets):

```bash
LINKEDIN_API_CLIENT_ID=...
LINKEDIN_API_CLIENT_SECRET=...
```

## Patterns to Follow

### Pattern 1: Service Layer Async via Thread Pool

**What:** All long-running operations return task_id immediately, execute in background thread, publish results to Kafka

**When:** Campaign publishing, metrics polling

**Example:**
```python
def submit_publish(self, campaign_id: str) -> str:
    task_id = str(uuid.uuid4())
    future = _get_executor().submit(self._run_publish, task_id, campaign_id)
    future.add_done_callback(_log_future_exception)
    return task_id
```

### Pattern 2: LLM Client Factory Reuse

**What:** Use existing `get_llm_client()` for all LLM operations (supports Gemini + local models)

**When:** Content variant generation

**Example:**
```python
from src.core.providers.llm_client import get_llm_client

llm = get_llm_client()
result = llm.invoke(prompt)
```

### Pattern 3: AgentDB Session Management

**What:** Use existing AgentDB class methods for all database operations

**When:** Storing campaigns, metrics, leads

**Example:**
```python
from src.core.api.app import get_agent_db

agent_db = get_agent_db()
agent_db.insert_campaign(campaign_data)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Putting LinkedIn API in MCP Server

**What:** Adding LinkedIn API client to MCP server

**Why bad:** MCP is for browser automation (Selenium RPA), not authenticated API workflows. Mixing concerns creates coupling.

**Instead:** Keep LinkedIn API client in Core Agent (`src/core/providers/linkedin_api_client.py`)

### Anti-Pattern 2: Synchronous Metrics Polling in Request Handler

**What:** Polling LinkedIn metrics during HTTP request

**Why bad:** Metrics API can take 5-10s, blocks request thread, violates FastAPI async patterns

**Instead:** Background APScheduler task polls metrics every 6h, stores snapshots in DB

### Anti-Pattern 3: Storing Tokens in Config Files

**What:** Putting access tokens in `agent.yaml`

**Why bad:** Tokens expire after 60 days, should be rotated, config is version-controlled

**Instead:** Store tokens in SQLite `linkedin_oauth_tokens` table with expiry tracking

## Scalability Considerations

| Concern | At 10 campaigns | At 100 campaigns | At 1000 campaigns |
|---------|----------------|-----------------|-------------------|
| **Metrics Polling** | Single API call | Batch 50 posts/call (2 calls) | Batch 50 posts/call (20 calls), rate limit buffer needed |
| **Database Size** | Negligible (KB) | 1-5 MB | 50-100 MB (time-series metrics grow linearly) |
| **Kafka Topics** | 2 topics, low traffic | Same | Consider partitioning by organization_urn |
| **Background Tasks** | Single scheduler thread | Same | Consider distributed task queue (Celery) if poller exceeds 1h runtime |

**Recommendation for MVP:** Single-node SQLite + APScheduler is sufficient up to 100 campaigns. Beyond that, consider PostgreSQL + Celery.

## Sources

### HIGH Confidence (Official Documentation)

- [LinkedIn Marketing API Overview](https://learn.microsoft.com/en-us/linkedin/marketing/) - Confirmed API structure, versioning (li-lms-2026-01), product offerings
- [LinkedIn UGC Post API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/ugc-post-api) - Confirmed endpoint structure, permissions (w_organization_social, r_organization_social), schema for ugcPosts, max text length (3000 chars)
- [LinkedIn Share Statistics API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/share-statistics) - Confirmed metrics schema (impressionCount, clickCount, likeCount, commentCount, shareCount, engagement), 12-month rolling window, time-bound vs lifetime stats
- [LinkedIn OAuth2 Authorization Code Flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow) - Confirmed 3-legged OAuth flow, token lifespan (60 days), required scopes, redirect URI validation

### MEDIUM Confidence (Existing Codebase)

- Existing Core Agent architecture (FastAPI + LangGraph + Kafka + SQLite) - Verified via code inspection
- Existing service layer pattern (OutreachService async via thread pool) - Verified in `outreach_service.py`
- Existing LLM client factory (supports Gemini + local models) - Verified in `llm_client.py`
- Existing database patterns (AgentDB + Alembic migrations) - Verified in `models.py` and `agent_db.py`

### Gaps and Limitations

1. **Lead Individual Attribution:** LinkedIn API does NOT provide who clicked/liked (privacy). Only aggregate counts available. Lead attribution is delta-based (anonymous).
2. **Rate Limits:** Share Statistics API rate limits not publicly documented. Conservative estimate: ~100 requests/day per app based on standard LinkedIn API limits.
3. **Refresh Tokens:** Programmatic refresh tokens are "available for a limited set of partners" per docs. MVP should assume manual re-auth every 60 days unless partner status granted.
4. **Metrics Latency:** Docs don't specify how often LinkedIn updates metrics internally. Assumed near-real-time but polling every 6h to respect rate limits.
