"""Controller for campaign management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.core.api.schemas.campaign_schemas import (
    CampaignCreateRequest,
    CampaignDeleteResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignStatusTransition,
    CampaignUpdateRequest,
)
from src.core.api.services.campaign_service import CampaignService

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def get_campaign_service() -> CampaignService:
    from src.core.api.app import get_campaign_service as _get

    return _get()


@router.post("", response_model=CampaignDetailResponse, status_code=201)
def create_campaign(
    request: CampaignCreateRequest,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignDetailResponse:
    """Create a new campaign with sentiment variants."""
    from src.config.config_loader import load_config

    config = load_config()

    # Apply defaults from config
    sentiments = request.sentiments or config.campaign.default_sentiments
    organization_urn = request.organization_urn or config.linkedin_api.organization_urn

    # Validate organization_urn
    if not organization_urn:
        raise HTTPException(
            status_code=400,
            detail="organization_urn is required. Set it in config or provide in request.",
        )

    try:
        # Create campaign
        result = service.create_campaign(
            base_message=request.base_message,
            sentiments=sentiments,
            organization_urn=organization_urn,
            scheduled_at=request.scheduled_at,
        )

        # Return full campaign details
        campaign = service.get_campaign(result["id"])
        return CampaignDetailResponse(**campaign)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    organization_urn: Optional[str] = None,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignListResponse:
    """List all campaigns with variant counts and metrics summary."""
    try:
        campaigns = service.list_campaigns(organization_urn=organization_urn)
        return CampaignListResponse(campaigns=campaigns, total=len(campaigns))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
def get_campaign(
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignDetailResponse:
    """Get full campaign details with all variants."""
    try:
        campaign = service.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return CampaignDetailResponse(**campaign)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{campaign_id}", response_model=CampaignDetailResponse)
def update_campaign(
    campaign_id: str,
    request: CampaignUpdateRequest,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignDetailResponse:
    """Update campaign fields (only allowed for draft campaigns)."""
    try:
        campaign = service.update_campaign(
            campaign_id=campaign_id,
            base_message=request.base_message,
            scheduled_at=request.scheduled_at,
        )
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return CampaignDetailResponse(**campaign)
    except ValueError as e:
        # Check if it's a "not found" error or validation error
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{campaign_id}", response_model=CampaignDeleteResponse)
def delete_campaign(
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignDeleteResponse:
    """Soft delete a campaign (preserves all historical data)."""
    try:
        result = service.delete_campaign(campaign_id)
        if not result:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return CampaignDeleteResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/status", response_model=CampaignDetailResponse)
def transition_status(
    campaign_id: str,
    request: CampaignStatusTransition,
    service: CampaignService = Depends(get_campaign_service),
) -> CampaignDetailResponse:
    """Transition campaign to a new status."""
    try:
        campaign = service.transition_status(campaign_id, request.status)
        return CampaignDetailResponse(**campaign)
    except ValueError as e:
        # Check if it's a "not found" error or validation error
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
