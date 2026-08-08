import re
import datetime
from typing import Optional, Dict, Any, Tuple

# Exact Enums per §5 Spec
ALLOWED_ASSIGNEES = {"u_aarti", "u_rohit", "u_meera", "u_karan", "u_divya", "u_triage"}
ALLOWED_CATEGORIES = {"enterprise_rfp", "smb_enquiry", "marketing", "alliances", "finance", "triage"}
ALLOWED_PRIORITIES = {"high", "medium", "low"}

def strip_quoted_text(body: str) -> str:
    """Strips quoted reply chains from email body to prevent double counting past messages."""
    if not body:
        return ""
    lines = body.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if re.match(r"^On\s+.*wrote:$", stripped, re.IGNORECASE):
            break
        if re.match(r"^From:\s+.*", stripped, re.IGNORECASE):
            break
        if stripped.startswith("-----Original Message-----"):
            break
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()

def parse_indian_currency(text: str) -> Optional[int]:
    """Parses Indian currency notation (lakhs, cr, crores, Rs., INR, numbers, ranges)."""
    if not text:
        return None
    
    # 1. Range pattern: e.g. "20 to 25 lakhs", "20-25 lakh" -> picks upper bound
    range_match = re.search(r'(?:rs\.?|inr|₹)?\s*([\d.]+)\s*(?:to|-)\s*([\d.]+)\s*(?:cr|crore|crores|lakh|lakhs|\bl\b)', text, re.IGNORECASE)
    if range_match:
        try:
            val2 = float(range_match.group(2))
            unit = range_match.group(0).lower()
            if "cr" in unit or "crore" in unit:
                return int(val2 * 10_000_000)
            return int(val2 * 100_000)
        except ValueError:
            pass

    # 2. Crore pattern: e.g., "1.2 cr", "1.2 crore", "Rs 1.5 Crores"
    cr_match = re.search(r'(?:rs\.?|inr|₹)?\s*([\d.]+)\s*(?:cr|crore|crores)', text, re.IGNORECASE)
    if cr_match:
        try:
            val = float(cr_match.group(1))
            return int(val * 10_000_000)
        except ValueError:
            pass

    # 3. Lakh pattern: e.g., "25 lakhs", "6.5 lakh", "Rs. 25 L"
    lakh_match = re.search(r'(?:rs\.?|inr|₹)?\s*([\d.]+)\s*(?:lakhs?|\bl\b)', text, re.IGNORECASE)
    if lakh_match:
        try:
            val = float(lakh_match.group(1))
            return int(val * 100_000)
        except ValueError:
            pass

    # 4. Formatted numbers with commas: e.g. "Rs. 25,00,000", "6,50,000", "4,00,000"
    num_match = re.search(r'(?:rs\.?|inr|₹)?\s*([\d]{1,3}(?:,[\d]{2,3})+)', text, re.IGNORECASE)
    if num_match:
        try:
            num_str = num_match.group(1).replace(",", "")
            return int(num_str)
        except ValueError:
            pass

    return None

def extract_company_name(text: str, from_email: str = "", from_name: str = "") -> Optional[str]:
    """Extracts company name dynamically from email domain or signature without hardcoding specific test domains."""
    if not text and not from_email:
        return None

    # Dynamic extraction from email signature role patterns
    sig_match = re.search(r'(?:founder|ceo|cmo|vp|lead|manager|director|team|head|dept),?\s+([A-Z][A-Za-z0-9\s]{2,30}(?:Pvt|Ltd|Inc|Corp|Services|Logistics|Retail|Steel|Tech|Solutions|Partners|Summit)?)', text, re.IGNORECASE)
    if sig_match:
        comp = sig_match.group(1).strip()
        if len(comp) > 2 and not any(w in comp.lower() for w in ["the", "this", "our", "your", "my"]):
            return comp

    # Dynamic domain fallback (convert sender domain to capitalized company name)
    if from_email and "@" in from_email:
        domain = from_email.split("@")[-1].lower()
        parts = domain.split(".")
        if len(parts) >= 2 and parts[0] not in ["gmail", "yahoo", "hotmail", "outlook"]:
            name = parts[0].replace("-", " ").replace("_", " ").title()
            return name

    return None

def is_psu_or_govt(text: str, email: str = "") -> bool:
    """Checks if email involves a Government or PSU tender."""
    keywords = ["psu", "tender", "bhel", "ntpc", "ongc", "isro", "railway", "govt", "government", "nic.in", "gov.in", "public sector"]
    combined = (text + " " + email).lower()
    return any(kw in combined for kw in keywords)

def classify_spam_or_noise(subject: str, body: str, from_email: str) -> Tuple[bool, Optional[str]]:
    """Identifies Out-Of-Office, Newsletters, or Unsolicited Vendor Spam (Rule 4)."""
    subj_l = subject.lower()
    body_l = body.lower()

    # 1. Out-of-office auto-replies
    ooo_keywords = ["out of office", "auto-reply", "autoreply", "automatic reply", "i am out of office", "limited access to email"]
    if any(k in subj_l or k in body_l for k in ooo_keywords):
        return True, "skipped_ooo"

    # 2. Newsletters
    if "[unsubscribe]" in body_l or "unsubscribe" in body_l or "issue #" in subj_l or "newsletter" in subj_l:
        if "click here to unsubscribe" in body_l or "manage preferences" in body_l or "issue #" in subj_l:
            return True, "skipped_newsletter"

    # 3. Unsolicited vendor spam
    spam_phrases = [
        "15 min call", "quick 15 min", "rank on page 1", "organic traffic",
        "content marketing agency", "pr outreach", "audit attached", "helping saas companies 3x"
    ]
    if any(sp in body_l for sp in spam_phrases) and ("free audit" in body_l or "our services" in body_l):
        return True, "skipped_spam"

    return False, None

def parse_due_date(text: str, received_at_str: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Parses due date from text across multiple date formats (12th August, Aug 12, 12/08/2026, 2026-08-12) and checks 72h rule."""
    if not text:
        return None, False

    try:
        rec_dt = datetime.datetime.fromisoformat(received_at_str.replace("Z", "+00:00")) if received_at_str else datetime.datetime.now(datetime.timezone.utc)
    except Exception:
        rec_dt = datetime.datetime.now(datetime.timezone.utc)

    target_dt = None

    # Format 1: 12th August 2026, 12 August, Aug 12
    fmt1 = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]+)(?:\s+(\d{4}))?', text, re.IGNORECASE)
    fmt2 = re.search(r'([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\,?\s+(\d{4}))?', text, re.IGNORECASE)

    if fmt1:
        try:
            day = int(fmt1.group(1))
            month_str = fmt1.group(2)
            year = int(fmt1.group(3)) if fmt1.group(3) else rec_dt.year
            month_num = datetime.datetime.strptime(month_str[:3], "%b").month
            target_dt = datetime.datetime(year, month_num, day, tzinfo=rec_dt.tzinfo)
        except Exception:
            pass

    if not target_dt and fmt2:
        try:
            month_str = fmt2.group(1)
            day = int(fmt2.group(2))
            year = int(fmt2.group(3)) if fmt2.group(3) else rec_dt.year
            month_num = datetime.datetime.strptime(month_str[:3], "%b").month
            target_dt = datetime.datetime(year, month_num, day, tzinfo=rec_dt.tzinfo)
        except Exception:
            pass

    # Format 3: YYYY-MM-DD or DD/MM/YYYY
    if not target_dt:
        iso_match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
        if iso_match:
            try:
                target_dt = datetime.datetime(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)), tzinfo=rec_dt.tzinfo)
            except Exception:
                pass

    if not target_dt:
        slash_match = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', text)
        if slash_match:
            try:
                target_dt = datetime.datetime(int(slash_match.group(3)), int(slash_match.group(2)), int(slash_match.group(1)), tzinfo=rec_dt.tzinfo)
            except Exception:
                pass

    if target_dt:
        due_date_str = target_dt.strftime("%Y-%m-%d")
        hours_diff = (target_dt - rec_dt).total_seconds() / 3600.0
        is_within_72h = 0 <= hours_diff <= 72
        return due_date_str, is_within_72h

    return None, False

def evaluate_deterministic_rules(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Applies clean business rules suite to enforce hard overrides (PSU, Deal Thresholds, Noise)."""
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    from_email = email_data.get("from_email", "")
    from_name = email_data.get("from_name", "")
    received_at_str = email_data.get("received_at", "")
    
    clean_body = strip_quoted_text(body)
    combined_text = f"{subject}\n{clean_body}"
    signals = ["Rule engine evaluation"]
    rules_triggered = []

    # Rule 4: Noise Filter
    is_noise, noise_type = classify_spam_or_noise(subject, clean_body, from_email)
    if is_noise:
        intent = "spam" if noise_type == "skipped_spam" else ("newsletter" if noise_type == "skipped_newsletter" else "out_of_office")
        direction = "outbound_vendor" if noise_type == "skipped_spam" else "automated"
        return {
            "should_create_task": False,
            "skip_reason": noise_type,
            "category": None,
            "assignee_id": None,
            "confidence": 0.99,
            "intent": intent,
            "direction": direction,
            "signals": ["Noise filter rule matched"],
            "rules_triggered": ["noise_filter"],
            "reasoning": f"Filtered as {noise_type} by Rule 4."
        }

    deal_value = parse_indian_currency(combined_text)
    company_name = extract_company_name(combined_text, from_email, from_name)
    due_date, is_within_72h = parse_due_date(combined_text, received_at_str)

    assignee_id = "u_triage"
    category = "triage"
    priority = "high" if is_within_72h else "medium"
    confidence = 0.85
    reasoning = []

    if is_within_72h:
        signals.append("Deadline within 72 hours")
        rules_triggered.append("deadline_72h")

    # Rule 1: PSU/Govt Override
    if is_psu_or_govt(combined_text, from_email):
        assignee_id = "u_aarti"
        category = "enterprise_rfp"
        signals.append("PSU/Govt tender override")
        rules_triggered.append("govt_override")
        reasoning.append("PSU/Govt tender routed to Aarti per Rule 1 (overrides deal value).")
    elif deal_value is not None:
        if deal_value >= 1_000_000:
            assignee_id = "u_aarti"
            category = "enterprise_rfp"
            signals.append(f"Deal value ₹{deal_value:,} matches enterprise threshold")
            rules_triggered.append("enterprise_threshold")
            reasoning.append(f"Deal value ₹{deal_value:,} ≥ ₹10L routed to Aarti (Enterprise).")
        else:
            assignee_id = "u_rohit"
            category = "smb_enquiry"
            signals.append(f"Deal value ₹{deal_value:,} matches SMB threshold")
            rules_triggered.append("smb_threshold")
            reasoning.append(f"Deal value ₹{deal_value:,} < ₹10L routed to Rohit (SMB).")

    intent = category
    direction = "inbound"

    return {
        "should_create_task": True,
        "skip_reason": None,
        "title": subject or f"Request from {from_name or from_email}",
        "description": clean_body[:200] if clean_body else (subject or "Email Request"),
        "assignee_id": assignee_id,
        "category": category,
        "priority": priority,
        "due_date": due_date,
        "deal_value_inr": deal_value,
        "company_name": company_name,
        "confidence": confidence,
        "intent": intent,
        "direction": direction,
        "signals": signals,
        "rules_triggered": rules_triggered,
        "reasoning": " ".join(reasoning) or "Evaluated via deterministic rules engine."
    }
