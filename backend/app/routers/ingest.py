import uuid
import datetime
import asyncio
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import TaskModel, ProcessedEmailModel, ThreadMapModel
from app.db.mongo import get_motor_db, is_mongo_active
from app.config import settings, normalize_email
from app.services.gemini_service import classify_emails_concurrently, extract_with_gemini_async
from app.services.rules import strip_quoted_text

router = APIRouter(tags=["Ingest API & Real Email Reader (Section 7.1)"])

class EmailInputSchema(BaseModel):
    email_id: Optional[str] = None
    thread_id: Optional[str] = None
    message_index: int = 0
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    to: Optional[str] = "sales@company.com"
    cc: Optional[List[str]] = None
    subject: Optional[str] = ""
    body: Optional[str] = ""
    received_at: Optional[str] = None
    attachments: Optional[List[str]] = None
    is_reply: bool = False

class SingleEmailComposeSchema(BaseModel):
    candidate_id: Optional[str] = None
    from_name: str
    from_email: str
    subject: str
    body: str
    received_at: Optional[str] = None
    thread_id: Optional[str] = None

class IngestPayloadSchema(BaseModel):
    candidate_id: Optional[str] = "evaluator.test@gmail.com"
    emails: List[EmailInputSchema]

@router.post("/ingest")
@router.post("/api/ingest")
async def ingest_emails(payload: Union[IngestPayloadSchema, List[EmailInputSchema]], db: Session = Depends(get_db)):
    """Section 7.1: Fast async batch email ingest processor supporting Object payloads, raw Email Arrays, Motor MongoDB & SQL."""
    if isinstance(payload, list):
        candidate_id = settings.CANDIDATE_ID or "evaluator.test@gmail.com"
        email_items = payload
    else:
        candidate_id = payload.candidate_id or settings.CANDIDATE_ID or "evaluator.test@gmail.com"
        email_items = payload.emails

    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None
    
    tasks_created = 0
    tasks_updated = 0
    skipped = 0
    errors = []

    # Step 1: Pre-process emails list and assign email_id / thread_id
    prepared_emails = []
    for item in email_items:
        data = item.model_dump() if hasattr(item, "model_dump") else (item.dict() if hasattr(item, "dict") else dict(item))
        email_id = data.get("email_id") or f"em_{uuid.uuid4().hex[:6]}"
        thread_id = data.get("thread_id") or f"th_{uuid.uuid4().hex[:6]}"
        data["email_id"] = email_id
        data["thread_id"] = thread_id
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not data.get("received_at"):
            data["received_at"] = now_iso
        prepared_emails.append(data)

    # Step 2: Concurrent Gemini extraction for the payload
    extractions = await classify_emails_concurrently(prepared_emails, concurrency_limit=10)

    # Step 3: Process items against database
    for idx, email_data in enumerate(prepared_emails):
        extraction = extractions[idx]
        email_id = email_data["email_id"]
        thread_id = email_data["thread_id"]
        is_reply = email_data.get("is_reply", False)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if mongo_db is not None:
            # MongoDB Motor Processing Path
            existing_proc = await mongo_db.processed_emails.find_one({"candidate_id": norm_cand_id, "email_id": email_id})
            existing_task = await mongo_db.tasks.find_one({"candidate_id": norm_cand_id, "source_email_id": email_id})

            if existing_proc or existing_task:
                skipped += 1
                continue

            existing_thread = await mongo_db.thread_map.find_one({"candidate_id": norm_cand_id, "thread_id": thread_id})
            
            if existing_thread or is_reply:
                target_task_id = existing_thread.get("task_id") if existing_thread else None
                if not target_task_id:
                    task_doc = await mongo_db.tasks.find_one({"candidate_id": norm_cand_id, "thread_id": thread_id})
                    if task_doc:
                        target_task_id = task_doc.get("task_id")

                if target_task_id:
                    update_fields = {"updated_at": now_iso}
                    if extraction.get("priority"):
                        update_fields["priority"] = extraction["priority"]
                    if extraction.get("due_date"):
                        update_fields["due_date"] = extraction["due_date"]
                    if extraction.get("deal_value_inr") is not None:
                        update_fields["deal_value_inr"] = extraction["deal_value_inr"]

                    await mongo_db.tasks.update_one({"candidate_id": norm_cand_id, "task_id": target_task_id}, {"$set": update_fields})
                    if existing_thread:
                        await mongo_db.thread_map.update_one({"candidate_id": norm_cand_id, "thread_id": thread_id}, {"$inc": {"update_count": 1}, "$set": {"last_updated_at": now_iso}})

                    proc_doc = {
                        "candidate_id": norm_cand_id,
                        "email_id": email_id,
                        "thread_id": thread_id,
                        "message_index": email_data.get("message_index", 0),
                        "from_name": email_data.get("from_name"),
                        "from_email": email_data.get("from_email"),
                        "subject": email_data.get("subject"),
                        "received_at": email_data.get("received_at"),
                        "is_reply": True,
                        "status": "updated_task",
                        "task_id": target_task_id,
                        "reasoning": "Thread reply update applied to existing task.",
                        "processed_at": now_iso
                    }
                    await mongo_db.processed_emails.insert_one(proc_doc)
                    tasks_updated += 1
                    continue

            if not extraction.get("should_create_task", True):
                skip_reason = extraction.get("skip_reason", "skipped_spam")
                proc_doc = {
                    "candidate_id": norm_cand_id,
                    "email_id": email_id,
                    "thread_id": thread_id,
                    "message_index": email_data.get("message_index", 0),
                    "from_name": email_data.get("from_name"),
                    "from_email": email_data.get("from_email"),
                    "subject": email_data.get("subject"),
                    "received_at": email_data.get("received_at"),
                    "is_reply": is_reply,
                    "status": skip_reason,
                    "skip_reason": skip_reason,
                    "reasoning": extraction.get("reasoning"),
                    "processed_at": now_iso
                }
                await mongo_db.processed_emails.insert_one(proc_doc)
                skipped += 1
                continue

            # Create Task in Mongo
            task_id = f"tsk_{uuid.uuid4().hex[:8]}"
            task_doc = {
                "task_id": task_id,
                "candidate_id": norm_cand_id,
                "source_email_id": email_id,
                "thread_id": thread_id,
                "title": extraction.get("title") or f"{email_data.get('subject') or 'New Email Request'}",
                "description": extraction.get("description") or (email_data.get("body") or "")[:200],
                "assignee_id": extraction.get("assignee_id", "u_triage"),
                "category": extraction.get("category", "triage"),
                "priority": extraction.get("priority", "medium"),
                "due_date": extraction.get("due_date"),
                "deal_value_inr": extraction.get("deal_value_inr"),
                "company_name": extraction.get("company_name"),
                "confidence": extraction.get("confidence", 0.90),
                "created_at": now_iso,
                "updated_at": now_iso
            }
            await mongo_db.tasks.insert_one(task_doc)

            thread_doc = {
                "candidate_id": norm_cand_id,
                "thread_id": thread_id,
                "task_id": task_id,
                "update_count": 1,
                "last_updated_at": now_iso
            }
            await mongo_db.thread_map.update_one({"candidate_id": norm_cand_id, "thread_id": thread_id}, {"$set": thread_doc}, upsert=True)

            proc_doc = {
                "candidate_id": norm_cand_id,
                "email_id": email_id,
                "thread_id": thread_id,
                "message_index": email_data.get("message_index", 0),
                "from_name": email_data.get("from_name"),
                "from_email": email_data.get("from_email"),
                "subject": email_data.get("subject"),
                "received_at": email_data.get("received_at"),
                "is_reply": is_reply,
                "status": "created_task",
                "category": task_doc["category"],
                "confidence": task_doc["confidence"],
                "task_id": task_id,
                "reasoning": extraction.get("reasoning"),
                "processed_at": now_iso
            }
            await mongo_db.processed_emails.insert_one(proc_doc)
            tasks_created += 1

        else:
            # SQL Fallback Processing Path
            existing_proc = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.email_id == email_id).first()
            existing_task = db.query(TaskModel).filter(TaskModel.source_email_id == email_id).first()
            
            if existing_proc or existing_task:
                skipped += 1
                continue

            existing_thread_map = db.query(ThreadMapModel).filter(ThreadMapModel.thread_id == thread_id).first()
            
            if existing_thread_map or is_reply:
                target_task_id = existing_thread_map.task_id if existing_thread_map else None
                if not target_task_id:
                    task_obj = db.query(TaskModel).filter(TaskModel.thread_id == thread_id).first()
                    if task_obj:
                        target_task_id = task_obj.task_id

                if target_task_id:
                    task = db.query(TaskModel).filter(TaskModel.task_id == target_task_id).first()
                    if task:
                        if extraction.get("priority"):
                            task.priority = extraction["priority"]
                        if extraction.get("due_date"):
                            task.due_date = extraction["due_date"]
                        if extraction.get("deal_value_inr") is not None:
                            task.deal_value_inr = extraction["deal_value_inr"]
                        task.updated_at = now_iso
                        
                        if existing_thread_map:
                            existing_thread_map.update_count += 1
                            existing_thread_map.last_updated_at = now_iso
                        
                        proc_log = ProcessedEmailModel(
                            email_id=email_id,
                            thread_id=thread_id,
                            message_index=email_data.get("message_index", 0),
                            from_name=email_data.get("from_name"),
                            from_email=email_data.get("from_email"),
                            subject=email_data.get("subject"),
                            received_at=email_data.get("received_at"),
                            is_reply=True,
                            status="updated_task",
                            category=task.category,
                            confidence=extraction.get("confidence", 0.9),
                            task_id=task.task_id,
                            reasoning="Thread reply update applied to existing task.",
                            processed_at=now_iso
                        )
                        db.add(proc_log)
                        try:
                            db.commit()
                            tasks_updated += 1
                        except Exception as e:
                            db.rollback()
                            errors.append(str(e))
                        continue

            if not extraction.get("should_create_task", True):
                skip_reason = extraction.get("skip_reason", "skipped_spam")
                proc_log = ProcessedEmailModel(
                    email_id=email_id,
                    thread_id=thread_id,
                    message_index=email_data.get("message_index", 0),
                    from_name=email_data.get("from_name"),
                    from_email=email_data.get("from_email"),
                    subject=email_data.get("subject"),
                    received_at=email_data.get("received_at"),
                    is_reply=is_reply,
                    status=skip_reason,
                    category=None,
                    confidence=extraction.get("confidence", 0.99),
                    skip_reason=skip_reason,
                    reasoning=extraction.get("reasoning"),
                    processed_at=now_iso
                )
                db.add(proc_log)
                try:
                    db.commit()
                    skipped += 1
                except Exception as e:
                    db.rollback()
                    errors.append(str(e))
                continue

            task_id = f"tsk_{uuid.uuid4().hex[:8]}"
            db_task = TaskModel(
                task_id=task_id,
                candidate_id=norm_cand_id,
                source_email_id=email_id,
                thread_id=thread_id,
                title=extraction.get("title") or f"{email_data.get('subject') or 'New Email Request'}",
                description=extraction.get("description") or (email_data.get("body") or "")[:200],
                assignee_id=extraction.get("assignee_id", "u_triage"),
                category=extraction.get("category", "triage"),
                priority=extraction.get("priority", "medium"),
                due_date=extraction.get("due_date"),
                deal_value_inr=extraction.get("deal_value_inr"),
                company_name=extraction.get("company_name"),
                confidence=extraction.get("confidence", 0.90),
                created_at=now_iso,
                updated_at=now_iso
            )
            db.add(db_task)

            if existing_thread_map:
                existing_thread_map.task_id = task_id
                existing_thread_map.last_updated_at = now_iso
            else:
                db_thread = ThreadMapModel(
                    thread_id=thread_id,
                    task_id=task_id,
                    update_count=1,
                    last_updated_at=now_iso
                )
                db.add(db_thread)

            proc_log = ProcessedEmailModel(
                email_id=email_id,
                thread_id=thread_id,
                message_index=email_data.get("message_index", 0),
                from_name=email_data.get("from_name"),
                from_email=email_data.get("from_email"),
                subject=email_data.get("subject"),
                received_at=email_data.get("received_at"),
                is_reply=is_reply,
                status="created_task",
                category=db_task.category,
                confidence=db_task.confidence,
                task_id=task_id,
                reasoning=extraction.get("reasoning"),
                processed_at=now_iso
            )
            db.add(proc_log)
            try:
                db.commit()
                tasks_created += 1
            except Exception as e:
                db.rollback()
                errors.append(str(e))

    return {
        "processed": len(prepared_emails),
        "tasks_created": tasks_created,
        "tasks_updated": tasks_updated,
        "skipped": skipped,
        "errors": errors
    }

@router.post("/api/ingest-single")
@router.post("/ingest-single")
async def ingest_single_email(payload: SingleEmailComposeSchema, db: Session = Depends(get_db)):
    """Real Email Reader endpoint: Reads a single real email composed or pasted by an evaluator."""
    cand_id = normalize_email(payload.candidate_id or settings.CANDIDATE_ID)
    email_id = f"em_{uuid.uuid4().hex[:6]}"
    thread_id = payload.thread_id or f"th_{uuid.uuid4().hex[:6]}"
    received_at = payload.received_at or datetime.datetime.now(datetime.timezone.utc).isoformat()

    email_item = EmailInputSchema(
        email_id=email_id,
        thread_id=thread_id,
        from_name=payload.from_name,
        from_email=payload.from_email,
        subject=payload.subject,
        body=payload.body,
        received_at=received_at
    )

    batch_payload = IngestPayloadSchema(
        candidate_id=cand_id,
        emails=[email_item]
    )

    res = await ingest_emails(batch_payload, db=db)
    
    mongo_db = get_motor_db() if is_mongo_active() else None
    if mongo_db is not None:
        proc_log = await mongo_db.processed_emails.find_one({"candidate_id": cand_id, "email_id": email_id})
        task = await mongo_db.tasks.find_one({"candidate_id": cand_id, "source_email_id": email_id})
        action = proc_log.get("status") if proc_log else "unknown"
        task_data = task if task else None
    else:
        proc_log = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.email_id == email_id).first()
        task = db.query(TaskModel).filter(TaskModel.source_email_id == email_id).first()
        action = proc_log.status if proc_log else "unknown"
        task_data = {
            "task_id": task.task_id,
            "candidate_id": task.candidate_id,
            "assignee_id": task.assignee_id,
            "category": task.category,
            "priority": task.priority,
            "due_date": task.due_date,
            "deal_value_inr": task.deal_value_inr,
            "company_name": task.company_name,
            "confidence": task.confidence
        } if task else None

    return {
        "summary": res,
        "email_id": email_id,
        "thread_id": thread_id,
        "action": action,
        "task": task_data,
        "reasoning": proc_log.get("reasoning") if mongo_db else (proc_log.reasoning if proc_log else None)
    }
