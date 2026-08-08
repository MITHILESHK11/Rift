import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    mongo_url = os.getenv("MONGODB_URL") or os.getenv("MONGO_URI")
    if not mongo_url:
        print("No MongoDB URL found.")
        return
        
    print("Connecting to MongoDB:", mongo_url)
    client = AsyncIOMotorClient(mongo_url)
    try:
        db = client.get_default_database()
    except Exception:
        db = client["sales_inbox"]
    
    try:
        tasks_cands = await db.tasks.distinct("candidate_id")
        print("Unique candidate_ids in tasks:", tasks_cands)
        tasks_count = await db.tasks.count_documents({})
        print("Total tasks in MongoDB:", tasks_count)
    except Exception as e:
        print("Error fetching tasks:", e)
        
    try:
        emails_cands = await db.processed_emails.distinct("candidate_id")
        print("Unique candidate_ids in processed_emails:", emails_cands)
        emails_count = await db.processed_emails.count_documents({})
        print("Total processed_emails in MongoDB:", emails_count)
    except Exception as e:
        print("Error fetching processed_emails:", e)
        
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
