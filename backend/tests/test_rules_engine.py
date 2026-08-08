import pytest
from app.services.rules import evaluate_deterministic_rules, parse_indian_currency, strip_quoted_text

def test_parse_indian_currency():
    assert parse_indian_currency("Rs. 25 lakhs") == 2500000
    assert parse_indian_currency("1.2 cr") == 12000000
    assert parse_indian_currency("Rs. 6,50,000") == 650000
    assert parse_indian_currency("4,00,000") == 400000
    assert parse_indian_currency("No money stated") is None

def test_strip_quoted_text():
    raw = "New update text\n\n> On 01 Aug, Suresh wrote:\n> Old text..."
    stripped = strip_quoted_text(raw)
    assert "New update text" in stripped
    assert "Old text" not in stripped

def test_worked_example_1_enterprise_rfp():
    email = {
        "subject": "RFP - Enterprise DMS",
        "body": "Meridian Steel invites proposals for an enterprise DMS covering 4 plants. Budget is Rs. 25 lakhs. Due 12th August 2026.",
        "from_email": "s.kulkarni@meridiansteel.co.in",
        "received_at": "2026-08-01T09:14:22+05:30"
    }
    res = evaluate_deterministic_rules(email)
    assert res["should_create_task"] is True
    assert res["assignee_id"] == "u_aarti"
    assert res["category"] == "enterprise_rfp"
    assert res["deal_value_inr"] == 2500000

def test_worked_example_3_psu_tender():
    email = {
        "subject": "Tender Notice No. BHEL/PROC/2026/0847",
        "body": "Bharat Heavy Electricals Limited invites bids for supply of licences. Estimated value: Rs. 6,50,000. Last date: 03-08-2026.",
        "from_email": "procurement@bhel.in",
        "received_at": "2026-08-01T14:20:00+05:30"
    }
    res = evaluate_deterministic_rules(email)
    assert res["should_create_task"] is True
    assert res["assignee_id"] == "u_aarti"  # Rule 3 overrides 10L threshold!
    assert res["category"] == "enterprise_rfp"
    assert res["deal_value_inr"] == 650000

def test_worked_example_7_ooo_reply():
    email = {
        "subject": "Out of Office: Raghav",
        "body": "I am out of office until 14th August with limited access to email.",
        "from_email": "raghav@northbridge.in",
        "received_at": "2026-08-01T10:00:00+05:30"
    }
    res = evaluate_deterministic_rules(email)
    assert res["should_create_task"] is False
    assert res["skip_reason"] == "skipped_ooo"

def test_worked_example_8_vendor_spam():
    email = {
        "subject": "Quick call regarding organic traffic",
        "body": "Hi, I noticed your website isn't ranking on page 1. We do content marketing agency work. Free audit attached - interested in a quick 15 min call?",
        "from_email": "sales@seoagency.com",
        "received_at": "2026-08-01T11:00:00+05:30"
    }
    res = evaluate_deterministic_rules(email)
    assert res["should_create_task"] is False
    assert res["skip_reason"] == "skipped_spam"
