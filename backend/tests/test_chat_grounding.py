from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_zero_count_trap():
    payload = {
        "candidate_id": "user@example.com",
        "query": "How many emails were about GST refunds?"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["supporting_data"].get("gst_refund_count", data["supporting_data"].get("matched_task_count")) == 0
    assert "0" in data["answer"]

def test_chat_out_of_scope_trap():
    payload = {
        "candidate_id": "user@example.com",
        "query": "Send Aarti an email about the Meridian Steel RFP."
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "cannot send emails" in data["answer"].lower() or "read-only" in data["answer"].lower()

def test_chat_spurious_rate():
    payload = {
        "candidate_id": "user@example.com",
        "query": "What is our spurious rate so far?"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "spurious_rate" in data["supporting_data"]
