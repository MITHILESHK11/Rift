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
    title="Sales Inbox Task Router & Grounded Chat API",
    description="Unified backend service fulfilling Alumnx FDE Challenge specs with Motor MongoDB & Vercel support.",
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
        "service": "Sales Inbox Task Router & Grounded Chat API",
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
async def clear_database():
    """Wipes all tasks, processed email logs, and thread maps from database safely."""
    if os.getenv("ENVIRONMENT", "development").lower() == "production" and not os.getenv("ALLOW_CLEAR_DATABASE", "").lower() == "true":
        return {"status": "error", "message": "Database clear endpoint disabled in production environment."}

    from app.db.models import TaskModel, ProcessedEmailModel, ThreadMapModel
    from app.db.database import SessionLocal

    cleaned_mongo = False
    if is_mongo_active():
        cleaned_mongo = await clear_all_mongo_data()

    session = SessionLocal()
    try:
        session.query(TaskModel).delete()
        session.query(ProcessedEmailModel).delete()
        session.query(ThreadMapModel).delete()
        session.commit()
    finally:
        session.close()

    return {
        "status": "success",
        "message": "Database wiped clean.",
        "mongo_cleared": cleaned_mongo
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
