from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_task_invalid_enum():
    payload = {
        "candidate_id": "user@example.com",
        "source_email_id": "em_test_001",
        "thread_id": "th_test_001",
        "title": "Test Task",
        "assignee_id": "Aarti",  # Bad enum! Should be u_aarti
        "category": "enterprise_rfp",
        "priority": "medium"
    }
    response = client.post("/tasks", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "invalid_enum_value"
    assert data["field"] == "assignee_id"
    assert data["received"] == "Aarti"
    assert "u_aarti" in data["allowed"]

def test_create_task_success_and_dedup():
    payload = {
        "candidate_id": "user@example.com",
        "source_email_id": "em_test_002",
        "thread_id": "th_test_002",
        "title": "Valid Enterprise RFP",
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "high",
        "due_date": "2026-08-12",
        "deal_value_inr": 2500000,
        "company_name": "Meridian Steel",
        "confidence": 0.95
    }
    # First post
    res1 = client.post("/tasks", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()
    assert "task_id" in data1

    # Second post (duplicate email_id)
    res2 = client.post("/tasks", json=payload)
    data2 = res2.json()
    assert data2["task_id"] == data1["task_id"]
    assert data2.get("note") == "existing_duplicate"

def test_list_tasks_and_candidate_isolation():
    # User A query
    resA = client.get("/tasks?candidate_id=user@example.com")
    assert resA.status_code == 200
    dataA = resA.json()
    assert isinstance(dataA, list)
    assert len(dataA) > 0
    assert dataA[0]["candidate_id"] == "user@example.com"

    # User B query (must return 0 tasks and MUST NOT reassign User A's tasks!)
    resB = client.get("/tasks?candidate_id=other_user@example.com")
    assert resB.status_code == 200
    dataB = resB.json()
    assert isinstance(dataB, list)
    assert len(dataB) == 0

    # Verify User A's tasks are intact and were NOT mutated by User B's GET request
    resA_check = client.get("/tasks?candidate_id=user@example.com")
    assert resA_check.status_code == 200
    dataA_check = resA_check.json()
    assert len(dataA_check) == len(dataA)
    assert dataA_check[0]["candidate_id"] == "user@example.com"
