import httpx

def main():
    prod_url = "https://rift-tan.vercel.app"
    cand_id = "m.kolhapurkar3529@gmail.com"
    
    print("Checking Production Tasks...")
    try:
        r = httpx.get(f"{prod_url}/api/tasks?candidate_id={cand_id}", timeout=10.0)
        print("GET /api/tasks status:", r.status_code)
        if r.status_code == 200:
            tasks = r.json()
            tasks_list = tasks.get("tasks", []) if isinstance(tasks, dict) else tasks
            print(f"Pushed to Vercel Tasks: {len(tasks_list)} found.")
        else:
            print("Response text:", r.text)
    except Exception as e:
        print("GET /api/tasks Error:", e)

    print("\nChecking Production Stats...")
    try:
        r = httpx.get(f"{prod_url}/api/stats?candidate_id={cand_id}", timeout=10.0)
        print("GET /api/stats status:", r.status_code)
        if r.status_code == 200:
            print("Stats:", r.json())
        else:
            print("Response text:", r.text)
    except Exception as e:
        print("GET /api/stats Error:", e)

    print("\nChecking Production Chat...")
    try:
        r = httpx.post(f"{prod_url}/api/chat", json={
            "candidate_id": cand_id,
            "query": "show me my tasks"
        }, timeout=10.0)
        print("POST /api/chat status:", r.status_code)
        if r.status_code == 200:
            print("Chat Response:", r.json())
        else:
            print("Response text:", r.text)
    except Exception as e:
        print("POST /api/chat Error:", e)

if __name__ == "__main__":
    main()
