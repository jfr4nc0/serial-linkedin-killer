"""Content generation service for campaign variants using LLM providers.

This service orchestrates the generation of sentiment-based content variants for campaigns,
leveraging the LLM client factory and text diversity validation to ensure quality output.
"""

from typing import Dict, List, Optional, Union

from langchain_core.messages import HumanMessage
from sqlalchemy import Engine

from src.core.db.engine import create_db_engine, create_session_factory
from src.core.db.models import Campaign, CampaignVariant
from src.core.providers.llm_client import get_llm_client
from src.core.utils.text_diversity import validate_diversity


class ContentGenerationService:
    """Service for generating campaign variant content using LLM providers."""

    # 10 sentiment presets with distinct prompt strategies
    SENTIMENT_PRESETS: Dict[str, str] = {
        "urgency": "Rewrite with a sense of urgency and time-sensitivity. Use action verbs, deadlines, and scarcity language.",
        "authority": "Rewrite as an authoritative thought leader. Use confident language, industry expertise, and data-driven assertions.",
        "calm": "Rewrite with a calm, measured tone. Use reassuring language, steady pacing, and thoughtful observations.",
        "empathy": "Rewrite with deep empathy and understanding. Acknowledge challenges, validate feelings, and offer genuine support.",
        "curiosity": "Rewrite to spark curiosity and engagement. Use thought-provoking questions, surprising facts, and open loops.",
        "social_proof": "Rewrite leveraging social proof. Reference trends, community adoption, peer success stories, and collective momentum.",
        "educational": "Rewrite as educational content. Teach something valuable, break down complexity, and provide actionable takeaways.",
        "provocative": "Rewrite with a provocative, contrarian angle. Challenge assumptions, question norms, and present bold perspectives.",
        "inspirational": "Rewrite to inspire and motivate. Use aspirational language, vision-casting, and empowering calls to action.",
        "humorous": "Rewrite with wit and humor. Use clever wordplay, relatable observations, and a light conversational tone.",
    }

    def __init__(self, engine_or_url: Union[Engine, str]):
        """Initialize ContentGenerationService with database engine or URL.

        Args:
            engine_or_url: SQLAlchemy Engine instance or database URL string
        """
        if isinstance(engine_or_url, str):
            self._engine = create_db_engine(engine_or_url)
        else:
            self._engine = engine_or_url
        self._session_factory = create_session_factory(self._engine)

    def get_sentiment_prompt(
        self, sentiment: str, custom_prompt: Optional[str] = None
    ) -> str:
        """Get the prompt instruction for a given sentiment.

        Args:
            sentiment: Sentiment name to look up in presets
            custom_prompt: Optional custom prompt to use instead of preset

        Returns:
            Prompt instruction string

        Raises:
            ValueError: If sentiment not found in presets and no custom_prompt provided
        """
        if custom_prompt is not None:
            return custom_prompt

        if sentiment not in self.SENTIMENT_PRESETS:
            raise ValueError(
                f"Unknown sentiment '{sentiment}'. Must be one of: "
                f"{', '.join(self.SENTIMENT_PRESETS.keys())} or provide custom_prompt."
            )

        return self.SENTIMENT_PRESETS[sentiment]

    def generate_variant_content(
        self, base_message: str, sentiment: str, custom_prompt: Optional[str] = None
    ) -> str:
        """Generate content for a single variant using LLM.

        Args:
            base_message: The base campaign message to transform
            sentiment: Sentiment name for prompt lookup
            custom_prompt: Optional custom prompt instruction

        Returns:
            Generated content string (stripped of whitespace)
        """
        sentiment_prompt = self.get_sentiment_prompt(sentiment, custom_prompt)

        # Build full LLM prompt
        prompt = f"""You are a LinkedIn content strategist. Your task is to create a LinkedIn post variant.

Base message:
{base_message}

Sentiment instruction:
{sentiment_prompt}

Requirements:
- Keep the core message and intent intact
- Adapt the tone, style, and framing according to the sentiment instruction
- Write for a professional LinkedIn audience
- Keep it concise (under 1300 characters for LinkedIn post limits)
- Do not include hashtags unless they naturally fit
- Output ONLY the rewritten post text, nothing else"""

        # Call LLM client
        llm_client = get_llm_client()
        response = llm_client.invoke([HumanMessage(content=prompt)])

        # Extract and return content
        generated_text = response.content.strip()
        return generated_text

    def generate_campaign_variants(
        self, campaign_id: str, custom_prompts: Optional[Dict[str, str]] = None
    ) -> dict:
        """Generate content for all empty variants in a campaign.

        Args:
            campaign_id: Campaign ID to generate variants for
            custom_prompts: Optional dict mapping sentiment names to custom prompts

        Returns:
            Dict with campaign_id, variants_generated count, diversity validation,
            and variant details

        Raises:
            ValueError: If campaign not found, not in draft status, or no empty variants
        """
        with self._session_factory() as session:
            # Load campaign
            campaign = session.get(Campaign, campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            if campaign.status != "draft":
                raise ValueError(
                    f"Cannot generate content for campaign with status '{campaign.status}'. "
                    "Only draft campaigns can have content generated."
                )

            # Load empty variants
            empty_variants = (
                session.query(CampaignVariant)
                .filter(
                    CampaignVariant.campaign_id == campaign_id,
                    CampaignVariant.content == "",
                )
                .all()
            )

            if not empty_variants:
                raise ValueError("No empty variants to generate content for")

            # Generate content for each empty variant
            generated_contents: List[str] = []
            variant_details: List[dict] = []

            for variant in empty_variants:
                # Get custom prompt if provided
                custom_prompt = None
                if custom_prompts:
                    custom_prompt = custom_prompts.get(variant.sentiment)

                # Generate content
                generated_content = self.generate_variant_content(
                    campaign.base_message, variant.sentiment, custom_prompt
                )

                # Update variant in database
                variant.content = generated_content
                generated_contents.append(generated_content)

                # Collect variant details for response
                variant_details.append({
                    "id": variant.id,
                    "sentiment": variant.sentiment,
                    "content_snippet": generated_content[:100],
                })

            # Validate diversity across all generated contents
            diversity_result = validate_diversity(generated_contents, threshold=0.7)

            # Commit all changes
            session.commit()

            return {
                "campaign_id": campaign_id,
                "variants_generated": len(empty_variants),
                "diversity": diversity_result,
                "variants": variant_details,
            }
