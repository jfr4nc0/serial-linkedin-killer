"""Campaign CRUD operations and status lifecycle management."""

import time
import uuid
from typing import Dict, List, Optional, Union

from sqlalchemy import Engine, func

from src.config.config_loader import load_config
from src.core.db.engine import create_db_engine, create_session_factory
from src.core.db.models import Campaign, CampaignMetric, CampaignVariant


class CampaignService:
    """Service for campaign CRUD operations and status transitions."""

    # Status lifecycle state machine
    VALID_TRANSITIONS = {
        "draft": ["scheduled", "active", "failed"],
        "scheduled": ["active", "paused", "failed"],
        "active": ["paused", "completed", "failed"],
        "paused": ["active", "completed", "failed"],
        "completed": [],  # terminal state
        "failed": ["draft"],  # allow retry from failed
        # "deleted" is not in transitions - can't transition out of deleted
    }

    def __init__(self, engine_or_url: Union[Engine, str]):
        """Initialize CampaignService with database engine or URL.

        Args:
            engine_or_url: SQLAlchemy Engine instance or database URL string
        """
        if isinstance(engine_or_url, str):
            self._engine = create_db_engine(engine_or_url)
        else:
            self._engine = engine_or_url
        self._session_factory = create_session_factory(self._engine)
        self._config = load_config()

    def create_campaign(
        self,
        base_message: str,
        sentiments: List[str],
        organization_urn: str,
        scheduled_at: Optional[float] = None,
    ) -> dict:
        """Create a new campaign with variants for each sentiment.

        Args:
            base_message: The base message template for the campaign
            sentiments: List of sentiment names for variant generation
            organization_urn: LinkedIn organization URN
            scheduled_at: Optional unix timestamp for scheduled publishing

        Returns:
            Dict with id, status, variant_count, created_at
        """
        campaign_id = str(uuid.uuid4())
        now = time.time()

        with self._session_factory() as session:
            # Create campaign
            campaign = Campaign(
                id=campaign_id,
                organization_urn=organization_urn,
                base_message=base_message,
                status="draft",
                scheduled_at=scheduled_at,
                created_at=now,
                updated_at=now,
            )
            session.add(campaign)

            # Create variant placeholders (content will be filled by Phase 10)
            for sentiment in sentiments:
                variant = CampaignVariant(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    sentiment=sentiment,
                    content="",  # empty until content generation
                    is_selected=1,  # selected by default
                    created_at=now,
                )
                session.add(variant)

            session.commit()

            return {
                "id": campaign_id,
                "status": "draft",
                "variant_count": len(sentiments),
                "created_at": now,
            }

    def list_campaigns(self, organization_urn: Optional[str] = None) -> List[dict]:
        """List all campaigns with variant counts and metrics summary.

        Args:
            organization_urn: Optional filter by organization URN

        Returns:
            List of campaign dicts matching CampaignListItem schema
        """
        with self._session_factory() as session:
            query = session.query(Campaign)

            if organization_urn:
                query = query.filter(Campaign.organization_urn == organization_urn)

            query = query.order_by(Campaign.created_at.desc())
            campaigns = query.all()

            result = []
            for campaign in campaigns:
                # Count variants for this campaign
                variant_count = (
                    session.query(func.count(CampaignVariant.id))
                    .filter(CampaignVariant.campaign_id == campaign.id)
                    .scalar()
                ) or 0

                # Get latest metrics aggregation
                metrics_summary = self._get_latest_metrics_summary(
                    session, campaign.id
                )

                # Truncate base_message to 100 chars
                truncated_message = campaign.base_message
                if len(truncated_message) > 100:
                    truncated_message = truncated_message[:100] + "..."

                result.append({
                    "id": campaign.id,
                    "organization_urn": campaign.organization_urn,
                    "base_message": truncated_message,
                    "status": campaign.status,
                    "variant_count": variant_count,
                    "metrics_summary": metrics_summary,
                    "scheduled_at": campaign.scheduled_at,
                    "created_at": campaign.created_at,
                    "updated_at": campaign.updated_at,
                })

            return result

    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        """Get full campaign details with all variants and metrics.

        Args:
            campaign_id: Campaign ID to retrieve

        Returns:
            Campaign dict matching CampaignDetailResponse schema, or None if not found
        """
        with self._session_factory() as session:
            campaign = session.get(Campaign, campaign_id)
            if not campaign:
                return None

            # Load all variants for this campaign
            variants = (
                session.query(CampaignVariant)
                .filter(CampaignVariant.campaign_id == campaign_id)
                .order_by(CampaignVariant.created_at)
                .all()
            )

            variant_list = [
                {
                    "id": v.id,
                    "campaign_id": v.campaign_id,
                    "sentiment": v.sentiment,
                    "content": v.content,
                    "linkedin_post_urn": v.linkedin_post_urn,
                    "published_at": v.published_at,
                    "is_selected": v.is_selected,
                    "created_at": v.created_at,
                }
                for v in variants
            ]

            # Get metrics summary
            metrics_summary = self._get_latest_metrics_summary(session, campaign_id)

            return {
                "id": campaign.id,
                "organization_urn": campaign.organization_urn,
                "base_message": campaign.base_message,
                "status": campaign.status,
                "scheduled_at": campaign.scheduled_at,
                "created_at": campaign.created_at,
                "updated_at": campaign.updated_at,
                "variants": variant_list,
                "metrics_summary": metrics_summary,
            }

    def update_campaign(
        self,
        campaign_id: str,
        base_message: Optional[str] = None,
        scheduled_at: Optional[float] = None,
    ) -> Optional[dict]:
        """Update campaign fields (only allowed for draft campaigns).

        Args:
            campaign_id: Campaign ID to update
            base_message: Optional new base message
            scheduled_at: Optional new scheduled timestamp

        Returns:
            Updated campaign dict, or None if not found

        Raises:
            ValueError: If campaign is not in draft status
        """
        with self._session_factory() as session:
            campaign = session.get(Campaign, campaign_id)
            if not campaign:
                return None

            if campaign.status != "draft":
                raise ValueError(
                    f"Cannot update campaign with status '{campaign.status}'. "
                    "Only draft campaigns can be edited."
                )

            # Update provided fields
            if base_message is not None:
                campaign.base_message = base_message
            if scheduled_at is not None:
                campaign.scheduled_at = scheduled_at

            campaign.updated_at = time.time()
            session.commit()

            # Return full campaign details
            return self.get_campaign(campaign_id)

    def delete_campaign(self, campaign_id: str) -> Optional[dict]:
        """Soft delete a campaign by setting status to 'deleted'.

        Preserves all historical data (variants, metrics, leads).

        Args:
            campaign_id: Campaign ID to delete

        Returns:
            Dict with id, status='deleted', deleted_at, or None if not found
        """
        with self._session_factory() as session:
            campaign = session.get(Campaign, campaign_id)
            if not campaign:
                return None

            now = time.time()
            campaign.status = "deleted"
            campaign.updated_at = now
            session.commit()

            return {
                "id": campaign.id,
                "status": "deleted",
                "deleted_at": now,
            }

    def transition_status(self, campaign_id: str, target_status: str) -> dict:
        """Transition campaign to a new status.

        Validates transition against the status lifecycle state machine.

        Args:
            campaign_id: Campaign ID to transition
            target_status: Target status to transition to

        Returns:
            Updated campaign dict with new status

        Raises:
            ValueError: If campaign not found or transition is invalid
        """
        with self._session_factory() as session:
            campaign = session.get(Campaign, campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            current_status = campaign.status

            # Check if transition is valid
            valid_targets = self.VALID_TRANSITIONS.get(current_status, [])
            if target_status not in valid_targets:
                if not valid_targets:
                    raise ValueError(
                        f"Cannot transition from '{current_status}' to '{target_status}'. "
                        f"Valid transitions from '{current_status}': none (terminal state)"
                    )
                else:
                    raise ValueError(
                        f"Cannot transition from '{current_status}' to '{target_status}'. "
                        f"Valid transitions from '{current_status}': {', '.join(valid_targets)}"
                    )

            # Perform transition
            campaign.status = target_status
            campaign.updated_at = time.time()
            session.commit()

            # Return updated campaign
            return self.get_campaign(campaign_id)

    def _get_latest_metrics_summary(
        self, session, campaign_id: str
    ) -> Optional[dict]:
        """Get aggregated latest metrics for a campaign.

        For each variant, gets the most recent metric row, then sums across all variants.

        Args:
            session: Active SQLAlchemy session
            campaign_id: Campaign ID to get metrics for

        Returns:
            Dict with impressions, clicks, likes, comments, shares, or None if no metrics
        """
        # Subquery: for each variant_id, get the max polled_at timestamp
        latest_polls_subquery = (
            session.query(
                CampaignMetric.variant_id,
                func.max(CampaignMetric.polled_at).label("max_polled_at"),
            )
            .filter(CampaignMetric.campaign_id == campaign_id)
            .group_by(CampaignMetric.variant_id)
            .subquery()
        )

        # Join to get the full metric rows with latest timestamps
        latest_metrics = (
            session.query(CampaignMetric)
            .join(
                latest_polls_subquery,
                (CampaignMetric.variant_id == latest_polls_subquery.c.variant_id)
                & (CampaignMetric.polled_at == latest_polls_subquery.c.max_polled_at),
            )
            .all()
        )

        if not latest_metrics:
            return None

        # Aggregate across all latest metrics
        total_impressions = sum(m.impressions for m in latest_metrics)
        total_clicks = sum(m.clicks for m in latest_metrics)
        total_likes = sum(m.likes for m in latest_metrics)
        total_comments = sum(m.comments for m in latest_metrics)
        total_shares = sum(m.shares for m in latest_metrics)

        return {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "likes": total_likes,
            "comments": total_comments,
            "shares": total_shares,
        }
