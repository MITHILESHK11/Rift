import uuid
import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.db.models import TaskModel
from app.db.mongo import get_motor_db, is_mongo_active
from app.config import settings, normalize_email
from app.services.rules import ALLOWED_ASSIGNEES, ALLOWED_CATEGORIES, ALLOWED_PRIORITIES

router = APIRouter(tags=["Task API (Section 5)"])

class TaskCreateSchema(BaseModel):
    candidate_id: str
    source_email_id: str
    thread_id: str
    title: str
    description: Optional[str] = None
    assignee_id: str
    category: str
    priority: str
    due_date: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    confidence: float = 1.0

class TaskPatchSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    confidence: Optional[float] = None

@router.post("/tasks", status_code=status.HTTP_201_CREATED)
@router.post("/api/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreateSchema, db: Session = Depends(get_db)):
    """Section 5.1: Create a task with strict enum error validation and candidate-scoped deduplication."""
    if payload.assignee_id not in ALLOWED_ASSIGNEES:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_enum_value",
                "field": "assignee_id",
                "received": payload.assignee_id,
                "allowed": sorted(list(ALLOWED_ASSIGNEES))
            }
        )
    if payload.category not in ALLOWED_CATEGORIES:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_enum_value",
                "field": "category",
                "received": payload.category,
                "allowed": sorted(list(ALLOWED_CATEGORIES))
            }
        )
    if payload.priority not in ALLOWED_PRIORITIES:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_enum_value",
                "field": "priority",
                "received": payload.priority,
                "allowed": sorted(list(ALLOWED_PRIORITIES))
            }
        )

    norm_cand_id = normalize_email(payload.candidate_id)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        # Check deduplication on candidate_id + source_email_id
        existing = await mongo_db.tasks.find_one({"candidate_id": norm_cand_id, "source_email_id": payload.source_email_id})
        if existing:
            return {
                "task_id": existing["task_id"],
                "candidate_id": existing["candidate_id"],
                "source_email_id": existing["source_email_id"],
                "thread_id": existing["thread_id"],
                "title": existing["title"],
                "description": existing.get("description"),
                "assignee_id": existing["assignee_id"],
                "category": existing["category"],
                "priority": existing["priority"],
                "due_date": existing.get("due_date"),
                "deal_value_inr": existing.get("deal_value_inr"),
                "company_name": existing.get("company_name"),
                "confidence": existing.get("confidence", 1.0),
                "created_at": existing["created_at"],
                "updated_at": existing["updated_at"],
                "note": "existing_duplicate"
            }

        task_id = f"tsk_{uuid.uuid4().hex[:8]}"
        doc = {
            "task_id": task_id,
            "candidate_id": norm_cand_id,
            "source_email_id": payload.source_email_id,
            "thread_id": payload.thread_id,
            "title": payload.title,
            "description": payload.description,
            "assignee_id": payload.assignee_id,
            "category": payload.category,
            "priority": payload.priority,
            "due_date": payload.due_date,
            "deal_value_inr": payload.deal_value_inr,
            "company_name": payload.company_name,
            "confidence": payload.confidence,
            "created_at": now_iso,
            "updated_at": now_iso
        }
        await mongo_db.tasks.insert_one(doc)
        return doc

    else:
        # SQL Processing
        existing = db.query(TaskModel).filter(
            TaskModel.candidate_id == norm_cand_id,
            TaskModel.source_email_id == payload.source_email_id
        ).first()

        if existing:
            return {
                "task_id": existing.task_id,
                "candidate_id": existing.candidate_id,
                "source_email_id": existing.source_email_id,
                "thread_id": existing.thread_id,
                "title": existing.title,
                "description": existing.description,
                "assignee_id": existing.assignee_id,
                "category": existing.category,
                "priority": existing.priority,
                "due_date": existing.due_date,
                "deal_value_inr": existing.deal_value_inr,
                "company_name": existing.company_name,
                "confidence": existing.confidence,
                "created_at": existing.created_at,
                "updated_at": existing.updated_at,
                "note": "existing_duplicate"
            }

        task_id = f"tsk_{uuid.uuid4().hex[:8]}"
        task = TaskModel(
            task_id=task_id,
            candidate_id=norm_cand_id,
            source_email_id=payload.source_email_id,
            thread_id=payload.thread_id,
            title=payload.title,
            description=payload.description,
            assignee_id=payload.assignee_id,
            category=payload.category,
            priority=payload.priority,
            due_date=payload.due_date,
            deal_value_inr=payload.deal_value_inr,
            company_name=payload.company_name,
            confidence=payload.confidence,
            created_at=now_iso,
            updated_at=now_iso
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return {
            "task_id": task.task_id,
            "candidate_id": task.candidate_id,
            "source_email_id": task.source_email_id,
            "thread_id": task.thread_id,
            "title": task.title,
            "description": task.description,
            "assignee_id": task.assignee_id,
            "category": task.category,
            "priority": task.priority,
            "due_date": task.due_date,
            "deal_value_inr": task.deal_value_inr,
            "company_name": task.company_name,
            "confidence": task.confidence,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }

@router.get("/tasks")
@router.get("/api/tasks")
async def list_tasks(
    candidate_id: str = Query(..., description="Mandatory candidate_id email"),
    thread_id: Optional[str] = None,
    source_email_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(250, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Section 5.4: Read-only candidate-scoped task list endpoint (Zero GET mutations)."""
    norm_cand_id = normalize_email(candidate_id)
    mongo_db = get_motor_db() if is_mongo_active() else None

    if mongo_db is not None:
        query = {"candidate_id": norm_cand_id}
        if thread_id: query["thread_id"] = thread_id
        if source_email_id: query["source_email_id"] = source_email_id
        if assignee_id: query["assignee_id"] = assignee_id
        if category: query["category"] = category
        if priority: query["priority"] = priority

        cursor = mongo_db.tasks.find(query, {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit)
        return await cursor.to_list(length=limit)
    else:
        query = db.query(TaskModel).filter(TaskModel.candidate_id == norm_cand_id)
        if thread_id: query = query.filter(TaskModel.thread_id == thread_id)
        if source_email_id: query = query.filter(TaskModel.source_email_id == source_email_id)
        if assignee_id: query = query.filter(TaskModel.assignee_id == assignee_id)
        if category: query = query.filter(TaskModel.category == category)
        if priority: query = query.filter(TaskModel.priority == priority)

        query = query.order_by(TaskModel.created_at.desc())
        tasks = query.offset(offset).limit(limit).all()

        return [
            {
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
                "updated_at": t.updated_at
            }
            for t in tasks
        ]
