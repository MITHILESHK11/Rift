import json
import sys
import os
import httpx

def run_verification(base_url: str):
    print("=" * 70)
    print(f"VERIFYING ALL ENDPOINTS AGAINST: {base_url}")
    print("=" * 70)

    client = httpx.Client(base_url=base_url, timeout=15.0)

    test_cand = "verification.test@company.com"

    # 1. GET /health & /api/health
    r_health = client.get("/health")
    print(f"[1] GET /health -> Status: {r_health.status_code}")
    assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
    
    r_api_health = client.get("/api/health")
    print(f"[2] GET /api/health -> Status: {r_api_health.status_code}")
    assert r_api_health.status_code == 200

    # 2. GET /docs & /api/docs & /openapi.json
    r_docs = client.get("/docs")
    print(f"[3] GET /docs -> Status: {r_docs.status_code}")
    assert r_docs.status_code == 200

    r_api_docs = client.get("/api/docs", follow_redirects=True)
    print(f"[4] GET /api/docs -> Status: {r_api_docs.status_code}")
    assert r_api_docs.status_code == 200

    r_openapi = client.get("/openapi.json")
    print(f"[5] GET /openapi.json -> Status: {r_openapi.status_code}")
    assert r_openapi.status_code == 200

    # 3. GET /users & /api/users
    r_users = client.get("/api/users")
    print(f"[6] GET /api/users -> Status: {r_users.status_code}")
    assert r_users.status_code == 200
    assert "team" in r_users.json()

    # 4. GET /api/sample-emails
    r_sample = client.get("/api/sample-emails?count=10")
    print(f"[7] GET /api/sample-emails -> Status: {r_sample.status_code}")
    assert r_sample.status_code == 200
    sample_emails = r_sample.json().get("emails", [])
    assert len(sample_emails) > 0

    # 5. POST /api/clear-database (reset state for clean test — scoped to test candidate only)
    r_clear = client.post(f"/api/clear-database?candidate_id={test_cand}")
    print(f"[8] POST /api/clear-database -> Status: {r_clear.status_code}, Res: {r_clear.json()}")
    # Accept success or "disabled" (production) — either is OK
    assert r_clear.status_code == 200

    # 6. POST /api/ingest (Object Payload)
    ingest_obj = {
        "candidate_id": test_cand,
        "emails": sample_emails[:5]
    }
    r_ingest_obj = client.post(f"/api/ingest?candidate_id={test_cand}", json=ingest_obj)
    print(f"[9] POST /api/ingest (Object) -> Status: {r_ingest_obj.status_code}, Res: {r_ingest_obj.json()}")
    assert r_ingest_obj.status_code == 200
    assert r_ingest_obj.json()["processed"] == len(sample_emails[:5])

    # 7. POST /api/ingest (Raw Array Payload)
    r_ingest_arr = client.post(f"/api/ingest?candidate_id={test_cand}", json=sample_emails[5:10])
    print(f"[10] POST /api/ingest (Raw Array) -> Status: {r_ingest_arr.status_code}, Res: {r_ingest_arr.json()}")
    assert r_ingest_arr.status_code == 200

    # 8. GET /api/tasks & GET /api/stats
    r_tasks = client.get(f"/api/tasks?candidate_id={test_cand}")
    res_tasks_json = r_tasks.json()
    task_count = len(res_tasks_json.get('tasks', [])) if isinstance(res_tasks_json, dict) else len(res_tasks_json)
    print(f"[11] GET /api/tasks -> Status: {r_tasks.status_code}, Tasks Count: {task_count}")
    assert r_tasks.status_code == 200

    r_stats = client.get(f"/api/stats?candidate_id={test_cand}")
    print(f"[12] GET /api/stats -> Status: {r_stats.status_code}, Stats: {r_stats.json()}")
    assert r_stats.status_code == 200

    # 9. POST /api/chat (Grounded Q&A)
    r_chat1 = client.post("/api/chat", json={"candidate_id": test_cand, "query": "How many emails were proposal or RFP related?"})
    print(f"[13] POST /api/chat (RFP) -> Status: {r_chat1.status_code}, Res: {r_chat1.json()}")
    assert r_chat1.status_code == 200
    assert "answer" in r_chat1.json()

    r_chat2 = client.post("/api/chat", json={"candidate_id": test_cand, "query": "what are the tasks here"})
    print(f"[14] POST /api/chat (Tasks) -> Status: {r_chat2.status_code}, Res: {r_chat2.json()}")
    assert r_chat2.status_code == 200

    # 10. POST /api/ingest-single (Real Email Reader)
    single_payload = {
        "candidate_id": test_cand,
        "from_name": "Test Vendor",
        "from_email": "vendor@testcorp.com",
        "subject": "Invoice INV-9901 Payment",
        "body": "Hi, attached invoice INV-9901 for Rs 50,000.",
        "received_at": "2026-08-08T18:00:00+05:30"
    }
    r_single = client.post("/api/ingest-single", json=single_payload)
    print(f"[15] POST /api/ingest-single -> Status: {r_single.status_code}, Action: {r_single.json().get('action')}")
    assert r_single.status_code == 200

    print("=" * 70)
    print("ALL 15 ENDPOINT VERIFICATION TESTS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    run_verification(target_url)
