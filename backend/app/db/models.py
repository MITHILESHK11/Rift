import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Float, Text, Boolean, DateTime
from app.db.database import Base

class TaskModel(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, index=True, nullable=False)
    source_email_id = Column(String, unique=True, index=True, nullable=False)
    thread_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(String, nullable=False)
    category = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    due_date = Column(String, nullable=True)
    deal_value_inr = Column(BigInteger, nullable=True)
    company_name = Column(String, nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    # Advanced Operations Fields
    direction = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    signals = Column(Text, nullable=True)
    rules_triggered = Column(Text, nullable=True)
    run_id = Column(String, index=True, nullable=True)
    needs_review = Column(Boolean, default=False, index=True)
    review_status = Column(String, default="completed", index=True)
    review_notes = Column(Text, nullable=True)

class ProcessedEmailModel(Base):
    __tablename__ = "processed_emails"

    email_id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, index=True, nullable=True)
    thread_id = Column(String, index=True, nullable=False)
    message_index = Column(Integer, default=0)
    from_name = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    received_at = Column(String, nullable=True)
    is_reply = Column(Boolean, default=False)
    status = Column(String, nullable=False)  # created_task, updated_task, skipped_spam, skipped_newsletter, skipped_ooo, triage
    category = Column(String, nullable=True)
    confidence = Column(Float, default=1.0)
    skip_reason = Column(String, nullable=True)
    reasoning = Column(Text, nullable=True)
    task_id = Column(String, nullable=True)
    processed_at = Column(String, nullable=False)

    # Advanced Operations Fields
    direction = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    signals = Column(Text, nullable=True)
    rules_triggered = Column(Text, nullable=True)
    run_id = Column(String, index=True, nullable=True)
    needs_review = Column(Boolean, default=False, index=True)
    review_status = Column(String, default="completed", index=True)
    review_notes = Column(Text, nullable=True)

class ThreadMapModel(Base):
    __tablename__ = "thread_map"

    thread_id = Column(String, primary_key=True, index=True)
    task_id = Column(String, nullable=False)
    update_count = Column(Integer, default=1)
    last_updated_at = Column(String, nullable=False)

class IngestionRunModel(Base):
    __tablename__ = "ingestion_runs"

    run_id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, index=True, nullable=False)
    processed_at = Column(String, nullable=False)
    processed_count = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    tasks_updated = Column(Integer, default=0)
    emails_skipped = Column(Integer, default=0)
    triage_count = Column(Integer, default=0)
    spurious_count = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
