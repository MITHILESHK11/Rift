import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import engine, Base
from app.db.mongo import init_mongo_indexes, is_mongo_active, clear_all_mongo_data
from app.routers import tasks, ingest, chat, stats, users, intelligence
from app.services.sample_generator import generate_sample_emails

# Create DB tables for SQL fallback (gracefully catch read-only filesystem errors on Vercel)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"SQL fallback table creation skipped on serverless: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if is_mongo_active():
        await init_mongo_indexes()
    yield
    # Shutdown

app = FastAPI(
    title="RIFT — Sales Inbox Router & Grounded Chat",
    description="Production-grade sales inbox routing service with deterministic rules engine, language model extraction, candidate-scoped task persistence, and grounded natural-language query interface.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(tasks.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(stats.router)
app.include_router(users.router)
app.include_router(intelligence.router)

@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RIFT Sales Inbox Router",
        "mongodb_active": is_mongo_active(),
        "candidate_id": settings.CANDIDATE_ID,
        "docs_url": "/docs"
    }

@app.get("/api/docs", include_in_schema=False)
def api_docs_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

@app.get("/api/sample-emails")
def get_sample_emails(count: int = 250):
    """Utility endpoint supplying synthetic test email batch for frontend testing."""
    return {"emails": generate_sample_emails(count=min(count, 250))}

@app.post("/api/clear-database")
@app.delete("/api/clear-database")
async def clear_database(candidate_id: str = None):
    """Wipes tasks/emails for a specific candidate_id only (requires candidate_id param).
    Blocked in production unless ALLOW_CLEAR_DATABASE=true env var is explicitly set."""
    # Block in production unless explicitly allowed
    if os.getenv("ALLOW_CLEAR_DATABASE", "").lower() != "true":
        return {"status": "error", "message": "Database clear endpoint is disabled. Set ALLOW_CLEAR_DATABASE=true env var to enable."}

    # Require candidate_id to prevent accidental full wipes
    if not candidate_id or not candidate_id.strip():
        return {"status": "error", "message": "candidate_id query parameter is required to scope the database clear."}

    # Protect the real production candidate from being wiped by test scripts
    PROTECTED_CANDIDATES = {"m.kolhapurkar3529@gmail.com"}
    if candidate_id.strip().lower() in PROTECTED_CANDIDATES:
        return {"status": "error", "message": f"Candidate '{candidate_id}' is protected and cannot be cleared."}

    from app.db.models import TaskModel, ProcessedEmailModel, ThreadMapModel, IngestionRunModel
    from app.db.database import SessionLocal
    from app.config import normalize_email

    norm_id = normalize_email(candidate_id)
    cleaned_mongo = False

    if is_mongo_active():
        # Scoped delete — only this candidate's data
        mongo_db = get_motor_db() if True else None
        from app.db.mongo import get_motor_db as _get_motor_db
        _mongo_db = _get_motor_db()
        if _mongo_db is not None:
            await _mongo_db.tasks.delete_many({"candidate_id": norm_id})
            await _mongo_db.processed_emails.delete_many({"candidate_id": norm_id})
            await _mongo_db.thread_map.delete_many({"candidate_id": norm_id})
            await _mongo_db.ingestion_runs.delete_many({"candidate_id": norm_id})
            cleaned_mongo = True

    session = SessionLocal()
    try:
        session.query(TaskModel).filter(TaskModel.candidate_id == norm_id).delete()
        session.query(ProcessedEmailModel).filter(ProcessedEmailModel.candidate_id == norm_id).delete()
        session.query(IngestionRunModel).filter(IngestionRunModel.candidate_id == norm_id).delete()
        session.commit()
    finally:
        session.close()

    return {
        "status": "success",
        "message": f"Data for candidate '{norm_id}' wiped clean.",
        "mongo_cleared": cleaned_mongo
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
