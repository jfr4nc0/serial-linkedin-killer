"""SQLAlchemy declarative models for all persistent tables."""

import time
import uuid

from sqlalchemy import Column, Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    data = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)
    expires_at = Column(Float, nullable=False, index=True)  # For cleanup queries


class JobApplication(Base):
    __tablename__ = "job_applications"

    job_id = Column(String, primary_key=True)
    applied_at = Column(Float)
    success = Column(Integer, index=True)  # For batch queries filtering by success
    error = Column(Text)


class MessageSent(Base):
    __tablename__ = "messages_sent"

    employee_profile_url = Column(String, primary_key=True)
    employee_name = Column(String)
    company_name = Column(String)
    company_linkedin_url = Column(
        String, index=True
    )  # For querying contacted companies
    sent_at = Column(Float)
    success = Column(Integer, index=True)  # For batch queries filtering by success
    method = Column(String)
    error = Column(Text)


class DailyQuota(Base):
    __tablename__ = "daily_quota"

    date = Column(String, primary_key=True)
    count = Column(Integer, default=0)


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String)
    industry = Column(String, index=True)
    country = Column(String, index=True)
    locality = Column(String)
    region = Column(String)
    size = Column(String, index=True)
    linkedin_url = Column(String)
    website = Column(String)
    founded = Column(String)


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, index=True, nullable=False)
    company_name = Column(String)
    company_linkedin_url = Column(String)
    employee_name = Column(String)
    employee_title = Column(String)
    employee_profile_url = Column(String)
    created_at = Column(Float, default=time.time)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_urn = Column(String, nullable=False, index=True)
    base_message = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft", index=True)  # draft, scheduled, active, paused, completed, failed
    scheduled_at = Column(Float, nullable=True)
    created_at = Column(Float, nullable=False, default=time.time)
    updated_at = Column(Float, nullable=False, default=time.time, onupdate=time.time)


class CampaignVariant(Base):
    __tablename__ = "campaign_variants"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, nullable=False, index=True)
    sentiment = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    linkedin_post_urn = Column(String, nullable=True)  # set after publishing
    published_at = Column(Float, nullable=True)
    is_selected = Column(Integer, nullable=False, default=1)  # 1=selected for publishing, 0=rejected
    created_at = Column(Float, nullable=False, default=time.time)


class CampaignMetric(Base):
    __tablename__ = "campaign_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String, nullable=False, index=True)
    variant_id = Column(String, nullable=False, index=True)
    polled_at = Column(Float, nullable=False, default=time.time)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    likes = Column(Integer, nullable=False, default=0)
    comments = Column(Integer, nullable=False, default=0)
    shares = Column(Integer, nullable=False, default=0)
    engagement = Column(Float, nullable=False, default=0.0)
    unique_impressions = Column(Integer, nullable=False, default=0)


class CampaignLead(Base):
    __tablename__ = "campaign_leads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String, nullable=False, index=True)
    variant_id = Column(String, nullable=False, index=True)
    lead_source = Column(String, nullable=False)  # "click", "like", "comment", "share"
    fingerprint = Column(String, nullable=True)  # UTM or engagement delta hash
    attributed_at = Column(Float, nullable=False, default=time.time)


class LinkedInOAuthToken(Base):
    __tablename__ = "linkedin_oauth_tokens"
    organization_urn = Column(String, primary_key=True)
    access_token = Column(Text, nullable=False)
    expires_at = Column(Float, nullable=False)  # Unix timestamp when token expires
    created_at = Column(Float, nullable=False, default=time.time)
