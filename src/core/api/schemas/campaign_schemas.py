"""Request/response schemas for campaign management endpoints."""

from typing import List, Optional

from pydantic import BaseModel


# Request schemas
class CampaignCreateRequest(BaseModel):
    """Request to create a new campaign."""
    base_message: str
    sentiments: Optional[List[str]] = None  # defaults to config.default_sentiments
    scheduled_at: Optional[float] = None  # unix timestamp
    organization_urn: Optional[str] = None  # defaults to config.organization_urn


class CampaignUpdateRequest(BaseModel):
    """Request to update a campaign (PATCH semantics - all fields optional)."""
    base_message: Optional[str] = None
    scheduled_at: Optional[float] = None


class CampaignStatusTransition(BaseModel):
    """Request to transition campaign status."""
    status: str  # target status to transition to


# Response schemas
class CampaignVariantResponse(BaseModel):
    """A single campaign variant with its content and metrics."""
    id: str
    campaign_id: str
    sentiment: str
    content: str
    linkedin_post_urn: Optional[str] = None
    published_at: Optional[float] = None
    is_selected: int  # 1=selected for publishing, 0=rejected
    created_at: float


class CampaignMetricsSummary(BaseModel):
    """Aggregated latest metrics across all campaign variants."""
    impressions: int = 0
    clicks: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class CampaignListItem(BaseModel):
    """Campaign summary for list view."""
    id: str
    organization_urn: str
    base_message: str  # truncated to 100 chars
    status: str
    variant_count: int
    metrics_summary: Optional[CampaignMetricsSummary] = None
    scheduled_at: Optional[float] = None
    created_at: float
    updated_at: float


class CampaignDetailResponse(BaseModel):
    """Full campaign details with all variants."""
    id: str
    organization_urn: str
    base_message: str  # full text
    status: str
    scheduled_at: Optional[float] = None
    created_at: float
    updated_at: float
    variants: List[CampaignVariantResponse]
    metrics_summary: Optional[CampaignMetricsSummary] = None


class CampaignListResponse(BaseModel):
    """Response containing multiple campaigns."""
    campaigns: List[CampaignListItem]
    total: int


class CampaignDeleteResponse(BaseModel):
    """Response after deleting a campaign."""
    id: str
    status: str = "deleted"
    deleted_at: float
