import os
import asyncio
from typing import Optional, Dict, Any, List
import motor.motor_asyncio
from pymongo import IndexModel, ASCENDING
from app.config import settings

_mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_db = None

def get_mongo_url() -> str:
    return settings.MONGODB_URL or (settings.DATABASE_URL if settings.DATABASE_URL.startswith("mongodb") else "")

def get_motor_client() -> Optional[motor.motor_asyncio.AsyncIOMotorClient]:
    global _mongo_client
    mongo_url = get_mongo_url()
    if not mongo_url:
        return None
    if _mongo_client is None:
        _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000
        )
    return _mongo_client

def get_motor_db():
    global _db
    client = get_motor_client()
    if client is None:
        return None
    if _db is None:
        try:
            _db = client.get_default_database()
        except Exception:
            _db = client["sales_inbox"]
    return _db

async def init_mongo_indexes():
    """Initializes candidate-scoped compound indexes on MongoDB Atlas for fast performance & multi-tenancy isolation."""
    db = get_motor_db()
    if db is None:
        return

    try:
        # Tasks indexes
        await db.tasks.create_index([("candidate_id", ASCENDING), ("source_email_id", ASCENDING)], unique=True)
        await db.tasks.create_index([("candidate_id", ASCENDING), ("thread_id", ASCENDING)])
        await db.tasks.create_index([("candidate_id", ASCENDING), ("category", ASCENDING)])
        await db.tasks.create_index([("candidate_id", ASCENDING), ("assignee_id", ASCENDING)])
        await db.tasks.create_index([("candidate_id", ASCENDING), ("priority", ASCENDING)])

        # Processed emails indexes
        await db.processed_emails.create_index([("candidate_id", ASCENDING), ("email_id", ASCENDING)], unique=True)
        await db.processed_emails.create_index([("candidate_id", ASCENDING), ("status", ASCENDING)])

        # Thread map indexes
        await db.thread_map.create_index([("candidate_id", ASCENDING), ("thread_id", ASCENDING)], unique=True)
    except Exception as e:
        print(f"MongoDB index init notice: {e}")

def is_mongo_active() -> bool:
    return get_mongo_url() != ""

async def clear_all_mongo_data():
    """Clears all collections in MongoDB."""
    db = get_motor_db()
    if db is not None:
        await db.tasks.delete_many({})
        await db.processed_emails.delete_many({})
        await db.thread_map.delete_many({})
        return True
    return False
