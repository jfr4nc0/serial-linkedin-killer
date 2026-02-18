---
phase: 08-api-foundation-authentication
plan: 02
subsystem: core-providers
tags: [oauth2, linkedin-api, authentication, token-management, fastapi]
dependency-graph:
  requires: [campaign-config, campaign-db-schema]
  provides: [linkedin-oauth-client, oauth-endpoints]
  affects: [api-app, providers]
tech-stack:
  added: []
  patterns: [oauth2-authorization-code-flow, token-persistence, token-expiration-tracking]
key-files:
  created:
    - src/core/providers/linkedin_api_client.py
    - src/core/api/controllers/oauth_controller.py
  modified:
    - src/core/providers/__init__.py
    - src/core/api/app.py
decisions:
  - Used httpx for HTTP requests instead of authlib's OAuth2Session (KISS principle for simple authorization code flow)
  - Implemented sync client pattern (consistent with existing codebase using thread pools for async operations)
  - Store token expiry warning threshold in CampaignConfig (7 days default) for configurability
  - Return reauth_url in TokenExpiredError for improved error messages and user experience
  - Added token health check to app startup (non-blocking, logs warnings/info)
metrics:
  duration: 223s
  completed: 2026-02-12T19:08:36Z
  tasks: 2
  commits: 2
---

# Phase 08 Plan 02: OAuth Implementation Summary

**One-liner:** LinkedIn API client with OAuth2 authorization code flow, token persistence, expiration tracking, 401 detection, and FastAPI callback endpoints.

## Tasks Completed

### Task 1: Create LinkedIn API client with OAuth2 and token management
- **Commit:** 6cf8fe0
- **Files:** src/core/providers/linkedin_api_client.py, src/core/providers/__init__.py
- **What:** Implemented LinkedInAPIClient class with OAuth2 authorization code flow. Key features: get_authorization_url (builds LinkedIn OAuth URL with scopes), exchange_code_for_token (POST to TOKEN_URL and stores token), get_valid_token (loads token from DB with expiry checking and 7-day warning), check_token_health (returns health dict for monitoring), _make_api_request (sets versioned headers and detects 401/429 responses), create_post (POST to /rest/posts). Custom exceptions: TokenExpiredError (with reauth_url), RateLimitError (with retry_after). Token persistence via LinkedInOAuthToken model using session.merge() pattern. Completely separated from RPA auth (no linkedin_mcp imports).

### Task 2: Add OAuth2 callback endpoints and register in FastAPI app
- **Commit:** e3de6f2
- **Files:** src/core/api/controllers/oauth_controller.py, src/core/api/app.py
- **What:** Created OAuth controller with 3 endpoints: GET /api/oauth/linkedin/authorize (generates authorization URL with state), GET /api/oauth/linkedin/callback (handles OAuth callback and exchanges code for token), GET /api/oauth/linkedin/token-health (returns token health status). Registered oauth_router in FastAPI app. Added startup token health check that logs warnings if token expires soon or info if no token exists. Error handling for TokenExpiredError, LinkedInAPIError, and generic exceptions.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All verification checks passed:
1. ✅ LinkedInAPIClient imports cleanly
2. ✅ Authorization URL contains linkedin.com/oauth, response_type=code, and configured scopes
3. ✅ check_token_health() returns {valid: False, needs_reauth: True} when no token exists
4. ✅ OAuth controller has 3 routes registered at /api/oauth/linkedin/*
5. ✅ FastAPI app includes oauth_router and all routes are accessible
6. ✅ No imports from src/linkedin_mcp/ (RPA separation verified)
7. ✅ API client uses required headers: LinkedIn-Version, X-Restli-Protocol-Version, Content-Type
8. ✅ Token expiry warning threshold uses config.campaign.token_expiry_warning_days (default 7)

## Key Decisions Made

1. **httpx over authlib's OAuth2Session:** Used httpx directly for token exchange POST request instead of authlib's OAuth2Session. LinkedIn's authorization code flow is simple (single POST, no refresh), so KISS principle applies. authlib remains in deps for potential future use.

2. **Sync client pattern:** Implemented synchronous LinkedInAPIClient consistent with existing codebase patterns. Project uses thread pools for async operations (see OutreachService), so sync client fits the architecture.

3. **Token expiry warning in CampaignConfig:** Placed token_expiry_warning_days in CampaignConfig (not LinkedInAPIConfig) for flexibility. Default 7 days balances advance notice with alert fatigue.

4. **reauth_url in TokenExpiredError:** Custom exception includes reauth_url field for better error messages. API endpoints can return reauth_url in 401 responses, improving developer/user experience.

5. **Non-blocking startup health check:** Token health check in app.py lifespan uses try/except to log status without blocking startup. Missing credentials are logged at INFO (not ERROR) since OAuth setup is optional initially.

## Impact Analysis

**Downstream Dependencies:**
- Phase 9 (Variant Generation) can now use LinkedInAPIClient to validate organization_urn before generating variants
- Phase 10 (Publishing) will use create_post() to publish campaign variants via Community Management API
- Phase 11 (Metrics Collection) will use _make_api_request() to poll metrics from LinkedIn API
- Health dashboards can poll /api/oauth/linkedin/token-health for token status monitoring

**API Endpoints:**
- GET /api/oauth/linkedin/authorize - returns authorization_url and state for user redirect
- GET /api/oauth/linkedin/callback - handles LinkedIn redirect with code parameter
- GET /api/oauth/linkedin/token-health - returns token health dict for monitoring

**Configuration:**
- Requires env vars: LINKEDIN_API_CLIENT_ID, LINKEDIN_API_CLIENT_SECRET, LINKEDIN_API_ORGANIZATION_URN
- Optional: LINKEDIN_API_REDIRECT_URI (defaults to http://localhost:8080/api/oauth/linkedin/callback)

**Authentication:**
- OAuth2 completely separated from RPA browser session authentication
- Tokens stored in linkedin_oauth_tokens table with 60-day expiry
- No programmatic refresh (manual re-authorization required when tokens expire)

## User Setup Required

Before using the LinkedIn API client, users must:

1. **Create LinkedIn Developer App:**
   - Visit https://www.linkedin.com/developers/apps
   - Create new app or use existing one

2. **Add Community Management API product:**
   - Navigate to Your App -> Products tab
   - Add "Community Management API"

3. **Configure redirect URI:**
   - Navigate to Your App -> Auth tab -> Redirect URLs
   - Add: http://localhost:8080/api/oauth/linkedin/callback

4. **Set environment variables:**
   ```bash
   export LINKEDIN_API_CLIENT_ID="<from Auth tab>"
   export LINKEDIN_API_CLIENT_SECRET="<from Auth tab>"
   export LINKEDIN_API_ORGANIZATION_URN="urn:li:organization:<id>"
   ```

5. **Authorize the app:**
   - Start FastAPI server: `poetry run uvicorn src.core.api.app:app --host 0.0.0.0 --port 8080`
   - Visit http://localhost:8080/api/oauth/linkedin/authorize
   - Follow authorization_url in response
   - LinkedIn redirects to callback endpoint automatically
   - Verify authentication: http://localhost:8080/api/oauth/linkedin/token-health

6. **Apply for Standard tier access (recommended):**
   - Development tier: 500 calls/app/24hrs
   - Standard tier: Higher limits for multi-variant campaigns
   - Navigate to Your App -> Access Request

## Self-Check: PASSED

**Created files verified:**
```bash
FOUND: src/core/providers/linkedin_api_client.py
FOUND: src/core/api/controllers/oauth_controller.py
```

**Commits verified:**
```bash
FOUND: 6cf8fe0 (Task 1: LinkedIn API client)
FOUND: e3de6f2 (Task 2: OAuth endpoints)
```

**Client features verified:**
```
✓ get_authorization_url() generates valid LinkedIn OAuth URL
✓ check_token_health() returns correct structure when no token exists
✓ Custom exceptions (TokenExpiredError, RateLimitError) defined
✓ _make_api_request() sets versioned headers (LinkedIn-Version: 202401, X-Restli-Protocol-Version: 2.0.0)
✓ No imports from src/linkedin_mcp/ (complete separation from RPA auth)
```

**OAuth endpoints verified:**
```
✓ GET /api/oauth/linkedin/authorize endpoint registered
✓ GET /api/oauth/linkedin/callback endpoint registered
✓ GET /api/oauth/linkedin/token-health endpoint registered
✓ oauth_router included in FastAPI app
✓ Startup token health check logs warnings/info appropriately
```

**Success criteria met:**
- [x] LinkedInAPIClient can generate OAuth2 authorization URL and exchange code for token
- [x] Token persistence works via SQLAlchemy (save/load/upsert pattern)
- [x] Token expiration tracking with 7-day warning works
- [x] 401 detection raises TokenExpiredError with reauth URL
- [x] Community Management API Posts endpoint used with correct versioned headers
- [x] OAuth2 fully separated from RPA (no linkedin_mcp imports)
- [x] FastAPI endpoints for authorize, callback, and token-health registered
- [x] Startup health check logs token status
