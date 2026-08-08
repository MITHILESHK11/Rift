import os
import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from app.config import settings
from app.services.rules import evaluate_deterministic_rules, is_psu_or_govt

EMAIL_ANALYSIS_PROMPT = """
Analyse the incoming business email and extract structured task fields.
Apply the routing rules and assignee roster below to determine the correct owner, category, and priority.

ROSTER & ASSIGNEE SCOPE:
- u_aarti (Sales - Enterprise): RFPs, RFIs, tenders, inbound deals >= ₹10,00,000, Government/PSU tenders.
- u_rohit (Sales - SMB): Product enquiries, demo requests, deals < ₹10,00,000.
- u_meera (Marketing): Webinars, event/conference sponsorships, content collaborations, PR/media.
- u_karan (Alliances): Reseller, channel partner, technology integration proposals.
- u_divya (Finance): Invoices, POs, payment reminders, GST, vendor billing.
- u_triage (Operations): Ambiguous requests with multiple competing asks or missing key values.

RULES:
1. Government or PSU tenders MUST go to u_aarti regardless of value.
2. Deals >= ₹10,00,000 go to u_aarti; < ₹10,00,000 go to u_rohit.
3. Parse Indian currency notation: "25 lakhs" -> 2500000, "1.2 cr" -> 12000000, "6,50,000" -> 650000.
4. Invoice amounts belong to u_divya and DO NOT set deal_value_inr.
5. NO TASK (is_noise = true) for Out-Of-Office auto-replies, newsletters, or unsolicited vendor spam.
6. DO NOT invent company names or due dates if unstated.

EMAIL DATA TO READ:
Subject: {subject}
From: {from_name} <{from_email}>
Received At: {received_at}
Body:
{body}

Return STRICT JSON:
{{
  "is_noise": false,
  "noise_type": null,
  "title": "Clear concise task title",
  "description": "Summary of request",
  "assignee_id": "u_aarti",
  "category": "enterprise_rfp",
  "priority": "high",
  "due_date": "YYYY-MM-DD or null",
  "deal_value_inr": 2500000,
  "company_name": "Company Name or null",
  "confidence": 0.95,
  "intent": "enterprise_rfp",
  "direction": "inbound",
  "signals": ["RFP request detected", "Deal value: ₹18L"],
  "rules_triggered": ["enterprise_threshold"],
  "reasoning": "Explanation based on content."
}}
"""

async def extract_with_gemini_async(email_data: Dict[str, Any], client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    """
    Extracts structured task fields from a single email using the language model extraction API.

    Falls back to the deterministic rules engine if the API key is absent, rate-limited,
    or returns an auth error.  Confidence is calibrated post-extraction by comparing the
    extraction result against the rules engine output and penalising ambiguous signals.

    Args:
        email_data: Raw email dict with keys subject, body, from_name, from_email, received_at.
        client:     Optional shared httpx.AsyncClient for connection pooling across batch calls.

    Returns:
        Extraction result dict with keys: should_create_task, assignee_id, category, priority,
        deal_value_inr, confidence, intent, direction, signals, rules_triggered, reasoning.
    """
    rules_eval = evaluate_deterministic_rules(email_data)
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return rules_eval

    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    from_name = email_data.get("from_name", "")
    from_email = email_data.get("from_email", "")
    received_at = email_data.get("received_at", "")

    prompt = EMAIL_ANALYSIS_PROMPT.format(
        subject=subject,
        body=body,
        from_name=from_name,
        from_email=from_email,
        received_at=received_at
    )

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close_client = True

    try:
        for attempt in range(3):
            try:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code in [401, 403]:
                    print(f"Gemini API Key Unauthorized (HTTP {resp.status_code}). Using rules engine fallback.")
                    break
                elif resp.status_code == 200:
                    res_json = resp.json()
                    text_content = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    extracted = json.loads(text_content)

                    # 1. Calibrated Confidence Calculation
                    raw_conf = float(extracted.get("confidence", 0.90))
                    rules_assignee = rules_eval.get("assignee_id") or "u_triage"
                    gemini_assignee = extracted.get("assignee_id") or "u_triage"
                    intent = extracted.get("intent") or extracted.get("category") or "ambiguous"
                    direction = extracted.get("direction") or "ambiguous"
                    is_ambiguous = (gemini_assignee == "u_triage" or intent == "ambiguous" or direction == "ambiguous")

                    calibrated_conf = raw_conf
                    
                    # Agreement check
                    if rules_assignee == gemini_assignee:
                        calibrated_conf += 0.05
                    else:
                        calibrated_conf -= 0.10
                        
                    # Ambiguity check
                    if is_ambiguous:
                        calibrated_conf -= 0.15
                        
                    # Noise / Outbound Vendor check
                    if direction == "outbound_vendor" and intent in ["spam", "newsletter"]:
                        calibrated_conf = 0.95 + (raw_conf * 0.05)
                    else:
                        if intent == "enterprise_rfp" and extracted.get("deal_value_inr") is None:
                            calibrated_conf -= 0.08
                        if not from_email:
                            calibrated_conf -= 0.10

                    calibrated_conf = min(1.0, max(0.10, round(calibrated_conf, 2)))

                    # 2. Extract signals & rules_triggered arrays
                    signals = extracted.get("signals") or []
                    rules_triggered = extracted.get("rules_triggered") or []

                    # Add Python evaluation results to signals/rules list
                    combined = f"{subject}\n{body}"
                    if is_psu_or_govt(combined, from_email):
                        if "PSU/Govt tender override" not in signals:
                            signals.append("PSU/Govt tender override")
                        if "govt_override" not in rules_triggered:
                            rules_triggered.append("govt_override")

                    if extracted.get("is_noise", False) or not rules_eval.get("should_create_task", True):
                        return {
                            "should_create_task": False,
                            "skip_reason": extracted.get("noise_type") or rules_eval.get("skip_reason") or "skipped_spam",
                            "category": None,
                            "assignee_id": None,
                            "confidence": calibrated_conf,
                            "intent": intent,
                            "direction": direction,
                            "signals": signals if signals else ["Noise criteria matched"],
                            "rules_triggered": rules_triggered if rules_triggered else ["noise_filter"],
                            "reasoning": extracted.get("reasoning") or rules_eval.get("reasoning")
                        }

                    category = extracted.get("category") or rules_eval.get("category") or "triage"
                    assignee_id = extracted.get("assignee_id") or rules_eval.get("assignee_id") or "u_triage"
                    priority = extracted.get("priority") or rules_eval.get("priority") or "medium"
                    company_name = extracted.get("company_name") or rules_eval.get("company_name")
                    due_date = extracted.get("due_date") or rules_eval.get("due_date")
                    deal_val = extracted.get("deal_value_inr") if extracted.get("deal_value_inr") is not None else rules_eval.get("deal_value_inr")

                    if is_psu_or_govt(combined, from_email):
                        assignee_id = "u_aarti"
                        category = "enterprise_rfp"
                        if "PSU/Govt tender override" not in signals:
                            signals.append("PSU/Govt tender override")
                        if "govt_override" not in rules_triggered:
                            rules_triggered.append("govt_override")
                    elif deal_val is not None:
                        if deal_val >= 1_000_000 and category in ["enterprise_rfp", "smb_enquiry", "triage"]:
                            assignee_id = "u_aarti"
                            category = "enterprise_rfp"
                            if f"Deal value ₹{deal_val:,} matches enterprise threshold" not in signals:
                                signals.append(f"Deal value ₹{deal_val:,} matches enterprise threshold")
                            if "enterprise_threshold" not in rules_triggered:
                                rules_triggered.append("enterprise_threshold")
                        elif deal_val < 1_000_000 and category in ["enterprise_rfp", "smb_enquiry", "triage"]:
                            assignee_id = "u_rohit"
                            category = "smb_enquiry"
                            if f"Deal value ₹{deal_val:,} matches SMB threshold" not in signals:
                                signals.append(f"Deal value ₹{deal_val:,} matches SMB threshold")
                            if "smb_threshold" not in rules_triggered:
                                rules_triggered.append("smb_threshold")

                    # Add deadline override to rules
                    from app.services.rules import parse_due_date
                    _, is_within_72h = parse_due_date(combined, received_at)
                    if is_within_72h:
                        priority = "high"
                        if "Deadline within 72 hours" not in signals:
                            signals.append("Deadline within 72 hours")
                        if "deadline_72h" not in rules_triggered:
                            rules_triggered.append("deadline_72h")

                    return {
                        "should_create_task": True,
                        "skip_reason": None,
                        "title": extracted.get("title") or f"Request from {from_name or from_email}",
                        "description": extracted.get("description") or body[:200],
                        "assignee_id": assignee_id,
                        "category": category,
                        "priority": priority,
                        "due_date": due_date,
                        "deal_value_inr": deal_val,
                        "company_name": company_name,
                        "confidence": calibrated_conf,
                        "intent": intent,
                        "direction": direction,
                        "signals": signals if signals else ["Buying intent detected"],
                        "rules_triggered": rules_triggered,
                        "reasoning": extracted.get('reasoning', '')
                    }
            except Exception:
                await asyncio.sleep(0.5 * (attempt + 1))
    finally:
        if should_close_client:
            await client.aclose()

    rules_eval["reasoning"] += " (Evaluated via deterministic rules engine)."
    return rules_eval

async def classify_emails_concurrently(emails: List[Dict[str, Any]], concurrency_limit: int = 10) -> List[Dict[str, Any]]:
    """
    Extracts structured task fields from a batch of emails concurrently.

    Uses a shared httpx.AsyncClient for HTTP connection pooling and an asyncio.Semaphore
    to cap the number of in-flight extraction requests (default: 10) and avoid rate-limiting.

    Args:
        emails:            List of raw email dicts.
        concurrency_limit: Maximum number of concurrent extraction requests.

    Returns:
        List of extraction result dicts, in the same order as the input list.
    """
    semaphore = asyncio.Semaphore(concurrency_limit)
    async with httpx.AsyncClient(timeout=12.0) as client:
        async def worker(email_item):
            async with semaphore:
                return await extract_with_gemini_async(email_item, client=client)

        results = await asyncio.gather(*[worker(em) for em in emails])
        return list(results)

def extract_with_gemini(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper around the async extraction function.

    Used in contexts where an event loop cannot be awaited directly (e.g., sync test runners).
    Falls back to the deterministic rules engine on any exception.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(extract_with_gemini_async(email_data))
        return asyncio.run(extract_with_gemini_async(email_data))
    except Exception:
        return evaluate_deterministic_rules(email_data)
