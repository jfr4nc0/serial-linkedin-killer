"""SQLAlchemy declarative models for all persistent tables."""

from sqlalchemy import Column, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    data = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)
    expires_at = Column(Float, nullable=False)


class JobApplication(Base):
    __tablename__ = "job_applications"

    job_id = Column(String, primary_key=True)
    applied_at = Column(Float)
    success = Column(Integer)
    error = Column(Text)


class MessageSent(Base):
    __tablename__ = "messages_sent"

    employee_profile_url = Column(String, primary_key=True)
    employee_name = Column(String)
    sent_at = Column(Float)
    success = Column(Integer)
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
