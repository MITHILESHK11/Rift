from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.db.database import get_db
from app.config import settings, normalize_email
from app.services.chat_executor import execute_grounded_chat_query

router = APIRouter(tags=["Grounded Chat API (Section 7.3)"])

class ChatMessage(BaseModel):
    sender: str
    text: str
    supporting_data: Optional[Dict[str, Any]] = None

class ChatQueryPayload(BaseModel):
    candidate_id: str
    query: str
    history: Optional[List[ChatMessage]] = None

@router.post("/api/chat")
@router.post("/chat")
async def chat_endpoint(payload: ChatQueryPayload, db: Session = Depends(get_db)):
    """Section 7.3: Grounded Conversational Q&A endpoint with supporting_data and history."""
    norm_cand_id = normalize_email(payload.candidate_id)
    history_list = []
    if payload.history:
        history_list = [
            {"sender": msg.sender, "text": msg.text, "supporting_data": msg.supporting_data}
            for msg in payload.history
        ]
    result = await execute_grounded_chat_query(
        db, 
        payload.query, 
        candidate_id=norm_cand_id,
        history=history_list
    )
    return result
