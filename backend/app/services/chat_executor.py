import re
import json
import httpx
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.config import settings, normalize_email
from app.db.models import TaskModel, ProcessedEmailModel, ThreadMapModel
from app.db.mongo import get_motor_db, is_mongo_active

GEMINI_PHRASER_PROMPT = """
You are a grounded assistant for a Sales Inbox Task Router.
Answer the user's question using ONLY the provided structured SQL query results.
DO NOT invent or extrapolate any numbers not present in supporting_data.
If the count is 0, state zero clearly.
If the request is out-of-scope (asking to send an email or take actions), decline politely.

USER QUESTION: {query}
SUPPORTING DATA (GROUND TRUTH): {supporting_data_json}

Write a concise 1-2 sentence response reflecting exact supporting_data metrics.
"""

def execute_grounded_chat_query(db: Session, query: str, candidate_id: str = "") -> Dict[str, Any]:
    """Executes a Candidate-Scoped Plan -> Execute -> Phrase grounded chat pipeline supporting both MongoDB & SQL."""
    norm_cand_id = normalize_email(candidate_id or settings.CANDIDATE_ID)
    q_lower = query.lower().strip()
    supporting_data: Dict[str, Any] = {"candidate_id": norm_cand_id}

    mongo_active = is_mongo_active()
    mongo_db = get_motor_db().delegate if mongo_active else None

    # 1. Out of scope / Action trap
    if any(q_lower.startswith(ak) or f" {ak}" in q_lower for ak in ["send", "write an email", "draft", "dispatch", "delete", "remove"]):
        return {
            "answer": "I am a read-only Sales Inbox analytical assistant. I cannot send emails or execute external actions.",
            "supporting_data": {"out_of_scope": True, "candidate_id": norm_cand_id}
        }

    # 2. Dynamic Spurious & Error Rate Query
    if "spurious" in q_lower or "noise rate" in q_lower or "error rate" in q_lower:
        if mongo_active and mongo_db is not None:
            total_tasks = mongo_db.tasks.count_documents({"candidate_id": norm_cand_id})
            spurious_count = mongo_db.tasks.count_documents({
                "candidate_id": norm_cand_id,
                "$or": [{"confidence": {"$lt": 0.70}}, {"category": "triage"}]
            })
            total_processed = mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id})
            skipped_count = mongo_db.processed_emails.count_documents({
                "candidate_id": norm_cand_id,
                "status": {"$regex": "^skipped_"}
            })
        else:
            total_tasks = db.query(func.count(TaskModel.task_id)).filter(TaskModel.candidate_id == norm_cand_id).scalar() or 0
            spurious_count = db.query(func.count(TaskModel.task_id)).filter(
                TaskModel.candidate_id == norm_cand_id,
                (TaskModel.confidence < 0.70) | (TaskModel.category == "triage")
            ).scalar() or 0
            total_processed = db.query(func.count(ProcessedEmailModel.email_id)).scalar() or 0
            skipped_count = db.query(func.count(ProcessedEmailModel.email_id)).filter(
                ProcessedEmailModel.status.startswith("skipped_")
            ).scalar() or 0

        spurious_rate = round(spurious_count / total_tasks, 4) if total_tasks > 0 else 0.0
        supporting_data = {
            "candidate_id": norm_cand_id,
            "total_tasks": total_tasks,
            "spurious_task_count": spurious_count,
            "spurious_rate": spurious_rate,
            "total_emails_processed": total_processed,
            "skipped_noise_count": skipped_count
        }
        answer = f"For candidate `{norm_cand_id}`, the spurious task rate is {spurious_rate * 100:.1f}% ({spurious_count} triage/low-confidence tasks out of {total_tasks} tasks)."
        return format_with_gemini_phraser(query, supporting_data, answer)

    # 3. Total Deal Value Aggregation
    if "deal value" in q_lower or "total value" in q_lower or "revenue" in q_lower or "budget" in q_lower:
        if mongo_active and mongo_db is not None:
            pipeline = [
                {"$match": {"candidate_id": norm_cand_id, "deal_value_inr": {"$ne": None}}},
                {"$group": {"_id": None, "total": {"$sum": "$deal_value_inr"}}}
            ]
            res = list(mongo_db.tasks.aggregate(pipeline))
            total_val = res[0]["total"] if res else 0
        else:
            total_val = db.query(func.sum(TaskModel.deal_value_inr)).filter(
                TaskModel.candidate_id == norm_cand_id,
                TaskModel.deal_value_inr.isnot(None)
            ).scalar() or 0

        supporting_data = {
            "candidate_id": norm_cand_id,
            "total_deal_value_inr": total_val,
            "formatted_inr": f"₹{total_val:,}"
        }
        answer = f"The total deal value for `{norm_cand_id}` is ₹{total_val:,} across active tasks."
        return format_with_gemini_phraser(query, supporting_data, answer)

    # 4. Assignee-Specific Queries
    assignee_map = {
        "aarti": "u_aarti",
        "rohit": "u_rohit",
        "meera": "u_meera",
        "karan": "u_karan",
        "divya": "u_divya",
        "triage": "u_triage"
    }
    matched_assignee = None
    for name, aid in assignee_map.items():
        if name in q_lower:
            matched_assignee = (name, aid)
            break

    if matched_assignee and not ("marketing vs" in q_lower or "proposal vs" in q_lower):
        name, aid = matched_assignee
        if mongo_active and mongo_db is not None:
            tasks_list = list(mongo_db.tasks.find({"candidate_id": norm_cand_id, "assignee_id": aid}))
            task_ids = [t.get("task_id") for t in tasks_list]
        else:
            tasks = db.query(TaskModel).filter(
                TaskModel.candidate_id == norm_cand_id,
                TaskModel.assignee_id == aid
            ).all()
            task_ids = [t.task_id for t in tasks]

        supporting_data = {
            "candidate_id": norm_cand_id,
            "assignee_name": name.capitalize(),
            "assignee_id": aid,
            "task_count": len(task_ids),
            "task_ids": task_ids
        }
        answer = f"{name.capitalize()} (`{aid}`) has {len(task_ids)} task(s) assigned for candidate `{norm_cand_id}`."
        return format_with_gemini_phraser(query, supporting_data, answer)

    # 5. Category Queries (RFPs, Marketing, Finance, Alliances, SMB)
    category_map = {
        "rfp": "enterprise_rfp",
        "proposal": "enterprise_rfp",
        "enterprise": "enterprise_rfp",
        "marketing": "marketing",
        "sponsorship": "marketing",
        "webinar": "marketing",
        "finance": "finance",
        "invoice": "finance",
        "billing": "finance",
        "gst": "finance",
        "alliance": "alliances",
        "partner": "alliances",
        "reseller": "alliances",
        "smb": "smb_enquiry",
        "demo": "smb_enquiry"
    }
    
    matched_cat = None
    for kw, cat in category_map.items():
        if kw in q_lower and not ("gst refund" in q_lower or "tax refund" in q_lower):
            matched_cat = cat
            break

    if matched_cat:
        if mongo_active and mongo_db is not None:
            tasks_list = list(mongo_db.tasks.find({"candidate_id": norm_cand_id, "category": matched_cat}))
            task_ids = [t.get("task_id") for t in tasks_list]
        else:
            tasks = db.query(TaskModel).filter(
                TaskModel.candidate_id == norm_cand_id,
                TaskModel.category == matched_cat
            ).all()
            task_ids = [t.task_id for t in tasks]

        supporting_data = {
            "candidate_id": norm_cand_id,
            "category": matched_cat,
            "task_count": len(task_ids),
            "task_ids": task_ids
        }
        answer = f"There are {len(task_ids)} task(s) in category `{matched_cat}` for candidate `{norm_cand_id}`."
        return format_with_gemini_phraser(query, supporting_data, answer)

    # 6. Specific Dynamic Keyword Search
    words = [w for w in re.findall(r'\w+', q_lower) if len(w) > 2 and w not in ["how", "many", "were", "about", "emails", "tasks", "related", "the", "show", "what", "are", "mails", "here"]]
    if words:
        if mongo_active and mongo_db is not None:
            tasks_list = list(mongo_db.tasks.find({"candidate_id": norm_cand_id}))
            filtered = []
            for t in tasks_list:
                text = f"{t.get('title', '')} {t.get('description') or ''}".lower()
                if any(w in text for w in words):
                    filtered.append(t.get("task_id"))
        else:
            matching_tasks = db.query(TaskModel).filter(
                TaskModel.candidate_id == norm_cand_id
            ).all()
            filtered = []
            for t in matching_tasks:
                text = f"{t.title} {t.description or ''}".lower()
                if any(w in text for w in words):
                    filtered.append(t.task_id)

        term_str = " ".join(words)
        supporting_data = {
            "candidate_id": norm_cand_id,
            "query_terms": term_str,
            "matched_task_count": len(filtered),
            "matched_task_ids": filtered
        }
        if filtered:
            answer = f"Found {len(filtered)} task(s) matching '{term_str}' for candidate `{norm_cand_id}`."
        else:
            answer = f"There were 0 tasks or emails related to '{term_str}' for candidate `{norm_cand_id}`."
        return format_with_gemini_phraser(query, supporting_data, answer)

    # 7. General query / fallback list tasks
    if mongo_active and mongo_db is not None:
        tasks_list = list(mongo_db.tasks.find({"candidate_id": norm_cand_id}))
        task_ids = [t.get("task_id") for t in tasks_list]
    else:
        tasks = db.query(TaskModel).filter(TaskModel.candidate_id == norm_cand_id).all()
        task_ids = [t.task_id for t in tasks]

    supporting_data = {
        "candidate_id": norm_cand_id,
        "matched_count": len(task_ids),
        "task_ids": task_ids[:10]
    }
    if task_ids:
        answer = f"There are {len(task_ids)} total tasks recorded for candidate `{norm_cand_id}`."
    else:
        answer = f"I do not have data or matching task records for '{query}' under candidate `{norm_cand_id}`."
    return format_with_gemini_phraser(query, supporting_data, answer)

def format_with_gemini_phraser(query: str, supporting_data: Dict[str, Any], fallback_answer: str) -> Dict[str, Any]:
    """Uses Gemini 2.5 Flash Phraser to format response based strictly on ground-truth supporting_data."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"answer": fallback_answer, "supporting_data": supporting_data}

    prompt = GEMINI_PHRASER_PROMPT.format(
        query=query,
        supporting_data_json=json.dumps(supporting_data, indent=2)
    )

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                res_data = resp.json()
                text_out = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return {"answer": text_out, "supporting_data": supporting_data}
    except Exception as e:
        print(f"Gemini Phraser Error: {e}")

    return {"answer": fallback_answer, "supporting_data": supporting_data}
