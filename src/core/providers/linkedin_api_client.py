"""LinkedIn Marketing API client using OAuth2 authorization code flow.

Fully separated from RPA browser session authentication.
Uses Community Management API with Posts endpoint (/rest/posts).
"""

import time
from typing import Optional
from urllib.parse import urlencode

import httpx
from loguru import logger
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from src.config.config_loader import load_config
from src.core.db.models import LinkedInOAuthToken


class LinkedInAPIError(Exception):
    """Base exception for LinkedIn API errors."""
    pass


class TokenExpiredError(LinkedInAPIError):
    """Raised when OAuth2 token is expired or revoked."""
    def __init__(self, message: str, reauth_url: Optional[str] = None):
        super().__init__(message)
        self.reauth_url = reauth_url


class RateLimitError(LinkedInAPIError):
    """Raised when LinkedIn API rate limit is hit."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class LinkedInAPIClient:
    """LinkedIn Marketing API client using OAuth2 authorization code flow.

    Fully separated from RPA browser session authentication.
    Uses Community Management API with Posts endpoint (/rest/posts).
    """

    AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_BASE_URL = "https://api.linkedin.com"
    API_VERSION = "202401"  # LinkedIn API versioning: YYYYMM format

    def __init__(self, db_engine_or_url, config=None):
        """Initialize LinkedIn API client.

        Args:
            db_engine_or_url: SQLAlchemy Engine or database URL string
            config: Optional AgentConfig. If None, will load from config_loader.
        """
        # Load config
        self.config = config or load_config()

        # Create session factory from engine
        if isinstance(db_engine_or_url, str):
            from src.core.db.engine import create_db_engine
            engine = create_db_engine(db_engine_or_url)
        else:
            engine = db_engine_or_url

        self._session_factory = sessionmaker(bind=engine)

        # Create httpx client for API calls
        self._http_client = httpx.Client(timeout=30.0)

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Build LinkedIn OAuth2 authorization URL.

        Args:
            state: Optional CSRF protection token

        Returns:
            Full authorization URL to redirect user to
        """
        params = {
            "response_type": "code",
            "client_id": self.config.linkedin_api.client_id,
            "redirect_uri": self.config.linkedin_api.redirect_uri,
            "scope": " ".join(self.config.linkedin_api.scopes),
        }

        if state:
            params["state"] = state

        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            dict with access_token and expires_at keys

        Raises:
            ValueError: On error response from LinkedIn
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.linkedin_api.redirect_uri,
            "client_id": self.config.linkedin_api.client_id,
            "client_secret": self.config.linkedin_api.client_secret,
        }

        try:
            response = self._http_client.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Token exchange failed: {error_detail}")
            raise ValueError(f"Token exchange failed: {error_detail}")
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            raise ValueError(f"Token exchange error: {e}")

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 5184000)  # Default 60 days

        if not access_token:
            raise ValueError("No access_token in response")

        expires_at = time.time() + expires_in

        # Save token to DB
        organization_urn = self.config.linkedin_api.organization_urn
        self._save_token(organization_urn, access_token, expires_at)

        logger.info(f"Token saved for {organization_urn}, expires at {expires_at}")

        return {
            "access_token": access_token,
            "expires_at": expires_at,
        }

    def _save_token(self, organization_urn: str, access_token: str, expires_at: float):
        """Upsert OAuth token in database.

        Args:
            organization_urn: LinkedIn organization URN (e.g. urn:li:organization:12345)
            access_token: OAuth2 access token
            expires_at: Unix timestamp when token expires
        """
        with self._session_factory() as session:
            session.merge(
                LinkedInOAuthToken(
                    organization_urn=organization_urn,
                    access_token=access_token,
                    expires_at=expires_at,
                    created_at=time.time(),
                )
            )
            session.commit()

    def _load_token(self, organization_urn: str) -> Optional[LinkedInOAuthToken]:
        """Load OAuth token from database.

        Args:
            organization_urn: LinkedIn organization URN

        Returns:
            LinkedInOAuthToken or None if not found
        """
        with self._session_factory() as session:
            return session.get(LinkedInOAuthToken, organization_urn)

    def get_valid_token(self, organization_urn: Optional[str] = None) -> str:
        """Get valid access token from database.

        Args:
            organization_urn: Optional organization URN. Uses config default if not provided.

        Returns:
            Valid access token string

        Raises:
            TokenExpiredError: If token is expired or not found
        """
        org_urn = organization_urn or self.config.linkedin_api.organization_urn

        if not org_urn:
            raise TokenExpiredError(
                "No organization_urn configured. Set LINKEDIN_API_ORGANIZATION_URN env var.",
                reauth_url=self.get_authorization_url()
            )

        token_row = self._load_token(org_urn)

        if not token_row:
            reauth_url = self.get_authorization_url()
            raise TokenExpiredError(
                f"No token found for {org_urn}. Re-authorize at: {reauth_url}",
                reauth_url=reauth_url
            )

        now = time.time()

        # Check if expired
        if now >= token_row.expires_at:
            reauth_url = self.get_authorization_url()
            raise TokenExpiredError(
                f"Token expired for {org_urn}. Re-authorize at: {reauth_url}",
                reauth_url=reauth_url
            )

        # Check if within warning threshold
        warning_days = self.config.campaign.token_expiry_warning_days
        warning_threshold = now + (warning_days * 24 * 3600)

        if token_row.expires_at <= warning_threshold:
            days_remaining = (token_row.expires_at - now) / (24 * 3600)
            logger.warning(
                f"LinkedIn OAuth token for {org_urn} expires in {days_remaining:.1f} days "
                f"(expires at {token_row.expires_at}). Re-authorize soon to avoid disruption."
            )

        return token_row.access_token

    def check_token_health(self, organization_urn: Optional[str] = None) -> dict:
        """Check token health status.

        Args:
            organization_urn: Optional organization URN. Uses config default if not provided.

        Returns:
            dict with keys: valid, expires_at, days_remaining, needs_reauth, warning
        """
        org_urn = organization_urn or self.config.linkedin_api.organization_urn

        if not org_urn:
            return {
                "valid": False,
                "expires_at": None,
                "days_remaining": None,
                "needs_reauth": True,
                "warning": "No organization_urn configured"
            }

        token_row = self._load_token(org_urn)

        if not token_row:
            return {
                "valid": False,
                "expires_at": None,
                "days_remaining": None,
                "needs_reauth": True,
                "warning": f"No token found for {org_urn}"
            }

        now = time.time()
        days_remaining = (token_row.expires_at - now) / (24 * 3600)

        if now >= token_row.expires_at:
            return {
                "valid": False,
                "expires_at": token_row.expires_at,
                "days_remaining": days_remaining,
                "needs_reauth": True,
                "warning": f"Token expired {abs(days_remaining):.1f} days ago"
            }

        warning_days = self.config.campaign.token_expiry_warning_days
        warning = None

        if days_remaining <= warning_days:
            warning = (
                f"Token expires in {days_remaining:.1f} days. "
                f"Re-authorize soon to avoid disruption."
            )

        return {
            "valid": True,
            "expires_at": token_row.expires_at,
            "days_remaining": days_remaining,
            "needs_reauth": False,
            "warning": warning
        }

    def _make_api_request(
        self,
        method: str,
        path: str,
        organization_urn: Optional[str] = None,
        **kwargs
    ) -> httpx.Response:
        """Make authenticated API request to LinkedIn.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g. /rest/posts)
            organization_urn: Optional organization URN
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response object

        Raises:
            TokenExpiredError: On 401 response
            RateLimitError: On 429 response
        """
        token = self.get_valid_token(organization_urn)

        # Set required headers
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": self.API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        })

        url = f"{self.API_BASE_URL}{path}"

        try:
            response = self._http_client.request(method, url, headers=headers, **kwargs)

            # Handle 401 - token expired or revoked
            if response.status_code == 401:
                reauth_url = self.get_authorization_url()
                raise TokenExpiredError(
                    f"LinkedIn API returned 401. Token expired or revoked. Re-authorize at: {reauth_url}",
                    reauth_url=reauth_url
                )

            # Handle 429 - rate limit
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_after_int = int(retry_after) if retry_after else None
                raise RateLimitError(
                    f"LinkedIn API rate limit exceeded. Retry after {retry_after} seconds.",
                    retry_after=retry_after_int
                )

            response.raise_for_status()
            return response

        except TokenExpiredError:
            raise
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn API error: {e.response.status_code} - {e.response.text}")
            raise LinkedInAPIError(f"API request failed: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"LinkedIn API request error: {e}")
            raise LinkedInAPIError(f"API request error: {e}")

    def create_post(
        self,
        text: str,
        organization_urn: Optional[str] = None,
        visibility: str = "PUBLIC"
    ) -> dict:
        """Create a LinkedIn post via Community Management API.

        Args:
            text: Post content text
            organization_urn: Optional organization URN. Uses config default if not provided.
            visibility: Post visibility (PUBLIC, CONNECTIONS, etc.)

        Returns:
            Parsed JSON response with post URN in 'id' field or 'x-restli-id' header

        Raises:
            LinkedInAPIError: On API error
            TokenExpiredError: If token is expired
            RateLimitError: If rate limit exceeded
        """
        org_urn = organization_urn or self.config.linkedin_api.organization_urn

        if not org_urn:
            raise LinkedInAPIError("No organization_urn configured")

        payload = {
            "author": org_urn,
            "commentary": text,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        response = self._make_api_request("POST", "/rest/posts", json=payload)

        # Post URN can be in response body or x-restli-id header
        response_data = response.json() if response.text else {}

        if not response_data.get("id"):
            # Check header
            post_urn = response.headers.get("x-restli-id")
            if post_urn:
                response_data["id"] = post_urn

        logger.info(f"Created LinkedIn post: {response_data.get('id', 'unknown')}")

        return response_data

    def __del__(self):
        """Clean up HTTP client on garbage collection."""
        if hasattr(self, '_http_client'):
            self._http_client.close()
