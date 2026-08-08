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
Answer the user's question using ONLY the provided structured query results.
DO NOT invent or extrapolate any numbers not present in supporting_data.
If the count is 0, state zero clearly.
If the request is out-of-scope (asking to send an email or take actions), decline politely.

USER QUESTION: {query}
SUPPORTING DATA (GROUND TRUTH): {supporting_data_json}

Write a concise 1-2 sentence response reflecting exact supporting_data metrics.
"""

GEMINI_INTERPRET_PROMPT = """
You are a translation layer for a Sales Inbox Router database.
Analyze the user's query and conversation history to map it to a structured query plan.

SCHEMA & CONFIGURATION CONTEXT:
- Assignee IDs: u_aarti (Enterprise), u_rohit (SMB), u_meera (Marketing), u_karan (Alliances), u_divya (Finance), u_triage (Triage)
- Categories: enterprise_rfp, smb_enquiry, marketing, alliances, finance, triage
- Priorities: high, medium, low
- Skipped statuses/reasons: skipped_spam, skipped_ooo, skipped_newsletter, skipped

INTENTS:
- LIST_TASKS: retrieve tasks (optionally filtered by assignee_id, priority, category, query_term)
- COUNT_TASKS: count total matching tasks
- LIST_SKIPPED: retrieve skipped emails
- COUNT_SKIPPED: count skipped emails (optionally filtered by skip_reason: spam, ooo, newsletter)
- SUM_DEAL_VALUE: sum deal_value_inr of active tasks
- LIST_TRIAGE: list tasks in triage category
- LIST_LOW_CONFIDENCE: list tasks where confidence < 0.70
- LIST_HIGH_PRIORITY: list high priority tasks
- GENERAL_STATS: get overview stats
- THREAD_HISTORY: trace history of a specific thread_id or thread reference
- LIST_RUNS: retrieve list of recent ingestion runs
- DECISION_TRACE: explain the classification routing decision trace of a specific task or query term
- OUT_OF_SCOPE: out-of-scope actions like sending emails, deleting, updating tasks

Return ONLY a valid JSON object matching this schema:
{{
  "intent": "LIST_TASKS" | "COUNT_TASKS" | "LIST_SKIPPED" | "COUNT_SKIPPED" | "SUM_DEAL_VALUE" | "LIST_TRIAGE" | "LIST_LOW_CONFIDENCE" | "LIST_HIGH_PRIORITY" | "GENERAL_STATS" | "THREAD_HISTORY" | "LIST_RUNS" | "DECISION_TRACE" | "OUT_OF_SCOPE",
  "filters": {{
    "category": string or null,
    "assignee_id": string or null,
    "priority": string or null,
    "reason": "spam" | "ooo" | "newsletter" | null,
    "query_term": string or null,
    "thread_id": string or null
  }},
  "limit": integer
}}

CONVERSATION HISTORY:
{history_context}

USER QUERY: {query}
"""

def fallback_intent_parse(query: str) -> Dict[str, Any]:
    """Offline deterministic regex fallback parser for query intent."""
    q = query.lower().strip()
    intent = "LIST_TASKS"
    filters = {"category": None, "assignee_id": None, "priority": None, "reason": None, "query_term": None, "thread_id": None}
    
    # Out of scope
    if any(ak in q for ak in ["send", "write", "draft", "dispatch", "delete", "remove", "assign", "reply"]):
        return {"intent": "OUT_OF_SCOPE", "filters": filters, "limit": 20}
        
    # General stats
    if "spurious" in q or "noise rate" in q or "error rate" in q or "stats" in q or "summarize" in q or "summary" in q or "overview" in q:
        return {"intent": "GENERAL_STATS", "filters": filters, "limit": 20}
        
    # Ingestion run history
    if "run history" in q or "ingestion run" in q or "latest run" in q or "batch" in q:
        return {"intent": "LIST_RUNS", "filters": filters, "limit": 10}

    # Decision trace / why
    if "why was" in q or "decision trace" in q or "reason for" in q or "why skipped" in q or "assigned to" in q:
        # Extract query term if possible
        for name in ["aarti", "rohit", "meera", "karan", "divya", "triage", "orbit", "finance", "halcyon"]:
            if name in q:
                filters["query_term"] = name
        return {"intent": "DECISION_TRACE", "filters": filters, "limit": 5}
        
    # Deal value aggregations
    if "deal value" in q or "total value" in q or "revenue" in q or "budget" in q or "value of" in q or "lakh" in q or "crore" in q or "potential" in q:
        return {"intent": "SUM_DEAL_VALUE", "filters": filters, "limit": 20}

    # Thread ID extraction
    thread_match = re.search(r'(th_\w+)', q)
    if thread_match:
        filters["thread_id"] = thread_match.group(1)
        return {"intent": "THREAD_HISTORY", "filters": filters, "limit": 20}

    # Assignee filters
    for name, aid in [("aarti", "u_aarti"), ("rohit", "u_rohit"), ("meera", "u_meera"), ("karan", "u_karan"), ("divya", "u_divya"), ("triage", "u_triage")]:
        if name in q:
            filters["assignee_id"] = aid
            
    # Category filters
    for kw, cat in [("rfp", "enterprise_rfp"), ("proposal", "enterprise_rfp"), ("marketing", "marketing"), ("sponsorship", "marketing"), ("invoice", "finance"), ("gst", "finance")]:
        if kw in q:
            filters["category"] = cat

    # Intent refinements
    if "spam" in q:
        intent = "COUNT_SKIPPED"
        filters["reason"] = "spam"
    elif "newsletter" in q:
        intent = "COUNT_SKIPPED"
        filters["reason"] = "newsletter"
    elif "ooo" in q or "office" in q:
        intent = "COUNT_SKIPPED"
        filters["reason"] = "ooo"
    elif "skipped" in q or "ignored" in q or "emails" in q or "mails" in q:
        intent = "LIST_SKIPPED"
    elif "low confidence" in q or "confidence" in q:
        intent = "LIST_LOW_CONFIDENCE"
    elif "triage" in q:
        intent = "LIST_TRIAGE"
    elif "high priority" in q or "urgent" in q or "attention" in q:
        intent = "LIST_HIGH_PRIORITY"
    elif "how many" in q or "count" in q:
        intent = "COUNT_TASKS"

    # Orbit Finance keyword search term
    if "orbit" in q or "finance" in q:
        filters["query_term"] = "Orbit Finance"

    return {"intent": intent, "filters": filters, "limit": 20}

async def interpret_query_with_gemini(query: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Uses Gemini 2.5 Flash structured output to translate query into structured intent."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or len(api_key) < 10 or api_key.startswith("AQ."):
        return fallback_intent_parse(query)

    history_context = ""
    if history:
        for msg in history:
            sender_lbl = "User" if msg.get("sender") == "user" else "AI"
            history_context += f"{sender_lbl}: {msg.get('text')}\n"
    if not history_context:
        history_context = "No previous context."

    prompt = GEMINI_INTERPRET_PROMPT.format(query=query, history_context=history_context)
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.0
        }
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                res_data = resp.json()
                text_out = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(text_out)
    except Exception as e:
        print(f"Gemini Interpret Query Error: {e}")
    
    return fallback_intent_parse(query)

async def execute_intent_query(db: Session, intent_plan: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
    """Deterministically queries the application store (Motor/SQLAlchemy) based on plan."""
    norm_cand_id = normalize_email(candidate_id)
    intent = intent_plan.get("intent", "LIST_TASKS")
    filters = intent_plan.get("filters", {})
    limit = intent_plan.get("limit", 20)
    
    mongo_active = is_mongo_active()
    mongo_db = get_motor_db() if mongo_active else None

    # Extract Filters
    category = filters.get("category")
    assignee_id = filters.get("assignee_id")
    priority = filters.get("priority")
    reason = filters.get("reason")
    query_term = filters.get("query_term")
    thread_id = filters.get("thread_id")

    if intent == "OUT_OF_SCOPE":
        return {"out_of_scope": True}

    if mongo_active and mongo_db is not None:
        if intent == "GENERAL_STATS":
            tasks_created = await mongo_db.tasks.count_documents({"candidate_id": norm_cand_id})
            total_processed = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id})
            skipped_spam = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "skipped_spam"})
            skipped_ooo = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "skipped_ooo"})
            skipped_newsletter = await mongo_db.processed_emails.count_documents({"candidate_id": norm_cand_id, "status": "skipped_newsletter"})
            total_skipped = skipped_spam + skipped_ooo + skipped_newsletter
            spurious_count = await mongo_db.tasks.count_documents({"candidate_id": norm_cand_id, "$or": [{"confidence": {"$lt": 0.70}}, {"category": "triage"}]})
            return {
                "total_tasks": tasks_created,
                "total_processed": total_processed,
                "total_skipped": total_skipped,
                "spurious_count": spurious_count,
                "spurious_rate": round(spurious_count / tasks_created, 4) if tasks_created > 0 else 0.0
            }
        elif intent == "SUM_DEAL_VALUE":
            match = {"candidate_id": norm_cand_id, "deal_value_inr": {"$ne": None}}
            if category: match["category"] = category
            pipeline = [{"$match": match}, {"$group": {"_id": None, "total": {"$sum": "$deal_value_inr"}}}]
            res = await mongo_db.tasks.aggregate(pipeline).to_list(length=1)
            total = res[0]["total"] if res else 0
            return {"total_deal_value_inr": total}
        elif intent == "COUNT_TASKS":
            q = {"candidate_id": norm_cand_id}
            if category: q["category"] = category
            if assignee_id: q["assignee_id"] = assignee_id
            if priority: q["priority"] = priority
            count = await mongo_db.tasks.count_documents(q)
            return {"count": count}
        elif intent == "COUNT_SKIPPED":
            q = {"candidate_id": norm_cand_id}
            if reason:
                q["status"] = f"skipped_{reason}"
            else:
                q["status"] = {"$in": ["skipped_spam", "skipped_ooo", "skipped_newsletter", "skipped"]}
            count = await mongo_db.processed_emails.count_documents(q)
            return {"count": count}
        elif intent in ["LIST_TASKS", "LIST_TRIAGE", "LIST_LOW_CONFIDENCE", "LIST_HIGH_PRIORITY"]:
            q = {"candidate_id": norm_cand_id}
            if category: q["category"] = category
            if assignee_id: q["assignee_id"] = assignee_id
            if priority: q["priority"] = priority
            if intent == "LIST_TRIAGE": q["category"] = "triage"
            if intent == "LIST_LOW_CONFIDENCE": q["confidence"] = {"$lt": 0.70}
            if intent == "LIST_HIGH_PRIORITY": q["priority"] = "high"
            
            if query_term:
                q["$or"] = [
                    {"title": {"$regex": query_term, "$options": "i"}},
                    {"description": {"$regex": query_term, "$options": "i"}},
                    {"company_name": {"$regex": query_term, "$options": "i"}}
                ]
            
            tasks = await mongo_db.tasks.find(q, {"_id": 0}).limit(limit).to_list(length=limit)
            return {"tasks": tasks, "count": len(tasks)}
        elif intent == "LIST_SKIPPED":
            q = {"candidate_id": norm_cand_id}
            if reason:
                q["status"] = f"skipped_{reason}"
            else:
                q["status"] = {"$in": ["skipped_spam", "skipped_ooo", "skipped_newsletter", "skipped"]}
            logs = await mongo_db.processed_emails.find(q, {"_id": 0}).limit(limit).to_list(length=limit)
            return {"skipped_emails": logs, "count": len(logs)}
        elif intent == "THREAD_HISTORY":
            t_id = thread_id or query_term
            if t_id:
                logs = await mongo_db.processed_emails.find(
                    {"candidate_id": norm_cand_id, "thread_id": t_id},
                    {"_id": 0}
                ).sort("processed_at", 1).to_list(length=100)
                return {"thread_id": t_id, "emails": logs, "count": len(logs)}
            return {"thread_id": None, "emails": [], "count": 0}
        elif intent == "LIST_RUNS":
            runs = await mongo_db.ingestion_runs.find({"candidate_id": norm_cand_id}, {"_id": 0}).sort("processed_at", -1).limit(limit).to_list(length=limit)
            return {"runs": runs, "count": len(runs)}
        elif intent == "DECISION_TRACE":
            q = {"candidate_id": norm_cand_id}
            if query_term:
                q["$or"] = [
                    {"subject": {"$regex": query_term, "$options": "i"}},
                    {"from_name": {"$regex": query_term, "$options": "i"}},
                    {"from_email": {"$regex": query_term, "$options": "i"}},
                    {"task_id": {"$regex": query_term, "$options": "i"}},
                    {"email_id": {"$regex": query_term, "$options": "i"}}
                ]
            item = await mongo_db.processed_emails.find_one(q, {"_id": 0})
            return {"decision_trace": item}
        
        return {}

    else:
        # SQL fallback path
        if intent == "GENERAL_STATS":
            tasks_created = db.query(TaskModel).filter(TaskModel.candidate_id == norm_cand_id).count()
            total_processed = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id).count()
            skipped_spam = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id, ProcessedEmailModel.status == "skipped_spam").count()
            skipped_ooo = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id, ProcessedEmailModel.status == "skipped_ooo").count()
            skipped_newsletter = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id, ProcessedEmailModel.status == "skipped_newsletter").count()
            total_skipped = skipped_spam + skipped_ooo + skipped_newsletter
            spurious_count = db.query(TaskModel).filter(
                TaskModel.candidate_id == norm_cand_id,
                (TaskModel.confidence < 0.70) | (TaskModel.category == "triage")
            ).count()
            return {
                "total_tasks": tasks_created,
                "total_processed": total_processed,
                "total_skipped": total_skipped,
                "spurious_count": spurious_count,
                "spurious_rate": round(spurious_count / tasks_created, 4) if tasks_created > 0 else 0.0
            }
        elif intent == "SUM_DEAL_VALUE":
            query = db.query(func.sum(TaskModel.deal_value_inr)).filter(
                TaskModel.candidate_id == norm_cand_id,
                TaskModel.deal_value_inr.isnot(None)
            )
            if category:
                query = query.filter(TaskModel.category == category)
            total = query.scalar() or 0
            return {"total_deal_value_inr": total}
        elif intent == "COUNT_TASKS":
            query = db.query(TaskModel).filter(TaskModel.candidate_id == norm_cand_id)
            if category: query = query.filter(TaskModel.category == category)
            if assignee_id: query = query.filter(TaskModel.assignee_id == assignee_id)
            if priority: query = query.filter(TaskModel.priority == priority)
            return {"count": query.count()}
        elif intent == "COUNT_SKIPPED":
            query = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id)
            if reason:
                query = query.filter(ProcessedEmailModel.status == f"skipped_{reason}")
            else:
                query = query.filter(ProcessedEmailModel.status.in_(["skipped_spam", "skipped_ooo", "skipped_newsletter", "skipped"]))
            return {"count": query.count()}
        elif intent in ["LIST_TASKS", "LIST_TRIAGE", "LIST_LOW_CONFIDENCE", "LIST_HIGH_PRIORITY"]:
            query = db.query(TaskModel).filter(TaskModel.candidate_id == norm_cand_id)
            if category: query = query.filter(TaskModel.category == category)
            if assignee_id: query = query.filter(TaskModel.assignee_id == assignee_id)
            if priority: query = query.filter(TaskModel.priority == priority)
            if intent == "LIST_TRIAGE": query = query.filter(TaskModel.category == "triage")
            if intent == "LIST_LOW_CONFIDENCE": query = query.filter(TaskModel.confidence < 0.70)
            if intent == "LIST_HIGH_PRIORITY": query = query.filter(TaskModel.priority == "high")
            
            if query_term:
                query = query.filter(
                    (TaskModel.title.contains(query_term)) | 
                    (TaskModel.description.contains(query_term)) |
                    (TaskModel.company_name.contains(query_term))
                )
            
            tasks = query.limit(limit).all()
            return {
                "tasks": [
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
                ],
                "count": len(tasks)
            }
        elif intent == "LIST_SKIPPED":
            query = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id)
            if reason:
                query = query.filter(ProcessedEmailModel.status == f"skipped_{reason}")
            else:
                query = query.filter(ProcessedEmailModel.status.in_(["skipped_spam", "skipped_ooo", "skipped_newsletter", "skipped"]))
            logs = query.limit(limit).all()
            return {
                "skipped_emails": [
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
                ],
                "count": len(logs)
            }
        elif intent == "THREAD_HISTORY":
            t_id = thread_id or query_term
            if t_id:
                logs = db.query(ProcessedEmailModel).filter(
                    ProcessedEmailModel.candidate_id == norm_cand_id,
                    ProcessedEmailModel.thread_id == t_id
                ).order_by(ProcessedEmailModel.processed_at.asc()).all()
                return {
                    "thread_id": t_id,
                    "emails": [
                        {
                            "email_id": log.email_id,
                            "from_email": log.from_email,
                            "subject": log.subject,
                            "status": log.status,
                            "reasoning": log.reasoning,
                            "processed_at": log.processed_at
                        }
                        for log in logs
                    ],
                    "count": len(logs)
                }
            return {"thread_id": None, "emails": [], "count": 0}
        elif intent == "LIST_RUNS":
            from app.db.models import IngestionRunModel
            runs = db.query(IngestionRunModel).filter(IngestionRunModel.candidate_id == norm_cand_id).order_by(IngestionRunModel.processed_at.desc()).limit(limit).all()
            return {
                "runs": [
                    {
                        "run_id": r.run_id,
                        "processed_at": r.processed_at,
                        "processed_count": r.processed_count,
                        "tasks_created": r.tasks_created,
                        "tasks_updated": r.tasks_updated,
                        "emails_skipped": r.emails_skipped,
                        "spurious_count": r.spurious_count,
                        "errors_count": r.errors_count
                    }
                    for r in runs
                ],
                "count": len(runs)
            }
        elif intent == "DECISION_TRACE":
            query = db.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_cand_id)
            if query_term:
                query = query.filter(
                    (ProcessedEmailModel.subject.contains(query_term)) |
                    (ProcessedEmailModel.from_name.contains(query_term)) |
                    (ProcessedEmailModel.from_email.contains(query_term)) |
                    (ProcessedEmailModel.task_id.contains(query_term)) |
                    (ProcessedEmailModel.email_id.contains(query_term))
                )
            item = query.order_by(ProcessedEmailModel.processed_at.desc()).first()
            if item:
                signals_data = []
                rules_data = []
                import json
                if item.signals:
                    try: signals_data = json.loads(item.signals)
                    except Exception: signals_data = [item.signals]
                if item.rules_triggered:
                    try: rules_data = json.loads(item.rules_triggered)
                    except Exception: rules_data = [item.rules_triggered]
                return {
                    "decision_trace": {
                        "email_id": item.email_id,
                        "from_name": item.from_name,
                        "subject": item.subject,
                        "status": item.status,
                        "category": item.category,
                        "confidence": item.confidence,
                        "reasoning": item.reasoning,
                        "direction": item.direction or "inbound",
                        "intent": item.intent or item.category or "ambiguous",
                        "signals": signals_data,
                        "rules_triggered": rules_data
                    }
                }
            return {"decision_trace": None}
            
        return {}

async def generate_grounded_answer(query: str, db_result: Dict[str, Any], intent_plan: Dict[str, Any], candidate_id: str) -> str:
    """Generates user-facing conversational response strictly scoped to database ground-truth result."""
    intent = intent_plan.get("intent")
    count = db_result.get("count")
    total_val = db_result.get("total_deal_value_inr")
    
    if intent == "SUM_DEAL_VALUE":
        fallback = f"The total deal value for candidate `{candidate_id}` is ₹{total_val:,} across active tasks."
    elif intent == "COUNT_TASKS":
        fallback = f"There are {count} total task(s) matching your query for candidate `{candidate_id}`."
    elif intent == "COUNT_SKIPPED":
        fallback = f"There are {count} skipped email(s) matching your query for candidate `{candidate_id}`."
    elif intent == "GENERAL_STATS":
        fallback = f"For candidate `{candidate_id}`, total tasks: {db_result.get('total_tasks')}, total processed: {db_result.get('total_processed')}, total skipped: {db_result.get('total_skipped')}."
    else:
        fallback = f"Query executed successfully for candidate `{candidate_id}`."

    api_key = settings.GEMINI_API_KEY
    if not api_key or len(api_key) < 10 or api_key.startswith("AQ."):
        return fallback

    prompt = GEMINI_PHRASER_PROMPT.format(
        query=query,
        supporting_data_json=json.dumps(db_result, indent=2)
    )
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                res_data = resp.json()
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Gemini Phraser Error: {e}")

    return fallback

async def execute_grounded_chat_query(
    db: Session, 
    query: str, 
    candidate_id: str = "", 
    history: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Executes full Candidate-Scoped Plan -> Execute -> Phrase grounded chat pipeline."""
    norm_cand_id = normalize_email(candidate_id or settings.CANDIDATE_ID)
    
    # 1. Interpret user query intent with Gemini model (including conversation history)
    intent_plan = await interpret_query_with_gemini(query, history=history)
    
    # 2. Execute plan deterministically against database store
    db_result = await execute_intent_query(db, intent_plan, norm_cand_id)
    
    if db_result.get("out_of_scope"):
        return {
            "answer": "I can analyze and query the processed inbox data, but I can't send emails or perform external actions from this chat.",
            "query_intent": "out_of_scope",
            "supporting_data": {"out_of_scope": True, "candidate_id": norm_cand_id},
            "metadata": {
                "candidate_id": norm_cand_id,
                "source": "validation"
            }
        }
        
    # 3. Conversational phrasing grounded strictly in query result
    answer = await generate_grounded_answer(query, db_result, intent_plan, norm_cand_id)
    
    return {
        "answer": answer,
        "query_intent": intent_plan.get("intent", "LIST_TASKS"),
        "supporting_data": db_result,
        "metadata": {
            "candidate_id": norm_cand_id,
            "source": "database"
        }
    }
