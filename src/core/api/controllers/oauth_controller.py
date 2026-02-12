"""Controller for LinkedIn OAuth2 flow endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from src.core.providers.linkedin_api_client import (
    LinkedInAPIClient,
    LinkedInAPIError,
    TokenExpiredError,
)

router = APIRouter(prefix="/api/oauth/linkedin", tags=["oauth"])


def get_linkedin_client() -> LinkedInAPIClient:
    """Get LinkedIn API client using shared AgentDB engine."""
    from src.core.api.app import get_agent_db

    agent_db = get_agent_db()
    if not agent_db:
        raise HTTPException(status_code=500, detail="AgentDB not initialized")

    return LinkedInAPIClient(agent_db._engine)


@router.get("/authorize")
def authorize():
    """Generate LinkedIn OAuth2 authorization URL.

    Returns:
        JSON with authorization_url and state fields
    """
    try:
        client = get_linkedin_client()
        state = str(uuid.uuid4())
        authorization_url = client.get_authorization_url(state=state)

        return {
            "authorization_url": authorization_url,
            "state": state
        }
    except Exception as e:
        logger.error(f"Failed to generate authorization URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
def callback(
    code: str = Query(..., description="Authorization code from LinkedIn"),
    state: str = Query(None, description="CSRF protection state parameter")
):
    """OAuth2 callback endpoint. LinkedIn redirects here after user authorizes.

    Args:
        code: Authorization code to exchange for access token
        state: Optional CSRF protection state

    Returns:
        JSON with status, expires_at, and days_until_expiry
    """
    try:
        client = get_linkedin_client()
        token_data = client.exchange_code_for_token(code)

        # Calculate days until expiry
        expires_at = token_data["expires_at"]
        import time
        days_until_expiry = (expires_at - time.time()) / (24 * 3600)

        return {
            "status": "authenticated",
            "expires_at": expires_at,
            "days_until_expiry": round(days_until_expiry, 1)
        }
    except ValueError as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/token-health")
def token_health():
    """Check LinkedIn OAuth token health status.

    Returns:
        Token health dict with valid, expires_at, days_remaining, needs_reauth, warning fields
    """
    try:
        client = get_linkedin_client()
        health = client.check_token_health()
        return health
    except TokenExpiredError as e:
        return {
            "valid": False,
            "expires_at": None,
            "days_remaining": None,
            "needs_reauth": True,
            "warning": str(e),
            "reauth_url": e.reauth_url
        }
    except Exception as e:
        logger.error(f"Token health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
