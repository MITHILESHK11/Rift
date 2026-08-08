import sys
import os
import json
import httpx

def main():
    base_url = "http://localhost:8000"
    print("=" * 70)
    print(f"VERIFYING INTELLIGENCE & OPERATIONS ENDPOINTS AGAINST: {base_url}")
    print("=" * 70)

    client = httpx.Client(base_url=base_url, timeout=15.0)
    test_cand = "operations.test@company.com"

    # Step 1: Clear Database to start clean
    print("Clearing database...")
    client.post("/api/clear-database")

    # Step 2: Ingest a custom batch of emails (including low confidence triggers, skipped ones, and threads)
    emails_payload = [
        {
            "email_id": "em_rfp001",
            "thread_id": "th_rfp999",
            "message_index": 0,
            "from_name": "Halcyon Enterprise LLC",
            "from_email": "procurement@halcyon.com",
            "subject": "Request for Proposal: Halcyon cloud migration",
            "body": "Dear Sales, we are initiating a PSU cloud migration RFP. The deal value is estimated at 35 Lakhs. Please assign an owner immediately. Category is enterprise_rfp, priority high, due date 2026-09-01.",
            "received_at": "2026-08-08T10:00:00Z",
            "is_reply": False
        },
        {
            "email_id": "em_spam002",
            "thread_id": "th_spam888",
            "message_index": 0,
            "from_name": "Casino Royal Promo",
            "from_email": "spammer@casino.net",
            "subject": "Win 10 Million Rupees NOW!!!",
            "body": "Click this link to claim your cash reward. Offer expires in 2 hours.",
            "received_at": "2026-08-08T10:05:00Z",
            "is_reply": False
        },
        {
            "email_id": "em_triage003",
            "thread_id": "th_triage777",
            "message_index": 0,
            "from_name": "Ambiguous Query User",
            "from_email": "user@uncertain.com",
            "subject": "Question about something general",
            "body": "Hi, I have a quick question. Can we schedule a call next week? Not sure what type of product we need yet, maybe SMB maybe enterprise.",
            "received_at": "2026-08-08T10:10:00Z",
            "is_reply": False
        },
        {
            "email_id": "em_rfp_reply004",
            "thread_id": "th_rfp999",
            "message_index": 1,
            "from_name": "Halcyon Procurement Manager",
            "from_email": "procurement@halcyon.com",
            "subject": "Re: Request for Proposal: Halcyon cloud migration",
            "body": "Further update: We have escalated this deal value. The revised budget is 45 Lakhs. Priority escalated to high.",
            "received_at": "2026-08-08T10:15:00Z",
            "is_reply": True
        }
    ]

    print("\nIngesting batch of 4 emails...")
    r_ing = client.post(f"/api/ingest?candidate_id={test_cand}", json=emails_payload)
    print(f"Ingest Status: {r_ing.status_code}, Res: {r_ing.text}")
    assert r_ing.status_code == 200

    # Step 3: GET /api/runs (Verify Run History list)
    print("\n[1] GET /api/runs...")
    r_runs = client.get(f"/api/runs?candidate_id={test_cand}")
    print(f"Status: {r_runs.status_code}")
    assert r_runs.status_code == 200
    runs_data = r_runs.json()
    print(f"Runs Logged: {json.dumps(runs_data, indent=2)}")
    assert len(runs_data) > 0
    run_id = runs_data[0]["run_id"]

    # Step 4: GET /api/runs/{run_id} (Verify Run Details)
    print(f"\n[2] GET /api/runs/{run_id}...")
    r_detail = client.get(f"/api/runs/{run_id}?candidate_id={test_cand}")
    print(f"Status: {r_detail.status_code}")
    assert r_detail.status_code == 200
    detail_data = r_detail.json()
    print(f"Run detail summary: {json.dumps(detail_data['run'], indent=2)}")
    print(f"Run items count: {len(detail_data['items'])}")
    assert len(detail_data["items"]) > 0

    # Step 5: GET /api/thread-timeline/{thread_id} (Verify Thread Timeline)
    print("\n[3] GET /api/thread-timeline/th_rfp999...")
    r_thread = client.get(f"/api/thread-timeline/th_rfp999?candidate_id={test_cand}")
    print(f"Status: {r_thread.status_code}")
    assert r_thread.status_code == 200
    thread_data = r_thread.json()
    print(f"Thread Timeline Logs: {json.dumps(thread_data, indent=2)}")
    assert len(thread_data) == 2  # Original + Reply

    # Step 6: GET /api/decision-center (Verify Decision Center aggregates & traces)
    print("\n[4] GET /api/decision-center...")
    r_dc = client.get(f"/api/decision-center?candidate_id={test_cand}")
    print(f"Status: {r_dc.status_code}")
    assert r_dc.status_code == 200
    dc_data = r_dc.json()
    print(f"Stats Aggregates: {json.dumps(dc_data['stats'], indent=2)}")
    print(f"Recent Decisions Count: {len(dc_data['recent_decisions'])}")
    assert dc_data["stats"]["total_decisions"] > 0

    # Step 7: GET /api/triage & POST /api/triage/{email_id}/review (Verify Triage Workspace)
    print("\n[5] GET /api/triage...")
    r_tr = client.get(f"/api/triage?candidate_id={test_cand}")
    print(f"Status: {r_tr.status_code}")
    assert r_tr.status_code == 200
    triage_items = r_tr.json()
    print(f"Triage Queue items count: {len(triage_items)}")
    
    # Let's find one triage item and review it
    triage_email_id = None
    for item in triage_items:
        if item["email_id"] == "em_triage003":
            triage_email_id = item["email_id"]
            break
    if not triage_email_id and triage_items:
        triage_email_id = triage_items[0]["email_id"]

    if triage_email_id:
        print(f"\n[6] POST /api/triage/{triage_email_id}/review...")
        review_payload = {
            "assignee_id": "u_rohit",
            "category": "smb_enquiry",
            "priority": "high",
            "notes": "Escalated to SMB Rohit after human triage review."
        }
        r_rev = client.post(f"/api/triage/{triage_email_id}/review?candidate_id={test_cand}", json=review_payload)
        print(f"Review Status: {r_rev.status_code}, Res: {r_rev.text}")
        assert r_rev.status_code == 200

        # Verify task was updated
        r_tasks = client.get(f"/api/tasks?candidate_id={test_cand}")
        tasks = r_tasks.json().get("tasks", []) if isinstance(r_tasks.json(), dict) else r_tasks.json()
        target_task = None
        for t in tasks:
            if t["source_email_id"] == triage_email_id:
                target_task = t
                break
        print(f"Verifying reviewed task: {json.dumps(target_task, indent=2)}")
        assert target_task is not None
        assert target_task["assignee_id"] == "u_rohit"
        assert target_task["category"] == "smb_enquiry"
        assert target_task["priority"] == "high"

    # Step 8: POST /api/chat (Verify new intents LIST_RUNS and DECISION_TRACE)
    print("\n[7] POST /api/chat (Run History)...")
    r_chat_runs = client.post("/api/chat", json={"candidate_id": test_cand, "query": "show me my ingestion run history"})
    print(f"Chat Runs Status: {r_chat_runs.status_code}")
    print(f"Answer: {r_chat_runs.json()['answer']}")
    assert r_chat_runs.status_code == 200

    print("\n[8] POST /api/chat (Decision Trace)...")
    r_chat_trace = client.post("/api/chat", json={"candidate_id": test_cand, "query": "why was Halcyon cloud migration proposal routed and who got it?"})
    print(f"Chat Trace Status: {r_chat_trace.status_code}")
    print(f"Answer: {r_chat_trace.json()['answer']}")
    assert r_chat_trace.status_code == 200

    print("\n" + "=" * 70)
    print("SUCCESS: ALL INTELLIGENCE & OPERATIONS ENDPOINTS FULLY VERIFIED!")
    print("=" * 70)

if __name__ == "__main__":
    main()
