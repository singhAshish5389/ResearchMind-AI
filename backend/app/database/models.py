"""
ResearchMind AI – SQLAlchemy Database Models
=============================================
Defines all ORM models for PostgreSQL storage.

Tables:
  - users
  - research_projects
  - research_plans (db)
  - research_sources (db)
  - research_reports (db)
  - uploaded_documents
  - agent_execution_logs
  - usage_records
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow():
    return datetime.now(timezone.utc)


def _new_uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── Users ──────────────────────────────────────────────────────────────────────


class User(Base):
    """Registered application user."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    research_projects = relationship("ResearchProject", back_populates="user", cascade="all, delete-orphan")
    uploaded_documents = relationship("UploadedDocument", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


# ── Research Projects ──────────────────────────────────────────────────────────


class ResearchProject(Base):
    """
    A research job created by a user.
    Tracks the full lifecycle from planning to completion.
    """

    __tablename__ = "research_projects"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Research topic and settings
    topic = Column(Text, nullable=False)
    depth = Column(String(20), nullable=False, default="standard")
    mode = Column(String(20), nullable=False, default="web")
    language = Column(String(50), nullable=False, default="English")

    # Workflow status
    status = Column(String(30), nullable=False, default="pending", index=True)

    # Result counts
    source_count = Column(Integer, default=0)
    finding_count = Column(Integer, default=0)
    claim_count = Column(Integer, default=0)

    # Flags
    plan_approved = Column(Boolean, default=False)
    has_report = Column(Boolean, default=False)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Workflow progress events (JSON array)
    workflow_events = Column(JSONB, default=list)

    # Timing
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="research_projects")
    plan = relationship("ResearchPlanDB", back_populates="project", uselist=False, cascade="all, delete-orphan")
    sources = relationship("ResearchSourceDB", back_populates="project", cascade="all, delete-orphan")
    report = relationship("ResearchReportDB", back_populates="project", uselist=False, cascade="all, delete-orphan")
    execution_logs = relationship("AgentExecutionLog", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_projects_user_status", "user_id", "status"),
        Index("ix_research_projects_created", "created_at"),
    )


class ResearchPlanDB(Base):
    """Persisted research plan for a project."""

    __tablename__ = "research_plans"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan_id = Column(String(36), nullable=False)  # Pydantic plan_id

    scope_and_objectives = Column(Text, nullable=False)
    information_categories = Column(JSONB, default=list)
    research_questions = Column(JSONB, default=list)  # Serialized ResearchQuestion list
    estimated_duration_minutes = Column(Integer, default=10)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship("ResearchProject", back_populates="plan")


class ResearchSourceDB(Base):
    """A source collected during research for a project."""

    __tablename__ = "research_sources"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(String(36), nullable=False)  # Pydantic source_id
    question_id = Column(String(36), nullable=False)

    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    domain = Column(String(255), default="")
    excerpt = Column(Text, default="")
    published_date = Column(String(50), nullable=True)
    relevance_score = Column(Float, nullable=True)
    is_duplicate = Column(Boolean, default=False)

    retrieved_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship("ResearchProject", back_populates="sources")

    __table_args__ = (
        Index("ix_research_sources_project", "project_id"),
        Index("ix_research_sources_question", "question_id"),
    )


class ResearchReportDB(Base):
    """Persisted research report for a project."""

    __tablename__ = "research_reports"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    report_id = Column(String(36), nullable=False)  # Pydantic report_id

    title = Column(Text, nullable=False)
    executive_summary = Column(Text, nullable=False)
    objectives = Column(Text, nullable=False)
    methodology = Column(Text, nullable=False)
    key_findings = Column(JSONB, default=list)
    detailed_analysis = Column(Text, nullable=False)
    industry_trends = Column(JSONB, default=list)
    opportunities = Column(JSONB, default=list)
    risks_and_challenges = Column(JSONB, default=list)
    verified_claims = Column(JSONB, default=list)
    uncertain_findings = Column(JSONB, default=list)
    limitations = Column(Text, nullable=False)
    conclusion = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    language = Column(String(50), default="English")

    # PDF stored as filesystem path (avoid storing large blobs in DB)
    pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship("ResearchProject", back_populates="report")


# ── Documents ──────────────────────────────────────────────────────────────────


class UploadedDocument(Base):
    """A document uploaded by a user for RAG research."""

    __tablename__ = "uploaded_documents"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)  # Local storage path

    chunk_count = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    is_indexed = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="uploaded_documents")

    __table_args__ = (
        Index("ix_uploaded_documents_user", "user_id"),
    )


# ── Observability ──────────────────────────────────────────────────────────────


class AgentExecutionLog(Base):
    """Log of a single agent execution within a research workflow."""

    __tablename__ = "agent_execution_logs"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)

    agent_name = Column(String(50), nullable=False)
    stage = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # success, failed, skipped
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship("ResearchProject", back_populates="execution_logs")

    __table_args__ = (
        Index("ix_agent_logs_project", "project_id"),
    )
