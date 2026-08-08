from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any

from app.db.database import get_db
from app.db.models import TaskModel, ProcessedEmailModel, ThreadMapModel
from app.db.mongo import get_motor_db, is_mongo_active
from app.config import settings, normalize_email

router = APIRouter(tags=["Frontend Wrappers & Stats (Section 7.2)"])

@router.get("/api/tasks")
@router.get("/tasks")
async def get_frontend_tasks(
    candidate_id: str = Query(..., description="Candidate email"),
    db: Session = Depends(get_db)
):
    """Section 7.2: Returns tasks joined with audit log data strictly scoped to candidate_id."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        tasks = await mongo_db.tasks.find({"candidate_id": norm_cand_id}, {"_id": 0}).to_list(length=1000)
        logs = await mongo_db.processed_emails.find({"candidate_id": norm_cand_id}, {"_id": 0}).to_list(length=1000)
        log_map = {log.get("task_id"): log for log in logs if log.get("task_id")}
        skipped_logs = [log for log in logs if str(log.get("status", "")).startswith("skipped_")]

        result_tasks = []
        for t in tasks:
            log = log_map.get(t.get("task_id"))
            t_copy = dict(t)
            t_copy["status"] = "active_task"
            t_copy["reasoning"] = log.get("reasoning") if log else None
            result_tasks.append(t_copy)

        return {
            "candidate_id": norm_cand_id,
            "tasks": result_tasks,
            "skipped_emails": skipped_logs
        }
    else:
        tasks = db.query(TaskModel).filter(TaskModel.candidate_id == norm_cand_id).all()
        processed_logs = db.query(ProcessedEmailModel).all()

        log_map = {log.task_id: log for log in processed_logs if log.task_id}
        skipped_logs = [log for log in processed_logs if log.status.startswith("skipped_")]

        result_tasks = []
        for t in tasks:
            log = log_map.get(t.task_id)
            result_tasks.append({
                "task_id": t.task_id,
                "candidate_id": t.candidate_id,
                "source_email_id": t.source_email_id,
                "thread_id": t.thread_id,
                "title": t.title,
                "description": t.description,
                "assignee_id": t.assignee_id,
                "category": t.category,
                "priority": t.priority,
                "due_date": t.due_date,
                "deal_value_inr": t.deal_value_inr,
                "company_name": t.company_name,
                "confidence": t.confidence,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "status": "active_task",
                "reasoning": log.reasoning if log else None
            })

        return {
            "candidate_id": norm_cand_id,
            "tasks": result_tasks,
            "skipped_emails": [
                {
                    "email_id": s.email_id,
                    "thread_id": s.thread_id,
                    "from_email": s.from_email,
                    "subject": s.subject,
                    "status": s.status,
                    "skip_reason": s.skip_reason,
                    "reasoning": s.reasoning
                }
                for s in skipped_logs
            ]
        }

@router.get("/api/stats")
@router.get("/stats")
async def get_system_stats(
    candidate_id: Optional[str] = Query(None, description="Optional candidate email to scope metrics"),
    db: Session = Depends(get_db)
):
    """Section 7.2: Serves aggregate counts, category breakdowns, and dynamic spurious rate metrics."""
    norm_cand_id = normalize_email(candidate_id) if candidate_id else None
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        query = {"candidate_id": norm_cand_id} if norm_cand_id else {}
        tasks_created = await mongo_db.tasks.count_documents(query)
        total_processed = await mongo_db.processed_emails.count_documents(query)
        
        skipped_spam = await mongo_db.processed_emails.count_documents({**query, "status": "skipped_spam"})
        skipped_ooo = await mongo_db.processed_emails.count_documents({**query, "status": "skipped_ooo"})
        skipped_newsletter = await mongo_db.processed_emails.count_documents({**query, "status": "skipped_newsletter"})
        total_skipped = skipped_spam + skipped_ooo + skipped_newsletter

        # Aggregation pipelines for distributions
        cat_pipeline = [{"$match": query}, {"$group": {"_id": "$category", "count": {"$sum": 1}}}]
        ass_pipeline = [{"$match": query}, {"$group": {"_id": "$assignee_id", "count": {"$sum": 1}}}]

        cat_results = await mongo_db.tasks.aggregate(cat_pipeline).to_list(length=100)
        ass_results = await mongo_db.tasks.aggregate(ass_pipeline).to_list(length=100)

        cat_dist = {r["_id"]: r["count"] for r in cat_results if r["_id"]}
        ass_dist = {r["_id"]: r["count"] for r in ass_results if r["_id"]}

        spurious_count = await mongo_db.tasks.count_documents({
            **query,
            "$or": [{"confidence": {"$lt": 0.70}}, {"category": "triage"}]
        })
        spurious_rate = round(spurious_count / tasks_created, 4) if tasks_created > 0 else 0.0

        return {
            "candidate_id": norm_cand_id,
            "processed": total_processed,
            "tasks_created": tasks_created,
            "tasks_updated": 0,
            "skipped": total_skipped,
            "skipped_breakdown": {
                "spam": skipped_spam,
                "out_of_office": skipped_ooo,
                "newsletter": skipped_newsletter
            },
            "spurious_count": spurious_count,
            "spurious_rate": spurious_rate,
            "category_distribution": cat_dist,
            "assignee_distribution": ass_dist
        }
    else:
        task_query = db.query(TaskModel)
        if norm_cand_id:
            task_query = task_query.filter(TaskModel.candidate_id == norm_cand_id)

        tasks_created = task_query.count()
        total_processed_q = db.query(func.count(ProcessedEmailModel.email_id))
        spam_q = db.query(func.count(ProcessedEmailModel.email_id)).filter(ProcessedEmailModel.status == "skipped_spam")
        ooo_q = db.query(func.count(ProcessedEmailModel.email_id)).filter(ProcessedEmailModel.status == "skipped_ooo")
        newsletter_q = db.query(func.count(ProcessedEmailModel.email_id)).filter(ProcessedEmailModel.status == "skipped_newsletter")

        if norm_cand_id:
            total_processed_q = total_processed_q.filter(ProcessedEmailModel.candidate_id == norm_cand_id)
            spam_q = spam_q.filter(ProcessedEmailModel.candidate_id == norm_cand_id)
            ooo_q = ooo_q.filter(ProcessedEmailModel.candidate_id == norm_cand_id)
            newsletter_q = newsletter_q.filter(ProcessedEmailModel.candidate_id == norm_cand_id)

        total_processed = total_processed_q.scalar() or 0
        skipped_spam = spam_q.scalar() or 0
        skipped_ooo = ooo_q.scalar() or 0
        skipped_newsletter = newsletter_q.scalar() or 0
        total_skipped = skipped_spam + skipped_ooo + skipped_newsletter

        # SQLite Thread Update Count Scoped (only task maps that were created for tasks of candidate_id)
        tasks_updated_q = db.query(func.count(ThreadMapModel.thread_id)).join(
            TaskModel, TaskModel.task_id == ThreadMapModel.task_id
        ).filter(ThreadMapModel.update_count > 1)
        if norm_cand_id:
            tasks_updated_q = tasks_updated_q.filter(TaskModel.candidate_id == norm_cand_id)
        tasks_updated = tasks_updated_q.scalar() or 0

        cat_query = db.query(TaskModel.category, func.count(TaskModel.task_id))
        if norm_cand_id:
            cat_query = cat_query.filter(TaskModel.candidate_id == norm_cand_id)
        category_counts = cat_query.group_by(TaskModel.category).all()

        ass_query = db.query(TaskModel.assignee_id, func.count(TaskModel.task_id))
        if norm_cand_id:
            ass_query = ass_query.filter(TaskModel.candidate_id == norm_cand_id)
        assignee_counts = ass_query.group_by(TaskModel.assignee_id).all()

        spurious_query = db.query(func.count(TaskModel.task_id)).filter(
            (TaskModel.confidence < 0.70) | (TaskModel.category == "triage")
        )
        if norm_cand_id:
            spurious_query = spurious_query.filter(TaskModel.candidate_id == norm_cand_id)
        spurious_count = spurious_query.scalar() or 0
        spurious_rate = round(spurious_count / tasks_created, 4) if tasks_created > 0 else 0.0

        return {
            "candidate_id": norm_cand_id,
            "processed": total_processed,
            "tasks_created": tasks_created,
            "tasks_updated": tasks_updated,
            "skipped": total_skipped,
            "skipped_breakdown": {
                "spam": skipped_spam,
                "out_of_office": skipped_ooo,
                "newsletter": skipped_newsletter
            },
            "spurious_count": spurious_count,
            "spurious_rate": spurious_rate,
            "category_distribution": dict(category_counts),
            "assignee_distribution": dict(assignee_counts)
        }

@router.get("/api/skipped")
@router.get("/skipped")
async def list_skipped_emails(
    candidate_id: str = Query(..., description="Mandatory candidate_id email"),
    db: Session = Depends(get_db)
):
    """Returns candidate-scoped processed emails that were skipped (Rule 4 spam/ooo/newsletter)."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    skipped_statuses = ["skipped_spam", "skipped_ooo", "skipped_newsletter", "skipped"]

    if mongo_db is not None:
        logs = await mongo_db.processed_emails.find(
            {"candidate_id": norm_cand_id, "status": {"$in": skipped_statuses}},
            {"_id": 0}
        ).sort("processed_at", -1).to_list(length=1000)
        return logs
    else:
        logs = db.query(ProcessedEmailModel).filter(
            ProcessedEmailModel.candidate_id == norm_cand_id,
            ProcessedEmailModel.status.in_(skipped_statuses)
        ).order_by(ProcessedEmailModel.processed_at.desc()).all()
        
        return [
            {
                "email_id": log.email_id,
                "thread_id": log.thread_id,
                "from_email": log.from_email,
                "subject": log.subject,
                "status": log.status,
                "skip_reason": log.skip_reason or log.status,
                "reasoning": log.reasoning,
                "processed_at": log.processed_at
            }
            for log in logs
        ]
