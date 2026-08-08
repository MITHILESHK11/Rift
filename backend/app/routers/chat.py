from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.db.database import get_db
from app.config import settings, normalize_email
from app.services.chat_executor import execute_grounded_chat_query

router = APIRouter(tags=["Grounded Chat API (Section 7.3)"])

class ChatQueryPayload(BaseModel):
    candidate_id: str
    query: str

@router.post("/api/chat")
@router.post("/chat")
async def chat_endpoint(payload: ChatQueryPayload, db: Session = Depends(get_db)):
    """Section 7.3: Grounded Conversational Q&A endpoint with supporting_data."""
    norm_cand_id = normalize_email(payload.candidate_id)
    result = await execute_grounded_chat_query(db, payload.query, candidate_id=norm_cand_id)
    return result
