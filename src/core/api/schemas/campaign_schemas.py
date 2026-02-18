"""Request/response schemas for campaign management endpoints."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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


class GenerateVariantsRequest(BaseModel):
    """Request to generate content for campaign variants."""
    custom_prompts: Optional[Dict[str, str]] = None  # Optional dict mapping sentiment name to custom prompt


class GenerateVariantsResponse(BaseModel):
    """Response after generating variant content."""
    campaign_id: str
    variants_generated: int
    diversity: dict  # Contains passed (bool), min_diversity (float), failing_pairs (list), pair_count (int)
    variants: List[dict]  # Each with id, sentiment, content_snippet


class VariantEditRequest(BaseModel):
    """Request to edit a variant's content."""
    content: str = Field(min_length=1)  # Must be non-empty


class VariantEditResponse(BaseModel):
    """Response after editing a variant."""
    id: str
    campaign_id: str
    sentiment: str
    content: str
    is_selected: int
