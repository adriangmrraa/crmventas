"""
CRM VENTAS - SQLAlchemy 2.0 ORM Models
All database tables mapped as declarative models.
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime, Date, Time,
    ForeignKey, DECIMAL, Float, Index, UniqueConstraint, CheckConstraint,
    Computed,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
import uuid


class Base(DeclarativeBase):
    pass


# ============================================================
# INFRASTRUCTURE
# ============================================================

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clinic_name = Column(Text, nullable=False, default="Clinica Dental")
    bot_phone_number = Column(Text, unique=True, nullable=False)
    owner_email = Column(Text)
    clinic_location = Column(Text)
    clinic_website = Column(Text)
    system_prompt_template = Column(Text)

    # Company profile (DEV-35)
    logo_url = Column(Text)
    contact_email = Column(Text)
    contact_phone = Column(Text)
    whatsapp_number = Column(Text)
    timezone = Column(Text, default="America/Argentina/Buenos_Aires")
    currency = Column(String(10), default="ARS")
    business_hours_start = Column(String(5), default="09:00")
    business_hours_end = Column(String(5), default="18:00")
    ai_agent_name = Column(Text, default="Asistente")
    ai_agent_active = Column(Boolean, default=True)
    website = Column(Text)
    address = Column(Text)
    industry = Column(Text)

    # AI Agent Personality & Script (DEV-36)
    ai_system_prompt = Column(Text)
    ai_tone = Column(Text, default="profesional_argentino")
    ai_services_description = Column(Text)
    ai_qualification_questions = Column(JSONB, default=[])
    ai_objection_responses = Column(JSONB, default=[])
    ai_company_description = Column(Text)
    business_hours = Column(JSONB, default={"weekdays": "09:00-18:00", "saturday": "09:00-13:00", "sunday": "closed"})

    # Usage stats
    total_tokens_used = Column(BigInteger, default=0)
    total_tool_calls = Column(BigInteger, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    professional_id = Column(Integer)
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('ceo', 'professional', 'secretary', 'setter', 'closer')", name="users_role_check"),
        CheckConstraint("status IN ('pending', 'active', 'suspended')", name="users_status_check"),
        Index("idx_users_email", "email"),
        Index("idx_users_status", "status"),
    )


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    scope = Column(Text, default="global")
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="credentials_tenant_name_unique"),
    )


class MetaToken(Base):
    __tablename__ = "meta_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(Text, nullable=False)
    token_type = Column(String(50))
    page_id = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "token_type", name="meta_tokens_tenant_type_unique"),
    )


class InboundMessage(Base):
    __tablename__ = "inbound_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    provider = Column(Text, nullable=False)
    provider_message_id = Column(Text, nullable=False)
    event_id = Column(Text)
    from_number = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    error = Column(Text)
    correlation_id = Column(Text)

    __table_args__ = (
        UniqueConstraint("provider", "provider_message_id", name="inbound_messages_provider_msgid_unique"),
        CheckConstraint("status IN ('received', 'processing', 'done', 'failed')", name="inbound_messages_status_check"),
        Index("idx_inbound_messages_from_number_received_at", "from_number", received_at.desc()),
        Index("idx_inbound_messages_status", "status"),
    )


class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    event_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="info")
    message = Column(Text)
    payload = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# CRM CORE — LEADS
# ============================================================

class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    phone_number = Column(String(50), nullable=False)
    first_name = Column(Text)
    last_name = Column(Text)
    email = Column(Text)
    status = Column(Text, default="new")
    source = Column(Text, default="whatsapp_inbound")
    meta_lead_id = Column(Text)
    assigned_seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    stage_id = Column(UUID(as_uuid=True))

    # Lead scoring (Patch 15)
    score = Column(Integer, default=0)
    score_breakdown = Column(JSONB, default={})
    score_updated_at = Column(DateTime(timezone=True))

    # Meta Ads attribution (Patch 009)
    lead_source = Column(String(50), default="ORGANIC")
    meta_campaign_id = Column(String(255))
    meta_ad_id = Column(String(255))
    meta_ad_headline = Column(Text)
    meta_ad_body = Column(Text)
    external_ids = Column(JSONB, default={})

    # Prospecting / Apify fields (Patch 7 + extended)
    apify_title = Column(Text)
    apify_category_name = Column(Text)
    apify_address = Column(Text)
    apify_city = Column(Text)
    apify_state = Column(Text)
    apify_country_code = Column(Text)
    apify_website = Column(Text)
    apify_place_id = Column(Text)
    apify_total_score = Column(Float)
    apify_reviews_count = Column(Integer)
    apify_rating = Column(Float)
    apify_scraped_at = Column(DateTime(timezone=True))
    prospecting_niche = Column(Text)
    prospecting_location_query = Column(Text)
    social_links = Column(JSONB, default={})

    # Outreach fields
    outreach_message_sent = Column(Boolean, default=False)
    outreach_send_requested = Column(Boolean, default=False)
    outreach_message_content = Column(Text)
    outreach_last_requested_at = Column(DateTime(timezone=True))
    outreach_last_sent_at = Column(DateTime(timezone=True))

    # Assignment tracking (Patch 11)
    initial_assignment_source = Column(Text)
    assignment_history = Column(JSONB, default=[])

    # Company & value (Patch 16)
    company = Column(Text)
    estimated_value = Column(DECIMAL(12, 2), default=0)

    # Lead status system (Patch 018)
    status_changed_at = Column(DateTime)
    status_changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status_metadata = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "phone_number", name="leads_tenant_phone_unique"),
        Index("idx_leads_score", "tenant_id", score.desc()),
        Index("idx_leads_lead_source", "tenant_id", "lead_source"),
        Index("idx_leads_meta_campaign", "tenant_id", "meta_campaign_id"),
        Index("idx_leads_meta_ad", "tenant_id", "meta_ad_id"),
    )


# ============================================================
# CRM CORE — LEAD STATUS SYSTEM (Patch 018)
# ============================================================

class LeadStatus(Base):
    __tablename__ = "lead_statuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(Text)
    color = Column(String(7), default="#6B7280")
    icon = Column(String(50), default="circle")
    badge_style = Column(Text, default="default")
    is_active = Column(Boolean, default=True)
    is_initial = Column(Boolean, default=False)
    is_final = Column(Boolean, default=False)
    requires_comment = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="lead_statuses_tenant_code_unique"),
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="lead_statuses_color_check"),
        CheckConstraint("code ~ '^[a-z_]+$'", name="lead_statuses_code_check"),
        Index("idx_lead_statuses_tenant", "tenant_id"),
        Index("idx_lead_statuses_active", "tenant_id", "is_active"),
        Index("idx_lead_statuses_initial", "tenant_id", "is_initial"),
        Index("idx_lead_statuses_final", "tenant_id", "is_final"),
    )


class LeadStatusTransition(Base):
    __tablename__ = "lead_status_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    from_status_code = Column(Text)
    to_status_code = Column(Text, nullable=False)
    is_allowed = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    approval_role = Column(Text)
    max_daily_transitions = Column(Integer)
    label = Column(Text)
    description = Column(Text)
    icon = Column(String(50))
    button_style = Column(Text, default="default")
    validation_rules = Column(JSONB, default={})
    pre_conditions = Column(JSONB, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "from_status_code", "to_status_code", name="lead_status_transitions_unique"),
        Index("idx_transitions_from", "tenant_id", "from_status_code"),
        Index("idx_transitions_to", "tenant_id", "to_status_code"),
        Index("idx_transitions_allowed", "tenant_id", "is_allowed"),
    )


class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    from_status_code = Column(Text)
    to_status_code = Column(Text, nullable=False)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    changed_by_name = Column(Text)
    changed_by_role = Column(Text)
    changed_by_ip = Column(INET)
    changed_by_user_agent = Column(Text)
    comment = Column(Text)
    reason_code = Column(Text)
    source = Column(Text, default="manual")
    metadata_ = Column("metadata", JSONB, default={})
    session_id = Column(UUID(as_uuid=True))
    request_id = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_history_lead_tenant", "lead_id", "tenant_id", created_at.desc()),
        Index("idx_history_tenant_date", "tenant_id", created_at.desc()),
        Index("idx_history_user", "changed_by_user_id", created_at.desc()),
        Index("idx_history_status", "to_status_code", created_at.desc()),
        Index("idx_history_source", "source", created_at.desc()),
    )


class LeadStatusTrigger(Base):
    __tablename__ = "lead_status_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    trigger_name = Column(Text, nullable=False)
    from_status_code = Column(Text)
    to_status_code = Column(Text, nullable=False)
    action_type = Column(Text, nullable=False)
    action_config = Column(JSONB, nullable=False)
    execution_mode = Column(Text, default="immediate")
    delay_minutes = Column(Integer, default=0)
    scheduled_time = Column(Time)
    timezone = Column(Text, default="UTC")
    conditions = Column(JSONB, default={})
    filters = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    max_executions = Column(Integer)
    error_handling = Column(Text, default="retry")
    retry_count = Column(Integer, default=3)
    retry_delay_minutes = Column(Integer, default=5)
    description = Column(Text)
    tags = Column(ARRAY(Text))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_executed_at = Column(DateTime)
    execution_count = Column(Integer, default=0)

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('email', 'whatsapp', 'task', 'webhook', 'api_call', 'notification')",
            name="lead_status_triggers_action_type_check",
        ),
        CheckConstraint(
            "execution_mode IN ('immediate', 'delayed', 'scheduled')",
            name="lead_status_triggers_execution_mode_check",
        ),
        Index("idx_triggers_active", "tenant_id", "is_active", "to_status_code"),
        Index("idx_triggers_type", "tenant_id", "action_type"),
        Index("idx_triggers_execution", "tenant_id", "execution_mode", "scheduled_time"),
    )


class LeadStatusTriggerLog(Base):
    __tablename__ = "lead_status_trigger_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_id = Column(UUID(as_uuid=True), ForeignKey("lead_status_triggers.id", ondelete="CASCADE"))
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    from_status_code = Column(Text)
    to_status_code = Column(Text, nullable=False)
    execution_status = Column(Text, nullable=False)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    execution_duration_ms = Column(Integer)
    result_data = Column(JSONB, default={})
    error_message = Column(Text)
    error_stack = Column(Text)
    retry_count = Column(Integer, default=0)
    worker_id = Column(Text)
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_trigger_logs_status", "execution_status", created_at.asc()),
        Index("idx_trigger_logs_trigger", "trigger_id", created_at.desc()),
        Index("idx_trigger_logs_lead", "lead_id", created_at.desc()),
        Index("idx_trigger_logs_tenant", "tenant_id", created_at.desc()),
    )


# ============================================================
# CRM CORE — ACTIVITY EVENTS (DEV-39)
# ============================================================

class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(String(100), nullable=False)
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_activity_events_tenant_created", "tenant_id", created_at.desc()),
        Index("idx_activity_events_actor", "actor_id", created_at.desc()),
        Index("idx_activity_events_entity", "entity_type", "entity_id"),
    )


# ============================================================
# CRM CORE — SLA RULES (DEV-42)
# ============================================================

class SlaRule(Base):
    __tablename__ = "sla_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    trigger_type = Column(String(50), nullable=False)
    threshold_minutes = Column(Integer, nullable=False)
    applies_to_statuses = Column(ARRAY(Text))
    applies_to_roles = Column(ARRAY(Text))
    escalate_to_ceo = Column(Boolean, default=True)
    escalate_after_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_sla_rules_tenant_active", "tenant_id", "is_active"),
    )


# ============================================================
# CRM CORE — NOTE MENTIONS (DEV-43)
# ============================================================

class NoteMention(Base):
    __tablename__ = "note_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id = Column(UUID(as_uuid=True), ForeignKey("lead_notes.id", ondelete="CASCADE"), nullable=False)
    mentioned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_note_mentions_user", "mentioned_user_id", created_at.desc()),
        Index("idx_note_mentions_note", "note_id"),
    )


# ============================================================
# CRM CORE — TASKS (Patch 16)
# ============================================================

class LeadTask(Base):
    __tablename__ = "lead_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"))
    seller_id = Column(Integer, ForeignKey("sellers.id", ondelete="SET NULL"))
    title = Column(Text, nullable=False)
    description = Column(Text)
    due_date = Column(DateTime(timezone=True))
    status = Column(Text, default="pending")
    priority = Column(Text, default="medium")
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed')", name="lead_tasks_status_check"),
        CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name="lead_tasks_priority_check"),
        Index("idx_lead_tasks_tenant", "tenant_id"),
        Index("idx_lead_tasks_lead", "lead_id"),
    )


# ============================================================
# CRM CORE — SELLERS
# ============================================================

class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    phone_number = Column(String(50))
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SellerMetrics(Base):
    """Seller performance metrics (Patch 11)."""
    __tablename__ = "seller_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Conversations
    total_conversations = Column(Integer, default=0)
    active_conversations = Column(Integer, default=0)
    conversations_assigned_today = Column(Integer, default=0)

    # Messages
    total_messages_sent = Column(Integer, default=0)
    total_messages_received = Column(Integer, default=0)
    avg_response_time_seconds = Column(Integer)

    # Leads
    leads_assigned = Column(Integer, default=0)
    leads_converted = Column(Integer, default=0)
    conversion_rate = Column(DECIMAL(5, 2))

    # Prospecting
    prospects_generated = Column(Integer, default=0)
    prospects_converted = Column(Integer, default=0)

    # Time
    total_chat_minutes = Column(Integer, default=0)
    avg_session_duration_minutes = Column(Integer)

    # Metadata
    last_activity_at = Column(DateTime(timezone=True))
    metrics_calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    metrics_period_start = Column(DateTime(timezone=True))
    metrics_period_end = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("seller_id", "tenant_id", "metrics_period_start", name="seller_metrics_unique"),
        CheckConstraint("conversion_rate >= 0 AND conversion_rate <= 100", name="seller_metrics_rate_check"),
        Index("idx_seller_metrics_tenant", "tenant_id"),
        Index("idx_seller_metrics_seller", "seller_id"),
        Index("idx_seller_metrics_period", metrics_period_start.desc()),
    )


class SellerAgendaEvent(Base):
    __tablename__ = "seller_agenda_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(Integer, ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"))
    client_id = Column(Integer, ForeignKey("clients.id"))
    notes = Column(Text)
    source = Column(Text, default="manual")
    status = Column(Text, default="scheduled")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# CRM CORE — SALES PIPELINE
# ============================================================

class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"))
    name = Column(Text, nullable=False)
    description = Column(Text)
    value = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(Text, default="USD")
    stage = Column(Text, nullable=False)
    probability = Column(DECIMAL(5, 2), default=0)
    expected_close_date = Column(Date)
    closed_at = Column(DateTime)
    close_reason = Column(Text)
    lost_reason = Column(Text)
    tags = Column(JSONB, default=[])
    custom_fields = Column(JSONB, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_opportunities_tenant", "tenant_id"),
        Index("idx_opportunities_lead", "tenant_id", "lead_id"),
        Index("idx_opportunities_seller", "tenant_id", "seller_id"),
        Index("idx_opportunities_stage", "tenant_id", "stage"),
        Index("idx_opportunities_expected_close", "tenant_id", "expected_close_date"),
    )


class SalesTransaction(Base):
    __tablename__ = "sales_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id"))
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"))
    amount = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(Text, default="USD")
    transaction_date = Column(Date, nullable=False)
    description = Column(Text)
    payment_method = Column(Text)
    payment_status = Column(Text, default="pending")
    payment_reference = Column(Text)
    attribution_source = Column(Text)
    meta_campaign_id = Column(String(255))
    meta_ad_id = Column(String(255))
    invoice_number = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_sales_transactions_tenant", "tenant_id"),
        Index("idx_sales_transactions_opportunity", "tenant_id", "opportunity_id"),
        Index("idx_sales_transactions_lead", "tenant_id", "lead_id"),
        Index("idx_sales_transactions_date", "tenant_id", "transaction_date"),
        Index("idx_sales_transactions_source", "tenant_id", "attribution_source"),
    )


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    phone_number = Column(String(50), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    status = Column(String(50), default="active")
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "phone_number", name="clients_tenant_phone_unique"),
    )


# ============================================================
# CHAT
# ============================================================

class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    external_user_id = Column(Text, nullable=False)
    channel = Column(Text, default="whatsapp")
    status = Column(Text, default="active")
    paused_until = Column(DateTime(timezone=True))
    pause_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_chat_conversations_tenant_user", "tenant_id", "external_user_id"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    from_number = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    correlation_id = Column(Text)

    # Seller assignment (Patch 11)
    assigned_seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_at = Column(DateTime(timezone=True))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assignment_source = Column(Text, default="manual")

    # Multi-channel routing (Patch 27)
    platform = Column(String(20))  # whatsapp | instagram | facebook
    platform_message_id = Column(Text)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="chat_messages_role_check"),
        Index("idx_chat_messages_from_number_created_at", "from_number", created_at.desc()),
        Index("idx_chat_messages_assigned_seller", "assigned_seller_id"),
        Index("idx_chat_messages_assignment_source", "assignment_source"),
        Index("idx_chat_messages_platform", "platform"),
    )


# ============================================================
# MULTI-CHANNEL ROUTING (Patch 27)
# ============================================================

class ChannelBinding(Base):
    __tablename__ = "channel_bindings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)     # ycloud | meta | chatwoot
    channel_type = Column(String(50), nullable=False)  # whatsapp | instagram | facebook
    channel_id = Column(String(255), nullable=False)   # page_id, waba_id, phone_number_id
    label = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "channel_id", name="channel_bindings_provider_channel_unique"),
        Index("idx_channel_bindings_tenant", "tenant_id", "is_active"),
        Index("idx_channel_bindings_lookup", "provider", "channel_id", "is_active"),
    )


class BusinessAsset(Base):
    __tablename__ = "business_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String(50), nullable=False)    # facebook_page | instagram_account | whatsapp_waba
    external_id = Column(String(255), nullable=False)
    name = Column(String(255))
    metadata_ = Column("metadata", JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "asset_type", "external_id", name="business_assets_tenant_type_extid_unique"),
        Index("idx_business_assets_tenant", "tenant_id", "is_active"),
    )


# ============================================================
# MARKETING — META ADS
# ============================================================

class MetaAdsCampaign(Base):
    __tablename__ = "meta_ads_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    meta_campaign_id = Column(String(255), nullable=False)
    meta_account_id = Column(String(255), nullable=False)
    meta_business_manager_id = Column(String(255))
    name = Column(Text, nullable=False)
    objective = Column(Text)
    status = Column(Text)
    daily_budget = Column(DECIMAL(12, 2))
    lifetime_budget = Column(DECIMAL(12, 2))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    targeting = Column(JSONB, default={})
    spend = Column(DECIMAL(12, 2), default=0)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    leads = Column(Integer, default=0)
    opportunities = Column(Integer, default=0)
    revenue = Column(DECIMAL(12, 2), default=0)
    roi_percentage = Column(DECIMAL(5, 2), default=0)
    last_synced_at = Column(DateTime)
    sync_status = Column(Text, default="pending")
    sync_error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "meta_campaign_id", name="unique_meta_campaign_per_tenant"),
        Index("idx_meta_campaigns_tenant", "tenant_id"),
        Index("idx_meta_campaigns_status", "tenant_id", "status"),
        Index("idx_meta_campaigns_account", "tenant_id", "meta_account_id"),
    )


class MetaAdsInsight(Base):
    __tablename__ = "meta_ads_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    meta_campaign_id = Column(String(255), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("meta_ads_campaigns.id"))
    date = Column(Date, nullable=False)
    date_start = Column(DateTime)
    date_stop = Column(DateTime)
    spend = Column(DECIMAL(12, 2), default=0)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    cpc = Column(DECIMAL(10, 2))
    cpm = Column(DECIMAL(10, 2))
    ctr = Column(DECIMAL(5, 2))
    leads = Column(Integer, default=0)
    cost_per_lead = Column(DECIMAL(10, 2))
    opportunities = Column(Integer, default=0)
    cost_per_opportunity = Column(DECIMAL(10, 2))
    attribution_window = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "meta_campaign_id", "date", "attribution_window", name="unique_insight_per_day"),
        Index("idx_meta_insights_tenant", "tenant_id"),
        Index("idx_meta_insights_campaign", "tenant_id", "meta_campaign_id"),
        Index("idx_meta_insights_date", "tenant_id", "date"),
    )


class MetaTemplate(Base):
    __tablename__ = "meta_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    meta_template_id = Column(String(255), nullable=False)
    waba_id = Column(String(255), nullable=False)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    language = Column(Text, default="es")
    status = Column(Text)
    components = Column(JSONB, nullable=False)
    example = Column(JSONB)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    read_count = Column(Integer, default=0)
    replied_count = Column(Integer, default=0)
    last_synced_at = Column(DateTime)
    sync_status = Column(Text, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "meta_template_id", name="unique_meta_template_per_tenant"),
        Index("idx_meta_templates_tenant", "tenant_id"),
        Index("idx_meta_templates_status", "tenant_id", "status"),
        Index("idx_meta_templates_category", "tenant_id", "category"),
    )


# ============================================================
# AUTOMATION
# ============================================================

class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(Text, nullable=False)
    trigger_type = Column(Text, nullable=False)
    trigger_conditions = Column(JSONB, nullable=False)
    action_type = Column(Text, nullable=False)
    action_config = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_automation_rules_tenant", "tenant_id"),
        Index("idx_automation_rules_active", "tenant_id", "is_active"),
        Index("idx_automation_rules_trigger", "tenant_id", "trigger_type"),
    )


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("automation_rules.id"))
    trigger_type = Column(Text, nullable=False)
    trigger_data = Column(JSONB, nullable=False)
    action_type = Column(Text, nullable=False)
    action_config = Column(JSONB, nullable=False)
    action_result = Column(JSONB)
    status = Column(Text, nullable=False)
    error_message = Column(Text)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_automation_logs_tenant", "tenant_id"),
        Index("idx_automation_logs_rule", "tenant_id", "rule_id"),
        Index("idx_automation_logs_status", "tenant_id", "status"),
        Index("idx_automation_logs_created", "tenant_id", created_at.asc()),
    )


# ============================================================
# NOTIFICATIONS (Patch 8 + Patch 016)
# ============================================================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(255), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(50), default="medium")
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    related_entity_type = Column(String(100))
    related_entity_id = Column(String(255))
    metadata_ = Column("metadata", JSONB)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_notifications_recipient_tenant", "recipient_id", "tenant_id", created_at.desc()),
    )


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    user_id = Column(String(255), primary_key=True)
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    desktop_notifications = Column(Boolean, default=True)
    mute_until = Column(DateTime(timezone=True))
    muted_types = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# ASSIGNMENT RULES (Patch 11)
# ============================================================

class AssignmentRule(Base):
    __tablename__ = "assignment_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    rule_name = Column(Text, nullable=False)
    rule_type = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    config = Column(JSONB, nullable=False, default={})
    apply_to_lead_source = Column(ARRAY(Text))
    apply_to_lead_status = Column(ARRAY(Text))
    apply_to_seller_roles = Column(ARRAY(Text))
    max_conversations_per_seller = Column(Integer)
    min_response_time_seconds = Column(Integer)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "rule_name", name="assignment_rules_tenant_name_unique"),
        CheckConstraint(
            "rule_type IN ('round_robin', 'performance', 'specialty', 'load_balance')",
            name="assignment_rules_type_check",
        ),
    )


# ============================================================
# CRM CORE — LEAD TAGS SYSTEM
# ============================================================

class LeadNote(Base):
    """Lead notes for handoff, internal comments, and follow-ups (DEV-21 + DEV-23)."""
    __tablename__ = "lead_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    note_type = Column(String(50), nullable=False, default="internal")
    content = Column(Text, nullable=False)
    structured_data = Column(JSONB, default={})
    visibility = Column(String(50), nullable=False, default="all")
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "note_type IN ('handoff', 'post_call', 'internal', 'follow_up')",
            name="lead_notes_type_check",
        ),
        CheckConstraint(
            "visibility IN ('setter_closer', 'all', 'private')",
            name="lead_notes_visibility_check",
        ),
        Index("idx_lead_notes_lead", "lead_id", created_at.desc()),
        Index("idx_lead_notes_tenant", "tenant_id", created_at.desc()),
        Index("idx_lead_notes_author", "author_id"),
        Index("idx_lead_notes_type", "tenant_id", "note_type"),
    )


class LeadTag(Base):
    __tablename__ = "lead_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(7), nullable=False, default="#6B7280")
    icon = Column(String(50))
    category = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="lead_tags_tenant_name_unique"),
        Index("idx_lead_tags_tenant", "tenant_id", "is_active"),
    )


# ============================================================
# META EMBEDDED SIGNUP — BUSINESS ASSETS & CHANNEL BINDINGS
# ============================================================

class BusinessAsset(Base):
    """Discovered Meta assets (Facebook Pages, Instagram accounts, WABAs, phone numbers)."""
    __tablename__ = "business_assets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)        # facebook, instagram, whatsapp
    asset_type = Column(String(50), nullable=False)       # page, instagram_account, waba, phone_number
    asset_id = Column(String(255), nullable=False)
    asset_name = Column(Text)
    parent_asset_id = Column(String(255))                 # e.g. page_id for instagram, waba_id for phone
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "platform", "asset_id", name="business_assets_tenant_platform_asset_unique"),
        Index("idx_business_assets_tenant", "tenant_id", "platform"),
    )


class ChannelBinding(Base):
    """Activated channel bindings — which assets are actively used for messaging."""
    __tablename__ = "channel_bindings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(50), nullable=False)          # whatsapp, instagram, facebook
    asset_id = Column(String(255), nullable=False)
    asset_name = Column(Text)
    config = Column(JSONB, default={})
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "channel", "asset_id", name="channel_bindings_tenant_channel_asset_unique"),
        Index("idx_channel_bindings_tenant_active", "tenant_id", "active"),
    )
