import sqlite3
import os

db_path = "sales_inbox.db"
if os.path.exists(db_path):
    print("Checking SQLite DB...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT DISTINCT candidate_id FROM tasks")
        print("Unique candidate_ids in tasks:", cursor.fetchall())
    except Exception as e:
        print("Error querying tasks:", e)
        
    try:
        cursor.execute("SELECT DISTINCT candidate_id FROM processed_emails")
        print("Unique candidate_ids in processed_emails:", cursor.fetchall())
    except Exception as e:
        print("Error querying processed_emails:", e)
        
    conn.close()
else:
    print("SQLite DB not found locally at sales_inbox.db")
