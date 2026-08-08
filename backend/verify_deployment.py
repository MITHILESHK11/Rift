import sys
import json
import httpx

def verify_backend(base_url="http://localhost:8000"):
    print(f"--- Running Verification Checklist against {base_url} ---")
    candidate_id = "evaluator.test@gmail.com"

    # 1. Health check
    try:
        r = httpx.get(f"{base_url}/health", timeout=5.0)
        print(f"1. GET /health: Status {r.status_code} | {r.json()}")
        assert r.status_code == 200
    except Exception as e:
        print(f"1. GET /health FAILED: {e}")
        return False

    # 2. Users roster
    try:
        r = httpx.get(f"{base_url}/users", timeout=5.0)
        print(f"2. GET /users: Status {r.status_code} | Count: {len(r.json())}")
        assert r.status_code == 200
    except Exception as e:
        print(f"2. GET /users FAILED: {e}")
        return False

    # 3. Create task
    try:
        task_payload = {
            "candidate_id": candidate_id,
            "source_email_id": "em_smoke_001",
            "thread_id": "th_smoke_001",
            "title": "Smoke Test Enterprise RFP",
            "assignee_id": "u_aarti",
            "category": "enterprise_rfp",
            "priority": "high",
            "deal_value_inr": 2500000,
            "company_name": "Smoke Test Corp",
            "confidence": 0.98
        }
        r = httpx.post(f"{base_url}/tasks", json=task_payload, timeout=5.0)
        print(f"3. POST /tasks: Status {r.status_code} | task_id: {r.json().get('task_id')}")
        assert r.status_code in [200, 201]
    except Exception as e:
        print(f"3. POST /tasks FAILED: {e}")
        return False

    # 4. List tasks (Candidate Scoped)
    try:
        r = httpx.get(f"{base_url}/tasks?candidate_id={candidate_id}", timeout=5.0)
        tasks = r.json()
        print(f"4. GET /tasks?candidate_id={candidate_id}: Status {r.status_code} | Task Count: {len(tasks)}")
        assert r.status_code == 200
        assert isinstance(tasks, list)
    except Exception as e:
        print(f"4. GET /tasks FAILED: {e}")
        return False

    # 5. Ingest batch
    try:
        ingest_payload = {
            "candidate_id": candidate_id,
            "emails": [
                {
                    "email_id": "em_smoke_002",
                    "thread_id": "th_smoke_002",
                    "from_name": "Ankit Bose",
                    "from_email": "ankit@railyard.in",
                    "subject": "Demo Request - Railyard Logistics",
                    "body": "Hi team, we need a demo of your platform for 30 users by Friday."
                }
            ]
        }
        r = httpx.post(f"{base_url}/ingest", json=ingest_payload, timeout=10.0)
        print(f"5. POST /ingest: Status {r.status_code} | Summary: {r.json()}")
        assert r.status_code == 200
    except Exception as e:
        print(f"5. POST /ingest FAILED: {e}")
        return False

    # 6. System Stats
    try:
        r = httpx.get(f"{base_url}/api/stats?candidate_id={candidate_id}", timeout=5.0)
        print(f"6. GET /api/stats: Status {r.status_code} | Stats: {r.json()}")
        assert r.status_code == 200
    except Exception as e:
        print(f"6. GET /api/stats FAILED: {e}")
        return False

    # 7. Grounded Chat
    try:
        chat_payload = {
            "candidate_id": candidate_id,
            "query": "How many high priority tasks do I have?"
        }
        r = httpx.post(f"{base_url}/api/chat", json=chat_payload, timeout=10.0)
        print(f"7. POST /api/chat: Status {r.status_code} | Answer: '{r.json().get('answer')}'")
        assert r.status_code == 200
        assert "supporting_data" in r.json()
    except Exception as e:
        print(f"7. POST /api/chat FAILED: {e}")
        return False

    print("\n--- ALL VERIFICATION CHECKLIST STEPS PASSED SUCCESSFULLY! ---")
    return True

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    success = verify_backend(url)
    sys.exit(0 if success else 1)
