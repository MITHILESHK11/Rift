import json
import httpx
import os

def main():
    json_path = "../test.json"
    if not os.path.exists(json_path):
        print("test.json not found.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        emails = json.load(f)
        
    print(f"Loaded {len(emails)} emails from test.json")
    
    cand_id = "m.kolhapurkar3529@gmail.com"
    payload = {
        "candidate_id": cand_id,
        "emails": emails
    }
    
    url = f"http://127.0.0.1:8000/api/ingest?candidate_id={cand_id}"
    print("Ingesting to local server:", url)
    
    try:
        r = httpx.post(url, json=payload, timeout=30.0)
        print("Status code:", r.status_code)
        print("Response:", r.json())
    except Exception as e:
        print("Ingestion error:", e)

if __name__ == "__main__":
    main()
