import json
import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import TaskModel, ProcessedEmailModel, IngestionRunModel
from app.db.mongo import get_motor_db, is_mongo_active
from app.config import settings, normalize_email
from app.services.rules import ALLOWED_ASSIGNEES, ALLOWED_CATEGORIES, ALLOWED_PRIORITIES

router = APIRouter(tags=["Intelligence & Operations (Section Advanced)"])

@router.get("/api/runs")
@router.get("/runs")
async def get_ingestion_runs(
    candidate_id: str = Query(..., description="Mandatory candidate email"),
    db: Session = Depends(get_db)
):
    """Retrieve run history logs scoped by candidate_id."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        runs = await mongo_db.ingestion_runs.find({"candidate_id": norm_cand_id}, {"_id": 0}).sort("processed_at", -1).to_list(length=100)
        return runs
    else:
        runs = db.query(IngestionRunModel).filter(IngestionRunModel.candidate_id == norm_cand_id).order_by(IngestionRunModel.processed_at.desc()).all()
        return [
            {
                "run_id": r.run_id,
                "candidate_id": r.candidate_id,
                "processed_at": r.processed_at,
                "processed_count": r.processed_count,
                "tasks_created": r.tasks_created,
                "tasks_updated": r.tasks_updated,
                "emails_skipped": r.emails_skipped,
                "triage_count": r.triage_count,
                "spurious_count": r.spurious_count,
                "errors_count": r.errors_count
            }
            for r in runs
        ]

@router.get("/api/runs/{run_id}")
@router.get("/runs/{run_id}")
async def get_run_details(
    run_id: str,
    candidate_id: str = Query(..., description="Candidate email"),
    db: Session = Depends(get_db)
):
    """Retrieve details and item list of a specific run."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        run = await mongo_db.ingestion_runs.find_one({"candidate_id": norm_cand_id, "run_id": run_id}, {"_id": 0})
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        items = await mongo_db.processed_emails.find({"candidate_id": norm_cand_id, "run_id": run_id}, {"_id": 0}).to_list(length=1000)
        return {"run": run, "items": items}
    else:
        run = db.query(IngestionRunModel).filter(IngestionRunModel.candidate_id == norm_cand_id, IngestionRunModel.run_id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        items = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id, ProcessedEmailModel.run_id == run_id).all()
        
        parsed_items = []
        for i in items:
            signals_data = []
            rules_data = []
            if i.signals:
                try:
                    signals_data = json.loads(i.signals)
                except Exception:
                    signals_data = [i.signals]
            if i.rules_triggered:
                try:
                    rules_data = json.loads(i.rules_triggered)
                except Exception:
                    rules_data = [i.rules_triggered]

            parsed_items.append({
                "email_id": i.email_id,
                "candidate_id": i.candidate_id,
                "thread_id": i.thread_id,
                "message_index": i.message_index,
                "from_name": i.from_name,
                "from_email": i.from_email,
                "subject": i.subject,
                "received_at": i.received_at,
                "status": i.status,
                "category": i.category,
                "confidence": i.confidence,
                "reasoning": i.reasoning,
                "task_id": i.task_id,
                "direction": i.direction or "inbound",
                "intent": i.intent or i.category or "ambiguous",
                "signals": signals_data,
                "rules_triggered": rules_data,
                "run_id": i.run_id,
                "needs_review": i.needs_review,
                "review_status": i.review_status
            })

        return {
            "run": {
                "run_id": run.run_id,
                "candidate_id": run.candidate_id,
                "processed_at": run.processed_at,
                "processed_count": run.processed_count,
                "tasks_created": run.tasks_created,
                "tasks_updated": run.tasks_updated,
                "emails_skipped": run.emails_skipped,
                "triage_count": run.triage_count,
                "spurious_count": run.spurious_count,
                "errors_count": run.errors_count
            },
            "items": parsed_items
        }

@router.get("/api/triage")
@router.get("/triage")
async def get_triage_queue(
    candidate_id: str = Query(..., description="Mandatory candidate email"),
    db: Session = Depends(get_db)
):
    """Retrieve items requiring human review/triage."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        # Fetch low confidence, ambiguous, or incomplete items needing review
        items = await mongo_db.processed_emails.find(
            {
                "candidate_id": norm_cand_id,
                "$or": [
                    {"needs_review": True},
                    {"review_status": "needs_review"},
                    {"status": "triage"},
                    {"category": "triage"}
                ]
            },
            {"_id": 0}
        ).sort("processed_at", -1).to_list(length=500)
        return items
    else:
        items = db.query(ProcessedEmailModel).filter(
            ProcessedEmailModel.candidate_id == norm_cand_id
        ).filter(
            (ProcessedEmailModel.needs_review == True) | 
            (ProcessedEmailModel.review_status == "needs_review") | 
            (ProcessedEmailModel.status == "triage") | 
            (ProcessedEmailModel.category == "triage")
        ).order_by(ProcessedEmailModel.processed_at.desc()).all()
        
        parsed_items = []
        for i in items:
            signals_data = []
            rules_data = []
            if i.signals:
                try: signals_data = json.loads(i.signals)
                except Exception: signals_data = [i.signals]
            if i.rules_triggered:
                try: rules_data = json.loads(i.rules_triggered)
                except Exception: rules_data = [i.rules_triggered]

            parsed_items.append({
                "email_id": i.email_id,
                "candidate_id": i.candidate_id,
                "thread_id": i.thread_id,
                "message_index": i.message_index,
                "from_name": i.from_name,
                "from_email": i.from_email,
                "subject": i.subject,
                "received_at": i.received_at,
                "status": i.status,
                "category": i.category,
                "confidence": i.confidence,
                "reasoning": i.reasoning,
                "task_id": i.task_id,
                "direction": i.direction or "inbound",
                "intent": i.intent or i.category or "ambiguous",
                "signals": signals_data,
                "rules_triggered": rules_data,
                "run_id": i.run_id,
                "needs_review": i.needs_review,
                "review_status": i.review_status
            })
        return parsed_items

class ReviewDecisionSchema(BaseModel):
    assignee_id: str
    category: str
    priority: str
    notes: Optional[str] = None

@router.post("/api/triage/{email_id}/review")
@router.post("/triage/{email_id}/review")
async def submit_human_review(
    email_id: str,
    payload: ReviewDecisionSchema,
    candidate_id: str = Query(..., description="Mandatory candidate email"),
    db: Session = Depends(get_db)
):
    """Update routing decision (assignee, category, priority) based on human review."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if payload.assignee_id not in ALLOWED_ASSIGNEES:
        raise HTTPException(status_code=400, detail=f"Invalid assignee_id: {payload.assignee_id}")
    if payload.category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {payload.category}")
    if payload.priority not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {payload.priority}")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if mongo_db is not None:
        email = await mongo_db.processed_emails.find_one({"candidate_id": norm_cand_id, "email_id": email_id})
        if not email:
            raise HTTPException(status_code=404, detail="Email record not found")
        
        task_id = email.get("task_id")
        
        # 1. Update processed email review status
        await mongo_db.processed_emails.update_one(
            {"candidate_id": norm_cand_id, "email_id": email_id},
            {
                "$set": {
                    "review_status": "reviewed",
                    "needs_review": False,
                    "review_notes": payload.notes,
                    "category": payload.category
                }
            }
        )

        # 2. Update task details or create task if it was skipped (or was triage)
        if task_id:
            await mongo_db.tasks.update_one(
                {"candidate_id": norm_cand_id, "task_id": task_id},
                {
                    "$set": {
                        "assignee_id": payload.assignee_id,
                        "category": payload.category,
                        "priority": payload.priority,
                        "needs_review": False,
                        "review_status": "completed",
                        "review_notes": payload.notes,
                        "updated_at": now_iso
                    }
                }
            )
        else:
            # Create a task since the human reviewed and promoted it!
            new_task_id = f"tsk_{email_id[3:] if email_id.startswith('em_') else email_id}"
            task_doc = {
                "task_id": new_task_id,
                "candidate_id": norm_cand_id,
                "source_email_id": email_id,
                "thread_id": email.get("thread_id"),
                "title": email.get("subject") or "Reviewed Task Request",
                "description": email.get("reasoning") or "Reviewed by Sales Ops",
                "assignee_id": payload.assignee_id,
                "category": payload.category,
                "priority": payload.priority,
                "due_date": None,
                "deal_value_inr": None,
                "company_name": None,
                "confidence": 1.0,
                "created_at": now_iso,
                "updated_at": now_iso,
                "direction": email.get("direction", "inbound"),
                "intent": email.get("intent", payload.category),
                "signals": ["Manually approved by human operator"],
                "rules_triggered": ["human_override"],
                "run_id": email.get("run_id"),
                "needs_review": False,
                "review_status": "completed",
                "review_notes": payload.notes
            }
            await mongo_db.tasks.insert_one(task_doc)
            await mongo_db.processed_emails.update_one(
                {"candidate_id": norm_cand_id, "email_id": email_id},
                {"$set": {"task_id": new_task_id, "status": "created_task"}}
            )

        return {"status": "success", "message": f"Review completed for email {email_id}."}
    else:
        email = db.query(ProcessedEmailModel).filter(
            ProcessedEmailModel.candidate_id == norm_cand_id,
            ProcessedEmailModel.email_id == email_id
        ).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email record not found")
        
        email.review_status = "reviewed"
        email.needs_review = False
        email.review_notes = payload.notes
        email.category = payload.category

        if email.task_id:
            task = db.query(TaskModel).filter(
                TaskModel.candidate_id == norm_cand_id,
                TaskModel.task_id == email.task_id
            ).first()
            if task:
                task.assignee_id = payload.assignee_id
                task.category = payload.category
                task.priority = payload.priority
                task.needs_review = False
                task.review_status = "completed"
                task.review_notes = payload.notes
                task.updated_at = now_iso
        else:
            new_task_id = f"tsk_{email_id[3:] if email_id.startswith('em_') else email_id}"
            import json
            task = TaskModel(
                task_id=new_task_id,
                candidate_id=norm_cand_id,
                source_email_id=email_id,
                thread_id=email.thread_id,
                title=email.subject or "Reviewed Task Request",
                description=email.reasoning or "Reviewed by Sales Ops",
                assignee_id=payload.assignee_id,
                category=payload.category,
                priority=payload.priority,
                due_date=None,
                deal_value_inr=None,
                company_name=None,
                confidence=1.0,
                created_at=now_iso,
                updated_at=now_iso,
                direction=email.direction or "inbound",
                intent=email.intent or payload.category,
                signals=json.dumps(["Manually approved by human operator"]),
                rules_triggered=json.dumps(["human_override"]),
                run_id=email.run_id,
                needs_review=False,
                review_status="completed",
                review_notes=payload.notes
            )
            db.add(task)
            email.task_id = new_task_id
            email.status = "created_task"

        try:
            db.commit()
            return {"status": "success", "message": f"Review completed for email {email_id}."}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/thread-timeline/{thread_id}")
@router.get("/thread-timeline/{thread_id}")
async def get_thread_timeline(
    thread_id: str,
    candidate_id: str = Query(..., description="Mandatory candidate email"),
    db: Session = Depends(get_db)
):
    """Retrieve full chronological interaction timeline and changes for a thread."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        emails = await mongo_db.processed_emails.find({"candidate_id": norm_cand_id, "thread_id": thread_id}, {"_id": 0}).sort("received_at", 1).to_list(length=100)
        return emails
    else:
        emails = db.query(ProcessedEmailModel).filter(
            ProcessedEmailModel.candidate_id == norm_cand_id,
            ProcessedEmailModel.thread_id == thread_id
        ).order_by(ProcessedEmailModel.received_at.asc()).all()
        
        parsed = []
        for i in emails:
            signals_data = []
            rules_data = []
            if i.signals:
                try: signals_data = json.loads(i.signals)
                except Exception: signals_data = [i.signals]
            if i.rules_triggered:
                try: rules_data = json.loads(i.rules_triggered)
                except Exception: rules_data = [i.rules_triggered]
                
            parsed.append({
                "email_id": i.email_id,
                "thread_id": i.thread_id,
                "from_name": i.from_name,
                "from_email": i.from_email,
                "subject": i.subject,
                "received_at": i.received_at,
                "is_reply": i.is_reply,
                "status": i.status,
                "category": i.category,
                "confidence": i.confidence,
                "reasoning": i.reasoning,
                "task_id": i.task_id,
                "direction": i.direction or "inbound",
                "intent": i.intent or i.category or "ambiguous",
                "signals": signals_data,
                "rules_triggered": rules_data,
                "run_id": i.run_id,
                "needs_review": i.needs_review,
                "review_status": i.review_status
            })
        return parsed

@router.get("/api/decision-center")
@router.get("/decision-center")
async def get_decision_center(
    candidate_id: str = Query(..., description="Mandatory candidate email"),
    db: Session = Depends(get_db)
):
    """Retrieve decision trace statistics and recent audit list scoped by candidate_id."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        total_decisions = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id})
        
        high_conf = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "confidence": {"$gte": 0.85}})
        med_conf = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "confidence": {"$gte": 0.65, "$lt": 0.85}})
        low_conf = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "confidence": {"$lt": 0.65}})
        
        created = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "created_task"})
        updated = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "updated_task"})
        
        skipped_spam = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "skipped_spam"})
        skipped_ooo = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "skipped_ooo"})
        skipped_news = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "skipped_newsletter"})
        skipped = skipped_spam + skipped_ooo + skipped_news
        
        triage = await mongo_db.processed_emails.count_documents({
            "candidate_id": norm_cand_id,
            "$or": [{"status": "triage"}, {"category": "triage"}]
        })
        
        # Calculate spurious metrics
        spurious_count = await mongo_db.tasks.count_documents({
            "candidate_id": norm_cand_id,
            "$or": [{"confidence": {"$lt": 0.70}}, {"category": "triage"}]
        })
        spurious_rate = round(spurious_count / created, 4) if created > 0 else 0.0
        
        avg_cursor = mongo_db.processed_emails.aggregate([
            {"$match": {"candidate_id": norm_cand_id}},
            {"$group": {"_id": None, "avg_conf": {"$avg": "$confidence"}}}
        ])
        avg_res = await avg_cursor.to_list(length=1)
        avg_confidence = round(avg_res[0]["avg_conf"], 2) if avg_res else 1.0

        recent_decisions = await mongo_db.processed_emails.find({"candidate_id": norm_cand_id}, {"_id": 0}).sort("processed_at", -1).limit(50).to_list(length=50)

        return {
            "stats": {
                "total_decisions": total_decisions,
                "high_confidence": high_conf,
                "medium_confidence": med_conf,
                "low_confidence": low_conf,
                "tasks_created": created,
                "tasks_updated": updated,
                "emails_skipped": skipped,
                "triage": triage,
                "avg_confidence": avg_confidence,
                "spurious_rate": spurious_rate
            },
            "recent_decisions": recent_decisions
        }
    else:
        emails = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id).all()
        created_tasks = db.query(TaskModel).filter(TaskModel.candidate_id == norm_cand_id).all()

        total_decisions = len(emails)
        high_conf = sum(1 for i in emails if i.confidence >= 0.85)
        med_conf = sum(1 for i in emails if 0.65 <= i.confidence < 0.85)
        low_conf = sum(1 for i in emails if i.confidence < 0.65)
        
        created = sum(1 for i in emails if i.status == "created_task")
        updated = sum(1 for i in emails if i.status == "updated_task")
        skipped = sum(1 for i in emails if i.status.startswith("skipped_"))
        triage = sum(1 for i in emails if i.status == "triage" or i.category == "triage")
        
        # Spurious rate
        spurious_count = sum(1 for t in created_tasks if t.confidence < 0.70 or t.category == "triage")
        spurious_rate = round(spurious_count / len(created_tasks), 4) if len(created_tasks) > 0 else 0.0
        
        avg_confidence = round(sum(i.confidence for i in emails) / len(emails), 2) if emails else 1.0

        recent = db.query(ProcessedEmailModel).filter(
            ProcessedEmailModel.candidate_id == norm_cand_id
        ).order_by(ProcessedEmailModel.processed_at.desc()).limit(50).all()

        parsed_recent = []
        for i in recent:
            signals_data = []
            rules_data = []
            if i.signals:
                try: signals_data = json.loads(i.signals)
                except Exception: signals_data = [i.signals]
            if i.rules_triggered:
                try: rules_data = json.loads(i.rules_triggered)
                except Exception: rules_data = [i.rules_triggered]

            parsed_recent.append({
                "email_id": i.email_id,
                "candidate_id": i.candidate_id,
                "thread_id": i.thread_id,
                "message_index": i.message_index,
                "from_name": i.from_name,
                "from_email": i.from_email,
                "subject": i.subject,
                "received_at": i.received_at,
                "status": i.status,
                "category": i.category,
                "confidence": i.confidence,
                "reasoning": i.reasoning,
                "task_id": i.task_id,
                "direction": i.direction or "inbound",
                "intent": i.intent or i.category or "ambiguous",
                "signals": signals_data,
                "rules_triggered": rules_data,
                "run_id": i.run_id,
                "needs_review": i.needs_review,
                "review_status": i.review_status
            })

        return {
            "stats": {
                "total_decisions": total_decisions,
                "high_confidence": high_conf,
                "medium_confidence": med_conf,
                "low_confidence": low_conf,
                "tasks_created": created,
                "tasks_updated": updated,
                "emails_skipped": skipped,
                "triage": triage,
                "avg_confidence": avg_confidence,
                "spurious_rate": spurious_rate
            },
            "recent_decisions": parsed_recent
        }
